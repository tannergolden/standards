# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Shared fixtures for the standards test suite.

THE HARD PART OF TESTING THIS REPOSITORY is that most of its logic does not
live in a file you can import. It lives in `run:` blocks inside reusable
workflows, and a reusable workflow cannot call a script from its own
repository: its checkout resolves to the CALLING repository, which is the
whole reason `actions/` exists. Factoring that shell out to `scripts/` to
make it testable would break the architecture the README sets out.

So the shell is not copied here. `workflow_step_shell()` reads the `run:`
block out of the workflow file that actually ships, and `run_shell()`
executes it against a temporary directory with the environment Actions
would provide. A test therefore exercises the shipped code, and editing the
workflow without editing the test is caught immediately.

Nothing here touches the network. `fake_gh` puts a scripted `gh` on PATH so
a script that shells out to it gets canned responses and records what it
asked for; a test that forgets to install it gets a `gh` that fails loudly
rather than a real one that reaches GitHub.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent


# --- Locating shipped code ------------------------------------------------


@pytest.fixture(scope="session")
def root() -> Path:
    """The repository root, so tests never depend on the working directory."""
    return ROOT


def load_yaml(rel: str) -> dict:
    """Parse a YAML file from the repository by its path relative to root."""
    return yaml.safe_load((ROOT / rel).read_text(encoding="utf-8"))


def workflow_on(doc: dict) -> dict:
    """The `on:` block of a parsed workflow.

    YAML 1.1 resolves a bare `on` key to the boolean true, and PyYAML
    follows the spec, so `doc["on"]` raises KeyError on every workflow file
    in this repository while `doc[True]` works. Handled once here rather
    than rediscovered by each test.
    """
    if "on" in doc:
        return doc["on"]
    return doc.get(True, {})


def workflow_inputs(rel: str) -> dict:
    """The declared `workflow_call` inputs of a reusable workflow."""
    return workflow_on(load_yaml(rel)).get("workflow_call", {}).get("inputs", {})


def _steps(doc: dict, job_id: str | None) -> list[dict]:
    if job_id is None:  # a composite action
        return doc["runs"]["steps"]
    return doc["jobs"][job_id]["steps"]


def workflow_step_shell(rel: str, job_id: str | None, step_id: str) -> str:
    """Return the `run:` shell of one step, read from the file that ships.

    `step_id` matches the step's `id:` first and its `name:` second, so a
    step without an id is still addressable. Raising on a miss is
    deliberate: a renamed step must break its test rather than silently
    stop being covered, which is the failure this whole suite exists to
    prevent elsewhere.
    """
    doc = load_yaml(rel)
    for step in _steps(doc, job_id):
        if step.get("id") == step_id or step.get("name") == step_id:
            if "run" not in step:
                raise AssertionError(f"{rel}: step {step_id!r} has no `run:` block")
            return step["run"]
    available = [s.get("id") or s.get("name") for s in _steps(doc, job_id)]
    raise AssertionError(f"{rel}: no step {step_id!r} in job {job_id!r}. Have: {available}")


# --- Executing it ---------------------------------------------------------


class ShellResult:
    """The outcome of running a step, in the terms Actions itself uses."""

    def __init__(self, proc: subprocess.CompletedProcess, outputs: dict, summary: str):
        self.proc = proc
        self.returncode = proc.returncode
        self.stdout = proc.stdout
        self.stderr = proc.stderr
        self.outputs = outputs
        self.summary = summary

    @property
    def output(self) -> str:
        """stdout and stderr together, for asserting on `::error` lines."""
        return self.stdout + self.stderr

    def __repr__(self) -> str:  # pragma: no cover - only used on failure
        return (
            f"<ShellResult rc={self.returncode} outputs={self.outputs!r}\n"
            f"--- stdout ---\n{self.stdout}\n--- stderr ---\n{self.stderr}>"
        )


