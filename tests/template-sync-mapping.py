# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Template sync through a mapping, for a repository DEFINED as a delta of its template.

tannergolden/repo is not generated from tannergolden/path; it is path with
five permitted differences, written down as a contract. A mapping is that
contract as the engine reads it: what never comes over, which folder sits
somewhere else, which footer reads differently. These tests hold the same
engine to the promises a mapped sync makes on top of the usual ones:

- a difference the mapping permits survives every sync;
- nothing the mapping leaves out ever arrives;
- a file missing here is drift, reported - never switched off, never re-created;
- the repository's own list keeps naming every file it ships, so its own
  template-side check passes on the sync's pull request.

The world is a public template and a private one shaped like the real pair,
on real git repositories, with no network.
"""

from __future__ import annotations

import json
import os
import re
import subprocess

import pytest
from conftest import SYNC_ENV, load_script

sync = load_script("scripts/template-sync.py")

MIT = "Distributed under the MIT License."
PROPRIETARY = "Proprietary and confidential; all rights reserved."

MAPPING = {
    "format": 1,
    "name": "📐 Template Parity Sync",
    "source": ".github/template-parity.yml",
    "lock": ".github/template-parity.lock",
    "list": ".github/template-sync",
    "exclude": [
        ".github/SECURITY.md",
        ".github/TEMPLATE_INIT",
        ".github/template-parity.lock",
        ".github/template-parity.yml",
        ".github/template-sync",
        "LICENSE",
        "README.md",
        "src",
    ],
    "relocate": {"docs": ".github/docs"},
    "replace": [{"under": "docs", "from": MIT, "to": PROPRIETARY}],
}

KEPT = "# --- Kept current -------------------------------------------------------------"
YOURS = "# --- Yours: seeded once, never synced -----------------------------------------"
ONLY = "# --- Only ever in the template ----------------------------------------------"
RULES = "# --- Your rules ---------------------------------------------------------------"

PUBLIC_LIST = f"""# --- 🔄 Template Sync ---
#
# Every path tannergolden/path ships.

{KEPT}
/.gitattributes
/.github/SECURITY.md
/.github/workflows/checks.yml
/docs/README.md
/docs/templates/ADR.md

{YOURS}
#/README.md
#/LICENSE
#/src/**

{ONLY}
#/.github/TEMPLATE_INIT

{RULES}
"""

PRIVATE_LIST = f"""# --- 🔄 Template Sync ---
#
# Every path tannergolden/repo ships.

{KEPT}
/.gitattributes
/.github/docs/README.md
/.github/docs/templates/ADR.md
/.github/workflows/checks.yml

{YOURS}
#/README.md
#/LICENSE

{ONLY}
#/.github/TEMPLATE_INIT
#/.github/template-parity.lock
#/.github/template-parity.yml

