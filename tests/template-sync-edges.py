# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The edges review and real use of template sync found, each pinned where it was found.

Every test here failed against the engine as it stood when the edge turned
up, and each names the promise it holds: an owner's edit is never taken from
them, a file they deleted comes back only when they ask, a choice they made
survives the template reshaping its list, nothing a sync starts is ever
abandoned, and a sync never goes backwards.

The last three classes come from the first repository generated for real,
tannergolden/markdown, played against the golden path template's next releases:
a machined index conflicted over rows nobody wrote, two additions to the end
of .gitignore conflicted, and a release that only forgot switched-off files
proposed a pull request that changed nothing but the lock. The one after them
holds the way out its owner needed for a line they had made their own.
"""

from __future__ import annotations

import os
import random
import shlex
import subprocess
import sys

import pytest
from conftest import ROOT, SYNC_ENV, TEMPLATE_LIST, load_script

sync = load_script(".github/scripts/template-sync.py")

# An unchanged line between the rewritten block and the owner's setting, as in
# any real file: git merges changes that do not touch, never ones that abut.
CHECKS = "".join(f"step-{i}: run {i}\n" for i in range(1, 11)) + "with:\n" + "lint-command: 'validate'\n"
REWRITTEN = "".join(f"stage-{i}: other {i}\n" for i in range(1, 11)) + "with:\n" + "lint-command: 'validate'\n"


def lines(world) -> list[str]:
    return world.text(".github/template-sync").splitlines()


def relist(world, edit) -> str:
    return edit((world.template / ".github/template-sync").read_text(encoding="utf-8"))


class TestAnEditIsNeverTakenFromItsOwner:
    """A rewrite and a copy look exactly like a move that left a new file behind."""

    def setup_world(self, world, owner_list=None):
        world.release("v1.0.1", {".github/workflows/checks.yml": CHECKS})
        world.generate()
        world.owner({".github/workflows/checks.yml": CHECKS.replace("'validate'", "'golangci-lint run'"),
                     **({".github/template-sync": owner_list(world.text(".github/template-sync"))}
                        if owner_list else {})})
        world.release("v1.1.0", {
            ".github/workflows/checks.yml": REWRITTEN,
            ".github/workflows/nightly.yml": CHECKS,
            ".github/template-sync": relist(world, lambda t: t.replace(
                "/.github/workflows/checks.yml\n",
                "/.github/workflows/checks.yml\n/.github/workflows/nightly.yml\n")),
        })

    def test_the_rewritten_file_merges_with_the_owners_edit_in_place(self, sync_world):
        self.setup_world(sync_world)
        result = sync_world.run_sync()
        outcomes = sync_world.outcomes(result)
        assert outcomes[".github/workflows/checks.yml"] == "merged"
        assert outcomes[".github/workflows/nightly.yml"] == "added"
        merged = sync_world.text(".github/workflows/checks.yml")
        assert "golangci-lint run" in merged and "stage-1: other 1" in merged
        assert sync_world.text(".github/workflows/nightly.yml") == CHECKS

    def test_a_switched_off_file_holds_its_copy_off_and_says_so(self, sync_world):
        self.setup_world(sync_world, lambda t: t.replace("\n/.github/workflows/checks.yml\n",
                                                         "\n#/.github/workflows/checks.yml\n"))
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)[".github/workflows/nightly.yml"] == "held-off"
        assert "#/.github/workflows/nightly.yml" in lines(sync_world)
        assert "nightly.yml" in result.report and "take the `#` away" in result.report
        assert not sync_world.run_sync().changed


class TestADeletedFileComesBackOnlyWhenAsked:
    def test_not_through_a_pattern_of_the_owners(self, sync_world):
        sync_world.generate()
        sync_world.owner({".github/template-sync": sync_world.text(".github/template-sync") + "/docs/**\n"})
        sync_world.owner({"docs/guide.md": None})
        sync_world.release("v1.1.0", {"scripts/tool.py": "print('v1.1')\n"})
        assert sync_world.outcomes(sync_world.run_sync())["docs/guide.md"] == "owner-deleted"
        sync_world.release("v1.2.0", {"docs/guide.md": "# Guide v1.2\n"})
        sync_world.run_sync()
        assert sync_world.read("docs/guide.md") is None

    def test_not_through_the_templates_folder_entry(self, sync_world):
        sync_world.release("v1.0.1", {".github/template-sync": TEMPLATE_LIST.replace("/docs/guide.md\n", "/docs/\n")})
        sync_world.generate()
        sync_world.owner({"docs/guide.md": None})
        sync_world.release("v1.1.0", {"scripts/tool.py": "print('v1.1')\n"})
        assert sync_world.outcomes(sync_world.run_sync())["docs/guide.md"] == "owner-deleted"
        sync_world.release("v1.2.0", {"docs/guide.md": "# Guide v1.2\n"})
        sync_world.run_sync()
        assert sync_world.read("docs/guide.md") is None, "a negation cannot reach under a folder pattern"

    def test_not_through_an_exact_rule_of_the_owners_which_is_switched_off_in_place(self, sync_world):
        sync_world.generate()
        sync_world.owner({".github/template-sync": sync_world.text(".github/template-sync") + "/README.md\n"})
        sync_world.owner({"README.md": None})
        sync_world.release("v1.1.0", {"scripts/tool.py": "print('v1.1')\n"})
        assert sync_world.outcomes(sync_world.run_sync())["README.md"] == "owner-deleted"
        assert lines(sync_world)[-1] == "#/README.md", "the owner's own rule is switched off where it stands"
        sync_world.release("v1.2.0", {"README.md": "# Template v1.2\n"})
        sync_world.run_sync()
        assert sync_world.read("README.md") is None

    def test_not_when_the_template_turns_an_opted_in_file_on_by_default(self, sync_world):
        sync_world.generate()
        sync_world.owner({".github/template-sync": sync_world.text(".github/template-sync").replace(
            "#/README.md", "/README.md")})
        sync_world.owner({"README.md": None})
        sync_world.release("v1.1.0", {"scripts/tool.py": "print('v1.1')\n"})
        sync_world.run_sync()
        sync_world.release("v1.2.0", {".github/template-sync": relist(
            sync_world, lambda t: t.replace("#/README.md", "/README.md"))})
        sync_world.run_sync()
        assert sync_world.read("README.md") is None

    def test_but_its_own_line_switched_back_on_restores_it(self, sync_world):
        sync_world.generate()
        sync_world.owner({".github/template-sync": sync_world.text(".github/template-sync") + "/docs/**\n"})
        sync_world.owner({"docs/guide.md": None})
        sync_world.run_sync()
        sync_world.owner({".github/template-sync": sync_world.text(".github/template-sync").replace(
            "#/docs/guide.md", "/docs/guide.md").replace("!/docs/guide.md\n", "")})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["docs/guide.md"] == "restored"
        assert sync_world.read("docs/guide.md") is not None


class TestAChoiceSurvivesTheTemplateReshapingItsList:
    def test_files_collapsed_into_a_folder_pattern(self, sync_world):
        sync_world.generate()
        frozen = sync_world.text("docs/guide.md")
        sync_world.owner({".github/template-sync": sync_world.text(".github/template-sync").replace(
            "\n/docs/guide.md\n", "\n#/docs/guide.md\n")})
        sync_world.release("v1.1.0", {"docs/guide.md": "# Guide, rewritten\n", ".github/template-sync": relist(
            sync_world, lambda t: t.replace("/docs/guide.md\n", "/docs/**\n"))})
        result = sync_world.run_sync()
        assert sync_world.text("docs/guide.md") == frozen, "a file the owner switched off was changed"
        assert "docs/guide.md" not in sync_world.sync.matched(sync_world.text(".github/template-sync"),
                                                             ["docs/guide.md"])
        assert "docs/guide.md" not in {d.path for d in result.decisions if d.write is not None}
        assert not sync_world.run_sync().changed

    def test_a_folder_pattern_spelled_out_into_files(self, sync_world):
        tlist = TEMPLATE_LIST.replace("/docs/guide.md\n", "/docs/**\n")
        sync_world.release("v1.0.1", {".github/template-sync": tlist})
        sync_world.generate()
        sync_world.owner({".github/template-sync": sync_world.text(".github/template-sync").replace(
            "\n/docs/**\n", "\n#/docs/**\n"), "docs/guide.md": "# Mine entirely\n"})
        sync_world.release("v1.1.0", {"docs/guide.md": "# Guide v1.1\n",
                                      ".github/template-sync": tlist.replace("/docs/**\n", "/docs/guide.md\n")})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result).get("docs/guide.md") in (None, "not-synced"), (
            "the owner's folder switch-off must hold the file off, not merely leave it in conflict")
        assert "!/docs/guide.md" in lines(sync_world), "the choice is written back by name"
        assert sync_world.text("docs/guide.md") == "# Mine entirely\n"
        assert not sync_world.run_sync().changed

    def test_a_switch_on_survives_too(self, sync_world):
        sync_world.release("v1.0.1", {".github/template-sync": TEMPLATE_LIST.replace("/docs/guide.md\n", "#/docs/guide.md\n")})
        sync_world.generate()
        sync_world.owner({".github/template-sync": sync_world.text(".github/template-sync").replace(
            "#/docs/guide.md", "/docs/guide.md")})
        sync_world.release("v1.1.0", {"docs/guide.md": "# Guide v1.1\n", ".github/template-sync": relist(
            sync_world, lambda t: t.replace("#/docs/guide.md\n", "#/docs/**\n"))})
        sync_world.run_sync()
        assert sync_world.text("docs/guide.md") == "# Guide v1.1\n"


class TestNothingASyncStartsIsAbandoned:
    def test_a_move_blocked_by_a_file_where_its_folder_goes_completes_once_cleared(self, sync_world):
        sync_world.generate()
        sync_world.owner({"bin": "an owner's file named bin\n"})
        sync_world.release("v1.1.0", {"scripts/tool.py": None, "bin/tool.py": "print('tool')\n",
                                      ".github/template-sync": relist(
                                          sync_world, lambda t: t.replace("/scripts/tool.py", "/bin/tool.py"))},
                           {"bin/tool.py": "100755"})
        assert sync_world.outcomes(sync_world.run_sync())["bin/tool.py"] == "conflict"
        assert "/scripts/tool.py" in lines(sync_world), "the old path waits, named"
        sync_world.owner({"bin": None})
        sync_world.run_sync()
        assert sync_world.read("scripts/tool.py") is None and sync_world.read("bin/tool.py") is not None

    def test_switching_off_a_conflicted_move_follows_the_file(self, sync_world):
        body = "".join(f"line {i}\n" for i in range(1, 11))
        sync_world.release("v1.0.1", {"docs/guide.md": "# Guide\n" + body})
        sync_world.generate()
        sync_world.owner({"docs/guide.md": "# My own guide\n" + body})
        sync_world.release("v1.1.0", {"docs/guide.md": None, "docs/moved/guide.md": "# Guide, revised\n" + body,
                                      ".github/template-sync": relist(
                                          sync_world, lambda t: t.replace("/docs/guide.md", "/docs/moved/guide.md"))})
        sync_world.run_sync()
        sync_world.owner({".github/template-sync": sync_world.text(".github/template-sync").replace(
            "\n/docs/guide.md", "\n#/docs/guide.md")})
        sync_world.run_sync()
        assert sync_world.read("docs/moved/guide.md") is None, "the owner kept theirs; no copy arrives"
        assert sync_world.text("docs/guide.md").startswith("# My own guide")

    def test_a_removal_made_while_the_list_was_missing_still_arrives(self, sync_world):
        sync_world.generate()
        sync_world.owner({".github/template-sync": None})
        sync_world.release("v1.1.0", {"scripts/tool.py": None, ".github/template-sync": relist(
            sync_world, lambda t: t.replace("/scripts/tool.py\n", ""))})
        sync_world.run_sync()
        assert sync_world.read(".github/template-sync") is not None
        assert sync_world.read("scripts/tool.py") is not None, "a restoring run syncs nothing else"
        sync_world.release("v1.2.0", {"docs/guide.md": "# Guide v1.2\n"})
        sync_world.run_sync()
        assert sync_world.read("scripts/tool.py") is None

    def test_a_file_kept_through_a_removal_stays_through_the_path_coming_and_going_again(self, sync_world):
        # Found by a random history: kept, re-added over, then removed again.
        with_old = TEMPLATE_LIST.replace("/scripts/tool.py\n", "/scripts/tool.py\n/scripts/old.py\n")
        sync_world.release("v1.0.1", {"scripts/old.py": "x = 1\n", ".github/template-sync": with_old})
        sync_world.generate()
        sync_world.owner({".github/template-sync": sync_world.text(".github/template-sync").replace(
            "\n/scripts/old.py\n", "\n#/scripts/old.py\n")})
        sync_world.release("v1.1.0", {"scripts/old.py": None, ".github/template-sync": TEMPLATE_LIST})
        assert sync_world.outcomes(sync_world.run_sync())["scripts/old.py"] == "not-synced"
        sync_world.release("v1.2.0", {"scripts/old.py": "x = 2\n", ".github/template-sync": with_old})
        assert sync_world.outcomes(sync_world.run_sync())["scripts/old.py"] == "conflict"
        assert "scripts/old.py" in sync_world.lock().pending
        sync_world.release("v1.3.0", {"scripts/old.py": None, ".github/template-sync": TEMPLATE_LIST})
        result = sync_world.run_sync()
        assert sync_world.read("scripts/old.py") == b"x = 1\n", "never recorded as the template's, so never removed"
        assert not sync_world.lock().pending, "and nothing waits on a file the template no longer ships"
        assert not sync_world.run_sync(write=False).changed, result.report

    def test_an_owner_rule_written_under_the_waiting_entries_is_kept(self):
        template = "# --- Kept current\n/a.md\n/docs/b.md\n\n# --- Your rules ---\n"
        drawn = sync.merge_list(template, template, template, waiting=["old.md"])
        mine = drawn.replace("/old.md\n", "/old.md\n!/docs/**\n")
        again = sync.merge_list(template, template, mine, waiting=["old.md"])
        assert "!/docs/**" in again.splitlines()
        assert "docs/b.md" not in sync.matched(again, ["docs/b.md"])


class TestASyncNeverGoesBackwards:
    def test_a_repository_generated_ahead_of_the_release_waits_for_one(self, sync_world):
        # "Use this template" copies the default branch, which can be ahead of v1.
        sync_world.put(sync_world.template, {"scripts/tool.py": "print('unreleased')\n", "scripts/new.py": "x = 1\n"})
        sync_world.commit(sync_world.template, "merged, not yet released")
        sync_world.git(sync_world.template, "tag", "-f", "v1", "v1.0.0")
        sync_world.repo.mkdir()
        sync_world.git(sync_world.repo, "init", "-q", "-b", "main")
        sync_world.git(sync_world.repo, "fetch", "-q", str(sync_world.template), "Development:refs/template/head")
        sync_world.git(sync_world.repo, "read-tree", "refs/template/head")
        sync_world.git(sync_world.repo, "checkout-index", "-a", "-f")
        sync_world.put(sync_world.repo, {".github/TEMPLATE_INIT": None})
        sync_world.commit(sync_world.repo, "Initial commit")
        lock = sync.generation_lock(sync_world.repo, template=sync_world.TEMPLATE,
                                    identity=sync.Identity("janedoe", "janedoe/widget", "Jane Doe", 2027))
        sync_world.put(sync_world.repo, {sync.LOCK_PATH: sync.dump_lock(lock)})
        sync_world.commit(sync_world.repo, "initialise")
        with pytest.raises(sync.Skip, match="already holds a newer version"):
            sync.run(sync_world.repo, sync_world.template, ref="v1")
        assert sync_world.text("scripts/tool.py") == "print('unreleased')\n"
        sync_world.release("v1.1.0", {"docs/guide.md": "# Guide v1.1\n"})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result).get("scripts/tool.py") in (None, "unchanged", "current")
        assert sync_world.text("scripts/tool.py") == "print('unreleased')\n"
        assert sync_world.read("scripts/new.py") is not None


class TestTheReportFitsAPullRequest:
    def test_a_long_report_is_cut_between_items_and_closes_nothing_open(self):
        decisions = [sync.Decision(f"docs/file-{i:03}.md", "conflict", detail="clash",
                                   diff="--- a\n+++ b\n" + "".join(f"+{'x' * 200} {j}\n" for j in range(60)))
                     for i in range(40)]
        report = sync.render_report(template="t/p", version="v1.1.0", previous="v1.0.0", decisions=decisions,
                                    list_changed=False)
        assert len(report) > sync.REPORT_LIMIT and "docs/file-039.md" in report, "the summary keeps everything"
        body = sync.pr_body(report)
        assert len(body) <= sync.REPORT_LIMIT
        assert body.count("<details>") == body.count("</details>")
        assert body.count("```") % 2 == 0
        assert "step summary lists every file" in body


class TestAPathThatCannotBeWritten:
    def test_a_name_that_is_not_utf8_is_unsafe(self):
        assert sync.unsafe(os.fsdecode(b"assets/caf\xe9.bin")) == "its name is not valid UTF-8"

    def test_it_is_skipped_rather_than_crashing_the_lock(self, sync_world, monkeypatch):
        name = os.fsdecode(b"assets/caf\xe9.bin")
        sync_world.release("v1.0.1", {name: b"\x00logo", ".github/template-sync":
                                      TEMPLATE_LIST.replace("/scripts/tool.py\n", "/scripts/tool.py\n/assets/**\n")})
        sync_world.generate()
        sync.dump_lock(sync_world.lock()).encode("utf-8")
        sync_world.release("v1.1.0", {"scripts/tool.py": "print('v1.1')\n"})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result).get(name) == "unsafe"


DOCS_README = (
    "# Docs\n\nThe template's introduction.\n\n"
    "<!-- AUTO-INDEX:BEGIN dir=. style=log -->\n<!-- AUTO-INDEX:END -->\n\n"
    "The template's closing words.\n"
)


def redraw(where) -> subprocess.CompletedProcess:
    """Every machined index in a tree, redrawn as Machined Indexes redraws it."""
    return subprocess.run([sys.executable, str(ROOT / ".github/scripts/update-doc-indexes.py"), "--write", "--tree"],
                          cwd=where, capture_output=True, text=True, check=False)


def checked(where) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / ".github/scripts/update-doc-indexes.py"), "--check", "--tree"],
                          cwd=where, capture_output=True, text=True, check=False)


def listed(*paths: str) -> str:
    """The template's list with more entries; one written `#/path` is listed switched off."""
    return TEMPLATE_LIST.replace("/docs/guide.md\n", "/docs/guide.md\n" + "".join(
        f"{p}\n" if p.startswith("#") else f"/{p}\n" for p in paths))


