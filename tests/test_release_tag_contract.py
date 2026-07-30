# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""A published version tag is immutable, and four files must agree on it.

`README.md` offers `@v1.4.2` as a supported pin, "Immutable release. For
anyone who wants exactness". `data/README.md` says the tag ruleset makes
published releases immutable. `release.yml` says `vX.Y.Z` is "cut once,
never moved". `data/rulesets/protect-release-tags.json` enforces it with a
`deletion` rule and no bypass actors.

And `release.yml` then deleted those tags on the next release, by passing
`delete-tags: true` into the prune. Whichever way that resolved it was
wrong: with the ruleset applied the delete is refused and the release job
fails; without it, every consumer who took `README.md` at its word gets an
unresolvable pin.

These tests pin the contract in all four places at once, so it cannot drift
apart again silently.
"""

from __future__ import annotations

import json
import re

import pytest
from conftest import ROOT, load_yaml, workflow_inputs, workflow_step_shell

RELEASE = ".github/workflows/release.yml"
PRUNE = ".github/workflows/prune-releases.yml"
RULESET = "data/rulesets/protect-release-tags.json"


class TestTheReleasePipelineKeepsVersionTags:
    def test_the_prune_job_does_not_delete_tags(self):
        """The defect: `delete-tags: true` destroyed the immutable tag."""
        doc = load_yaml(RELEASE)
        prune = doc["jobs"]["prune"]
        assert prune["with"].get("delete-tags") is not True, (
            "release.yml deletes the vX.Y.Z tags that README.md offers as a pin and "
            "protect-release-tags.json forbids deleting"
        )

    def test_the_prune_job_still_prunes_the_release_pages(self):
        # The page is clutter once superseded; the tag is a contract. Only
        # the second half was ever the problem.
        prune = load_yaml(RELEASE)["jobs"]["prune"]
        assert prune["with"]["keep"] == 1
        assert prune["with"]["dry-run"] is False


@pytest.fixture(scope="module")
def ruleset() -> dict:
    return json.loads((ROOT / RULESET).read_text(encoding="utf-8"))


class TestTheRulesetForbidsIt:
    def test_version_tags_cannot_be_deleted(self, ruleset):
        assert ruleset["enforcement"] == "active"
        assert "refs/tags/v*.*.*" in ruleset["conditions"]["ref_name"]["include"]
        assert any(rule["type"] == "deletion" for rule in ruleset["rules"])

    def test_nothing_bypasses_it(self, ruleset):
        # If a bypass actor is ever added, the immutability claim in
        # README.md and data/README.md stops being true and must change too.
        assert not ruleset.get("bypass_actors")


class TestTheGuardInThePruneStillProtectsTheMajor:
    """Whatever a caller asks for, `v1` itself is never deletable."""

    def test_a_bare_major_is_kept(self, run_shell, fake_gh, tmp_path):
        releases = [
            {"tag_name": "v2", "draft": False, "prerelease": False, "published_at": "2024-01-01T00:00:00Z"},
            {"tag_name": "v1.9.9", "draft": False, "prerelease": False, "published_at": "2024-02-01T00:00:00Z"},
        ]
        fake_gh.route("releases", "\n".join(json.dumps(r) for r in releases) + "\n")
        fake_gh.route("release delete", "")
        result = run_shell(
            workflow_step_shell(PRUNE, "prune", "🧹 Prune"),
            cwd=tmp_path,
            env=fake_gh.env(
                GH_TOKEN="t",
                REPO="o/r",
                KEEP="1",
                DRY_RUN="false",
                INCLUDE_PRERELEASES="false",
                DELETE_TAGS="true",
            ),
        )
        assert result.returncode == 0, result
        deletes = [c for c in fake_gh.calls if "release delete" in c]
        assert deletes, "nothing was deleted; the fixture no longer exercises the guard"
        assert all("--cleanup-tag" not in c for c in deletes if " v2 " in f" {c} "), (
            "a bare major tag must never be deleted, whatever delete-tags says"
        )

    def test_delete_tags_still_defaults_off(self):
        assert workflow_inputs(PRUNE)["delete-tags"]["default"] is False

    def test_dry_run_still_defaults_on(self):
        assert workflow_inputs(PRUNE)["dry-run"]["default"] is True


class TestTheDocumentationAgrees:
    """Four files make the same promise; none may quietly stop making it."""

    def test_readme_still_offers_the_exact_pin(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        assert re.search(r"@v1\.\d+\.\d+.*[Ii]mmutable", text), (
            "README.md no longer advertises an exact version pin; if that was "
            "intentional the tag ruleset and release.yml should change with it"
        )

    def test_data_readme_still_calls_published_releases_immutable(self):
        text = (ROOT / "data/README.md").read_text(encoding="utf-8")
        assert "immutable" in text.lower()

    def test_release_workflow_still_documents_the_two_contracts(self):
        text = (ROOT / RELEASE).read_text(encoding="utf-8")
        assert "immutable" in text.lower()
        assert "moving" in text.lower()
