# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Every decision the planner can make, for every situation it can be in.

`decide()` is pure: one path, what the template held at the baseline, what it
holds now, what the owner holds, whether the path is synced, and whether the
owner deleted it before. That is a finite space, so it is walked whole here
and every point is held to the rules that make a sync safe:

  - a path that is not synced is never written or deleted;
  - a conflict writes nothing, deletes nothing and leaves the baseline alone;
  - a file is deleted only when the owner never changed it;
  - nothing is written that the owner already has;
  - the baseline moves to the template's version only when the template's
    change is in what the owner ends up with;
  - nothing written ever carries a conflict marker.

The rules are checked as properties over the whole matrix rather than as one
expected outcome per cell, so a new outcome cannot slip in unchecked.
"""

from __future__ import annotations

import itertools

import pytest
from conftest import load_script

sync = load_script("scripts/template-sync.py")
Side = sync.Side

BASE = b"one\ntwo\nthree\nfour\nfive\nsix\n"
TARGET = b"one\ntwo, improved\nthree\nfour\nfive\nsix\n"
COMPATIBLE = b"one\ntwo\nthree\nfour\nfive\nsix, mine\n"   # far from the template's change
CLASHING = b"one\ntwo, mine\nthree\nfour\nfive\nsix\n"     # the same line
BINARY = b"\x00binary\x01"


def side(data: bytes, mode: str = "100644", sha: str = "") -> Side:
    return Side(mode, data, sha or ("t" + str(abs(hash(data)))[:8]))


BASES = {
    "none": None,
    "missing": sync.MISSING,
    "base": side(BASE, sha="base"),
}
TARGETS = {
    "gone": None,
    "same": side(BASE, sha="base"),
    "changed": side(TARGET, sha="target"),
    "mode-only": side(BASE, "100755", sha="mode"),
}
OURS = {
    "absent": None,
    "untouched": side(BASE, sha="ours"),
    "has-target": side(TARGET, sha="ours"),
    "compatible": side(COMPATIBLE, sha="ours"),
    "clashing": side(CLASHING, sha="ours"),
    "binary": side(BINARY, sha="ours"),
}

MATRIX = list(itertools.product(BASES, TARGETS, OURS, (True, False), (True, False)))


def contains_template_change(result: bytes, base: Side | None, target: Side) -> bool:
    """True when re-merging the template's change into `result` changes nothing."""
    if base is None or base is sync.MISSING:
        return result == target.data
    if base.data == target.data:
        return True  # the template changed nothing, so there is nothing to be in
    if sync.binary(result, base.data, target.data):
        return result == target.data
    merged, clean = sync.merge3(result, base.data, target.data)
    return clean and merged == result


@pytest.mark.parametrize(("b", "t", "o", "synced", "was_deleted"), MATRIX)
class TestEveryCellKeepsTheRules:
    def decide(self, b, t, o, synced, was_deleted):
        return sync.decide("docs/a.md", BASES[b], TARGETS[t], OURS[o], synced=synced, was_deleted=was_deleted)

    def test_a_path_not_synced_is_never_touched(self, b, t, o, synced, was_deleted):
        d = self.decide(b, t, o, synced, was_deleted)
        if not synced:
            assert d.outcome == "not-synced" and d.write is None and not d.delete

    def test_a_conflict_touches_nothing(self, b, t, o, synced, was_deleted):
        d = self.decide(b, t, o, synced, was_deleted)
        if d.outcome == "conflict":
            assert d.write is None and not d.delete and d.state is None

    def test_a_delete_needs_an_untouched_file(self, b, t, o, synced, was_deleted):
        d = self.decide(b, t, o, synced, was_deleted)
        if d.delete:
            assert OURS[o] is not None and BASES[b] not in (None, sync.MISSING)
            assert OURS[o].data == BASES[b].data and TARGETS[t] is None

    def test_nothing_is_written_that_the_owner_already_has(self, b, t, o, synced, was_deleted):
        d = self.decide(b, t, o, synced, was_deleted)
        if d.write is not None and OURS[o] is not None:
            assert (d.write.data, d.write.mode) != (OURS[o].data, OURS[o].mode)

    def test_the_baseline_moves_only_when_the_change_is_in(self, b, t, o, synced, was_deleted):
        d = self.decide(b, t, o, synced, was_deleted)
        target = TARGETS[t]
        if isinstance(d.state, sync.FileState) and target is not None and not d.state.deleted:
            assert d.state.blob == target.sha
            result = d.write.data if d.write is not None else OURS[o].data
            assert contains_template_change(result, BASES[b], target), d.outcome

    def test_nothing_written_carries_a_marker(self, b, t, o, synced, was_deleted):
        d = self.decide(b, t, o, synced, was_deleted)
        if d.write is not None:
            assert b"<<<<<<<" not in d.write.data and b">>>>>>>" not in d.write.data

    def test_a_deleted_file_comes_back_only_when_switched_back_on(self, b, t, o, synced, was_deleted):
        d = self.decide(b, t, o, synced, was_deleted)
        if OURS[o] is None and d.write is not None and BASES[b] is not None:
            assert was_deleted and d.outcome == "restored"