class TestAMachinedIndexIsNeverMerged:
    """Its rows are drawn from the tree, so only the prose around them merges."""

    def setup_world(self, world, template_files: dict, owner_files: dict, owner_redraws: bool = True):
        world.put(world.template, {"docs/README.md": DOCS_README, ".github/template-sync": listed("docs/README.md")})
        redraw(world.template)
        world.release("v1.0.1", {})
        world.generate()
        world.put(world.repo, owner_files)
        if owner_redraws:
            redraw(world.repo)
        world.commit(world.repo, "the owner's own documents, logged")
        world.put(world.template, template_files)
        redraw(world.template)
        world.release("v1.1.0", {})

    def test_an_owners_new_file_in_the_folder_never_conflicts_with_the_templates_edit(self, sync_world):
        self.setup_world(
            sync_world,
            {"docs/README.md": DOCS_README.replace("introduction.", "introduction, now longer."),
             "docs/new.md": "# New\n\nA document the template added.\n",
             ".github/template-sync": listed("docs/README.md", "docs/new.md")},
            {"docs/a-much-longer-name-of-the-owners-own.md": "# Mine\n\nThe owner's own document.\n"})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["docs/README.md"] == "updated"
        text = sync_world.text("docs/README.md")
        assert "introduction, now longer." in text
        assert "a-much-longer-name-of-the-owners-own.md" in text and "new.md" in text
        assert checked(sync_world.repo).returncode == 0, "the index must match the tree the sync left"
        assert "redrawn from the tree" in result.report
        assert not sync_world.run_sync(merge=False).changed

    def test_prose_both_sides_changed_is_still_a_conflict_and_left_byte_for_byte(self, sync_world):
        self.setup_world(
            sync_world,
            {"docs/README.md": DOCS_README.replace("introduction.", "introduction, the template's way."),
             "docs/new.md": "# New\n\nA document the template added.\n",
             ".github/template-sync": listed("docs/README.md", "docs/new.md")},
            {"docs/README.md": DOCS_README.replace("introduction.", "introduction, the owner's way."),
             "docs/mine.md": "# Mine\n\nThe owner's own document.\n"})
        before = sync_world.read("docs/README.md")
        result = sync_world.run_sync()
        decision = next(d for d in result.decisions if d.path == "docs/README.md")
        assert decision.outcome == "conflict"
        assert sync_world.read("docs/README.md") == before
        assert "the template's way" in decision.diff and "mine.md" not in decision.diff

    def test_a_marker_shown_in_a_fence_is_an_example_and_merges_as_text(self):
        example = (b"# Spec\n\n```markdown\n<!-- AUTO-INDEX:BEGIN dir=. style=log -->\n| row |\n"
                   b"<!-- AUTO-INDEX:END -->\n```\n")
        assert sync.masked("docs/Spec.md", example) == (example, [])
        assert sync.masked("docs/notes.txt", DOCS_README.encode()) == (DOCS_README.encode(), [])

    def test_a_dry_run_redraws_nothing(self, sync_world):
        self.setup_world(
            sync_world,
            {"docs/new.md": "# New\n\nA document the template added.\n",
             ".github/template-sync": listed("docs/README.md", "docs/new.md")},
            {"docs/mine.md": "# Mine\n\nThe owner's own document.\n"})
        sync_world.sync.run(sync_world.repo, sync_world.template, ref="v1", write=False)
        assert sync_world.clean()

    def test_the_workflows_folder_is_redrawn_only_with_a_token_that_can_write_it(self, sync_world):
        readme = "# Workflows\n\n<!-- AUTO-INDEX:BEGIN dir=. style=log fields=name,on -->\n<!-- AUTO-INDEX:END -->\n"
        sync_world.put(sync_world.template, {".github/workflows/README.md": readme, ".github/template-sync":
                                             listed(".github/workflows/README.md")})
        redraw(sync_world.template)
        sync_world.release("v1.0.1", {})
        sync_world.generate()
        sync_world.owner({"docs/guide.md": "# The owner's guide\n"})
        sync_world.put(sync_world.template, {".github/workflows/nightly.yml": "name: nightly\non:\n  schedule:\n",
                                             "scripts/tool.py": "print('v1.1')\n", ".github/template-sync": listed(
                                                 ".github/workflows/README.md", ".github/workflows/nightly.yml")})
        redraw(sync_world.template)
        sync_world.release("v1.1.0", {})
        before = sync_world.read(".github/workflows/README.md")
        result = sync_world.run_sync(workflow_files=False)
        assert sync_world.outcomes(result)[".github/workflows/nightly.yml"] == "deferred"
        assert sync_world.read(".github/workflows/README.md") == before


