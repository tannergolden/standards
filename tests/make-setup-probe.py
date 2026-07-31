# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""`make setup` is optional everywhere, so nowhere may assume it exists.

Nothing in the published contract requires a repository to define a `setup`
target. `ci.yml` calls it "the repository's own answer to get ready to
build" and treats it as a fallback; `actions/setup` skips it with a notice
when it is absent.

`release-publish.yml` ran it bare, gated only on a Makefile existing at all.
A repository with a perfectly ordinary Makefile declaring `build` and `test`
but no `setup` got `make: *** No rule to make target 'setup'. Stop.` and the
release job died before anything was built, packaged, attested or
published.

This is the same probe defect as the build stages, in a step that is
harder to notice because it only fires on a release.
"""

from __future__ import annotations

import pytest
from conftest import workflow_step_shell

SITES = [
    (".github/workflows/release-publish.yml", "release", "📦 Install Dependencies"),
    ("actions/setup/action.yml", None, "📦 Install Dependencies"),
]


@pytest.mark.parametrize(("rel", "job", "step"), SITES)
class TestSetupIsProbedNotAssumed:
    def test_skips_when_the_makefile_has_no_setup_target(self, run_shell, tmp_path, rel, job, step):
        """The defect: this aborted the whole release job."""
        (tmp_path / "Makefile").write_text("build:\n\t@true\ntest:\n\t@true\n", encoding="utf-8")
        result = run_shell(workflow_step_shell(rel, job, step), cwd=tmp_path)
        assert result.returncode == 0, result
        assert "No rule to make target" not in result.output

    def test_says_why_it_skipped(self, run_shell, tmp_path, rel, job, step):
        (tmp_path / "Makefile").write_text("build:\n\t@true\n", encoding="utf-8")
        result = run_shell(workflow_step_shell(rel, job, step), cwd=tmp_path)
        assert "setup" in result.output.lower()

    def test_runs_a_declared_setup_target(self, run_shell, tmp_path, rel, job, step):
        (tmp_path / "Makefile").write_text("setup:\n\t@echo ran-setup\n", encoding="utf-8")
        result = run_shell(workflow_step_shell(rel, job, step), cwd=tmp_path)
        assert result.returncode == 0, result
        assert "ran-setup" in result.stdout

    def test_a_failing_setup_target_still_fails_the_step(
        self, run_shell, tmp_path, rel, job, step
    ):
        """Skipping an absent target must not become swallowing a real error."""
        (tmp_path / "Makefile").write_text("setup:\n\t@exit 9\n", encoding="utf-8")
        result = run_shell(workflow_step_shell(rel, job, step), cwd=tmp_path)
        assert result.returncode != 0, result

    def test_a_directory_named_setup_is_not_a_target(self, run_shell, tmp_path, rel, job, step):
        """`make -n setup` exits 0 for a `setup/` directory, so a step using
        it reports having installed dependencies while running nothing.
        Asserting on the skip notice rather than only on the exit code,
        because a no-op `make setup` also exits 0."""
        (tmp_path / "setup").mkdir()
        (tmp_path / "Makefile").write_text("build:\n\t@true\n", encoding="utf-8")
        result = run_shell(workflow_step_shell(rel, job, step), cwd=tmp_path)
        assert result.returncode == 0, result
        assert "setup" in result.output.lower()
        assert "Nothing to be done" not in result.output, (
            "make was invoked for a target the Makefile does not declare"
        )
