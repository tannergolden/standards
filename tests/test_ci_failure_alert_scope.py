# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The escalator must only escalate runs from the repository it guards.

`ci-failure-alert.yml` listens on `workflow_run` and opens a
`priority: high` issue when a run on a watched branch fails. Its gate
filtered on the head BRANCH NAME alone.

`workflow_run` also fires for runs triggered by pull requests from forks,
in the base repository's context and with the base repository's token. An
external contributor opening a pull request from their fork's `main`, which
is the ordinary case rather than a contrived one, produced a `head_branch`
of `main`. On any repository whose default branch is `main` that matched,
and the escalator opened a real issue upstream pointing at the fork's run.
That is unauthenticated issue creation needing only a failing fork pull
request.

THESE ASSERTIONS ARE STRUCTURAL. A GitHub `if:` expression cannot be
evaluated outside Actions, so the test reads the condition rather than
running it. That is enough to catch the guard being removed or weakened,
which is what it is for.
"""

from __future__ import annotations

import re

from conftest import load_yaml, workflow_inputs

WORKFLOW = ".github/workflows/ci-failure-alert.yml"


def alert_condition() -> str:
    return " ".join(load_yaml(WORKFLOW)["jobs"]["alert"]["if"].split())


class TestTheRunMustComeFromThisRepository:
    def test_the_gate_compares_the_head_repository(self):
        """The defect: any fork's failing run could open an issue here."""
        condition = alert_condition()
        assert re.search(
            r"github\.event\.workflow_run\.head_repository\.full_name\s*==\s*github\.repository",
            condition,
        ), (
            "the alert job does not require the completed run to have originated in "
            f"this repository. Condition is: {condition}"
        )

    def test_the_provenance_check_is_required_not_alternative(self):
        """An `||` would make it decorative."""
        condition = alert_condition()
        head = condition.index("head_repository")
        assert "&&" in condition[head:] or "&&" in condition[:head], (
            "the provenance check must be joined with && so it cannot be bypassed"
        )
        assert "||" not in condition.split("head_repository")[0][-40:], (
            "the provenance check appears to be an alternative rather than a requirement"
        )


class TestTheBranchFilterIsUnchanged:
    """The existing behaviour, pinned so the new clause cannot displace it."""

    def test_still_filters_on_the_head_branch(self):
        assert "github.event.workflow_run.head_branch" in alert_condition()

    def test_still_defaults_to_the_repositorys_own_default_branch(self):
        assert "github.event.repository.default_branch" in alert_condition()

    def test_branches_input_still_defaults_to_empty(self):
        assert workflow_inputs(WORKFLOW)["branches"]["default"] == ""


class TestPermissionsStayMinimal:
    def test_the_job_asks_only_for_issues_write(self):
        assert load_yaml(WORKFLOW)["jobs"]["alert"]["permissions"] == {"issues": "write"}
