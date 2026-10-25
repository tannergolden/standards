#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
# =============================================================================
# Initialise From Template - make a generated repository belong to its owner
# =============================================================================
# GitHub's "Use this template" copies files VERBATIM. It substitutes nothing:
# no owner, no repository name, no licence holder. Every generated repository
# therefore starts out carrying the template author's identity until somebody
# edits it by hand, and most people never do.
#
# This runs once in the generated repository and rewrites that identity to
# the new owner's, deletes what only the template needs, then removes its own
# sentinel so it can never run again.
#
# ⚠️ WHAT ONLY THE TEMPLATE NEEDS IS DELETED HERE, NOT LEFT TO THE OWNER. A
# template ships files that serve the template itself and nothing generated
# from it: the sentinel, its changelog, and any contract it is held to, with
# everything enforcing it. Left behind they were scaffolding every owner had
# to find and delete by hand - and a test among them was not even inert,
# since a generated repository's own CI runs every test beside its scripts.
# The template names each of them, one to a line, under
# `# --- Only ever in the template` in `.github/template-sync`; every one is
# deleted before anything is rewritten - but a workflow file, below. Their
# lines stay in the list, switched off, so the owner still sees what the
# template ships and can take one back with a sync.
#
# ⚠️ NOTHING UNDER .github/workflows/ IS EVER CHANGED HERE. The push below
# authenticates with the workflow token, and GitHub refuses any push from it
# that creates, changes or deletes a file in that folder - the README beside
# the workflows included - whatever the job's permissions say: no
# `permissions:` key grants that right. Deleting a workflow only the template
# needed once got a generated repository's push refused, and with it the
# whole initialisation. So a workflow file only the template needs stays
# where it is, named in the commit and the run for its owner to delete; no
# identity is rewritten in that folder; and its folder log is never
# redrawn, which it never needs, since nothing beside it changed.
#
# 🏷️ Cut Release is NOT one of them. It publishes the template's releases,
# but any repository consumed by tag cuts its own the same way - the
# Markdown Kit, generated from the golden path template, does - so it stays,
# inert until its owner adopts it.
#
# ⚠️ ON A PUBLIC REPOSITORY THE VULNERABILITY ISSUE FORM GOES TOO. Every
# issue on a public repository is public, so a vulnerability reported
# through `.github/ISSUE_TEMPLATE/Vulnerability-Report.yaml` would be
# published the moment it was filed. Private vulnerability reporting is the
# intake there, with the form the golden path template ships for it in
# `.github/VULNERABILITY_REPORT.yml`. A private repository keeps the issue
# form, since an issue there is as private as the repository. Whether the
# repository is public is read from the repository object fetched below for
# the template's name, else from the event that started the run; when
# neither says, the form stays and the run warns, because deleting it from a
# private repository would leave that repository no intake at all. Its line
# in the list is left as it is, and the first 🔄 Template Sync after this
# reads the absence as a deletion: it switches the line off and never
# brings the form back.
#
# EVERY FOLDER LOG IS REDRAWN LAST, the workflows' aside. A log lists the
# files beside it, so one naming the sentinel, or a file deleted above, would
# describe a repository that does not exist; the lock written below belongs
# in its folder's log too. Redrawn from the finished tree, each row says what
# its file now says, exactly as 🗂️ Machined Indexes would draw it on the
# owner's first push.
#
# ⚠️ WHAT IT DOES NOT REWRITE: a repository on the template owner's account.
# The SHARED repositories every consumer calls - `tannergolden/standards`,
# `tannergolden/intelligence`, and the Markdown Kit, `tannergolden/markdown`,
# whose folders the template's assets/ READMEs link - are the commonest, but
# the template itself and the account's `.github` are the same kind of
# thing: an ADDRESS on that account. Rewriting one to the new owner
# names a repository that does not exist. Only the handle on its own is an
# identity.
# The distinction is the whole reason this uses targeted rules rather than a
# blanket find-and-replace.
#
# ⚠️ NOR ANYTHING INSIDE A SEALED BLOCK. A block whose marker carries its
# hash, `<!-- NAME:BEGIN sha256:<hash> -->`, such as the INTELLIGENCE block
# tannergolden/intelligence delivers into AGENTS.md, belongs to the machine
# that sealed it, which is why template sync masks one too. Its rules name
# the template owner on purpose, to say whose repositories the owner's own
# rules govern; rewriting the handle there broke the seal and handed those
# rules to every new owner. Each sealed block passes through whole, marker
# lines included. A marker inside a code fence is an example, not a block.
#
# THE EMAIL IS THE `noreply` FORM, AND THAT IS DELIBERATE. GitHub keeps
# account emails private by default and the API returns null for most users,
# so a real address cannot be read. `ID+login@users.noreply.github.com` is
# always valid, routes to the owner, and publishes nothing they chose to
# keep private.
#
# THE INITIAL COMMIT IS REWRITTEN when this is the only commit in the
# repository. Template generation leaves a bare "Initial commit", which
# fails the Conventional Commits gate these standards apply to everything
# else. Amending it means a generated repository's history is compliant from
# its first entry rather than from its second.
#
# Requires: GH_TOKEN, REPO, OWNER
# Optional: SENTINEL, DEFAULT_BRANCH, TEMPLATE_OWNER, AMEND_INITIAL
# =============================================================================
from __future__ import annotations

