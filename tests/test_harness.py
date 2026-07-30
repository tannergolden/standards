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
from conftest import ROOT, load_yaml, workflow_inputs, workflow_on, workflow_step_shell


class TestWorkflowStepShell:
    def test_reads_the_shell_that_actually_ships(self):
        # Asserts on the step's contract, not on how the target probe is
        # spelled: the behaviour of that probe is owned by
        # test_ci_stage_resolution.py, which runs it rather than reading it.
        shell = workflow_step_shell(".github/workflows/ci.yml", "validate", "build")
        assert "ran=true" in shell
        assert "ran=false" in shell
        assert "Build skipped" in shell

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


class TestWorkflowOn:
    """`on:` is the boolean true after YAML 1.1 resolution, not the string."""

    def test_reads_the_trigger_block(self):
        assert "workflow_call" in workflow_on(load_yaml(".github/workflows/ci.yml"))

    def test_reads_declared_inputs(self):
        inputs = workflow_inputs(".github/workflows/ci.yml")
        assert "lint-command" in inputs
        assert inputs["node-version"]["default"] == "22.x"

    def test_every_reusable_workflow_is_reachable_this_way(self):
        for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
            assert workflow_on(load_yaml(f".github/workflows/{path.name}")), (
                f"{path.name}: no trigger block found"
            )


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


class TestFakeGhAppliesJq:
    """Several scripts rely on `gh api --jq` doing the transform."""

    def test_applies_a_jq_filter_to_the_routed_body(self, run_shell, fake_gh):
        fake_gh.route("repos/o/r", '{"default_branch":"main"}')
        result = run_shell("""gh api repos/o/r --jq '.default_branch'""", env=fake_gh.env())
        assert result.stdout.strip() == "main"

    def test_emits_raw_strings_the_way_gh_does(self, run_shell, fake_gh):
        fake_gh.route("list", '[{"n":"a"},{"n":"b"}]')
        result = run_shell("""gh api list --jq '.[].n'""", env=fake_gh.env())
        assert result.stdout.split() == ["a", "b"]

    def test_without_a_filter_the_body_is_untouched(self, run_shell, fake_gh):
        fake_gh.route("raw", '{"a":1}')
        assert '{"a":1}' in run_shell("gh api raw", env=fake_gh.env()).stdout