def sealed(rules: str, digest: str) -> str:
    """An AGENTS.md block sealed with a hash, as tannergolden/intelligence delivers one."""
    return f"<!-- INTELLIGENCE:BEGIN sha256:{digest * 64} -->\n\n## Constitution\n\n{rules}\n<!-- INTELLIGENCE:END -->\n"


def agents(intro: str, block: str, mine: str = "") -> bytes:
    return (f"# Agents\n\n{intro}\n\n{block}\n## Commands\n\n- make test\n{mine}").encode()


class TestASealedBlockIsNeverMerged:
    """A block another machine seals with its hash is that machine's to keep current."""

    def decide(self, base: bytes, target: bytes, ours: bytes):
        return sync.decide("AGENTS.md", sync.Side("100644", base), sync.Side("100644", target),
                           sync.Side("100644", ours), synced=True, was_deleted=False)

    def test_masking_takes_the_marker_with_it_and_refilling_puts_it_back(self):
        data = agents("Intro.", sealed("- SEC-001: Never.", "a"))
        text, rows = sync.masked("AGENTS.md", data)
        assert b"sha256:" not in text and b"SEC-001" not in text
        assert b"<!-- INTELLIGENCE:BEGIN -->" in text and b"<!-- INTELLIGENCE:END -->" in text
        assert rows[0][0] == b"sealed INTELLIGENCE"
        assert sync.refilled(text, rows) == data

    def test_two_releases_of_the_block_merge_the_prose_and_keep_the_repositorys_block(self):
        base = agents("The template's intro.", sealed("- SEC-001: First.", "a"))
        target = agents("The template's intro, now longer.", sealed("- SEC-001: Third.", "c"))
        ours = agents("The template's intro.", sealed("- SEC-001: Second.", "b"), "\n## Overrides\n\nNone.\n")
        decision = self.decide(base, target, ours)
        assert decision.outcome == "merged", decision.detail
        written = decision.write.data
        assert b"intro, now longer." in written and b"## Overrides" in written
        assert sealed("- SEC-001: Second.", "b").encode() in written
        assert b"Third" not in written and b"sha256:" + b"c" * 64 not in written

    def test_a_file_that_differs_only_in_its_block_is_current(self):
        base = agents("Intro.", sealed("- SEC-001: First.", "a"))
        target = agents("Intro.", sealed("- SEC-001: Third.", "c"))
        ours = agents("Intro.", sealed("- SEC-001: Second.", "b"))
        assert self.decide(base, target, ours).outcome in ("unchanged", "current")

    def test_a_sealed_marker_in_a_fence_is_an_example_and_merges_as_text(self):
        example = ("# Spec\n\n```markdown\n" + sealed("- X: Y.", "a") + "```\n").encode()
        assert sync.masked("docs/Spec.md", example) == (example, [])

    def test_an_unsealed_block_is_left_as_text(self):
        plain = b"# Notes\n\n<!-- INTELLIGENCE:BEGIN -->\nWritten by hand.\n<!-- INTELLIGENCE:END -->\n"
        assert sync.masked("docs/Notes.md", plain) == (plain, [])
        assert sync.refilled(plain) == plain


