#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
# =============================================================================
# Apply Repository Settings - the settings half of "set up to standard"
# =============================================================================
# Reads data/repository-settings.json and brings a repository's settings in
# line with it. Rulesets are NOT touched here: they live in data/rulesets/ and
# are applied by apply-rulesets.sh, because branch protection is the change
# that can lock a repository's own automation out of it.
#
# READ BEFORE WRITE. Every setting is compared against its current value and
# only the differences are sent, so a no-op run reports "0 changed" and
# anything else in the summary is a real difference.
#
# THREE ENDPOINT GROUPS, ONE PLAN: the repository object, the Actions
# policies (the workflow token and fork pull requests, under Settings →
# Actions → General), and the security features. The settings file mirrors
# that shape, and everything deliberately NOT written lives in its _excluded
# block so absence is a decision rather than an oversight.
#
# In Actions, the plan is also written to the job's step summary, so the
# dry-run verdict is readable without opening the log.
#
# DRY RUN BY DEFAULT, like apply-rulesets.sh. A caller that forgets the flag
# gets a plan rather than a change.
#
# ⚠️ VISIBILITY AND PLAN GATE SOME OF THIS. Secret scanning is free on public
# repositories and needs Advanced Security on private ones; private
# vulnerability reporting is public-only. Both are detected and SKIPPED with a
# notice rather than failing the run, because a private repository that cannot
# have a feature has not misconfigured anything.
#
# Usage:
#     bash scripts/apply-settings.sh                  # preview
#     DRY_RUN=false bash scripts/apply-settings.sh    # apply
#     TARGET_REPO=owner/name DRY_RUN=false bash scripts/apply-settings.sh
#
# Requires: gh, authenticated with a token holding administration write.
# Optional: TARGET_REPO   defaults to the repository gh is pointed at
#           SETTINGS_FILE defaults to ../data/repository-settings.json
#           DRY_RUN       defaults to TRUE; set false to actually apply
# =============================================================================
set -euo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SETTINGS_FILE="${SETTINGS_FILE:-${HERE}/../data/repository-settings.json}"

if [ ! -f "$SETTINGS_FILE" ]; then
  echo "::error title=Repository settings::No settings file at ${SETTINGS_FILE}."
  exit 1
fi

if [ -z "${TARGET_REPO:-}" ]; then
  TARGET_REPO="$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null || true)"
fi
if [ -z "$TARGET_REPO" ]; then
  echo "::error title=Repository settings::TARGET_REPO is required, and no repository could be inferred from the current directory."
  exit 1
fi

DRY_RUN="$(printf '%s' "${DRY_RUN:-true}" | tr '[:upper:]' '[:lower:]')"

# Every plan line goes to stdout AND is kept for the Actions step summary,
# so a dispatcher reads the verdict without opening the log. Outside Actions
# (no GITHUB_STEP_SUMMARY) the summary is simply skipped.
PLAN=''
plan() { printf '%s\n' "$1"; PLAN="${PLAN}${1}"$'\n'; }
write_summary() {
  [ -z "${GITHUB_STEP_SUMMARY:-}" ] && return 0
  {
    echo "### ⚙️ Repository settings: \`${TARGET_REPO}\`"
    echo
    echo '```text'
    printf '%s' "$PLAN"
    echo '```'
    echo
    echo "$1"
  } >> "$GITHUB_STEP_SUMMARY"
}

# One read of the repository, reused for every comparison below.
CURRENT="$(gh api "repos/${TARGET_REPO}" 2>/dev/null || true)"
if [ -z "$CURRENT" ]; then
  echo "::error title=Repository settings::Could not read '${TARGET_REPO}'. Check that it exists, that you are authenticated, and that the token can administer it."
  exit 1
fi

VISIBILITY="$(printf '%s' "$CURRENT" | jq -r '.visibility // "unknown"')"
IS_PUBLIC=false
[ "$VISIBILITY" = "public" ] && IS_PUBLIC=true

echo "Target:     ${TARGET_REPO} (${VISIBILITY})"
echo "Settings:   ${SETTINGS_FILE}"
[ "$DRY_RUN" = "true" ] && echo "Mode:       DRY RUN - nothing will be changed."
echo

# ── Plain repository settings ────────────────────────────────────────────────
# Compared one at a time so the plan names the setting rather than a blob.
PATCH='{}'
CHANGED=0
UNCHANGED=0

while IFS=$'\t' read -r key want; do
  # `// null` would be wrong here: jq treats FALSE as empty, so every setting
  # whose correct value is false would read as null and be re-sent forever.
  have="$(printf '%s' "$CURRENT" | jq -c --arg k "$key" 'if has($k) then .[$k] else null end')"
  if [ "$have" = "$want" ]; then
    UNCHANGED=$((UNCHANGED + 1))
    continue
  fi
  plan "$(printf '  CHANGE  %-32s %s -> %s' "$key" "$have" "$want")"
  PATCH="$(printf '%s' "$PATCH" | jq -c --arg k "$key" --argjson v "$want" '.[$k] = $v')"
  CHANGED=$((CHANGED + 1))
