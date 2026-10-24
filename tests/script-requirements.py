# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The template's own scripts get their requirements before CI runs them.

The golden path template's `ci` job lints with
`python3 .github/scripts/validate-repository.py`, which imports `yaml`, and
names PyYAML in `.github/scripts/requirements.txt`. Nothing installed it:
`.github/actions/setup` set Python up only for a manifest at the root, so the
script ran on the runner's system Python and worked only while the image
happened to carry PyYAML, which the runner images do not promise.

So the setup action reads that file as a Python manifest, sets Python up at
the caller's `python-version`, and installs the file before the setup
command, lint, test and build, whatever `install` says. These hold the
step's gate, its place in the order, and the command it runs, read from the
action that ships.
"""

from __future__ import annotations

import os

from conftest import load_yaml, workflow_step_shell

ACTION = ".github/actions/setup/action.yml"
CI = ".github/workflows/ci.yml"
STEP = "📜 Install Script Requirements"
REQUIREMENTS = ".github/scripts/requirements.txt"


def steps() -> list[dict]:
    return load_yaml(ACTION)["runs"]["steps"]


def named(name: str) -> dict:
    return next(step for step in steps() if step.get("name") == name)


def fake_python(tmp_path, code: int = 0) -> tuple[dict, object]:
    """A `python` on PATH that records its arguments and exits with `code`."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    log = tmp_path / "python.log"
    shim = bindir / "python"
    shim.write_text(f'#!/bin/sh\necho "$@" >> "{log}"\nexit {code}\n', encoding="utf-8")
    shim.chmod(0o755)
    return {"PATH": f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}"}, log


class TestTheFileSetsPythonUp:
    def test_setup_python_reads_it_as_a_manifest(self):
        """The defect: only root manifests set Python up, so the template got the system one."""
        assert f"'{REQUIREMENTS}'" in named("🐍 Setup Python")["if"]

    def test_at_the_callers_version(self):
        assert named("🐍 Setup Python")["with"]["python-version"] == "${{ inputs.python-version }}"


class TestTheStep:
    def test_it_runs_only_where_the_file_is(self):
        assert named(STEP)["if"] == f"hashFiles('{REQUIREMENTS}') != ''"

    def test_it_does_not_wait_on_install(self):
        """`ci.yml` turns `install` off whenever a caller passes setup-command,
        and that command, like every stage after it, may run these scripts."""
        assert "install" not in named(STEP)["if"]

    def test_it_follows_setup_python_and_precedes_the_dependency_install(self):
        order = [step.get("name") for step in steps()]
        assert order.index("🐍 Setup Python") < order.index(STEP) < order.index("📦 Install Dependencies")

    def test_it_installs_the_file_into_the_python_just_set_up(self, run_shell, tmp_path):
        env, log = fake_python(tmp_path)
        result = run_shell(workflow_step_shell(ACTION, None, STEP), cwd=tmp_path / "repo", env=env)
        assert result.returncode == 0, result
        assert log.read_text(encoding="utf-8").split() == ["-m", "pip", "install", "--requirement", REQUIREMENTS]

    def test_a_failed_install_fails_the_step(self, run_shell, tmp_path):
        """A script that cannot import what it names fails every stage after it, so this must not pass."""
        env, _log = fake_python(tmp_path, code=1)
        result = run_shell(workflow_step_shell(ACTION, None, STEP), cwd=tmp_path / "repo", env=env)
        assert result.returncode != 0, result


class TestItLandsBeforeEveryStage:
    def validate(self) -> list[dict]:
        return load_yaml(CI)["jobs"]["validate"]["steps"]

    def test_ci_sets_up_before_the_setup_command_and_every_stage(self):
        names = [step.get("name") for step in self.validate()]
        setup = names.index("🧰 Setup Toolchain")
        for stage in ("📦 Run Setup Command", "✨ Run Linter", "🧪 Run Tests", "🏗️ Build Project"):
            assert setup < names.index(stage), f"{stage} runs before the script requirements are installed"

    def test_ci_hands_the_setup_action_its_python_version(self):
        step = next(step for step in self.validate() if step.get("name") == "🧰 Setup Toolchain")
        assert step["with"]["python-version"] == "${{ inputs.python-version }}"