FOOTER = "---\n\n<div align=\"center\">\n\n[↑ Back to Top](#top)\n\n</div>\n"


def research(line: str = "- Reports go in docs/technical/research/.") -> str:
    """The section a template keeps in AGENTS.md, as the golden path template ships one."""
    return f"<!-- TEMPLATE-SYNC:BEGIN -->\n## Research\n\n{line}\n<!-- TEMPLATE-SYNC:END -->\n"


def shipped(section: str = "", *, footer: bool = True) -> bytes:
    """The template's AGENTS.md: its own empty sections, and the section it keeps."""
    return (f"# Agents\n\n## Commands\n\n<!-- How to build. -->\n\n## Where things live\n\n<!-- The folders. -->\n\n"
            f"{section + chr(10) if section else ''}## Gotchas\n\n" + (FOOTER if footer else "")).encode()


# An AGENTS.md the repository's own sync wrote and its owner filled in, long
# before the template shipped one: there is no baseline to merge it from.
OWNED = ("# Agents\n\n" + sealed("- SEC-001: Never.", "a") + "\n## Commands\n\n- make test\n\n"
         "## Where things live\n\n- src/: the code\n\n## Gotchas\n\n- The build is slow.\n\n" + FOOTER).encode()


class TestATemplatesSectionInAFileTheOwnerWrites:
    """A TEMPLATE-SYNC block is the template's; every other line of the file stays the owner's."""

    @staticmethod
    def side(data, sha):
        return None if data is None else sync.Side("100644", data, sha)

    def decide(self, base, target, ours, keep=False):
        return sync.decide("AGENTS.md", self.side(base, "base"), self.side(target, "target"),
                           self.side(ours, "ours"), synced=True, was_deleted=False, keep=keep)

    def test_a_file_with_no_baseline_takes_the_section_under_its_heading(self):
        decision = self.decide(None, shipped(research()), OWNED)
        assert decision.outcome == "shared", decision.detail
        assert "under `## Where things live`" in decision.detail
        written = decision.write.data.decode()
        assert written == OWNED.decode().replace("- src/: the code\n\n", "- src/: the code\n\n" + research() + "\n")
        assert decision.state.blob == "target"

    def test_taking_the_section_twice_changes_nothing(self):
        once = self.decide(None, shipped(research()), OWNED).write.data
        assert self.decide(shipped(research()), shipped(research()), once).outcome == "unchanged"
        assert self.decide(None, shipped(research()), once).outcome == "current"

    def test_the_templates_change_to_its_section_arrives(self):
        once = self.decide(None, shipped(research()), OWNED).write.data
        newer = shipped(research("- Reports go in docs/technical/research/, one per question."))
        decision = self.decide(shipped(research()), newer, once)
        assert decision.outcome == "shared" and b"one per question" in decision.write.data
        assert decision.write.data.replace(b", one per question", b"") == once

    def test_an_owners_change_to_the_section_is_a_conflict_that_writes_nothing(self):
        once = self.decide(None, shipped(research()), OWNED).write.data
        mine = once.replace(b"- Reports go", b"- Our reports go")
        decision = self.decide(shipped(research()), shipped(research("- Reports go elsewhere.")), mine)
        assert decision.outcome == "conflict" and decision.write is None and decision.state is None
        assert "+- Reports go elsewhere." in decision.diff

    def test_an_owners_change_stands_while_the_template_leaves_its_section_alone(self):
        mine = self.decide(None, shipped(research()), OWNED).write.data.replace(b"- Reports go", b"- Ours go")
        decision = self.decide(shipped(research()), shipped(research()), mine)
        assert decision.outcome == "unchanged" and decision.write is None

    def test_keep_mine_keeps_the_owners_section_and_says_what_the_template_changed(self):
        mine = self.decide(None, shipped(research()), OWNED).write.data.replace(b"- Reports go", b"- Ours go")
        decision = self.decide(shipped(research()), shipped(research("- Elsewhere.")), mine, keep=True)
        assert decision.outcome == "yours-kept" and decision.write is None
        assert "+- Elsewhere." in decision.diff

    def test_a_section_the_owner_took_out_stays_out(self):
        decision = self.decide(shipped(research()), shipped(research("- Moved on.")), OWNED)
        assert decision.outcome == "current" and decision.write is None

    def test_a_section_the_template_drops_goes_where_the_owner_left_it_alone(self):
        once = self.decide(None, shipped(research()), OWNED).write.data
        decision = self.decide(shipped(research()), shipped(), once)
        assert decision.outcome == "shared" and decision.write.data == OWNED
        mine = once.replace(b"- Reports go", b"- Ours go")
        assert self.decide(shipped(research()), shipped(), mine).write is None

    def test_a_file_the_template_stops_shipping_stays_the_owners(self):
        once = self.decide(None, shipped(research()), OWNED).write.data
        decision = self.decide(shipped(research()), None, once)
        assert decision.outcome == "kept" and not decision.delete and decision.write.data == OWNED

    def test_with_no_such_heading_the_section_goes_above_the_footer_or_at_the_end(self):
        bare = b"# Notes\n\nSome notes.\n\n" + FOOTER.encode()
        written = self.decide(None, shipped(research()), bare).write.data.decode()
        assert written == "# Notes\n\nSome notes.\n\n" + research() + "\n" + FOOTER
        plain = self.decide(None, shipped(research()), b"# Notes\n\nSome notes.\n").write.data.decode()
        assert plain == "# Notes\n\nSome notes.\n\n" + research()

    def test_markers_in_a_fence_are_an_example_and_the_file_merges_as_a_whole(self):
        example = ("# Spec\n\n```markdown\n" + research() + "```\n").encode()
        assert not sync.is_shared("docs/Spec.md", sync.Side("100644", example))
        assert sync.template_blocks(example) == []

    def test_a_repository_whose_agents_file_came_first_takes_the_section_in_a_real_sync(self, sync_world):
        sync_world.release("v1.0.1", {})
        sync_world.generate()
        sync_world.owner({"AGENTS.md": OWNED.decode()})
        sync_world.release("v1.1.0", {"AGENTS.md": shipped(research()).decode(), ".github/template-sync": listed(
            "AGENTS.md")})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["AGENTS.md"] == "shared"
        text = sync_world.text("AGENTS.md")
        assert research() in text and "- The build is slow." in text and "sha256:" + "a" * 64 in text
        assert not sync_world.run_sync().changed


    def test_a_heading_inside_another_machines_block_is_never_an_anchor(self):
        # The template's section follows the universal rules, whose last heading sits inside the sealed block.
        target = ("# Agents\n\n" + sealed("- SEC-001: Never.", "a") + "\n" + research() + "\n## Commands\n").encode()
        ours = ("# Agents\n\n" + sealed("- SEC-001: Never.", "b") + "\n## Commands\n\n- make test\n").encode()
        assert sync.anchor_of(target, b"TEMPLATE-SYNC") == b"# Agents"
        written = self.decide(None, target, ours).write.data.decode()
        assert written.index("<!-- INTELLIGENCE:END -->") < written.index("<!-- TEMPLATE-SYNC:BEGIN -->")


