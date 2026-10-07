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

  <!-- AUTO-INDEX:BEGIN dir=<path> style=<list|table|records|log>
       [recursive=1] [exclude=A.md,B.md,*.svg]
       [fields=k1,k2 headers=Col0,Col1,Col2 sort=field:desc] -->
  ...generated content (do not edit by hand)...
  <!-- AUTO-INDEX:END -->

`dir=` is a path under docs/ (`dir=distribution`), or, when it is `.` or
starts with `./` or `../`, a path relative to the folder of the file the
block sits in (`dir=.` is that folder itself). The relative form is what
lets the same block work wherever its file is copied, and in a repository
with no docs/ folder at all. `exclude=` takes file names or glob patterns.

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
an empty directory yields a single `_none yet_` row. Frontmatter is read
from either form: the hidden `<!-- -->` comment or a `---` fence.

The `log` style is a FOLDER LOG: one row for every file and folder directly
inside `dir`, folders first, ignored files left out the way git leaves them
out, and the hosting file listed as "This file.". Each row's description is
what the entry says about itself:

  - a folder: its README.md's frontmatter description
  - Markdown: the frontmatter description, else the opening comment's first
    sentence
  - Python: the first sentence of the module docstring
  - YAML: a top-level `description:`, else a GitHub form's opening markdown,
    else the leading comment
  - JSON: the leading `//` comment, else a top-level `"//"` key
  - anything else that opens with a `#` or `//` comment: that comment
  - a plain-text file named in capitals (LICENSE): its first line

In a leading comment, separator lines, bare URLs and the file's own name are
skipped, as is the "Installed from" banner every standards stub carries; a
paragraph labelled `Purpose:` wins over the ones before it. An entry that
cannot describe itself (an image, a folder with no README) keeps the
description already in its row, so it is written once, by hand, and survives
every regeneration; until then it reads `-`. `fields=name,on` adds a column
for each: `name` is a YAML `name:` or a Markdown title, `on` is a workflow's
triggers. Non-ASCII text is emitted as HTML hex entities, so every cell is
the width the formatter measures.

Modes: --write regenerates every block in place; --check (the
`make lint-docs` gate) fails when any block is stale, naming the file
and telling you to run `make docs-index`. Table rows are compared
whitespace-insensitively so Prettier's cell padding never false-flags.
--tree widens the search from docs/ to every Markdown file in the
repository, which is how a repository generated from a template keeps
its folder logs current: the 🗂️ Machined Indexes workflow published
beside this script runs `--tree --write` after every push and proposes
whatever changed as a pull request.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import os
import re
import subprocess
import sys
import unicodedata

DOCS = "docs"
BEGIN = re.compile(r"<!--\s*AUTO-INDEX:BEGIN\s+(.*?)\s*-->")
END = "<!-- AUTO-INDEX:END -->"
FENCE = re.compile(r"^(?:```|~~~)")
ALWAYS_EXCLUDE = {"README.md", "Documentation.md"}

# How many AUTO-INDEX blocks this run has met. A `--tree` run that met none
# inspected nothing, and must not report that as a pass.
BLOCKS_SEEN = 0


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
# fenced example) can never spoof a record's field. Both forms the styling
# spec has used: the hidden comment it requires today, and the `---` fence.
FRONT_BLOCK = re.compile(r"\A(?:---|<!--)\n(.*?)\n(?:---|-->)", re.S)


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


def resolve_dir(dir_rel: str, host: str) -> str:
    """Where a block's `dir=` points. Relative to the host for `.`, `./`, `../`."""
    if dir_rel == "." or dir_rel.startswith(("./", "../")):
        return os.path.normpath(os.path.join(os.path.dirname(host) or ".", dir_rel))
    return os.path.join(DOCS, dir_rel) if dir_rel else DOCS


def excluded(name: str, patterns) -> bool:
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)


def collect(base: str, recursive: bool, exclude: set, host: str, exclude_dirs: set = frozenset()):
    found = []
    for root, dirs, names in os.walk(base):
        if not recursive:
            dirs[:] = []
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for name in sorted(names, key=str.lower):
            if not name.endswith(".md"):
                continue
            if name in ALWAYS_EXCLUDE or excluded(name, exclude):
                continue
            path = os.path.join(root, name)
            if os.path.abspath(path) == os.path.abspath(host):
                continue
            found.append(path)
    return sorted(found, key=lambda p: os.path.basename(p).lower())


