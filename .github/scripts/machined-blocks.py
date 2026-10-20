#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
# =============================================================================
# Machined Block Check - a block marked with its own hash still matches it
# =============================================================================
# Some text in a repository is written by a machine somewhere else and only
# delivered here: the INTELLIGENCE block in AGENTS.md, rendered by
# tannergolden/intelligence and replaced on every sync, is the first. Such a
# block opens with a marker that carries the SHA-256 of its own text:
#
#     <!-- INTELLIGENCE:BEGIN sha256:<64 hex digits> -->
#     ...the block...
#     <!-- INTELLIGENCE:END -->
#
# A hand edit inside it is overwritten by the next delivery, silently, so
# this says so on the pull request that makes it instead. Any marker of that
# shape is checked, whatever its name, so the next machine-written block
# needs no change here.
#
# THE HASH covers the text between the markers with CRLF read as LF and the
# blank lines around it ignored, exactly as the renderer computes it, so a
# formatter that pads the block with blank lines or a checkout that converts
# line endings does not count as an edit. A block shown inside a fenced code
# block is an example, not a block, and is skipped; a fenced code block inside
# a block is part of its text, and the hash covers it.
#
# A repository with no machined block passes. Nothing here touches the
# network or anything outside the working tree.
#
# Run it from a repository's root:
#
#     python3 .github/scripts/machined-blocks.py
# =============================================================================
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys

BLOCK = re.compile(
    r"^<!-- (?P<name>[A-Z][A-Z0-9]*(?::[A-Z][A-Z0-9]*)*):BEGIN sha256:(?P<hash>[0-9a-f]{64}) -->[ \t]*\r?\n"
    r"(?P<inner>.*?)"
    r"^<!-- (?P=name):END -->[ \t]*(?:\r?\n|\Z)",
    re.M | re.S,
)
FENCE = re.compile(r"^\s*(```|~~~)")


def markdown_files() -> list[str]:
    """Every tracked Markdown file, or every one on disk outside a git checkout."""
    done = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.md", "*.markdown", "*.mdc"],
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode == 0:
        return sorted(name for name in done.stdout.split("\0") if name)
    found = []
    for folder, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules")]
        found += [os.path.join(folder, f)[2:] for f in files if f.endswith((".md", ".markdown", ".mdc"))]
    return sorted(found)


def without_fences(text: str) -> str:
    """The text with every fenced code block blanked, line for line, so line numbers hold."""
    lines, inside = [], None
    for line in text.split("\n"):
        fence = FENCE.match(line)
        if inside is None and fence:
            inside = fence.group(1)
            lines.append("")
        elif inside is not None:
            if line.strip().startswith(inside):
                inside = None
            lines.append("")
        else:
            lines.append(line)
    return "\n".join(lines)


def problems(path: str, text: str) -> list[tuple[int, str]]:
    """Each machined block in one file that no longer matches its hash, by line."""
    found = []
    seen: dict[str, int] = {}
    rows = text.split("\n")
    shown = without_fences(text)
    for match in BLOCK.finditer(shown):
        line = shown.count("\n", 0, match.start()) + 1
        name = match.group("name")
        seen[name] = seen.get(name, 0) + 1
        if seen[name] > 1:
            found.append((line, f"a second {name} block; a file carries at most one of each"))
            continue
        # The markers are found where no fence hides them, but the text the hash
        # covers is the block's own lines as they stand, its code fences included.
        first, end = shown.count("\n", 0, match.start("inner")), shown.count("\n", 0, match.end("inner"))
        inner = "".join(row + "\n" for row in rows[first:end])
        inner = inner.replace("\r\n", "\n").strip("\n") + "\n"
        if hashlib.sha256(inner.encode("utf-8")).hexdigest() != match.group("hash"):
            found.append((line, f"the {name} block was edited by hand: its text no longer matches the "
                                "hash in its marker, and the next delivery will overwrite the edit"))
    return found


def main() -> int:
    offenders: list[tuple[str, int, str]] = []
    blocks = 0
    for path in markdown_files():
        try:
            with open(path, encoding="utf-8", newline="") as handle:
                text = handle.read()
        except (OSError, UnicodeDecodeError):
            continue
        blocks += len(BLOCK.findall(without_fences(text)))
        offenders += [(path, line, message) for line, message in problems(path, text)]

    if not offenders:
        if blocks:
            print(f"✅ Machined blocks: all {blocks} match the hash their marker carries.")
        else:
            print("✅ Machined blocks: none in this repository.")
        return 0

    for path, line, message in offenders:
        print(f"::error file={path},line={line},title=Machined block::{message}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("### 🧠 Machined Block Check Failed\n\n")
            handle.write("| File | Line | Problem |\n| :--- | :--- | :--- |\n")
            for path, line, message in offenders:
                handle.write(f"| `{path}` | {line} | {message} |\n")
            handle.write(
                "\n**Fix it:** put the block back as it was delivered, with "
                "`git checkout <base> -- <file>` for that file, and change the text where "
                "it is rendered instead. For the INTELLIGENCE block, that is "
                "tannergolden/intelligence.\n"
            )
    return 1


if __name__ == "__main__":
    sys.exit(main())
