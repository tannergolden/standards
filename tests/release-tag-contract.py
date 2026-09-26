# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""A repository consumed by tag carries two tags, and four files must agree.

After a release, `release.yml` prunes every release it superseded, page and
tag, so what remains is the bare major every stub pins and the version it
points at. `README.md` offers a version pin as a pin for the moment and a
commit SHA as the one for exactness. `data/README.md` says a version tag is
never moved while it exists and is pruned when superseded.
`data/rulesets/protect-release-tags.json` enforces exactly that: `update`
and `non_fast_forward` rules and no `deletion` rule, so the prune is never
refused while a version can still never be re-pointed.

This once read the other way. `release.yml` kept every version tag as an
immutable pin, the ruleset forbade deleting one, and the README advertised
`@v1.4.2` as exact. Whichever half of that a repository honoured, the other
half was a lie, which is why the contract is pinned here in all four places
at once, so it cannot drift apart again silently.
"""

from __future__ import annotations

import json
import re

import pytest
from conftest import ROOT, load_yaml, workflow_inputs, workflow_step_shell

RELEASE = ".github/workflows/release.yml"
PRUNE = ".github/workflows/prune-releases.yml"
RULESET = "data/rulesets/protect-release-tags.json"


class TestTheReleasePipelinePrunesVersionTags:
    def test_the_prune_job_deletes_superseded_tags(self):
        prune = load_yaml(RELEASE)["jobs"]["prune"]
        assert prune["with"].get("delete-tags") is True, (
            "release.yml must prune the tags of the releases it supersedes; "
            "README.md and data/README.md promise a repository carries only the "
            "major and the version it points at"
        )

    def test_the_prune_job_keeps_exactly_the_latest_release(self):
        prune = load_yaml(RELEASE)["jobs"]["prune"]
        assert prune["with"]["keep"] == 1
        assert prune["with"]["dry-run"] is False


@pytest.fixture(scope="module")
def ruleset() -> dict:
    return json.loads((ROOT / RULESET).read_text(encoding="utf-8"))


class TestTheRulesetLetsThePruneRunAndNothingMove:
    def test_version_tags_can_be_deleted(self, ruleset):
        # A deletion rule would refuse the prune outright, and the prune job
        # runs under `set -euo pipefail`, so every release would end red.
        assert ruleset["enforcement"] == "active"
        assert "refs/tags/v*.*.*" in ruleset["conditions"]["ref_name"]["include"]
        assert not any(rule["type"] == "deletion" for rule in ruleset["rules"])

    def test_version_tags_still_cannot_be_moved(self, ruleset):
        types = {rule["type"] for rule in ruleset["rules"]}
        assert {"update", "non_fast_forward"} <= types

    def test_nothing_bypasses_it(self, ruleset):
        assert not ruleset.get("bypass_actors")


def _prune(run_shell, fake_gh, tmp_path, **env):
    defaults = dict(GH_TOKEN="t", REPO="o/r", KEEP="1", DRY_RUN="false",
                    INCLUDE_PRERELEASES="false", DELETE_TAGS="true")
    defaults.update(env)
    return run_shell(
        workflow_step_shell(PRUNE, "prune", "🧹 Prune"),
        cwd=tmp_path,
        env=fake_gh.env(**defaults),
    )


def _release(tag: str, published: str) -> dict:
    return {"tag_name": tag, "draft": False, "prerelease": False, "published_at": published}


def _refs(*tags: str) -> str:
    return json.dumps([{"ref": f"refs/tags/{tag}"} for tag in tags])


class TestThePruneSweepsEveryTagNoKeptReleaseStandsOn:
    """With delete-tags on, only the major and the kept releases' tags remain."""

    def test_orphans_go_and_the_kept_release_and_the_major_stay(self, run_shell, fake_gh, tmp_path):
        fake_gh.route("matching-refs", _refs(
            "v1", "v1.7.0", "v1.8.0", "v1.8.1", "v1.8.2", "v1.9.0",
            "v2.0.0-rc.1", "v0.1.0-development.2601072132.g7b3f1a",
        ))
        fake_gh.route("releases", json.dumps([
            _release("v1.9.0", "2026-09-26T00:00:00Z"),
            _release("v1.8.2", "2026-09-20T00:00:00Z"),
        ]))
        fake_gh.route("release delete", "")
        fake_gh.route("git/refs/tags", "")
        result = _prune(run_shell, fake_gh, tmp_path)
        assert result.returncode == 0, result

        pages = [c for c in fake_gh.calls if "release delete" in c]
        assert len(pages) == 1 and " v1.8.2 " in f" {pages[0]} " and "--cleanup-tag" in pages[0], pages
        swept = sorted(c.rsplit("/", 1)[1] for c in fake_gh.calls if "-X DELETE" in c)
        assert swept == ["v1.7.0", "v1.8.0", "v1.8.1"], (
            "the sweep takes every plain vX.Y.Z tag with no kept release, and only those: "
            "not the major, not the kept release, not a prerelease, not a stamped tag"
        )
        assert "Deleted 1 release(s) and 3 tag(s)" in result.stdout

    def test_a_dry_run_plans_the_sweep_and_deletes_nothing(self, run_shell, fake_gh, tmp_path):
        fake_gh.route("matching-refs", _refs("v1", "v1.8.0", "v1.9.0"))
        fake_gh.route("releases", json.dumps([_release("v1.9.0", "2026-09-26T00:00:00Z")]))
        result = _prune(run_shell, fake_gh, tmp_path, DRY_RUN="true")
        assert result.returncode == 0, result
        assert "DELETE  v1.8.0  (tag with no release page)" in result.stdout
        assert not [c for c in fake_gh.calls if "-X DELETE" in c or "release delete" in c]

    def test_orphans_are_swept_even_when_no_page_is_superseded(self, run_shell, fake_gh, tmp_path):
        fake_gh.route("matching-refs", _refs("v1", "v1.8.0", "v1.9.0"))
        fake_gh.route("releases", json.dumps([_release("v1.9.0", "2026-09-26T00:00:00Z")]))
        fake_gh.route("git/refs/tags", "")
        result = _prune(run_shell, fake_gh, tmp_path)
        assert result.returncode == 0, result
        assert [c for c in fake_gh.calls if "-X DELETE" in c and c.endswith("v1.8.0")]

    def test_with_delete_tags_off_the_tags_are_never_read(self, run_shell, fake_gh, tmp_path):
        fake_gh.route("releases", json.dumps([
            _release("v1.9.0", "2026-09-26T00:00:00Z"),
            _release("v1.8.2", "2026-09-20T00:00:00Z"),
        ]))
        fake_gh.route("release delete", "")
        result = _prune(run_shell, fake_gh, tmp_path, DELETE_TAGS="false")
        assert result.returncode == 0, result
        assert not [c for c in fake_gh.calls if "matching-refs" in c or "-X DELETE" in c]
        assert all("--cleanup-tag" not in c for c in fake_gh.calls)

    def test_an_unreadable_tag_list_fails_the_run(self, run_shell, fake_gh, tmp_path):
        # An empty sweep must mean nothing to sweep, never an unasked question.
        fake_gh.route("matching-refs", "", code=1)
        fake_gh.route("releases", json.dumps([_release("v1.9.0", "2026-09-26T00:00:00Z")]))
        result = _prune(run_shell, fake_gh, tmp_path)
        assert result.returncode != 0, result