import datetime
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
SKIP_DIRS = {".git", "node_modules", ".venv", "vendor", "target", "dist", "build"}
TEXT_SUFFIXES = {
    ".md", ".yml", ".yaml", ".json", ".jsonc", ".toml", ".txt", ".cfg", ".ini",
    ".sh", ".py", ".js", ".ts",
}

# ⚠️ MATCHED BY NAME, NOT BY SUFFIX. A leading-dot file has no suffix at all:
# `PurePath(".gitignore").suffix` is `''`, because the whole name is the stem.
# These three used to sit in TEXT_SUFFIXES, where they matched nothing ever,
# and a generated repository kept the template owner's handle verbatim in all
# three while the commit this script writes claimed every identity had been
# rewritten.
TEXT_NAMES = {
    "LICENSE", "CODEOWNERS", ".editorconfig", ".gitignore", ".gitattributes",
}

# The folder whose every file - workflow or not - GitHub refuses to let the
# workflow token create, change or delete. See the header.
WORKFLOW_DIR = ".github/workflows/"

# The issue form that would publish a vulnerability on a public repository.
# See the header: deleted there, kept on a private one.
VULNERABILITY_FORM = ".github/ISSUE_TEMPLATE/Vulnerability-Report.yaml"

# A sealed block's opening marker and a code fence, read as template sync
# reads them. See the header: nothing inside a sealed block is rewritten.
SEALED_BEGIN = re.compile(r"<!--\s*(?P<name>[A-Z][A-Z0-9_-]*(?::[A-Z][A-Z0-9_-]*)*):BEGIN\s+sha256:[0-9a-f]{64}\s*-->")
FENCE = re.compile(r"^(?:```|~~~)")


def run(*args: str, check: bool = True) -> str:
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        raise SystemExit(f"::error title=Initialisation::`{' '.join(args[:3])}` failed: {result.stderr.strip()}")
    return result.stdout.strip()


