# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Template sync under random histories, and the broken designs it rejects.

Hand-written scenarios test the situations somebody thought of. These test
the ones nobody did: each seed builds a real template that releases random
changes - edits, additions, deletions, moves, mode flips, binary and CRLF
files, names with spaces and brackets in them - and a real repository whose
owner edits lines, deletes files, switches paths off and on, writes rules,
adds files of their own and resolves conflicts, while syncs run with and
without a workflow token and some of their pull requests are never merged.

THE ORACLE DOES NOT ASK THE ENGINE. Every line any file ever holds is a
unique token, `T<release>.<n>` for the template's and `O<n>` for the
owner's. That makes "did the template's change arrive" a set question with
an answer independent of how the engine merges: after every merged sync, a
synced file that is not pending must hold every token the template's version
holds - bar the ones the owner deleted - and none the template has removed.
Which paths count as synced is decided by an UNPATCHED copy of the engine's
matcher reading the list, never by the engine under test.

After every sync, whatever happened:

  - files the template never shipped are untouched;
  - template paths the lists do not sync are untouched;
  - nothing it wrote holds a conflict marker or the template author's identity;
  - the init sentinel is never written;
  - a file the owner deleted stays deleted until they switch it back on;
  - a file the template removed, that the owner never touched, is gone;
  - the lock reads back, and (mechanism) running again changes nothing;
  - (mechanism) a conflict or a deferral never moves that file's baseline.

`TEMPLATE_SYNC_SEEDS` raises the number of histories, and
`TEMPLATE_SYNC_SEED_START` moves the window, for a deep run.