done < <(jq -r '.repository | to_entries[] | [.key, (.value | tojson)] | @tsv' "$SETTINGS_FILE")

# ── Actions workflow-token policy ────────────────────────────────────────────
# A separate endpoint from the repository object, and the one setting whose
# absence has no error log: a narrowed token fails a called workflow before
# any job starts. Read before write, like everything above.
ACT_PATCH='{}'
WANT_WFP="$(jq -r '(.actions // {}).default_workflow_permissions // ""' "$SETTINGS_FILE")"
WANT_APPROVE="$(jq -r '(.actions // {}) | if has("can_approve_pull_request_reviews") then (.can_approve_pull_request_reviews | tostring) else "" end' "$SETTINGS_FILE")"

if [ -n "$WANT_WFP" ] || [ -n "$WANT_APPROVE" ]; then
  ACT_CURRENT="$(gh api "repos/${TARGET_REPO}/actions/permissions/workflow" 2>/dev/null || true)"
  if [ -z "$ACT_CURRENT" ]; then
    plan "  SKIP    workflow_permissions             could not be read; is Actions enabled here?"
  else
    if [ -n "$WANT_WFP" ]; then
      have="$(printf '%s' "$ACT_CURRENT" | jq -r '.default_workflow_permissions // ""')"
      if [ "$have" = "$WANT_WFP" ]; then
        UNCHANGED=$((UNCHANGED + 1))
      else
        plan "$(printf '  CHANGE  %-32s %s -> %s' "default_workflow_permissions" "$have" "$WANT_WFP")"
        ACT_PATCH="$(printf '%s' "$ACT_PATCH" | jq -c --arg v "$WANT_WFP" '.default_workflow_permissions = $v')"
        CHANGED=$((CHANGED + 1))
      fi
    fi
    if [ -n "$WANT_APPROVE" ]; then
      have="$(printf '%s' "$ACT_CURRENT" | jq -r '.can_approve_pull_request_reviews | tostring')"
      if [ "$have" = "$WANT_APPROVE" ]; then
        UNCHANGED=$((UNCHANGED + 1))
      else
        plan "$(printf '  CHANGE  %-32s %s -> %s' "can_approve_pull_request_reviews" "$have" "$WANT_APPROVE")"
        ACT_PATCH="$(printf '%s' "$ACT_PATCH" | jq -c --argjson v "$WANT_APPROVE" '.can_approve_pull_request_reviews = $v')"
        CHANGED=$((CHANGED + 1))
      fi
    fi
  fi
fi

# ── Fork pull request approval policy ────────────────────────────────────────
# Its own endpoint again. This is the gate between an external fork and your
# runners: first-time contributors wait for a maintainer before their
# workflows execute. Readable, so it diffs like everything else.
FORK_WANT="$(jq -r '(.actions // {}).fork_pr_approval_policy // ""' "$SETTINGS_FILE")"
FORK_APPLY=''
# A private repository cannot be forked by an outside contributor, so GitHub
# refuses this endpoint outright ("Fork PR approval is not allowed for private
# repositories"). Gate it on visibility like the other public-only features:
# a repository that cannot have a feature has not misconfigured anything.
if [ -n "$FORK_WANT" ] && [ "$IS_PUBLIC" != "true" ]; then
  plan "  SKIP    fork_pr_approval_policy          public repositories only"
  FORK_WANT=''
fi
if [ -n "$FORK_WANT" ]; then
  FORK_CURRENT="$(gh api "repos/${TARGET_REPO}/actions/permissions/fork-pr-contributor-approval" 2>/dev/null || true)"
  if [ -z "$FORK_CURRENT" ]; then
    plan "  SKIP    fork_pr_approval_policy          could not be read; not available here"
  else
    have="$(printf '%s' "$FORK_CURRENT" | jq -r '.approval_policy // ""')"
    if [ "$have" = "$FORK_WANT" ]; then
      UNCHANGED=$((UNCHANGED + 1))
    else
      plan "$(printf '  CHANGE  %-32s %s -> %s' "fork_pr_approval_policy" "$have" "$FORK_WANT")"
      FORK_APPLY="$FORK_WANT"
      CHANGED=$((CHANGED + 1))
    fi
  fi
fi

# ── Security settings, each gated on what this repository can actually have ──
# Reported separately because they use their own endpoints, and because a skip
# here is a fact about the repository rather than a failure.
SEC_ENABLE=()
want_bool() { jq -r --arg k "$1" '.security[$k] // false' "$SETTINGS_FILE"; }

if [ "$(want_bool secret_scanning)" = "true" ]; then
  have="$(printf '%s' "$CURRENT" | jq -r '.security_and_analysis.secret_scanning.status // "unavailable"')"
  if [ "$have" = "enabled" ]; then
    UNCHANGED=$((UNCHANGED + 1))
  elif [ "$IS_PUBLIC" = "true" ] || [ "$have" != "unavailable" ]; then
    plan "  CHANGE  secret_scanning                  ${have} -> enabled"
    SEC_ENABLE+=("secret_scanning")
    CHANGED=$((CHANGED + 1))
  else
    plan "  SKIP    secret_scanning                  needs Advanced Security on a private repository"
  fi
