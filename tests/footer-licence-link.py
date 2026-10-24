# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Every footer links to the licence file and names no licence.

A footer that names its licence, "Distributed under the MIT License.", is
right only until the licence changes, and then it is wrong on every page at
once, with nothing to say so. Every footer here reads "Distributed under
the terms in [LICENSE](/LICENSE).": the link names no licence, so it stays
true whatever the file holds, and it starts at the repository root, which
GitHub resolves from any folder on any branch and the link check resolves
through `--root-dir`. It names no repository either, so it survives a fork,
a rename, or a page moved to another folder.
"""

from __future__ import annotations

import re
import subprocess

from conftest import ROOT

CLAUSE = re.compile(r"distributed under", re.IGNORECASE)
LINK = re.compile(r"\[[^\]]*\]\([^)]*\)")
# A licence named in the clause's own words, outside the link to its file.
NAMED = re.compile(r"\b(licen[cs]e[sd]?|MIT|Apache|A?GPL|LGPL|BSD|MPL|ISC|Unlicense|CC0|EPL)\b", re.IGNORECASE)
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
# Inline code quotes a clause as an example, as the styling guide does; it is no footer.
INLINE = re.compile(r"(`+)(?:(?!\1).)+?\1")


def footers():
    """Every line a footer's licence clause sits on, outside code of either kind."""
    listed = subprocess.run(["git", "ls-files", "-z", "*.md"], cwd=ROOT, capture_output=True, text=True, check=True)
    for rel in filter(None, listed.stdout.split("\0")):
        fence = None
        for number, line in enumerate((ROOT / rel).read_text(encoding="utf-8").splitlines(), 1):
            marker = FENCE.match(line)
            if fence:
                if marker and marker.group(1)[0] == fence[0] and len(marker.group(1)) >= len(fence):
                    fence = None
                continue
            if marker:
                fence = marker.group(1)
                continue
            text = INLINE.sub("", line)
            if CLAUSE.search(text):
                yield f"{rel}:{number}", text


def test_there_are_footers_to_check():
    """A reworded clause must not leave the two checks below with nothing to read."""
    assert len(list(footers())) >= 50


def test_every_footer_links_to_the_licence_from_the_root():
    stray = [where for where, line in footers() if "](/LICENSE)" not in line]
    assert not stray, "link the licence as [LICENSE](/LICENSE), which resolves from any folder:\n" + "\n".join(stray)


def test_no_footer_names_a_licence():
    named = [where for where, line in footers() if NAMED.search(LINK.sub("", line))]
    assert not named, "a footer names its licence, which goes stale when the licence changes:\n" + "\n".join(named)