test_the_suite_rejects_a_known_bad_design is the suite testing itself: each
known-bad design is patched into a fresh copy of the engine, and the
property NAMED for it must catch it, with the mechanism checks (baseline
bookkeeping, idempotence) switched off - so it is the damage an owner would
see that is caught, not the mechanism behind it.
"""

from __future__ import annotations

import os
import random
import re
from collections import defaultdict

import pytest
from conftest import SYNC_ENV, SyncWorld, load_script

SEEDS = int(os.environ.get("TEMPLATE_SYNC_SEEDS", "30"))
START = int(os.environ.get("TEMPLATE_SYNC_SEED_START", "0"))

TEXT_PATHS = [
    "docs/a.md",
    "docs/b.md",
    "docs/sub/c.md",
    "notes/with space.md",
    "notes/amp&er.md",
    "notes/br[ack]et.md",
    "scripts/run.sh",
    ".github/workflows/w.yml",
    "id/footer.md",
    "deep/x/y/z.md",
    "cfg/crlf.txt",
]
BINARY_PATH = "assets/logo.bin"
MOVES = {"docs/b.md": "docs/b-moved.md", "notes/amp&er.md": "notes/moved/amp&er.md"}
FOOTER = "Built with ❤️ by [@tannergolden](https://github.com/tannergolden)."
ADDRESS = "Uses tannergolden/standards."
LEAK = re.compile(r"tannergolden(?!/[A-Za-z0-9._-])|Tanner Golden")
TOKEN = re.compile(r"^(T\d+\.\d+|O\d+)$")
YOURS = ("README.md", "LICENSE")

# The engine, unpatched, for the oracle's own reading of lists and identity.
ORACLE = load_script("scripts/template-sync.py")


class Violation(AssertionError):
    """A property broke: the message says which, for which seed and path."""


class History:
    """One random template, one random owner, and the syncs between them."""

    def __init__(self, seed: int, root, sync_module=None, *, mechanism: bool = True):
        self.seed = seed
        self.rng = random.Random(seed)  # noqa: S311 - reproducible histories, not secrets
        # Off, only the outcome properties run: what the owner would see.
        self.mechanism = mechanism
        self.world = SyncWorld(root)
        if sync_module is not None:
            self.world.sync = sync_module
            self.world.init = sync_module.INIT
        self.sync = self.world.sync
        self.files: dict[str, list[str] | bytes] = {}
        self.modes: dict[str, str] = {}
        self.default_on: dict[str, bool] = {}
        self.release_no = 0
        self.token_no = 0
        self.owner_removed: dict[str, set[str]] = defaultdict(set)
        self.owner_files: dict[str, bytes] = {}
        self.owner_deleted: set[str] = set()
        self.owner_touched: set[str] = set()
        # old path -> new path, for every move the template has made.
        self.moved_to: dict[str, str] = {}
        # Removed by the template while synced and untouched here: each must be
        # gone after the next merged sync that has a token to delete with.
        self.awaiting_removal: set[str] = set()

    # --- The template ---------------------------------------------------

    def token(self, owner: bool = False) -> str:
        self.token_no += 1
        return f"O{self.token_no}" if owner else f"T{self.release_no}.{self.token_no}"

    def render(self, path: str) -> bytes:
        content = self.files[path]
        if isinstance(content, bytes):
            return content
        lines = list(content)
        if path == "id/footer.md":
            lines = [*lines, ADDRESS, FOOTER]
        newline = "\r\n" if path.endswith("crlf.txt") else "\n"
        return (newline.join(lines) + newline).encode()

    def list_text(self) -> str:
        escape = ORACLE.escape
        on = [p for p in sorted(self.files) if self.default_on[p]]
        off = [p for p in sorted(self.files) if not self.default_on[p]]
        return (
            "# 🔄 TEMPLATE SYNC - a random template\n\n# --- Kept current\n"
            + "".join(f"{escape(p)}\n" for p in on)
            + "\n# --- Yours\n#/README.md\n#/LICENSE\n"
            + "".join(f"#{escape(p)}\n" for p in off)
            + "\n# --- Template only\n#/.github/TEMPLATE_INIT\n\n# --- Your rules ---\n"
        )

    def release(self) -> None:
        self.release_no += 1
        version = f"v1.{self.release_no}.0"
        before = set(self.files)
        extra: dict = {}
        if self.release_no == 1:
            for path in self.rng.sample(TEXT_PATHS, 7):
                self.files[path] = [self.token() for _ in range(self.rng.randint(4, 9))]
                self.modes[path] = "100755" if path.endswith(".sh") else "100644"
                self.default_on[path] = True
            if self.rng.random() < 0.5:
                self.files[BINARY_PATH] = b"\x00\x01" + bytes(self.rng.randrange(256) for _ in range(16))
                self.modes[BINARY_PATH] = "100644"
                self.default_on[BINARY_PATH] = True
            extra = {
                ".github/TEMPLATE_INIT": "Not initialised yet.\n",
                "README.md": "# Template\n",
                "LICENSE": "MIT License\n\nCopyright (c) 2026 Tanner Golden\n",
            }
        else:
            for _ in range(self.rng.randint(1, 4)):
                self.template_change()
        put = {p: self.render(p) for p in self.files}
        put.update(extra)
        put[ORACLE.LIST_PATH] = self.list_text()
        removed = before - set(self.files)
        put.update({p: None for p in removed})
        self.world.release(version, put, dict(self.modes))
        if self.release_no > 1:
            owner_list = self.world.text(ORACLE.LIST_PATH)
            for path in removed:
                if (self.world.read(path) is not None and path not in self.owner_touched
                        and ORACLE.matched(owner_list, [path])):
                    self.awaiting_removal.add(path)
        self.awaiting_removal -= set(self.files)

    def template_change(self) -> None:
        choice = self.rng.random()
        text = [p for p in self.files if isinstance(self.files[p], list)]
        absent = [p for p in TEXT_PATHS if p not in self.files and p not in MOVES.values()]
        if choice < 0.5 and text:
            self.edit(self.files[self.rng.choice(sorted(text))], owner=False)
        elif choice < 0.6 and absent:
            path = self.rng.choice(absent)
            self.files[path] = [self.token() for _ in range(self.rng.randint(3, 6))]
            self.modes[path] = "100644"
            self.default_on[path] = True
            # A path the template adds is a new file, whatever happened to an
            # old one there: the owner's record of the old file ends with it.
            self.owner_deleted.discard(path)
            self.owner_touched.discard(path)
            self.owner_removed.pop(path, None)
        elif choice < 0.68 and len(self.files) > 3:
            path = self.rng.choice(sorted(self.files))
            del self.files[path], self.modes[path], self.default_on[path]
        elif choice < 0.76:
            for old, new in MOVES.items():
                if old in self.files and new not in self.files:
                    self.files[new] = self.files.pop(old)
                    self.modes[new] = self.modes.pop(old)
                    self.default_on[new] = self.default_on.pop(old)
                    # What the owner did to the file travels with it.
                    self.moved_to[old] = new
                    self.owner_removed[new] |= self.owner_removed.pop(old, set())
                    for record in (self.owner_deleted, self.owner_touched):
                        if old in record:
                            record.add(new)
                    break
        elif choice < 0.84 and self.files:
            path = self.rng.choice(sorted(self.files))
            self.modes[path] = "100755" if self.modes[path] == "100644" else "100644"
        elif choice < 0.9 and self.files:
            path = self.rng.choice(sorted(self.files))
            self.default_on[path] = not self.default_on[path]
        elif BINARY_PATH in self.files:
            self.files[BINARY_PATH] = b"\x00\x02" + bytes(self.rng.randrange(256) for _ in range(16))

    def where(self, path: str) -> str:
        """The template path an owner's file at `path` now corresponds to."""
        while path in self.moved_to and path not in self.files:
            path = self.moved_to[path]
        return path

    def edit(self, lines: list[str], *, owner: bool, path: str = "") -> None:
        path = self.where(path) if owner else path
        op = self.rng.random()
        if op < 0.4 or not lines:
            lines.insert(self.rng.randint(0, len(lines)), self.token(owner))
        elif op < 0.7:
            removed = lines.pop(self.rng.randrange(len(lines)))
            if owner and removed.startswith("T"):
                self.owner_removed[path].add(removed)
        else:
            index = self.rng.randrange(len(lines))
            if owner and lines[index].startswith("T"):
                self.owner_removed[path].add(lines[index])
            lines[index] = self.token(owner)

    # --- The owner ------------------------------------------------------

    def derived_lines(self, path: str) -> list[str]:
        data = self.world.read(path) or b""
        return [ln for ln in data.decode("utf-8", "replace").replace("\r\n", "\n").split("\n") if TOKEN.match(ln)]

    def write_lines(self, path: str, lines: list[str]) -> None:
        data = self.world.read(path) or b""
        crlf = b"\r\n" in data
        text = data.decode("utf-8").replace("\r\n", "\n")
        extra = [ln for ln in text.split("\n") if ln and not TOKEN.match(ln)]
        newline = "\r\n" if crlf else "\n"
        self.world.put(self.world.repo, {path: (newline.join(lines + extra) + newline).encode()})

    def owner_turn(self) -> None:
        lock = self.world.lock()
        list_text = self.world.text(ORACLE.LIST_PATH)
        for _ in range(self.rng.randint(0, 3)):
            choice = self.rng.random()
            present = sorted(p for p in lock.files if self.world.read(p) is not None
                             and p not in ORACLE.NEVER and p not in YOURS)
            texts = [p for p in present if b"\0" not in self.world.read(p)]
            if choice < 0.35 and texts:
                path = self.rng.choice(texts)
                lines = self.derived_lines(path)
                self.edit(lines, owner=True, path=path)
                self.write_lines(path, lines)
                self.owner_touched.add(path)
                self.awaiting_removal.discard(path)
            elif choice < 0.45 and present:
                path = self.rng.choice(present)
                self.world.put(self.world.repo, {path: None})
                # Deleting a file the template has since moved deletes it there too.
                self.owner_deleted |= {path, self.where(path)}
                self.awaiting_removal.discard(path)
            elif choice < 0.55:
                ons = [ln for ln in list_text.splitlines() if ln.startswith("/") and ln[1:] in lock.files]
                if ons:
                    line = self.rng.choice(ons)
                    list_text = list_text.replace(f"\n{line}\n", f"\n#{line}\n", 1)
            elif choice < 0.65:
                offs = [ln for ln in list_text.splitlines()
                        if ln.startswith("#/") and ORACLE.unescape(ln[1:]) in self.files]
                if offs:
                    line = self.rng.choice(offs)
                    list_text = list_text.replace(f"\n{line}\n", f"\n{line[1:]}\n", 1)
                    self.owner_deleted.discard(ORACLE.unescape(line[1:]))
            elif choice < 0.7:
                if "!/notes/**" not in list_text:
                    list_text += "!/notes/**\n"
            elif choice < 0.8:
                path = f"mine/{self.token(owner=True)}.md"
                self.owner_files[path] = f"owner file {path}\n".encode()
                self.world.put(self.world.repo, {path: self.owner_files[path]})
            elif choice < 0.9 and lock.pending:
                path = self.rng.choice(sorted(lock.pending))
                if path in self.files and self.world.read(path) is not None:
                    self.world.put(self.world.repo, {path: self.expected(path)})
                    self.owner_removed[path].clear()
                    self.owner_touched.add(path)
            elif present:
                path = self.rng.choice(present)
                mode = "100755" if not os.access(self.world.repo / path, os.X_OK) else "100644"
                self.world.put(self.world.repo, {}, {path: mode})
        self.world.put(self.world.repo, {ORACLE.LIST_PATH: list_text})
        self.world.commit(self.world.repo, "owner turn")

    def expected(self, path: str) -> bytes:
        """The template's current version, as initialisation would have left it."""
        return ORACLE.rewriter(self.world.lock().identity, SyncWorld.TEMPLATE)(path, self.render(path))

    # --- Syncing, and every property after it ----------------------------

    def snapshot(self) -> dict[str, tuple[bytes, bool]]:
        out = {}
        for path in self.world.git(self.world.repo, "ls-files", "-z").split("\0"):
            full = self.world.repo / path
            if path and full.is_file():
                out[path] = (full.read_bytes(), os.access(full, os.X_OK))
        return out

    def fail(self, message: str) -> None:
        raise Violation(f"seed {self.seed}, release {self.release_no}: {message}")

    def sync_turn(self) -> None:
        before = self.snapshot()
        lock_before = ORACLE.load_lock(self.world.text(ORACLE.LIST_PATH.replace("template-sync", "template-sync.lock")))
        list_before = self.world.text(ORACLE.LIST_PATH)
        token = self.rng.random() < 0.8
        result = self.sync.run(self.world.repo, self.world.template, workflow_files=token)
        after = self.snapshot()
        list_after = self.world.text(ORACLE.LIST_PATH)
        changed = {p for p in set(before) | set(after) if before.get(p) != after.get(p)}
        shipped = set(self.files)
        gone = set(lock_before.files) - shipped - ORACLE.NEVER

        # Untouched: what the template never shipped, and what the lists do
        # not sync - judged by the oracle's own reading of the lists.
        for path, data in self.owner_files.items():
            if self.world.read(path) != data:
                self.fail(f"{path}, a file the template never shipped, was changed")
        allowed = ORACLE.matched(list_after, shipped) | ORACLE.matched(list_before, gone)
        for path in changed - {ORACLE.LOCK_PATH, ORACLE.LIST_PATH}:
            if path in shipped | gone and path not in allowed:
                self.fail(f"{path} is not synced by the list and was changed")

        for path in changed - {ORACLE.LOCK_PATH, ORACLE.LIST_PATH}:
            data = self.world.read(path)
            if data is None:
                continue
            if b"<<<<<<<" in data or b">>>>>>>" in data:
                self.fail(f"{path} was written with a conflict marker")
            if LEAK.search(data.decode("utf-8", "replace")):
                self.fail(f"{path} was written with the template author's identity")
        if self.world.read(ORACLE.SENTINEL) is not None:
            self.fail("the init sentinel was written")
        for path in self.owner_deleted:
            if self.world.read(path) is not None and before.get(path) is None:
                still_off = path not in ORACLE.matched(list_before, [path])
                if still_off:
                    self.fail(f"{path} was deleted by the owner and came back")
        lock = ORACLE.load_lock(self.world.text(ORACLE.LOCK_PATH))

        if self.mechanism:
            for d in result.decisions:
                if d.outcome in ("conflict", "deferred", "waiting") and \
                        lock.files.get(d.path) != lock_before.files.get(d.path):
                    self.fail(f"{d.path} is {d.outcome} and its baseline moved")

        if self.rng.random() < 0.15:
            self.world.git(self.world.repo, "reset", "-q", "--hard", "HEAD")  # the pull request sat unmerged
            return
        if result.changed:
            self.world.commit(self.world.repo, f"sync {result.version}")
        if self.mechanism:
            again = self.sync.run(self.world.repo, self.world.template, workflow_files=token, write=False)
            if again.changed:
                files = sorted(d.path for d in again.decisions if d.write is not None or d.delete)
                if not files:
                    old, new = ORACLE.load_lock(self.world.text(ORACLE.LOCK_PATH)), again.lock
                    files = [f"lock: {p}" for p in sorted(set(old.files) | set(new.files))
                             if old.files.get(p) != new.files.get(p)]
                    files += [f"pending: {p}" for p in sorted(set(old.pending) ^ set(new.pending))]
                self.fail(f"a second run would change more: {files}")

        # Arrived: every synced, non-pending file holds the template's tokens.
        listed = ORACLE.matched(list_after, shipped)
        for path, content in self.files.items():
            data = self.world.read(path)
            if path in lock.pending or path not in listed or data is None:
                continue
            if isinstance(content, bytes):
                if data != content:
                    self.fail(f"{path}: the binary file is neither current nor pending")
                continue
            have = set(self.derived_lines(path))
            missing = set(content) - self.owner_removed[path] - have
            if missing:
                self.fail(f"{path}: the template's {sorted(missing)} never arrived and nothing is pending")
            stale = {t for t in have if t.startswith("T")} - set(content)
            if stale:
                self.fail(f"{path}: {sorted(stale)} were removed by the template and are still here")

        # Removed, eventually: judged without the engine's lock at all.
        if token:
            for path in sorted(self.awaiting_removal):
                if self.world.read(path) is not None and ORACLE.matched(list_before, [path]):
                    self.fail(f"{path} was removed by the template, untouched here, and survived")
            self.awaiting_removal = {p for p in self.awaiting_removal if self.world.read(p) is not None}

        if not self.mechanism:
            return
        # Removed, this run: what the lock says was synced and untouched is gone.
        transform = ORACLE.rewriter(lock_before.identity, SyncWorld.TEMPLATE)
        synced_gone = ORACLE.matched(list_before, gone)
        old = ORACLE.read_blobs(self.world.template, (lock_before.files[p].blob for p in synced_gone))
        for path in sorted(synced_gone):
            state = lock_before.files[path]
            mine = before.get(path)
            # Pending after this run - held back for a token, say - is waiting, not lost.
            if mine is None or path in lock_before.pending or path in lock.pending or state.blob not in old:
                continue
            if mine[0] == transform(path, old[state.blob]) and self.world.read(path) is not None:
                self.fail(f"{path} was removed by the template, untouched here, and survived")

    def play(self, rounds: int = 5) -> None:
        self.release()
        self.world.generate()
        for _ in range(rounds):
            if self.rng.random() < 0.8:
                self.release()
            self.owner_turn()
            self.sync_turn()


