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

    def __init__(
        self,
        proc: subprocess.CompletedProcess,
        outputs: dict,
        summary: str,
        exported: dict,
        path_additions: list,
    ):
        self.proc = proc
        self.returncode = proc.returncode
        self.stdout = proc.stdout
        self.stderr = proc.stderr
        self.outputs = outputs
        self.summary = summary
        # What the step handed to the steps after it, via $GITHUB_ENV and
        # $GITHUB_PATH. A step that "selects a toolchain" is only observable
        # through these.
        self.exported = exported
        self.path_additions = path_additions

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

    `GITHUB_OUTPUT`, `GITHUB_ENV`, `GITHUB_PATH` and `GITHUB_STEP_SUMMARY`
    are real files, so a step that writes `ran=false` to `$GITHUB_OUTPUT`
    can be asserted on exactly as the next step would read it, and a step
    that selects a toolchain is observable through what it exported.

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
        path_file = tmp_path / "_github_path"
        for f in (out_file, env_file, sum_file, path_file):
            f.write_text("", encoding="utf-8")

        base = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(tmp_path),
            "LANG": "C.UTF-8",
            "GITHUB_OUTPUT": str(out_file),
            "GITHUB_ENV": str(env_file),
            "GITHUB_STEP_SUMMARY": str(sum_file),
            "GITHUB_PATH": str(path_file),
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

        def as_pairs(path):
            pairs = {}
            for line in path.read_text(encoding="utf-8").splitlines():
                if "=" in line:
                    key, _, value = line.partition("=")
                    pairs[key] = value
            return pairs

        return ShellResult(
            proc,
            as_pairs(out_file),
            sum_file.read_text(encoding="utf-8"),
            as_pairs(env_file),
            [ln for ln in path_file.read_text(encoding="utf-8").splitlines() if ln.strip()],
        )

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
            # A scripted `gh`. `--jq` is applied for real, by shelling out to
            # jq, because several scripts here rely on gh doing the transform
            # and a fake that returned raw JSON would exercise a code path
            # that never runs in production.
            import json, subprocess, sys, pathlib
            argv = sys.argv[1:]
            args = " ".join(argv)
            pathlib.Path({str(calls_file)!r}).open("a").write(args + "\\n")

            jq_filter = None
            for i, a in enumerate(argv):
                if a == "--jq" and i + 1 < len(argv):
                    jq_filter = argv[i + 1]
                elif a.startswith("--jq="):
                    jq_filter = a[len("--jq="):]

            for route in json.loads(pathlib.Path({str(routes_file)!r}).read_text()):
                if route["match"] in args:
                    out = route["stdout"]
                    if jq_filter and route["code"] == 0 and out.strip():
                        done = subprocess.run(
                            ["jq", "-r", jq_filter],
                            input=out, capture_output=True, text=True,
                        )
                        if done.returncode != 0:
                            sys.stderr.write(done.stderr)
                            sys.exit(done.returncode)
                        out = done.stdout
                    sys.stdout.write(out)
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

    Registered in sys.modules before it runs, as importlib's own recipe for
    importing a file does. A script with a dataclass needs it: under
    postponed annotations, dataclasses resolves each field's type through
    sys.modules, and an unregistered module fails to load at all.
    """
    import importlib.util
    import sys

    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# --- Template sync worlds -------------------------------------------------
#
# Template sync is only as trustworthy as the situations it has been put in,
# and almost none of them can be faked: it reads git trees, merges with git,
# matches with git and writes through git's index. So these are REAL
# repositories - a template with tagged releases, and a repository generated
# from it exactly as GitHub does (the same tree, one commit) and initialised
# with init-template.py's own functions - built in a temporary directory with
# no network and no global git configuration.

SYNC_ENV = {
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@example.invalid",
}

TEMPLATE_LIST = """\
# 🔄 TEMPLATE SYNC - what tannergolden/path keeps current here
#
# A line naming a path is kept current; `#/path` is left to you.

# --- Kept current -----------------------------------------------------------
/.github/workflows/checks.yml
/docs/guide.md
/scripts/tool.py

# --- Yours: seeded once, never synced ---------------------------------------
#/README.md
#/LICENSE

# --- Template only ------------------------------------------------------------
#/.github/TEMPLATE_INIT

