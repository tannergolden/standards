#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
# =============================================================================
# Sync Labels - declarative label delivery via the GitHub API
# =============================================================================
# Applies the shared label taxonomy (LABELS_FILE) to a repository:
# create-or-update for every declared label, never pruning extras - so labels
# a repository adds for itself survive.
#
# READS BEFORE IT WRITES. The repository's current labels are fetched once,
# and a label already matching its declaration is left alone. A no-op sync
# therefore issues zero writes and reports "N unchanged", which makes the
# summary worth reading: anything other than unchanged is a real difference
# between the registry and the repository. The previous version rewrote all
# sixty-one on every run, so the output looked identical whether the taxonomy
# had changed or not.
#
# Renames are first-class: a label carrying `renamed_from: 'old name'` is
# MOVED onto its new identity via PATCH (issue and PR attachments travel with
# it) when the old name exists and the new one does not. The rename is
# one-shot and idempotent - once it has happened, the entry degrades to an
# ordinary create-or-update.
#
# Every declaration is validated before the first write, so a bad entry fails
# the run with the offending names rather than half-applying the taxonomy and
# reporting a 422 from somewhere in the middle.
#
# Requires: GH_TOKEN with issues write scope, GITHUB_REPOSITORY, LABELS_FILE.
# Optional: DRY_RUN=true prints the plan and writes nothing.
# =============================================================================
set -euo pipefail

: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${LABELS_FILE:?LABELS_FILE is required}"
DRY_RUN="${DRY_RUN:-false}"
export DRY_RUN

python3 - <<'PY'
import json
import os
import re
import subprocess
import sys
from urllib.parse import quote

PATH = os.environ["LABELS_FILE"]
REPO = os.environ["GITHUB_REPOSITORY"]
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"

# GitHub's documented ceilings. Both are enforced here rather than discovered
# as a 422 partway through a sync that has already written half the taxonomy.
MAX_NAME = 50
MAX_DESC = 100


# --- 1. Read the registry -------------------------------------------------
# PyYAML when the runner has it, which handles comments, quoting styles and
# multi-line scalars properly. The line parser is the fallback so the script
# keeps working on a bare runner, and it is deliberately strict: it would
# rather refuse a line it does not understand than guess at it.
def load(path):
    try:
        import yaml
    except ImportError:
        pass
    else:
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh), "PyYAML"

    field = re.compile(r"^(?:-\s+)?(name|color|description|renamed_from):\s*'(.*)'\s*$")
    labels, current = [], {}
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            m = field.match(line)
            if not m:
                sys.exit(f"unparseable line in {path}: {raw!r}\n"
                         "  the fallback parser needs single-quoted scalars, one per line")
            key, value = m.group(1), m.group(2).replace("''", "'")
            if key == "name":
                current = {"name": value}
                labels.append(current)
            else:
                current[key] = value
    return labels, "line parser"


labels, parser = load(PATH)
if not isinstance(labels, list) or not labels:
    sys.exit(f"{PATH}: expected a non-empty list of labels")


# --- 2. Validate the whole registry before writing anything ---------------
problems = []
seen = {}
for i, label in enumerate(labels):
    if not isinstance(label, dict) or not label.get("name"):
        problems.append(f"entry {i}: no name")
        continue
    name = label["name"]
    lowered = name.lower()
    if lowered in seen:
        # GitHub treats label names case-insensitively for uniqueness, so two
        # entries differing only in case collide on the second write.
        problems.append(f"{name!r}: duplicate of {seen[lowered]!r}")
    seen[lowered] = name
    if len(name) > MAX_NAME:
        problems.append(f"{name!r}: name is {len(name)} chars, over GitHub's {MAX_NAME}")
    color = str(label.get("color", ""))
    if not re.fullmatch(r"[0-9a-fA-F]{6}", color):
        problems.append(f"{name!r}: color {color!r} is not six hex digits")
    desc = label.get("description")
    if desc is None:
        problems.append(f"{name!r}: no description")
    elif len(desc) > MAX_DESC:
        problems.append(f"{name!r}: description is {len(desc)} chars, over GitHub's {MAX_DESC}")
    if label.get("renamed_from") == name:
        problems.append(f"{name!r}: renamed_from names the label itself")