@pytest.fixture
def isolated_git(monkeypatch):
    for key, value in SYNC_ENV.items():
        monkeypatch.setenv(key, value)


@pytest.mark.parametrize("seed", [pytest.param(s, id=f"seed-{s}") for s in range(START, START + SEEDS)])
def test_every_property_holds_through_a_random_history(seed, tmp_path, isolated_git):
    History(seed, tmp_path).play()


# --- The suite testing itself ---------------------------------------------


def global_baseline(m):
    real = m.decide

    def decide(path, base, target, ours, **kw):
        d = real(path, base, target, ours, **kw)
        if d.outcome == "conflict" and target is not None:
            d.state = m.state_of(target)  # the baseline moves on regardless
        return d

    m.decide = decide


def no_identity_rewrite(m):
    m.rewriter = lambda identity, template: (lambda path, data: data)


def reinstall_deletions(m):
    real = m.decide

    def decide(path, base, target, ours, **kw):
        d = real(path, base, target, ours, **kw)
        if d.outcome == "owner-deleted":
            return m.Decision(path, "added", write=target, state=m.state_of(target))
        return d

    m.decide = decide


def conflict_markers(m):
    real = m.decide

    def decide(path, base, target, ours, **kw):
        d = real(path, base, target, ours, **kw)
        if d.outcome == "conflict" and ours is not None and target is not None:
            return m.Decision(path, "merged", write=m.Side(ours.mode, ours.data + b"<<<<<<< yours\n"),
                              state=m.state_of(target))
        return d

    m.decide = decide