def render(params: str, host: str, current=()):
    opts = dict(p.split("=", 1) for p in params.split() if "=" in p)
    style = opts.get("style", "list")
    base = resolve_dir(opts.get("dir", ""), host)
    recursive = opts.get("recursive") == "1"
    exclude = {e for e in opts.get("exclude", "").split(",") if e}
    exclude_dirs = {e for e in opts.get("exclude_dirs", "").split(",") if e}
    host_dir = os.path.dirname(host)

    if style == "records":
        return render_records(opts, base, recursive, exclude, exclude_dirs, host, host_dir)
    if style == "log":
        return render_log(opts, base, exclude, host, current)

    rows = []
    for i, path in enumerate(collect(base, recursive, exclude, host, exclude_dirs), 1):
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


def render_records(opts, base, recursive, exclude, exclude_dirs, host, host_dir):
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
    for path in collect(base, recursive, exclude, host, exclude_dirs):
        name = os.path.basename(path)
        label = name[:-3].replace("-", " ")
        rel = os.path.relpath(path, host_dir).replace(os.sep, "/")
        if not rel.startswith("."):
            rel = f"./{rel}"
        records.append((label, rel, record_fields(path, fields)))
    if sort_field:
        records.sort(key=lambda r: r[0].lower())  # stable tiebreak by label
        records.sort(key=lambda r: r[2].get(sort_field, ""), reverse=(sort_order == "desc"))
    body = [
        [f"[{label}]({rel})"] + [vals.get(f) or "-" for f in fields]
        for label, rel, vals in records
    ]
    if not body:
        body = [["_none yet_"] + ["-"] * len(fields)]
    return table_block(headers, body)


# --- Folder logs ------------------------------------------------------------

# Directories never listed, whether or not git is there to say so.
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}

# The header each `fields=` key gets, between the entry and its purpose.
FIELD_HEADERS = {"name": "Name", "on": "Triggers"}

# A line that only draws a rule (`# =====`, `# --- Reusable Workflow ---`).
RULE = re.compile(r"^(?:[=\-#*_~+]{3,}|-{2,3}\s.*\s-{2,3})$")
URL_ONLY = re.compile(r"^(?:https?://|www\.)\S+$")
SENTENCE = re.compile(r"(.+?[.!?])(?=\s|$)")
TABLE_DELIMITER = re.compile(r"\|(?:\s*:?-+:?\s*\|)+")


def repository_files():
    """Every file git would commit here, as POSIX paths from the current folder.

    Tracked or untracked, never ignored, and still on disk. A file `.gitignore`
    keeps out of the repository is kept out of its folder's log for the same
    reason. Outside a git checkout the folders that are never content are
    skipped instead.
    """
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            capture_output=True,
            check=True,
        ).stdout.decode("utf-8", "surrogateescape")
        names = [n for n in out.split("\0") if n]
    except (OSError, subprocess.CalledProcessError):
        names = []
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for name in files:
                names.append(os.path.relpath(os.path.join(root, name)).replace(os.sep, "/"))
    return sorted({n for n in names if os.path.isfile(n)})


def children(base: str):
    """The folders and files directly inside `base`, as two sorted lists."""
    prefix = "" if os.path.normpath(base) == "." else os.path.normpath(base).replace(os.sep, "/") + "/"
    folders, files = set(), set()
    for path in repository_files():
        if not path.startswith(prefix):
            continue
        rest = path[len(prefix) :]
        if "/" in rest:
            folders.add(rest.split("/", 1)[0])
        else:
            files.add(rest)
    return sorted(folders, key=str.lower), sorted(files, key=str.lower)


def read_text(path: str) -> str:
    """The file's text, or '' for anything binary or unreadable."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read(262144)
    except OSError:
        return ""
    if b"\0" in raw[:8192]:
        return ""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return ""


def first_sentence(text: str) -> str:
    """The opening sentence, taking the next one too when the first is a fragment."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    sentences = SENTENCE.findall(text)
    if not sentences:
        return text
    first = sentences[0]
    if len(first) < 40 and len(sentences) > 1 and sentences[1].endswith("."):
        first = f"{first} {sentences[1].strip()}"
    return first.strip()


