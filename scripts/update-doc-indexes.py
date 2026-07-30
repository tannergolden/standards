#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Machined documentation indexes - generated, never hand-maintained.

Every list of documents in the docs tree (the Summary map's category
lists, the hub pages' "In This Category" tables) drifts the moment a
file is added or renamed. This tool ends that: index content lives
between marker comments and is REGENERATED from the filesystem plus
each document's own frontmatter, so an index can never disagree with
the tree.

Marker grammar (one block per list; params are space-separated):

  <!-- AUTO-INDEX:BEGIN dir=<path relative to docs/> style=<list|table|records>
       [recursive=1] [exclude=A.md,B.md]
       [fields=k1,k2 headers=Col0,Col1,Col2 sort=field:desc] -->
  ...generated content (do not edit by hand)...
  <!-- AUTO-INDEX:END -->

Rules per entry: the link label is the filename with hyphens as spaces
(the naming law already capitalizes every word and uses & for And); the
emoji is taken from the document's frontmatter title and emitted as
HTML hex entities (the spec's portability rule); the table description
is the document's frontmatter description. README.md, the seeded
Documentation.md, and the hosting file itself are always excluded;
entries sort case-insensitively by filename.

The `records` style builds a metadata TRACKING table (not a doc listing)
from each record file's own frontmatter: the first column is the
filename-derived link, and each `fields=` key becomes a column filled
from that key in the record's frontmatter (missing -> `-`). `headers=`
names the columns (one more than `fields=`, the first naming the link
column) and `sort=field:desc` orders the rows (ties broken by label).
This is how a record shelf (research reports, decision records) keeps its
index generated from the records themselves rather than hand-maintained -
an empty directory yields a single `_none yet_` row.

Modes: --write regenerates every block in place; --check (the
`make lint-docs` gate) fails when any block is stale, naming the file
and telling you to run `make docs-index`. Table rows are compared
whitespace-insensitively so Prettier's cell padding never false-flags.
Repositories created from the template receive this tool with the
engine and can adopt the same markers in their own docs.
"""

import argparse
import os
import re
import sys
import unicodedata

DOCS = "docs"
BEGIN = re.compile(r"<!--\s*AUTO-INDEX:BEGIN\s+(.*?)\s*-->")
END = "<!-- AUTO-INDEX:END -->"
ALWAYS_EXCLUDE = {"README.md", "Documentation.md"}


def entities(cluster: str) -> str:
    return "".join(f"&#x{ord(ch):X};" for ch in cluster)


def frontmatter(path: str):
    """Return (title, description) from a doc's YAML frontmatter."""
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read(2000)
    except (OSError, UnicodeDecodeError):
        return "", ""
    title = re.search(r"^title:\s*['\"]?(.*?)['\"]?\s*$", text, re.M)
    desc = re.search(r"^description:\s*['\"]?(.*?)['\"]?\s*$", text, re.M)
    return (title.group(1) if title else "", desc.group(1) if desc else "")


# The frontmatter BLOCK only, so a body line (e.g. a `verified:` inside a
# fenced example) can never spoof a record's field.
FRONT_BLOCK = re.compile(r"\A---\n(.*?)\n---", re.S)


def record_fields(path: str, keys):
    """Read named frontmatter fields from a record file. Missing -> ''.

    Used by the `records` table style so a shelf's index columns come from
    each record's own frontmatter (verified date, focus, decision, status),
    not from a hand-typed row."""
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except (OSError, UnicodeDecodeError):
        return {k: "" for k in keys}
    block = FRONT_BLOCK.match(text)
    body = block.group(1) if block else ""
    out = {}
    for key in keys:
        match = re.search(rf"^{re.escape(key)}:\s*['\"]?(.*?)['\"]?\s*$", body, re.M)
        out[key] = match.group(1).strip() if match else ""
    return out


def collect(dir_rel: str, recursive: bool, exclude: set, host: str, exclude_dirs: set = frozenset()):
    base = os.path.join(DOCS, dir_rel) if dir_rel else DOCS
    found = []
    for root, dirs, names in os.walk(base):
        if not recursive:
            dirs[:] = []
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for name in sorted(names, key=str.lower):
            if not name.endswith(".md"):
                continue
            if name in ALWAYS_EXCLUDE or name in exclude:
                continue
            path = os.path.join(root, name)
            if os.path.abspath(path) == os.path.abspath(host):
                continue
            found.append(path)
    return sorted(found, key=lambda p: os.path.basename(p).lower())


def render(params: str, host: str):
    opts = dict(p.split("=", 1) for p in params.split() if "=" in p)
    dir_rel = opts.get("dir", "")
    style = opts.get("style", "list")
    recursive = opts.get("recursive") == "1"
    exclude = {e for e in opts.get("exclude", "").split(",") if e}
    exclude_dirs = {e for e in opts.get("exclude_dirs", "").split(",") if e}
    host_dir = os.path.dirname(host)

    if style == "records":
        return render_records(
            opts, dir_rel, recursive, exclude, exclude_dirs, host, host_dir
        )

    rows = []
    for i, path in enumerate(
        collect(dir_rel, recursive, exclude, host, exclude_dirs), 1
    ):
        name = os.path.basename(path)
        label = name[:-3].replace("-", " ")
        title, desc = frontmatter(path)
        emoji = title.split(" ", 1)[0] if " " in title else ""
        prefix = f"{entities(emoji)} " if emoji else ""
        rel = os.path.relpath(path, host_dir).replace(os.sep, "/")
        if not rel.startswith("."):
            rel = f"./{rel}"
        rows.append((i, f"{prefix}{label}", rel, desc))

    if style == "table":
        # Emit the FULL table - header, delimiter, AND body - inside the
        # AUTO-INDEX markers so all three lines stay contiguous. A table
        # whose header is split from its body by a blank line or an HTML
        # comment (the markers themselves) is not recognized by CommonMark
        # and renders as literal-pipe text. Columns are left-aligned and
        # padded to the width Prettier settles on, so `make docs-index`
        # stays lint-clean without a follow-up formatter pass.
        header = ["Index", "Strategic Artifact", "Critical Intent"]
        body = [[f"**{i:02d}**", f"[{label}]({rel})", desc] for i, label, rel, desc in rows]
        return table_block(header, body)

    return [f"- [{label}]({rel})" for _, label, rel, _ in rows]


def render_records(opts, dir_rel, recursive, exclude, exclude_dirs, host, host_dir):
    """A metadata tracking table sourced from each record's frontmatter.

    Column 0 is the filename-derived link; every `fields=` key becomes a
    column read from that record's frontmatter. `headers=` (one more than
    fields) names the columns; `sort=field:desc` orders the rows. No
    records yields a single `_none yet_` row so the shelf reads clean when
    empty (a freshly generated repository, or one whose reports were all
    pruned)."""
    fields = [f for f in opts.get("fields", "").split(",") if f]
    headers = [h for h in opts.get("headers", "").split(",") if h]
    if len(headers) != len(fields) + 1:
        sys.exit(
            f"AUTO-INDEX records in {host}: headers ({len(headers)}) must be "
            f"exactly one more than fields ({len(fields)}) - the first header "
            "names the filename-link column."
        )
    sort_field, _, sort_order = opts.get("sort", "").partition(":")
    records = []
    for path in collect(dir_rel, recursive, exclude, host, exclude_dirs):
        name = os.path.basename(path)
        label = name[:-3].replace("-", " ")
        rel = os.path.relpath(path, host_dir).replace(os.sep, "/")
        if not rel.startswith("."):
            rel = f"./{rel}"
        records.append((label, rel, record_fields(path, fields)))
    if sort_field:
        records.sort(key=lambda r: r[0].lower())  # stable tiebreak by label
        records.sort(
            key=lambda r: r[2].get(sort_field, ""), reverse=(sort_order == "desc")
        )
    body = [
        [f"[{label}]({rel})"] + [vals.get(f) or "-" for f in fields]
        for label, rel, vals in records
    ]
    if not body:
        body = [["_none yet_"] + ["-"] * len(fields)]
    return table_block(headers, body)


def display_width(text: str) -> int:
    """Column width the way Prettier's `string-width` sizes table cells:
    combining marks are zero-width, East-Asian wide/fullwidth glyphs are
    two. Our cells are ASCII (emoji ship as `&#x…;` entities), so this is
    len() in practice, but it stays correct if a wide character ever lands
    in a description."""
    width = 0
    for ch in text:
        if unicodedata.combining(ch):
            continue
        width += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return width


def table_block(header, body):
    """Render a GFM table (header, delimiter, rows) with the left-aligned,
    width-padded columns Prettier produces, so the emitted block is already
    formatter-stable."""
    cols = len(header)
    widths = [max(3, display_width(header[c])) for c in range(cols)]
    for row in body:
        for c in range(cols):
            widths[c] = max(widths[c], display_width(row[c]))

    def fmt(cells):
        padded = [cell + " " * (widths[c] - display_width(cell)) for c, cell in enumerate(cells)]
        return "| " + " | ".join(padded) + " |"

    delimiter = "| " + " | ".join(":" + "-" * (widths[c] - 1) for c in range(cols)) + " |"
    return [fmt(header), delimiter] + [fmt(row) for row in body]


def normalized(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def process(path: str, write: bool):
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    out, stale, i = [], False, 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = BEGIN.search(line)
        if not m:
            i += 1
            continue
        try:
            end = next(
                j for j in range(i + 1, len(lines)) if END in lines[j]
            )
        except StopIteration:
            sys.exit(f"{path}: AUTO-INDEX block opened but never closed")
        current = [line for line in lines[i + 1 : end] if line.strip()]
        fresh = render(m.group(1), path)
        if [normalized(line) for line in current] != [normalized(line) for line in fresh]:
            stale = True
        # Prettier-stable emission: pad the generated block with one blank
        # line on each side - the exact form Prettier's Markdown formatter
        # settles on - so `make docs-index` (and any automation that runs
        # --write, like Day-0 init and the sync workflow) leaves `make lint`
        # green without a separate formatter pass. --check compares
        # whitespace-insensitively, so both padded and unpadded blocks pass.
        if fresh:
            out.append("")
            out.extend(fresh)
            out.append("")
        out.append(lines[end])
        i = end + 1
    if stale and write:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(out))
    return stale


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="fail when any index is stale")
    mode.add_argument("--write", action="store_true", help="regenerate every index in place")
    args = ap.parse_args()

    # ⚠️ A MISSING DOCS FOLDER IS AN ERROR, NOT AN EMPTY RESULT. `os.walk`
    # on a path that does not exist yields nothing and raises nothing, so
    # `hosts` came back empty and --check printed its success line having
    # inspected zero files. Run from the wrong directory, or in a repository
    # that adopted this generator without a docs/ folder, the gate the
    # styling spec lists as enforcement said everything was fine.
    #
    # Present-but-empty is left alone: a repository can legitimately have
    # the folder and no markdown in it yet. Only ABSENT is unanswerable.
    if not os.path.isdir(DOCS):
        print(f"::error::'{DOCS}/' does not exist, so no index could be checked.")
        print(f"         Run this from the repository root, or create {DOCS}/.")
        return 1

    hosts = []
    for root, _dirs, names in os.walk(DOCS):
        for name in sorted(names):
            if name.endswith(".md"):
                hosts.append(os.path.join(root, name))

    stale_files = [h for h in hosts if process(h, args.write)]
    if args.write:
        print(f"✅ Doc indexes regenerated - {len(stale_files)} file(s) updated.")
        return 0
    if stale_files:
        for path in stale_files:
            print(f"❌ {path}: machined index is stale - run `make docs-index`.")
        return 1
    print("✅ Doc indexes check passed - every machined index matches the tree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
