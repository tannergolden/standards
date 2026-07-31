# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Three narrow defects, each one an unknown being read as a benign answer.

open-pr.sh          `git status` failing is indistinguishable from a clean
                    tree, so a broken checkout printed "No changes detected"
                    and exited 0. The pull request silently never opened.

check-standards     the advisory compares the HIGHEST pinned major, so a
-version.py         repository half-migrated (one stub still on v1, the rest
                    on v2) is never told about the stale one, by the single
                    mechanism that exists to tell it.

update-doc-indexes  `process()` scans line by line with no notion of a fenced
.py                 code block, so the AUTO-INDEX example inside the styling
                    spec is parsed as a live marker. Harmless only while that
                    example stays empty; add one illustrative row and --write
                    deletes it.
"""

from __future__ import annotations

import pytest
from conftest import ROOT, load_script

version_check = load_script("scripts/check-standards-version.py")
doc_indexes = load_script("scripts/update-doc-indexes.py")


class TestOpenPrDistinguishesFailureFromCleanliness:
    def test_a_broken_repository_is_an_error(self, run_script, fake_gh, tmp_path):
        """The defect: git failing printed "No changes detected" and exited 0."""
        result = run_script(
            "scripts/open-pr.sh",
            cwd=tmp_path,  # not a git repository at all
            env=fake_gh.env(
                GH_TOKEN="t",
                BRANCH_PREFIX="style/auto-format",
                COMMIT_TITLE="style(auto): 🎨 x",
                PR_TITLE="style(auto): 🎨 x",
                PR_BODY="body",
            ),
        )
        assert result.returncode != 0, result
        assert "No changes detected" not in result.output, (
            "a failing `git status` is being reported as a clean tree"
        )

    def test_a_genuinely_clean_tree_still_no_ops(self, run_script, fake_gh, git_repo):
        result = run_script(
            "scripts/open-pr.sh",
            cwd=git_repo,
            env=fake_gh.env(
                GH_TOKEN="t",
                BRANCH_PREFIX="style/auto-format",
                COMMIT_TITLE="style(auto): 🎨 x",
                PR_TITLE="style(auto): 🎨 x",
                PR_BODY="body",
            ),
        )
        assert result.returncode == 0, result
        assert "No changes detected" in result.output


class TestTheVersionNoticeWatchesTheStalestPin:
    @pytest.mark.parametrize(
        ("pinned", "expected"),
        [({"a.yml": 1}, 1), ({"a.yml": 1, "b.yml": 2}, 1), ({"a.yml": 3, "b.yml": 3}, 3)],
    )
    def test_it_compares_the_lowest_major(self, pinned, expected):
        """The defect: `max()` meant one migrated stub silenced the rest."""
        assert version_check.current_major(pinned) == expected


class TestDocIndexesRespectFencedBlocks:
    def test_an_example_marker_in_a_fence_is_not_live(self, tmp_path, monkeypatch):
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "Spec.md").write_text(
            "# Spec\n\n"
            "```markdown\n"
            "<!-- AUTO-INDEX:BEGIN dir=guides style=list -->\n"
            "- [An Example](./An-Example.md)\n"
            "<!-- AUTO-INDEX:END -->\n"
            "```\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)
        assert doc_indexes.process(str(docs / "Spec.md"), write=True) is False, (
            "the example inside a fenced block is treated as a live marker"
        )
        assert "- [An Example](./An-Example.md)" in (docs / "Spec.md").read_text(encoding="utf-8"), (
            "--write deleted the illustrative content out of a documentation example"
        )

    def test_a_real_marker_outside_a_fence_still_works(self, tmp_path, monkeypatch):
        docs = tmp_path / "docs"
        (docs / "guides").mkdir(parents=True)
        (docs / "guides" / "A-Guide.md").write_text("<!--\ntitle: '📘 A GUIDE'\n-->\n", encoding="utf-8")
        (docs / "Hub.md").write_text(
            "# Hub\n\n<!-- AUTO-INDEX:BEGIN dir=guides style=list -->\n<!-- AUTO-INDEX:END -->\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)
        assert doc_indexes.process(str(docs / "Hub.md"), write=True) is True
        assert "A Guide" in (docs / "Hub.md").read_text(encoding="utf-8")

    def test_the_shipped_spec_is_unaffected(self):
        # The styling spec carries exactly this example, and must stay clean.
        assert doc_indexes.process(
            str(ROOT / "docs/technical/interface/Document-Styling-&-Formatting.md"), write=False
        ) is False
