# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Tests for the test harness itself.

A suite whose fixtures silently do nothing passes everything, which is the
same failure this repository keeps finding in its own gates: a check that
checked nothing reporting success. These assert that the machinery works
before anything relies on it.
"""

from __future__ import annotations

import pytest
from conftest import ROOT, load_yaml, workflow_step_shell


class TestWorkflowStepShell:
    def test_reads_the_shell_that_actually_ships(self):
        shell = workflow_step_shell(".github/workflows/ci.yml", "validate", "build")
        assert "make -n build" in shell
        assert "ran=false" in shell

    def test_finds_a_step_by_name_when_it_has_no_id(self):
        shell = workflow_step_shell(
            ".github/workflows/ci.yml", "validate", "🚦 Verify Something Was Validated"
        )
        assert "Nothing was validated" in shell

    def test_reads_a_composite_action_step(self):
        shell = workflow_step_shell("actions/config/action.yml", None, "resolve")
        assert "Unknown shared config" in shell

    def test_raises_on_a_step_that_no_longer_exists(self):
        # A renamed step must break its test rather than stop being covered.
        with pytest.raises(AssertionError, match="no step"):
            workflow_step_shell(".github/workflows/ci.yml", "validate", "does-not-exist")


class TestRunShell:
    def test_captures_step_outputs(self, run_shell):
        result = run_shell('echo "ran=true" >> "$GITHUB_OUTPUT"')
        assert result.outputs == {"ran": "true"}
        assert result.returncode == 0

    def test_reports_a_failing_exit_code(self, run_shell):
        assert run_shell("exit 3").returncode == 3

    def test_captures_the_step_summary(self, run_shell):
        assert "hello" in run_shell('echo hello >> "$GITHUB_STEP_SUMMARY"').summary

    def test_runs_in_the_directory_it_is_given(self, run_shell, tmp_path):
        (tmp_path / "marker").mkdir()
        assert "marker" in run_shell("ls", cwd=tmp_path).stdout

    def test_does_not_leak_the_developers_environment(self, run_shell, monkeypatch):
        # A test must not pass because of something exported outside it.
        monkeypatch.setenv("LEAKED_FROM_OUTSIDE", "yes")
        assert run_shell('echo "[${LEAKED_FROM_OUTSIDE:-unset}]"').stdout.strip() == "[unset]"


class TestFakeGh:
    def test_answers_a_routed_call(self, run_shell, fake_gh):
        fake_gh.route("repos/o/r", '{"default_branch":"main"}')
        result = run_shell('gh api "repos/o/r"', env=fake_gh.env())
        assert '"default_branch":"main"' in result.stdout
        assert result.returncode == 0

    def test_records_what_was_asked_for(self, run_shell, fake_gh):
        fake_gh.route("releases", "[]")
        run_shell('gh api "repos/o/r/releases" >/dev/null', env=fake_gh.env())
        assert any("repos/o/r/releases" in call for call in fake_gh.calls)

    def test_an_unrouted_call_fails_loudly(self, run_shell, fake_gh):
        result = run_shell("gh api something-nobody-routed", env=fake_gh.env())
        assert result.returncode != 0
        assert "no route" in result.stderr

    def test_can_simulate_an_api_failure(self, run_shell, fake_gh):
        fake_gh.route("pulls", "", code=1)
        assert run_shell("gh api pulls", env=fake_gh.env()).returncode == 1

    def test_is_not_on_path_unless_a_test_asks_for_it(self, run_shell):
        # Guards against a real gh on the runner answering a test by accident.
        assert "no route" not in run_shell("gh --version || true").stdout


class TestGitRepo:
    def test_provides_a_repository_with_one_commit(self, run_shell, git_repo):
        result = run_shell("git log --oneline | wc -l", cwd=git_repo)
        assert result.stdout.strip() == "1"

    def test_is_clean_to_start_with(self, run_shell, git_repo):
        assert run_shell("git status --porcelain", cwd=git_repo).stdout.strip() == ""


class TestRepositoryShape:
    """Cheap invariants that keep the rest of the suite honest."""

    def test_every_workflow_parses_and_names_its_jobs(self):
        for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
            doc = load_yaml(f".github/workflows/{path.name}")
            assert doc.get("jobs"), f"{path.name} declares no jobs"

    def test_run_script_reaches_a_real_script(self, run_script, fake_gh):
        # check-standards-version exits early and cleanly when no stub pins
        # anything, which makes it the cheapest end-to-end proof available.
        result = run_script(
            "scripts/check-standards-version.py",
            env=fake_gh.env(GH_TOKEN="t", REPO="o/r", WORKFLOW_DIR="nowhere"),
        )
        assert result.returncode == 0
        assert "Nothing to compare" in result.stdout