@pytest.fixture
def run_shell(tmp_path):
    """Run a step's shell in a temp directory with Actions' environment.

    `GITHUB_OUTPUT`, `GITHUB_ENV` and `GITHUB_STEP_SUMMARY` are real files,
    so a step that writes `ran=false` to `$GITHUB_OUTPUT` can be asserted on
    exactly as the next step would read it.

    The environment is CLEARED apart from what a runner guarantees, so a
    test cannot pass because of a variable that happened to be exported in
    the developer's shell.
    """

    def _run(script: str, cwd: Path | None = None, env: dict | None = None, shell: str = "bash"):
        workdir = Path(cwd) if cwd else tmp_path
        workdir.mkdir(parents=True, exist_ok=True)
        runner_temp = tmp_path / "_runner_temp"
        runner_temp.mkdir(exist_ok=True)

        out_file = tmp_path / "_github_output"
        env_file = tmp_path / "_github_env"
        sum_file = tmp_path / "_github_summary"
        for f in (out_file, env_file, sum_file):
            f.write_text("", encoding="utf-8")

        base = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(tmp_path),
            "LANG": "C.UTF-8",
            "GITHUB_OUTPUT": str(out_file),
            "GITHUB_ENV": str(env_file),
            "GITHUB_STEP_SUMMARY": str(sum_file),
            "RUNNER_TEMP": str(runner_temp),
            "GITHUB_WORKSPACE": str(workdir),
        }
        base.update(env or {})

        script_file = tmp_path / "_step.sh"
        script_file.write_text(script, encoding="utf-8")
        proc = subprocess.run(
            [shell, str(script_file)],
            cwd=str(workdir),
            env=base,
            capture_output=True,
            text=True,
            timeout=120,
        )

        outputs = {}
        for line in out_file.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                outputs[key] = value
        return ShellResult(proc, outputs, sum_file.read_text(encoding="utf-8"))

    return _run


@pytest.fixture
def run_script(tmp_path, run_shell):
    """Run one of this repository's own scripts, by path relative to root."""

    def _run(rel: str, cwd: Path | None = None, env: dict | None = None):
        path = ROOT / rel
        assert path.is_file(), f"{rel} does not exist"
        interpreter = "bash" if path.suffix == ".sh" else "python3"
        return run_shell(
            f'exec {interpreter} "{path}"',
            cwd=cwd,
            env=env,
        )

    return _run


# --- Faking the outside world --------------------------------------------


@pytest.fixture
def fake_gh(tmp_path):
    """Put a scripted `gh` on PATH, and record every call made to it.

    Routes are matched as an ordered list of (substring, response) pairs
    against the joined argument list, so a test states only the part of the
    call it cares about. An unmatched call exits 1 with a loud message
    rather than returning empty output, because "the command produced
    nothing" is exactly the ambiguity several of these scripts get wrong.
    """
    bindir = tmp_path / "_fakebin"
    bindir.mkdir(exist_ok=True)
    routes_file = tmp_path / "_gh_routes.json"
    calls_file = tmp_path / "_gh_calls.log"
    calls_file.write_text("", encoding="utf-8")

    class Gh:
        def __init__(self):
            self.routes: list[tuple[str, str, int]] = []
            self._write()

        def _write(self):
            routes_file.write_text(
                json.dumps([{"match": m, "stdout": o, "code": c} for m, o, c in self.routes]),
                encoding="utf-8",
            )

        def route(self, match: str, stdout: str = "", code: int = 0):
            """Answer any call whose arguments contain `match`."""
            self.routes.append((match, stdout, code))
            self._write()
            return self

        @property
        def calls(self) -> list[str]:
            return [
                line for line in calls_file.read_text(encoding="utf-8").splitlines() if line
            ]

        @property
        def bin(self) -> str:
            return str(bindir)

        def env(self, **extra) -> dict:
            """The environment a script needs to reach this fake and nothing else."""
            merged = {"PATH": f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}"}
            merged.update(extra)
            return merged

    shim = bindir / "gh"
    shim.write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env python3
            import json, sys, pathlib
            args = " ".join(sys.argv[1:])
            pathlib.Path({str(calls_file)!r}).open("a").write(args + "\\n")
            for route in json.loads(pathlib.Path({str(routes_file)!r}).read_text()):
                if route["match"] in args:
                    sys.stdout.write(route["stdout"])
                    sys.exit(route["code"])
            sys.stderr.write("fake gh: no route for: " + args + "\\n")
            sys.exit(1)
            """
        ),
        encoding="utf-8",
    )
    shim.chmod(shim.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return Gh()


@pytest.fixture
def git_repo(tmp_path):
    """An initialized git repository, for scripts that shell out to git."""
    work = tmp_path / "work"
    work.mkdir()
    env = {**os.environ, "GIT_CONFIG_GLOBAL": str(tmp_path / "_gitconfig"), "HOME": str(tmp_path)}
    for args in (
        ["init", "-q", "-b", "main"],
        ["config", "user.name", "Test"],
        ["config", "user.email", "test@example.invalid"],
    ):
        subprocess.run(["git", *args], cwd=work, env=env, check=True)
    (work / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=work, env=env, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "chore(test): 🌱 seed", "--no-gpg-sign"],
        cwd=work,
        env=env,
        check=True,
    )
    return work


def requires(tool: str):
    """Skip a test when a tool the runner normally provides is absent."""
    return pytest.mark.skipif(shutil.which(tool) is None, reason=f"{tool} not installed")


def load_script(rel: str):
    """Import one of this repository's scripts as a module.

    The file names use hyphens, so they are not importable by name. Loading
    by path lets a test exercise a function directly instead of only
    through the process boundary.
    """
    import importlib.util

    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