if problems:
    print(f"::error title=Label taxonomy::{PATH} is invalid; nothing was written")
    for p in problems:
        print(f"  {p}")
    sys.exit(1)


# --- 3. Read the repository's current labels ------------------------------
def gh(method, path, payload=None):
    args = ["gh", "api", "-X", method, path]
    kwargs = {"capture_output": True, "text": True}
    if payload is not None:
        args += ["--input", "-"]
        kwargs["input"] = json.dumps(payload)
    return subprocess.run(args, **kwargs)


existing = {}
r = subprocess.run(
    ["gh", "api", "--paginate", f"/repos/{REPO}/labels", "--jq", ".[] | @json"],
    capture_output=True, text=True,
)
if r.returncode != 0:
    sys.exit(f"could not read existing labels: {r.stderr.strip()[:300]}")
for line in r.stdout.splitlines():
    if line.strip():
        cur = json.loads(line)
        existing[cur["name"].lower()] = cur


# --- 4. Decide what actually needs to happen ------------------------------
def path_for(name):
    # safe='' matters: a label such as 'area: ui/ux' would otherwise keep its
    # slash and address a different, non-existent endpoint. That made every
    # re-sync of a slashed label fail, create-then-404, forever.
    return f"/repos/{REPO}/labels/{quote(name, safe='')}"


plan = []
for label in labels:
    name, color, desc = label["name"], label["color"].lower(), label["description"]
    old = label.get("renamed_from")
    cur = existing.get(name.lower())

    if old and old.lower() in existing and cur is None:
        plan.append(("rename", label, old))
    elif cur is None:
        plan.append(("create", label, None))
    elif (cur.get("color", "").lower() != color
          or (cur.get("description") or "") != desc):
        plan.append(("update", label, None))
    else:
        plan.append(("unchanged", label, None))

counts = {k: 0 for k in ("create", "update", "rename", "unchanged")}
for action, label, old in plan:
    counts[action] += 1
    if action == "unchanged":
        continue
    detail = f" (from {old!r})" if old else ""
    print(f"  {action.upper():9} {label['name']}{detail}")

print(f"\n{len(labels)} declared via {parser}: "
      f"{counts['create']} to create, {counts['update']} to update, "
      f"{counts['rename']} to rename, {counts['unchanged']} already correct")

if DRY_RUN:
    print("\nDry run: nothing was written. Set DRY_RUN=false to apply this plan.")
    sys.exit(0)

if not (counts["create"] or counts["update"] or counts["rename"]):
    print("\nNothing to do.")
    sys.exit(0)


# --- 5. Apply -------------------------------------------------------------
created = updated = renamed = failed = 0
for action, label, old in plan:
    if action == "unchanged":
        continue
    body = {
        "name": label["name"],
        "color": label["color"].lower(),
        "description": label["description"],
    }

    if action == "rename":
        payload = {"new_name": label["name"],
                   "color": body["color"], "description": body["description"]}
        r = gh("PATCH", path_for(old), payload)
        if r.returncode == 0:
            renamed += 1
            continue
        # The rename lost a race, or the old label went away between the read
        # and the write. Fall through and converge the ordinary way.
        print(f"::warning::rename of {old!r} to {label['name']!r} did not apply; "
              "falling back to create-or-update")
        action = "create"

    create_err = None
    if action == "create":
        r = gh("POST", f"/repos/{REPO}/labels", body)
        if r.returncode == 0:
            created += 1
            continue
        create_err = r.stderr.strip()[:200]

    r = gh("PATCH", path_for(label["name"]), body)
    if r.returncode == 0:
        updated += 1
    else:
        failed += 1
        # Report BOTH failures when a create was attempted: if the label never
        # existed, the update's 404 is noise and the create's 422 is the cause.
        extra = f"create: {create_err}; " if create_err else ""
        print(f"::warning::could not sync label {label['name']!r}: "
              f"{extra}update: {r.stderr.strip()[:200]}")

print(f"\nlabels: {created} created, {updated} updated, {renamed} renamed, "
      f"{counts['unchanged']} unchanged, {failed} failed, {len(labels)} declared")
sys.exit(1 if failed else 0)
PY
