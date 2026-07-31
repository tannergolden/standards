# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""An inventory that claims to be complete must be complete.

`.github/workflows/README.md` promises "Every callable workflow, the stub
that calls it, and what any repository needs to adopt them". Its "Pruning
and release" table omitted `prune-releases.yml` and `prune-runs.yml` - the
two most destructive workflows in the family, one of which deletes PUBLISHED
releases and can take their tags with them.

`data/README.md` defines its folder as everything "written to a target
repository" and then lists four files, omitting `repository-settings.json`,
which rewrites merge strategy, workflow-token permissions and the security
feature set.

`apply-standards.yml`'s own header says "Two jobs, nothing else" while
defining three.

These are counted rather than read, so the next workflow or data file added
cannot quietly go undocumented.
"""

from __future__ import annotations

import re

import pytest
from conftest import ROOT, load_yaml

WF_README = ROOT / ".github/workflows/README.md"
DATA_README = ROOT / "data/README.md"
APPLY = ".github/workflows/apply-standards.yml"

# Local to this repository, not published, so not part of the inventory.
NOT_PUBLISHED = {"release.yml", "self-checks.yml"}


class TestEveryPublishedWorkflowIsListed:
    def test_none_are_missing(self):
        published = {
            p.name for p in (ROOT / ".github/workflows").glob("*.yml")
        } - NOT_PUBLISHED
        text = WF_README.read_text(encoding="utf-8")
        missing = sorted(name for name in published if f"`{name}`" not in text)
        assert not missing, (
            f".github/workflows/README.md promises every callable workflow and omits: {missing}"
        )

    def test_the_destructive_ones_are_marked_as_such(self):
        text = WF_README.read_text(encoding="utf-8")
        row = next(
            (ln for ln in text.splitlines() if "`prune-releases.yml`" in ln and ln.startswith("|")),
            "",
        )
        assert row, "prune-releases.yml has no row in a table"
        assert re.search(r"published|⚠️", row, re.I), (
            "the row for the workflow that deletes PUBLISHED releases does not say so: "
            f"{row}"
        )


class TestEveryDataFileIsListed:
    def test_none_are_missing(self):
        on_disk = {p.name for p in (ROOT / "data").glob("*.json")}
        on_disk |= {f"rulesets/{p.name}" for p in (ROOT / "data/rulesets").glob("*.json")}
        on_disk |= {p.name for p in (ROOT / "data").glob("*.yml")}
        text = DATA_README.read_text(encoding="utf-8")
        missing = sorted(name for name in on_disk if f"`{name}`" not in text)
        assert not missing, f"data/README.md omits files it applies to a repository: {missing}"


class TestJobCountsAreRight:
    @pytest.mark.parametrize("rel", [APPLY])
    def test_the_header_does_not_undercount_its_jobs(self, rel):
        header = (ROOT / rel).read_text(encoding="utf-8").split("\n---\n", 1)[0]
        actual = len(load_yaml(rel)["jobs"])
        words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
        claimed = [
            words[m.lower()]
            for m in re.findall(r"\b(One|Two|Three|Four|Five)\b(?= jobs?\b)", header)
        ]
        for count in claimed:
            assert count == actual, (
                f"{rel}'s header claims {count} job(s) and the file defines {actual}"
            )