class TestAHiddenFolderIsSyncedWhereItLives:
    """A generated repository that keeps docs/ as .docs/ is synced there, never handed a new docs/."""

    @staticmethod
    def hide_docs(world):
        world.release("v1.0.1", {})
        world.generate()
        world.owner({"docs/guide.md": None, ".docs/guide.md": world.text("docs/guide.md")}, message="hide docs")

    def test_it_needs_the_hidden_folder_and_nothing_at_the_template_path(self):
        assert sync.hidden_folders([".docs/a.md", "README.md"], ["docs/a.md"]).pairs == (("docs", ".docs"),)
        assert sync.hidden_folders([".assets/logo.svg"], ["assets/logo.svg"]).pairs == (("assets", ".assets"),)
        assert sync.hidden_folders([".docs/a.md", "docs/b.md"], ["docs/a.md"]).pairs == ()
        assert sync.hidden_folders([".docs/a.md"], ["docs/a.md", ".docs/x.md"]).pairs == ()
        assert sync.hidden_folders(["docs/a.md"], ["docs/a.md"]).pairs == ()

    def test_a_change_and_a_new_file_land_in_the_hidden_folder(self, sync_world):
        self.hide_docs(sync_world)
        sync_world.release("v1.1.0", {"docs/guide.md": "# Guide v2\n", "docs/new.md": "# New\n",
                                      ".github/template-sync": listed("docs/new.md")})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["docs/guide.md"] == "updated"
        assert sync_world.outcomes(result)["docs/new.md"] == "added"
        assert sync_world.text(".docs/guide.md") == "# Guide v2\n" and sync_world.text(".docs/new.md") == "# New\n"
        assert not any(f.is_file() for f in (sync_world.repo / "docs").rglob("*"))
        assert "`.docs/new.md`" in result.report and "`docs/` in `.docs/`" in result.report
        assert "/docs/new.md" in sync_world.text(".github/template-sync")
        assert not sync_world.run_sync().changed

    def test_an_owners_edit_in_the_hidden_folder_merges(self, sync_world):
        self.hide_docs(sync_world)
        sync_world.owner({".docs/guide.md": sync_world.text(".docs/guide.md") + "\nMine.\n"})
        sync_world.release("v1.1.0", {"docs/guide.md": "# Guide, renamed\n\n" + sync_world.text(".docs/guide.md")
                                      .split("\n", 2)[2]})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["docs/guide.md"] == "merged"
        text = sync_world.text(".docs/guide.md")
        assert text.startswith("# Guide, renamed\n") and text.endswith("\nMine.\n")

    def test_a_file_deleted_from_the_hidden_folder_is_switched_off(self, sync_world):
        self.hide_docs(sync_world)
        sync_world.owner({".docs/guide.md": None, ".docs/notes.md": "# Notes\n"})
        sync_world.release("v1.1.0", {"docs/guide.md": "# Guide v2\n"})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["docs/guide.md"] == "owner-deleted"
        assert not any(f.is_file() for f in (sync_world.repo / "docs").rglob("*"))
        assert not (sync_world.repo / ".docs/guide.md").exists()

    def test_keep_mine_may_name_the_file_where_it_lives(self, sync_world):
        self.hide_docs(sync_world)
        mine = sync_world.text(".docs/guide.md").replace("# Guide", "# Our guide")
        sync_world.owner({".docs/guide.md": mine, ".github/template-sync": sync_world.text(".github/template-sync")
                          + "# keep mine: /.docs/guide.md\n"})
        sync_world.release("v1.1.0", {"docs/guide.md": sync_world.text(".docs/guide.md").replace(
            "# Our guide", "# The guide")})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["docs/guide.md"] == "yours-kept"
        assert sync_world.text(".docs/guide.md").startswith("# Our guide")


class TestTheTemplatesSectionsAreChecked:
    def check(self, world):
        return world.sync.check(world.template)

    def test_a_section_that_never_closes_is_named(self, sync_world):
        sync_world.release("v1.0.1", {"docs/guide.md": "# Guide\n\n<!-- TEMPLATE-SYNC:BEGIN -->\nOpen.\n"})
        assert any("docs/guide.md: `TEMPLATE-SYNC` opens and never closes" in p for p in self.check(sync_world))

    def test_two_sections_of_one_name_are_named(self, sync_world):
        twice = "# Guide\n\n" + research() + "\n" + research()
        sync_world.release("v1.0.1", {"docs/guide.md": twice})
        assert any("a second `TEMPLATE-SYNC`" in p for p in self.check(sync_world))

    def test_a_section_in_a_file_switched_off_is_named(self, sync_world):
        sync_world.release("v1.0.1", {"README.md": "# Template\n\n" + research()})
        assert any("README.md holds a TEMPLATE-SYNC block but is not kept current" in p
                   for p in self.check(sync_world))

    def test_a_well_formed_section_in_a_kept_file_passes(self, sync_world):
        sync_world.release("v1.0.1", {"docs/guide.md": "# Guide\n\n" + research()})
        assert self.check(sync_world) == []


def with_notes(*notes: str, text: str = TEMPLATE_LIST) -> str:
    """A template's list with notes of its own, above Your rules."""
    return text.replace("# --- Yours:", "".join(f"{note}\n" for note in notes) + "\n# --- Yours:", 1)


# A template derived from another, which took that template's section into an
# AGENTS.md whose every other rule is its own.
RULES = "# Agents\n\n## Rules\n\n- Notes open with frontmatter.\n\n## Gotchas\n\n- Profile/ is read-only.\n"
RULES_WITH_SECTION = RULES.replace("## Gotchas", research() + "\n## Gotchas")
NEWER_RULES = RULES_WITH_SECTION.replace("frontmatter.\n", "frontmatter.\n- Names are plain.\n")


class TestATemplateKeepsAFileWhole:
    """`# kept whole: /path`: the template's file, another template's section in it included."""

    @staticmethod
    def decide(base, target, ours, *, whole):
        def side(data, sha):
            return sync.Side("100644", data.encode(), sha)
        return sync.decide("AGENTS.md", side(base, "base"), side(target, "target"), side(ours, "ours"),
                           synced=True, was_deleted=False, whole=whole)

    def test_its_change_outside_the_section_merges_with_the_owners(self):
        mine = RULES_WITH_SECTION + "- My own gotcha.\n"
        decision = self.decide(RULES_WITH_SECTION, NEWER_RULES, mine, whole=True)
        assert decision.outcome == "merged", decision.detail
        assert decision.write.data.decode() == NEWER_RULES + "- My own gotcha.\n"

    def test_without_the_note_the_section_alone_is_the_templates(self):
        # The default every other template relies on: the rest is the owner's, so it never arrives.
        decision = self.decide(RULES_WITH_SECTION, NEWER_RULES, RULES_WITH_SECTION, whole=False)
        assert decision.outcome == "unchanged" and decision.write is None

    def test_only_the_templates_own_note_counts(self):
        text = with_notes("# kept whole: /AGENTS.md", "# kept whole: /docs/*.md") + "# kept whole: /docs/guide.md\n"
        assert sync.kept_whole(text) == {"AGENTS.md"}

    @pytest.mark.parametrize("noted", [True, False])
    def test_a_derived_templates_rules_keep_reaching_its_repositories(self, sync_world, noted):
        notes = ("# kept whole: /AGENTS.md",) if noted else ()
        sync_world.release("v1.0.1", {"AGENTS.md": RULES, ".github/template-sync": with_notes(
            *notes, text=listed("AGENTS.md"))})
        sync_world.generate()
        sync_world.release("v1.1.0", {"AGENTS.md": NEWER_RULES})
        result = sync_world.run_sync()
        text = sync_world.text("AGENTS.md")
        assert research() in text
        if noted:
            assert sync_world.outcomes(result)["AGENTS.md"] == "updated" and text == NEWER_RULES
        else:
            assert sync_world.outcomes(result)["AGENTS.md"] == "shared" and "- Names are plain." not in text
        assert not sync_world.run_sync().changed


class TestTheTemplatesNotesAreChecked:
    def check(self, world, *notes):
        world.release("v1.0.1", {".github/template-sync": with_notes(*notes)})
        return world.sync.check(world.template)

    def test_a_file_kept_whole_must_be_kept_current(self, sync_world):
        assert any("`# kept whole: /README.md` names a file the list does not keep current" in p
                   for p in self.check(sync_world, "# kept whole: /README.md"))

    def test_a_pattern_kept_whole_is_named(self, sync_world):
        assert any("`# kept whole: /docs/*.md` is a pattern" in p for p in self.check(sync_world, "# kept whole: /docs/*.md"))

    def test_a_second_redraw_is_named(self, sync_world):
        problems = self.check(sync_world, "# redraw: make index", "# redraw: make catalog")
        assert any("more than one `# redraw:`" in p for p in problems)

    def test_a_redraw_that_does_not_parse_is_named(self, sync_world):
        assert any("does not parse as a command" in p for p in self.check(sync_world, "# redraw: python3 'unclosed"))

    def test_drawn_blocks_must_name_a_namespace(self, sync_world):
        problems = self.check(sync_world, "# drawn blocks: Brain Blocks", "# redraw: python3 scripts/tool.py")
        assert any("`# drawn blocks: Brain Blocks` names no namespace" in p for p in problems)

    def test_drawn_blocks_need_a_redraw_to_draw_them_again(self, sync_world):
        assert any("no `# redraw:` command" in p for p in self.check(sync_world, "# drawn blocks: brain"))

    def test_well_formed_notes_pass(self, sync_world):
        assert self.check(sync_world, "# kept whole: /docs/guide.md", "# redraw: python3 scripts/tool.py",
                          "# drawn blocks: brain") == []


