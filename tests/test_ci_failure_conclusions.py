# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The escalator must react to every conclusion that means "broken".

`ci-failure-alert.sh` branched on exactly two values: `failure` escalates,
`success` resolves, everything else fell through to "Nothing to do".

`workflow_run.conclusion` also takes `timed_out`, `startup_failure`,
`cancelled`, `action_required`, `neutral` and `skipped`, and
`ci-failure-alert.yml` passes the field straight through. So the two most
alarming outcomes were the two that never alerted:

  timed_out        a workflow on the default branch hung and the runner
                   killed it. No issue, and the caller's step goes green.
  startup_failure  broken YAML pushed to the default branch, so the workflow
                   could not start at all. Same silence.

`cancelled` and `skipped` stay inert deliberately: someone chose those, and
an escalation issue for a deliberate cancellation is noise.
"""

from __future__ import annotations

import json

import pytest

SCRIPT = "scripts/ci-failure-alert.sh"

ESCALATES = ["failure", "timed_out", "startup_failure"]
IGNORES = ["cancelled", "skipped", "neutral", "action_required"]


TITLE = "🚨 CI failing on main: Checks"


def run_alert(run_script, fake_gh, tmp_path, conclusion, existing=None):
    """`existing` is an open issue number, or None for a clean slate.

    The script asks `gh issue list --json number,title --jq ...`, so the
    route returns the real API shape and the fake applies the filter.
    """
    listing = [{"number": existing, "title": TITLE}] if existing else []
    fake_gh.route("issue list", json.dumps(listing))
    fake_gh.route("issue create", "https://github.com/o/r/issues/9")
    fake_gh.route("issue comment", "")
    fake_gh.route("issue close", "")
    return run_script(
        SCRIPT,
        cwd=tmp_path,
        env=fake_gh.env(
            GH_TOKEN="t",
            GH_REPO="o/r",
            WORKFLOW_NAME="Checks",
            CONCLUSION=conclusion,
            BRANCH="main",
            RUN_URL="https://example.invalid/run",
            HEAD_SHA="abc123",
            LABEL="priority: high",
        ),
    )


class TestABrokenRunIsEscalated:
    @pytest.mark.parametrize("conclusion", ESCALATES)
    def test_an_issue_is_opened(self, run_script, fake_gh, tmp_path, conclusion):
        """The defect: only `failure` escalated."""
        result = run_alert(run_script, fake_gh, tmp_path, conclusion)
        assert result.returncode == 0, result
        assert any("issue create" in c for c in fake_gh.calls), (
            f"conclusion={conclusion!r} opened no issue: {result.output}"
        )

    @pytest.mark.parametrize("conclusion", ESCALATES)
    def test_an_existing_issue_is_commented_on_instead(
        self, run_script, fake_gh, tmp_path, conclusion
    ):
        result = run_alert(run_script, fake_gh, tmp_path, conclusion, existing=7)
        assert result.returncode == 0, result
        assert any("issue comment" in c for c in fake_gh.calls)
        assert not any("issue create" in c for c in fake_gh.calls), "opened a duplicate"


class TestRecoveryStillCloses:
    def test_success_closes_an_open_issue(self, run_script, fake_gh, tmp_path):
        result = run_alert(run_script, fake_gh, tmp_path, "success", existing=7)
        assert result.returncode == 0, result
        assert any("issue close" in c for c in fake_gh.calls)

    def test_success_with_nothing_open_does_nothing(self, run_script, fake_gh, tmp_path):
        result = run_alert(run_script, fake_gh, tmp_path, "success")
        assert result.returncode == 0
        assert not any("issue close" in c for c in fake_gh.calls)


class TestDeliberateOutcomesStayQuiet:
    @pytest.mark.parametrize("conclusion", IGNORES)
    def test_no_issue_is_opened(self, run_script, fake_gh, tmp_path, conclusion):
        """Someone chose these. An issue for a deliberate cancellation is
        noise, and noise is what makes an escalation channel ignorable."""
        result = run_alert(run_script, fake_gh, tmp_path, conclusion)
        assert result.returncode == 0, result
        assert not any("issue create" in c for c in fake_gh.calls), (
            f"conclusion={conclusion!r} opened an issue it should not have"
        )

    @pytest.mark.parametrize("conclusion", IGNORES)
    def test_an_open_issue_is_not_closed_either(self, run_script, fake_gh, tmp_path, conclusion):
        run_alert(run_script, fake_gh, tmp_path, conclusion, existing=7)
        assert not any("issue close" in c for c in fake_gh.calls)
