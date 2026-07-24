#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
# =============================================================================
# Open-PR - PR-only delivery for automated maintenance changes
# =============================================================================
# Commits whatever the calling workflow changed in the working tree to ONE
# fixed topic branch per concern (exactly BRANCH_PREFIX), force-pushed each
# run, and opens - or updates in place - a single evolving pull request
# against the integration branch. Automation obeys the same PR-only
# contract the repository rulesets (data/rulesets/) enforce for humans:
# nothing is ever pushed directly to a long-lived branch.
#
# Why one fixed branch: a per-run branch would mint a NEW PR every cron
# firing; in a lightly-maintained repository the stale bot then closes
# each one and the next firing re-opens a duplicate, forever. One branch
# means one PR that simply stays current until a maintainer merges it.
# The PR is also labeled 'automated' - the purpose-built marker for
# machine-authored PRs: it is stale-exempt (PRs opened with the default
# GITHUB_TOKEN cannot run required checks and legitimately wait for a
# human) and lets maintainers filter bot housekeeping from human work.
#
# Commit identity: authored, committed, and signed off (--signoff) as the
# repository OWNER, resolved from the identity Actions exposes. The change
# is made in their repository on their behalf, so they are the author of
# record and the DCO certification is theirs. The sign-off is not optional
# here: the DCO gate exempts only commits whose GitHub author login ends in
# [bot], and these map to a human, so without the trailer the required
# check fails and auto-merge could never fire.
#
# Commit message: COMMIT_TITLE/COMMIT_BODY come from the caller - pass
# run-specific measured values (counts, dates, observed numbers) so every
# commit is unique and meaningful, not a repeated boilerplate line. The
# script then appends a per-run change manifest (file counts + a bounded
# name-status list) so each commit also records exactly what it touched.
#
# No-ops cleanly when the working tree is unchanged.
#
# Required env:
#   GH_TOKEN - token for gh (PR creation) and, when set to a PAT,
#                    for the branch push (see token contract below)
#   BRANCH_PREFIX - the fixed topic branch, e.g. 'chore/license-year'
#   COMMIT_TITLE - Conventional Commit title for the change
#   PR_TITLE - pull request title (Conventional Commit format)
#   PR_BODY - pull request body (markdown)
# Optional env:
#   COMMIT_BODY - extended commit message body
#   PR_BASE - base branch for the PR (default: the repository's
#                    own default branch, resolved at run time)
#   AUTOMERGE - when 'true', queue the PR to squash-merge itself once the
#                    required checks pass (needs 'Allow auto-merge' in the
#                    repository settings, and BOT_ACCESS_TOKEN so the checks
#                    can run). Still gated on green CI - nothing merges
#                    unvalidated. Default: off (delivery waits for a human).
# Token contract: every checkout in this repository runs with
# persist-credentials: false (credential hygiene), so pushes ALWAYS use an
# explicit x-access-token URL built from GH_TOKEN when running in Actions
# (GITHUB_REPOSITORY set); outside Actions the ordinary origin remote is
# used. PRs opened with the default GITHUB_TOKEN do not trigger new
# workflow runs, so required checks stay pending until a maintainer
# re-runs them (or closes/reopens the PR). Configure a BOT_ACCESS_TOKEN
# secret to lift that limitation and to allow workflow-file pushes.
# =============================================================================
set -euo pipefail

: "${BRANCH_PREFIX:?BRANCH_PREFIX is required}"
: "${COMMIT_TITLE:?COMMIT_TITLE is required}"
: "${PR_TITLE:?PR_TITLE is required}"
: "${PR_BODY:?PR_BODY is required}"
# Base branch: whatever the caller named, else the repository's OWN
# default branch. Never a hardcoded branch name, which would be wrong for
# every repository that does not happen to share this one's conventions.
BASE="${PR_BASE:-}"
if [ -z "$BASE" ]; then
  if [ -n "${GITHUB_REPOSITORY:-}" ] && command -v gh >/dev/null 2>&1; then
    BASE="$(gh api "repos/${GITHUB_REPOSITORY}" --jq '.default_branch' 2>/dev/null || true)"
  fi
  BASE="${BASE:-$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')}"
  BASE="${BASE:-main}"
  echo "No base branch given; using the repository default '$BASE'."
