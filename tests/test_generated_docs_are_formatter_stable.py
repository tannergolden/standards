# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""A generator and the formatter must not fight over the same file.

`update-label-docs.py` writes a Markdown table between markers and then
compares the whole document byte for byte. Prettier pads table cells to a
common width. So running this repository's own published Prettier config
over `docs/references/Repository-Labels.md` made `--check` report the
document out of date; regenerating it removed the padding; running Prettier
again put it back. Neither tool is wrong and neither converges.

`update-doc-indexes.py` already solved this, and its docstring says so:
"Table rows are compared whitespace-insensitively so Prettier's cell padding
never false-flags." That is the pattern this repository chose, so it is the
one applied here rather than a second answer to the same question.

The distinction that has to survive: padding is not content. A row whose
CELLS changed is still stale.
"""

from __future__ import annotations

import re
import shutil
import subprocess

import pytest
from conftest import ROOT

DOC = ROOT / "docs/references/Repository-Labels.md"
SCRIPT = ROOT / "scripts/update-label-docs.py"

requires_npx = pytest.mark.skipif(shutil.which("npx") is None, reason="npx not installed")


def check() -> int:
    return subprocess.run(
        ["python3", str(SCRIPT), "--check"], cwd=str(ROOT), capture_output=True, text=True
    ).returncode


class TestPaddingIsNotDrift:
    def test_the_committed_document_passes(self):
        assert check() == 0

    def test_extra_cell_padding_is_tolerated(self, tmp_path, monkeypatch):
        """The defect: Prettier's padding read as an out-of-date document."""
        original = DOC.read_text(encoding="utf-8")
        padded = re.sub(r"^\| `", "|  `", original, flags=re.M)
        assert padded != original, "the fixture no longer changes anything"
        DOC.write_text(padded, encoding="utf-8")
        try:
            assert check() == 0, "cell padding is being reported as drift"
        finally:
            DOC.write_text(original, encoding="utf-8")

    def test_a_changed_cell_is_still_drift(self, tmp_path):
        """Whitespace-insensitive must not become content-insensitive."""
        original = DOC.read_text(encoding="utf-8")
        DOC.write_text(original.replace("`bug`", "`insect`", 1), encoding="utf-8")
        try:
            assert check() != 0, "a changed label name is no longer detected"
        finally:
            DOC.write_text(original, encoding="utf-8")

    def test_a_removed_row_is_still_drift(self):
        original = DOC.read_text(encoding="utf-8")
        lines = original.split("\n")
        row = next(i for i, ln in enumerate(lines) if ln.startswith("| `bug`"))
        DOC.write_text("\n".join(lines[:row] + lines[row + 1 :]), encoding="utf-8")
        try:
            assert check() != 0, "a deleted row is no longer detected"
        finally:
            DOC.write_text(original, encoding="utf-8")


@requires_npx
class TestTheTwoToolsAgree:
    def test_the_document_is_prettier_clean_and_check_clean_at_once(self):
        """The property that was impossible before: both gates green on the
        same bytes."""
        done = subprocess.run(
            [
                "npx", "--yes", "prettier@3.8.1",
                "--config", "config/prettierrc.json",
                "--ignore-path", "config/prettierignore",
                "--check", str(DOC.relative_to(ROOT)),
            ],
            cwd=str(ROOT), capture_output=True, text=True,
        )
        assert done.returncode == 0, done.stdout + done.stderr
        assert check() == 0


def first_delimiter(text: str) -> str:
    """A delimiter row from INSIDE the generated block.

    One outside it appears identically on both sides of the comparison, so
    mutating it would prove nothing.
    """
    from conftest import load_script

    module = load_script("scripts/update-label-docs.py")
    block = text.split(module.BEGIN, 1)[1].split(module.END, 1)[0]
    row = next(
        (ln for ln in block.split("\n") if re.fullmatch(r"\|(?:\s*:?-+:?\s*\|)+", ln)), None
    )
    assert row, "no table delimiter row inside the generated block; re-point this test"
    return row


class TestAlignmentIsStillContent:
    """A delimiter's dash COUNT is padding; its colons are meaning."""

    def test_a_changed_alignment_is_drift(self):
        original = DOC.read_text(encoding="utf-8")
        row = first_delimiter(original)
        flipped = row.replace(":-", "-", 1)[:-2] + ":|" if ":-" in row else row
        assert flipped != row, "the fixture no longer changes the alignment"
        DOC.write_text(original.replace(row, flipped, 1), encoding="utf-8")
        try:
            assert check() != 0, "an alignment change is no longer detected"
        finally:
            DOC.write_text(original, encoding="utf-8")

    def test_a_widened_delimiter_is_not_drift(self):
        original = DOC.read_text(encoding="utf-8")
        row = first_delimiter(original)
        widened = row.replace("-", "----", 1)
        assert widened != row
        DOC.write_text(original.replace(row, widened, 1), encoding="utf-8")
        try:
            assert check() == 0, "delimiter padding is being reported as drift"
        finally:
            DOC.write_text(original, encoding="utf-8")
