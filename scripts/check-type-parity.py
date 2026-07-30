#!/usr/bin/env python3
"""Assert the Conventional Commit type list is the same in all five places.

docs/distribution/Conventional-Commits.md promises one rule set with more
than one encoding. Nothing enforced that promise, and the copies sit in
three languages, so drift would be silent and would show up as a commit that
passes one gate and fails another.

The five:

  scripts/commit-check.py            DEFAULT_TYPES, the fallback the CI gate
                                     uses when no COMMIT_TYPES is passed
  config/commitlint.config.js        type-enum, for anyone running commitlint
                                     locally in a Node toolchain
  .github/workflows/semantic-pr.yml  the commit-types input default, which is
                                     what actually reaches the commit gate
  .github/workflows/semantic-pr.yml  the title check's own `types:` list. A
    (title-types)                    squash merge inherits the pull request
                                     title as the commit subject, so this is
                                     the most consequential copy of all
  actions/commit-check/action.yml    the action's `types` default, for anyone
                                     calling the action directly

Run it with `make check-types`, or as part of `make lint-docs`, which is
what `self-checks.yml` calls.

Exit 0 when they agree, 1 when they do not, naming what differs.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Keyed by LABEL, not by path: `semantic-pr.yml` encodes the list twice and
# each copy needs its own pattern. A label may carry a `:suffix` to
# distinguish them; the path is everything before it.
SOURCES = {
    "scripts/commit-check.py": (
        r'DEFAULT_TYPES\s*=\s*\(\s*"([^"]*)"',
        lambda m: m.split(","),
    ),
    "config/commitlint.config.js": (
        r"'type-enum':\s*\[.*?\[(.*?)\]",
        lambda m: re.findall(r"'([a-z]+)'", m),
    ),
    ".github/workflows/semantic-pr.yml": (
        r"commit-types:.*?default:\s*'([^']*)'",
        lambda m: m.split(","),
    ),
    # ⚠️ THE TITLE GATE, and the reason this file grew past three sources.
    # A squash merge inherits the pull request title as the commit subject,
    # and `semantic-pr.yml` calls this "the only gate keeping a banned em
    # dash out of history". Adding a type to the other copies without this
    # one passed parity and then failed the required title check on the
    # first pull request that used it: exactly the "passes one gate and
    # fails another" drift this script exists to prevent, in the copy it
    # was not reading.
    ".github/workflows/semantic-pr.yml:title-types": (
        r"\n\s+types:\s*\|\n((?:\s+[a-z]+\n)+)",
        lambda m: m.split(),
    ),
    # The action's own default, which reaches anyone calling it directly
    # rather than through semantic-pr.yml.
    "actions/commit-check/action.yml": (
        r"\n  types:.*?default:\s*'([^']*)'",
        lambda m: m.split(","),
    ),
}


def read(rel: str, pattern: str, parse) -> list[str] | None:
    # A label may carry a `:suffix` naming which copy in the file it means.
    path = ROOT / rel.split(":", 1)[0]
    if not path.is_file():
        print(f"::error::{rel} is missing; the type list cannot be compared.")
        return None
    match = re.search(pattern, path.read_text(encoding="utf-8"), re.S)
    if not match:
        print(f"::error::{rel} no longer matches the pattern this check reads.")
        print("         Either the file was restructured or the list moved.")
        return None
    return [t.strip() for t in parse(match.group(1)) if t.strip()]


def main() -> int:
    found: dict[str, list[str]] = {}
    for rel, (pattern, parse) in SOURCES.items():
        types = read(rel, pattern, parse)
        if types is None:
            return 1
        found[rel] = types

    lists = list(found.values())
    if all(t == lists[0] for t in lists):
        print(f"OK: all {len(found)} sources agree on {len(lists[0])} types.")
        print("    " + ", ".join(lists[0]))
        return 0

    print("::error::The Conventional Commit type list has drifted.")
    for rel, types in found.items():
        print(f"  {rel}")
        print(f"    {', '.join(types)}")

    union = sorted({t for types in found.values() for t in types})
    for rel, types in found.items():
        missing = [t for t in union if t not in types]
        if missing:
            print(f"  {rel} is missing: {', '.join(missing)}")

    # Order matters as well as membership: the lists are read by humans
    # comparing them side by side, and a reordered copy reads as a different
    # rule even when it accepts the same set.
    sets = [set(t) for t in lists]
    if all(s == sets[0] for s in sets):
        print("  Membership matches; only the ORDER differs. Align them anyway.")

    return 1


if __name__ == "__main__":
    sys.exit(main())
