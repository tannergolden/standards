#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
# =============================================================================
# Template Sync - bring a generated repository's scaffold up to date, on request
# =============================================================================
# "Use this template" hands over a copy and then forgets it. The stubs, the
# repository scripts, the seeded documents: every fix made to them in the
# template afterwards stays in the template. This carries those fixes into a
# generated repository as one evolving pull request, and never as a push.
#
# THREE FILES DESCRIBE THE RELATIONSHIP, and each has exactly one author.
#
#   .github/template-sync       The OWNER's. Every path the template ships,
#                               in .gitignore syntax: a line naming a path is
#                               kept current, `#/path` is left alone. The
#                               template writes the defaults, the owner flips
#                               them, and each sync redraws the file from the
#                               template's latest list with every flip kept.
#   .github/template-sync.lock  THIS SCRIPT's. Where each file was last
#                               merged from, per file. Never edited by hand.
#   the template's own list     The TEMPLATE AUTHOR's. Checked in the
#                               template itself: every file it ships must be
#                               named, so nothing new arrives unannounced.
#
# ⚠️ THE BASELINE IS PER FILE, AND THAT IS NOT A DETAIL. Replaying the real
# history of both templates showed that one baseline for the whole repository
# loses changes silently: a sync pull request with twenty clean updates and
# one conflict gets merged, the baseline moves past the conflict, and no
# later sync ever sees that change again. A file that did not merge keeps the
# baseline it had, so the change is offered again until it lands or the owner
# switches the file off.
#
# ⚠️ THE TEMPLATE IS REWRITTEN INTO THE OWNER'S IDENTITY BEFORE ANY MERGE.
# Initialisation rewrote the template author's identity in this repository.
# Merging raw template content against that leaks the author's name into
# every new file and conflicts on every line init touched; the same replay
# found the leak in more than half of all generation points. So every
# template file passes through init-template.py's own `initialised()` first,
# with the identity init recorded in the lock: one function, imported rather
# than copied, so the two can never disagree about a byte.
#
# WHAT IT NEVER DOES: write a conflict marker, re-create a file the owner
# deleted, touch a path the template does not ship, write the init sentinel,
# write through a symlink, or write outside the repository. A conflict leaves
# the owner's file exactly as it was, and says what the template changed.
#
# Requires: git
# Usage:    template-sync.py run   --template-dir DIR [--template OWNER/REPO] [--ref v1] [--map MAP]
#           template-sync.py check
#           template-sync.py track --repository OWNER/REPO [--version V] [--map MAP]
#           template-sync.py lock  --template OWNER/REPO --owner O --repository O/R
#                                  --name NAME --year YEAR [--root REV]
#           template-sync.py lock  --template OWNER/REPO --map MAP --template-dir DIR --ref REF
#
# With --map, run, track and lock serve a repository DEFINED as a delta of
# its template rather than generated from it - see "A mapping" below.
# =============================================================================
from __future__ import annotations

import argparse
import atexit
import dataclasses
import difflib
import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable

LIST_PATH = ".github/template-sync"
LOCK_PATH = ".github/template-sync.lock"
SENTINEL = ".github/TEMPLATE_INIT"
WORKFLOW_DIR = ".github/workflows/"

# Never synced, whatever any list says. The sentinel because re-creating it
# re-runs initialisation over a repository that already has history; the
# list and the lock because they describe THIS repository's relationship
# and are kept by rules of their own.
NEVER = frozenset({SENTINEL, LIST_PATH, LOCK_PATH})

RULES_MARKER = "# --- Your rules"
# Above the marker, the engine's own: paths the template dropped that still
# wait on the owner, kept named so the next run can finish what this one
# could not. Redrawn on every run, so they leave once they resolve.
WAITING_NOTE = "# --- Waiting on you: the template moved or removed these, and they are not settled yet"
LOCK_FORMAT = 1
# GitHub refuses a pull request body over 65,536 characters.
REPORT_LIMIT = 60_000
DIFF_LINES = 80

SHA = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
MODES = frozenset({"100644", "100755"})
TEMPLATE_NAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?/[A-Za-z0-9._-]+$")


class SyncError(Exception):
    """A problem the run must stop on, with a sentence naming it."""


class Skip(Exception):
    """Nothing to do yet, and nothing wrong: said once, as a notice."""


# =============================================================================
# Git
# =============================================================================


def git(repo: pathlib.Path | str, *args: str, data: bytes | None = None, ok: tuple[int, ...] = (0,),
        env: dict | None = None) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        input=data,
        capture_output=True,
        check=False,
        env={**os.environ, **env} if env else None,
    )
    if proc.returncode not in ok:
        detail = proc.stderr.decode("utf-8", "replace").strip().splitlines()
        raise SyncError(
            f"`git {' '.join(args[:2])}` failed in {repo}: {detail[-1] if detail else 'no output'}"
        )
    return proc.stdout


def encode(path: str) -> bytes:
    return path.encode("utf-8", "surrogateescape")


def decode(raw: bytes) -> str:
    return raw.decode("utf-8", "surrogateescape")


@dataclasses.dataclass(frozen=True)
class Entry:
    """One path in a git tree."""

    mode: str
    kind: str
    sha: str


def tree(repo: pathlib.Path, rev: str) -> dict[str, Entry]:
    """Every path in `rev`'s tree, recursively, keyed by its POSIX path."""
    out: dict[str, Entry] = {}
    for record in git(repo, "ls-tree", "-r", "-z", "--full-tree", rev).split(b"\0"):
        if not record:
            continue
        meta, _, path = record.partition(b"\t")
        mode, kind, sha = meta.decode().split()
        out[decode(path)] = Entry(mode, kind, sha)
    return out


def read_blobs(repo: pathlib.Path, shas: Iterable[str]) -> dict[str, bytes]:
    """Blob contents by SHA, in one `cat-file --batch`. Missing ones are left out."""
    wanted = sorted(set(shas))
    if not wanted:
        return {}
    raw = git(repo, "cat-file", "--batch", data=("\n".join(wanted) + "\n").encode())
    out: dict[str, bytes] = {}
    pos = 0
    for sha in wanted:
        end = raw.index(b"\n", pos)
        header = raw[pos:end].decode().split()
        pos = end + 1
        if len(header) == 2 and header[1] == "missing":
            continue
        _, kind, size = header
        size = int(size)
        if kind == "blob":
            out[sha] = raw[pos:pos + size]
        pos += size + 1
    return out


def resolve(repo: pathlib.Path, ref: str) -> str | None:
    """The commit a tag, branch or SHA names in the template, or None."""
    for candidate in (f"refs/tags/{ref}", f"refs/heads/{ref}", f"refs/remotes/origin/{ref}", ref):
        out = git(repo, "rev-parse", "--verify", "-q", f"{candidate}^{{commit}}", ok=(0, 1, 128)).strip()
        if out:
            return out.decode()
    return None


def version_label(repo: pathlib.Path, commit: str, ref: str) -> str:
    """The exact `vX.Y.Z` on a commit when there is one, else the ref and a short SHA."""
    tags = git(repo, "tag", "--points-at", commit).decode().split()
    versions = [t for t in tags if re.fullmatch(r"v\d+\.\d+\.\d+", t)]
    if versions:
        return max(versions, key=lambda t: tuple(int(n) for n in t[1:].split(".")))
    if re.fullmatch(r"[0-9a-f]{7,64}", ref) and commit.startswith(ref):
        return commit[:7]  # a commit named by its own SHA needs no second copy of it
    return f"{ref}@{commit[:7]}"


def newer_objects(repo: pathlib.Path, commit: str) -> set[str]:
    """Everything only the template's NEWER history holds: reachable from a ref that contains `commit`, not from it.

    Divergent history - an old tag left behind by a rewrite - is not newer,
    so a baseline found only there is not mistaken for one from the future.
    """
    refs = [r for r in git(repo, "for-each-ref", "--contains", commit, "--format=%(objectname)").decode().split()
            if r != commit]
    if not refs:
        return set()
    return set(git(repo, "rev-list", "--objects", "--no-object-names", *refs, "--not", commit).decode().split())


# =============================================================================
# Paths
# =============================================================================


def unsafe(path: str) -> str | None:
    """Why a path must never be written, or None when it is safe.

    A git tree cannot hold most of these, but a lock file is plain text that
    anyone with write access can edit, and the cost of checking is nothing.
    """
    if not path or path.startswith("/") or "\\" in path or "\0" in path:
        return "it is not a relative POSIX path"
    try:
        path.encode("utf-8")
    except UnicodeEncodeError:
        return "its name is not valid UTF-8"
    parts = path.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return "it climbs out of the repository or has an empty segment"
    if any(part.lower() == ".git" for part in parts):
        return "it names git's own directory"
    return None


def escape(path: str) -> str:
    """The anchored .gitignore pattern that matches exactly `path` and nothing else."""
    out = re.sub(r"([\\*?\[])", r"\\\1", path)
    if out.endswith(" "):
        out = out[:-1] + "\\ "
    return "/" + out


def unescape(key: str) -> str:
    """The path an anchored, literal entry names: the inverse of `escape`."""
    return re.sub(r"\\(.)", r"\1", key[1:] if key.startswith("/") else key)


def literal(key: str) -> bool:
    """True when an entry names one path rather than a pattern of them."""
    unescaped = re.sub(r"\\.", "", key)
    return not any(ch in unescaped for ch in "*?[") and not key.endswith("/")


# =============================================================================
# The list: .github/template-sync
# =============================================================================


@dataclasses.dataclass(frozen=True)
class Line:
    """One line of a list: a blank, a note, or an entry (on or off)."""

    kind: str  # 'blank' | 'note' | 'entry'
    text: str
    key: str = ""
    on: bool = False


def classify(text: str) -> Line:
    """A note starts `# ` or is a bare `#`. An entry switched off is `#` and no space."""
    if not text.strip():
        return Line("blank", text)
    if text.startswith("#"):
        if len(text) == 1 or text[1] in " \t":
            return Line("note", text)
        return Line("entry", text, text[1:], False)
    return Line("entry", text, text, True)


@dataclasses.dataclass
class ParsedList:
    body: list[Line]
    marker: str | None
    rules: list[str]

    def defaults(self) -> dict[str, bool]:
        out: dict[str, bool] = {}
        for line in self.body:
            if line.kind == "entry":
                out[line.key] = line.on
        return out


def parse_list(text: str | None) -> ParsedList | None:
    if text is None:
        return None
    body: list[Line] = []
    marker = None
    rules: list[str] = []
    for raw in text.splitlines():
        if marker is None and raw.startswith(RULES_MARKER):
            marker = raw
            continue
        if marker is None:
            body.append(classify(raw))
        else:
            rules.append(raw)
    return ParsedList(body, marker, rules)


