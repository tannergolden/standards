#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Prune stale and superseded GitHub deployments.

Keeps only the most recent SUCCESSFUL ("passing") deployment per
environment and deletes every older or non-passing one (superseded
successes, failures, errors, inactivated). Deployments that are still
in-flight (in_progress / queued / pending) are never touched, so a running
deploy is safe. Idempotent and 404-tolerant: re-runs and paginated-list
overlaps do not error.

A deployment must be inactive before the API will delete it, so each
target is set inactive and then deleted. The kept deployment stays active,
so every environment still shows exactly its current passing deployment.

Environment scoping (a documentation site and an application environment
are different in kind, so each can be pruned without the other):
  ONLY_ENVIRONMENTS      comma-separated allowlist - prune only these
  EXCLUDE_ENVIRONMENTS   comma-separated denylist - prune all but these
With neither set, every environment is pruned.

Required env:
  GITHUB_REPOSITORY   owner/repo (set automatically inside Actions)
  GITHUB_TOKEN        token with `deployments: write`
Optional env:
  GITHUB_API_URL      API base (default https://api.github.com)
  DRY_RUN             "1"/"true"/"yes" to log the plan without deleting

Run locally:
  GITHUB_REPOSITORY=owner/repo GITHUB_TOKEN=$(gh auth token) \
    DRY_RUN=1 python3 scripts/prune-deployments.py
"""

import json
import os
import sys
import urllib.error
import urllib.request

API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
REPO = os.environ.get("GITHUB_REPOSITORY", "")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
DRY_RUN = os.environ.get("DRY_RUN", "").strip().lower() in ("1", "true", "yes")

# Latest-status states that mean the deployment is STILL RUNNING - a prune
# must never disturb one of these.
IN_FLIGHT = frozenset({"in_progress", "queued", "pending"})
PASSING = "success"


def _csv(name):
    return {item.strip() for item in os.environ.get(name, "").split(",") if item.strip()}


ONLY = _csv("ONLY_ENVIRONMENTS")
EXCLUDE = _csv("EXCLUDE_ENVIRONMENTS")


def in_scope(env, only=None, exclude=None):
    only = ONLY if only is None else only
    exclude = EXCLUDE if exclude is None else exclude
    if only:
        return env in only
    if exclude:
        return env not in exclude
    return True


def plan(deployments, only=None, exclude=None):
    """Pure decision function (no I/O), so it is unit-testable.

    `deployments` must be sorted newest-first and each dict must carry a
    `_state` key (its latest deployment-status state). Returns three lists:
    (keep, delete, skip)."""
    keep, delete, skip = [], [], []
    kept_envs = set()
    for dep in deployments:
        env = dep.get("environment") or ""
        if not in_scope(env, only, exclude):
            continue
        state = dep.get("_state")
        if state in IN_FLIGHT or state is None:
            skip.append(dep)
        elif state == PASSING and env not in kept_envs:
            kept_envs.add(env)
            keep.append(dep)
        else:
            delete.append(dep)
    return keep, delete, skip


# The URL is always the GitHub API base plus a literal path, never user
# input, so no file: or custom scheme can reach urlopen. Annotated per
# call site rather than ignored repository-wide, so a future urlopen on
# an untrusted URL is still flagged.
def request(method, path, data=None):
    req = urllib.request.Request(API + path, method=method)  # noqa: S310
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    if data is not None:
        req.data = json.dumps(data).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        raw = resp.read()
        return json.loads(raw) if raw else None


def paginate(path):
    items, page = [], 1
    while True:
        sep = "&" if "?" in path else "?"
        chunk = request("GET", f"{path}{sep}per_page=100&page={page}")
        if not chunk:
            break
        items.extend(chunk)
        if len(chunk) < 100:
            break
        page += 1
    return items


def latest_state(dep_id):
    statuses = request("GET", f"/repos/{REPO}/deployments/{dep_id}/statuses?per_page=1")
    return statuses[0]["state"] if statuses else None


def prune(dep):
    dep_id = dep["id"]
    try:
        request("POST", f"/repos/{REPO}/deployments/{dep_id}/statuses", {"state": "inactive"})
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        print(f"  note: could not set #{dep_id} inactive ({exc}); deleting anyway")
    try:
        request("DELETE", f"/repos/{REPO}/deployments/{dep_id}")
        return True
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            print(f"  #{dep_id} already gone")
            return True
        print(f"  FAILED to delete #{dep_id}: HTTP {exc.code}", file=sys.stderr)
        return False
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"  FAILED to delete #{dep_id}: network error ({exc}); "
              "will retry next run", file=sys.stderr)
        return False


def main():
    if not REPO:
        print("GITHUB_REPOSITORY is required", file=sys.stderr)
        return 1

    try:
        deployments = paginate(f"/repos/{REPO}/deployments")
    except urllib.error.HTTPError as exc:
        print(f"could not list deployments (HTTP {exc.code}); "
              "check the token has deployments:write", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"could not list deployments (network error: {exc}); "
              "retrying next run", file=sys.stderr)
        return 1
    deployments.sort(key=lambda d: d.get("created_at", ""), reverse=True)
    for dep in deployments:
        # A status read that fails leaves _state None, which plan() treats as
        # fail-closed (skip, never delete): a read error must never widen the
        # delete set.
        try:
            dep["_state"] = latest_state(dep["id"])
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            dep["_state"] = None
            print(f"  note: could not read status for #{dep['id']} ({exc}); "
                  "skipping it this run", file=sys.stderr)

    keep, delete, skip = plan(deployments)

    for dep in keep:
        print(f"KEEP   [{dep.get('environment')}] #{dep['id']} passing {dep.get('created_at')}")
    for dep in skip:
        print(f"SKIP   [{dep.get('environment')}] #{dep['id']} {dep.get('_state')} (in-flight)")

    done = 0
    failed = 0
    for dep in delete:
        label = f"[{dep.get('environment')}] #{dep['id']} {dep.get('_state')} {dep.get('created_at')}"
        if DRY_RUN:
            print(f"DRYRUN would delete {label}")
            done += 1
        elif prune(dep):
            print(f"DELETE {label}")
            done += 1
        else:
            failed += 1

    verb = "would delete" if DRY_RUN else "deleted"
    print(f"\nKept {len(keep)}, {verb} {done}, skipped {len(skip)} (in-flight).")
    if failed:
        print(f"::error title=Prune deployments::{failed} deployment(s) failed to delete (see the log "
              "above); verify the token has deployments:write. Marking the job failed.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