# A generator of the repository's own: the first line of the guide, drawn into
# a catalog the owner keeps, which no sync ever writes.
DRAW = ("import pathlib\n"
        "first = pathlib.Path('docs/guide.md').read_text(encoding='utf-8').splitlines()[0]\n"
        "pathlib.Path('catalog.txt').write_text(first + '\\n', encoding='utf-8')\n")


def drawing(world, draw: str = DRAW) -> None:
    """A template that names its redraw command, released and generated from."""
    text = (TEMPLATE_LIST.replace("/scripts/tool.py\n", "/scripts/tool.py\n/scripts/draw.py\n")
            .replace("#/LICENSE\n", "#/LICENSE\n#/catalog.txt\n"))
    world.release("v1.0.1", {".github/template-sync": with_notes(
        f"# redraw: {shlex.quote(sys.executable)} scripts/draw.py", text=text),
        "scripts/draw.py": draw, "catalog.txt": "# Guide\n"})
    world.generate()


class TestWhatARepositoryGeneratesIsRedrawn:
    """`# redraw: COMMAND`: once a sync has written, the repository's own generated files are drawn again."""

    def test_it_runs_once_a_sync_writes_and_what_it_changes_joins_the_pull_request(self, sync_world):
        drawing(sync_world)
        sync_world.release("v1.1.0", {"docs/guide.md": "# Guide, revised\n"})
        result = sync_world.run_sync(merge=False)
        assert result.remade == ["catalog.txt"] and result.redraw_problem == ""
        assert sync_world.text("catalog.txt") == "# Guide, revised\n"
        assert "🧮" in result.report and "`catalog.txt`" in result.report
        sync_world.commit(sync_world.repo, "sync")
        assert not sync_world.run_sync().changed

    def test_it_never_runs_when_the_sync_changes_nothing(self, sync_world):
        drawing(sync_world, DRAW + "pathlib.Path('ran.txt').write_text('ran\\n', encoding='utf-8')\n")
        assert not sync_world.run_sync().changed
        assert not (sync_world.repo / "ran.txt").exists()

    def test_no_token_reaches_it(self, sync_world, monkeypatch):
        tokens = {"GH_TOKEN", "GITHUB_TOKEN", "WORKFLOW_TOKEN", "BOT_ACCESS_TOKEN"}
        drawing(sync_world, DRAW + "import os\npathlib.Path('env.txt').write_text('\\n'.join(os.environ), "
                                   "encoding='utf-8')\n")
        for name in tokens:
            monkeypatch.setenv(name, "not-a-real-token")
        sync_world.release("v1.1.0", {"docs/guide.md": "# Guide, revised\n"})
        sync_world.run_sync(merge=False)
        seen = set(sync_world.text("env.txt").split())
        assert not seen & tokens and "PYTHONDONTWRITEBYTECODE" in seen

    def test_one_that_fails_is_said_and_the_sync_is_still_proposed(self, sync_world, tmp_path, monkeypatch):
        drawing(sync_world, "import sys\nprint('The catalog cannot be drawn.')\nsys.exit(3)\n")
        sync_world.release("v1.1.0", {"docs/guide.md": "# Guide, revised\n"})
        output = tmp_path / "output"
        monkeypatch.setenv("GITHUB_OUTPUT", str(output))
        code = sync_world.sync.main(["run", "--repo-dir", str(sync_world.repo), "--template-dir",
                                     str(sync_world.template), "--ref", "v1"])
        assert code == 0
        said = output.read_text(encoding="utf-8")
        assert "changed=true" in said and "clean=false" in said, "a failed redraw never merges itself"
        assert "exited with 3" in said and "The catalog cannot be drawn." in said and "[!WARNING]" in said
        assert sync_world.text("docs/guide.md") == "# Guide, revised\n"


# A README whose block the repository's own generator fills from the notes
# beside it, as a notes vault's are.
EMPTY_PEOPLE = "_No people recorded yet._"
INTRO = "Everyone the owner knows well."


def people(rows: str = EMPTY_PEOPLE, intro: str = INTRO) -> str:
    return (f"# People\n\n{intro}\n\n<!-- brain:entries (drawn by scripts/draw.py) -->\n{rows}\n"
            "<!-- /brain:entries -->\n\n---\n")


DRAW_PEOPLE = '''\
import pathlib
import re

EMPTY = "_No people recorded yet._"
folder = pathlib.Path("people")
names = sorted(p.stem for p in folder.glob("*.md") if p.name != "README.md")
rows = "\\n".join(f"- {name}" for name in names) or EMPTY
readme = folder / "README.md"
block = re.compile(r"(<!-- brain:entries[^>]*-->\\n).*?(\\n<!-- /brain:entries -->)", re.S)
readme.write_text(block.sub(lambda m: m.group(1) + rows + m.group(2), readme.read_text(encoding="utf-8")),
                  encoding="utf-8")
'''


class TestABlockTheRepositoryDrawsIsNeverMerged:
    """`# drawn blocks: NS`: rows the repository draws from its own files never meet the template's."""

    BRAIN = frozenset({b"brain"})

    def decide(self, base, target, ours, drawn=BRAIN):
        def side(data, sha):
            return sync.Side("100644", data.encode(), sha)
        return sync.decide("people/README.md", side(base, "base"), side(target, "target"), side(ours, "ours"),
                           synced=True, was_deleted=False, drawn=drawn)

    def test_a_reworded_empty_list_is_no_conflict_for_an_owner_with_entries(self):
        decision = self.decide(people(), people("_Nobody recorded yet._"), people("- Alex Rivera"))
        assert decision.outcome == "unchanged" and decision.write is None

    def test_without_the_note_the_same_change_is_a_conflict(self):
        decision = self.decide(people(), people("_Nobody recorded yet._"), people("- Alex Rivera"),
                               drawn=frozenset())
        assert decision.outcome == "conflict"

    def test_the_templates_prose_arrives_around_the_owners_rows(self):
        newer = people("_Nobody recorded yet._", "Everyone close to the owner.")
        decision = self.decide(people(), newer, people("- Alex Rivera"))
        assert decision.outcome == "updated"
        assert decision.write.data.decode() == people("- Alex Rivera", "Everyone close to the owner.")

    def test_a_marker_named_in_a_sentence_or_a_fence_is_no_block(self):
        text = (b"From `<!-- brain:x -->` to `<!-- /brain:x -->`.\n\n```markdown\n"
                b"<!-- brain:x -->\nrow\n<!-- /brain:x -->\n```\n")
        assert sync.machined_blocks(text.split(b"\n"), drawn=self.BRAIN) == []

    def test_a_marker_without_its_end_is_no_block(self):
        text = (b"## Log\n\n<!-- brain:log-entries -->\n\n### An entry\n\n## Open\n\n"
                b"<!-- brain:open-loops (drawn) -->\n_None._\n<!-- /brain:open-loops -->\n")
        prose, rows = sync.masked("Log.md", text, self.BRAIN)
        assert rows == [(b"drawn brain:open-loops", [b"_None._"])]
        assert b"### An entry" in prose and b"_None._" not in prose

    def test_only_the_templates_own_well_formed_note_counts(self):
        text = with_notes("# drawn blocks: brain", "# drawn blocks: Not A Namespace") + "# drawn blocks: own\n"
        assert sync.drawn_blocks(text) == self.BRAIN

    @staticmethod
    def world(world, *, entries: bool) -> None:
        """A template whose people README its generator draws, and a repository generated from it."""
        text = TEMPLATE_LIST.replace("/scripts/tool.py\n", "/scripts/tool.py\n/scripts/draw.py\n/people/README.md\n")
        world.release("v1.0.1", {".github/template-sync": with_notes(
            f"# redraw: {shlex.quote(sys.executable)} scripts/draw.py", "# drawn blocks: brain", text=text),
            "scripts/draw.py": DRAW_PEOPLE, "people/README.md": people()})
        world.generate()
        if entries:
            world.owner({"people/Alex Rivera.md": "# Alex Rivera\n", "people/README.md": people("- Alex Rivera")})

    def test_a_real_sync_merges_around_an_owners_entries(self, sync_world):
        self.world(sync_world, entries=True)
        sync_world.release("v1.1.0", {"scripts/draw.py": DRAW_PEOPLE.replace(EMPTY_PEOPLE, "_Nobody recorded yet._"),
                                      "people/README.md": people("_Nobody recorded yet._", "Everyone close.")})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["people/README.md"] == "updated"
        assert sync_world.text("people/README.md") == people("- Alex Rivera", "Everyone close.")
        assert not sync_world.run_sync().changed

    def test_an_untouched_repository_takes_the_new_wording_from_the_redraw(self, sync_world):
        self.world(sync_world, entries=False)
        sync_world.release("v1.1.0", {"scripts/draw.py": DRAW_PEOPLE.replace(EMPTY_PEOPLE, "_Nobody recorded yet._"),
                                      "people/README.md": people("_Nobody recorded yet._")})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["people/README.md"] == "unchanged"
        assert result.remade == ["people/README.md"]
        assert sync_world.text("people/README.md") == people("_Nobody recorded yet._")