def ignore_the_list(m):
    m.matched = lambda list_text, paths: set(paths)


def removals_judged_by_the_new_list(m):
    real = m.decide

    def decide(path, base, target, ours, **kw):
        if target is None:
            kw["synced"] = False  # the new list never names a removed path
        return real(path, base, target, ours, **kw)

    m.decide = decide


# Each design, and the words of the properties allowed to catch it. A lost
# change shows as a token that never arrived or one the template removed that
# never left; both are the same damage, so either may be first to see it.
LOST = ("never arrived", "removed by the template and are still here")
MUTANTS = {
    "one baseline for the whole repository": (global_baseline, LOST),
    "no identity rewrite": (no_identity_rewrite, ("identity",)),
    "reinstalling deleted files": (reinstall_deletions, ("deleted by the owner and came back",)),
    "writing conflict markers": (conflict_markers, ("conflict marker",)),
    "ignoring the list": (ignore_the_list, ("is not synced by the list and was changed",)),
    "judging removed files by the new list": (removals_judged_by_the_new_list,
                                              ("removed by the template, untouched here, and survived",)),
}


@pytest.mark.parametrize("name", sorted(MUTANTS))
def test_the_suite_rejects_a_known_bad_design(name, tmp_path, isolated_git):
    patch, expected = MUTANTS[name]
    module = load_script("scripts/template-sync.py")
    patch(module)
    for seed in range(200):
        root = tmp_path / f"seed-{seed}"
        root.mkdir()
        try:
            History(seed, root, module, mechanism=False).play()
        except Violation as violation:
            assert any(words in str(violation) for words in expected), (
                f"{name!r} was caught, but by the wrong property: {violation}"
            )
            return
    pytest.fail(f"no history out of 200 caught {name!r}: the properties have no teeth for it")
