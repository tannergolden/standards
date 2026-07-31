# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""A non-integer java-version must fall back, not crash the step.

`actions/setup` builds a shell VARIABLE NAME from the input:

    VAR="JAVA_HOME_${WANTED}_X64"
    SELECTED="${!VAR:-}"

Any value that is not a bare integer produces an illegal identifier, and
bash aborts with `invalid variable name` under `set -euo pipefail`. The
input's own description promises the opposite: "Falls back to the image
default if the runner does not carry it."

So `java-version: '21.0.5'`, which is how most people write a Java version,
failed every job calling `actions/setup` in a repository with a pom.xml.
"""

from __future__ import annotations

import pytest
from conftest import workflow_step_shell

ACTION = "actions/setup/action.yml"
STEP = "☕ Select Java"

# Runner images expose preinstalled JDKs as JAVA_HOME_<major>_X64.
RUNNER = {"JAVA_HOME_21_X64": "/opt/java/21", "JAVA_HOME_17_X64": "/opt/java/17"}


def select(run_shell, tmp_path, wanted, runner=None, present=True):
    env = dict(runner if runner is not None else RUNNER)
    if present:
        for path in env.values():
            (tmp_path / path.lstrip("/")).mkdir(parents=True, exist_ok=True)
        env = {k: str(tmp_path / v.lstrip("/")) for k, v in env.items()}
    env["WANTED"] = wanted
    return run_shell(workflow_step_shell(ACTION, None, STEP), cwd=tmp_path, env=env)


class TestAnIntegerMajorIsSelected:
    @pytest.mark.parametrize("wanted", ["21", "17"])
    def test_it_is_written_to_the_environment(self, run_shell, tmp_path, wanted):
        """Selecting a toolchain is only observable through what the step
        hands to the steps after it."""
        result = select(run_shell, tmp_path, wanted)
        assert result.returncode == 0, result
        assert f"Selected preinstalled Java {wanted}" in result.stdout
        assert result.exported["JAVA_HOME"].endswith(f"/opt/java/{wanted}")
        assert result.path_additions == [result.exported["JAVA_HOME"] + "/bin"]

    def test_a_major_the_runner_lacks_falls_back(self, run_shell, tmp_path):
        result = select(run_shell, tmp_path, "8")
        assert result.returncode == 0, result
        assert "not preinstalled" in result.output
        assert result.exported == {}, "nothing may be exported for a JDK that is not there"


class TestANonIntegerFallsBackInsteadOfCrashing:
    @pytest.mark.parametrize(
        "wanted",
        ["21.0.5", "17.0.2", "temurin-21", "21 ", " 21", "1.8", "latest", ""],
    )
    def test_the_step_survives(self, run_shell, tmp_path, wanted):
        """The defect: bash aborted with `invalid variable name`."""
        result = select(run_shell, tmp_path, wanted)
        assert result.returncode == 0, result
        assert "invalid variable name" not in result.output
        assert result.exported == {}, "a value that names no runner variable must export nothing"

    @pytest.mark.parametrize("wanted", ["21.0.5", "temurin-21"])
    def test_it_says_why_it_fell_back(self, run_shell, tmp_path, wanted):
        result = select(run_shell, tmp_path, wanted)
        assert "::warning" in result.output or "::notice" in result.output
        assert wanted.strip() in result.output


class TestNothingIsWrittenWhenTheDirectoryIsAbsent:
    def test_a_variable_naming_a_missing_directory_is_ignored(self, run_shell, tmp_path):
        result = select(
            run_shell, tmp_path, "21", runner={"JAVA_HOME_21_X64": "/nowhere"}, present=False
        )
        assert result.returncode == 0, result
        assert "not preinstalled" in result.output
