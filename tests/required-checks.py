# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Every required check comes from GitHub Actions, and nothing behind one can forge it.

A required status check is matched by its name. Without an `integration_id`,
anything that can post a commit status under that name satisfies it: a
personal access token, another app, or a workflow job holding
`statuses: write`. The pull request title job held that permission without
using it, around a third-party action.

So every required check in the branch rulesets is tied to the GitHub Actions
app, id 15368, read off a real check run, and no shared workflow asks for
`statuses: write`. Dependency review joined the required checks: it failed a
pull request that added a vulnerable dependency, and the pull request could
merge anyway, because nothing required it.
"""

from __future__ import annotations

import json

import pytest
from conftest import ROOT, load_yaml

RULESETS = [
    "data/rulesets/protect-integration-branches.json",
    "data/rulesets/protect-promotion-branches.json",
]
ACTIONS_APP = 15368
SOURCES = {
    "ci": ".github/workflows/ci.yml",
    "secrets": ".github/workflows/gitleaks.yml",
    "pr": ".github/workflows/semantic-pr.yml",
}
DEPENDENCY_REVIEW = "ci / 📦 Dependency Review"


def required(rel: str) -> list[dict]:
    doc = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    rule = next(r for r in doc["rules"] if r["type"] == "required_status_checks")
    return rule["parameters"]["required_status_checks"]


def contexts(rel: str) -> list[str]:
    return [check["context"] for check in required(rel)]


class TestEveryRequiredCheckComesFromActions:
    @pytest.mark.parametrize("rel", RULESETS)
    def test_each_is_tied_to_the_actions_app(self, rel):
        loose = [c["context"] for c in required(rel) if c.get("integration_id") != ACTIONS_APP]
        assert not loose, f"{rel}: anything posting a status under these names satisfies them: {loose}"

    def test_both_branch_rulesets_require_the_same_checks(self):
        integration, promotion = (contexts(rel) for rel in RULESETS)
        assert integration == promotion

    @pytest.mark.parametrize("rel", RULESETS)
    def test_each_names_a_job_that_exists(self, rel):
        """A required check nothing reports leaves every pull request pending."""
        for context in contexts(rel):
            job_id, _, name = context.partition(" / ")
            jobs = load_yaml(SOURCES[job_id])["jobs"]
            assert name in {job.get("name") for job in jobs.values()}, (
                f"{rel} requires {context!r}, and {SOURCES[job_id]} has no job by that name"
            )


class TestDependencyReviewIsRequired:
    @pytest.mark.parametrize("rel", RULESETS)
    def test_it_is_required(self, rel):
        assert DEPENDENCY_REVIEW in contexts(rel)

    def test_it_skips_where_it_cannot_run(self):
        """A skipped job reports as passing; a failing one would block every private repository."""
        condition = load_yaml(SOURCES["ci"])["jobs"]["dependency-review"]["if"]
        assert "github.event_name == 'pull_request'" in condition
        assert "github.event.repository.private == false" in condition


class TestNothingBehindThemCanForgeAStatus:
    @pytest.mark.parametrize(
        "rel", sorted(f".github/workflows/{p.name}" for p in (ROOT / ".github/workflows").glob("*.yml"))
    )
    def test_no_shared_workflow_asks_for_statuses_write(self, rel):
        doc = load_yaml(rel)
        scopes = [doc.get("permissions")] + [job.get("permissions") for job in doc["jobs"].values()]
        assert not any(isinstance(s, dict) and s.get("statuses") == "write" for s in scopes), (
            f"{rel} can post a commit status, under a required check's name as easily as any other"
        )

    def test_the_title_stub_does_not_grant_it_either(self):
        header = (ROOT / SOURCES["pr"]).read_text(encoding="utf-8").split("\n# ---\n", 1)
        assert len(header) == 2, "the header no longer ends at '# ---'"
        assert "statuses: write" not in header[0]