def merge_list(
    base: str | None,
    target: str,
    ours: str | None,
    *,
    disabled: Iterable[str] = (),
    renames: dict[str, str] | None = None,
    carry_off: dict[str, str] | None = None,
    waiting: Iterable[str] = (),
) -> str:
    """Redraw the list from the template's latest, keeping every choice the owner made.

    A choice is a difference between the owner's copy and the template list it
    was drawn from (`base`): an entry switched off, an entry switched on, a
    line deleted (read as off), and anything the template never wrote - which
    moves under "Your rules", where it wins over everything above it.
    `disabled` names paths this run found deleted by the owner; each is
    switched off where an entry names it exactly, and ruled out with `!`
    where only a pattern does.

    ⚠️ `waiting` NAMES PATHS THE TEMPLATE DROPPED THAT ARE NOT SETTLED: a move
    that conflicted, a deletion held for a token. The template's list no
    longer names them, so without this the redraw dropped their lines, the
    next run read them as unsynced, and the conflict - or the deletion - was
    abandoned without a word. They stay named, switched on, under
    WAITING_NOTE, until a run settles them.

    `renames` carries every choice across a move; `carry_off` carries only
    "off", for a move git could see only by its content - one that left a
    new file at the old path, which may as well be a rewrite and a copy.
    """
    t = parse_list(target)
    b = parse_list(base)
    d = parse_list(ours)
    t_defaults = t.defaults()
    b_defaults = b.defaults() if b else {}

    choices: dict[str, bool] = {}
    # ⚠️ A LINE THE OWNER HAS OFF IS NEVER SWITCHED ON FOR THEM. A template
    # may change its own default either way, but only "off" may reach an
    # owner who never chose: a line off by the owner's hand and then off by
    # the template's default too reads exactly like one following the
    # default, and the template switching it back on restored a file the
    # owner had deleted. Off is the safe direction - it stops writes - so
    # that is the only one a template's default can take an owner in.
    held_off: set[str] = set()
    rules: list[str] = []
    if d is not None:
        mine = d.defaults()
        reference = b_defaults if b is not None else t_defaults
        for key, default in reference.items():
            state = mine.get(key, False)
            if state != default:
                choices[key] = state
            if not state:
                held_off.add(key)

        template_notes = {line.text for line in (b.body if b else []) + t.body if line.kind == "note"}
        template_notes.add(WAITING_NOTE)
        template_keys = set(b_defaults) | set(t_defaults)
        in_waiting = False
        for line in d.body:
            # The waiting section is the engine's - but only the exact paths
            # it writes there. Anything else an owner put under it is a rule
            # of theirs, kept like any other.
            if line.kind == "note" or line.kind == "blank":
                in_waiting = line.text == WAITING_NOTE
            if line.kind == "entry" and in_waiting and line.key.startswith("/") and literal(line.key):
                if not line.on:
                    choices[line.key] = False  # the owner gave up on it: settled as theirs
                    held_off.add(line.key)
                continue
            if line.kind == "entry" and line.key not in template_keys:
                rules.append(line.text)
            elif line.kind == "note" and line.text not in template_notes:
                rules.append(line.text)
        rules.extend(d.rules)

        # After every choice is known, the waiting section's included: a file
        # the owner settled as theirs there carries that across its move too.
        for old, new in (renames or {}).items():
            if escape(old) in choices and escape(new) not in choices:
                choices[escape(new)] = choices[escape(old)]
            if escape(old) in held_off:
                held_off.add(escape(new))
        for old, new in (carry_off or {}).items():
            if escape(old) in held_off and escape(new) not in choices:
                choices[escape(new)] = False
                held_off.add(escape(new))

    off_keys = set()
    for path in sorted(set(disabled)):
        key = escape(path)
        # A rule of the owner's that names the file exactly is switched off
        # where it stands: it would otherwise go on syncing - and restoring -
        # the file they just deleted.
        named = key in rules
        rules = [f"#{key}" if rule == key else rule for rule in rules]
        if key in t_defaults:
            off_keys.add(key)
        elif not named and f"!{key}" not in rules:
            rules.append(f"!{key}")

    out: list[str] = []
    for line in t.body:
        if line.kind == "entry":
            on = choices.get(line.key, line.on and line.key not in held_off) and line.key not in off_keys
            out.append(line.key if on else f"#{line.key}")
        else:
            out.append(line.text)
    while out and not out[-1].strip():
        out.pop()
    held = sorted({escape(p) for p in waiting} - set(t_defaults))
    held = [key for key in held if choices.get(key, True)]
    if held:
        out += ["", WAITING_NOTE, *held]
    out.append("")
    out.append(t.marker or f"{RULES_MARKER} {'-' * 60}")
    while rules and not rules[0].strip():
        rules.pop(0)
    while rules and not rules[-1].strip():
        rules.pop()
    out.extend(rules)
    return "\n".join(out) + "\n"


def exact_on(text: str | None) -> set[str]:
    """The paths a list switches on by a line of their own: what an owner can only have meant."""
    parsed = parse_list(text)
    if parsed is None:
        return set()
    lines = [line for line in parsed.body if line.kind == "entry"] + [classify(rule) for rule in parsed.rules]
    return {unescape(line.key) for line in lines
            if line.kind == "entry" and line.on and line.key.startswith("/") and literal(line.key)}


def honour_choices(redrawn: str, ours: str, reference: str, paths: Iterable[str],
                   renames: dict[str, str] | None = None, *, settled: Iterable[str] = ()) -> tuple[str, set[str]]:
    """Keep every owner's choice per PATH, whatever shape the template gave its list.

    The redraw keeps choices line by line. When the template reshapes its
    list - a pattern where it named files, or files where it had a pattern -
    a choice made on a line that no longer exists has nowhere to stay, and
    the redraw quietly followed the template instead: a file the owner
    switched off was synced again. So each path is compared directly, the
    owner's list against the one it was drawn from (`reference`), and
    wherever the redraw would undo a choice it is written back by name under
    "Your rules". A path git's matcher cannot rule out by name - one under a
    folder a pattern takes whole - is returned to be held off by the run.

    `settled` names paths this run switched off itself - files the owner
    deleted - which no choice in their list as committed may switch back on.
    """
    wanted = sorted(set(paths) - set(settled))
    if not wanted:
        return redrawn, set()
    mine = matched(ours, wanted)
    default = matched(reference, wanted)
    for old, new in (renames or {}).items():
        if old in wanted and new in wanted:
            mine = (mine - {new}) | ({new} if old in mine else set())
            default = (default - {new}) | ({new} if old in default else set())
    chosen_off = {p for p in wanted if p in default and p not in mine}
    chosen_on = {p for p in wanted if p in mine and p not in default}
    now = matched(redrawn, wanted)
    lost_off, lost_on = sorted(chosen_off & now), sorted(chosen_on - now)
    if not lost_off and not lost_on:
        return redrawn, set()
    text = redrawn.rstrip("\n") + "\n"
    text += "".join(f"!{escape(p)}\n" for p in lost_off) + "".join(f"{escape(p)}\n" for p in lost_on)
    return text, set(lost_off) & matched(text, lost_off)


def section_of(lines: list[str], index: int) -> str | None:
    """The `# --- ` heading a list line sits under, or None above the first one."""
    for line in reversed(lines[:index]):
        if line.startswith("# ---"):
            return line
    return None


def amend_list(
    text: str,
    template_list: str | None,
    *,
    added: dict[str, str],
    removed: Iterable[str] = (),
    renamed: dict[str, str] | None = None,
) -> str:
    """This repository's OWN list, still naming every file it ships after a mapped sync.

    A repository synced through a mapping is usually a template itself, and
    its list is the one ITS generated repositories read, so it is amended,
    never redrawn: a file that left loses its line, a moved file's line moves
    with it, and a file that arrived gains one. `added` maps each arrival to
    the template path it came from, and its line copies the template list's
    choice for it - on or off, in the section of the same name, in order -
    so a file the template leaves to its owners is left to them here too.

    ⚠️ THE TEMPLATE'S CHOICE IS READ THE WAY ITS LIST MEANS IT, PATTERNS
    INCLUDED. A file the template names only through `#/assets/**` is a file
    it leaves to owners, and taking "no line of its own" for "not named"
    switched it on here - kept current in every repository generated from
    this one, and named both on and off, which this list's own check refuses.
    And an arrival this list already names, by a line of its own or a pattern,
    gains no line: a second could only repeat this list's choice or
    contradict it.
    """
    lines = text.splitlines()

    def body_end() -> int:
        for i, line in enumerate(lines):
            if line.startswith(RULES_MARKER) or line == WAITING_NOTE:
                return i
        return len(lines)

    def position(key: str) -> int | None:
        for i, line in enumerate(lines[:body_end()]):
            parsed = classify(line)
            if parsed.kind == "entry" and parsed.key == key:
                return i
        return None

    def insert(key: str, on: bool, section: str | None) -> None:
        if position(key) is not None:
            return
        end = body_end()
        if section is None or section not in lines[:end]:
            # No section of that name here: the one holding the first entry
            # in the same state, so an arrival lands among its own kind.
            listed = [i for i in range(end) if classify(lines[i]).kind == "entry"]
            alike = [i for i in listed if classify(lines[i]).on == on] or listed
            if not alike:
                lines.insert(end, key if on else f"#{key}")
                return
            section = section_of(lines, alike[0])
        start = lines.index(section) + 1 if section is not None else 0
        stop = next((i for i in range(start, end) if lines[i].startswith("# ---")), end)
        entries = [i for i in range(start, stop) if classify(lines[i]).kind == "entry"]
        after = [i for i in entries if classify(lines[i]).key > key]
        at = after[0] if after else (entries[-1] + 1 if entries else start)
        lines.insert(at, key if on else f"#{key}")

    template_lines = (template_list or "").splitlines()
    rules_at = next((i for i, line in enumerate(template_lines) if line.startswith(RULES_MARKER)),
                    len(template_lines))

    moving: list[tuple[str, bool, str | None]] = []
    for old, new in sorted((renamed or {}).items()):
        at = position(escape(old))
        if at is not None:
            moving.append((escape(new), classify(lines[at]).on, section_of(lines, at)))
            del lines[at]
    for path in sorted(set(removed)):
        at = position(escape(path))
        if at is not None:
            del lines[at]
    for key, on, section in moving:
        insert(key, on, section)
    arrivals = sorted(added.items())
    named_here = naming(lines[:body_end()], [path for path, _ in arrivals])
    choices = naming(template_lines[:rules_at], [origin for _, origin in arrivals])
    for path, origin in arrivals:
        if path not in named_here:
            on, section = choices.get(origin, (True, None))
            insert(escape(path), on, section)
    return "\n".join(lines) + "\n"


_ISOLATED = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
_MATCH_REPO: pathlib.Path | None = None


def _match_repo() -> pathlib.Path:
    """An empty repository to evaluate lists in, so no real .gitignore interferes."""
    global _MATCH_REPO
    if _MATCH_REPO is None:
        _MATCH_REPO = pathlib.Path(tempfile.mkdtemp(prefix="template-sync-match-"))
        atexit.register(shutil.rmtree, _MATCH_REPO, True)
        git(_MATCH_REPO, "init", "-q", env=_ISOLATED)
    return _MATCH_REPO


def matched(list_text: str, paths: Iterable[str]) -> set[str]:
    """The paths a list keeps current, decided by git's own .gitignore matcher.

    Git rather than a reimplementation, so the file means exactly what the same
    lines would mean in a .gitignore: anchoring, `**`, negation, the last match
    winning. A list here is an allowlist, so "ignored" reads as "kept current".
    """
    return {path for path, (_, pattern) in deciding(list_text, paths).items() if not pattern.startswith("!")}