{RULES}
"""


def seed(body: str, footer: str) -> str:
    return f"# Title\n\nFirst paragraph.\n\n{body}\n\nLast paragraph.\n\nBuilt with love. {footer}\n"


ATTRIBUTES = "* text=auto eol=lf\n\n*.png binary\n\n*.md diff=markdown\n"

PUBLIC = {
    ".github/template-sync": PUBLIC_LIST,
    ".github/TEMPLATE_INIT": "Not initialised yet.\n",
    ".github/SECURITY.md": "# Security\n",
    ".github/workflows/checks.yml": "name: checks\non: push\njobs: {}\n",
    ".gitattributes": ATTRIBUTES,
    "README.md": "# The public template\n",
    "LICENSE": "MIT License\n",
    "src/README.md": "# Source\n",
    "docs/README.md": seed("The seeds live in docs/templates/.", MIT),
    "docs/templates/ADR.md": seed("Record one decision.", MIT),
}

PRIVATE = {
    ".github/template-sync": PRIVATE_LIST,
    ".github/TEMPLATE_INIT": "Not initialised yet, and says so differently.\n",
    ".github/template-parity.yml": "baseline: tannergolden/path\n",
    ".github/workflows/checks.yml": PUBLIC[".github/workflows/checks.yml"],
    ".gitattributes": ATTRIBUTES + "\n.github/docs/** linguist-documentation\n",
    "README.md": "# The private template\n",
    "LICENSE": "PROPRIETARY\n",
    ".github/docs/README.md": seed("The seeds live in .github/docs/templates/.", PROPRIETARY),
    ".github/docs/templates/ADR.md": seed("Record one decision.", PROPRIETARY),
}


class MapWorld:
    """A public template, and a private one defined against it through a mapping."""

    def __init__(self, root):
        self.public = root / "public"
        self.private = root / "private"
        self.mapping = sync.load_mapping(json.dumps(MAPPING))
        for where, files, branch in ((self.public, PUBLIC, "Development"), (self.private, PRIVATE, "Development")):
            where.mkdir()
            self.git(where, "init", "-q", "-b", branch)
            self.put(where, files)
            self.commit(where, "initial")
        lock = sync.mapped_lock(self.private, self.public, template="tannergolden/path", ref="Development",
                                mapping=self.mapping)
        self.put(self.private, {self.mapping.lock: sync.dump_lock(lock)})
        self.commit(self.private, "record the parity lock")

    @staticmethod
    def git(where, *args):
        proc = subprocess.run(["git", "-C", str(where), *args], capture_output=True,
                              env={**os.environ, **SYNC_ENV}, check=False)
        assert proc.returncode == 0, proc.stderr.decode()
        return proc.stdout.decode()

    @staticmethod
    def put(where, files):
        for rel, content in files.items():
            path = where / rel
            if content is None:
                if path.exists():
                    path.unlink()
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def commit(self, where, message):
        self.git(where, "add", "-A")
        self.git(where, "commit", "-q", "--allow-empty", "-m", message)

    def publish(self, files, list_edit=None):
        """A change to the public template, with its list kept honest as its check requires."""
        self.put(self.public, files)
        if list_edit:
            current = (self.public / ".github/template-sync").read_text(encoding="utf-8")
            self.put(self.public, {".github/template-sync": list_edit(current)})
        self.commit(self.public, "public change")

    def here(self, files):
        self.put(self.private, files)
        self.commit(self.private, "private change")

    def run(self, *, merge=True, **kwargs):
        result = sync.run(self.private, self.public, template="tannergolden/path", ref="Development",
                          mapping=self.mapping, **kwargs)
        if merge and result.changed:
            self.commit(self.private, "parity sync")
        return result

    def text(self, rel):
        path = self.private / rel
        return path.read_text(encoding="utf-8") if path.is_file() else None

    def lock(self):
        return sync.load_lock(self.text(self.mapping.lock), self.mapping.lock)

    @staticmethod
    def outcomes(result):
        return {d.path: d.outcome for d in result.decisions
                if d.outcome not in ("unchanged", "current", "not-synced")}

    def listed(self):
        """What the private template's own list check says, as it runs on the sync's pull request."""
        return sync.check(self.private)


@pytest.fixture
def world(tmp_path, monkeypatch):
    for key, value in SYNC_ENV.items():
        monkeypatch.setenv(key, value)
    return MapWorld(tmp_path)


# =============================================================================
# The mapping itself
# =============================================================================


class TestTheMapping:
    mapping = sync.load_mapping(json.dumps(MAPPING))

    @pytest.mark.parametrize("path", [
        "docs/templates/ADR.md", "docs/README.md", ".gitattributes", ".github/workflows/checks.yml",
        "docsy/x.md", "docs", "a/docs/b.md",
    ])
    def test_here_and_there_are_inverses(self, path):
        local = self.mapping.here(path)
        assert local is not None
        assert self.mapping.there(local) == path

    @pytest.mark.parametrize("path", ["README.md", "LICENSE", "src/README.md", "src/a/b.py", ".github/SECURITY.md",
                                      ".github/template-sync", ".github/TEMPLATE_INIT"])
    def test_what_is_left_out_never_comes_here(self, path):
        assert self.mapping.here(path) is None

    def test_a_path_here_that_no_template_path_reaches_has_no_origin(self):
        # `docs/x` here would have to come from `docs/x` there, which the
        # mapping sends to `.github/docs/x` instead: nothing lands on it.
        assert self.mapping.there("docs/x.md") is None
        assert self.mapping.there("README.md") is None
        assert self.mapping.there("src/a.py") is None

    def test_relocation_is_by_folder_not_by_prefix(self):
        assert self.mapping.here("docsy/x.md") == "docsy/x.md"
        assert self.mapping.here("docs/x.md") == ".github/docs/x.md"

    def test_the_footer_swaps_only_under_the_named_folder(self):
        data = f"x\n{MIT}\n".encode()
        assert self.mapping.content("docs/a.md", data) == f"x\n{PROPRIETARY}\n".encode()
        assert self.mapping.content(".github/workflows/README.md", data) == data

    def test_a_binary_file_passes_untouched(self):
        data = b"\0" + MIT.encode()
        assert self.mapping.content("docs/a.png", data) == data

    @pytest.mark.parametrize("change, message", [
        ({"format": 2}, "format 1"),
        ({"surprise": True}, "does not know"),
        ({"name": ""}, "`name`"),
        ({"lock": "../escape.lock"}, "unsafe"),
        ({"lock": ".github/template-sync.lock"}, "file of its own"),
        ({"lock": ".github/template-sync", "list": ".github/template-sync"}, "file of its own"),
        ({"exclude": "src"}, "list of paths"),
        ({"exclude": ["/abs"]}, "unsafe"),
        ({"relocate": ["docs"]}, "`relocate`"),
        ({"relocate": {"docs": "docs/inner"}}, "overlap"),
        ({"relocate": {"docs": ".github/docs", "notes": ".github/docs/notes"}}, "overlap"),
        ({"relocate": {"docs": "docs"}}, "overlap"),
        ({"replace": [{"under": "docs", "from": "", "to": "x"}]}, "`replace`"),
        ({"replace": [{"under": "docs", "from": "a"}]}, "`replace`"),
        ({"replace": {"under": "docs"}}, "`replace`"),
    ])
    def test_a_wrong_mapping_is_refused_with_a_sentence(self, change, message):
        doc = {**MAPPING, **change}
        with pytest.raises(sync.SyncError, match=message):
            sync.load_mapping(json.dumps(doc))

    def test_invalid_json_is_refused(self):
        with pytest.raises(sync.SyncError, match="not valid JSON"):
            sync.load_mapping("{")


# =============================================================================
# The repository's own list, amended
# =============================================================================


class TestAmendingTheOwnList:
    def test_an_arrival_takes_its_place_in_order_among_its_section(self):
        out = sync.amend_list(PRIVATE_LIST, PUBLIC_LIST + "/docs/templates/New.md\n",
                              added={".github/docs/templates/New.md": "docs/templates/New.md"})
        lines = out.splitlines()
        at = lines.index("/.github/docs/templates/New.md")
        assert lines[at - 1] == "/.github/docs/templates/ADR.md"
        assert lines[at + 1] == "/.github/workflows/checks.yml"

    def test_an_arrival_copies_the_templates_choice_and_section(self):
        public = PUBLIC_LIST.replace("#/.github/TEMPLATE_INIT\n", "#/.github/TEMPLATE_INIT\n#/.github/workflows/cut.yml\n")
        out = sync.amend_list(PRIVATE_LIST, public, added={".github/workflows/cut.yml": ".github/workflows/cut.yml"})
        lines = out.splitlines()
        assert "#/.github/workflows/cut.yml" in lines
        assert "/.github/workflows/cut.yml" not in lines
        assert sync.section_of(lines, lines.index("#/.github/workflows/cut.yml")) == ONLY

    def test_an_arrival_the_template_list_does_not_name_is_kept_current(self):
        out = sync.amend_list(PRIVATE_LIST, PUBLIC_LIST, added={"zeta.txt": "zeta.txt"})
        lines = out.splitlines()
        assert "zeta.txt" not in lines and "/zeta.txt" in lines
        assert sync.section_of(lines, lines.index("/zeta.txt")) == KEPT

    def test_a_departure_takes_its_line_on_or_off(self):
        out = sync.amend_list(PRIVATE_LIST, PUBLIC_LIST, added={},
                              removed=[".github/workflows/checks.yml", ".github/template-parity.yml"])
        assert "/.github/workflows/checks.yml" not in out.splitlines()
        assert "#/.github/template-parity.yml" not in out.splitlines()

    def test_a_move_keeps_its_own_lines_choice_and_section(self):
        own = PRIVATE_LIST.replace("/.github/workflows/checks.yml", "#/.github/workflows/checks.yml")
        out = sync.amend_list(own, PUBLIC_LIST, added={".github/workflows/gates.yml": ".github/workflows/gates.yml"},
                              renamed={".github/workflows/checks.yml": ".github/workflows/gates.yml"})
        lines = out.splitlines()
        assert "#/.github/workflows/gates.yml" in lines and "/.github/workflows/gates.yml" not in lines
        assert sync.section_of(lines, lines.index("#/.github/workflows/gates.yml")) == KEPT

    def test_a_line_already_there_is_never_duplicated_or_flipped(self):
        own = PRIVATE_LIST.replace("/.gitattributes", "#/.gitattributes")
        out = sync.amend_list(own, PUBLIC_LIST, added={".gitattributes": ".gitattributes"})
        assert out.splitlines().count("#/.gitattributes") == 1
        assert "/.gitattributes" not in out.splitlines()

    def test_the_rules_section_is_never_written_into(self):
        out = sync.amend_list(PRIVATE_LIST, PUBLIC_LIST, added={"zzz/last.md": "zzz/last.md"})
        assert out.splitlines()[-1] == RULES

    def test_an_arrival_a_pattern_leaves_to_owners_needs_no_line_where_the_same_pattern_does(self):
        public = PUBLIC_LIST.replace(f"{YOURS}\n", f"{YOURS}\n#/assets/**\n")
        own = PRIVATE_LIST.replace(f"{YOURS}\n", f"{YOURS}\n#/assets/**\n")
        out = sync.amend_list(own, public, added={"assets/html/README.md": "assets/html/README.md"})
        assert out == own

    def test_an_arrival_a_pattern_leaves_to_owners_arrives_switched_off(self):
        public = PUBLIC_LIST.replace(f"{YOURS}\n", f"{YOURS}\n#/assets/**\n")
        out = sync.amend_list(PRIVATE_LIST, public, added={"assets/html/README.md": "assets/html/README.md"})
        lines = out.splitlines()
        assert "#/assets/html/README.md" in lines and "/assets/html/README.md" not in lines
        assert sync.section_of(lines, lines.index("#/assets/html/README.md")) == YOURS

    def test_a_pattern_here_that_names_an_arrival_is_never_contradicted(self):
        public = PUBLIC_LIST.replace(f"{YOURS}\n", f"{YOURS}\n#/assets/html/README.md\n")
        own = PRIVATE_LIST.replace(f"{KEPT}\n", f"{KEPT}\n/assets/**\n")
        out = sync.amend_list(own, public, added={"assets/html/README.md": "assets/html/README.md"})
        assert out == own, "a line of the template's choice would name the file both on and off here"


# =============================================================================
# A mapped sync, end to end
# =============================================================================


class TestAMappedSync:
    def test_the_first_sync_after_the_lock_changes_nothing(self, world):
        result = world.run()
        assert not result.changed
        assert world.outcomes(result) == {}

    def test_a_new_seed_arrives_relocated_in_this_repositorys_form(self, world):
        world.publish({"docs/templates/Runbook.md": seed("Steps.", MIT)},
                      lambda t: t.replace("/docs/templates/ADR.md\n", "/docs/templates/ADR.md\n/docs/templates/Runbook.md\n"))
        result = world.run()
        assert world.outcomes(result) == {".github/docs/templates/Runbook.md": "added"}
        assert world.text(".github/docs/templates/Runbook.md") == seed("Steps.", PROPRIETARY)
        assert not (world.private / "docs").exists(), "nothing lands at the template's own path"
        assert world.listed() == []

    def test_a_file_a_pattern_leaves_to_owners_arrives_without_a_line_of_its_own(self, world):
        world.here({".github/template-sync": PRIVATE_LIST.replace(f"{YOURS}\n", f"{YOURS}\n#/assets/**\n")})
        world.publish({"assets/html/README.md": "# HTML\n"},
                      lambda t: t.replace(f"{YOURS}\n", f"{YOURS}\n#/assets/**\n"))
        result = world.run()
        assert world.outcomes(result) == {"assets/html/README.md": "added"}
        lines = world.text(".github/template-sync").splitlines()
        assert "/assets/html/README.md" not in lines and "#/assets/html/README.md" not in lines
        assert world.listed() == [], "the file must stay named off, and only off"

    def test_a_changed_seed_updates_and_keeps_this_repositorys_footer(self, world):
        world.publish({"docs/templates/ADR.md": seed("Record one decision, and why.", MIT)})
        result = world.run()
        assert world.outcomes(result) == {".github/docs/templates/ADR.md": "updated"}
        assert world.text(".github/docs/templates/ADR.md") == seed("Record one decision, and why.", PROPRIETARY)

    def test_what_the_mapping_leaves_out_never_arrives(self, world):
        world.publish({
            "README.md": "# The public template, renamed\n",
            "LICENSE": "MIT License, revised\n",
            "src/README.md": "# Source, revised\n",
            "src/new.py": "print('new')\n",
            ".github/SECURITY.md": "# Security, revised\n",
            ".github/TEMPLATE_INIT": "Revised.\n",
        })
        result = world.run()
        assert world.outcomes(result) == {}
        assert not result.changed
        assert world.text("README.md") == PRIVATE["README.md"]
        assert world.text("LICENSE") == PRIVATE["LICENSE"]
        assert world.text(".github/TEMPLATE_INIT") == PRIVATE[".github/TEMPLATE_INIT"]
        assert not (world.private / "src").exists()
        assert not (world.private / ".github/SECURITY.md").exists()

    def test_a_permitted_difference_survives_a_merge(self, world):
        world.publish({".gitattributes": ATTRIBUTES.replace("*.png binary", "*.png binary\n*.jpg binary")})
        result = world.run()
        assert world.outcomes(result) == {".gitattributes": "merged"}
        text = world.text(".gitattributes")
        assert "*.jpg binary" in text, "the template's change must land"
        assert ".github/docs/** linguist-documentation" in text, "this repository's difference must survive"

    def test_a_seed_that_differs_in_prose_merges_around_the_difference(self, world):
        world.publish({"docs/README.md": seed("The seeds live in docs/templates/.", MIT).replace(
            "Last paragraph.", "Last paragraph, revised.")})
        result = world.run()
        assert world.outcomes(result) == {".github/docs/README.md": "merged"}
        text = world.text(".github/docs/README.md")
        assert "Last paragraph, revised." in text
        assert ".github/docs/templates/." in text and PROPRIETARY in text

    def test_a_clash_is_left_untouched_and_kept_in_view(self, world):
        world.here({".github/docs/README.md": seed("The seeds live in .github/docs/templates/, privately.", PROPRIETARY)})
        world.publish({"docs/README.md": seed("The seeds live in docs/templates/, publicly.", MIT)})
        before = world.text(".github/docs/README.md")
        result = world.run()
        assert world.outcomes(result) == {".github/docs/README.md": "conflict"}
        assert world.text(".github/docs/README.md") == before
        assert world.lock().pending[".github/docs/README.md"]["reason"] == "conflict"
        assert "<<<<<<<" not in before

    def test_a_file_missing_here_is_drift_not_a_choice(self, world):
        world.here({".github/workflows/checks.yml": None})
        world.publish({".github/workflows/checks.yml": "name: checks\non: push\njobs: {} # revised\n"})
        result = world.run()
        assert world.outcomes(result) == {".github/workflows/checks.yml": "conflict"}
        conflict = next(d for d in result.decisions if d.path == ".github/workflows/checks.yml")
        assert "missing here" in conflict.detail and ".github/template-parity.yml" in conflict.detail
        assert world.text(".github/workflows/checks.yml") is None, "never re-created"
        assert not world.lock().files[".github/workflows/checks.yml"].deleted, "never switched off"
        assert "/.github/workflows/checks.yml" in world.text(".github/template-sync").splitlines()
        # Still in view on the next run, and settled once it is restored.
        again = world.run()
        assert world.outcomes(again) == {".github/workflows/checks.yml": "conflict"}
        world.here({".github/workflows/checks.yml": "name: checks\non: push\njobs: {} # revised\n"})
        settled = world.run()
        assert world.outcomes(settled) == {}
        assert world.lock().pending == {}

    def test_a_file_missing_here_stays_missing_when_the_template_moves_it(self, world):
        world.here({".github/docs/templates/ADR.md": None})
        adr = (world.public / "docs/templates/ADR.md").read_text(encoding="utf-8")
        world.publish({"docs/templates/ADR.md": None, "docs/templates/decisions/ADR.md": adr},
                      lambda t: t.replace("/docs/templates/ADR.md", "/docs/templates/decisions/ADR.md"))
        first = world.run()
        assert world.outcomes(first).get(".github/docs/templates/decisions/ADR.md") == "conflict"
        second = world.run()
        assert world.text(".github/docs/templates/decisions/ADR.md") is None, "a missing file was re-created"
        assert world.outcomes(second).get(".github/docs/templates/decisions/ADR.md") == "conflict"
        assert ".github/docs/templates/decisions/ADR.md" in world.lock().pending

    def test_a_move_inside_the_relocated_folder_moves_here_with_its_line(self, world):
        world.here({".github/docs/templates/ADR.md": seed("Record one decision.", PROPRIETARY) + "A private note.\n"})
        adr = (world.public / "docs/templates/ADR.md").read_text(encoding="utf-8")
        world.publish({"docs/templates/ADR.md": None, "docs/templates/decisions/ADR.md": adr},
                      lambda t: t.replace("/docs/templates/ADR.md", "/docs/templates/decisions/ADR.md"))
        result = world.run()
        assert world.outcomes(result) == {".github/docs/templates/ADR.md": "moved",
                                          ".github/docs/templates/decisions/ADR.md": "moved-here"}
        assert world.text(".github/docs/templates/ADR.md") is None
        assert world.text(".github/docs/templates/decisions/ADR.md").endswith("A private note.\n")
        lines = world.text(".github/template-sync").splitlines()
        assert "/.github/docs/templates/decisions/ADR.md" in lines
        assert "/.github/docs/templates/ADR.md" not in lines
        assert world.listed() == []

    def test_a_move_that_leaves_a_new_file_behind_keeps_both_lines(self, world):
        adr = (world.public / "docs/templates/ADR.md").read_text(encoding="utf-8")
        # Nothing in common with the record that moved: a new file, not a rewrite of the old one.
        index = f"# Decisions\n\nEvery record, by number.\n\n| No. | Title |\n| --- | --- |\n\n{MIT}\n"
        world.publish({"docs/templates/ADR.md": index, "docs/templates/decisions/ADR.md": adr},
                      lambda t: t.replace("/docs/templates/ADR.md\n",
                                          "/docs/templates/ADR.md\n/docs/templates/decisions/ADR.md\n"))
        result = world.run()
        assert world.outcomes(result) == {".github/docs/templates/ADR.md": "updated",
                                          ".github/docs/templates/decisions/ADR.md": "added"}
        assert world.text(".github/docs/templates/decisions/ADR.md") == seed("Record one decision.", PROPRIETARY)
        assert world.text(".github/docs/templates/ADR.md") == index.replace(MIT, PROPRIETARY)
        lines = world.text(".github/template-sync").splitlines()
        assert "/.github/docs/templates/ADR.md" in lines and "/.github/docs/templates/decisions/ADR.md" in lines
        assert world.listed() == []
        assert not world.run().changed

    def test_a_removal_takes_its_line_with_it(self, world):
        world.publish({".github/workflows/checks.yml": None},
                      lambda t: t.replace("/.github/workflows/checks.yml\n", ""))
        result = world.run()
        assert world.outcomes(result) == {".github/workflows/checks.yml": "deleted"}
        assert "/.github/workflows/checks.yml" not in world.text(".github/template-sync").splitlines()
        assert world.listed() == []

    def test_a_file_the_template_leaves_to_owners_is_left_to_them_here_too(self, world):
        world.publish({".github/workflows/cut-release.yml": "name: cut\non: workflow_dispatch\njobs: {}\n"},
                      lambda t: t.replace("#/.github/TEMPLATE_INIT\n",
                                          "#/.github/TEMPLATE_INIT\n#/.github/workflows/cut-release.yml\n"))
        result = world.run()
        assert world.outcomes(result) == {".github/workflows/cut-release.yml": "added"}
        assert "#/.github/workflows/cut-release.yml" in world.text(".github/template-sync").splitlines()
        assert world.listed() == []

    def test_workflow_files_wait_for_a_token_and_their_line_waits_with_them(self, world):
        world.publish({".github/workflows/new.yml": "name: new\non: push\njobs: {}\n"},
                      lambda t: t.replace("/.github/workflows/checks.yml\n",
                                          "/.github/workflows/checks.yml\n/.github/workflows/new.yml\n"))
        result = world.run(workflow_files=False)
        assert world.outcomes(result) == {".github/workflows/new.yml": "deferred"}
        assert world.text(".github/workflows/new.yml") is None
        assert "/.github/workflows/new.yml" not in world.text(".github/template-sync").splitlines()
        assert world.listed() == [], "a line for a file not delivered would fail the check"
        delivered = world.run()
        assert world.outcomes(delivered) == {".github/workflows/new.yml": "added"}
        assert world.listed() == []

    def test_the_sentinel_does_not_stop_a_mapped_sync(self, world):
        assert world.text(".github/TEMPLATE_INIT") is not None
        world.publish({"docs/templates/ADR.md": seed("Changed.", MIT)})
        assert world.outcomes(world.run()) == {".github/docs/templates/ADR.md": "updated"}

    def test_the_lock_is_this_syncs_own_and_carries_no_identity(self, world):
        world.publish({"docs/templates/ADR.md": seed("Changed.", MIT)})
        world.run()
        lock = world.lock()
        assert lock.identity is None
        assert ".github/template-sync" not in lock.files, "the template's list is not this repository's"
        assert world.text(sync.LOCK_PATH) is None, "a generated repository's lock is never written here"

    def test_a_second_run_changes_nothing(self, world):
        world.publish({"docs/templates/ADR.md": seed("Changed.", MIT), ".gitattributes": ATTRIBUTES + "*.zip binary\n"})
        world.run()
        assert not world.run().changed

    def test_a_waiting_file_keeps_the_version_it_started_waiting_at(self, world):
        world.here({".github/docs/README.md": seed("Private words.", PROPRIETARY)})
        world.publish({"docs/README.md": seed("Public words.", MIT)})
        world.run()
        since = world.lock().pending[".github/docs/README.md"]["version"]
        world.publish({"docs/templates/ADR.md": seed("Unrelated.", MIT)})
        world.run()
        assert world.lock().pending[".github/docs/README.md"]["version"] == since


class TestWhatAMappedSyncRefuses:
    def test_no_lock_is_an_error_that_says_how_to_record_one(self, world):
        world.here({world.mapping.lock: None})
        with pytest.raises(sync.SyncError, match="lock --map"):
            world.run()

    def test_a_template_path_where_a_folder_is_relocated_to_stops_the_run(self, world):
        # Its origin could not be told from the relocated files' - the same
        # place, and so the same footer swap, would apply to a file never moved.
        world.publish({".github/docs/NOTES.md": "a stray public file\n"})
        with pytest.raises(sync.SyncError, match="sits where the mapping relocates a folder to"):
            world.run()

    def test_two_template_paths_landing_on_one_stop_the_run(self, world):
        mapping = sync.load_mapping(json.dumps({**MAPPING, "relocate": {"docs": ".github/docs", "notes": "extra"}}))
        world.publish({"extra/a.md": "one\n", "notes/a.md": "two\n"})
        with pytest.raises(sync.SyncError, match=re.escape("extra/a.md in tannergolden/path sits where")):
            sync.run(world.private, world.public, template="tannergolden/path", ref="Development", mapping=mapping)

    def test_a_lock_is_not_recorded_while_the_trees_disagree(self, world):
        world.here({".github/docs/templates/ADR.md": None})
        with pytest.raises(sync.SyncError, match="missing here"):
            sync.mapped_lock(world.private, world.public, template="tannergolden/path", ref="Development",
                             mapping=world.mapping)


# =============================================================================
# The command line, as the parity workflow calls it
# =============================================================================


class TestTheCommandLine:
    def test_run_and_lock_take_the_mapping(self, world, tmp_path, monkeypatch):
        mapping = tmp_path / "map.json"
        mapping.write_text(json.dumps(MAPPING), encoding="utf-8")
        output = tmp_path / "output"
        monkeypatch.setenv("GITHUB_OUTPUT", str(output))
        world.publish({"docs/templates/ADR.md": seed("Changed.", MIT)})
        code = sync.main(["run", "--repo-dir", str(world.private), "--template-dir", str(world.public),
                          "--template", "tannergolden/path", "--ref", "Development", "--map", str(mapping)])
        assert code == 0
        assert "changed=true" in output.read_text(encoding="utf-8")
        assert "PROPRIETARY" not in world.text(".github/docs/templates/ADR.md")
        assert PROPRIETARY in world.text(".github/docs/templates/ADR.md")

    def test_lock_with_a_mapping_prints_the_lock_to_record(self, world, tmp_path, capsys):
        mapping = tmp_path / "map.json"
        mapping.write_text(json.dumps(MAPPING), encoding="utf-8")
        code = sync.main(["lock", "--repo-dir", str(world.private), "--template", "tannergolden/path",
                          "--map", str(mapping), "--template-dir", str(world.public), "--ref", "Development"])
        assert code == 0
        printed = sync.load_lock(capsys.readouterr().out, "printed")
        assert set(printed.files) == set(world.lock().files)

    def test_a_generated_repositorys_lock_still_needs_its_identity(self, world, capsys):
        code = sync.main(["lock", "--repo-dir", str(world.private), "--template", "tannergolden/path"])
        assert code == 1
        assert "--owner" in capsys.readouterr().out

    def test_track_uses_the_mapped_syncs_own_issue(self, world, tmp_path, fake_gh, monkeypatch):
        mapping = tmp_path / "map.json"
        mapping.write_text(json.dumps(MAPPING), encoding="utf-8")
        world.here({".github/docs/README.md": seed("Private words.", PROPRIETARY)})
        world.publish({"docs/README.md": seed("Public words.", MIT)})
        world.run()
        fake_gh.route("issue list", "[]")
        fake_gh.route("label create", "")
        fake_gh.route("issue create", "https://github.com/tannergolden/repo/issues/3")
        monkeypatch.setenv("PATH", fake_gh.env()["PATH"])
        code = sync.main(["track", "--repo-dir", str(world.private), "--repository", "tannergolden/repo",
                          "--map", str(mapping)])
        assert code == 0
        calls = "\n".join(fake_gh.calls)
        assert "📐 Template Parity Sync is waiting on you" in calls
        assert ".github/template-parity.yml" in calls, "the issue says where a difference is recorded"
        assert "--limit" in calls
