#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
# =============================================================================
# Standards Version Check - the one gap a moving major tag leaves open
# =============================================================================
# Stubs pin `@v1`, a MOVING major tag, so every fix and feature in the v1 line
# reaches a consuming repository the moment it is published. No pull request,
# no action, nothing to maintain. That is the point of the moving tag and it
# needs no help.
#
# It leaves exactly one thing uncovered: `@v1` never becomes `@v2`. A new
# major is a BREAKING change - a renamed required check, a removed input - so
# it must never arrive by itself. But nothing tells a consumer it exists
# either, and a repository can sit on a superseded major indefinitely without
# a single signal.
#
# This is that signal, and nothing more. It opens ONE issue when a newer major
# is published and never opens a second, because a notice repeated weekly is
# a notice nobody reads. It changes no files and moves no pins: adopting a new
# major is a decision, not a chore.
#
# ⚠️ THIS IS NOT A DEPENDENCY UPDATER, deliberately. Dependabot already
# updates `uses:` references, including reusable-workflow calls, and this
# repository's own dependabot stub enables it. Writing a third mechanism to do
# what a moving tag and Dependabot already cover between them would be a
# maintenance burden invented to solve a problem that is already solved.
#
# Requires: GH_TOKEN, REPO
# Optional: STANDARDS_REPO, WORKFLOW_DIR, LABEL
# =============================================================================
from __future__ import annotations

import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"


def api(path: str, token: str, method: str = "GET", body: dict | None = None):
    data = json.dumps(body).encode() if body else None
    request = urllib.request.Request(  # noqa: S310 - constant API host
        f"{API}/{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "standards-version-check",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        return json.load(response)


def main() -> int:
    # Read by name rather than by subscript: a consumer whose stub forgets
    # `secrets: inherit` used to get a bare KeyError traceback out of a
    # workflow whose entire job is to post a friendly advisory notice. Every
    # other script here names the cause and the fix.
    missing = [name for name in ("GH_TOKEN", "REPO") if not os.environ.get(name)]
    if missing:
        print(
            f"::error title=Standards version::{' and '.join(missing)} "
            f"{'are' if len(missing) > 1 else 'is'} not set, so this check cannot run. "
            "Pass `secrets: inherit` from your stub, and check the action is given a "
            "`token` and a `repository`."
        )
        return 1
    token = os.environ["GH_TOKEN"]
    repo = os.environ["REPO"]
    standards = os.environ.get("STANDARDS_REPO", "tannergolden/standards")
    workflow_dir = pathlib.Path(os.environ.get("WORKFLOW_DIR", ".github/workflows"))
    label = os.environ.get("LABEL", "").strip()

    # What this repository actually pins, read from its own stubs.
    pinned: dict[str, int] = {}
    pattern = re.compile(re.escape(standards) + r"/[^@\s]+@v(\d+)")
    for f in sorted(workflow_dir.glob("*.yml")) + sorted(workflow_dir.glob("*.yaml")):
        for major in pattern.findall(f.read_text(encoding="utf-8")):
            pinned[f.name] = max(pinned.get(f.name, 0), int(major))

    if not pinned:
        print(f"::notice::No stub in {workflow_dir} pins {standards} at a major tag. Nothing to compare.")
        return 0

    current = max(pinned.values())
    print(f"Pinned major across {len(pinned)} stub(s): v{current}")

    try:
        latest = api(f"repos/{standards}/releases/latest", token)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        # Advisory by nature: a notifier that reddens CI because an API blipped
        # is worse than one that stays quiet for a week.
        print(f"::warning title=Could not check for a new major::{exc}")
        return 0

    tag = (latest.get("tag_name") or "").strip()
    match = re.match(r"^v?(\d+)", tag)
    if not match:
        print(f"::warning::Latest release of {standards} is tagged '{tag}', which has no readable major.")
        return 0

    available = int(match.group(1))
    print(f"Latest published major: v{available}")

    if available <= current:
        print(f"✅ Up to date: pinned at v{current}, latest is v{available}.")
        return 0

    title = f"⬆️ {standards} v{available} is available (this repository pins v{current})"

    # One issue, ever. Searching by title rather than tracking state in a file
    # means this works from the first run in a repository that has never run
    # it before.
    query = urllib.parse.quote(f'repo:{repo} in:title "{standards} v{available} is available"')
    try:
        found = api(f"search/issues?q={query}", token)
        if found.get("total_count", 0) > 0:
            existing = found["items"][0]
            print(f"Already reported in #{existing['number']}. Not opening another.")
            return 0
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print(f"::warning::Could not search existing issues ({exc}); not opening one, to avoid duplicates.")
        return 0

    stub_list = "\n".join(f"- `{name}` pins `v{major}`" for name, major in sorted(pinned.items()))
    body = (
        f"`{standards}` has published **v{available}**. This repository pins **v{current}**.\n"
        "\n"
        "### Why nothing has changed\n"
        "\n"
        f"A major version is a **breaking** change: a renamed required check, a removed input, "
        f"a different job id. Moving to it is a decision, so `@v{current}` keeps working exactly "
        "as it does today and nothing here has been touched. Fixes and features within "
        f"v{current} continue to arrive on their own, as they always have.\n"
        "\n"
        "### Your stubs\n"
        "\n"
        f"{stub_list}\n"
        "\n"
        "### Adopting it\n"
        "\n"
        f"1. Read the v{available} release notes, paying attention to any **required check name** "
        "that changed - renaming one leaves branch protection waiting on a check that never reports.\n"
        f"2. Change `@v{current}` to `@v{available}` in the stubs above, on a branch.\n"
        "3. Open a pull request and confirm every required check still reports before merging.\n"
        "\n"
        "---\n"
        "_This is the only notice you will get for v"
        f"{available}. Close it whenever you like; it will not be reopened._"
    )

    payload: dict = {"title": title, "body": body}
    if label:
        payload["labels"] = [label]

    try:
        issue = api(f"repos/{repo}/issues", token, method="POST", body=payload)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print(f"::error title=Could not open the notice::{exc}")
        return 1

    print(f"::notice title=New major available::Opened #{issue['number']} for {standards} v{available}.")
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(
                "### ⬆️ Standards Version\n\n"
                f"`{standards}` **v{available}** is available; this repository pins **v{current}**.\n\n"
                f"Opened issue #{issue['number']}. Nothing was changed - adopting a major is a decision.\n"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