def deciding(list_text: str, paths: Iterable[str]) -> dict[str, tuple[int, str]]:
    """For each path a list's lines match, the line that decides it: its number, from 1, and its pattern.

    Git's own matcher, as in `matched`, so the last matching line wins. A path
    no line matches is left out.
    """
    wanted = sorted(set(paths))
    if not wanted:
        return {}
    repo = _match_repo()
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".list", delete=False) as handle:
        handle.write(list_text)
        list_file = handle.name
    try:
        raw = git(
            repo,
            "-c", f"core.excludesFile={list_file}",
            "check-ignore", "--no-index", "-v", "-n", "-z", "--stdin",
            data=b"".join(encode(p) + b"\0" for p in wanted),
            ok=(0, 1),
            env=_ISOLATED,
        )
    finally:
        os.unlink(list_file)
    fields = raw.split(b"\0")
    out: dict[str, tuple[int, str]] = {}
    for i in range(0, len(fields) - 3, 4):
        pattern = decode(fields[i + 2])
        if pattern:
            out[decode(fields[i + 3])] = (int(decode(fields[i + 1])), pattern)
    return out


def naming(lines: list[str], paths: Iterable[str]) -> dict[str, tuple[bool, str | None]]:
    """For each path a list's entries name, on or off, the state and section of the entry that decides it.

    Every entry is read as the pattern it carries, whatever its state, so
    `#/assets/**` names each file under assets/ just as `/assets/**` would:
    which line speaks for a file is the question, and the last match wins, as
    in a .gitignore. A negation that decides names its file off. A path no
    entry names is left out.
    """
    entries = [classify(line) for line in lines]
    text = "\n".join(line.key if line.kind == "entry" else "" for line in entries) + "\n"
    return {path: (entries[number - 1].on and not pattern.startswith("!"), section_of(lines, number - 1))
            for path, (number, pattern) in deciding(text, paths).items()}


# =============================================================================
# Identity: init-template.py's own rules
# =============================================================================


