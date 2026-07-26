#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Prune the Actions run history, keeping only the most recent run(s) per
workflow.

For every workflow (grouped by its stable workflow id), the newest
KEEP_PER_WORKFLOW completed runs are kept and every older completed run is
deleted - deleting a run removes its logs and artifacts too.

Two protections keep a run regardless of its workflow's quota:

  * KEEP_RECENT_DAYS - a run started within the window AND triggered by a
    commit event (push, pull request, merge group). Time alone is not
    enough: a schedule or a dispatch fires without anyone committing, and
    that history is what this exists to clear. Every kept run therefore
    answers "what happened to this commit?".
  * KEEP_RECENT_COMMITS - a run belonging to one of the last N commits on
    the default branch. A count rather than a window, for repositories
    that go quiet for weeks and still want their last commits explicable.

Either may be 0 to disable it; both may be on at once. Runs that are not
yet completed (queued / in_progress / waiting
/ requested / pending) are never deleted: the API refuses to delete an
in-flight run, and this run itself is one of them, so it can never delete
the job it is executing in. Idempotent and 404-tolerant.

Required env:
  GITHUB_REPOSITORY   owner/repo (set automatically inside Actions)
  GITHUB_TOKEN        token with `actions: write` (and `contents: read`
                      when KEEP_RECENT_COMMITS > 0, to read the commit list)
