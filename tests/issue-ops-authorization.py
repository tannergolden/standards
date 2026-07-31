# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Slash commands need a relationship to the repository, not just a slash.

The gate checked that the comment was on an issue and started with `/`, and
nothing else. On any public consuming repository, a stranger could comment
`/label pinned` and the job applied it with `issues: write`.

`pinned` and `automated` are both in the stale sweep's exemption list in
`governance.yml`, so an outsider could make any issue permanently
un-ageable. `governance.yml` already gates its own greeting on
`author_association`, so the shape was established here and simply not
applied to the one job that acts on a stranger's instruction.

STRUCTURAL, like the escalator's provenance test: a GitHub `if:` cannot be
evaluated outside Actions. It catches the gate being removed or weakened,
which is what it is for.
"""

from __future__ import annotations

import re

from conftest import load_yaml

WORKFLOW = ".github/workflows/issue-ops.yml"
TRUSTED = ("OWNER", "MEMBER", "COLLABORATOR")


def condition() -> str:
    return " ".join(load_yaml(WORKFLOW)["jobs"]["issue-ops"]["if"].split())


class TestOnlyTrustedCommentersAreObeyed:
    def test_the_gate_reads_the_author_association(self):
        assert "author_association" in condition(), (
            "any commenter can drive this job; it holds issues: write. "
            f"Condition is: {condition()}"
        )

    def test_the_trusted_set_is_the_established_one(self):
        text = condition()
        for association in TRUSTED:
            assert association in text, f"{association} is not accepted"

    def test_a_first_time_commenter_is_not_trusted(self):
        # The associations governance.yml treats as newcomers must not
        # appear here, where the job acts on what they said.
        for newcomer in ("NONE", "FIRST_TIME_CONTRIBUTOR", "FIRST_TIMER"):
            assert not re.search(rf"\b{newcomer}\b", condition()), (
                f"{newcomer} is accepted as a trusted commenter"
            )

    def test_the_check_is_required_not_alternative(self):
        text = condition()
        assert "&&" in text
        assert "||" not in text.split("author_association")[0][-30:], (
            "the association check appears to be an alternative rather than a requirement"
        )


class TestTheExistingFiltersRemain:
    def test_still_skips_pull_request_comments(self):
        assert "github.event.issue.pull_request" in condition()

    def test_still_requires_a_leading_slash(self):
        assert "startsWith(github.event.comment.body, '/')" in condition()


class TestPermissionsStayMinimal:
    def test_the_job_asks_only_for_issues_write(self):
        assert load_yaml(WORKFLOW)["jobs"]["issue-ops"]["permissions"] == {"issues": "write"}
