# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The lock is read strictly, and written the same way every time.

A lock read loosely is a baseline guessed, and a wrong baseline merges an
owner's own edits away as if the template had made them. So every way the
file can be wrong stops the run with a sentence naming it, before anything
is planned, and nothing it names is ever trusted as a path to write.
"""

from __future__ import annotations

import json

import pytest
from conftest import load_script

sync = load_script("scripts/template-sync.py")

BLOB = "a" * 40


def lock(**overrides) -> dict:
    doc = {
        "format": 1,
        "template": "tannergolden/path",
        "version": "v1.2.0",
        "commit": "b" * 40,
        "identity": {"owner": "janedoe", "repository": "janedoe/widget", "name": "Jane Doe", "year": 2027},
        "files": {"docs/a.md": {"blob": BLOB, "mode": "100644"}},
        "pending": {},
    }
    doc.update(overrides)
    return doc


def load(doc) -> object:
    return sync.load_lock(json.dumps(doc) if not isinstance(doc, str) else doc)


class TestARoundTrip:
    def test_what_is_written_reads_back_identically(self):
        first = load(lock(files={"z.md": {"blob": BLOB, "mode": "100755", "deleted": True},
                                 "a.md": {"blob": BLOB, "mode": "100644"}}))
        text = sync.dump_lock(first)
        assert sync.dump_lock(sync.load_lock(text)) == text

    def test_files_are_sorted_and_the_file_ends_in_a_newline(self):
        text = sync.dump_lock(load(lock(files={"z.md": {"blob": BLOB, "mode": "100644"},
                                               "a.md": {"blob": BLOB, "mode": "100644"}})))
        assert text.index('"a.md"') < text.index('"z.md"') and text.endswith("}\n")

    def test_a_false_deleted_flag_is_not_written(self):
        text = sync.dump_lock(load(lock(files={"a.md": {"blob": BLOB, "mode": "100644", "deleted": False}})))
        assert "deleted" not in text

    def test_a_sha256_repository_is_accepted(self):
        assert load(lock(files={"a.md": {"blob": "c" * 64, "mode": "100644"}})).files["a.md"].blob == "c" * 64

    def test_a_lock_without_an_identity_is_accepted(self):
        assert load(lock(identity=None)).identity is None


class TestTheNoteForPeople:
    def test_the_lock_says_what_it_is_and_who_writes_it(self):
        doc = json.loads(sync.dump_lock(load(lock())))
        assert next(iter(doc)) == "//", "the note comes first, where a person opening the file looks"
        assert "never edit it by hand" in doc["//"] and "🔄 Template Sync" in doc["//"]

    def test_a_mapped_lock_names_its_own_writer(self):
        assert "📐 Template Parity Sync" in sync.dump_lock(load(lock()), "📐 Template Parity Sync")

    def test_the_note_is_read_past_whatever_it_says(self):
        assert load(lock(**{"//": "anything at all"})).template == "tannergolden/path"


class TestEveryWayToBeWrong:
    @pytest.mark.parametrize(
        ("doc", "message"),
        [
            ("{not json", "not valid JSON"),
            ("[]", "must be a JSON object"),
            (lock(format=2), "format 2"),
            (lock(extra=True), "does not know"),
            (lock(template="not a name"), "not OWNER/REPO"),
            (lock(template=7), "not OWNER/REPO"),
            (lock(commit="nope"), "not a SHA"),
            (lock(version=3), "must be a string"),
            (lock(identity={"owner": "a"}), "exactly owner, repository, name and year"),
            (lock(identity={"owner": "", "repository": "a/b", "name": "n", "year": 2027}), "non-empty"),
            (lock(identity={"owner": "a", "repository": "a/b", "name": "n", "year": True}), "four-digit"),
            (lock(identity={"owner": "a", "repository": "a/b", "name": "n", "year": 99999}), "four-digit"),
            (lock(files=[]), "must be an object"),
            (lock(files={"a.md": {"blob": BLOB}}), "needs `blob` and `mode`"),
            (lock(files={"a.md": {"blob": BLOB, "mode": "100644", "x": 1}}), "nothing but `deleted`"),
            (lock(files={"a.md": {"blob": "zz", "mode": "100644"}}), "not a SHA"),
            (lock(files={"a.md": {"blob": BLOB, "mode": "120000"}}), "only 100644 and 100755"),
            (lock(files={"a.md": {"blob": BLOB, "mode": "100644", "deleted": "yes"}}), "true or false"),
            (lock(pending=[]), "must map paths to objects"),
            (lock(pending={"a.md": "x"}), "must map paths to objects"),
        ],
    )
    def test_it_stops_and_says_why(self, doc, message):
        with pytest.raises(sync.SyncError, match=message):
            load(doc)

    @pytest.mark.parametrize("path", ["../escape", "/abs", ".git/config", "a/.GIT/x", "a//b", "a/./b", "a\\b", ""])
    def test_an_unsafe_path_is_refused(self, path):
        with pytest.raises(sync.SyncError, match="unsafe"):
            load(lock(files={path: {"blob": BLOB, "mode": "100644"}}))


class TestWhatIsSafe:
    @pytest.mark.parametrize("path", ["a.md", ".github/workflows/x.yml", "a b/c&d.md", "ünï/ç.md", ".gitignore",
                                      ".github/git/x"])
    def test_ordinary_paths(self, path):
        assert sync.unsafe(path) is None

    @pytest.mark.parametrize("path", ["", "/a", "a/../b", "..", ".git", "x/.git/y", "a//b", "a\\b", "a\0b"])
    def test_hostile_paths(self, path):
        assert sync.unsafe(path)


class TestAnEmptyValueIsNotAMissingOne:
    """`value or default` read an empty list as absent; each field is typed first."""

    @pytest.mark.parametrize("field", ["template", "commit", "version"])
    @pytest.mark.parametrize("value", [[], 0, False, {}])
    def test_a_falsy_value_of_the_wrong_type_is_refused(self, field, value):
        with pytest.raises(sync.SyncError):
            load(lock(**{field: value}))
