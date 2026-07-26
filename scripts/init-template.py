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
# the new owner's, then removes its own sentinel so it can never run again.
#
# ⚠️ WHAT IT DOES NOT REWRITE: `tannergolden/standards` references. Those are
# the SHARED repository every consumer calls, and they are correct for
# everybody. Rewriting them to the new owner would point the stubs at a
# repository that does not exist. The distinction is the whole reason this
# uses targeted rules rather than a blanket find-and-replace.
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
    ".sh", ".py", ".js", ".ts", ".editorconfig", ".gitignore", ".gitattributes",
}


def run(*args: str, check: bool = True) -> str:
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        raise SystemExit(f"::error::`{' '.join(args[:3])}` failed: {result.stderr.strip()}")
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
    # that a rename would falsify.
    generated_from = ((api(f"repos/{repo}", token).get("template_repository") or {})
                      .get("full_name") or "").strip()

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

    # Targeted rules, never a blanket replace. The template owner's handle
    # appears both as an identity to rewrite and as part of the shared
    # standards repository path, which must survive untouched.
    # UTC, explicitly: a naive local date is whatever the runner's clock
    # says, and a copyright year that flips a day early or late is exactly
    # the kind of thing nobody notices until an audit.
    this_year = datetime.datetime.now(tz=datetime.timezone.utc).year
    keep = f"{template_owner}/standards"
    guard = "\x00KEEP\x00"

    replacements = [
        # Contact links carry a placeholder because GitHub never substitutes
        # one; this is the substitution.
        ("OWNER/REPOSITORY", repo),
        (f"[@{template_owner}](https://github.com/{template_owner})", f"[@{owner}](https://github.com/{owner})"),
        (f"github: [{template_owner}]", f"github: [{owner}]"),
    ]

    changed: list[str] = []
    for path in sorted(pathlib.Path(".").rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix not in TEXT_SUFFIXES and path.name not in {"LICENSE", "CODEOWNERS"}:
            continue
        try:
            original = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        text = original
        for old, new in replacements:
            text = text.replace(old, new)

        # The licence holder is the template author's name, not a handle.
        # The YEAR is restamped too: it is the year this repository was
        # created, not the year the template was written. Carrying the
        # template's year forward would put a copyright date on a generated
        # repository that predates the work it covers, and nothing would ever
        # correct it - `license-year` only rolls a year forward, it never
        # questions the one already there.
        # A lambda, not a replacement string: a display name is arbitrary user
        # input and `\1` in it would be read as a backreference.
        text = re.sub(
            r"Copyright \(c\) \d{4}(?:\s*[-\u2013]\s*\d{4})?\s+Tanner Golden",
            lambda _: f"Copyright (c) {this_year} {display}",
            text,
        )

        # Any remaining bare handle becomes the new owner's, EXCEPT where it
        # is part of the shared standards path.
        if template_owner in text:
            text = text.replace(keep, guard)
            text = text.replace(template_owner, owner)
            text = text.replace(guard, keep)

        if text != original:
            path.write_text(text, encoding="utf-8")
            changed.append(str(path))

    sentinel.unlink()
    changed.append(str(sentinel))
    print(f"Rewrote {len(changed) - 1} file(s); removed {sentinel}.")

    run("git", "config", "user.name", display)
    run("git", "config", "user.email", email)
    run("git", "add", "-A")

    if not run("git", "status", "--porcelain"):
        print("Nothing changed after substitution.")
        return 0

    commit_count = int(run("git", "rev-list", "--count", "HEAD") or "0")
    message = (
        f"feat: 🎉 initialise {name} from the repository template\n"
        "\n"
        + (f"Generated from {generated_from}, a language-agnostic scaffold that\n"
           if generated_from else "Generated from a language-agnostic scaffold that\n")
        + "carries structure, community health files, and document templates while every\n"
        "engineering standard is followed by link rather than copied.\n"
        "\n"
        "Initialisation rewrote the template author's identity to this repository's\n"
        "owner: the licence holder, the funding target, the documentation footers, and\n"
        "the issue-chooser contact link. References to the shared standards repository\n"
        "were deliberately left alone, since those are what the workflow stubs call.\n"
        "\n"
        "What is wired already: continuous integration, secret scanning, static\n"
        "analysis, workflow linting, governance automation, and pull request validation\n"
        "all run from the first push, calling shared workflows pinned to a major tag so\n"
        "fixes arrive without a pull request.\n"
        "\n"
        "What is not wired yet: this repository has no build system, deliberately. CI\n"
        "fails until .github/workflows/checks.yml is given the lint, test, and build\n"
        "commands for whatever language this project turns out to be written in. A\n"
        "check that checked nothing would report green to branch protection, so it\n"
        "refuses to.\n"
    )

    # A fresh generation has exactly one commit, and template generation
    # leaves it as a bare "Initial commit". Amending is safe there and
    # nowhere else, so the count is checked rather than assumed.
    if amend and commit_count == 1:
        # --reset-author, because --amend keeps the ORIGINAL author and the
        # whole point is that this commit becomes the new owner's.
        run("git", "commit", "--amend", "--reset-author", "-m", message, "--signoff")
        push = ["git", "push", "--force-with-lease",
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
        f"| Files rewritten | {len(changed) - 1} |\n"
        f"| History | {mode} |\n"
        "\n"
        "The sentinel has been removed, so this workflow is now inert and will not run again.\n"
        "\n"
        "> **Next:** give `.github/workflows/checks.yml` the lint, test, and build commands for "
        "your language. Until then CI fails on purpose.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
