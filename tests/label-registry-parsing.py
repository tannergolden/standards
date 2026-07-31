# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The label registry is YAML, so both quoting styles must parse.

`update-label-docs.py` is stdlib-only by design, so it reads `labels.yml`
with a regex rather than a YAML parser. That regex accepted a
SINGLE-quoted value and nothing else, and exited on anything it could not
match.

YAML permits both. `'Something isn''t working'` and
`"Something isn't working"` are the same string, and a formatter is free to
prefer either: running this repository's own published Prettier config over
`data/labels.yml` converts the first form to the second, at which point the
generator refuses the file it is meant to read and `make lint-docs` fails
with "unparseable line".

That is a real incompatibility between two tools this repository ships, and
it surfaced only when the formatter was finally run here.
"""

from __future__ import annotations

import pathlib

import pytest
from conftest import ROOT, load_script

label_docs = load_script("scripts/update-label-docs.py")

QUOTING = [
    ("single", "- name: 'bug'\ncolor: 'd73a4a'\ndescription: 'Something is broken'\n"),
    ("double", '- name: "bug"\ncolor: "d73a4a"\ndescription: "Something is broken"\n'),
]

APOSTROPHE = [
    ("single, doubled", "- name: 'bug'\ncolor: 'd73a4a'\ndescription: 'Something isn''t working'\n"),
    ("double, bare", '- name: "bug"\ncolor: "d73a4a"\ndescription: "Something isn\'t working"\n'),
]


def load(tmp_path, text):
    path = pathlib.Path(tmp_path / "labels.yml")
    path.write_text(text, encoding="utf-8")
    return label_docs.load(path)


class TestBothQuotingStylesParse:
    @pytest.mark.parametrize(("style", "text"), QUOTING)
    def test_a_plain_entry(self, tmp_path, style, text):
        """The defect: only single quotes were accepted."""
        assert load(tmp_path, text) == [
            {"name": "bug", "color": "d73a4a", "description": "Something is broken"}
        ], style

    @pytest.mark.parametrize(("style", "text"), APOSTROPHE)
    def test_an_apostrophe_yields_the_same_value(self, tmp_path, style, text):
        """The two spellings are the same string, and must read as one."""
        assert load(tmp_path, text)[0]["description"] == "Something isn't working", style


class TestTheShippedRegistryIsUnaffected:
    def test_it_still_parses(self):
        entries = label_docs.load(ROOT / "data" / "labels.yml")
        assert len(entries) > 30

    def test_the_stock_bug_label_reads_correctly(self):
        entries = label_docs.load(ROOT / "data" / "labels.yml")
        bug = next(e for e in entries if e["name"] == "bug")
        assert bug["description"] == "Something isn't working"


class TestMalformedLinesStillFail:
    def test_an_unquoted_value_is_rejected(self, tmp_path):
        # The registry's contract is quoted values; loosening to bare
        # scalars would start accepting things YAML would read differently.
        with pytest.raises(SystemExit):
            load(tmp_path, "- name: bug\ncolor: d73a4a\n")

    def test_a_mismatched_quote_is_rejected(self, tmp_path):
        with pytest.raises(SystemExit):
            load(tmp_path, "- name: 'bug\"\n")
