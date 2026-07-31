# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""An accepted security finding is only accepted while its reason is true.

`config/zizmor.yml` suppresses the `dangerous-triggers` audit for the three
workflows a consumer runs under `pull_request_target`, and its own rule says
"Do not add an entry without a comment explaining why the risk does not
apply."

The comment was wrong in both directions. It said the single checkout among
the three was in semantic-pr's DCO job; semantic-pr has no checkout at all,
and the one checkout in the family is in governance.yml's `triage` job. So
the suppression silencing that audit rested on a statement that was false
about the very file holding the privileged checkout, which was safe by
accident of `actions/checkout`'s default ref rather than by the reasoning
recorded beside it.

These tests hold the topology the comment now describes, so the note and the
code cannot drift apart again.
"""

from __future__ import annotations

import pytest
import yaml
from conftest import ROOT, load_yaml

CONFIG = ROOT / "config/zizmor.yml"
SUPPRESSED = ["governance.yml", "semantic-pr.yml", "ci-failure-alert.yml"]


def checkouts(rel: str) -> list[tuple[str, dict]]:
    return [
        (job_id, step)
        for job_id, job in load_yaml(rel)["jobs"].items()
        for step in job.get("steps", [])
        if "actions/checkout" in str(step.get("uses", ""))
    ]


class TestTheSuppressionCoversWhatItSays:
    def test_all_three_are_still_listed(self):
        rules = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["rules"]
        assert sorted(rules["dangerous-triggers"]["ignore"]) == sorted(SUPPRESSED)


class TestTheTopologyMatchesTheComment:
    def test_semantic_pr_checks_nothing_out(self):
        assert checkouts(".github/workflows/semantic-pr.yml") == []

    def test_ci_failure_alert_checks_nothing_out(self):
        assert checkouts(".github/workflows/ci-failure-alert.yml") == []

    def test_governance_holds_the_only_checkout(self):
        found = checkouts(".github/workflows/governance.yml")
        assert [job for job, _ in found] == ["triage"], (
            f"the accepted-risk note describes one checkout, in triage; found: {found}"
        )

    @pytest.mark.parametrize("rel", [f".github/workflows/{n}" for n in SUPPRESSED])
    def test_no_checkout_takes_the_pull_request_head(self, rel):
        """The whole basis of the suppression."""
        for job_id, step in checkouts(rel):
            with_ = step.get("with") or {}
            assert "ref" not in with_, (
                f"{rel}:{job_id} pins a ref under pull_request_target; if that is the "
                "PR head this suppression is no longer safe"
            )
            assert with_.get("persist-credentials") is False, (
                f"{rel}:{job_id} checks out without disabling credential persistence"
            )


class TestTheCommentNamesTheRightFile:
    def test_it_no_longer_credits_semantic_pr_with_a_checkout(self):
        text = CONFIG.read_text(encoding="utf-8")
        head = text.split("cache-poisoning", 1)[0]
        assert "semantic-pr's DCO job" not in head, (
            "the accepted-risk note still attributes the family's only checkout to a "
            "workflow that has none"
        )

    def test_it_names_governance_triage(self):
        head = CONFIG.read_text(encoding="utf-8").split("cache-poisoning", 1)[0]
        assert "governance.yml" in head and "triage" in head
