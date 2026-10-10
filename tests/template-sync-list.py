# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The list an owner edits, and git's matcher reading it.

`.github/template-sync` is the one file of the three an owner is invited to
change, so the rules for reading and redrawing it are the rules that decide
whether an owner's choice is kept. Each one is pinned here: a switch-off
survives the template's next release, a deleted line reads as off, a rule of
the owner's always comes last, and nothing the template did not write is
ever dropped.

The matcher is git's own, run against an empty repository, so these also
pin what the documentation promises: a line means here exactly what it would
mean in a .gitignore.
"""

from __future__ import annotations

import pytest
from conftest import load_script

sync = load_script("scripts/template-sync.py")

TEMPLATE = """\
# Header note.

# --- Kept current
/a.md
/b.md

# --- Yours
#/README.md

# --- Your rules ---
"""


def lines(text: str) -> list[str]:
    return text.splitlines()


class TestClassifyingALine:
    @pytest.mark.parametrize(
        ("text", "kind", "key", "on"),
        [
            ("", "blank", "", False),
            ("   ", "blank", "", False),
            ("# a note", "note", "", False),
            ("#", "note", "", False),
            ("#\tnote", "note", "", False),
            ("/a.md", "entry", "/a.md", True),
            ("#/a.md", "entry", "/a.md", False),
            ("!/docs/**", "entry", "!/docs/**", True),
            ("#!/docs/**", "entry", "!/docs/**", False),
        ],
    )
    def test_each_kind(self, text, kind, key, on):
        line = sync.classify(text)
        assert (line.kind, line.key, line.on) == (kind, key, on)


class TestRedrawingTheList:
    def test_a_fresh_list_redraws_to_itself(self):
        assert sync.merge_list(TEMPLATE, TEMPLATE, TEMPLATE) == TEMPLATE

    def test_a_switch_off_survives_a_new_release(self):
        mine = TEMPLATE.replace("\n/a.md\n", "\n#/a.md\n")
        newer = TEMPLATE.replace("/b.md\n", "/b.md\n/c.md\n")
        out = lines(sync.merge_list(TEMPLATE, newer, mine))
        assert "#/a.md" in out and "/c.md" in out

    def test_a_switch_on_survives_a_new_release(self):
        mine = TEMPLATE.replace("#/README.md", "/README.md")
        out = lines(sync.merge_list(TEMPLATE, TEMPLATE.replace("# Header note.", "# Changed note."), mine))
        assert "/README.md" in out

    def test_a_deleted_line_reads_as_switched_off(self):
        mine = TEMPLATE.replace("/a.md\n", "")
        out = lines(sync.merge_list(TEMPLATE, TEMPLATE, mine))
        assert "#/a.md" in out, "a deleted line must come back visibly off, not silently on"

    def test_a_deleted_line_that_was_already_off_stays_off(self):
        mine = TEMPLATE.replace("#/README.md\n", "")
        assert "#/README.md" in lines(sync.merge_list(TEMPLATE, TEMPLATE, mine))

    def test_an_entry_the_template_never_wrote_moves_under_your_rules_and_keeps_its_order(self):
        mine = TEMPLATE.replace("/a.md\n", "/a.md\n!/b.md\n/src/**\n")
        out = lines(sync.merge_list(TEMPLATE, TEMPLATE, mine))
        marker = out.index("# --- Your rules ---")
        assert out[marker + 1:] == ["!/b.md", "/src/**"]

    def test_your_own_notes_are_kept_and_the_templates_are_redrawn(self):
        mine = TEMPLATE.replace("# --- Yours", "# my note about yours\n# --- Yours")
        newer = TEMPLATE.replace("# Header note.", "# A new header.")
        out = lines(sync.merge_list(TEMPLATE, newer, mine))
        assert "# A new header." in out and "# Header note." not in out
        assert "# my note about yours" in out[out.index("# --- Your rules ---"):]

    def test_rules_are_kept_verbatim_and_last(self):
        mine = TEMPLATE + "!/b.md\n\n# because\n/README.md\n"
        out = sync.merge_list(TEMPLATE, TEMPLATE.replace("/b.md\n", "/b.md\n/z.md\n"), mine)
        assert out.endswith("# --- Your rules ---\n!/b.md\n\n# because\n/README.md\n")

    def test_a_new_entry_arrives_with_the_templates_default(self):
        newer = TEMPLATE.replace("/b.md\n", "/b.md\n/c.md\n#/d.md\n")
        out = lines(sync.merge_list(TEMPLATE, newer, TEMPLATE))
        assert "/c.md" in out and "#/d.md" in out

    def test_a_removed_entry_goes(self):
        newer = TEMPLATE.replace("/b.md\n", "")
        out = lines(sync.merge_list(TEMPLATE, newer, TEMPLATE))
        assert "/b.md" not in out and "#/b.md" not in out

    def test_a_changed_default_reaches_an_owner_who_never_chose(self):
        newer = TEMPLATE.replace("\n/a.md\n", "\n#/a.md\n")
        assert "#/a.md" in lines(sync.merge_list(TEMPLATE, newer, TEMPLATE))

    def test_a_changed_default_does_not_override_an_owner_who_did(self):
        mine = TEMPLATE.replace("#/README.md", "/README.md")
        newer = TEMPLATE  # still off by default
        assert "/README.md" in lines(sync.merge_list(TEMPLATE, newer, mine))

    def test_a_changed_default_never_switches_on_a_line_the_owner_has_off(self):
        # The owner switched a.md off; the template then made it off by default
        # too, so the owner's line reads like the default - and then the
        # template made it on again. It stays off: only off reaches an owner.
        mine = TEMPLATE.replace("\n/a.md\n", "\n#/a.md\n")
        base = mine  # the template's own default had become off
        newer = TEMPLATE  # and is on again
        assert "#/a.md" in lines(sync.merge_list(base, newer, mine))

    def test_a_line_held_off_stays_off_through_a_move(self):
        mine = TEMPLATE.replace("\n/a.md\n", "\n#/a.md\n")
        newer = TEMPLATE.replace("/a.md\n", "/moved.md\n")
        out = lines(sync.merge_list(mine, newer, mine, renames={"a.md": "moved.md"}))
        assert "#/moved.md" in out and "/moved.md" not in out

    def test_a_line_the_owner_has_on_still_follows_a_default_to_off(self):
        newer = TEMPLATE.replace("\n/a.md\n", "\n#/a.md\n")
        assert "#/a.md" in lines(sync.merge_list(TEMPLATE, newer, TEMPLATE))

    def test_a_disabled_path_with_its_own_line_is_switched_off(self):
        out = lines(sync.merge_list(TEMPLATE, TEMPLATE, TEMPLATE, disabled=["a.md"]))
        assert "#/a.md" in out

    def test_a_disabled_path_covered_only_by_a_pattern_gets_one_rule(self):
        template = TEMPLATE.replace("/a.md\n", "/docs/**\n")
        out = sync.merge_list(template, template, template, disabled=["docs/x.md"])
        assert lines(out).count("!/docs/x.md") == 1
        again = sync.merge_list(template, template, out, disabled=["docs/x.md"])
        assert lines(again).count("!/docs/x.md") == 1, "a rule must not be added twice"

    def test_a_rename_carries_the_owners_choice(self):
        mine = TEMPLATE.replace("\n/a.md\n", "\n#/a.md\n")
        newer = TEMPLATE.replace("/a.md\n", "/moved.md\n")
        out = lines(sync.merge_list(TEMPLATE, newer, mine, renames={"a.md": "moved.md"}))
        assert "#/moved.md" in out

    def test_without_a_base_choices_are_read_against_the_new_defaults(self):
        mine = TEMPLATE.replace("\n/a.md\n", "\n#/a.md\n")
        assert "#/a.md" in lines(sync.merge_list(None, TEMPLATE, mine))

    def test_without_an_owners_copy_the_defaults_are_drawn(self):
        assert sync.merge_list(TEMPLATE, TEMPLATE, None) == TEMPLATE

    def test_a_template_without_a_marker_still_gets_one(self):
        bare = "/a.md\n"
        assert sync.RULES_MARKER in sync.merge_list(bare, bare, bare)

    @pytest.mark.parametrize(
        "mine",
        [
            TEMPLATE,
            TEMPLATE.replace("\n/a.md\n", "\n#/a.md\n"),
            TEMPLATE.replace("/b.md\n", ""),
            TEMPLATE.replace("#/README.md", "/README.md") + "!/a.md\n",
            TEMPLATE.replace("# Header note.", "# Header note.\n# mine\n/extra/**"),
        ],
    )
    def test_redrawing_twice_is_redrawing_once(self, mine):
        newer = TEMPLATE.replace("/b.md\n", "/b.md\n/c.md\n").replace("# Header note.", "# Newer.")
        once = sync.merge_list(TEMPLATE, newer, mine)
        assert sync.merge_list(newer, newer, once) == once


NASTY = [
    "plain.md",
    "dir/nested/file.md",
    "with space.md",
    "trailing space ",
    "amp&ersand.md",
    "star*name.md",
    "question?.md",
    "br[ack]et.md",
    "back\\slash.md",
    "#hash-first.md",
    "!bang-first.md",
    "ünïcødé/ファイル.md",
    "Packages-&-Workspaces.md",
]


class TestEscapingAPath:
    @pytest.mark.parametrize("path", NASTY)
    def test_the_escaped_pattern_matches_exactly_that_path(self, path):
        others = [p for p in NASTY if p != path] + [f"sub/{path}", f"{path}x"]
        assert sync.matched(sync.escape(path) + "\n", [path, *others]) == {path}

    @pytest.mark.parametrize("path", NASTY)
    def test_unescape_inverts_escape(self, path):
        assert sync.unescape(sync.escape(path)) == path

    @pytest.mark.parametrize("path", NASTY)
    def test_an_escaped_path_reads_as_literal(self, path):
        assert sync.literal(sync.escape(path))

    @pytest.mark.parametrize("pattern", ["/docs/**", "/a?.md", "/[ab].md", "/docs/"])
    def test_a_pattern_does_not(self, pattern):
        assert not sync.literal(pattern)


class TestGitsMatcherReadsTheList:
    PATHS = ("README.md", "docs/README.md", "docs/a.md", "docs/sub/b.md", "src/x.go", "LICENSE")

    def test_a_leading_slash_anchors_to_the_root(self):
        assert sync.matched("/README.md\n", self.PATHS) == {"README.md"}

    def test_a_bare_name_matches_at_any_depth_which_is_why_the_check_insists_on_slashes(self):
        assert sync.matched("README.md\n", self.PATHS) == {"README.md", "docs/README.md"}

    def test_the_last_match_wins(self):
        assert sync.matched("/docs/**\n!/docs/a.md\n", self.PATHS) == {"docs/README.md", "docs/sub/b.md"}
        assert sync.matched("!/docs/a.md\n/docs/**\n", self.PATHS) == {
            "docs/README.md", "docs/a.md", "docs/sub/b.md"}

    def test_a_directory_pattern_covers_everything_under_it(self):
        assert sync.matched("/docs/\n", self.PATHS) == {"docs/README.md", "docs/a.md", "docs/sub/b.md"}

    def test_switched_off_lines_and_notes_match_nothing(self):
        assert sync.matched("# /README.md\n#/README.md\n#\n", self.PATHS) == set()

    def test_nothing_asked_nothing_matched(self):
        assert sync.matched("/README.md\n", []) == set()

    def test_the_repositorys_own_gitignore_cannot_interfere(self, tmp_path, monkeypatch):
        """The matcher runs in an empty repository of its own, not here."""
        (tmp_path / ".gitignore").write_text("*\n")
        monkeypatch.chdir(tmp_path)
        assert sync.matched("/README.md\n", self.PATHS) == {"README.md"}