fi
AUTO_LABEL='automated'

# Snapshot porcelain output once - piping into `grep -q` under pipefail
# can SIGPIPE git on large change sets and misreport them.
if [ -z "$(git status --porcelain)" ]; then
  echo "No changes detected - nothing to propose."
  exit 0
fi

# Resolve the repository OWNER's identity for the author, the committer,
# and the DCO sign-off. GitHub links an identity to an account only
# through an email that account owns, and the canonical always-linked form
# is the ID-based no-reply address (<id>+<login>@users.noreply.github.com).
# Build it from the owner login and numeric id Actions exposes, falling
# back to a gh API lookup, then to the plain no-reply address, and finally
# to the Actions bot identity for runs outside Actions. The NAME prefers
# the owner's display name (one best-effort API call) over the bare login.
REPO_OWNER="${GITHUB_REPOSITORY_OWNER:-}"
if [ -z "$REPO_OWNER" ] && [ -n "${GITHUB_REPOSITORY:-}" ]; then
  REPO_OWNER="${GITHUB_REPOSITORY%%/*}"
fi
OWNER_ID="${GITHUB_REPOSITORY_OWNER_ID:-}"
OWNER_NAME=""
if [ -n "$REPO_OWNER" ] && command -v gh >/dev/null 2>&1; then
  if [ -z "$OWNER_ID" ]; then
    OWNER_ID="$(gh api "users/${REPO_OWNER}" --jq '.id' 2>/dev/null || true)"
  fi
  OWNER_NAME="$(gh api "users/${REPO_OWNER}" --jq '.name // empty' 2>/dev/null || true)"
fi
if [ -n "$REPO_OWNER" ] && [ -n "$OWNER_ID" ]; then
  git config user.name "${OWNER_NAME:-$REPO_OWNER}"
  git config user.email "${OWNER_ID}+${REPO_OWNER}@users.noreply.github.com"
elif [ -n "$REPO_OWNER" ]; then
  git config user.name "${OWNER_NAME:-$REPO_OWNER}"
  git config user.email "${REPO_OWNER}@users.noreply.github.com"
else
  git config user.name 'github-actions[bot]'
  git config user.email 'github-actions[bot]@users.noreply.github.com'
fi

BRANCH="$BRANCH_PREFIX"
git checkout -B "$BRANCH"
git add -A

# Per-run change manifest: every commit records what THIS run actually
# touched (status letters + bounded file list), so no two automation
# commits read alike and the log answers "what changed?" without a diff.
# Callers add domain detail (measured values) via COMMIT_TITLE/COMMIT_BODY;
# this manifest is the engine-level floor every commit gets for free.
NAME_STATUS="$(git diff --cached --name-status)"
FILE_COUNT="$(printf '%s\n' "$NAME_STATUS" | sed '/^$/d' | wc -l | tr -d ' ')"
ADDED="$(printf '%s\n' "$NAME_STATUS" | grep -c '^A' || true)"
DELETED="$(printf '%s\n' "$NAME_STATUS" | grep -c '^D' || true)"
RENAMED="$(printf '%s\n' "$NAME_STATUS" | grep -c '^R' || true)"
MODIFIED=$((FILE_COUNT - ADDED - DELETED - RENAMED))
MANIFEST_LIMIT=15
MANIFEST="Run delta: ${FILE_COUNT} file(s) - ${ADDED} added, ${MODIFIED} modified, ${DELETED} deleted"
[ "$RENAMED" -gt 0 ] && MANIFEST="${MANIFEST}, ${RENAMED} renamed"
MANIFEST="${MANIFEST}.

$(printf '%s\n' "$NAME_STATUS" | sed '/^$/d' | head -n "$MANIFEST_LIMIT" | sed 's/^/  /')"
if [ "$FILE_COUNT" -gt "$MANIFEST_LIMIT" ]; then
  MANIFEST="${MANIFEST}
  ... and $((FILE_COUNT - MANIFEST_LIMIT)) more"
fi