def capitalized(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text


def yaml_scalar(value: str) -> str:
    """A one-line YAML scalar, unquoted the way YAML unquotes it."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return value[1:-1].replace('\\"', '"')
    return re.sub(r"\s+#.*$", "", value)


def front_value(text: str, key: str) -> str:
    """A one-line key from a Markdown file's frontmatter block, either form."""
    block = FRONT_BLOCK.match(text)
    if not block:
        return ""
    match = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", block.group(1), re.M)
    return yaml_scalar(match.group(1)) if match else ""


def top_level(text: str, key: str) -> str:
    """A one-line top-level key from a YAML document."""
    match = re.search(rf"^{re.escape(key)}:[ \t]*(\S.*?)\s*$", text, re.M)
    if not match or match.group(1)[0] in "|>":
        return ""
    return yaml_scalar(match.group(1))


def leading_comment(text: str, marker: str, name: str) -> str:
    """The description a file's opening comment gives, or ''."""
    paragraphs, current = [], []
    for raw in text.splitlines():
        line = raw.strip()
        if not paragraphs and not current and (not line or line.startswith("#!") or line in ("{", "[")):
            continue
        if not line.startswith(marker):
            break
        body = line[len(marker) :].strip()
        if not body or RULE.match(body):
            if current:
                paragraphs.append(current)
                current = []
            continue
        names_itself = body == name or body.endswith("/" + name)
        if URL_ONLY.match(body) or names_itself or body.startswith("SPDX-"):
            continue
        current.append(body)
    if current:
        paragraphs.append(current)
    texts = [" ".join(p) for p in paragraphs]
    texts = [t for t in texts if not t.startswith("Installed from ")]
    purpose = next((t for t in texts if t.startswith("Purpose:")), "")
    chosen = purpose or (texts[0] if texts else "")
    return capitalized(first_sentence(re.sub(r"^Purpose:\s*", "", chosen)))


def indent_of(line: str) -> int:
    return len(line) - len(line.lstrip())


def form_markdown(text: str) -> str:
    """The opening prose of a GitHub form's first markdown field, or ''.

    A discussion form has no `description:` of its own; what it says about
    itself is the markdown shown above its fields, under a heading.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not re.match(r"^\s*-\s*type:\s*['\"]?markdown['\"]?\s*$", line):
            continue
        for j in range(i + 1, len(lines)):
            if lines[j].strip() and indent_of(lines[j]) <= indent_of(line):
                break
            value = re.match(r"^(\s*)value:\s*[|>][-+]?\s*$", lines[j])
            if not value:
                continue
            # A heading ends a paragraph as surely as a blank line does: the
            # forms put their prose directly beneath one.
            paragraph = []
            for k in range(j + 1, len(lines)):
                text_line = lines[k].strip()
                if text_line and indent_of(lines[k]) <= len(value.group(1)):
                    break
                if not text_line or text_line.startswith("#"):
                    if paragraph:
                        break
                    continue
                paragraph.append(text_line)
            return capitalized(first_sentence(" ".join(paragraph)))
        return ""
    return ""


def describe(path: str) -> str:
    """What a file or folder says about itself, in one sentence, or ''."""
    if os.path.isdir(path):
        readme = os.path.join(path, "README.md")
        return describe(readme) if os.path.isfile(readme) else ""
    text = read_text(path)
    if not text:
        return ""
    name = os.path.basename(path)
    suffix = os.path.splitext(name)[1].lower() if not name.startswith(".") or name.count(".") > 1 else ""

    if suffix in (".md", ".markdown"):
        description = front_value(text, "description")
        if description:
            return description
        comment = re.match(r"\A<!--\s*(.*?)-->", text, re.S)
        if comment and not re.match(r"^[A-Za-z_-]+:\s", comment.group(1)):
            return capitalized(first_sentence(comment.group(1)))
        return ""
    if suffix == ".py":
        try:
            docstring = ast.get_docstring(ast.parse(text))
        except SyntaxError:
            docstring = None
        if docstring:
            return capitalized(first_sentence(docstring.strip().split("\n\n", 1)[0]))
        return leading_comment(text, "#", name)
    if suffix in (".yml", ".yaml"):
        return top_level(text, "description") or form_markdown(text) or leading_comment(text, "#", name)
    if suffix in (".json", ".jsonc", ".json5"):
        comment = leading_comment(text, "//", name)
        if comment:
            return comment
        key = re.search(r'^\s*"//"\s*:\s*"((?:[^"\\]|\\.)*)"', text, re.M)
        return capitalized(first_sentence(key.group(1))) if key else ""

    opening = text.lstrip()
    if opening.startswith("#"):
        return leading_comment(text, "#", name)
    if opening.startswith("//"):
        return leading_comment(text, "//", name)
    if not suffix and not name.startswith(".") and name.upper() == name:
        return capitalized(first_sentence(opening.split("\n\n", 1)[0].split("\n", 1)[0]))
    return ""


def list_values(lines, key: str):
    """`key: [a, b]` or a `- item` list beneath `key:`, from an indented block."""
    for i, line in enumerate(lines):
        match = re.match(rf"^(\s*){re.escape(key)}:\s*(.*?)\s*$", line)
        if not match:
            continue
        inline = match.group(2)
        if inline.startswith("["):
            return [v.strip().strip("'\"") for v in inline.strip("[]").split(",") if v.strip()]
        if inline:
            return [inline.strip("'\"")]
        indent = len(match.group(1))
        values = []
        for item in lines[i + 1 :]:
            if len(item) - len(item.lstrip()) <= indent and item.strip():
                break
            bullet = re.match(r"^\s*-\s*(.+?)\s*$", item)
            if bullet:
                values.append(bullet.group(1).strip("'\""))
        return values
    return []


def workflow_triggers(text: str) -> str:
    """A workflow's `on:` events, in file order, with their branch, path or cron filters."""
    lines = text.splitlines()
    start = next(
        (i for i, ln in enumerate(lines) if re.match(r"^(?:on|'on'|\"on\"):(?:\s|$)", ln)), None
    )
    if start is None:
        return ""
    inline = re.sub(r"\s+#.*$", "", lines[start].split(":", 1)[1]).strip()
    if inline:
        events = [e.strip().strip("'\"") for e in inline.strip("[]").split(",") if e.strip()]
        return ", ".join(f"`{e}`" for e in events)
    block = []
    for line in lines[start + 1 :]:
        if line.strip() and not line.startswith((" ", "\t")):
            break
        if line.strip() and not line.strip().startswith("#"):
            block.append(line)
    if not block:
        return ""
    indent = min(len(ln) - len(ln.lstrip()) for ln in block)
    events = []
    for line in block:
        key = re.match(r"^\s*([A-Za-z_]+):", line)
        if len(line) - len(line.lstrip()) == indent and key:
            events.append((key.group(1), []))
        elif events:
            events[-1][1].append(line)
    parts = []
    for event, body in events:
        if event == "schedule":
            detail = re.findall(r"cron:\s*['\"]([^'\"]+)['\"]", "\n".join(body))
        else:
            detail = list_values(body, "branches") or list_values(body, "paths")
        listed = ", ".join(f"`{d}`" for d in detail)
        parts.append(f"`{event}` ({listed})" if listed else f"`{event}`")
    return ", ".join(parts)


def field(path: str, key: str) -> str:
    """A `fields=` column for one entry: `name` or `on`."""
    if os.path.isdir(path):
        return ""
    text = read_text(path)
    suffix = os.path.splitext(path)[1].lower()
    if key == "name":
        if suffix in (".md", ".markdown"):
            return front_value(text, "title")
        return top_level(text, "name") if suffix in (".yml", ".yaml") else ""
    if key == "on" and suffix in (".yml", ".yaml"):
        return workflow_triggers(text)
    return ""


def cell(text: str) -> str:
    """Text made safe for one table cell: one line, no bare pipe, ASCII only."""
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"(?<!\\)\|", r"\\|", text)
    return "".join(ch if ord(ch) < 128 else f"&#x{ord(ch):X};" for ch in text)


