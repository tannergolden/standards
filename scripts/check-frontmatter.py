#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
# =============================================================================
# Frontmatter Check - every document says what it is before it is opened
# =============================================================================
# Document Styling & Formatting asks every Markdown document to open with
# hidden frontmatter: an HTML comment holding a few flat YAML fields.
#
#     <!--
#     title: '📝 DOCUMENT TITLE'
#     description: 'What it covers, and when to read it.'
#     type: guide
#     keywords: [search term, acronym]
#     -->
#
# An agent reads that block, or the folder log drawn from it, to decide what
# a document is and whether to open it at all. This checks every rule a
# machine can: the hidden form, the required fields, and only the fields and
# values the standard allows. Whether a description really says when to read
# its document is left to review.
#
# EXEMPT, as the standard lists them: the pull request template and any
# Markdown issue template, which GitHub reads as they are; every file a tool
# loads in its own format, meaning a skill's folder, anything under
# `.claude/`, a `*.agent.md`, `*.instructions.md`, `*.prompt.md` or
# `*.chatmode.md`, and any `---` block that names its agent or skill; a test
# fixture, which is data; and anything `.gitattributes` marks
# `linguist-generated`, which belongs to the generator that writes it. An
# agent instruction file (AGENTS.md, CLAUDE.md, GEMINI.md) may leave
# frontmatter out; one that carries it is checked like any other document.
#
# `--mode enforce`, the default, exits 1 on any problem; `--mode warn`
# reports each one as a warning and exits 0. Nothing here touches the
# network or anything outside the working tree.
#
# Run it from a repository's root:
#
#     python3 scripts/check-frontmatter.py
# =============================================================================
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

TYPES = ("index", "guide", "standard", "reference", "record", "template")
REQUIRED = ("title", "description", "type")
FIELDS = (*REQUIRED, "keywords", "status")
# A record or a template may add the fields its kind needs, each defined once
# in its template: a decision's date and evidence, a research log's verified
# date, focus and decision. Every other type carries FIELDS and no more.
OWN_FIELDS = ("record", "template")
STATUSES = ("draft", "deprecated", "archived")
DECISION_STATUSES = ("proposed", "accepted", "superseded", "deprecated")
RETIRED = {
    "tags": "type now says what the document is, and keywords holds its search terms",
    "category": "type now says what the document is",
}
MAX_KEYWORDS = 8
AGENT_FILES = ("AGENTS.md", "CLAUDE.md", "GEMINI.md", "copilot-instructions.md")
LOADER_SUFFIXES = (".agent.md", ".instructions.md", ".prompt.md", ".chatmode.md")

BLOCK = re.compile(r"\A<!--\n(?P<body>.*?)\n-->[ \t]*(?:\n|\Z)", re.S)
FIELD = re.compile(r"^(?P<key>[A-Za-z_][\w-]*):(?:[ \t]+(?P<value>.*?))?[ \t]*$")


def markdown_files() -> list[str]:
    """Every tracked Markdown file, or every one on disk outside a git checkout."""
    done = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.md"], capture_output=True, text=True, check=False
    )
    if done.returncode == 0:
        return sorted(name for name in done.stdout.split("\0") if name)
    found = []
    for folder, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules")]
        found += [os.path.join(folder, f)[2:] for f in files if f.endswith(".md")]
    return sorted(found)


