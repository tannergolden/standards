# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The changelog config must use keys git-cliff actually reads.

`config/cliff.toml` carried `skip_commits = "chore\\(docs\\): 🏥 update
repository health status on.*"` under a comment saying "Skip commits from
the bot". `skip_commits` is not a git-cliff key. The `[git]` table accepts
`skip_tags` and `ignore_tags`; skipping a COMMIT is done with a
`commit_parsers` entry carrying `skip = true`, which this same file already
uses correctly one group above for `^test`.

git-cliff ignores an unknown key silently, so the bot commits it was meant
to suppress were matched by the `^chore` parser instead and landed in
"🔧 Miscellaneous & Tooling" in every set of release notes, in every
repository consuming this config.

A config key that does nothing is worse than an absent one: it reads as a
solved problem.
"""

from __future__ import annotations

import re

import pytest
import tomllib
from conftest import ROOT

CLIFF = ROOT / "config/cliff.toml"

# Every key git-cliff recognises in [git]. An entry outside this set is
# either a typo or a version drift, and either way it is doing nothing.
KNOWN_GIT_KEYS = {
    "conventional_commits",
    "filter_unconventional",
    "require_conventional",
    "split_commits",
    "commit_preprocessors",
    "commit_parsers",
    "protect_breaking_commits",
    "filter_commits",
    "tag_pattern",
    "skip_tags",
    "ignore_tags",
    "count_tags",
    "use_branch_tags",
    "topo_order",
    "topo_order_commits",
    "sort_commits",
    "limit_commits",
    "recurse_submodules",
    "link_parsers",
    "exclude_paths",
    "include_paths",
}


@pytest.fixture(scope="module")
def cliff() -> dict:
    return tomllib.loads(CLIFF.read_text(encoding="utf-8"))


class TestOnlyRealKeys:
    def test_no_unknown_key_in_the_git_table(self, cliff):
        """The defect: `skip_commits` was silently ignored."""
        unknown = set(cliff["git"]) - KNOWN_GIT_KEYS
        assert not unknown, (
            f"config/cliff.toml [git] carries keys git-cliff does not read: {sorted(unknown)}. "
            "An ignored key looks like a solved problem and is not one."
        )

    def test_the_file_still_parses_as_toml(self, cliff):
        assert cliff["git"]["conventional_commits"] is True


class TestTheBotCommitsAreSkipped:
    def test_a_parser_skips_the_health_status_commits(self, cliff):
        skipping = [p for p in cliff["git"]["commit_parsers"] if p.get("skip")]
        assert any(
            re.search(r"health status", p.get("message", "")) for p in skipping
        ), "nothing skips the repository-health bot commits"

    def test_that_parser_is_ordered_before_the_chore_group(self, cliff):
        """git-cliff takes the FIRST matching parser, so a skip placed after
        `^chore` would never be reached by a `chore(docs):` message."""
        parsers = cliff["git"]["commit_parsers"]
        health = next(
            i for i, p in enumerate(parsers) if "health status" in p.get("message", "")
        )
        # The GROUPING parser, not the skip: the skip's own pattern also
        # begins `^chore`, and matching it here would compare it to itself.
        chore = next(
            i
            for i, p in enumerate(parsers)
            if p.get("message", "").startswith("^chore") and p.get("group")
        )
        assert health < chore, (
            f"the health-status skip is at index {health}, after the ^chore group at {chore}; "
            "git-cliff takes the first match, so it would never fire"
        )

    def test_the_pattern_matches_a_real_bot_subject(self, cliff):
        parser = next(
            p for p in cliff["git"]["commit_parsers"] if "health status" in p.get("message", "")
        )
        subject = "chore(docs): 🏥 update repository health status on 2026-07-30"
        assert re.search(parser["message"], subject), (
            f"{parser['message']!r} does not match {subject!r}"
        )

    def test_an_ordinary_chore_is_still_grouped(self, cliff):
        """The skip must be narrow: it is not a licence to drop every chore."""
        parsers = cliff["git"]["commit_parsers"]
        subject = "chore(deps): 🔧 bump the pinned actions"
        first = next(p for p in parsers if re.search(p["message"], subject))
        assert not first.get("skip"), f"an ordinary chore is being skipped by {first}"
        assert first.get("group")