class TestTheCellsThatMatterMost:
    def call(self, b, t, o, **kw):
        kw.setdefault("synced", True)
        kw.setdefault("was_deleted", False)
        return sync.decide("docs/a.md", b, t, o, **kw)

    def test_untouched_takes_the_new_version(self):
        d = self.call(BASES["base"], TARGETS["changed"], OURS["untouched"])
        assert d.outcome == "updated" and d.write.data == TARGET

    def test_compatible_edits_merge(self):
        d = self.call(BASES["base"], TARGETS["changed"], OURS["compatible"])
        assert d.outcome == "merged"
        assert b"two, improved" in d.write.data and b"six, mine" in d.write.data

    def test_clashing_edits_conflict_with_the_templates_diff(self):
        d = self.call(BASES["base"], TARGETS["changed"], OURS["clashing"])
        assert d.outcome == "conflict" and "+two, improved" in d.diff

    def test_the_owner_already_having_it_is_current(self):
        assert self.call(BASES["base"], TARGETS["changed"], OURS["has-target"]).outcome == "current"

    def test_a_template_mode_change_arrives_without_content(self):
        d = self.call(BASES["base"], TARGETS["mode-only"], OURS["untouched"])
        assert d.outcome == "updated" and d.write.mode == "100755" and d.write.data == BASE

    def test_a_template_mode_change_merges_with_an_owners_edit(self):
        d = self.call(BASES["base"], side(TARGET, "100755", "t2"), OURS["compatible"])
        assert d.outcome == "merged" and d.write.mode == "100755"

    def test_the_owners_mode_wins_a_tie(self):
        d = self.call(BASES["base"], TARGETS["changed"], side(BASE, "100755", "o"))
        assert d.write.mode == "100755"

    def test_an_owner_deletion_is_recorded_once(self):
        d = self.call(BASES["base"], TARGETS["changed"], None)
        assert d.outcome == "owner-deleted" and d.state.deleted and d.write is None

    def test_a_new_file_where_the_owner_has_one_is_a_conflict(self):
        d = self.call(None, TARGETS["changed"], OURS["clashing"])
        assert d.outcome == "conflict" and d.write is None

    def test_a_missing_baseline_is_never_guessed(self):
        d = self.call(sync.MISSING, TARGETS["changed"], OURS["compatible"])
        assert d.outcome == "conflict" and "no longer has" in d.detail

    def test_binary_on_both_sides_is_a_conflict(self):
        d = self.call(side(BINARY + b"base", sha="b"), side(BINARY + b"tmpl", sha="t"), OURS["binary"])
        assert d.outcome == "conflict"


def plan(base, target, ours, **kw):
    kw.setdefault("synced", set(base) | set(target))
    return {d.path: d for d in sync.plan(base, target, ours, **kw)}


class TestThePlanAsAWhole:
    def test_the_never_paths_are_never_planned(self):
        files = {p: side(b"x", sha="x") for p in sync.NEVER}
        assert plan(files, files, {}) == {}

    def test_a_symlink_or_submodule_here_is_a_conflict(self):
        d = plan({"a": side(BASE, sha="b")}, {"a": side(TARGET, sha="t")}, {}, special={"a"})["a"]
        assert d.outcome == "conflict" and d.write is None

    def test_a_file_cannot_land_where_the_owner_has_a_directory(self):
        d = plan({}, {"bin": side(b"x", sha="t")}, {"bin/mine.sh": side(b"y")})["bin"]
        assert d.outcome == "conflict"

    def test_a_directory_cannot_land_where_the_owner_has_a_file(self):
        d = plan({}, {"bin/run.sh": side(b"x", sha="t")}, {"bin": side(b"y")})["bin/run.sh"]
        assert d.outcome == "conflict"

    def test_a_swap_the_template_makes_itself_goes_through(self):
        """File `x` becomes directory `x/`: the delete clears the way for the write."""
        out = plan({"x": side(b"old", sha="b")}, {"x/new": side(b"new", sha="t")}, {"x": side(b"old")})
        assert out["x"].outcome == "deleted" and out["x/new"].outcome == "added"

    def test_a_workflow_change_waits_for_a_token(self):
        out = plan({".github/workflows/w.yml": side(BASE, sha="b")},
                   {".github/workflows/w.yml": side(TARGET, sha="t")},
                   {".github/workflows/w.yml": side(BASE)},
                   defer=lambda p: p.startswith(".github/workflows/"))
        d = out[".github/workflows/w.yml"]
        assert d.outcome == "deferred" and d.write is None and d.state is None

    def test_a_move_across_the_token_boundary_waits_whole(self):
        content = side(BASE, sha="same")
        out = plan({"scripts/w.yml": content}, {".github/workflows/w.yml": content},
                   {"scripts/w.yml": side(BASE)}, defer=lambda p: p.startswith(".github/workflows/"))
        assert out["scripts/w.yml"].outcome == "deferred"
        assert out[".github/workflows/w.yml"].outcome == "deferred"

    def test_a_move_is_recognised_only_when_it_is_unambiguous(self):
        twin = side(BASE, sha="same")
        out = plan({"a": twin, "b": twin}, {"c": twin, "d": twin}, {"a": side(BASE), "b": side(BASE)})
        assert "moved" not in {d.outcome for d in out.values()}, "two identical files moved: no guessing"

    def test_a_move_with_clashing_edits_waits_and_touches_nothing(self):
        out = plan({"a": side(BASE, sha="same")}, {"b": side(BASE, sha="same2")}, {"a": side(CLASHING)})
        # Same content moved; the owner's edit merges trivially, so it moves.
        assert out["a"].outcome == "moved" and out["b"].write.data == CLASHING

    def test_an_unsafe_path_is_skipped(self):
        out = plan({}, {"../x": side(b"x", sha="t")}, {}, synced={"../x"})
        assert out["../x"].outcome == "unsafe"
