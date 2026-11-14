# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The escalator must work in a repository with issues turned off.

`ci-failure-alert.sh` reports a broken run by opening an issue, and every
call it makes to do so is a `gh issue` call. A repository can turn issues
off, as a private vault does, and there each of those calls fails. So when
a watched workflow failed, the escalator failed beside it: a second red
run, an error that blamed the token's `issues: write`, and the failure
tracked nowhere.

Where issues are off, a broken run now goes in the escalator's run summary
with a warning, a recovery has nothing to close, and the escalator passes.
Only an explicit `has_issues: false` takes that path. A lookup that fails
says nothing about issues, so the escalator goes on to the issue path,
which still fails loudly when it cannot open an issue.
"""

from __future__ import annotations

import json

import pytest

SCRIPT = ".github/scripts/ci-failure-alert.sh"

ESCALATES = ["failure", "timed_out", "startup_failure"]
IGNORES = ["cancelled", "skipped", "neutral", "action_required"]

RUN_URL = "https://example.invalid/run"


def run_alert(run_script, fake_gh, tmp_path, conclusion, *, has_issues, create_code=0):
    """`has_issues` is what the repository lookup answers: True, False, or
    None for a lookup that fails.

    Where issues are off, every `gh issue` call fails, as GitHub refuses it
    ("the 'o/r' repository has disabled issues"), so a script that still
    makes one fails here exactly as it did in a real run.
    """
    if has_issues is None:
        fake_gh.route("api repos/", "", code=1)
    else:
        fake_gh.route("api repos/", json.dumps({"full_name": "o/r", "has_issues": has_issues}))
    if has_issues is False:
        fake_gh.route("issue ", "", code=1)
    else:
        fake_gh.route("issue list", json.dumps([]))
        fake_gh.route("issue create", "https://github.com/o/r/issues/9", code=create_code)
        fake_gh.route("issue comment", "")
        fake_gh.route("issue close", "")
    fake_gh.route("label create", "")
    return run_script(
        SCRIPT,
        cwd=tmp_path,
        env=fake_gh.env(
            GH_TOKEN="t",
            GH_REPO="o/r",
            WORKFLOW_NAME="Checks",
            CONCLUSION=conclusion,
            BRANCH="main",
            RUN_URL=RUN_URL,
            HEAD_SHA="abc123",
        ),
    )


def issue_calls(fake_gh) -> list[str]:
    """Every call that needs issues: the ones that fail where they are off."""
    return [c for c in fake_gh.calls if c.startswith(("issue ", "label "))]


class TestABrokenRunWhereIssuesAreOff:
    @pytest.mark.parametrize("conclusion", ESCALATES)
    def test_the_escalator_passes(self, run_script, fake_gh, tmp_path, conclusion):
        """The defect: it failed beside the workflow it reports."""
        result = run_alert(run_script, fake_gh, tmp_path, conclusion, has_issues=False)
        assert result.returncode == 0, result

    @pytest.mark.parametrize("conclusion", ESCALATES)
    def test_it_makes_no_issue_call(self, run_script, fake_gh, tmp_path, conclusion):
        run_alert(run_script, fake_gh, tmp_path, conclusion, has_issues=False)
        assert issue_calls(fake_gh) == []

    @pytest.mark.parametrize("conclusion", ESCALATES)
    def test_the_summary_says_what_failed(self, run_script, fake_gh, tmp_path, conclusion):
        """With no issue to hold it, the run summary is the record."""
        result = run_alert(run_script, fake_gh, tmp_path, conclusion, has_issues=False)
        for fact in ("Checks", f"`{conclusion}`", "`main`", "abc123", RUN_URL):
            assert fact in result.summary, f"{fact!r} missing from the summary:\n{result.summary}"
        assert "Issues are turned off" in result.summary

    @pytest.mark.parametrize("conclusion", ESCALATES)
    def test_it_warns(self, run_script, fake_gh, tmp_path, conclusion):
        """A warning shows on the run, where a summary alone would not."""
        result = run_alert(run_script, fake_gh, tmp_path, conclusion, has_issues=False)
        assert "::warning title=CI failure alert::" in result.output
        assert "::error" not in result.output


class TestTheRestWhereIssuesAreOff:
    def test_a_recovery_does_nothing(self, run_script, fake_gh, tmp_path):
        result = run_alert(run_script, fake_gh, tmp_path, "success", has_issues=False)
        assert result.returncode == 0, result
        assert issue_calls(fake_gh) == []
        assert result.summary == ""

    @pytest.mark.parametrize("conclusion", IGNORES)
    def test_a_deliberate_outcome_stays_quiet(self, run_script, fake_gh, tmp_path, conclusion):
        result = run_alert(run_script, fake_gh, tmp_path, conclusion, has_issues=False)
        assert result.returncode == 0, result
        assert issue_calls(fake_gh) == []
        assert "::warning" not in result.output
        assert result.summary == ""


class TestWhereIssuesAreOnNothingChanges:
    @pytest.mark.parametrize("conclusion", ESCALATES)
    def test_an_issue_is_still_opened(self, run_script, fake_gh, tmp_path, conclusion):
        result = run_alert(run_script, fake_gh, tmp_path, conclusion, has_issues=True)
        assert result.returncode == 0, result
        assert any(c.startswith("issue create") for c in fake_gh.calls)
        assert result.summary == ""

    def test_an_issue_it_cannot_open_still_fails_the_run(self, run_script, fake_gh, tmp_path):
        """Issues on and the issue refused is a real fault, so it stays loud."""
        result = run_alert(run_script, fake_gh, tmp_path, "failure", has_issues=True, create_code=1)
        assert result.returncode == 1, result
        assert "::error title=CI failure alert::" in result.output

    @pytest.mark.parametrize("conclusion", ESCALATES)
    def test_a_lookup_that_fails_goes_on_to_the_issue(
        self, run_script, fake_gh, tmp_path, conclusion
    ):
        """A failed lookup says nothing about issues, so it is no reason to
        stop tracking a failure: the issue is opened as before."""
        result = run_alert(run_script, fake_gh, tmp_path, conclusion, has_issues=None)
        assert result.returncode == 0, result
        assert any(c.startswith("issue create") for c in fake_gh.calls)