# A front page the Markdown Kit draws: a header and a footer between its own
# markers, each repository's from its own measurement, and the template's prose
# between them.
def front_page(stars: int, updated: str, prose: str = "What it is.") -> str:
    return (f'<!-- markdown:header:start -->\n<img alt="Stars: {stars}" src="assets/banners/header-day.svg">\n'
            f"<!-- markdown:header:end -->\n\n## About\n\n{prose}\n\n<!-- markdown:footer:start -->\n"
            f'<img alt="Last updated {updated}" src="assets/banners/footer-day.svg">\n<!-- markdown:footer:end -->\n')


class TestABlockTheMarkdownKitDrawsIsNeverMerged:
    """`# drawn blocks: markdown`: a page the kit draws keeps its own drawing, however often the template's moves."""

    KIT = frozenset({b"markdown"})

    def decide(self, base, target, ours, drawn=KIT):
        def side(data, sha):
            return sync.Side("100644", data.encode(), sha)
        return sync.decide("README.md", side(base, "base"), side(target, "target"), side(ours, "ours"),
                           synced=True, was_deleted=False, drawn=drawn)

    def test_the_templates_redrawn_page_is_no_conflict_for_a_page_drawn_its_own(self):
        decision = self.decide(front_page(3, "May 1"), front_page(4, "May 2"), front_page(0, "June 9"))
        assert decision.outcome == "unchanged" and decision.write is None

    def test_without_the_note_the_same_redraw_is_a_conflict(self):
        decision = self.decide(front_page(3, "May 1"), front_page(4, "May 2"), front_page(0, "June 9"),
                               drawn=frozenset())
        assert decision.outcome == "conflict"

    def test_the_templates_prose_arrives_around_the_pages_own_drawing(self):
        decision = self.decide(front_page(3, "May 1"), front_page(4, "May 2", "What it is, and why."),
                               front_page(0, "June 9"))
        assert decision.outcome == "updated"
        assert decision.write.data.decode() == front_page(0, "June 9", "What it is, and why.")

    def test_an_element_is_a_block_and_a_marker_in_a_fence_or_with_the_wrong_end_is_not(self):
        text = (b"<!-- markdown:element:flow:start -->\nrow\n<!-- markdown:element:flow:end -->\n\n"
                b"<!-- markdown:badges:start -->\nrow\n<!-- /markdown:badges -->\n\n```markdown\n"
                b"<!-- markdown:header:start -->\nrow\n<!-- markdown:header:end -->\n```\n")
        prose, rows = sync.masked("README.md", text, self.KIT)
        assert rows == [(b"drawn markdown:element:flow", [b"row"])]
        assert prose.count(b"row") == 2

    def test_a_real_sync_keeps_the_pages_drawing_and_brings_the_templates_prose(self, sync_world):
        text = TEMPLATE_LIST.replace("/scripts/tool.py\n", "/scripts/tool.py\n/docs/front.md\n")
        sync_world.release("v1.0.1", {".github/template-sync": with_notes(
            f"# redraw: {shlex.quote(sys.executable)} -c pass", "# drawn blocks: markdown", text=text),
            "docs/front.md": front_page(3, "May 1")})
        sync_world.generate()
        sync_world.owner({"docs/front.md": front_page(0, "June 9")})
        sync_world.release("v1.1.0", {"docs/front.md": front_page(4, "May 2", "What it is, and why.")})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["docs/front.md"] == "updated"
        assert sync_world.text("docs/front.md") == front_page(0, "June 9", "What it is, and why.")
        assert not sync_world.run_sync().changed


GITIGNORE = "# Built\n/build/\n/dist/\n"


class TestALineSetKeepsBothAdditions:
    """In .gitignore and .gitattributes the last matching line decides, so the owner's stay last."""

    def setup_world(self, world, template_text: str, owner_text: str, name: str = ".gitignore"):
        world.release("v1.0.1", {name: GITIGNORE, ".github/template-sync": TEMPLATE_LIST.replace(
            "/scripts/tool.py\n", f"/scripts/tool.py\n/{name}\n")})
        world.generate()
        world.owner({name: owner_text})
        world.release("v1.1.0", {name: template_text})

    def test_two_sections_added_at_the_end_are_both_kept_the_templates_first(self, sync_world):
        self.setup_world(sync_world, GITIGNORE + "\n# Cache\n/.cache/\n", GITIGNORE + "\n# Mine\n/preview/\n")
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)[".gitignore"] == "merged"
        assert sync_world.text(".gitignore") == GITIGNORE + "\n# Cache\n/.cache/\n\n# Mine\n/preview/\n"

    def test_an_entry_both_added_is_kept_once_where_the_owner_put_it(self, sync_world):
        self.setup_world(sync_world, GITIGNORE + "/.cache/\n/preview/\n", GITIGNORE + "/preview/\n")
        sync_world.run_sync()
        assert sync_world.text(".gitignore") == GITIGNORE + "/.cache/\n/preview/\n"

    def test_a_pattern_the_owner_deleted_never_comes_back(self, sync_world):
        self.setup_world(sync_world, GITIGNORE.replace("/dist/", "/dist/\n/dist-*/"),
                         GITIGNORE.replace("/dist/\n", ""))
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)[".gitignore"] == "conflict"
        assert "/dist" not in sync_world.text(".gitignore")

    def test_any_other_file_still_calls_two_additions_in_one_place_a_conflict(self, sync_world):
        self.setup_world(sync_world, GITIGNORE + "/.cache/\n", GITIGNORE + "/preview/\n", name="scripts/list.txt")
        assert sync_world.outcomes(sync_world.run_sync())["scripts/list.txt"] == "conflict"


class TestBookkeepingAloneOpensNoPullRequest:
    def test_a_release_that_only_forgets_a_switched_off_file(self, sync_world):
        sync_world.generate()
        sync_world.owner({".github/template-sync": sync_world.text(".github/template-sync").replace(
            "\n/scripts/tool.py\n", "\n#/scripts/tool.py\n")})
        sync_world.release("v1.1.0", {"scripts/tool.py": None, ".github/template-sync": TEMPLATE_LIST})
        result = sync_world.run_sync()
        assert not result.changed
        assert "scripts/tool.py" in sync_world.lock().files, "kept until a change that matters"
        sync_world.release("v1.2.0", {"docs/guide.md": "# Guide v1.2\n"})
        assert sync_world.run_sync().changed
        assert "scripts/tool.py" not in sync_world.lock().files, "and written with it"

    def test_a_release_that_only_redraws_the_templates_own_rows(self, sync_world):
        # A document the template keeps to itself changes what it says about
        # itself, so the template's own log of the folder redraws one row.
        extra = "<!--\ndescription: '{}'\n-->\n# Extra\n"
        sync_world.put(sync_world.template, {"docs/README.md": DOCS_README, "docs/extra.md": extra.format("One."),
                                             ".github/template-sync": listed("docs/README.md", "#/docs/extra.md")})
        redraw(sync_world.template)
        sync_world.release("v1.0.1", {})
        sync_world.generate()
        sync_world.put(sync_world.template, {"docs/extra.md": extra.format("A new description.")})
        redraw(sync_world.template)
        sync_world.release("v1.1.0", {})
        assert "A new description." in (sync_world.template / "docs/README.md").read_text(encoding="utf-8")
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["docs/README.md"] == "unchanged"
        assert not result.changed

    def test_an_owner_who_caught_up_by_hand_still_records_it(self, sync_world):
        sync_world.generate()
        sync_world.owner({"scripts/tool.py": "print('v1.1')\n"})
        sync_world.release("v1.1.0", {"scripts/tool.py": "print('v1.1')\n"})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["scripts/tool.py"] == "current"
        assert result.changed, "left behind, the template's next edit to those lines would conflict"


# A stub whose command its owner made their own, a line apart from the rest.
STUB = "name: checks\njobs:\n  ci:\n    with:\n      lint-command: 'validate'\n\n      test-command: 'test'\n"


def keeping(world, path: str = ".github/workflows/checks.yml") -> str:
    """The owner's list with `# keep mine` for `path` under Your rules."""
    return world.text(".github/template-sync").rstrip("\n") + f"\n# keep mine: /{path}\n"