def link_target(target: str) -> str:
    return f"<{target}>" if re.search(r"[\s()<>]", target) else target


def carried(current) -> dict:
    """The description already in each row of a block, keyed by its entry."""
    found = {}
    for line in current:
        row = line.strip()
        if not row.startswith("|") or TABLE_DELIMITER.fullmatch(row):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", row)[1:-1]]
        entry = re.search(r"`([^`]+)`", cells[0]) if cells else None
        if entry and len(cells) >= 2 and cells[-1] not in ("", "-"):
            found[entry.group(1)] = cells[-1]
    return found


def render_log(opts, base, exclude, host, current):
    """One row per entry directly inside `base`: folders first, then files."""
    fields = [f for f in opts.get("fields", "").split(",") if f]
    unknown = [f for f in fields if f not in FIELD_HEADERS]
    if unknown:
        sys.exit(f"AUTO-INDEX log in {host}: unknown field(s) {unknown} - known: {sorted(FIELD_HEADERS)}")
    headers = [h for h in opts.get("headers", "").split(",") if h] or (
        ["Entry"] + [FIELD_HEADERS[f] for f in fields] + ["Purpose"]
    )
    if len(headers) != len(fields) + 2:
        sys.exit(
            f"AUTO-INDEX log in {host}: headers ({len(headers)}) must be exactly two more "
            f"than fields ({len(fields)}) - one for the entry, one for its purpose."
        )
    if not os.path.isdir(base):
        sys.exit(f"AUTO-INDEX log in {host}: dir '{base}' does not exist.")
    kept = carried(current)
    host_dir = os.path.dirname(host) or "."
    folders, files = children(base)
    body = []
    for name, is_folder in [(f, True) for f in folders] + [(f, False) for f in files]:
        path = os.path.join(base, name)
        if excluded(name, exclude):
            continue
        if not is_folder and os.path.abspath(path) == os.path.abspath(host):
            # The file the reader is looking at. Listed, so the log really is
            # every file here, but described by what it is to that reader.
            rel = os.path.relpath(path, host_dir).replace(os.sep, "/")
            body.append([f"[`{name}`]({link_target(rel)})"] + ["-"] * len(fields) + ["This file."])
            continue
        shown = f"{name}/" if is_folder else name
        target = os.path.join(path, "README.md") if is_folder and os.path.isfile(os.path.join(path, "README.md")) else path
        rel = os.path.relpath(target, host_dir).replace(os.sep, "/")
        if is_folder and not rel.endswith("README.md"):
            rel += "/"
        description = describe(path) or kept.get(shown, "") or "-"
        values = [cell(field(path, f)) or "-" for f in fields]
        body.append([f"[`{shown}`]({link_target(rel)})", *values, cell(description)])
    if not body:
        body = [["_none yet_"] + ["-"] * (len(fields) + 1)]
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
    """A line as compared: whitespace collapsed, and a table delimiter's dash
    count ignored. Both are padding that follows the widest cell, so a hand-
    written description in a folder log would otherwise read as drift until
    something re-padded it. A delimiter's colons are alignment, which is
    meaning, and stay in the comparison."""
    line = re.sub(r"\s+", " ", line).strip()
    if TABLE_DELIMITER.fullmatch(line.replace(" ", "")):
        return re.sub(r"-+", "-", line.replace(" ", ""))
    return line