def generated(paths: list[str]) -> set[str]:
    """The paths .gitattributes marks linguist-generated, which their generator owns."""
    if not paths:
        return set()
    done = subprocess.run(
        ["git", "check-attr", "-z", "--stdin", "linguist-generated"],
        input="\0".join(paths) + "\0",
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        return set()
    parts = done.stdout.split("\0")
    return {
        parts[i] for i in range(0, len(parts) - 2, 3) if parts[i + 2] in ("set", "true")
    }


def exempt(path: str, skills: set[str]) -> bool:
    """A file a tool reads in its own format, GitHub inserts verbatim, or a test keeps as data."""
    name = os.path.basename(path)
    folders = path.split("/")[:-1]
    if name == "pull_request_template.md" or "PULL_REQUEST_TEMPLATE" in folders:
        return True
    if "ISSUE_TEMPLATE" in folders and name != "README.md":
        return True
    if name == "SKILL.md" or name.endswith(LOADER_SUFFIXES):
        return True
    if ".claude" in folders or "fixtures" in folders:
        return True
    return any(path.startswith(folder + "/") for folder in skills)


def loader_fence(text: str) -> bool:
    """A `---` block naming its agent or skill, the format a loader reads and nothing else."""
    if not text.startswith("---\n"):
        return False
    block = text[4:].split("\n---", 1)[0]
    return re.search(r"^name:", block, re.M) is not None


def value(raw: str):
    """A field's value: a string, or a list for an inline `[a, b]`."""
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        items = [item.strip() for item in re.split(r",(?=(?:[^'\"]|'[^']*'|\"[^\"]*\")*$)", raw[1:-1])]
        return [unquote(item) for item in items if item]
    return unquote(raw)


def unquote(raw: str) -> str:
    if len(raw) >= 2 and raw[0] == raw[-1] == "'":
        return raw[1:-1].replace("''", "'")
    if len(raw) >= 2 and raw[0] == raw[-1] == '"':
        return raw[1:-1].replace('\\"', '"')
    return raw


def plain(text: str) -> str:
    """Letters and digits only, lowercased, so a title and a description compare by words."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def problems(path: str, text: str) -> list[tuple[int, str]]:
    """Each way one document's frontmatter breaks the standard, by line."""
    text = text.replace("\r\n", "\n")
    name = os.path.basename(path)
    if text.startswith("---\n"):
        return [(1, "the frontmatter is fenced with ---, which GitHub shows as a table at the top "
                    "of the page: wrap the same fields in <!-- and --> instead")]
    match = BLOCK.match(text)
    if not match:
        if name in AGENT_FILES:
            return []
        if text.startswith("<!--"):
            return [(1, "the frontmatter must open with <!-- alone on the first line and close "
                        "with --> alone on its own line")]
        return [(1, "no frontmatter: open the file with the hidden block Document Styling & "
                    "Formatting describes, with at least a title, a description and a type")]

    found: list[tuple[int, str]] = []
    fields: dict = {}
    lines: dict[str, int] = {}
    for offset, line in enumerate(match.group("body").split("\n"), start=2):
        if not line.strip():
            continue
        field = FIELD.match(line)
        if not field or line[0].isspace():
            found.append((offset, f"'{line.strip()}' is not a field: each one sits on its own "
                                  "line as key: value, with lists written inline as [a, b]"))
            continue
        key = field.group("key")
        if key in fields:
            found.append((offset, f"{key} appears twice"))
            continue
        fields[key] = value(field.group("value") or "")
        lines[key] = offset

    if name in AGENT_FILES and not ({"title", "description"} & fields.keys()):
        return []  # a leading comment that is not frontmatter, in a file that may go without

    kind = fields.get("type")
    for key, line in lines.items():
        if key in RETIRED:
            found.append((line, f"{key} is retired: {RETIRED[key]}"))
        elif key not in FIELDS and kind not in OWN_FIELDS:
            found.append((line, f"{key} is not a frontmatter field: a {kind or 'document'} carries "
                                f"{', '.join(FIELDS)}, and only a record or a template adds fields "
                                "of its own"))

    for key in REQUIRED:
        if key not in fields:
            found.append((1, f"missing {key}"))
        elif fields[key] in ("", []):
            found.append((lines[key], f"{key} is empty"))

    if isinstance(kind, str) and kind and kind not in TYPES:
        found.append((lines["type"], f"type is '{kind}': use one of {', '.join(TYPES)}"))
    title, description = fields.get("title"), fields.get("description")
    if isinstance(title, str) and isinstance(description, str) and title and plain(title) == plain(description):
        found.append((lines["description"], "description repeats the title: say what the document "
                                            "covers, and when to read it"))

    if kind != "template" and "status" in fields:  # a template's values are placeholders
        status = str(fields["status"]).lower()
        allowed = STATUSES + (DECISION_STATUSES if kind == "record" else ())
        if status in ("active", "current"):
            found.append((lines["status"], "leave status out while the document is current"))
        elif status not in allowed:
            found.append((lines["status"], f"status is '{fields['status']}': use "
                                           f"{', '.join(dict.fromkeys(allowed))}"))

    if "keywords" in fields:
        words, line = fields["keywords"], lines["keywords"]
        if not isinstance(words, list):
            found.append((line, "keywords is a list, written inline as [a, b]"))
        elif not words:
            found.append((line, "keywords is empty: leave the field out instead"))
        else:
            if len(words) > MAX_KEYWORDS:
                found.append((line, f"keywords holds {len(words)} terms: keep the {MAX_KEYWORDS} "
                                    "that best find this document"))
            for word in words:
                if word != word.lower():
                    found.append((line, f"keyword '{word}' is not lowercase"))
            for word in sorted({w for w in words if words.count(w) > 1}):
                found.append((line, f"keyword '{word}' appears twice"))
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check every Markdown document's hidden frontmatter.")
    parser.add_argument("--mode", choices=("enforce", "warn"), default="enforce",
                        help="enforce exits 1 on a problem; warn reports it and exits 0")
    mode = parser.parse_args(argv).mode

    files = markdown_files()
    skills = {os.path.dirname(f) for f in files if os.path.basename(f) == "SKILL.md"}
    skip = generated(files)
    checked = 0
    offenders: list[tuple[str, int, str]] = []
    for path in files:
        if path in skip or exempt(path, skills):
            continue
        try:
            with open(path, encoding="utf-8", newline="") as handle:
                text = handle.read().replace("\r\n", "\n")
        except (OSError, UnicodeDecodeError):
            continue
        if loader_fence(text):
            continue
        checked += 1
        offenders += [(path, line, message) for line, message in problems(path, text)]

    if not offenders:
        print(f"✅ Frontmatter: all {checked} document(s) carry the hidden frontmatter the standard defines.")
        return 0

    level = "error" if mode == "enforce" else "warning"
    for path, line, message in offenders:
        print(f"::{level} file={path},line={line},title=Frontmatter::{message}")
    broken = len({path for path, _, _ in offenders})
    print(f"\nFrontmatter: {len(offenders)} problem(s) in {broken} of {checked} document(s).")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            verdict = "Failed" if mode == "enforce" else "Found Problems"
            handle.write(f"### 🗂️ Frontmatter Check {verdict}\n\n")
            handle.write("| File | Line | Problem |\n| :--- | :--- | :--- |\n")
            for path, line, message in offenders:
                handle.write(f"| `{path}` | {line} | {message} |\n")
            handle.write(
                "\n**Fix it:** every document opens with a hidden block holding its `title`, "
                "`description` and `type`, and only the fields Document Styling & Formatting "
                "allows: https://github.com/tannergolden/standards/blob/Development/docs/"
                "technical/interface/Document-Styling-%26-Formatting.md\n"
            )
    return 1 if mode == "enforce" else 0


if __name__ == "__main__":
    sys.exit(main())
