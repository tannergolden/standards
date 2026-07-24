#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
# =============================================================================
# Commit Message Check - Conventional Commits, enforced per commit
# =============================================================================
# The pull-request TITLE check covers what a squash merge writes into
# history. It covers nothing else. On a repository that merges or rebases
# instead, every commit message on the branch lands on the default branch
# having been validated by nothing at all. This is that gate.
#
# WHY THIS IS NOT commitlint. The workflow that calls it runs on
# `pull_request_target`, which hands an elevated token to a job whose
# checkout would be the CONTRIBUTOR'S code. Running `npm install` there,
# with the pull request's own package.json and its postinstall scripts,
# would hand that token to whoever opened it. So this reads the commits
# through the API and never checks out, executes, or installs anything from
# the branch under review - the same reasoning that shapes the DCO check
# beside it.
#
# `config/commitlint.config.js` remains published for running the same rules
# in a local Node toolchain. The two encode ONE rule set and change
# together; editing either alone produces a rule nobody enforces or a gate
# nothing documents.
#
# EXEMPT BY CONTRACT, matching the DCO check so one pull request cannot pass
# one gate and fail the other on the same commit:
#   - bot-authored commits, which follow their own conventions
#   - merge commits, which are mechanical rather than authored
#
# FAILS CLOSED on API errors. A gate that passes when GitHub is unreachable
# is not a gate.
#
# Requires: GH_TOKEN, REPO, PR_NUMBER
# Optional: COMMIT_TYPES, MAX_HEADER_LENGTH
# =============================================================================
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"

DEFAULT_TYPES = (
    "feat,fix,docs,style,refactor,perf,test,build,ci,chore,revert,security"
)

# U+2013 EN DASH through U+2015 HORIZONTAL BAR. The em dash is the banned
# character; its neighbours are caught with it because none of the three
# belongs in a commit message and a range is harder to get wrong than a
# single code point. Written as escapes so this file never contains one.
BANNED_DASHES = re.compile("[\u2013-\u2015]")

# An optional leading emoji and space. The pull request title check encodes
# the same thing as UTF-16 surrogate pairs, because the JavaScript action
# compiling it has no unicode flag; Python matches code points directly, so
# the ranges stay legible here.
EMOJI_PREFIX = re.compile(
    "^[\U0001F000-\U0001FAFF\u2190-\u21FF\u2300-\u27BF\u2900-\u2BFF]\uFE0F?\\s"
)


def fail(message: str) -> None:
    print(f"::error title=Commit check::{message}")
    sys.exit(1)


def fetch_commits() -> list[dict]:
    """Two clients, one contract, matching scripts/dco-check.sh.

    `gh api` is the primary. When it cannot reach the endpoint, a plain
    HTTPS client retries. If both are exhausted the caller fails closed
    rather than reporting zero offenders.
    """
    repo = os.environ["REPO"]
    number = os.environ["PR_NUMBER"]
    path = f"repos/{repo}/pulls/{number}/commits"

    try:
        out = subprocess.run(
            ["gh", "api", "-X", "GET", path, "--paginate"],
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        ).stdout
        # --paginate concatenates one JSON array per page.
        commits: list[dict] = []
        decoder = json.JSONDecoder()
        index = 0
        while index < len(out):
            while index < len(out) and out[index].isspace():
                index += 1
            if index >= len(out):
                break
            page, index = decoder.raw_decode(out, index)
            commits.extend(page)
        return commits
    except (subprocess.SubprocessError, OSError, ValueError) as exc:
        print(f"::warning::gh could not list the PR's commits ({exc}) - retrying via direct HTTPS.")

    commits = []
    page = 1
    while True:
        url = f"{API}/{path}?per_page=100&page={page}"
        request = urllib.request.Request(  # noqa: S310 - the URL is built from a constant API host
            url,
            headers={
                "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "commit-check",
            },
        )
        body = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
                    body = json.load(response)
                break
            except (urllib.error.URLError, OSError, ValueError) as exc:
                if attempt == 3:
                    fail(f"Unable to list the PR's commits ({exc}) - failing closed.")
        if not isinstance(body, list):
            fail("The commits endpoint did not return a list - failing closed.")
        commits.extend(body)
        if len(body) < 100:
            break
        page += 1
    return commits


def problems_for(message: str, types: list[str], max_header: int) -> list[str]:
    found = []
    header = message.split("\n", 1)[0].rstrip()

    if len(header) > max_header:
        found.append(f"the subject line is {len(header)} characters (limit {max_header})")

    match = re.match(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?: (?P<subject>.+)$", header)
    if not match:
        found.append("it does not match `<type>(<scope>): <subject>`")
    elif match.group("type") not in types:
        found.append(f"`{match.group('type')}` is not an allowed type ({', '.join(types)})")
    else:
        subject = EMOJI_PREFIX.sub("", match.group("subject"))
        if not subject[:1].islower() or not subject[:1].isascii():
            found.append(
                "the subject must start with a lowercase letter, optionally after an emoji and a space"
            )

    if BANNED_DASHES.search(message):
        found.append("it contains an em dash (use a comma, a colon, or a spaced hyphen)")

    return found


def main() -> int:
    types = [t.strip() for t in os.environ.get("COMMIT_TYPES", DEFAULT_TYPES).split(",") if t.strip()]
    max_header = int(os.environ.get("MAX_HEADER_LENGTH", "100"))

    commits = fetch_commits()
    offenders: list[tuple[str, str, list[str]]] = []
    checked = 0

    for commit in commits:
        sha = (commit.get("sha") or "")[:7]
        author = ((commit.get("author") or {}) or {}).get("login") or "-"
        parents = commit.get("parents") or []
        message = (commit.get("commit") or {}).get("message") or ""

        if author.endswith("[bot]"):
            continue
        if len(parents) >= 2:
            continue

        checked += 1
        found = problems_for(message, types, max_header)
        if found:
            offenders.append((sha, message.split("\n", 1)[0].strip(), found))

    if not offenders:
        print(f"✅ Commit messages: all {checked} human commit(s) follow Conventional Commits.")
        return 0

    print(f"::error::{len(offenders)} of {checked} commit(s) have a non-conforming message.")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("### ✍️ Commit Message Check Failed\n\n")
            handle.write(
                "Every commit must follow [Conventional Commits](https://www.conventionalcommits.org/). "
                "The pull request title is checked separately, and passing that one does not cover these.\n\n"
            )
            handle.write("| Commit | Subject | Problem |\n| :--- | :--- | :--- |\n")
            for sha, subject, found in offenders:
                handle.write(f"| `{sha}` | {subject} | {'; '.join(found)} |\n")
            handle.write(
                "\n**Fix it:** `git rebase -i @{upstream}`, reword the offending commits, "
                "then `git push --force-with-lease`. For the most recent commit, "
                "`git commit --amend` is enough.\n"
            )
    return 1


if __name__ == "__main__":
    sys.exit(main())