def process(path: str, write: bool):
    global BLOCKS_SEEN
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    out, stale, i = [], False, 0
    # ⚠️ A MARKER INSIDE A FENCED BLOCK IS AN EXAMPLE, NOT AN INSTRUCTION.
    # The styling spec documents this very format by showing it, and without
    # tracking fences that example is parsed as a live marker: `--write`
    # deletes whatever sits between the two lines and `--check` calls the
    # spec permanently stale. It is harmless only while the example happens
    # to be empty, which is not a property anyone maintains on purpose.
    fenced = False
    while i < len(lines):
        line = lines[i]
        out.append(line)
        if FENCE.match(line.strip()):
            fenced = not fenced
            i += 1
            continue
        m = None if fenced else BEGIN.search(line)
        if not m:
            i += 1
            continue
        try:
            end = next(j for j in range(i + 1, len(lines)) if END in lines[j])
        except StopIteration:
            sys.exit(f"{path}: AUTO-INDEX block opened but never closed")
        BLOCKS_SEEN += 1
        current = [line for line in lines[i + 1 : end] if line.strip()]
        fresh = render(m.group(1), path, current)
        if [normalized(line) for line in current] != [normalized(line) for line in fresh]:
            stale = True
        # Prettier-stable emission: pad the generated block with one blank
        # line on each side - the exact form Prettier's Markdown formatter
        # settles on - so `make docs-index` (and any automation that runs
        # --write, like the 🗂️ Machined Indexes workflow) leaves `make lint`
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
    ap.add_argument(
        "--tree",
        action="store_true",
        help="search every Markdown file in the repository, not only docs/",
    )
    args = ap.parse_args()

    if args.tree:
        hosts = [p for p in repository_files() if p.endswith(".md")]
    else:
        # ⚠️ A MISSING DOCS FOLDER IS AN ERROR, NOT AN EMPTY RESULT. `os.walk`
        # on a path that does not exist yields nothing and raises nothing, so
        # `hosts` came back empty and --check printed its success line having
        # inspected zero files. Run from the wrong directory, or in a
        # repository that adopted this generator without a docs/ folder, the
        # gate the styling spec lists as enforcement said everything was fine.
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

    # The same rule as a missing docs/ folder, for the whole-repository
    # search: a run that met no block at all checked nothing, so it says so
    # rather than printing a pass over an empty set.
    if args.tree and BLOCKS_SEEN == 0:
        print("::error::No AUTO-INDEX block in any Markdown file here, so nothing was indexed.")
        print("         Add a block, or remove the workflow that runs this.")
        return 1

    regenerate = "make docs-index" if not args.tree else "update-doc-indexes.py --tree --write"
    if args.write:
        for path in stale_files:
            print(f"📝 {path}")
        print(f"✅ Doc indexes regenerated - {len(stale_files)} file(s) updated.")
        return 0
    if stale_files:
        for path in stale_files:
            print(f"❌ {path}: machined index is stale - run `{regenerate}`.")
        return 1
    print(f"✅ Doc indexes check passed - every machined index matches the tree ({BLOCKS_SEEN} block(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