Optional env:
  GITHUB_API_URL       API base (default https://api.github.com)
  KEEP_PER_WORKFLOW    how many recent runs to keep per workflow (default 1)
  KEEP_RECENT_DAYS     never delete a COMMIT-TRIGGERED run started within
                       this many days (default 0 - disabled)
  KEEP_RECENT_COMMITS  never delete runs tied to this many latest default-
                       branch commits (default 35 - one page of the repo's
                       commit-history view; set 0 to disable)
  COMMIT_EVENTS        comma-separated events that count as commit-triggered
                       (default push,pull_request,pull_request_target,
                       merge_group)
  DELETE_DELAY         seconds to pause between deletes (default 0.3) to stay
                       under the secondary rate limit
  DRY_RUN              "1"/"true"/"yes" to log the plan without deleting

Run locally:
  GITHUB_REPOSITORY=owner/repo GITHUB_TOKEN=$(gh auth token) \
    DRY_RUN=1 python3 scripts/prune-workflow-runs.py
"""

import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
REPO = os.environ.get("GITHUB_REPOSITORY", "")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
DRY_RUN = os.environ.get("DRY_RUN", "").strip().lower() in ("1", "true", "yes")


def _int(name, default):
    try:
        value = int(os.environ.get(name, "").strip())
        return value if value >= 0 else default
    except (TypeError, ValueError):
        return default


def _float(name, default):
    try:
        return max(0.0, float(os.environ.get(name, "").strip()))
    except (TypeError, ValueError):
        return default


KEEP_PER_WORKFLOW = max(1, _int("KEEP_PER_WORKFLOW", 1))
# Default 35 == one page of the repo's commit-history view on GitHub, so the
# runs for every commit still visible on that first page are always kept.
KEEP_RECENT_COMMITS = _int("KEEP_RECENT_COMMITS", 35)
# 0 == disabled, so a caller that never heard of this keeps its old behaviour.
KEEP_RECENT_DAYS = _int("KEEP_RECENT_DAYS", 0)
DELETE_DELAY = _float("DELETE_DELAY", 0.3)

# What "connected to a commit" means. A push, a pull request, and a merge
# group all carry work someone wrote; a schedule or a dispatch does not.
COMMIT_EVENTS = frozenset(
    e.strip()
    for e in os.environ.get(
        "COMMIT_EVENTS", "push,pull_request,pull_request_target,merge_group"
    ).split(",")
    if e.strip()
)


def cutoff(days):
    """The instant a run must start after to be inside the window, or None
    when the window is disabled."""
    if days <= 0:
        return None
    return datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)


def started_at(run):
    """A run's creation time as an aware datetime, or None if unparseable -
    an unreadable timestamp must never look recent."""
    raw = (run.get("created_at") or "").strip()
    if not raw:
        return None
    try:
        return datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None

# Only a completed run can be deleted; every other status is in-flight and
# must be left alone.
COMPLETED = "completed"


def plan(runs, keep_per=KEEP_PER_WORKFLOW, recent_shas=frozenset(),
         since=None, commit_events=COMMIT_EVENTS):
    """Pure decision function (no I/O), so it is unit-testable.

    `runs` must be sorted newest-first. Returns (keep, delete, skip):
      keep   - the newest `keep_per` COMPLETED runs of each workflow, PLUS
               every completed run whose head_sha is in `recent_shas`, PLUS
               every completed COMMIT-TRIGGERED run started at or after
               `since` (None disables the window)
      delete - every other completed run
      skip   - runs that are not completed (never deletable)

    The per-workflow quota is spent by protected runs too, so a workflow
    whose recent runs are all protected does not also retain an ancient
    one: "one run each" is a floor for quiet workflows, not an extra.
    """
    keep, delete, skip = [], [], []
    kept = {}
    for run in runs:
        if run.get("status") != COMPLETED:
            skip.append(run)
            continue
        wid = run.get("workflow_id")
        protected = run.get("head_sha") in recent_shas
        if not protected and since is not None and run.get("event") in commit_events:
            when = started_at(run)
            protected = when is not None and when >= since
        if protected or kept.get(wid, 0) < keep_per:
            kept[wid] = kept.get(wid, 0) + 1
            keep.append(run)
        else:
            delete.append(run)
    return keep, delete, skip


# The URL is always the GitHub API base plus a literal path, never user
# input, so no file: or custom scheme can reach urlopen. Annotated per
# call site rather than ignored repository-wide, so a future urlopen on
# an untrusted URL is still flagged.
def request(method, path):
    req = urllib.request.Request(API + path, method=method)  # noqa: S310
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        raw = resp.read()
        return json.loads(raw) if raw else None


def list_runs():
    """Every workflow run, newest first. The runs endpoint wraps the page in
    a `workflow_runs` array (unlike the flat deployments list)."""
    items, page = [], 1
    while True:
        data = request("GET", f"/repos/{REPO}/actions/runs?per_page=100&page={page}")
        chunk = (data or {}).get("workflow_runs", [])
        if not chunk:
            break
        items.extend(chunk)
        if len(chunk) < 100:
            break
        page += 1
    return items


def default_branch():
    info = request("GET", f"/repos/{REPO}")
    return (info or {}).get("default_branch") or "main"


def recent_commit_shas(count):
    """The head SHAs of the newest `count` commits on the default branch.
    Runs whose head_sha is in this set are protected from deletion."""
    if count <= 0:
        return frozenset()
    branch = default_branch()
    shas, page = [], 1
    while len(shas) < count:
        chunk = request("GET", f"/repos/{REPO}/commits?sha={branch}&per_page=100&page={page}")
        if not chunk:
            break
        shas.extend(commit["sha"] for commit in chunk)
        if len(chunk) < 100:
            break
        page += 1
    return frozenset(shas[:count])


def main():
    if not REPO:
        print("GITHUB_REPOSITORY is required", file=sys.stderr)
        return 1

    recent = frozenset()
    if KEEP_RECENT_COMMITS > 0:
        try:
            recent = recent_commit_shas(KEEP_RECENT_COMMITS)
        except urllib.error.HTTPError as exc:
            # Abort rather than risk deleting runs the caller asked to protect.
            print(
                f"could not read the last {KEEP_RECENT_COMMITS} commits (HTTP {exc.code}); "
                "aborting so no protected run is deleted",
                file=sys.stderr,
            )
            return 1
        except (urllib.error.URLError, TimeoutError) as exc:
            print(
                f"could not read the last {KEEP_RECENT_COMMITS} commits (network error: {exc}); "
                "aborting so no protected run is deleted",
                file=sys.stderr,
            )
            return 1

    try:
        runs = list_runs()
    except urllib.error.HTTPError as exc:
        print(f"could not list workflow runs (HTTP {exc.code}); "
              "check the token has actions:write", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"could not list workflow runs (network error: {exc}); "
              "retrying next run", file=sys.stderr)
        return 1
    runs.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    since = cutoff(KEEP_RECENT_DAYS)
    keep, delete, skip = plan(runs, recent_shas=recent, since=since)

    kept_workflows = {r.get("workflow_id") for r in keep}
    protections = [f"keeping {KEEP_PER_WORKFLOW} per workflow"]
    if since is not None:
        protections.append(
            f"every commit-triggered run since {since:%Y-%m-%d %H:%M} UTC "
            f"({KEEP_RECENT_DAYS}d)"
        )
    if recent:
        protections.append(f"any run from the last {len(recent)} commit(s)")
    print(
        f"{len(runs)} run(s) across {len(kept_workflows)} workflow(s); "
        + ", plus ".join(protections) + "."
    )
    for run in skip:
        print(f"SKIP   [{run.get('name')}] #{run.get('run_number')} {run.get('status')} (in-flight)")

    done = 0
    failed = 0
    for run in delete:
        label = (
            f"[{run.get('name')}] #{run.get('run_number')} "
            f"{run.get('conclusion')} {run.get('created_at')} (id {run['id']})"
        )
        if DRY_RUN:
            print(f"DRYRUN would delete {label}")
            done += 1
            continue
        try:
            request("DELETE", f"/repos/{REPO}/actions/runs/{run['id']}")
            print(f"DELETE {label}")
            done += 1
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                print(f"  #{run['id']} already gone")
            elif exc.code in (403, 429):
                # Secondary rate limit: stop cleanly. The weekly schedule (or
                # a re-run) picks up the remainder next time.
                print(f"  rate limited (HTTP {exc.code}); stopping - the rest is pruned next run")
                break
            else:
                # An unexpected status (401/422/5xx) is a real failure, not a
                # no-op: count it so the job exits non-zero instead of going
                # green while deletions silently fail.
                failed += 1
                print(f"  FAILED to delete #{run['id']}: HTTP {exc.code}", file=sys.stderr)
        except (urllib.error.URLError, TimeoutError) as exc:
            failed += 1
            print(f"  FAILED to delete #{run['id']}: network error ({exc}); "
                  "will retry next run", file=sys.stderr)
        if DELETE_DELAY:
            time.sleep(DELETE_DELAY)

    verb = "would delete" if DRY_RUN else "deleted"
    print(f"\nKept {len(keep)}, {verb} {done}, skipped {len(skip)} (in-flight).")
    if failed:
        print(f"::error title=Prune run history::{failed} workflow run(s) failed to delete (see the log "
              "above); verify the token has actions:write. Marking the job failed.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
