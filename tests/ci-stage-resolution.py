# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The primary required check must never report green having run nothing.

`ci.yml` resolves each stage the same way: an explicit command, else a
Makefile target of that name, else skip. The header states plainly that if
NOTHING resolves the job fails, "because a validation gate that validated
nothing is worse than no gate".

The probe for "does this repository define that target?" is what decides
all of it, and `make` does not answer the question people assume it does.
GNU make treats an existing FILE OR DIRECTORY of the target's name as an
already-satisfied target and exits 0 with no Makefile present at all. A
repository with a `build/` or `test/` directory therefore reported a stage
as having run when nothing ran, and the guard that exists to catch exactly
that saw `ran=true` and passed.

These tests run the shell out of the workflow that ships, in a temporary
directory, against the layouts that trigger it.
"""

from __future__ import annotations

import pytest
from conftest import workflow_step_shell

CI = ".github/workflows/ci.yml"

# (step id, the input the caller would pass, the Makefile target name)
STAGES = [
    ("lint", "COMMAND", "lint"),
    ("test", "COMMAND", "test"),
    ("build", "COMMAND", "build"),
]


def stage(step_id: str) -> str:
    return workflow_step_shell(CI, "validate", step_id)


class TestNoMakefileAtAll:
    """With no Makefile, no stage can resolve. Nothing is a valid target."""

    @pytest.mark.parametrize(("step_id", "var", "target"), STAGES)
    def test_skips_on_an_empty_tree(self, run_shell, tmp_path, step_id, var, target):
        result = run_shell(stage(step_id), cwd=tmp_path, env={var: ""})
        assert result.outputs.get("ran") == "false", result

    @pytest.mark.parametrize(("step_id", "var", "target"), STAGES)
    def test_a_directory_of_that_name_is_not_a_target(
        self, run_shell, tmp_path, step_id, var, target
    ):
        """The defect: `mkdir build` made `make -n build` exit 0.

        `build/`, `test/` and `dist/` are ordinary repository layouts. Before
        the fix this recorded ran=true, `make build` printed "Nothing to be
        done", and the required check passed having validated nothing.
        """
        (tmp_path / target).mkdir()
        result = run_shell(stage(step_id), cwd=tmp_path, env={var: ""})
        assert result.outputs.get("ran") == "false", result

    @pytest.mark.parametrize(("step_id", "var", "target"), STAGES)
    def test_a_file_of_that_name_is_not_a_target(
        self, run_shell, tmp_path, step_id, var, target
    ):
        (tmp_path / target).write_text("not a makefile\n", encoding="utf-8")
        result = run_shell(stage(step_id), cwd=tmp_path, env={var: ""})
        assert result.outputs.get("ran") == "false", result


class TestWithAMakefile:
    """A real Makefile must still work, including the awkward shapes."""

    @pytest.mark.parametrize(("step_id", "var", "target"), STAGES)
    def test_runs_a_declared_target(self, run_shell, tmp_path, step_id, var, target):
        (tmp_path / "Makefile").write_text(
            f"{target}:\n\t@echo ran-{target}\n", encoding="utf-8"
        )
        result = run_shell(stage(step_id), cwd=tmp_path, env={var: ""})
        assert result.outputs.get("ran") == "true", result
        assert f"ran-{target}" in result.stdout

    @pytest.mark.parametrize(("step_id", "var", "target"), STAGES)
    def test_skips_when_the_makefile_lacks_that_target(
        self, run_shell, tmp_path, step_id, var, target
    ):
        (tmp_path / "Makefile").write_text("something-else:\n\t@true\n", encoding="utf-8")
        result = run_shell(stage(step_id), cwd=tmp_path, env={var: ""})
        assert result.outputs.get("ran") == "false", result

    @pytest.mark.parametrize(("step_id", "var", "target"), STAGES)
    def test_runs_a_declared_target_even_when_a_directory_shadows_it(
        self, run_shell, tmp_path, step_id, var, target
    ):
        """The inverse trap: a real target must not be skipped because a
        directory of the same name happens to exist beside it."""
        (tmp_path / target).mkdir()
        (tmp_path / "Makefile").write_text(
            f".PHONY: {target}\n{target}:\n\t@echo ran-{target}\n", encoding="utf-8"
        )
        result = run_shell(stage(step_id), cwd=tmp_path, env={var: ""})
        assert result.outputs.get("ran") == "true", result

    @pytest.mark.parametrize(("step_id", "var", "target"), STAGES)
    def test_a_failing_target_fails_the_step(self, run_shell, tmp_path, step_id, var, target):
        (tmp_path / "Makefile").write_text(f"{target}:\n\t@exit 7\n", encoding="utf-8")
        result = run_shell(stage(step_id), cwd=tmp_path, env={var: ""})
        assert result.returncode != 0, result


class TestExplicitCommandWins:
    @pytest.mark.parametrize(("step_id", "var", "target"), STAGES)
    def test_command_takes_precedence_over_a_makefile(
        self, run_shell, tmp_path, step_id, var, target
    ):
        (tmp_path / "Makefile").write_text(f"{target}:\n\t@echo from-make\n", encoding="utf-8")
        result = run_shell(stage(step_id), cwd=tmp_path, env={var: "echo from-command"})
        assert result.outputs.get("ran") == "true", result
        assert "from-command" in result.stdout
        assert "from-make" not in result.stdout

    @pytest.mark.parametrize(("step_id", "var", "target"), STAGES)
    def test_a_failing_command_fails_the_step(self, run_shell, tmp_path, step_id, var, target):
        result = run_shell(stage(step_id), cwd=tmp_path, env={var: "exit 4"})
        assert result.returncode != 0, result


class TestDocumentationStage:
    """`lint-docs` has no input; it resolves from a Makefile or skips."""

    def test_a_directory_named_lint_docs_is_not_a_target(self, run_shell, tmp_path):
        (tmp_path / "lint-docs").mkdir()
        result = run_shell(stage("lintdocs"), cwd=tmp_path)
        assert result.outputs.get("ran") == "false", result

    def test_runs_a_declared_target(self, run_shell, tmp_path):
        (tmp_path / "Makefile").write_text("lint-docs:\n\t@echo ran-docs\n", encoding="utf-8")
        result = run_shell(stage("lintdocs"), cwd=tmp_path)
        assert result.outputs.get("ran") == "true", result


class TestNothingValidatedGuard:
    """The guard that turns four skips into a failure."""

    GUARD = "🚦 Verify Something Was Validated"

    def test_fails_when_every_stage_skipped(self, run_shell):
        result = run_shell(
            workflow_step_shell(CI, "validate", self.GUARD),
            env={"RAN_LINT": "false", "RAN_DOCS": "false", "RAN_TEST": "false", "RAN_BUILD": "false"},
        )
        assert result.returncode != 0
        assert "Nothing was validated" in result.output

    @pytest.mark.parametrize("ran", ["RAN_LINT", "RAN_DOCS", "RAN_TEST", "RAN_BUILD"])
    def test_passes_when_any_single_stage_ran(self, run_shell, ran):
        env = {k: "false" for k in ("RAN_LINT", "RAN_DOCS", "RAN_TEST", "RAN_BUILD")}
        env[ran] = "true"
        assert run_shell(workflow_step_shell(CI, "validate", self.GUARD), env=env).returncode == 0