def _load_init():
    path = pathlib.Path(__file__).with_name("init-template.py")
    spec = importlib.util.spec_from_file_location("init_template", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


INIT = _load_init()


@dataclasses.dataclass(frozen=True)
class Identity:
    """What initialisation stamped: kept in the lock so every run rewrites alike."""

    owner: str
    repository: str
    name: str
    year: int


def rewriter(identity: Identity | None, template: str) -> Callable[[str, bytes], bytes]:
    """What init did to each file, as a function of its path and content."""
    if identity is None:
        return lambda _path, data: data
    template_owner = template.split("/", 1)[0]

    def apply(path: str, data: bytes) -> bytes:
        return INIT.initialised(
            path,
            data,
            owner=identity.owner,
            repo=identity.repository,
            display=identity.name,
            template_owner=template_owner,
            year=identity.year,
        )

    return apply


# =============================================================================
# A mapping: for a repository defined as a delta of its template
# =============================================================================
#
# Some repositories are not generated from a template but DEFINED against
# one: tannergolden/repo is tannergolden/path with five permitted
# differences, written down as data in its own contract. A mapping is that
# contract in the form this script reads - which template paths never come
# here, which folders sit somewhere else, and which text differs inside them
# - and with one, the same per-file merge keeps such a repository current
# with its template while every difference it is defined by survives.
#
# ⚠️ IT IS NOT A LIST, AND THERE IS NO OWNER TO ASK. The contract already
# says what may differ, so everything it does not leave out is synced. A
# file missing here is drift rather than a choice, so it is reported and
# never switched off - and never re-created either.

MAP_FORMAT = 1


def covers(prefixes: Iterable[str], path: str) -> bool:
    """True when `path` is one of `prefixes`, or sits underneath one."""
    return any(path == prefix or path.startswith(prefix + "/") for prefix in prefixes)


@dataclasses.dataclass(frozen=True)
class Mapping:
    name: str  # what the sync is called here, as its report and its issue say
    source: str  # the file the mapping was written from, which a fix belongs in
    lock: str  # this sync's own lock
    list: str  # this repository's own list, amended as files arrive and leave; "" for none
    exclude: tuple[str, ...]  # template paths, or folders, that never come here
    relocate: tuple[tuple[str, str], ...]  # (template folder, the folder it lives in here)
    replace: tuple[tuple[str, str, str], ...]  # (template folder, its text, this repository's)

    def here(self, path: str) -> str | None:
        """Where a template path lives in this repository, or None when it never comes here."""
        if covers(self.exclude, path):
            return None
        for source, dest in self.relocate:
            if covers([source], path):
                return dest + path[len(source):]
        return path

    def there(self, path: str) -> str | None:
        """The template path a path here comes from, or None when no template path could."""
        for source, dest in self.relocate:
            if covers([dest], path):
                origin = source + path[len(dest):]
                return origin if self.here(origin) == path else None
        return path if self.here(path) == path else None

    def content(self, path: str, data: bytes) -> bytes:
        """A template file's bytes as this repository holds them. Text only: a binary file passes as is."""
        if b"\0" in data:
            return data
        for source, old, new in self.replace:
            if covers([source], path):
                data = data.replace(old.encode("utf-8"), new.encode("utf-8"))
        return data


def load_mapping(text: str, name: str = "the mapping") -> Mapping:
    """Parse and validate a mapping, as strictly as a lock: a wrong one syncs the wrong files."""
    try:
        doc = json.loads(text)
    except ValueError as exc:
        raise SyncError(f"{name} is not valid JSON ({exc}).") from None
    if not isinstance(doc, dict) or doc.get("format") != MAP_FORMAT:
        raise SyncError(f"{name} must be a JSON object of format {MAP_FORMAT}.")
    unknown = set(doc) - {"format", "name", "source", "lock", "list", "exclude", "relocate", "replace"}
    if unknown:
        raise SyncError(f"{name} has keys this script does not know: {sorted(unknown)}.")

    def text_field(key: str, *, path: bool, required: bool) -> str:
        value = doc.get(key, "")
        if not isinstance(value, str) or (required and not value):
            raise SyncError(f"{name}: `{key}` must be a{' non-empty' if required else ''} string.")
        if path and value and unsafe(value):
            raise SyncError(f"{name}: `{key}` names {value!r}, which is unsafe because {unsafe(value)}.")
        return value

    def paths(values: object, key: str) -> list[str]:
        if not isinstance(values, list) or not all(isinstance(v, str) and v for v in values):
            raise SyncError(f"{name}: `{key}` must be a list of paths.")
        for value in values:
            if unsafe(value):
                raise SyncError(f"{name}: `{key}` names {value!r}, which is unsafe because {unsafe(value)}.")
        return values

    label = text_field("name", path=False, required=True)
    source = text_field("source", path=True, required=False)
    lock = text_field("lock", path=True, required=True)
    own_list = text_field("list", path=True, required=False)
    if lock in NEVER or lock == own_list:
        raise SyncError(f"{name}: `lock` must be a file of its own, not {lock}.")
    exclude = paths(doc.get("exclude", []), "exclude")
    relocate = doc.get("relocate", {})
    if not isinstance(relocate, dict):
        raise SyncError(f"{name}: `relocate` must map template folders to folders here.")
    pairs = list(zip(paths(list(relocate), "relocate"), paths(list(relocate.values()), "relocate")))
    # Every folder named, on either side, is disjoint from every other: then
    # each path has one place here and one origin there, and nothing chains.
    folders = [folder for pair in pairs for folder in pair]
    for i, a in enumerate(folders):
        for b in folders[i + 1:]:
            if covers([a], b) or covers([b], a):
                raise SyncError(f"{name}: `relocate` folders must not overlap, and {a} and {b} do.")
    replace = doc.get("replace", [])
    if not isinstance(replace, list):
        raise SyncError(f"{name}: `replace` must be a list.")
    replacements = []
    for item in replace:
        if (not isinstance(item, dict) or set(item) != {"under", "from", "to"}
                or not all(isinstance(item[k], str) for k in item) or not item["from"] or not item["under"]):
            raise SyncError(f"{name}: each `replace` entry needs `under`, a non-empty `from`, and `to`.")
        paths([item["under"]], "replace")
        replacements.append((item["under"], item["from"], item["to"]))
    return Mapping(label, source, lock, own_list, tuple(exclude), tuple(pairs), tuple(replacements))


# =============================================================================
# The lock: .github/template-sync.lock
# =============================================================================


@dataclasses.dataclass(frozen=True)
class FileState:
    """Where one file was last merged from: a template blob, and its mode."""

    blob: str
    mode: str
    deleted: bool = False


@dataclasses.dataclass
class Lock:
    template: str
    version: str
    commit: str
    identity: Identity | None
    files: dict[str, FileState]
    pending: dict[str, dict]


def load_lock(text: str, name: str = LOCK_PATH) -> Lock:
    """Parse and validate a lock, naming the first thing wrong with it.

    Strict on purpose. A lock read loosely is a baseline guessed, and a wrong
    baseline merges the owner's own edits away as if the template made them.
    """
    try:
        doc = json.loads(text)
    except ValueError as exc:
        raise SyncError(f"{name} is not valid JSON ({exc}). Restore it from history.") from None
    if not isinstance(doc, dict):
        raise SyncError(f"{name} must be a JSON object.")
    if doc.get("format") != LOCK_FORMAT:
        raise SyncError(f"{name} is format {doc.get('format')!r}; this script reads format {LOCK_FORMAT}.")
    unknown = set(doc) - {"//", "format", "template", "version", "commit", "identity", "files", "pending"}
    if unknown:
        raise SyncError(f"{name} has keys this script does not know: {sorted(unknown)}.")
    # Typed before defaulted: `value or ""` would read an empty list, a zero
    # or a false as "absent" and carry on, which is the loose read this
    # function exists to refuse.
    template = doc.get("template", "")
    if not isinstance(template, str) or (template and not TEMPLATE_NAME.match(template)):
        raise SyncError(f"{name} names {template!r} as its template, which is not OWNER/REPO.")
    commit = doc.get("commit", "")
    if not isinstance(commit, str) or (commit and not SHA.match(commit)):
        raise SyncError(f"{name} records {commit!r} as its commit, which is not a SHA.")
    version = doc.get("version", "")
    if not isinstance(version, str):
        raise SyncError(f"{name}: `version` must be a string.")
    identity = None
    raw_identity = doc.get("identity")
    if raw_identity is not None:
        if not isinstance(raw_identity, dict) or set(raw_identity) != {"owner", "repository", "name", "year"}:
            raise SyncError(f"{name}: `identity` needs exactly owner, repository, name and year.")
        if not all(isinstance(raw_identity[k], str) and raw_identity[k] for k in ("owner", "repository", "name")):
            raise SyncError(f"{name}: `identity` owner, repository and name must be non-empty strings.")
        if (not isinstance(raw_identity["year"], int) or isinstance(raw_identity["year"], bool)
                or not 1970 <= raw_identity["year"] <= 9999):
            raise SyncError(f"{name}: `identity.year` must be a four-digit year.")
        identity = Identity(**raw_identity)
    raw_files = doc.get("files")
    if not isinstance(raw_files, dict):
        raise SyncError(f"{name}: `files` must be an object mapping paths to their baselines.")
    files: dict[str, FileState] = {}
    for path, state in raw_files.items():
        reason = unsafe(path)
        if reason:
            raise SyncError(f"{name} names {path!r}, which is unsafe because {reason}.")
        if not isinstance(state, dict) or not {"blob", "mode"} <= set(state) <= {"blob", "mode", "deleted"}:
            raise SyncError(f"{name}: {path} needs `blob` and `mode`, and nothing but `deleted` besides.")
        if not isinstance(state["blob"], str) or not SHA.match(state["blob"]):
            raise SyncError(f"{name}: {path} has blob {state['blob']!r}, which is not a SHA.")
        if state["mode"] not in MODES:
            raise SyncError(f"{name}: {path} has mode {state['mode']!r}; only 100644 and 100755 are synced.")
        deleted = state.get("deleted", False)
        if not isinstance(deleted, bool):
            raise SyncError(f"{name}: {path} has a `deleted` that is not true or false.")
        files[path] = FileState(state["blob"], state["mode"], deleted)
    pending = doc.get("pending", {})
    if not isinstance(pending, dict) or not all(isinstance(v, dict) for v in pending.values()):
        raise SyncError(f"{name}: `pending` must map paths to objects.")
    return Lock(template, version, commit, identity, files, pending)


def dump_lock(lock: Lock, writer: str = "🔄 Template Sync") -> str:
    doc: dict = {
        # Read by nothing here: it is what a person - and a folder index -
        # sees first when they open the file.
        "//": f"Where each file here was last synced from. Written by {writer} alone; never edit it by hand.",
        "format": LOCK_FORMAT,
        "template": lock.template,
        "version": lock.version,
        "commit": lock.commit,
        "identity": dataclasses.asdict(lock.identity) if lock.identity else None,
        "files": {
            path: {"blob": s.blob, "mode": s.mode, **({"deleted": True} if s.deleted else {})}
            for path, s in sorted(lock.files.items())
        },
        "pending": {path: lock.pending[path] for path in sorted(lock.pending)},
    }
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


# =============================================================================
# Planning: one decision per path, and no side effects
# =============================================================================


@dataclasses.dataclass(frozen=True)
class Side:
    """One version of one file. `sha` is the template blob it came from, if any."""

    mode: str
    data: bytes
    sha: str = ""


MISSING = Side("", b"", "missing")  # a baseline the lock names and the template no longer has
REMOVE = "remove"


@dataclasses.dataclass
class Decision:
    path: str
    outcome: str
    write: Side | None = None
    delete: bool = False
    # None leaves the lock entry alone; REMOVE drops it; a FileState replaces it.
    state: FileState | None | str = None
    detail: str = ""
    diff: str = ""
    pair: str = ""  # the other half of a move


def merge3(ours: bytes, base: bytes, theirs: bytes) -> tuple[bytes, bool]:
    """git merge-file, so a merge here means exactly what it means anywhere in git."""
    with tempfile.TemporaryDirectory(prefix="template-sync-merge-") as tmp:
        root = pathlib.Path(tmp)
        for name, data in (("ours", ours), ("base", base), ("theirs", theirs)):
            (root / name).write_bytes(data)
        proc = subprocess.run(
            ["git", "merge-file", "-p", "-q", "-L", "yours", "-L", "base", "-L", "template",
             str(root / "ours"), str(root / "base"), str(root / "theirs")],
            capture_output=True,
            check=False,
        )
    if proc.returncode < 0 or proc.returncode > 127:
        raise SyncError(f"git merge-file failed: {proc.stderr.decode('utf-8', 'replace').strip()}")
    return proc.stdout, proc.returncode == 0


def binary(*datas: bytes) -> bool:
    return any(b"\0" in data for data in datas)


def merge_mode(ours: str, base: str, theirs: str) -> str:
    """The executable bit merges like a line: whoever changed it wins, the owner on a tie."""
    return theirs if ours == base else ours


def udiff(path: str, before: bytes, after: bytes) -> str:
    """The template's change, as a unified diff bounded for a pull request body."""
    if binary(before, after):
        return "(binary file)"
    lines = list(difflib.unified_diff(
        before.decode("utf-8", "replace").splitlines(),
        after.decode("utf-8", "replace").splitlines(),
        f"a/{path}", f"b/{path}", lineterm="",
    ))
    if len(lines) > DIFF_LINES:
        lines = [*lines[:DIFF_LINES], f"... {len(lines) - DIFF_LINES} more line(s)"]
    return "\n".join(lines)


def state_of(side: Side) -> FileState:
    return FileState(side.sha, side.mode)


def decide(
    path: str,
    base: Side | None,
    target: Side | None,
    ours: Side | None,
    *,
    synced: bool,
    was_deleted: bool,
) -> Decision:
    """The one decision for one path. Pure: every input is passed in.

    `base` is what the template held when this file last merged (None for a
    file new to this repository, MISSING when the lock names a blob the
    template no longer has), `target` what it holds now, `ours` what this
    repository holds. Template sides are already in the owner's identity.
    """
    if not synced:
        # A file the template stopped shipping is the owner's from here on,
        # so its baseline goes; one still shipped keeps it, for the day the
        # owner switches it back on and it merges rather than overwrites.
        return Decision(path, "not-synced", state=REMOVE if target is None else None)

    if target is None:  # the template no longer ships it
        if ours is None:
            return Decision(path, "gone", state=REMOVE)
        if base is not None and base is not MISSING and ours.data == base.data:
            return Decision(path, "deleted", delete=True, state=REMOVE)
        return Decision(path, "kept", state=REMOVE,
                        detail="The template removed this file and you had changed it, so it stays, as yours.")

    if ours is None:
        if base is None:
            return Decision(path, "added", write=target, state=state_of(target))
        if was_deleted:
            return Decision(path, "restored", write=target, state=state_of(target),
                            detail="You switched this file back on in .github/template-sync.")
        recorded = target if base is MISSING else base
        return Decision(path, "owner-deleted", state=FileState(recorded.sha, recorded.mode, True),
                        detail="You deleted this file, so it is now switched off in .github/template-sync.")

    if base is MISSING:
        if ours.data == target.data:
            if ours.mode == target.mode:
                return Decision(path, "current", state=state_of(target))
            return Decision(path, "updated", write=Side(target.mode, ours.data), state=state_of(target))
        return Decision(path, "conflict", detail=(
            "The template no longer has the version this file was last synced from, so your "
            "changes cannot be told apart from the template's. Make the file match the "
            "template's version to resume syncing it, or switch it off."),
            diff=udiff(path, ours.data, target.data))

    if base is None:
        if ours.data == target.data:
            if ours.mode == target.mode:
                return Decision(path, "current", state=state_of(target))
            return Decision(path, "updated", write=Side(target.mode, ours.data), state=state_of(target))
        return Decision(path, "conflict", detail=(
            "The template added a file here and you already have a different one. Yours is "
            "untouched; make it match the template's, or switch the path off."),
            diff=udiff(path, ours.data, target.data))

    mode = merge_mode(ours.mode, base.mode, target.mode)
    if base.data == target.data or ours.data == target.data:
        # Nothing for the content to do: the template did not change it, or
        # the owner already has exactly what the template now holds.
        if mode == ours.mode:
            kind = "unchanged" if base.data == target.data else "current"
            return Decision(path, kind, state=state_of(target))
        return Decision(path, "updated", write=Side(mode, ours.data), state=state_of(target))
    if ours.data == base.data:
        return Decision(path, "updated", write=Side(mode, target.data), state=state_of(target))
    if binary(ours.data, base.data, target.data):
        return Decision(path, "conflict", detail=(
            "You and the template both changed this binary file. Yours is untouched."),
            diff=udiff(path, base.data, target.data))
    merged, clean = merge3(ours.data, base.data, target.data)
    if clean:
        return Decision(path, "merged", write=Side(mode, merged), state=state_of(target))
    return Decision(path, "conflict", detail=(
        "You and the template changed the same lines. Your file is untouched; the template's "
        "change is below. Make those lines match it on your default branch - not on the sync "
        "branch, which each run replaces - and the next sync stops asking. To keep yours, switch "
        "the file off."),
        diff=udiff(path, base.data, target.data))


def renames_of(base: dict[str, Side], target: dict[str, Side]) -> dict[str, str]:
    """Files the template moved: gone from one path, arrived at another, same content.

    Exact matches only, and only one-to-one. A similarity guess that paired the
    wrong two files would move the owner's edits into a file they never
    touched, while a missed rename costs only a delete and an add.

    Decided from the template's side alone, before anything is judged synced:
    a move has to carry the owner's choice with it, so a file they switched
    off or deleted does not come back under its new name.
    """
    gone = {p: s for p, s in base.items() if p not in target and s is not MISSING}
    arrived = {p: s for p, s in target.items() if p not in base}
    by_content: dict[bytes, list[str]] = {}
    for path, side in sorted(arrived.items()):
        by_content.setdefault(side.data, []).append(path)
    sources: dict[bytes, list[str]] = {}
    for path, side in sorted(gone.items()):
        sources.setdefault(side.data, []).append(path)
    return {
        olds[0]: by_content[data][0]
        for data, olds in sources.items()
        if len(olds) == 1 and len(by_content.get(data, [])) == 1
    }


def rewritten(before: bytes, after: bytes) -> bool:
    """True when a path's new content no longer resembles its old: the same name, another file."""
    if before == after:
        return False
    if binary(before, after):
        return True
    return difflib.SequenceMatcher(None, before.splitlines(), after.splitlines(), autojunk=False).ratio() < 0.5


def template_moves(template_dir: pathlib.Path, known: dict[str, FileState],
                   commit: str) -> tuple[dict[str, str], dict[str, str]]:
    """The moves git itself sees between this repository's baselines and the target.

    The baselines are laid out as a tree of their own, through a throwaway
    index, and diffed against the target with git's rename detection: the
    same `-M` a merge uses, so a file the template moved AND edited is still
    recognised as moved. Exact-content matching alone missed exactly the case
    that mattered - a file the owner switched off, which the template kept
    editing and then moved, came back under its new name, switched on.

    ⚠️ A MOVE CAN LEAVE A NEW FILE BEHIND. A template that moves a file and,
    in the same release, puts a different one at the old path gives git no
    rename to see: its source still exists. So a path whose content now no
    longer resembles its baseline is left out of the target's side before
    git looks. If the old content lives on somewhere new, git calls that a
    move; if it does not, nothing is found and nothing changes. Without this,
    a file the owner had deleted came back under its new name.

    Such a pair is returned APART from the true moves, because content alone
    cannot tell "moved, and a new file put in its place" from "rewritten, and
    a copy added": it carries an owner's "off" across and nothing else, and
    the file at the old path is never taken away from them.
    """
    entries = {p: s for p, s in known.items() if p not in NEVER and not unsafe(p)}
    if not entries:
        return {}, {}
    check = git(template_dir, "cat-file", "--batch-check",
                data=("\n".join(sorted({s.blob for s in entries.values()})) + "\n").encode()).decode()
    present = {line.split()[0] for line in check.splitlines() if not line.endswith("missing")}
    rows = b"".join(encode(f"{s.mode} {s.blob}\t{p}") + b"\0" for p, s in sorted(entries.items())
                    if s.blob in present)
    if not rows:
        return {}, {}
    target = tree(template_dir, commit)
    changed = sorted(p for p, s in entries.items() if s.blob in present and p in target
                     and target[p].kind == "blob" and target[p].sha != s.blob)
    blobs = read_blobs(template_dir, [entries[p].blob for p in changed] + [target[p].sha for p in changed])
    replaced = {p for p in changed if rewritten(blobs.get(entries[p].blob, b""), blobs.get(target[p].sha, b""))}
    with tempfile.TemporaryDirectory(prefix="template-sync-index-") as tmp:
        env = {"GIT_INDEX_FILE": str(pathlib.Path(tmp) / "index")}
        git(template_dir, "update-index", "-z", "--index-info", data=rows, env=env)
        previous = git(template_dir, "write-tree", env=env).decode().strip()
        destination = commit
        if replaced:
            kept = b"".join(encode(f"{e.mode} {e.sha}\t{p}") + b"\0" for p, e in sorted(target.items())
                            if p not in replaced)
            env = {"GIT_INDEX_FILE": str(pathlib.Path(tmp) / "target")}
            if kept:
                git(template_dir, "update-index", "-z", "--index-info", data=kept, env=env)
            destination = git(template_dir, "write-tree", env=env).decode().strip()
    fields = git(template_dir, "diff-tree", "-r", "-z", "-M", "--diff-filter=R", "--name-status",
                 previous, destination).split(b"\0")
    moves: dict[str, str] = {}
    i = 0
    while i + 2 < len(fields):
        if fields[i].startswith(b"R"):
            moves[decode(fields[i + 1])] = decode(fields[i + 2])
            i += 3
        else:
            i += 1
    found = {old: new for old, new in moves.items() if new not in NEVER and not unsafe(new)}
    return ({old: new for old, new in found.items() if old not in replaced},
            {old: new for old, new in found.items() if old in replaced})


def plan(
    base: dict[str, Side],
    target: dict[str, Side],
    ours: dict[str, Side],
    *,
    synced: set[str],
    deleted: set[str] = frozenset(),
    special: set[str] = frozenset(),
    defer: Callable[[str], bool] = lambda _p: False,
    moves: dict[str, str] | None = None,
    replaced: dict[str, str] | None = None,
) -> list[Decision]:
    """Every decision for every path the template ships or shipped.

    `base` holds an entry for every path the lock knows (MISSING when its blob
    is gone), so a path absent from it is new to this repository. `special`
    names paths this repository holds as a symlink or submodule, which are
    never written over. A move is carried out only when both of its paths
    are synced; otherwise each path is decided on its own.
    """
    decisions: dict[str, Decision] = {}
    if moves is None:
        moves = renames_of(base, target)
    for old, new in (replaced or {}).items():
        # The old path's content lives on at a new one, and something else
        # took its place. Only a deletion is carried across: the content the
        # owner deleted is not re-created under its new name. Everything else
        # is decided path by path below - the file at the old path is never
        # taken from an owner who edited it, since this may as well be a
        # rewrite and a copy.
        if (new in synced and new not in ours and new not in special and old not in ours
                and base.get(old) not in (None, MISSING)):
            decisions[new] = Decision(new, "owner-deleted", state=FileState(target[new].sha, target[new].mode, True),
                                      detail=f"It carries on `{old}`, which you deleted, so it is switched off "
                                             "in .github/template-sync.")
    for old, new in moves.items():
        if old not in synced or new not in synced:
            continue
        if old not in ours and new not in ours and base.get(old) not in (None, MISSING):
            # The owner deleted the file while the template was moving it.
            # It was the same file, so it stays deleted under its new name
            # too, switched off there like any other deletion.
            decisions[old] = Decision(old, "gone", state=REMOVE)
            decisions[new] = Decision(new, "owner-deleted", state=FileState(target[new].sha, target[new].mode, True),
                                      detail="You deleted this file before the template moved it here, so it "
                                             "is switched off in .github/template-sync.")
            continue
        if old in ours and new not in ours and new not in special:
            result = decide(new, base[old], target[new], ours[old], synced=True, was_deleted=False)
            if result.outcome != "conflict":
                write = result.write or Side(merge_mode(ours[old].mode, base[old].mode, target[new].mode),
                                             ours[old].data)
                edited = ours[old].data != base[old].data
                decisions[old] = Decision(old, "moved", delete=True, state=REMOVE, pair=new, detail=(
                    f"The template moved this file to `{new}`" + (", and your changes came with it."
                                                                  if edited else ".")))
                decisions[new] = Decision(new, "moved-here", write=write, state=state_of(target[new]), pair=old)
            else:
                decisions[old] = Decision(old, "conflict", pair=new, detail=(
                    f"The template moved this file to `{new}`, and your changes to it do not merge "
                    "into the new version. Yours is untouched at the old path."),
                    diff=udiff(old, base[old].data, target[new].data))
                decisions[new] = Decision(new, "waiting", pair=old, detail=f"Waits on the conflict at `{old}`.")
    for path in sorted((set(base) | set(target)) - NEVER):
        if path in decisions:
            continue
        reason = unsafe(path)
        if reason:
            decisions[path] = Decision(path, "unsafe", detail=f"Skipped: the path is unsafe because {reason}.")
            continue
        decisions[path] = decide(
            path,
            base.get(path),
            target.get(path),
            ours.get(path),
            synced=path in synced,
            was_deleted=path in deleted,
        )
        if path in special and decisions[path].outcome not in ("not-synced", "gone"):
            decisions[path] = Decision(path, "conflict", detail=(
                "This repository has a symlink or submodule here, which a sync never replaces."))

    clash_check(decisions, ours, special)
    for path, decision in list(decisions.items()):
        if decision.outcome == "deferred" or not (decision.write is not None or decision.delete):
            continue
        if defer(path) or (decision.pair and defer(decision.pair)):
            for name in filter(None, (path, decision.pair)):
                decisions[name] = Decision(name, "deferred", detail=(
                    "A workflow file, and this run's token cannot write workflows. Set a "
                    "BOT_ACCESS_TOKEN that can - the `workflow` scope, or Workflows write - and the "
                    "next sync delivers it."),
                    diff=decisions[name].diff)
    return [decisions[p] for p in sorted(decisions)]


def clash_check(decisions: dict[str, Decision], ours: dict[str, Side], special: set[str]) -> None:
    """Turn a write into a conflict where a file and a directory would share a name."""
    deleting = {p for p, d in decisions.items() if d.delete}
    writing = {p for p, d in decisions.items() if d.write is not None}
    final = ((set(ours) | set(special)) - deleting) | writing
    for path in sorted(writing):
        parts = path.split("/")
        prefixes = {"/".join(parts[:i]) for i in range(1, len(parts))}
        if prefixes & final or any(other.startswith(path + "/") for other in final):
            pair = decisions[path].pair
            decisions[path] = Decision(path, "conflict", detail=(
                f"`{path}` would need a file where a directory is, or the reverse. Nothing was "
                "written; move one of them and the next sync delivers it."))
            if pair and decisions.get(pair) and decisions[pair].outcome == "moved":
                decisions[pair] = Decision(pair, "waiting", detail=f"Waits on the conflict at `{path}`.")


# =============================================================================
# Applying a plan to the working tree
# =============================================================================


def apply(repo: pathlib.Path, writes: dict[str, Side], deletes: Iterable[str]) -> None:
    """Write through git's index, so attributes like eol apply as on any checkout."""
    root = repo.resolve()
    for path in sorted(writes) + sorted(deletes):
        reason = unsafe(path)
        if reason:
            raise SyncError(f"Refusing to touch {path!r}: {reason}.")
        for parent in pathlib.PurePosixPath(path).parents:
            if str(parent) != "." and (root / parent).is_symlink():
                raise SyncError(f"Refusing to touch {path!r}: {parent} is a symlink.")
        if (root / path).is_symlink():
            raise SyncError(f"Refusing to touch {path!r}: it is a symlink.")
    gone = sorted(set(deletes))
    if gone:
        git(root, "--literal-pathspecs", "rm", "-q", "-f", "--ignore-unmatch",
            "--pathspec-from-file=-", "--pathspec-file-nul", data=b"".join(encode(p) + b"\0" for p in gone))
    if not writes:
        return
    info = []
    for path, side in sorted(writes.items()):
        sha = git(root, "hash-object", "-w", "--stdin", data=side.data).decode().strip()
        info.append(encode(f"{side.mode} {sha}\t{path}") + b"\0")
    git(root, "update-index", "-z", "--index-info", data=b"".join(info))
    git(root, "checkout-index", "-f", "-z", "--stdin", data=b"".join(encode(p) + b"\0" for p in sorted(writes)))


# =============================================================================
# Reporting
# =============================================================================

HEADINGS = (
    ("conflict", "⚠️ Needs you"),
    ("deferred", "⏸️ Waiting on a token"),
    ("updated", "✅ Updated to the template's version"),
    ("merged", "🔀 Merged with your changes"),
    ("added", "🆕 Added"),
    ("restored", "♻️ Switched back on and restored"),
    ("moved", "🚚 Moved by the template"),
    ("deleted", "🗑️ Removed, as the template removed it"),
    ("kept", "📌 Kept as yours after the template removed it"),
    ("owner-deleted", "🙈 Switched off, because you deleted it"),
    ("held-off", "✋ Held off, as you chose"),
    ("unsafe", "⛔ Skipped as unsafe"),
)
EXPLAINED = frozenset({"conflict", "deferred", "kept", "unsafe", "restored", "owner-deleted", "moved", "held-off"})


def render_report(*, template: str, version: str, previous: str, decisions: list[Decision],
                  list_changed: bool, mapping: Mapping | None = None) -> str:
    groups: dict[str, list[Decision]] = {}
    for decision in decisions:
        groups.setdefault(decision.outcome, []).append(decision)
    lines = [f"### {mapping.name if mapping else '🔄 Template Sync'}", ""]
    origin = f"`{template}` **{version}**"
    lines.append(f"{origin}, synced from {previous}." if previous and previous != version else f"{origin}.")
    lines.append("")
    counted = [(title, len(groups[key])) for key, title in HEADINGS if groups.get(key)]
    if counted:
        lines += ["| Outcome | Files |", "| :------ | ----: |"]
        lines += [f"| {title} | {count} |" for title, count in counted]
        lines.append("")
    else:
        lines += ["Everything synced is already current.", ""]
    if list_changed and mapping:
        lines += [f"`{mapping.list}` was amended so it still names every file this repository ships.", ""]
    elif list_changed:
        lines += ["`.github/template-sync` was redrawn from the template's latest list. Every "
                  "choice you made in it is kept.", ""]
    for key, title in HEADINGS:
        items = groups.get(key)
        if not items:
            continue
        lines += [f"#### {title}", ""]
        for d in items:
            lines.append(f"- `{d.path}`" + (f" - {d.detail}" if d.detail and key in EXPLAINED else ""))
            if d.diff and key == "conflict":
                # Longer than any backtick run inside: a Markdown file's own
                # fences would otherwise close this one partway through.
                fence = "`" * max(3, 1 + max((len(run) for run in re.findall(r"`+", d.diff)), default=0))
                lines += ["", "  <details><summary>The template's change</summary>", "", f"  {fence}diff"]
                lines += [f"  {ln}" for ln in d.diff.splitlines()]
                lines += [f"  {fence}", "", "  </details>", ""]
        lines.append("")
    if mapping:
        lines += [
            "> [!TIP]",
            f"> `{mapping.source or 'The mapping'}` says how this repository differs from `{template}`.",
            "> Everything it does not set apart is synced; a difference belongs there, not in a file.",
        ]
    else:
        lines += [
            "> [!TIP]",
            "> `.github/template-sync` names every path the template ships. Put a `#` in front of",
            "> one to keep it as yours, or add a rule under **Your rules**.",
        ]
    return "\n".join(lines) + "\n"


def pr_body(report: str) -> str:
    """The report as a pull request can carry it: GitHub refuses a body over 65,536 characters.

    Cut between items, never inside one, so no code fence or <details> is
    left open; the run's step summary keeps all of it.
    """
    if len(report) <= REPORT_LIMIT:
        return report
    note = "\n... and more: the run's step summary lists every file.\n"
    cut = report.rfind("\n- `", 0, REPORT_LIMIT - len(note))
    return report[:cut if cut > 0 else REPORT_LIMIT - len(note)].rstrip() + "\n" + note


def write_output(name: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        if "\n" in value:
            delimiter = "TEMPLATE_SYNC_EOF"
            while delimiter in value:
                delimiter += "_"
            handle.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n")
        else:
            handle.write(f"{name}={value}\n")


def write_summary(text: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(text)


# =============================================================================
# The run
# =============================================================================


def head_files(repo: pathlib.Path) -> tuple[dict[str, Side], set[str]]:
    """This repository's committed files as git stores them, and its symlinks and submodules."""
    entries = tree(repo, "HEAD")
    regular = {p: e for p, e in entries.items() if e.kind == "blob" and e.mode in MODES}
    blobs = read_blobs(repo, (e.sha for e in regular.values()))
    special = {p for p in entries if p not in regular}
    return {p: Side(e.mode, blobs[e.sha], e.sha) for p, e in regular.items()}, special


def root_commit(repo: pathlib.Path) -> str:
    roots = git(repo, "rev-list", "--max-parents=0", "HEAD").decode().split()
    if not roots:
        raise SyncError("This repository has no commits.")
    return roots[-1]


def generation_lock(
    repo: pathlib.Path,
    *,
    template: str,
    identity: Identity,
    root: str | None = None,
) -> Lock:
    """The lock a repository is born with: every file exactly as generated.

    Taken from the ROOT commit, which is the template's own tree byte for byte
    when GitHub generates a repository, so each blob is the template's and the
    template's history can always produce it. The list is recorded too: it is
    the base every later redraw of the owner's copy is measured against.
    """
    files = {
        path: FileState(entry.sha, entry.mode)
        for path, entry in tree(repo, root or root_commit(repo)).items()
        if entry.kind == "blob" and entry.mode in MODES and path not in (SENTINEL, LOCK_PATH)
        and not unsafe(path)
    }
    return Lock(template, "", "", identity, files, {})


def bootstrap(repo: pathlib.Path, template_dir: pathlib.Path, *, template: str, identity: Identity) -> Lock:
    """A lock for a repository that never got one, recovered from its first commit.

    A blob the template's history already holds is its own baseline. One that
    init rewrote is matched by rewriting every version of that path the
    template ever had and looking for the one that produces it. A file with
    no match keeps no baseline, and the plan reports it rather than guessing.
    """
    lock = generation_lock(repo, template=template, identity=identity)
    have = read_blobs(template_dir, (s.blob for s in lock.files.values()))
    unknown = sorted(p for p, s in lock.files.items() if s.blob not in have)
    if not unknown:
        return lock
    versions: dict[str, set[str]] = {p: set() for p in unknown}
    for commit in git(template_dir, "rev-list", "--all").decode().split():
        snapshot = tree(template_dir, commit)
        for path in unknown:
            if path in snapshot and snapshot[path].kind == "blob":
                versions[path].add(snapshot[path].sha)
    contents = read_blobs(template_dir, {sha for shas in versions.values() for sha in shas})
    mine = read_blobs(repo, (lock.files[p].blob for p in unknown))

    def recover(year: int) -> dict[str, str]:
        transform = rewriter(dataclasses.replace(identity, year=year), template)
        found = {}
        for path in unknown:
            want = mine.get(lock.files[path].blob)
            matches = sorted(sha for sha in versions[path]
                             if sha in contents and transform(path, contents[sha]) == want)
            if matches:
                found[path] = matches[0]
        return found

    # ⚠️ THE YEAR IS A GUESS FROM A DATE, SO NEIGHBOURS ARE TRIED. Init
    # stamps the year at the moment it runs, which is seconds after the root
    # commit - and on the other side of a New Year when generation lands
    # near midnight. The year that reproduces the most files is the one init
    # used, and the identity records it so every later run agrees.
    best_year, best = identity.year, recover(identity.year)
    for year in (identity.year + 1, identity.year - 1):
        found = recover(year)
        if len(found) > len(best):
            best_year, best = year, found
    lock.identity = dataclasses.replace(identity, year=best_year)
    for path in unknown:
        if path in best:
            lock.files[path] = FileState(best[path], lock.files[path].mode)
        else:
            del lock.files[path]
    return lock


def sides(template_dir: pathlib.Path, wanted: dict[str, str], modes: dict[str, str],
          transform: Callable[[str, bytes], bytes]) -> dict[str, Side]:
    """Template sides for `wanted` (path to blob SHA), already in the owner's identity."""
    blobs = read_blobs(template_dir, wanted.values())
    return {
        path: Side(modes[path], transform(path, blobs[sha]), sha) if sha in blobs else MISSING
        for path, sha in wanted.items()
    }


@dataclasses.dataclass
class Result:
    decisions: list[Decision]
    lock: Lock
    list_text: str
    list_changed: bool
    changed: bool
    version: str
    previous: str
    report: str


def text_of(data: bytes, path: str) -> str:
    """A file this script reads as text, or a sentence naming why it cannot be."""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SyncError(f"{path} is not valid UTF-8 ({exc.reason} at byte {exc.start}).") from None


def run(
    repo: pathlib.Path,
    template_dir: pathlib.Path,
    *,
    template: str = "",
    ref: str = "v1",
    workflow_files: bool = True,
    name: str = "",
    write: bool = True,
    mapping: Mapping | None = None,
) -> Result:
    """Sync `repo` from the template repository at `template_dir` (bare or not).

    With a `mapping`, `repo` is defined as a delta of the template rather than
    generated from it: the mapping says what syncs and where it lives, nothing
    is rewritten into another identity, and the lock is the mapping's own.
    """
    files_here, special = head_files(repo)
    lock_path = mapping.lock if mapping else LOCK_PATH
    never = NEVER | {lock_path}
    if SENTINEL in files_here and mapping is None:
        raise Skip("This repository has not been initialised yet, so there is no baseline to sync from.")

    lock_side = files_here.get(lock_path)
    if lock_side is not None:
        lock = load_lock(text_of(lock_side.data, lock_path), lock_path)
        if template and lock.template and template != lock.template:
            raise SyncError(
                f"{lock_path} says this repository syncs from {lock.template}, and the workflow "
                f"names {template}. Change one of them so they agree."
            )
        template = template or lock.template
    if not TEMPLATE_NAME.match(template or ""):
        raise SyncError(
            f"{template!r} is not a template of the form OWNER/REPO. Name it in the workflow's "
            "`template` input, or in the lock."
        )
    if lock_side is None and mapping is not None:
        # A mapped repository was never generated, so no first commit holds
        # the template's tree to recover a baseline from. Guessing one would
        # read every difference the mapping permits as an edit to keep.
        raise SyncError(
            f"There is no {lock_path} yet. Record it once, while this repository and {template} "
            "agree, with `template-sync.py lock --map`, and commit it."
        )
    if lock_side is None:
        here_owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "")
        here_repo = os.environ.get("GITHUB_REPOSITORY", "")
        if not here_owner or not here_repo:
            raise SyncError("There is no lock, and GITHUB_REPOSITORY is not set, so the identity "
                            "initialisation stamped cannot be recovered.")
        root = root_commit(repo)
        year = int(git(repo, "show", "-s", "--format=%cd", "--date=format-local:%Y", root,
                       env={"TZ": "UTC"}).decode().strip())
        lock = bootstrap(repo, template_dir, template=template,
                         identity=Identity(here_owner, here_repo, name or here_owner, year))
    lock.template = template

    commit = resolve(template_dir, ref)
    if commit is None:
        raise Skip(f"{template} has not published `{ref}` yet, so there is nothing to sync to.")
    version = version_label(template_dir, commit, ref)
    target_tree = {p: e for p, e in tree(template_dir, commit).items() if e.kind == "blob"}
    if LIST_PATH not in target_tree and mapping is None:
        raise SyncError(f"{template} at {version} publishes no {LIST_PATH}, so it says nothing about what to sync.")

    base_blob = lock.files[LIST_PATH].blob if LIST_PATH in lock.files and mapping is None else ""
    raw_lists = read_blobs(template_dir, [s for s in (
        target_tree[LIST_PATH].sha if LIST_PATH in target_tree else "", base_blob) if s])
    target_list = (text_of(raw_lists[target_tree[LIST_PATH].sha], LIST_PATH)
                   if LIST_PATH in target_tree else None)
    base_list = text_of(raw_lists[base_blob], LIST_PATH) if base_blob in raw_lists else None
    own_list = mapping.list if mapping else LIST_PATH
    ours_list = text_of(files_here[own_list].data, own_list) if own_list and own_list in files_here else None

    # Each template path is decided at the path it lives at HERE: its own,
    # unless a mapping moves it or leaves it out. Two template paths landing
    # on one would make a merge of strangers, so that stops the run - and so
    # does a template path sitting where a relocated folder lands, whose
    # origin could not be told apart from the relocated files'.
    origin: dict[str, str] = {}
    for path, entry in sorted(target_tree.items()):
        local = mapping.here(path) if mapping else path
        if entry.mode not in MODES or path in NEVER or local is None or local in never:
            continue
        if local in origin:
            raise SyncError(f"{origin[local]} and {path} in {template} would both live at {local} here. "
                            "Fix the mapping so each has a place of its own.")
        if mapping and mapping.there(local) != path:
            raise SyncError(f"{path} in {template} sits where the mapping relocates a folder to. "
                            "Fix the mapping so each file has a place of its own.")
        origin[local] = path
    shipped = {local: target_tree[path] for local, path in origin.items()}
    known = {p: s for p, s in lock.files.items() if p not in never}

    if mapping:
        def transform(path: str, data: bytes) -> bytes:
            there = mapping.there(path)
            return mapping.content(there, data) if there is not None else data
    else:
        transform = rewriter(lock.identity, template)

    # ⚠️ EACH PATH IS JUDGED BY THE LIST THAT GOVERNED IT. A path the template
    # still ships is judged by the list as redrawn now. A path it stopped
    # shipping has also left the template's list, so the redrawn list cannot
    # name it at all: it is judged by the owner's list as it stood, which is
    # what said whether it was synced when it last was. Judging it by the new
    # list read every removal as "not synced", and no deletion ever arrived.
    #
    # A MISSING LIST IS RESTORED, NOT REPLACED BY DEFAULTS. An owner who
    # deleted it may have meant "stop", and defaults would sync everything.
    # This run writes the list back and syncs nothing else; the next one
    # follows whatever it then says. Deleting the stub is how to stop.
    base = sides(template_dir, {p: s.blob for p, s in known.items()},
                 {p: s.mode for p, s in known.items()}, transform)
    target = sides(template_dir, {p: e.sha for p, e in shipped.items()},
                   {p: e.mode for p, e in shipped.items()}, transform)
    ours = {p: s for p, s in files_here.items() if p not in never}

    # ⚠️ A SYNC NEVER GOES BACKWARDS. "Use this template" copies the
    # template's default branch, not its release, so a repository generated
    # between a merge and the next release holds files newer than `v1`. A
    # sync to `v1` would read each of those changes as the template taking
    # it back - proposing to revert every one and delete every file added
    # since. A baseline only the template's NEWER history holds means this
    # repository is ahead of the target, and there is nothing to sync until
    # the template releases past it.
    newer = newer_objects(template_dir, commit)
    ahead = sorted(p for p, s in known.items() if s.blob in newer)
    if ahead:
        raise Skip(f"This repository already holds a newer version of {template} than {ref} ({version}) - "
                   f"{', '.join(ahead[:3])}{' and more' if len(ahead) > 3 else ''}. There is nothing to sync "
                   "until the template releases past it.")

    if mapping:
        # Moves are git's to see between TEMPLATE paths, so the baselines are
        # laid out where they came from, and each move found is brought home.
        theirs = {there: s for p, s in known.items() if (there := mapping.there(p)) is not None}
        found, found_replaced = template_moves(template_dir, theirs, commit)
        moves, replaced = {}, {}
        for into, pairs in ((moves, found), (replaced, found_replaced)):
            for old, new in pairs.items():
                old_here, new_here = mapping.here(old), mapping.here(new)
                if old_here is not None and new_here is not None and new_here not in never:
                    into[old_here] = new_here
        synced = set(shipped) | {p for p in known if mapping.there(p) is not None}
        held: set[str] = set()
    else:
        moves, replaced = template_moves(template_dir, known, commit)
        held = set()
        if ours_list is None:
            synced = set()
        else:
            reference = base_list if base_list is not None else target_list
            draft, held = honour_choices(
                merge_list(base_list, target_list, ours_list, renames=moves, carry_off=replaced),
                ours_list, reference, set(shipped), {**moves, **replaced})
            synced = (matched(draft, set(shipped)) | matched(ours_list, set(known) - set(shipped))) - held
            # ⚠️ A DELETED FILE COMES BACK ONLY WHEN ITS OWNER ASKS. That
            # means a line of its own, switched on: a pattern - the
            # template's or a rule of the owner's - still matching the path
            # is not a request, and git's matcher cannot always rule a single
            # file out from under a folder pattern anyway.
            asked = exact_on(ours_list)
            synced -= {p for p, s in known.items() if s.deleted and p not in asked}

    decisions = plan(
        base,
        target,
        ours,
        synced=synced,
        deleted={p for p, s in known.items() if s.deleted},
        special=special,
        defer=(lambda _p: False) if workflow_files else (lambda p: p.startswith(WORKFLOW_DIR)),
        moves=moves,
        replaced=replaced,
    )
    if mapping:
        # A file missing here is drift from the mapping, not an owner's choice:
        # it is neither switched off nor re-created, and stays in view until
        # it is restored or the mapping records its absence. Its baseline is
        # kept - or made, at a path a move just brought it to - so the next
        # run finds it missing again rather than new.
        decisions = [
            Decision(d.path, "conflict", pair=d.pair, detail=(
                f"This file is missing here, and nothing in {mapping.source or 'the mapping'} sets it "
                "apart. Restore it, or record its absence there."),
                diff=udiff(d.path, b"", target[d.path].data) if d.path in target else "",
                state=FileState(d.state.blob, d.state.mode) if isinstance(d.state, FileState) else None)
            if d.outcome == "owner-deleted" else d
            for d in decisions
        ]
    elif ours_list is None:
        # Restoring a deleted list syncs nothing else, but a file the template
        # removed meanwhile keeps its baseline and waits in the restored list,
        # so the run that follows it can still remove it.
        candidates = {d.path for d in decisions if d.outcome == "not-synced" and d.state == REMOVE
                      and d.path in ours}
        dropped = matched(base_list, candidates) if base_list is not None else set()
        decisions = [Decision(d.path, "not-synced") if d.path in dropped else d for d in decisions]
    else:
        # A choice the list could not express by name is held off here, and
        # said; so is a new file that carries on one the owner has off.
        already = {line.key for line in parse_list(ours_list).body if line.kind == "entry"}
        mentioned = {d.path for d in decisions if d.outcome != "not-synced"}
        notes = [Decision(path, "held-off", detail=(
            "You switched this file off, and the template's list no longer has a line that can say so; "
            "it is held off for you. A rule of your own under Your rules settles it.")) for path in sorted(held)]
        notes += [Decision(new, "held-off", detail=(
            f"It carries on `{old}`, which you have off, so it starts switched off too. If it is a new file "
            "you want, take the `#` away from its line."))
            for old, new in sorted(replaced.items())
            if new in shipped and new not in synced and old not in synced and escape(new) not in already
            and new not in mentioned and new not in held]
        noted = {d.path for d in notes}
        decisions = sorted([d for d in decisions if d.path not in noted] + notes, key=lambda d: d.path)

    unsettled = ("conflict", "deferred", "waiting")
    if mapping:
        list_text = ours_list
        if ours_list is not None:
            list_text = amend_list(
                ours_list,
                target_list,
                added={d.path: origin.get(d.path, d.path) for d in decisions
                       if d.write is not None and d.path not in ours},
                removed=[d.path for d in decisions if d.delete and d.outcome != "moved"],
                renamed={d.path: d.pair for d in decisions if d.outcome == "moved"},
            )
    else:
        list_text = merge_list(
            base_list,
            target_list,
            ours_list,
            disabled=[d.path for d in decisions if d.outcome == "owner-deleted"],
            renames=moves,
            carry_off=replaced,
            waiting=[d.path for d in decisions if d.path not in shipped and (
                d.outcome in unsettled or (ours_list is None and d.outcome == "not-synced"
                                           and d.state is None and d.path in known))],
        )
        if ours_list is not None:
            reference = base_list if base_list is not None else target_list
            list_text, _ = honour_choices(list_text, ours_list, reference, set(shipped), {**moves, **replaced},
                                          settled=[d.path for d in decisions if d.outcome == "owner-deleted"])
    list_changed = list_text != ours_list

    writes = {d.path: d.write for d in decisions if d.write is not None}
    deletes = [d.path for d in decisions if d.delete]
    if list_changed:
        writes[own_list] = Side(files_here[own_list].mode if own_list in files_here else "100644",
                                list_text.encode("utf-8"))

    files = dict(lock.files)
    for d in decisions:
        if isinstance(d.state, FileState):
            files[d.path] = d.state
        elif d.state == REMOVE:
            files.pop(d.path, None)
    if mapping is None:
        files[LIST_PATH] = FileState(target_tree[LIST_PATH].sha, target_tree[LIST_PATH].mode)
    # A file keeps the version it STARTED waiting at, so the issue can say
    # how long it has waited - and a release that changes nothing for it
    # leaves the lock, and so the pull request, alone.
    pending: dict[str, dict] = {}
    for d in decisions:
        if d.outcome not in ("conflict", "deferred"):
            continue
        reason = "conflict" if d.outcome == "conflict" else "needs a token"
        before = lock.pending.get(d.path, {})
        since = before.get("version") if before.get("reason") == reason else None
        pending[d.path] = {"version": since if isinstance(since, str) and since else version, "reason": reason}
    previous = lock.version
    new_lock = Lock(template, version, commit, None if mapping else lock.identity, files, pending)

    # A new version that changed nothing here is not worth a pull request:
    # only the files, the per-file baselines and what is still pending count.
    old = json.loads(lock_side.data) if lock_side is not None else None
    lock_moved = old is None or {k: old.get(k) for k in ("files", "pending")} != {
        k: json.loads(dump_lock(new_lock))[k] for k in ("files", "pending")}
    changed = bool(writes or deletes) or lock_moved
    if changed:
        writes[lock_path] = Side(lock_side.mode if lock_side else "100644",
                                 dump_lock(new_lock, mapping.name if mapping else "🔄 Template Sync").encode("utf-8"))
        if write:
            apply(repo, writes, deletes)

    report = render_report(template=template, version=version, previous=previous, decisions=decisions,
                           list_changed=list_changed, mapping=mapping)
    return Result(decisions, new_lock, list_text or "", list_changed, changed, version, previous, report)


def mapped_lock(repo: pathlib.Path, template_dir: pathlib.Path, *, template: str, ref: str,
                mapping: Mapping) -> Lock:
    """The lock a mapped repository starts from: every mapped file, as the template holds it at `ref`.

    Recorded once, by hand, at a moment the two trees are known to agree -
    when the repository's own check of the mapping passes - because that is
    the claim it makes: everything up to `ref` is already here, in this
    repository's own form. A file the template ships that is missing here
    makes the claim false, so it refuses.
    """
    commit = resolve(template_dir, ref)
    if commit is None:
        raise SyncError(f"{template} has no `{ref}` to record a lock at.")
    files_here, _ = head_files(repo)
    never = NEVER | {mapping.lock}
    files: dict[str, FileState] = {}
    missing: list[str] = []
    for path, entry in sorted(tree(template_dir, commit).items()):
        local = mapping.here(path)
        if entry.kind != "blob" or entry.mode not in MODES or path in NEVER or local is None or local in never:
            continue
        if local not in files_here:
            missing.append(local)
            continue
        files[local] = FileState(entry.sha, entry.mode)
    if missing:
        raise SyncError(f"{len(missing)} file(s) {template} ships are missing here, so the trees do not agree "
                        f"yet: {', '.join(missing[:5])}{' ...' if len(missing) > 5 else ''}.")
    return Lock(template, version_label(template_dir, commit, ref), commit, None, files, {})


# =============================================================================
# The template's own check
# =============================================================================


def check(repo: pathlib.Path) -> list[str]:
    """Problems with a template's list. Empty means every file it ships is named.

    A file the list does not name is a file no generated repository will ever
    receive an update to, and nobody decided that: the template author added
    it and forgot the line. So an unnamed file fails, and the message says
    which line to add.
    """
    path = repo / LIST_PATH
    if not path.is_file():
        return [f"{LIST_PATH} is missing. A template must say what it keeps current."]
    text = path.read_text(encoding="utf-8")
    parsed = parse_list(text)
    problems: list[str] = []
    if parsed.marker is None:
        problems.append(f"{LIST_PATH} has no `{RULES_MARKER}` line, which every owner's rules sit under.")
    elif any(line.strip() for line in parsed.rules):
        problems.append(f"{LIST_PATH} has lines under `{RULES_MARKER}`. That section is the owner's; "
                        "a template's defaults belong above it.")
    seen: set[str] = set()
    for line in parsed.body:
        if line.kind == "entry":
            if line.key in seen:
                problems.append(f"`{line.key}` is listed more than once. Keep one line for it.")
            seen.add(line.key)
    tracked = [p for p in decode(git(repo, "ls-files", "-z")).split("\0") if p and p != LIST_PATH]
    on = matched(text, tracked)
    off = matched("\n".join(line.key for line in parsed.body if line.kind == "entry" and not line.on) + "\n",
                  tracked)
    for p in sorted(set(tracked) - on - off):
        problems.append(f"{p} is shipped but not named. Add `{escape(p)}` to keep it current, or "
                        f"`#{escape(p)}` to leave it to each owner.")
    for p in sorted(on & off):
        problems.append(f"{p} is named both on and off. Keep one line for it.")
    if SENTINEL in on:
        problems.append(f"{SENTINEL} is switched on. Re-creating it would re-run initialisation; "
                        f"write it as `#{escape(SENTINEL)}`.")
    present = set(tracked)
    for line in parsed.body:
        if line.kind != "entry":
            continue
        if not line.key.startswith("/"):
            problems.append(f"`{line.text}` is not anchored, so it matches that name in every folder. "
                            "Start it with `/`.")
        elif literal(line.key) and unescape(line.key) not in present:
            problems.append(f"`{line.text}` names a file the template does not ship. Remove the line.")
    return problems


# =============================================================================
# The issue that keeps waiting files in view
# =============================================================================

ISSUE_TITLE = "🔄 Template sync is waiting on you"
ISSUE_LABEL = "automated"
REASONS = {
    "conflict": "You and the template changed the same part of it",
    "needs a token": "It is a workflow file, and no BOT_ACCESS_TOKEN can write it",
}


def issue_title(mapping: Mapping | None = None) -> str:
    return f"{mapping.name} is waiting on you" if mapping else ISSUE_TITLE


def issue_body(template: str, pending: dict[str, dict], mapping: Mapping | None = None) -> str:
    rows = "\n".join(
        f"| `{path}` | {info.get('version', '')} | {REASONS.get(info.get('reason', ''), info.get('reason', ''))} |"
        for path, info in sorted(pending.items())
    )
    settle = (
        f"or when `{mapping.source or 'the mapping'}` records the difference, if it is one this "
        "repository is meant to have."
        if mapping else
        "or when you put a `#` in front of it in `.github/template-sync` to keep it as yours."
    )
    return (
        f"### {issue_title(mapping)}\n\n"
        f"These files have changes from `{template}` that could not be applied on their own. "
        "Nothing in them was touched.\n\n"
        "| File | Waiting since | Why |\n| :--- | :--- | :--- |\n"
        f"{rows}\n\n"
        "**A conflict** settles when the lines the template changed read as the template has them - "
        f"the sync pull request shows the change - {settle} Make the change on your default branch, "
        "never on the sync branch: each sync rewrites that branch from your default branch.\n\n"
        "**A workflow file** settles once a `BOT_ACCESS_TOKEN` secret that can write workflows exists.\n\n"
        "This issue is redrawn on every sync and closes itself when nothing is waiting.\n"
    )


def gh(*args: str, env: dict | None = None) -> tuple[int, str]:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True, check=False,
                          env={**os.environ, **(env or {})})
    return proc.returncode, (proc.stdout or "").strip()


def track(repository: str, lock: Lock | None, version: str, mapping: Mapping | None = None) -> list[str]:
    """Keep one issue open while files wait on the owner; close it when none do.

    A pull request names a conflict once. When it is merged with the conflict
    still in it - the usual case, since the rest of it is worth having - the
    file keeps its old baseline and the next sync offers the change again,
    but a sync with nothing new to propose opens no pull request, so the wait
    would go quiet. The issue is what keeps it in view. Failures here warn and
    never fail the run: the sync itself already succeeded.
    """
    warnings: list[str] = []
    pending = lock.pending if lock else {}
    title = issue_title(mapping)
    # Every open automated issue, not the first page of them: a repository
    # with more than a page would otherwise open a second copy of this one.
    code, found = gh("issue", "list", "--repo", repository, "--state", "open", "--label", ISSUE_LABEL,
                     "--limit", "1000", "--json", "number,title",
                     "--jq", ".[] | select(.title == env.TITLE) | .number", env={"TITLE": title})
    if code != 0:
        warnings.append("Could not list issues, so the waiting-files issue was not updated this run.")
        return warnings
    existing = found.split("\n", 1)[0].strip()
    if pending:
        body = issue_body(lock.template, pending, mapping)
        if existing:
            if gh("issue", "edit", existing, "--repo", repository, "--body", body)[0] != 0:
                warnings.append(f"Could not update issue #{existing}.")
        else:
            gh("label", "create", ISSUE_LABEL, "--repo", repository, "--color", "c0a062", "--force",
               "--description", "🤖 Opened by repository automation (sync, formatting, refresh) - stale-exempt.")
            if gh("issue", "create", "--repo", repository, "--title", title, "--label", ISSUE_LABEL,
                  "--body", body)[0] != 0:
                warnings.append("Could not open the waiting-files issue.")
    elif existing:
        if gh("issue", "close", existing, "--repo", repository, "--comment",
              f"Nothing waits on you any more, as of {version or 'this sync'}.")[0] != 0:
            warnings.append(f"Could not close issue #{existing}.")
    return warnings


# =============================================================================
# Command line
# =============================================================================


def read_mapping(path: str) -> Mapping | None:
    """The mapping named on the command line, or None when none is."""
    if not path:
        return None
    try:
        raw = pathlib.Path(path).read_bytes()
    except OSError as exc:
        raise SyncError(f"Could not read the mapping {path}: {exc.strerror}.") from None
    return load_mapping(text_of(raw, path), path)


def cmd_run(args: argparse.Namespace) -> int:
    repo = pathlib.Path(args.repo_dir).resolve()
    mapping = read_mapping(args.map)
    if not args.dry_run and git(repo, "status", "--porcelain", "--untracked-files=no").strip():
        raise SyncError("The working tree has uncommitted changes. A sync runs on a clean checkout.")
    try:
        result = run(
            repo,
            pathlib.Path(args.template_dir).resolve(),
            template=args.template,
            ref=args.ref,
            workflow_files=args.workflow_files == "true",
            name=args.name,
            write=not args.dry_run,
            mapping=mapping,
        )
    except Skip as skip:
        print(f"::notice title=Template sync::{skip}")
        write_summary(f"### {mapping.name if mapping else '🔄 Template Sync'}\n\n{skip}\n")
        write_output("changed", "false")
        write_output("clean", "true")
        write_output("pending", "0")
        return 0
    conflicts = [d for d in result.decisions if d.outcome == "conflict"]
    deferred = [d for d in result.decisions if d.outcome == "deferred"]
    touched = sum(1 for d in result.decisions if d.write is not None or d.delete)
    for d in conflicts:
        print(f"::warning file={d.path},title=Template sync conflict::{d.detail}")
    print(f"{result.lock.template} {result.version}: {touched} file(s) changed, "
          f"{len(conflicts)} conflict(s), {len(deferred)} waiting on a token.")
    write_summary(result.report)
    if args.report:
        pathlib.Path(args.report).write_text(result.report, encoding="utf-8")
    name = result.lock.template
    title = f"chore(template): 🔄 sync with {name} {result.version}"
    commit_title = f"chore(template): 🔄 sync {touched} file(s) with {name} {result.version}"
    write_output("changed", "true" if result.changed else "false")
    write_output("clean", "true" if not result.lock.pending else "false")
    write_output("pending", str(len(result.lock.pending)))
    write_output("version", result.version)
    write_output("pr-title", title if len(title) <= 100 else "chore(template): 🔄 sync with the template")
    write_output("commit-title", commit_title if len(commit_title) <= 100
                 else "chore(template): 🔄 sync with the template")
    write_output("report", pr_body(result.report))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    problems = check(pathlib.Path(args.repo_dir).resolve())
    for p in problems:
        print(f"::error file={LIST_PATH},title=Template sync list::{p}")
    verdict = f"{LIST_PATH}: {len(problems)} problem(s)."
    print(verdict)
    write_summary(f"### 🔄 Template Sync List\n\n{verdict}\n" + "".join(f"\n- ❌ {p}" for p in problems) + "\n")
    return 1 if problems else 0


def cmd_track(args: argparse.Namespace) -> int:
    mapping = read_mapping(args.map)
    lock_path = mapping.lock if mapping else LOCK_PATH
    path = pathlib.Path(args.repo_dir) / lock_path
    lock = load_lock(text_of(path.read_bytes(), lock_path), lock_path) if path.is_file() else None
    for warning in track(args.repository, lock, args.version, mapping):
        print(f"::warning title=Template sync::{warning}")
    return 0


def cmd_lock(args: argparse.Namespace) -> int:
    mapping = read_mapping(args.map)
    if mapping:
        if not args.template_dir:
            raise SyncError("A mapped lock is recorded from the template itself: pass --template-dir.")
        lock = mapped_lock(pathlib.Path(args.repo_dir).resolve(), pathlib.Path(args.template_dir).resolve(),
                           template=args.template, ref=args.ref, mapping=mapping)
    else:
        missing = [flag for flag in ("owner", "repository", "name", "year") if not getattr(args, flag)]
        if missing:
            raise SyncError(f"A generated repository's lock needs --{', --'.join(missing)}.")
        lock = generation_lock(
            pathlib.Path(args.repo_dir).resolve(),
            template=args.template,
            identity=Identity(args.owner, args.repository, args.name, int(args.year)),
            root=args.root or None,
        )
    sys.stdout.write(dump_lock(lock, mapping.name) if mapping else dump_lock(lock))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bring a generated repository's scaffold up to date, on request.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="sync this repository from its template")
    p_run.add_argument("--repo-dir", default=".")
    p_run.add_argument("--template-dir", required=True)
    p_run.add_argument("--template", default="")
    p_run.add_argument("--ref", default="v1")
    p_run.add_argument("--workflow-files", choices=("true", "false"), default="true")
    p_run.add_argument("--name", default="")
    p_run.add_argument("--report", default="")
    p_run.add_argument("--dry-run", action="store_true")
    p_run.add_argument("--map", default="", help="a mapping, for a repository defined as a delta of its template")
    p_run.set_defaults(func=cmd_run)

    p_check = sub.add_parser("check", help="check that a template's list names every file it ships")
    p_check.add_argument("--repo-dir", default=".")
    p_check.set_defaults(func=cmd_check)

    p_track = sub.add_parser("track", help="keep one issue open while files wait on the owner")
    p_track.add_argument("--repo-dir", default=".")
    p_track.add_argument("--repository", required=True)
    p_track.add_argument("--version", default="")
    p_track.add_argument("--map", default="")
    p_track.set_defaults(func=cmd_track)

    p_lock = sub.add_parser("lock", help="print the lock a repository starts with")
    p_lock.add_argument("--repo-dir", default=".")
    p_lock.add_argument("--template", required=True)
    p_lock.add_argument("--owner", default="")
    p_lock.add_argument("--repository", default="")
    p_lock.add_argument("--name", default="")
    p_lock.add_argument("--year", default="")
    p_lock.add_argument("--root", default="")
    p_lock.add_argument("--map", default="", help="record a mapped repository's lock instead")
    p_lock.add_argument("--template-dir", default="")
    p_lock.add_argument("--ref", default="v1")
    p_lock.set_defaults(func=cmd_lock)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except SyncError as exc:
        print(f"::error title=Template sync::{exc}")
        write_summary(f"### 🔄 Template Sync\n\n❌ {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