fi

if [ "$(want_bool secret_scanning_push_protection)" = "true" ]; then
  have="$(printf '%s' "$CURRENT" | jq -r '.security_and_analysis.secret_scanning_push_protection.status // "unavailable"')"
  if [ "$have" = "enabled" ]; then
    UNCHANGED=$((UNCHANGED + 1))
  elif [ "$IS_PUBLIC" = "true" ] || [ "$have" != "unavailable" ]; then
    plan "  CHANGE  secret_scanning_push_protection  ${have} -> enabled"
    SEC_ENABLE+=("secret_scanning_push_protection")
    CHANGED=$((CHANGED + 1))
  else
    plan "  SKIP    secret_scanning_push_protection  needs Advanced Security on a private repository"
  fi
fi

# Non-provider patterns are stricter than the two above: plan-gated even on
# public repositories, so this is written only where the repository already
# REPORTS the feature. An absent field means the plan does not have it, and
# that is a skip, not a change.
if [ "$(want_bool secret_scanning_non_provider_patterns)" = "true" ]; then
  have="$(printf '%s' "$CURRENT" | jq -r '.security_and_analysis.secret_scanning_non_provider_patterns.status // "unavailable"')"
  if [ "$have" = "enabled" ]; then
    UNCHANGED=$((UNCHANGED + 1))
  elif [ "$have" != "unavailable" ]; then
    plan "  CHANGE  secret_scanning_non_provider_patterns  ${have} -> enabled"
    SEC_ENABLE+=("secret_scanning_non_provider_patterns")
    CHANGED=$((CHANGED + 1))
  else
    plan "  SKIP    secret_scanning_non_provider_patterns  not reported by this repository's plan"
  fi
fi

# These three are separate endpoints with no readable field on the repository
# object, so they are applied idempotently rather than compared. PUT on an
# already-enabled feature is a no-op that returns 204.
declare -a TOGGLES=()
[ "$(want_bool vulnerability_alerts)" = "true" ] && TOGGLES+=("vulnerability-alerts")
[ "$(want_bool automated_security_fixes)" = "true" ] && TOGGLES+=("automated-security-fixes")
if [ "$(want_bool private_vulnerability_reporting)" = "true" ]; then
  if [ "$IS_PUBLIC" = "true" ]; then
    TOGGLES+=("private-vulnerability-reporting")
  else
    plan "  SKIP    private_vulnerability_reporting  public repositories only"
  fi
fi
for t in "${TOGGLES[@]}"; do
  plan "  ENSURE  ${t}"
done

echo
plan "Plan: ${CHANGED} change(s), ${UNCHANGED} already correct, ${#TOGGLES[@]} ensured."

if [ "$CHANGED" -eq 0 ] && [ "${#TOGGLES[@]}" -eq 0 ]; then
  echo "Nothing to do."
  write_summary "Nothing to change: \`${TARGET_REPO}\` already matches the published set."
  exit 0
fi

if [ "$DRY_RUN" = "true" ]; then
  echo "Dry run: nothing was changed. Set DRY_RUN=false to apply this plan."
  write_summary "Dry run: **${CHANGED}** change(s) would be applied to \`${TARGET_REPO}\`. Nothing was changed."
  exit 0
fi

plan ""
if [ "$PATCH" != '{}' ]; then
  printf '%s' "$PATCH" | gh api --method PATCH "repos/${TARGET_REPO}" --input - >/dev/null
  plan "Applied repository settings."
fi

if [ "$ACT_PATCH" != '{}' ]; then
  printf '%s' "$ACT_PATCH" | gh api --method PUT "repos/${TARGET_REPO}/actions/permissions/workflow" --input - >/dev/null
  plan "Applied the Actions workflow-token policy."
fi

if [ -n "$FORK_APPLY" ]; then
  # Tolerated rather than fatal, like the security toggles below: this
  # endpoint is gated by things the plan cannot always see, and one refused
  # setting must not abandon every setting that comes after it.
  if gh api --method PUT "repos/${TARGET_REPO}/actions/permissions/fork-pr-contributor-approval" \
       -f "approval_policy=${FORK_APPLY}" >/dev/null 2>&1; then
    plan "Applied the fork pull request approval policy."
  else
    echo "::warning title=Repository settings::Could not set the fork pull request approval policy on ${TARGET_REPO}; it is unavailable on this repository's visibility or plan. Everything else was applied."
  fi
fi

for name in "${SEC_ENABLE[@]}"; do
  gh api --method PATCH "repos/${TARGET_REPO}" \
    -f "security_and_analysis[${name}][status]=enabled" >/dev/null
  plan "Enabled ${name}."
done

for t in "${TOGGLES[@]}"; do
  if gh api --method PUT "repos/${TARGET_REPO}/${t}" --silent 2>/dev/null; then
    plan "Ensured ${t}."
  else
    echo "::warning::Could not enable ${t}. It may be unavailable on this repository's plan or visibility."
  fi
done

write_summary "Applied to \`${TARGET_REPO}\`. A re-run now plans \`0 change(s)\`."

echo
echo "Done. Rulesets are a separate act: see scripts/apply-rulesets.sh."