def api(path: str, token: str) -> dict:
    request = urllib.request.Request(  # noqa: S310 - constant API host
        f"{API}/{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "init-template",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            return json.load(response)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print(f"::warning::Could not read {path} ({exc}); falling back to the login.")
        return {}


def summary(text: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(text)


def sealed_parts(text: str) -> list[tuple[str, bool]]:
    """`text`, in order, as (part, sealed) pairs: each sealed block whole, its marker lines included.

    Read as template sync reads one: a marker inside a code fence is an
    example, and a BEGIN that never closes is no block at all.
    """
    lines = [line + "\n" for line in text.split("\n")]
    lines[-1] = lines[-1][:-1]
    parts: list[tuple[str, bool]] = []
    start = i = 0
    fenced = False
    while i < len(lines):
        if FENCE.match(lines[i].strip()):
            fenced = not fenced
        elif not fenced and (begin := SEALED_BEGIN.search(lines[i])):
            closing = re.compile(r"<!--\s*" + re.escape(begin.group("name")) + r":END\s*-->")
            end = next((j for j in range(i + 1, len(lines)) if closing.search(lines[j])), None)
            if end is not None:
                parts += [("".join(lines[start:i]), False), ("".join(lines[i:end + 1]), True)]
                start = i = end + 1
                continue
        i += 1
    parts.append(("".join(lines[start:]), False))
    return [(part, sealed) for part, sealed in parts if part]


def rewrite(
    text: str,
    *,
    owner: str,
    repo: str,
    display: str,
    template_owner: str,
    year: int,
) -> str:
    """Every identity substitution, applied to one file's text.

    Pure, and at module level, so the rules can be exercised directly. They
    used to sit inside `main()`, unreachable without a token, a network call
    and a push - which is why the one rule the template DOCUMENTED WRONGLY,
    the contact-link placeholder, had no test at all. A rule and its gate
    change together; this is the gate.

    The rules run only on the text around a sealed block, which passes
    through whole: the header says why.
    """
    return "".join(
        part if sealed else substitute(part, owner=owner, repo=repo, display=display,
                                       template_owner=template_owner, year=year)
        for part, sealed in sealed_parts(text)
    )


def substitute(
    text: str,
    *,
    owner: str,
    repo: str,
    display: str,
    template_owner: str,
    year: int,
) -> str:
    """The identity substitutions themselves, on text that holds no sealed block."""
    # Targeted rules, never a blanket replace. The template owner's handle
    # appears both as an identity to rewrite and as the first half of a
    # repository address, which must survive untouched. The last rule below
    # is where that line is drawn.
    for old, new in (
        # Contact links carry a placeholder because GitHub never substitutes
        # one; this is the substitution.
        ("OWNER/REPOSITORY", repo),
        (f"[@{template_owner}](https://github.com/{template_owner})", f"[@{owner}](https://github.com/{owner})"),
        (f"github: [{template_owner}]", f"github: [{owner}]"),
    ):
        text = text.replace(old, new)

    # The licence holder is the template author's name, not a handle.
    # The YEAR is restamped too: it is the year this repository was
    # created, not the year the template was written. Carrying the
    # template's year forward would put a copyright date on a generated
    # repository that predates the work it covers, and NOTHING WOULD EVER
    # CORRECT IT: the year is fixed at generation by design, and no
    # workflow rolls it afterwards. This substitution is the only chance
    # to get it right.
    # A lambda, not a replacement string: a display name is arbitrary user
    # input and `\1` in it would be read as a backreference.
    text = re.sub(
        r"Copyright \(c\) \d{4}(?:\s*[-\u2013]\s*\d{4})?\s+Tanner Golden",
        lambda _: f"Copyright (c) {year} {display}",
        text,
    )

    # A YAML `author:` names the person a file belongs to, such as a
    # manifest's or a document's metadata, and a repository generated from
    # a template is its owner's from the first commit, so the author follows
    # the owner the way the licence holder does. Only a whole
    # `author:` value is replaced, quoted as it was and escaped for that
    # quote, so the YAML still parses whatever the display name holds.
    def author(match: re.Match[str]) -> str:
        if match.group("quote") == "'":
            value = "'" + display.replace("'", "''") + "'"
        else:
            value = '"' + display.replace("\\", "\\\\").replace('"', '\\"') + '"'
        return f"{match.group('key')}{value}{match.group('rest')}"

    text = re.sub(
        r"""^(?P<key>author:[ \t]*)(?P<quote>["']?)Tanner Golden(?P=quote)(?P<rest>[ \t]*(?:#.*)?)$""",
        author,
        text,
        flags=re.M,
    )

    # Any remaining handle becomes the new owner's, EXCEPT where it opens a
    # repository ADDRESS: `<template owner>/<name>`, the name included.
    #
    # ⚠️ A LIST OF SPARED NAMES BROKE EVERY ADDRESS NOT ON IT. Only
    # `/standards` was spared at first, then the three shared repositories;
    # the "third route" remote pointing back at the template, and links to
    # the template itself and the account's `.github`, still came out naming
    # a repository on the new owner's account that does not exist. No address
    # in a template should follow the owner: a link meant as "this repository"
    # carries the OWNER/REPOSITORY placeholder above, because a rewritten
    # address would name `<owner>/<template>`, which is wrong as well.
    #
    # `.github` is an address like any other and survives too. Health-file
    # inheritance is per account, so the link keeps naming the repository the
    # template's files come from rather than asserting that the new owner has
    # one.
    #
    # One pass, so an address is consumed whole before its name is looked
    # at: in `<owner>/<owner>` the second handle is a repository name, not an
    # identity. `@<owner>/<name>` is a team or a package scope - a namespace
    # of the owner's, not a repository - so the lookbehind hands it to the
    # identity branch.
    if template_owner in text:
        handle = re.escape(template_owner)
        text = re.sub(
            rf"(?<!@)({handle}/[A-Za-z0-9._-]+)|{handle}",
            lambda match: match.group(1) or owner,
            text,
        )

    return text


def workflow_file(path: str | pathlib.PurePath) -> bool:
    """Whether GitHub refuses the workflow token any change to `path`: anything under WORKFLOW_DIR."""
    return pathlib.PurePosixPath(path).as_posix().startswith(WORKFLOW_DIR)


def considered(path: pathlib.PurePath) -> bool:
    """Whether initialisation looks inside a file at all.

    Never inside a workflow file, whatever its name: initialisation could not
    push the rewrite, so its identity stays as the template wrote it - and
    template sync, reproducing init through `initialised()`, agrees.
    """
    if any(part in SKIP_DIRS for part in path.parts) or workflow_file(path):
        return False
    return path.suffix in TEXT_SUFFIXES or path.name in TEXT_NAMES


def initialised(
    path: str,
    data: bytes,
    *,
    owner: str,
    repo: str,
    display: str,
    template_owner: str,
    year: int,
) -> bytes:
    """What initialisation leaves in one file: `data` itself, or its rewrite.

    `main()` runs exactly this for every file, and template sync runs it to
    reproduce what init did to a file months ago. One function, so the two
    can never disagree about a single byte: a file that read as unchanged
    to init but as changed to the sync would look like the owner's own edit,
    and be merged as one.

    ⚠️ THE NEWLINES ARE PART OF THE CONTRACT. Init reads with universal
    newlines and writes only when the text changed, so a CRLF file whose
    identity was rewritten comes out LF, and one with nothing to rewrite
    keeps every byte.

    Two things init does lie outside this, and a sync meets neither. A file
    only the template needs is deleted - or, a workflow file, left as it was
    generated - and no sync keeps it current or remembers it. A folder log's
    rows are redrawn, and a sync never compares a log's rows, only the words
    around them.
    """
    if not considered(pathlib.PurePosixPath(path)):
        return data
    try:
        original = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    original = original.replace("\r\n", "\n").replace("\r", "\n")
    text = rewrite(
        original,
        owner=owner,
        repo=repo,
        display=display,
        template_owner=template_owner,
        year=year,
    )
    return text.encode("utf-8") if text != original else data


def _template_sync():
    """template-sync.py, beside this script. Loaded on use: it imports this file too."""
    path = pathlib.Path(__file__).with_name("template-sync.py")
    spec = importlib.util.spec_from_file_location("template_sync", path)
    module = importlib.util.module_from_spec(spec)
    # Registered BEFORE it runs, as importlib's own recipe does: its
    # dataclasses resolve their string annotations through sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def shape_of(root: pathlib.Path) -> str:
    """The paragraph the initial commit gives the template's shape.

    Chosen by what is actually IN the tree rather than by a name a fork could
    change: the golden path carries a structure, src/ among it, beside its
    seeds in docs/templates/, and any other tree is described in general.
    """
    if (root / "docs/templates").is_dir() and (root / "src").is_dir():
        return (
            "This is the golden path. A working structure arrived with\n"
            "it - src/, tests/, packages/, benchmarks/, assets/, docs/ - along\n"
            "with the community health files, while every engineering standard\n"
            "is followed by link to the shared standards repository rather than\n"
            "by copy.\n"
        )
    return (
        "This is a golden-path template whose engineering standards are\n"
        "followed by link to the shared standards repository rather than by\n"
        "copy.\n"
    )


def remove_template_only(root: pathlib.Path, sync) -> tuple[list[str], list[str]]:
    """Delete every tracked file the list keeps for the template alone, but a workflow file.

    Returns the paths deleted, and the workflow files left for the owner to
    delete: GitHub refuses the push of a deleted one, and with it everything
    else initialisation did.

    `sync` is template-sync.py, whose reader decides what the list means, so
    initialisation and every later sync read its heading alike. The list and
    the lock are never deleted, whatever it says: a generated repository syncs
    through them. A template with no list deletes nothing here.
    """
    listed = root / sync.LIST_PATH
    if not listed.is_file():
        return [], []
    tracked = [p for p in sync.decode(sync.git(root, "ls-files", "-z")).split("\0") if p]
    only = sync.template_only(listed.read_text(encoding="utf-8", errors="replace"), tracked)
    removed: list[str] = []
    left: list[str] = []
    for rel in sorted(only - {sync.LIST_PATH, sync.LOCK_PATH}):
        path = root / rel
        if sync.unsafe(rel) or not (path.is_file() or path.is_symlink()):
            continue
        if workflow_file(rel):
            left.append(rel)
            continue
        path.unlink()
        removed.append(rel)
    return removed, left


def visibility_of(repository) -> str | None:
    """`public`, `private` or `internal`, as a repository object says it; None when it says neither."""
    if not isinstance(repository, dict):
        return None
    visibility = repository.get("visibility")
    if visibility in ("public", "private", "internal"):
        return visibility
    private = repository.get("private")
    if isinstance(private, bool):
        return "private" if private else "public"
    return None


def event_repository() -> dict:
    """The repository object in the payload of the event that started this run, or {} without one."""
    path = os.environ.get("GITHUB_EVENT_PATH")
    if not path:
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload.get("repository") or {}


def remove_vulnerability_form(root: pathlib.Path, visibility: str | None) -> tuple[list[str], list[str]]:
    """Delete the vulnerability issue form from a public repository; see the header.

    Returns the paths deleted, and the paths kept because the visibility
    could not be read. Neither case is guessed: kept on a public repository
    the form publishes every report filed through it, and deleted from a
    private one it leaves no intake at all.
    """
    present = [VULNERABILITY_FORM] if (root / VULNERABILITY_FORM).is_file() else []
    if visibility == "public":
        for rel in present:
            (root / rel).unlink()
        return present, []
    if visibility is None:
        return [], present
    return [], []


def main() -> int:
    token = os.environ["GH_TOKEN"]
    repo = os.environ["REPO"]                       # owner/name
    owner = os.environ["OWNER"]
    sentinel = pathlib.Path(os.environ.get("SENTINEL", ".github/TEMPLATE_INIT"))
    template_owner = os.environ.get("TEMPLATE_OWNER", "tannergolden")
    amend = os.environ.get("AMEND_INITIAL", "true").lower() == "true"
    branch = os.environ.get("DEFAULT_BRANCH") or run("git", "rev-parse", "--abbrev-ref", "HEAD")

    if not sentinel.is_file():
        print(f"No sentinel at {sentinel}: this repository is already initialised. Nothing to do.")
        summary("### 🎉 Template Init\n\nAlready initialised; nothing to do.\n")
        return 0

    # THE GUARD IS THE FLAG, NOT THE NAME. Matching on a repository name would
    # break the moment the template is renamed, and would break silently: the
    # template would start initialising itself, rewriting its own identity and
    # deleting its own sentinel. `is_template` is true only for a template and
    # false for every repository generated from one.
    if os.environ.get("IS_TEMPLATE", "").lower() == "true":
        print("This IS a template repository, not a copy of one. Refusing to initialise itself.")
        summary("### 🎉 Template Init\n\nSkipped: this is the template itself.\n")
        return 0

    name = repo.split("/", 1)[1]

    # GitHub records which template a repository was generated from, so the
    # commit message can name it accurately instead of repeating a constant
    # that a rename would falsify. The same object says whether the
    # repository is public, and the event that started the run says it too
    # when the API could not be read.
    repository = api(f"repos/{repo}", token)
    generated_from = ((repository.get("template_repository") or {}).get("full_name") or "").strip()
    visibility = visibility_of(repository) or visibility_of(event_repository())

    profile = api(f"users/{owner}", token)
    display = (profile.get("name") or "").strip() or owner
    account_id = profile.get("id")
    email = (
        f"{account_id}+{owner}@users.noreply.github.com"
        if account_id
        else f"{owner}@users.noreply.github.com"
    )

    print(f"Owner: {display} ({owner}) <{email}>")
    print(f"Repository: {repo}")

    # UTC, explicitly: a naive local date is whatever the runner's clock
    # says, and a copyright year that flips a day early or late is exactly
    # the kind of thing nobody notices until an audit.
    this_year = datetime.datetime.now(tz=datetime.timezone.utc).year

    # Template sync's script reads the list - what the template keeps for
    # itself, and what a sync keeps current - and draws the folder logs, so
    # initialisation reads and draws them exactly as every later sync will.
    sync = _template_sync()
    root = pathlib.Path(".")
    listed = (root / sync.LIST_PATH).is_file()

    # First, before anything is rewritten: a file only the template needs is
    # deleted, never claimed - but a workflow file, which only its owner can
    # delete. The sentinel is usually among them, and is removed below either
    # way.
    try:
        removed, left = remove_template_only(root, sync)
    except sync.SyncError as exc:
        raise SystemExit(f"::error title=Initialisation::{exc}") from None
    deleted = [path for path in removed if path != sentinel.as_posix()]
    if deleted:
        print(f"Deleted {len(deleted)} file(s) only the template needs: {', '.join(deleted)}.")
    for path in left:
        print(f"::warning title=Initialisation::{path} serves only the template, but GitHub lets no workflow "
              f"token change a workflow file, so it stays. Delete it yourself; its line in {sync.LIST_PATH} "
              "is switched off, so no sync brings it back.")

    # A public repository's issues are public, so the issue form for
    # vulnerabilities goes; its reports take the private route. The header
    # says why, and what the next sync does about it.
    exposed, unsure = remove_vulnerability_form(root, visibility)
    for path in exposed:
        print(f"Deleted {path}: this repository is public, so a vulnerability reported through it would be published.")
    for path in unsure:
        print(f"::warning title=Initialisation::Could not tell whether this repository is public, so {path} stays. "
              "If it is public, delete it: every issue there is public, so a vulnerability reported through it "
              "is published. A private repository keeps it.")

    changed: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or not considered(path):
            continue
        try:
            original = path.read_bytes()
        except OSError:
            continue

        data = initialised(
            path.as_posix(),
            original,
            owner=owner,
            repo=repo,
            display=display,
            template_owner=template_owner,
            year=this_year,
        )

        if data != original:
            path.write_bytes(data)
            changed.append(str(path))

    sentinel.unlink(missing_ok=True)
    print(f"Rewrote {len(changed)} file(s); removed {sentinel}.")

    # ⚠️ TEMPLATE SYNC'S BASELINE IS RECORDED HERE OR NOWHERE. The commit
    # GitHub generated is the template's tree byte for byte, and the amend
    # below replaces it, so this is the last moment its blobs are known
    # exactly. The lock records them, with the identity just stamped, and
    # every later sync measures the owner's edits against it - every file but
    # those the list keeps for the template alone, which this repository
    # never holds once its owner deletes what was left above. Written after
    # the rewrite above, so its own contents are never rewritten.
    if listed:
        lock = sync.generation_lock(
            root,
            template=generated_from,
            identity=sync.Identity(owner, repo, display, this_year),
        )
        (root / sync.LOCK_PATH).write_text(sync.dump_lock(lock), encoding="utf-8")
        print(f"Recorded the template's {len(lock.files)} file(s) in {sync.LOCK_PATH}.")

    # Last, once the tree is final: every folder log is redrawn from it, so
    # none names the sentinel or a file deleted above, and the lock is logged
    # beside the list it belongs to. Never the log beside the workflows: the
    # push would be refused for it, and nothing beside it changed.
    try:
        markdown = [p for p in sync.decode(sync.git(root, "ls-files", "-z")).split("\0")
                    if p.endswith(".md") and not workflow_file(p)]
    except sync.SyncError as exc:
        raise SystemExit(f"::error title=Initialisation::{exc}") from None
    redrawn = sync.redraw_indexes(root, markdown, title="Initialisation")
    if redrawn:
        print(f"Redrew the folder log in {', '.join(redrawn)}.")

    run("git", "config", "user.name", display)
    run("git", "config", "user.email", email)
    run("git", "add", "-A")

    if not run("git", "status", "--porcelain"):
        print("Nothing changed after substitution.")
        return 0

    commit_count = int(run("git", "rev-list", "--count", "HEAD") or "0")
    before_amend = run("git", "rev-parse", "HEAD")

    # The subject names the ACTUAL template, read from the API rather than
    # hardcoded, so a rename never falsifies history. Guarded against the
    # subject-length law for pathological repository names.
    subject = f"feat: 🎉 initialise {name} from {generated_from}" if generated_from else f"feat: 🎉 initialise {name} from its template"
    if len(subject) > 100:
        subject = f"feat: 🎉 initialise {name}"
    if len(subject) > 100:
        subject = "feat: 🎉 initialise the generated repository"

    shape = shape_of(root)
    source_line = f"Generated from {generated_from}.\n" if generated_from else "Generated from a template.\n"
    # Named file by file, so the history says exactly what never arrived and
    # where to look for it.
    gone = (
        "\n"
        "It also deleted what only ever served the template, as\n"
        ".github/template-sync names it under \"Only ever in the template\":\n"
        "\n"
        + "".join(f"- {path}\n" for path in deleted) +
        "\n"
        "Each keeps its line there, switched off. Take the # away from one\n"
        "and run 🔄 Template Sync to have it back.\n"
    ) if deleted else ""
    # And what is still here, file by file, since only its owner can delete it.
    stays = (
        "\n"
        "It could not delete what only ever served the template under\n"
        ".github/workflows/, because GitHub lets no workflow token change a\n"
        "file there. Delete each by hand; its line stays switched off, so no\n"
        "sync brings it back:\n"
        "\n"
        + "".join(f"- {path}\n" for path in left)
    ) if left else ""
    # And the issue form a public repository would publish reports through.
    public = (
        "\n"
        "This repository is public, and so is every issue on it, so it also\n"
        "deleted the issue form for vulnerability reports:\n"
        "\n"
        + "".join(f"- {path}\n" for path in exposed)
        + "\n"
        "A report filed through it would be published the moment it was\n"
        "filed. Private vulnerability reporting, which 🎯 Apply Standards\n"
        "switches on, is the intake here instead.\n"
        + (
            "\n"
            "Its line in .github/template-sync stays as it was, and the next\n"
            "🔄 Template Sync reads it as deleted: it switches the line off and\n"
            "never brings the form back.\n"
            if listed else ""
        )
    ) if exposed else ""
    message = (
        subject + "\n"
        "\n"
        + source_line + shape +
        "\n"
        "Initialisation rewrote every identity the template stamped - the\n"
        "licence holder, the contact links, every credit naming the template's\n"
        "author - to this repository's owner, and set the licence year to the\n"
        "year of generation, where it stays. References to repositories on the\n"
        "template's account were deliberately left alone - the shared\n"
        "standards the workflow stubs call among them - because each belongs\n"
        "to that account, not this one.\n"
        + gone + stays + public +
        "\n"
        "Already wired: continuous integration, secret scanning, static\n"
        "analysis, workflow linting, governance automation, and pull request\n"
        "validation all run from the first push, calling shared workflows\n"
        "pinned to a major tag so fixes arrive without a pull request.\n"
        "\n"
        "Not wired yet, and deliberately so. checks.yml needs this project's\n"
        "real lint, test, and build commands. Until it has them it checks only\n"
        "what the template gave it, or fails where it was given nothing to\n"
        "check, because a check that checks nothing would report green to\n"
        "branch protection.\n"
        "The repository settings and the branch and tag rulesets are written\n"
        "by dispatching 🎯 Apply Standards with an ADMIN_TOKEN. The README's\n"
        "first five minutes walks through both.\n"
    )

    # A fresh generation has exactly one commit, and template generation
    # leaves it as a bare "Initial commit". Amending is safe there and
    # nowhere else, so the count is checked rather than assumed.
    if amend and commit_count == 1:
        # --reset-author, because --amend keeps the ORIGINAL author and the
        # whole point is that this commit becomes the new owner's.
        run("git", "commit", "--amend", "--reset-author", "-m", message, "--signoff")
        # ⚠️ THE LEASE NEEDS AN EXPLICIT VALUE HERE. A bare --force-with-lease
        # compares against the remote-tracking ref for the destination, and
        # there is none: the push targets a credentialed URL rather than a
        # named remote, so git has no refs/remotes/*/<branch> to read and
        # rejects the push as "stale info" every single time. Naming the
        # commit we started from keeps the protection (a push that raced us
        # still aborts) without depending on a ref that cannot exist.
        push = ["git", "push",
                f"--force-with-lease=refs/heads/{branch}:{before_amend}",
                f"https://x-access-token:{token}@github.com/{repo}.git", f"HEAD:{branch}"]
        mode = "amended the initial commit"
    else:
        run("git", "commit", "-m", message, "--signoff")
        push = ["git", "push",
                f"https://x-access-token:{token}@github.com/{repo}.git", f"HEAD:{branch}"]
        mode = f"added a commit ({commit_count} already present, so history was not rewritten)"

    result = subprocess.run(push, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = result.stderr.replace(token, "***").strip()
        print(f"::error title=Init could not push::{detail}")
        summary(
            "### 🎉 Template Init\n\n"
            "**The substitution was made but could not be pushed.** This usually means "
            "branch protection is already active on the default branch. Run the workflow "
            "again once protection allows it, or apply the changes by hand.\n"
        )
        return 1

    print(f"Initialised: {mode}.")
    summary(
        "### 🎉 Template Init\n\n"
        "| Field | Value |\n| :--- | :--- |\n"
        f"| Owner | {display} (`@{owner}`) |\n"
        f"| Commit identity | `{email}` |\n"
        f"| Files rewritten | {len(changed)} |\n"
        f"| Deleted, only the template needs them | {len(deleted)} |\n"
        + (f"| Left for you to delete, workflow files only the template needs | {len(left)} |\n" if left else "")
        + (f"| Deleted, issue forms a public repository would publish reports through | {len(exposed)} |\n"
           if exposed else "") +
        f"| Folder logs redrawn | {len(redrawn)} |\n"
        f"| History | {mode} |\n"
        "\n"
        + ("**Deleted:** " + ", ".join(f"`{path}`" for path in deleted) + ". Each keeps its line in "
           "`.github/template-sync`, switched off.\n\n" if deleted else "")
        + ("**Left for you to delete:** " + ", ".join(f"`{path}`" for path in left) + ". GitHub lets no "
           "workflow token change a workflow file, so initialisation could not. Each keeps its line in "
           "`.github/template-sync`, switched off, so no sync brings it back.\n\n" if left else "")
        + ("**Deleted, as this repository is public:** " + ", ".join(f"`{path}`" for path in exposed) + ". "
           "Every issue here is public, so a vulnerability reported through it would be published; private "
           "vulnerability reporting is the intake instead."
           + (" The next 🔄 Template Sync switches its line off rather than bringing it back." if listed else "")
           + "\n\n" if exposed else "")
        + ("**Kept, visibility unknown:** " + ", ".join(f"`{path}`" for path in unsure) + ". Delete it if "
           "this repository is public.\n\n" if unsure else "") +
        "The sentinel has been removed, so this workflow is now inert and will not run again.\n"
        "\n"
        "> **Next:** give `.github/workflows/checks.yml` the lint, test, and build commands for "
        "your language. Until then CI fails on purpose.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