class TestAnOwnerKeepsTheirLines:
    """`# keep mine: /path` under Your rules: where both changed the same lines, the owner's stand."""

    def setup_world(self, world, keep: bool = True):
        world.release("v1.0.1", {".github/workflows/checks.yml": STUB})
        world.generate()
        world.owner({".github/workflows/checks.yml": STUB.replace("'validate'", "'make lint'"),
                     **({".github/template-sync": keeping(world)} if keep else {})})
        world.release("v1.1.0", {".github/workflows/checks.yml": STUB.replace(
            "'validate'", "'validate --strict'").replace("'test'", "'test --all'")})

    def test_the_owners_line_stands_and_the_templates_other_change_arrives(self, sync_world):
        self.setup_world(sync_world)
        result = sync_world.run_sync()
        decision = next(d for d in result.decisions if d.path == ".github/workflows/checks.yml")
        assert decision.outcome == "yours-kept"
        text = sync_world.text(".github/workflows/checks.yml")
        assert "'make lint'" in text and "'test --all'" in text and "--strict" not in text
        assert not sync_world.lock().pending, "nothing waits: the owner has decided"
        assert "validate --strict" in decision.diff, "the change not applied is shown"
        assert "Merged, your lines kept" in result.report and "validate --strict" in result.report

    def test_the_templates_next_change_elsewhere_merges_as_usual(self, sync_world):
        self.setup_world(sync_world)
        sync_world.run_sync()
        sync_world.release("v1.2.0", {".github/workflows/checks.yml": STUB.replace(
            "'validate'", "'validate --strict'").replace("'test'", "'test --all'").replace(
            "name: checks", "name: checks, renamed")})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)[".github/workflows/checks.yml"] == "merged"
        text = sync_world.text(".github/workflows/checks.yml")
        assert "name: checks, renamed" in text and "'make lint'" in text

    def test_without_the_note_it_is_a_conflict_that_names_the_way_out(self, sync_world):
        self.setup_world(sync_world, keep=False)
        result = sync_world.run_sync()
        decision = next(d for d in result.decisions if d.path == ".github/workflows/checks.yml")
        assert decision.outcome == "conflict"
        assert "`# keep mine: /.github/workflows/checks.yml` under Your rules" in decision.detail
        assert "'make lint'" in sync_world.text(".github/workflows/checks.yml")

    def test_the_note_survives_every_redraw_of_the_list(self, sync_world):
        self.setup_world(sync_world)
        sync_world.release("v1.2.0", {".github/template-sync": TEMPLATE_LIST.replace(
            "/scripts/tool.py\n", "/scripts/tool.py\n/scripts/other.py\n"), "scripts/other.py": "x = 1\n"})
        sync_world.run_sync()
        assert "# keep mine: /.github/workflows/checks.yml" in sync_world.text(".github/template-sync")
        assert sync.kept_mine(sync_world.text(".github/template-sync")) == {".github/workflows/checks.yml"}

    def test_only_the_owners_rules_can_keep_and_only_by_exact_path(self):
        listing = (TEMPLATE_LIST.replace("# --- Kept current", "# keep mine: /docs/guide.md\n# --- Kept current")
                   + "# keep mine: /scripts/*.py\n# KEEP MINE: /scripts/tool.py\n")
        assert sync.kept_mine(listing) == {"scripts/tool.py"}

    def test_a_binary_file_stays_the_owners(self, sync_world):
        sync_world.release("v1.0.1", {"scripts/logo.bin": b"\x00logo-1", ".github/template-sync":
                                      TEMPLATE_LIST.replace("/scripts/tool.py\n", "/scripts/tool.py\n/scripts/logo.bin\n")})
        sync_world.generate()
        sync_world.owner({"scripts/logo.bin": b"\x00mine", ".github/template-sync": keeping(sync_world, "scripts/logo.bin")})
        sync_world.release("v1.1.0", {"scripts/logo.bin": b"\x00logo-2"})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["scripts/logo.bin"] == "yours-kept"
        assert sync_world.read("scripts/logo.bin") == b"\x00mine"
        assert not sync_world.lock().pending

    def test_a_file_the_template_added_beside_the_owners_own_stays_theirs(self, sync_world):
        sync_world.generate()
        sync_world.owner({"scripts/new.py": "a = 1\n\nb = 'mine'\n\nc = 3\n",
                          ".github/template-sync": keeping(sync_world, "scripts/new.py")})
        sync_world.release("v1.1.0", {"scripts/new.py": "a = 1\n\nb = 'theirs'\n\nc = 3\n", ".github/template-sync":
                                      TEMPLATE_LIST.replace("/scripts/tool.py\n", "/scripts/tool.py\n/scripts/new.py\n")})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)["scripts/new.py"] == "yours-kept"
        assert sync_world.text("scripts/new.py") == "a = 1\n\nb = 'mine'\n\nc = 3\n"
        # The template's file is the baseline from here on, so its next change merges.
        sync_world.release("v1.2.0", {"scripts/new.py": "a = 1\n\nb = 'theirs'\n\nc = 4\n"})
        assert sync_world.outcomes(sync_world.run_sync())["scripts/new.py"] == "merged"
        assert sync_world.text("scripts/new.py") == "a = 1\n\nb = 'mine'\n\nc = 4\n"

    def test_only_the_change_kept_over_is_shown_never_one_that_arrived(self, sync_world):
        self.setup_world(sync_world)
        decision = next(d for d in sync_world.run_sync().decisions if d.path == ".github/workflows/checks.yml")
        shown = [line for line in decision.diff.splitlines() if line[:1] in "+-" and line[:3] not in ("+++", "---")]
        assert shown == ["-      lint-command: 'make lint'", "+      lint-command: 'validate --strict'"]

    def test_in_a_line_set_both_additions_still_arrive_and_the_owners_change_stands(self, sync_world):
        listing = TEMPLATE_LIST.replace("/scripts/tool.py\n", "/scripts/tool.py\n/.gitignore\n")
        sync_world.release("v1.0.1", {".gitignore": GITIGNORE + "\n/tmp/\n", ".github/template-sync": listing})
        sync_world.generate()
        sync_world.owner({".gitignore": GITIGNORE.replace("/build/", "/build/mine/") + "\n/tmp/\n/preview/\n",
                          ".github/template-sync": keeping(sync_world, ".gitignore")})
        sync_world.release("v1.1.0", {".gitignore": GITIGNORE.replace("/build/", "/build/theirs/") + "\n/tmp/\n/.cache/\n"})
        result = sync_world.run_sync()
        assert sync_world.outcomes(result)[".gitignore"] == "yours-kept"
        assert sync_world.text(".gitignore") == (GITIGNORE.replace("/build/", "/build/mine/")
                                                 + "\n/tmp/\n/.cache/\n/preview/\n")

    def test_settling_each_hunk_is_exactly_what_git_merge_file_does(self, tmp_path):
        # Each hunk settled for the owner, or for the template, must be git's own
        # --ours or --theirs, down to a last line with no newline, in LF or CRLF.
        rng = random.Random(2026)  # noqa: S311 - reproducible trials, not secrets

        def native(flag: str, *sides: bytes) -> bytes:
            for name, data in zip("obt", sides):
                (tmp_path / name).write_bytes(data)
            return subprocess.run(["git", "merge-file", "-p", flag, *(str(tmp_path / n) for n in "obt")],
                                  capture_output=True, check=False).stdout

        def edited(lines: list[str]) -> list[str]:
            lines = list(lines)
            for _ in range(rng.randint(1, 3)):
                at = rng.randrange(len(lines) + 1)
                roll = rng.random()
                if roll < 0.5 or not lines:
                    lines.insert(at, f"new {rng.randint(0, 9)}")
                elif roll < 0.8:
                    lines[min(at, len(lines) - 1)] = f"changed {rng.randint(0, 9)}"
                else:
                    del lines[min(at, len(lines) - 1)]
            return lines

        settled = 0
        for _ in range(400):
            base = [f"line {i}" for i in range(rng.randint(1, 6))]
            eol = rng.choice(["\n", "\r\n"])
            o, b, t = (eol.join(lines) + rng.choice([eol, ""]) for lines in (edited(base), base, edited(base)))
            o, b, t = (text.encode() for text in (o, b, t))
            marked, clean = sync.merge3(o, b, t)
            if clean:
                continue
            settled += 1
            assert sync.resolved(marked, o, t, line_set=False, side="yours") == (native("--ours", o, b, t), True)
            assert sync.resolved(marked, o, t, line_set=False, side="template") == (native("--theirs", o, b, t), True)
            assert sync.resolved(marked, o, t, line_set=False) == (marked, False)
        assert settled > 100, "the trials must reach conflicts to prove anything"


@pytest.fixture(autouse=True)
def _isolated(monkeypatch):
    for key, value in SYNC_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("GIT_TERMINAL_PROMPT", "0")
    subprocess.run(["git", "--version"], check=True, capture_output=True)