class TestTheGuardInThePruneStillProtectsTheMajor:
    """Whatever a caller asks for, `v1` itself is never deletable."""

    def test_a_bare_major_is_kept(self, run_shell, fake_gh, tmp_path):
        fake_gh.route("matching-refs", _refs("v2", "v1.9.9"))
        fake_gh.route("releases", json.dumps([
            _release("v2", "2024-01-01T00:00:00Z"),
            _release("v1.9.9", "2024-02-01T00:00:00Z"),
        ]))
        fake_gh.route("release delete", "")
        result = _prune(run_shell, fake_gh, tmp_path)
        assert result.returncode == 0, result
        deletes = [c for c in fake_gh.calls if "release delete" in c]
        assert deletes, "nothing was deleted; the fixture no longer exercises the guard"
        assert all("--cleanup-tag" not in c for c in deletes if " v2 " in f" {c} "), (
            "a bare major tag must never be deleted, whatever delete-tags says"
        )
        assert not [c for c in fake_gh.calls if "-X DELETE" in c], "the sweep never matches a bare major"

    def test_delete_tags_still_defaults_off(self):
        assert workflow_inputs(PRUNE)["delete-tags"]["default"] is False

    def test_dry_run_still_defaults_on(self):
        assert workflow_inputs(PRUNE)["dry-run"]["default"] is True


class TestTheDocumentationAgrees:
    """Four files make the same promise; none may quietly stop making it."""

    def test_readme_offers_the_commit_as_the_exact_pin_and_the_version_as_a_pruned_one(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        assert re.search(r"@<commit>.*[Ii]mmutable", text), "README.md must offer a commit SHA as the exact pin"
        assert re.search(r"@v1\.\d+\.\d+.*[Pp]runed", text), "README.md must say a version pin is pruned at the next release"
        assert not re.search(r"@v1\.\d+\.\d+.*[Ii]mmutable", text), "README.md must not call a version pin immutable"

    def test_data_readme_says_version_tags_are_pruned_and_never_moved(self):
        text = (ROOT / "data/README.md").read_text(encoding="utf-8")
        assert "pruned" in text.lower() and "never moved" in text.lower()
        assert "making published releases immutable" not in text

    def test_release_workflow_documents_the_two_tags(self):
        text = (ROOT / RELEASE).read_text(encoding="utf-8")
        assert "THE TAG GOES WITH THE PAGE" in text
        assert "moving" in text.lower()
        assert "Published immutable tag" not in text