# --signoff: the DCO gate exempts only commits whose GitHub author login
# ends in [bot]. These map to a human, so they are held to the human
# contract and the trailer is required for the check to pass and for
# AUTOMERGE to ever fire. Author and committer are both the owner.
if [ -n "${COMMIT_BODY:-}" ]; then
  git commit --signoff -m "$COMMIT_TITLE" -m "$COMMIT_BODY" -m "$MANIFEST"
else
  git commit --signoff -m "$COMMIT_TITLE" -m "$MANIFEST"
fi

# Force-push the fixed branch: each run replaces the branch content with
# the freshly generated change, keeping the single PR current. A push
# failure is the single most likely real error here (the default
# GITHUB_TOKEN cannot push .github/workflows/ files, branch protection,
# or a permissions/network rejection), so name the cause instead of
# letting set -e abort on git's raw stderr.
if [ -n "${GH_TOKEN:-}" ] && [ -n "${GITHUB_REPOSITORY:-}" ]; then
  PUSH_ARGS=("https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" "$BRANCH")
else
  PUSH_ARGS=(-u origin "$BRANCH")
fi
if ! git push --force "${PUSH_ARGS[@]}"; then
  echo "::error::Failed to push branch '$BRANCH'. If this change includes .github/workflows/ files, the default GITHUB_TOKEN cannot push them - configure a BOT_ACCESS_TOKEN secret (repo + workflow scopes). Otherwise verify branch-protection rules and the token's contents:write permission. No pull request was opened."
  exit 1
fi

# Update-in-place: when the branch already has an open PR, the force-push
# above already refreshed its content; a comment records the new run.
PR_REF=""
EXISTING=$(gh pr list --head "$BRANCH" --state open --json number --jq '.[0].number' 2>/dev/null || true)
if [ -n "$EXISTING" ]; then
  # The comment carries the run's (dynamic) commit title, so the PR's
  # timeline reads as a change log of what each refresh actually measured.
  gh pr comment "$EXISTING" --body "🔄 $(date -u +%F) run - \`${COMMIT_TITLE}\` (force-pushed \`$BRANCH\`)." >/dev/null 2>&1 || true
  echo "Updated existing pull request #$EXISTING in place."
  PR_REF="$EXISTING"
else
  if ! PR_URL=$(gh pr create --base "$BASE" --head "$BRANCH" \
    --title "$PR_TITLE" --body "$PR_BODY"); then
    echo "::error::Could not open the pull request. If this repository blocks Actions-created PRs, enable 'Allow GitHub Actions to create and approve pull requests' (Settings → Actions → General), or configure a BOT_ACCESS_TOKEN secret. The branch '$BRANCH' was pushed - you can open the PR manually."
    exit 1
  fi
  PR_REF="$PR_URL"

  # Automation marker (stale-exempt): best-effort only - a missing label or
  # a token without issues scope must never fail the delivery itself. The
  # create mirrors the labels.yml entry for repositories whose label sync
  # has not delivered it yet.
  gh label create "$AUTO_LABEL" --color 'c0a062' \
    --description '🤖 Opened by repository automation (sync, formatting, refresh) - stale-exempt and ready to merge.' \
    --force >/dev/null 2>&1 || true
  gh pr edit "$PR_URL" --add-label "$AUTO_LABEL" >/dev/null 2>&1 ||
    echo "::warning::Could not apply the '$AUTO_LABEL' label - the stale bot may close this PR after 30 days of inactivity."

  echo "Opened pull request: $PR_URL"
fi

# Optional auto-merge: when AUTOMERGE=true, queue the PR to squash-merge
# itself onto the base branch once the required checks pass - still gated on
# green CI, so nothing merges unvalidated. Requires 'Allow auto-merge' in the
# repository settings; best-effort so a disabled setting never fails the run.
if [ "${AUTOMERGE:-}" = "true" ] && [ -n "$PR_REF" ]; then
  gh pr merge --auto --squash "$PR_REF" \
    && echo "::notice::Auto-merge enabled - the PR will merge automatically once required CI checks pass." \
    || echo "::warning::Could not enable auto-merge (enable 'Allow auto-merge' in repository settings, and set BOT_ACCESS_TOKEN so required checks can run)."
fi
