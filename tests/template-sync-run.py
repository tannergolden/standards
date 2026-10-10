# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Template sync, end to end, on real repositories.

Each class here is one promise the sync makes to the owner of a generated
repository, tested the way it would be broken: a template that releases, an
owner who edits, deletes and opts out, and a sync pull request that gets
merged whether or not it was clean.

The one that matters most is TestNothingIsLostAcrossSyncs. Replaying the real
history of both templates showed that a single baseline for the whole
repository loses a change silently once a sync pull request with a conflict
in it is merged. Nothing about any one run looks wrong; the loss only shows
across two. So that scenario is played out in full here, and the property
suite plays out thousands more like it.
"""

from __future__ import annotations

import json
import os
import re

import pytest
from conftest import SYNC_ENV, TEMPLATE_FILES, load_script

LEAK = re.compile(r"tannergolden(?!/[A-Za-z0-9._-])")


def entry_on(world, key: str) -> bool:
    lines = world.text(".github/template-sync").splitlines()
    return key in lines


class TestAFreshRepository:
    def test_the_generation_lock_records_the_template_as_shipped(self, sync_world):
        sync_world.generate()
        lock = sync_world.lock()
        template = sync_world.sync.tree(sync_world.template, "v1")
        assert lock.template == "tannergolden/path"
        assert sync_world.sync.SENTINEL not in lock.files
        for path, state in lock.files.items():
            assert state.blob == template[path].sha, f"{path} is not recorded as the template shipped it"
        assert ".github/template-sync" in lock.files, "the list's own baseline must be recorded"

    def test_the_first_sync_at_the_same_version_changes_nothing(self, sync_world):
        sync_world.generate()
        result = sync_world.run_sync()
        assert not result.changed, "a fresh repository must not get a pull request for nothing"
        assert sync_world.clean()

    def test_an_uninitialised_repository_is_left_alone(self, sync_world):
        sync_world.generate(init=False)
        with pytest.raises(sync_world.sync.Skip, match="not been initialised"):
            sync_world.run_sync()

    def test_a_template_with_no_major_tag_yet_is_a_notice_not_a_failure(self, sync_world):
        sync_world.generate()
        with pytest.raises(sync_world.sync.Skip, match="has not published `v9`"):
            sync_world.run_sync(ref="v9")


class TestTheTemplatesChangesArrive:
    def test_an_untouched_file_takes_the_new_version(self, sync_world):
        sync_world.generate()
        sync_world.release("v1.1.0", {"scripts/tool.py": "print('better')\n"})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["scripts/tool.py"] == "updated"
        assert sync_world.text("scripts/tool.py") == "print('better')\n"
        assert sync_world.lock().version == "v1.1.0"

    def test_a_new_file_arrives_in_the_owners_identity(self, sync_world):
        sync_world.generate()
        list_text = sync_world.text(".github/template-sync").replace(
            "/scripts/tool.py\n", "/scripts/tool.py\n/docs/new.md\n")
        sync_world.release("v1.1.0", {
            "docs/new.md": "# New\n\nBuilt with ❤️ by [@tannergolden](https://github.com/tannergolden).\n",
            ".github/template-sync": list_text,
        })
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["docs/new.md"] == "added"
        text = sync_world.text("docs/new.md")
        assert "[@janedoe](https://github.com/janedoe)" in text
        assert not LEAK.search(text), "the template author's identity leaked into a new file"
        assert entry_on(sync_world, "/docs/new.md"), "the list must show the new path"

    def test_an_address_in_a_new_file_is_left_alone(self, sync_world):
        sync_world.generate()
        sync_world.release("v1.1.0", {
            "docs/guide.md": "# Guide\n\nUses tannergolden/standards.\n\n"
                             "Built with ❤️ by [@tannergolden](https://github.com/tannergolden).\n",
        })
        sync_world.run_sync()
        text = sync_world.text("docs/guide.md")
        assert "tannergolden/standards" in text and "[@janedoe]" in text

    def test_a_removed_file_goes_when_untouched_and_stays_when_edited(self, sync_world):
        sync_world.generate()
        sync_world.owner({"docs/guide.md": "# My guide\n"})
        list_text = sync_world.text(".github/template-sync")
        sync_world.release("v1.1.0", {
            "scripts/tool.py": None,
            "docs/guide.md": None,
            ".github/template-sync": list_text.replace("/scripts/tool.py\n", "").replace("/docs/guide.md\n", ""),
        })
        result = sync_world.run_sync()
        outcomes = sync_world.outcomes(result)
        assert outcomes["scripts/tool.py"] == "deleted"
        assert sync_world.read("scripts/tool.py") is None
        assert outcomes["docs/guide.md"] == "kept"
        assert sync_world.text("docs/guide.md") == "# My guide\n"
        assert "docs/guide.md" not in sync_world.lock().files, "a kept file is the owner's now"

    def test_the_executable_bit_arrives_and_the_owners_own_choice_wins(self, sync_world):
        sync_world.generate()
        sync_world.release("v1.1.0", {"docs/guide.md": "# Guide v2\n"}, {"docs/guide.md": "100755"})
        sync_world.run_sync()
        assert os.access(sync_world.repo / "docs/guide.md", os.X_OK)
        sync_world.owner({}, {"scripts/tool.py": "100644"})
        sync_world.release("v1.2.0", {"scripts/tool.py": "print('v2')\n"})
        sync_world.run_sync()
        assert not os.access(sync_world.repo / "scripts/tool.py", os.X_OK), "the owner cleared the bit"
        assert sync_world.text("scripts/tool.py") == "print('v2')\n"


class TestTheReportRendersWhatItShows:
    def test_a_conflict_in_a_markdown_file_keeps_its_own_fences_inside_the_diff(self):
        sync = load_script("scripts/template-sync.py")
        diff = "--- a/x.md\n+++ b/x.md\n@@ -1 +1,3 @@\n+```yaml\n+a: 1\n+```"
        report = sync.render_report(template="t/p", version="v1.1.0", previous="v1.0.0", list_changed=False,
                                    decisions=[sync.Decision("x.md", "conflict", detail="clash", diff=diff)])
        fence = re.search(r"^  (`{3,})diff$", report, re.M).group(1)
        assert len(fence) > 3, "a three-backtick fence would close at the diff's own"
        assert f"\n  {fence}\n" in report

    def test_a_version_named_by_its_own_sha_is_not_said_twice(self, sync_world):
        tagged = sync_world.git(sync_world.template, "rev-parse", "HEAD").strip()
        assert sync_world.sync.version_label(sync_world.template, tagged, tagged) == "v1.0.0", "a release tag wins"
        sha = sync_world.commit(sync_world.template, "untagged work")
        assert sync_world.sync.version_label(sync_world.template, sha, sha[:12]) == sha[:7]
        assert sync_world.sync.version_label(sync_world.template, sha, "Development") == f"Development@{sha[:7]}"


class TestABareTemplateClone:
    def test_a_sync_from_a_bare_clone_matches_one_from_a_working_tree(self, sync_world, tmp_path):
        import subprocess
        sync_world.generate()
        sync_world.owner({"docs/guide.md": sync_world.text("docs/guide.md") + "An owner's line.\n"})
        moved = TEMPLATE_FILES["docs/guide.md"] + "\nEdited after the move.\n"
        sync_world.release("v1.1.0", {
            "docs/guide.md": None, "docs/moved/guide.md": moved, "scripts/tool.py": "print('v1.1')\n",
            ".github/template-sync": sync_world.text(".github/template-sync").replace(
                "/docs/guide.md", "/docs/moved/guide.md"),
        })
        bare = tmp_path / "template.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(sync_world.template), str(bare)], check=True,
                       env={**os.environ, **SYNC_ENV})
        from_bare = sync_world.sync.run(sync_world.repo, bare, ref="v1", write=False)
        from_tree = sync_world.sync.run(sync_world.repo, sync_world.template, ref="v1", write=False)
        assert sync_world.outcomes(from_bare) == sync_world.outcomes(from_tree)
        assert from_bare.lock == from_tree.lock
        assert sync_world.outcomes(from_bare)["docs/moved/guide.md"] in ("moved-here", "waiting")


class TestWhatTheRunRefusesToGuess:
    def test_an_owners_list_that_is_not_utf8_is_a_sentence_not_a_traceback(self, sync_world):
        sync_world.generate()
        sync_world.owner({".github/template-sync": b"/docs/guide.md\n\xff\xfe\n"})
        with pytest.raises(sync_world.sync.SyncError, match="not valid UTF-8"):
            sync_world.run_sync()

    def test_a_waiting_file_keeps_the_version_it_started_waiting_at(self, sync_world):
        sync_world.generate()
        sync_world.owner({"scripts/tool.py": "print('mine')\n"})
        sync_world.release("v1.1.0", {"scripts/tool.py": "print('theirs')\n"})
        sync_world.run_sync()
        assert sync_world.lock().pending["scripts/tool.py"]["version"] == "v1.1.0"
        sync_world.release("v1.2.0", {"README.md": "# Template, revised\n"})  # the owner's file, never synced
        result = sync_world.run_sync()
        assert sync_world.lock().pending["scripts/tool.py"]["version"] == "v1.1.0"
        assert not result.changed, "a release that changes nothing here opens no pull request"

    def test_a_missing_baseline_still_takes_the_templates_mode(self):
        sync = load_script("scripts/template-sync.py")
        target = sync.Side("100755", b"same\n", "t" * 40)
        ours = sync.Side("100644", b"same\n", "o" * 40)
        decision = sync.decide("tool.sh", sync.MISSING, target, ours, synced=True, was_deleted=False)
        assert decision.outcome == "updated" and decision.write.mode == "100755"
        assert decision.write.data == b"same\n"


class TestTheOwnersEditsSurvive:
    def test_an_edit_away_from_the_templates_change_merges(self, sync_world):
        sync_world.generate()
        sync_world.owner({".github/workflows/checks.yml": sync_world.text(".github/workflows/checks.yml")
                          .replace("'validate'", "'golangci-lint run'")})
        sync_world.release("v1.1.0", {".github/workflows/checks.yml": TEMPLATE_CHECKS
                                      .replace("# The commands", "# The real commands")})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)[".github/workflows/checks.yml"] == "merged"
        text = sync_world.text(".github/workflows/checks.yml")
        assert "golangci-lint run" in text and "# The real commands" in text

    def test_a_clash_leaves_the_file_untouched_and_says_what_the_template_changed(self, sync_world):
        sync_world.generate()
        mine = TEMPLATE_CHECKS.replace("'validate'", "'golangci-lint run'")
        sync_world.owner({".github/workflows/checks.yml": mine})
        sync_world.release("v1.1.0", {".github/workflows/checks.yml": TEMPLATE_CHECKS
                                      .replace("'validate'", "'validate --strict'")})
        result = sync_world.run_sync()
        decision = next(d for d in result.decisions if d.path == ".github/workflows/checks.yml")
        assert decision.outcome == "conflict"
        assert sync_world.text(".github/workflows/checks.yml") == mine, "a conflict must not touch the file"
        assert "<<<<<<<" not in sync_world.text(".github/workflows/checks.yml")
        assert "+      lint-command: 'validate --strict'" in decision.diff
        assert ".github/workflows/checks.yml" in sync_world.lock().pending
        assert "The template's change" in result.report


TEMPLATE_CHECKS = (
    "name: checks\n"
    "# The commands your project builds with.\n"
    "jobs:\n"
    "  ci:\n"
    "    with:\n"
    "      lint-command: 'validate'\n"
)


class TestNothingIsLostAcrossSyncs:
    """The failure the history replay found, played out in full."""

    def make_conflict(self, world):
        world.generate()
        world.owner({".github/workflows/checks.yml": TEMPLATE_CHECKS.replace("'validate'", "'mine'")})
        world.release("v1.1.0", {
            ".github/workflows/checks.yml": TEMPLATE_CHECKS.replace("'validate'", "'validate --strict'"),
            "scripts/tool.py": "print('v1.1')\n",
        })

    def test_merging_a_pull_request_with_a_conflict_in_it_does_not_lose_the_change(self, sync_world):
        self.make_conflict(sync_world)
        first = sync_world.run_sync()  # merged with the conflict unresolved
        assert sync_world.outcomes(first)[".github/workflows/checks.yml"] == "conflict"
        assert sync_world.outcomes(first)["scripts/tool.py"] == "updated"
        # The next release does not touch checks.yml at all. A whole-repository
        # baseline would now sit past the conflicted change and never see it again.
        sync_world.release("v1.2.0", {"scripts/tool.py": "print('v1.2')\n"})
        second = sync_world.run_sync()
        assert sync_world.outcomes(second)[".github/workflows/checks.yml"] == "conflict", (
            "the conflicted change was dropped once its pull request merged"
        )
        assert ".github/workflows/checks.yml" in sync_world.lock().pending
        assert "validate --strict" in next(
            d.diff for d in second.decisions if d.path == ".github/workflows/checks.yml")

    def test_the_baseline_does_not_move_until_the_change_lands(self, sync_world):
        self.make_conflict(sync_world)
        before = sync_world.lock().files[".github/workflows/checks.yml"].blob
        sync_world.run_sync()
        assert sync_world.lock().files[".github/workflows/checks.yml"].blob == before

    def test_applying_the_change_by_hand_resolves_it(self, sync_world):
        self.make_conflict(sync_world)
        sync_world.run_sync()
        sync_world.owner({".github/workflows/checks.yml": TEMPLATE_CHECKS.replace(
            "'validate'", "'mine --strict'")})
        # The owner kept their own command and took the template's flag. That
        # is not byte-identical to either side, so it must still conflict:
        # only the owner can say they are done with it.
        third = sync_world.run_sync()
        assert sync_world.outcomes(third)[".github/workflows/checks.yml"] == "conflict"
        sync_world.owner({".github/workflows/checks.yml": TEMPLATE_CHECKS.replace(
            "'validate'", "'validate --strict'")})
        fourth = sync_world.run_sync()
        assert sync_world.outcomes(fourth)[".github/workflows/checks.yml"] == "current"
        assert not sync_world.lock().pending

    def test_switching_the_file_off_ends_the_question(self, sync_world):
        self.make_conflict(sync_world)
        sync_world.run_sync()
        sync_world.owner({".github/template-sync": sync_world.text(".github/template-sync").replace(
            "\n/.github/workflows/checks.yml\n", "\n#/.github/workflows/checks.yml\n")})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)[".github/workflows/checks.yml"] == "not-synced"
        assert not sync_world.lock().pending


class TestTheOwnersChoicesHold:
    def test_a_deleted_file_is_switched_off_and_never_reinstalled(self, sync_world):
        sync_world.generate()
        sync_world.owner({"scripts/tool.py": None})
        sync_world.release("v1.1.0", {"scripts/tool.py": "print('v1.1')\n"})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["scripts/tool.py"] == "owner-deleted"
        assert sync_world.read("scripts/tool.py") is None
        assert entry_on(sync_world, "#/scripts/tool.py"), "the list must show the path switched off"
        assert sync_world.lock().files["scripts/tool.py"].deleted
        sync_world.release("v1.2.0", {"scripts/tool.py": "print('v1.2')\n"})
        again = sync_world.run_sync()
        assert sync_world.outcomes(again)["scripts/tool.py"] == "not-synced"
        assert sync_world.read("scripts/tool.py") is None

    def test_a_deleted_file_stays_deleted_when_the_template_flips_its_default(self, sync_world):
        """A random history found this: off by default, then on again, restored a deleted file."""
        sync_world.generate()
        sync_world.owner({"scripts/tool.py": None})
        sync_world.run_sync()
        assert entry_on(sync_world, "#/scripts/tool.py")
        listed = sync_world.text(".github/template-sync")
        template_list = (sync_world.template / ".github/template-sync").read_text(encoding="utf-8")
        sync_world.release("v1.1.0", {".github/template-sync": template_list.replace(
            "\n/scripts/tool.py\n", "\n#/scripts/tool.py\n")})
        sync_world.run_sync()
        sync_world.release("v1.2.0", {".github/template-sync": template_list,
                                      "scripts/tool.py": "print('tool, revised')\n"})
        result = sync_world.run_sync()
        assert sync_world.read("scripts/tool.py") is None, "a deleted file came back"
        assert entry_on(sync_world, "#/scripts/tool.py")
        assert "scripts/tool.py" not in {d.path for d in result.decisions if d.write is not None}
        assert listed  # the owner never touched the line

    def test_switching_a_deleted_file_back_on_restores_it(self, sync_world):
        sync_world.generate()
        sync_world.owner({"scripts/tool.py": None})
        sync_world.run_sync()
        sync_world.owner({".github/template-sync": sync_world.text(".github/template-sync").replace(
            "#/scripts/tool.py", "/scripts/tool.py")})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["scripts/tool.py"] == "restored"
        assert sync_world.text("scripts/tool.py") == "print('tool')\n"
        assert not sync_world.lock().files["scripts/tool.py"].deleted

    def test_a_path_switched_off_ignores_the_template_until_switched_on(self, sync_world):
        sync_world.generate()
        sync_world.owner({
            "docs/guide.md": sync_world.text("docs/guide.md") + "\nMine.\n",
            ".github/template-sync": sync_world.text(".github/template-sync").replace(
                "\n/docs/guide.md\n", "\n#/docs/guide.md\n"),
        })
        sync_world.release("v1.1.0", {"docs/guide.md": "# Guide, improved\n\n"
                                      "Built with ❤️ by [@tannergolden](https://github.com/tannergolden).\n"})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["docs/guide.md"] == "not-synced"
        assert sync_world.text("docs/guide.md").startswith("# Guide\n")
        assert entry_on(sync_world, "#/docs/guide.md"), "the owner's choice must survive the redraw"
        sync_world.owner({".github/template-sync": sync_world.text(".github/template-sync").replace(
            "#/docs/guide.md", "/docs/guide.md")})
        back = sync_world.run_sync()
        assert sync_world.outcomes(back)["docs/guide.md"] == "merged"
        text = sync_world.text("docs/guide.md")
        assert "# Guide, improved" in text and "Mine." in text, "switching back on must merge, not overwrite"

    def test_a_rule_of_the_owners_wins_over_the_templates_defaults(self, sync_world):
        sync_world.generate()
        sync_world.owner({".github/template-sync": sync_world.text(".github/template-sync") + "!/docs/**\n"})
        sync_world.release("v1.1.0", {"docs/guide.md": "# Changed\n"})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["docs/guide.md"] == "not-synced"
        assert "!/docs/**" in sync_world.text(".github/template-sync").splitlines()

    def test_a_file_left_to_the_owner_can_be_switched_on(self, sync_world):
        sync_world.generate()
        sync_world.owner({".github/template-sync": sync_world.text(".github/template-sync").replace(
            "#/README.md", "/README.md")})
        sync_world.release("v1.1.0", {"README.md": "# Template\n\nReplace this README, please.\n"})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["README.md"] == "updated"

    def test_files_the_template_never_shipped_are_never_touched(self, sync_world):
        sync_world.generate()
        sync_world.owner({"src/main.go": "package main\n", "docs/mine.md": "# Mine\n"})
        sync_world.owner({".github/template-sync": sync_world.text(".github/template-sync") + "/src/**\n/docs/**\n"})
        sync_world.release("v1.1.0", {"docs/guide.md": "# Changed\n"})
        result = sync_world.run_sync()
        assert "src/main.go" not in sync_world.outcomes(result)
        assert sync_world.text("src/main.go") == "package main\n"
        assert sync_world.text("docs/mine.md") == "# Mine\n"

    def test_a_yours_file_is_never_touched_by_default(self, sync_world):
        sync_world.generate()
        sync_world.owner({"README.md": "# Widget\n"})
        sync_world.release("v1.1.0", {"README.md": "# Template, rewritten\n", "LICENSE": "changed\n"})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["README.md"] == "not-synced"
        assert sync_world.text("README.md") == "# Widget\n"


class TestWorkflowFiles:
    def test_without_a_token_they_wait_and_nothing_is_lost(self, sync_world):
        sync_world.generate()
        sync_world.release("v1.1.0", {".github/workflows/checks.yml": TEMPLATE_CHECKS + "# more\n",
                                      "scripts/tool.py": "print('v1.1')\n"})
        result = sync_world.run_sync(workflow_files=False)
        outcomes = sync_world.outcomes(result)
        assert outcomes[".github/workflows/checks.yml"] == "deferred"
        assert outcomes["scripts/tool.py"] == "updated"
        assert sync_world.text(".github/workflows/checks.yml") == TEMPLATE_CHECKS
        assert sync_world.lock().pending[".github/workflows/checks.yml"]["reason"] == "needs a token"
        later = sync_world.run_sync(workflow_files=True)
        assert sync_world.outcomes(later)[".github/workflows/checks.yml"] == "updated"
        assert not sync_world.lock().pending

    def test_a_new_workflow_waits_too(self, sync_world):
        sync_world.generate()
        list_text = sync_world.text(".github/template-sync").replace(
            "/.github/workflows/checks.yml\n", "/.github/workflows/checks.yml\n/.github/workflows/new.yml\n")
        sync_world.release("v1.1.0", {".github/workflows/new.yml": "name: new\n", ".github/template-sync": list_text})
        result = sync_world.run_sync(workflow_files=False)
        assert sync_world.outcomes(result)[".github/workflows/new.yml"] == "deferred"
        assert sync_world.read(".github/workflows/new.yml") is None


class TestMoves:
    def rename(self, world, old, new):
        """What `git mv` in the template does: same content, same mode, new path."""
        text = world.text(".github/template-sync").replace(f"/{old}\n", f"/{new}\n")
        content = (world.template / old).read_bytes()
        mode = "100755" if os.access(world.template / old, os.X_OK) else "100644"
        world.release("v1.1.0", {old: None, new: content, ".github/template-sync": text}, {new: mode})

    def test_an_untouched_file_moves(self, sync_world):
        sync_world.generate()
        self.rename(sync_world, "scripts/tool.py", "bin/tool.py")
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["scripts/tool.py"] == "moved"
        assert sync_world.read("scripts/tool.py") is None
        assert sync_world.text("bin/tool.py") == "print('tool')\n"
        assert os.access(sync_world.repo / "bin/tool.py", os.X_OK)

    def test_the_owners_edits_move_with_it(self, sync_world):
        sync_world.generate()
        sync_world.owner({"scripts/tool.py": "print('tool')\nprint('mine')\n"})
        self.rename(sync_world, "scripts/tool.py", "bin/tool.py")
        sync_world.run_sync()
        assert sync_world.text("bin/tool.py") == "print('tool')\nprint('mine')\n"
        assert sync_world.read("scripts/tool.py") is None

    def test_a_deleted_file_does_not_come_back_under_its_new_name(self, sync_world):
        sync_world.generate()
        sync_world.owner({"scripts/tool.py": None})
        sync_world.run_sync()
        self.rename(sync_world, "scripts/tool.py", "bin/tool.py")
        sync_world.run_sync()
        assert sync_world.read("bin/tool.py") is None
        assert entry_on(sync_world, "#/bin/tool.py"), "the owner's switch-off must follow the move"

    def test_a_file_deleted_while_the_template_moved_it_stays_deleted(self, sync_world):
        """The deletion and the move land in the same sync: neither knew of the other."""
        sync_world.generate()
        self.rename(sync_world, "scripts/tool.py", "bin/tool.py")
        sync_world.owner({"scripts/tool.py": None})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["bin/tool.py"] == "owner-deleted"
        assert sync_world.read("bin/tool.py") is None and sync_world.read("scripts/tool.py") is None
        assert entry_on(sync_world, "#/bin/tool.py")

    def test_an_opt_out_follows_the_file(self, sync_world):
        sync_world.generate()
        sync_world.owner({".github/template-sync": sync_world.text(".github/template-sync").replace(
            "\n/scripts/tool.py\n", "\n#/scripts/tool.py\n")})
        self.rename(sync_world, "scripts/tool.py", "bin/tool.py")
        result = sync_world.run_sync()
        assert sync_world.read("bin/tool.py") is None, "a file the owner switched off came back under a new name"
        assert sync_world.text("scripts/tool.py") == "print('tool')\n"
        assert "bin/tool.py" not in {d.path for d in result.decisions if d.write is not None}


class TestAMoveThatLeavesANewFileBehind:
    """The template moves a file and, in the same release, puts a new one where it was.

    Git sees no rename there - the source still exists - so the move used to
    go unnoticed, and a file the owner had deleted came back under its new
    name. A random history found it; each case is pinned here.
    """

    FRESH = "print('a new tool, in the old place')\nprint('unrelated to the one that moved')\n"

    def replace_move(self, world, old="scripts/tool.py", new="bin/tool.py"):
        text = world.text(".github/template-sync")
        content = (world.template / old).read_bytes()
        mode = "100755" if os.access(world.template / old, os.X_OK) else "100644"
        listed = text.replace(f"/{old}\n", f"/{old}\n/{new}\n") if f"/{old}\n" in text else text
        world.release("v1.1.0", {old: self.FRESH, new: content, ".github/template-sync": listed}, {new: mode})

    def test_an_edited_file_is_never_taken_from_its_owner(self, sync_world):
        # Content cannot tell this from a rewrite and a copy, so the old path
        # is merged as itself - here it conflicts, untouched - and the new
        # path arrives as the template has it.
        sync_world.generate()
        sync_world.owner({"scripts/tool.py": "print('tool')\nprint('mine')\n"})
        self.replace_move(sync_world)
        result = sync_world.run_sync()
        outcomes = sync_world.outcomes(result)
        assert outcomes["scripts/tool.py"] == "conflict" and outcomes["bin/tool.py"] == "added"
        assert sync_world.text("scripts/tool.py") == "print('tool')\nprint('mine')\n", "the owner's file stays"
        assert sync_world.text("bin/tool.py") == "print('tool')\n"

    def test_an_untouched_file_takes_the_new_one_and_the_moved_one_arrives(self, sync_world):
        sync_world.generate()
        self.replace_move(sync_world)
        outcomes = sync_world.outcomes(sync_world.run_sync())
        assert outcomes["scripts/tool.py"] == "updated" and outcomes["bin/tool.py"] == "added"
        assert sync_world.text("scripts/tool.py") == self.FRESH
        assert sync_world.text("bin/tool.py") == "print('tool')\n"
        assert not sync_world.run_sync().changed

    def test_a_deleted_file_does_not_come_back_when_its_old_path_is_reused(self, sync_world):
        sync_world.generate()
        sync_world.owner({"scripts/tool.py": None})
        sync_world.run_sync()
        self.replace_move(sync_world)
        result = sync_world.run_sync()
        assert sync_world.read("bin/tool.py") is None, "the deleted file came back under its new name"
        assert entry_on(sync_world, "#/bin/tool.py")
        assert "bin/tool.py" not in {d.path for d in result.decisions if d.write is not None}

    def test_a_switched_off_file_does_not_come_back_when_its_old_path_is_reused(self, sync_world):
        sync_world.generate()
        sync_world.owner({".github/template-sync": sync_world.text(".github/template-sync").replace(
            "\n/scripts/tool.py\n", "\n#/scripts/tool.py\n")})
        self.replace_move(sync_world)
        sync_world.run_sync()
        assert sync_world.read("bin/tool.py") is None
        assert sync_world.text("scripts/tool.py") == "print('tool')\n", "a switched-off file is never touched"

    def test_a_file_deleted_in_the_same_turn_comes_back_under_neither_name(self, sync_world):
        # Either reading of the pair - a move, or a rewrite and a copy - has
        # one of these paths holding what the owner deleted, so neither is
        # written; both are switched off, and say so.
        sync_world.generate()
        self.replace_move(sync_world)
        sync_world.owner({"scripts/tool.py": None})
        result = sync_world.run_sync()
        outcomes = sync_world.outcomes(result)
        assert outcomes["bin/tool.py"] == "owner-deleted" and outcomes["scripts/tool.py"] == "owner-deleted"
        assert sync_world.read("bin/tool.py") is None and sync_world.read("scripts/tool.py") is None
        assert not sync_world.run_sync().changed

    def test_a_rewrite_with_nothing_like_it_elsewhere_is_not_a_move(self, sync_world):
        sync_world.generate()
        text = sync_world.text(".github/template-sync").replace("/scripts/tool.py\n", "/scripts/tool.py\n/bin/other.py\n")
        sync_world.release("v1.1.0", {"scripts/tool.py": self.FRESH, "bin/other.py": "x = 1\n",
                                      ".github/template-sync": text})
        outcomes = sync_world.outcomes(sync_world.run_sync())
        assert outcomes["scripts/tool.py"] == "updated" and outcomes["bin/other.py"] == "added"

    def test_a_copy_is_not_a_move(self, sync_world):
        sync_world.generate()
        text = sync_world.text(".github/template-sync").replace("/scripts/tool.py\n", "/scripts/tool.py\n/bin/tool.py\n")
        sync_world.release("v1.1.0", {"scripts/tool.py": "print('tool')\nprint('more')\n",
                                      "bin/tool.py": "print('tool')\n", ".github/template-sync": text})
        outcomes = sync_world.outcomes(sync_world.run_sync())
        assert outcomes["scripts/tool.py"] == "updated" and outcomes["bin/tool.py"] == "added"
        assert sync_world.text("scripts/tool.py") == "print('tool')\nprint('more')\n"


class TestSafety:
    def test_a_lock_naming_another_template_stops_the_run(self, sync_world):
        sync_world.generate()
        with pytest.raises(sync_world.sync.SyncError, match="agree"):
            sync_world.sync.run(sync_world.repo, sync_world.template, template="someone/else")

    def test_a_corrupt_lock_stops_the_run_and_writes_nothing(self, sync_world):
        sync_world.generate()
        sync_world.owner({".github/template-sync.lock": "{not json"})
        with pytest.raises(sync_world.sync.SyncError, match="not valid JSON"):
            sync_world.run_sync()
        assert sync_world.clean()

    def test_an_unsafe_path_in_the_lock_stops_the_run(self, sync_world):
        sync_world.generate()
        lock = json.loads(sync_world.text(".github/template-sync.lock"))
        lock["files"]["../escape"] = lock["files"]["scripts/tool.py"]
        sync_world.owner({".github/template-sync.lock": json.dumps(lock)})
        with pytest.raises(sync_world.sync.SyncError, match="unsafe"):
            sync_world.run_sync()

    def test_a_rewritten_template_history_is_reported_not_guessed(self, sync_world):
        sync_world.generate()
        sync_world.owner({"scripts/tool.py": "print('mine')\n"})
        lock = json.loads(sync_world.text(".github/template-sync.lock"))
        lock["files"]["scripts/tool.py"]["blob"] = "0" * 40
        sync_world.owner({".github/template-sync.lock": json.dumps(lock)})
        result = sync_world.run_sync()
        decision = next(d for d in result.decisions if d.path == "scripts/tool.py")
        assert decision.outcome == "conflict" and "no longer has" in decision.detail
        assert sync_world.text("scripts/tool.py") == "print('mine')\n"

    def test_a_symlink_here_is_never_written_over(self, sync_world):
        sync_world.generate()
        (sync_world.repo / "scripts/tool.py").unlink()
        os.symlink("../README.md", sync_world.repo / "scripts/tool.py")
        sync_world.commit(sync_world.repo, "a symlink of the owner's")
        sync_world.release("v1.1.0", {"scripts/tool.py": "print('v1.1')\n"})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["scripts/tool.py"] == "conflict"
        assert os.path.islink(sync_world.repo / "scripts/tool.py")
        assert sync_world.text("README.md") == "# Template\n\nReplace this README.\n"

    def test_a_file_where_the_template_needs_a_directory_is_a_conflict(self, sync_world):
        sync_world.generate()
        sync_world.owner({"bin": "an owner's file named bin\n"})
        list_text = sync_world.text(".github/template-sync").replace(
            "/scripts/tool.py\n", "/scripts/tool.py\n/bin/run.sh\n")
        sync_world.release("v1.1.0", {"bin/run.sh": "echo hi\n", ".github/template-sync": list_text})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["bin/run.sh"] == "conflict"
        assert sync_world.text("bin") == "an owner's file named bin\n"

    def test_the_sentinel_is_never_written_even_if_switched_on(self, sync_world):
        sync_world.generate()
        list_text = sync_world.text(".github/template-sync").replace(
            "#/.github/TEMPLATE_INIT", "/.github/TEMPLATE_INIT")
        sync_world.release("v1.1.0", {".github/template-sync": list_text,
                                      ".github/TEMPLATE_INIT": "changed\n"})
        sync_world.run_sync()
        assert sync_world.read(".github/TEMPLATE_INIT") is None

    def test_a_template_without_a_list_is_an_error(self, sync_world):
        sync_world.generate()
        sync_world.release("v1.1.0", {".github/template-sync": None})
        with pytest.raises(sync_world.sync.SyncError, match="publishes no"):
            sync_world.run_sync()

    def test_a_binary_file_changed_on_both_sides_is_a_conflict(self, sync_world):
        list_text = TEMPLATE_FILES_LIST_WITH("/assets/logo.bin")
        sync_world.release("v1.0.1", {"assets/logo.bin": b"\x00\x01base", ".github/template-sync": list_text})
        sync_world.generate()
        sync_world.owner({"assets/logo.bin": b"\x00\x01mine"})
        sync_world.release("v1.1.0", {"assets/logo.bin": b"\x00\x01template"})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["assets/logo.bin"] == "conflict"
        assert sync_world.read("assets/logo.bin") == b"\x00\x01mine"


def TEMPLATE_FILES_LIST_WITH(key: str) -> str:
    from conftest import TEMPLATE_LIST

    return TEMPLATE_LIST.replace("/scripts/tool.py\n", f"/scripts/tool.py\n{key}\n")


class TestARepositoryWithoutALock:
    def test_the_lock_is_recovered_through_inits_own_rewrite(self, sync_world, monkeypatch):
        monkeypatch.setenv("GITHUB_REPOSITORY_OWNER", "janedoe")
        monkeypatch.setenv("GITHUB_REPOSITORY", "janedoe/widget")
        sync_world.generate(lock=False)
        # The root commit is init's amend, so rewritten files hold blobs the
        # template never had. Bootstrap must find them by rewriting.
        result = sync_world.sync.run(sync_world.repo, sync_world.template, template="tannergolden/path",
                                     name="Jane Doe")
        assert result.changed, "the recovered lock should be proposed"
        lock = sync_world.lock()
        template = sync_world.sync.tree(sync_world.template, "v1")
        assert lock.files["docs/guide.md"].blob == template["docs/guide.md"].sha
        assert lock.files["LICENSE"].blob == template["LICENSE"].sha
        assert {d.outcome for d in result.decisions} <= {"unchanged", "not-synced", "current"}


class TestTheCommandLine:
    def run_cli(self, world, run_script, *args):
        env = {**SYNC_ENV, "GITHUB_REPOSITORY": "janedoe/widget", "GITHUB_REPOSITORY_OWNER": "janedoe"}
        return run_script("scripts/template-sync.py", cwd=world.repo, env=env) if not args else \
            world  # placeholder, replaced below

    def test_run_reports_through_actions_outputs(self, sync_world, run_shell):
        sync_world.generate()
        sync_world.owner({".github/workflows/checks.yml": TEMPLATE_CHECKS.replace("'validate'", "'mine'")})
        sync_world.release("v1.1.0", {".github/workflows/checks.yml": TEMPLATE_CHECKS.replace(
            "'validate'", "'theirs'"), "scripts/tool.py": "print('v1.1')\n"})
        script = f'exec python3 "{sync_world.sync.__file__}" run --template-dir "{sync_world.template}"'
        result = run_shell(script, cwd=sync_world.repo, env=SYNC_ENV)
        assert result.returncode == 0, result.output
        assert result.outputs["changed"] == "true"
        assert result.outputs["clean"] == "false"
        assert result.outputs["pending"] == "1"
        assert result.outputs["version"] == "v1.1.0"
        assert "::warning file=.github/workflows/checks.yml" in result.output
        assert "Needs you" in result.summary
        commit_check = load_script("scripts/commit-check.py")
        types = list(commit_check.DEFAULT_TYPES) if not isinstance(commit_check.DEFAULT_TYPES, str) else \
            [t.strip() for t in commit_check.DEFAULT_TYPES.split(",")]
        for title in (result.outputs["pr-title"], result.outputs["commit-title"]):
            assert commit_check.problems_for(title, types, 100) == [], title

    def test_run_refuses_a_dirty_working_tree(self, sync_world, run_shell):
        sync_world.generate()
        (sync_world.repo / "scripts/tool.py").write_text("uncommitted\n")
        script = f'exec python3 "{sync_world.sync.__file__}" run --template-dir "{sync_world.template}"'
        result = run_shell(script, cwd=sync_world.repo, env=SYNC_ENV)
        assert result.returncode == 1
        assert "uncommitted changes" in result.output

    def test_a_skip_is_a_notice_and_a_success(self, sync_world, run_shell):
        sync_world.generate()
        script = (f'exec python3 "{sync_world.sync.__file__}" run --template-dir "{sync_world.template}" '
                  "--ref v7")
        result = run_shell(script, cwd=sync_world.repo, env=SYNC_ENV)
        assert result.returncode == 0
        assert "::notice title=Template sync::" in result.output
        assert result.outputs["changed"] == "false"

    def test_lock_prints_a_lock_that_reads_back(self, sync_world, run_shell):
        sync_world.generate(lock=False)
        script = (f'exec python3 "{sync_world.sync.__file__}" lock --template tannergolden/path '
                  "--owner janedoe --repository janedoe/widget --name 'Jane Doe' --year 2027")
        result = run_shell(script, cwd=sync_world.repo, env=SYNC_ENV)
        assert result.returncode == 0, result.output
        lock = sync_world.sync.load_lock(result.stdout)
        assert lock.identity.year == 2027 and "docs/guide.md" in lock.files


class TestTheTemplatesOwnCheck:
    def check(self, world):
        return world.sync.check(world.template)

    def test_the_default_template_passes(self, sync_world):
        assert self.check(sync_world) == []

    def test_an_unnamed_file_fails_and_says_which_line_to_add(self, sync_world):
        sync_world.release("v1.0.1", {"docs/forgotten.md": "# Forgotten\n"})
        problems = self.check(sync_world)
        assert any("docs/forgotten.md is shipped but not named" in p and "`/docs/forgotten.md`" in p
                   for p in problems), problems

    def test_a_stale_entry_fails(self, sync_world):
        sync_world.release("v1.0.1", {"docs/guide.md": None})
        assert any("does not ship" in p for p in self.check(sync_world))

    def test_an_unanchored_entry_fails(self, sync_world):
        sync_world.release("v1.0.1", {".github/template-sync": TEMPLATE_FILES_LIST_WITH("README.md")
                                      .replace("#/README.md\n", "")})
        assert any("not anchored" in p for p in self.check(sync_world))

    def test_the_sentinel_switched_on_fails(self, sync_world):
        from conftest import TEMPLATE_LIST

        sync_world.release("v1.0.1", {".github/template-sync": TEMPLATE_LIST.replace(
            "#/.github/TEMPLATE_INIT", "/.github/TEMPLATE_INIT")})
        assert any("re-run initialisation" in p for p in self.check(sync_world))

    def test_rules_under_the_marker_fail(self, sync_world):
        from conftest import TEMPLATE_LIST

        sync_world.release("v1.0.1", {".github/template-sync": TEMPLATE_LIST + "!/docs/**\n"})
        assert any("That section is the owner's" in p for p in self.check(sync_world))

    def test_a_duplicate_entry_fails(self, sync_world):
        from conftest import TEMPLATE_LIST

        sync_world.release("v1.0.1", {".github/template-sync": TEMPLATE_LIST.replace(
            "/docs/guide.md\n", "/docs/guide.md\n/docs/guide.md\n")})
        assert any("more than once" in p for p in self.check(sync_world))


class TestIdempotence:
    def test_a_second_run_after_merging_changes_nothing(self, sync_world):
        sync_world.generate()
        sync_world.owner({"docs/guide.md": sync_world.text("docs/guide.md") + "\nMine.\n"})
        sync_world.release("v1.1.0", {"docs/guide.md": "# Guide v2\n\n"
                                      "Built with ❤️ by [@tannergolden](https://github.com/tannergolden).\n",
                                      "scripts/tool.py": "print('v1.1')\n"})
        sync_world.run_sync()
        again = sync_world.run_sync()
        assert not again.changed