# --- Your rules ---------------------------------------------------------------
"""

TEMPLATE_FILES = {
    ".github/template-sync": TEMPLATE_LIST,
    ".github/TEMPLATE_INIT": "This repository has not been initialised yet.\n",
    "README.md": "# Template\n\nReplace this README.\n",
    "LICENSE": "MIT License\n\nCopyright (c) 2026 Tanner Golden\n",
    ".github/workflows/checks.yml": (
        "name: checks\n"
        "# The commands your project builds with.\n"
        "jobs:\n"
        "  ci:\n"
        "    with:\n"
        "      lint-command: 'validate'\n"
    ),
    "docs/guide.md": "# Guide\n\nBuilt with ❤️ by [@tannergolden](https://github.com/tannergolden).\n",
    "scripts/tool.py": "print('tool')\n",
}


class SyncWorld:
    """A template, and a repository generated from it, as real git repositories."""

    TEMPLATE = "tannergolden/path"
    OWNER, REPOSITORY, NAME, YEAR = "janedoe", "janedoe/widget", "Jane Doe", 2027

    def __init__(self, root: Path):
        self.root = root
        self.template = root / "template"
        self.repo = root / "derived"
        self.sync = load_script("scripts/template-sync.py")
        self.init = self.sync.INIT
        self.versions: list[str] = []
        self.template.mkdir()
        self.git(self.template, "init", "-q", "-b", "Development")

    # Plumbing

    def git(self, where: Path, *args: str, data: bytes | None = None) -> str:
        proc = subprocess.run(
            ["git", "-C", str(where), *args],
            input=data,
            capture_output=True,
            env={**os.environ, **SYNC_ENV},
            check=False,
        )
        if proc.returncode != 0:
            raise AssertionError(f"git {' '.join(args)} failed: {proc.stderr.decode()}")
        return proc.stdout.decode("utf-8", "surrogateescape")

    @staticmethod
    def put(where: Path, files: dict, modes: dict | None = None) -> None:
        """Write `files` (None deletes) and set any `modes` ('100755' marks executable)."""
        for rel, content in files.items():
            path = where / rel
            if content is None:
                if path.exists() or path.is_symlink():
                    path.unlink()
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.encode() if isinstance(content, str) else content)
        for rel, mode in (modes or {}).items():
            path = where / rel
            path.chmod(0o755 if mode == "100755" else 0o644)

    def commit(self, where: Path, message: str) -> str:
        self.git(where, "add", "-A")
        self.git(where, "commit", "-q", "--allow-empty", "-m", message)
        return self.git(where, "rev-parse", "HEAD").strip()

    # The template's side

    def release(self, version: str, files: dict | None = None, modes: dict | None = None,
                move_major: bool = True) -> str:
        """Commit to the template, tag `version`, and move `v1` onto it as Cut Release does."""
        self.put(self.template, files or {}, modes)
        commit = self.commit(self.template, f"release {version}")
        self.git(self.template, "tag", version)
        if move_major:
            self.git(self.template, "tag", "-f", version.split(".")[0])
        self.versions.append(version)
        return commit

    # The generated repository's side

    def generate(self, *, init: bool = True, lock: bool = True) -> None:
        """What "Use this template" does, then what init does, at the template's v1."""
        self.repo.mkdir()
        self.git(self.repo, "init", "-q", "-b", "main")
        # The FULL tree at v1, as GitHub copies it. Not `git archive`, which
        # honours export-ignore - and both real templates mark .github/ so.
        self.git(self.repo, "fetch", "-q", str(self.template), "refs/tags/v1:refs/template/v1")
        self.git(self.repo, "read-tree", "refs/template/v1")
        self.git(self.repo, "checkout-index", "-a", "-f")
        self.commit(self.repo, "Initial commit")
        if not init:
            return
        for path in sorted(self.repo.rglob("*")):
            if not path.is_file() or ".git" in path.relative_to(self.repo).parts:
                continue
            rel = path.relative_to(self.repo).as_posix()
            data = path.read_bytes()
            new = self.init.initialised(
                rel, data, owner=self.OWNER, repo=self.REPOSITORY, display=self.NAME,
                template_owner=self.TEMPLATE.split("/")[0], year=self.YEAR,
            )
            if new != data:
                path.write_bytes(new)
        (self.repo / self.sync.SENTINEL).unlink()
        if lock:
            made = self.sync.generation_lock(
                self.repo, template=self.TEMPLATE,
                identity=self.sync.Identity(self.OWNER, self.REPOSITORY, self.NAME, self.YEAR),
            )
            (self.repo / self.sync.LOCK_PATH).write_text(self.sync.dump_lock(made), encoding="utf-8")
        self.git(self.repo, "add", "-A")
        self.git(self.repo, "commit", "-q", "--amend", "-m", "feat: initialise")

    def owner(self, files: dict, modes: dict | None = None, message: str = "owner edits") -> str:
        self.put(self.repo, files, modes)
        return self.commit(self.repo, message)

    def run_sync(self, *, workflow_files: bool = True, ref: str = "v1", merge: bool = True, **kwargs):
        """One sync, then - by default - its pull request merged."""
        result = self.sync.run(self.repo, self.template, ref=ref, workflow_files=workflow_files, **kwargs)
        if merge and result.changed:
            self.commit(self.repo, f"sync {result.version}")
        return result

    def read(self, rel: str) -> bytes | None:
        path = self.repo / rel
        return path.read_bytes() if path.is_file() else None

    def text(self, rel: str) -> str | None:
        data = self.read(rel)
        return data.decode("utf-8") if data is not None else None

    def lock(self):
        return self.sync.load_lock(self.text(self.sync.LOCK_PATH))

    def outcomes(self, result) -> dict[str, str]:
        return {d.path: d.outcome for d in result.decisions}

    def clean(self) -> bool:
        return not self.git(self.repo, "status", "--porcelain").strip()


@pytest.fixture
def sync_world(tmp_path, monkeypatch):
    """A template released at v1.0.0 with the default files, nothing generated yet."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for key, value in SYNC_ENV.items():
        monkeypatch.setenv(key, value)
    world = SyncWorld(tmp_path)
    world.release("v1.0.0", TEMPLATE_FILES, {"scripts/tool.py": "100755"})
    return world
