#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
# =============================================================================
# Apply Rulesets - declarative branch and tag protection via the GitHub API
# =============================================================================
# Applies every ruleset in RULESETS_DIR to a repository, matched BY NAME:
# a ruleset whose name already exists is UPDATED in place, and one that
# does not is created. Rulesets the repository defines for itself are
# never touched, because nothing here deletes.
#
# Matching by name rather than by id is what makes this idempotent across
# repositories. Ids are per-repository and unknowable in advance; the name
# is the stable identity, and it is the thing a human reads in the settings
# UI anyway.
#
# ⚠️ THE PREFLIGHT IS THE POINT. A ruleset names required status checks by
# `<job id> / <job name>`. A required check that nothing in the repository
# can ever report does not FAIL a pull request - it leaves it PENDING, so
# every merge in the repository blocks indefinitely with no error anywhere
# to explain why. So this reads the target's own workflows first and refuses
# to apply a ruleset whose checks nothing declares. REQUIRE_CHECKS=false
# overrides it for the case where the workflows are arriving next.
#
# ⚠️ RUNNABLE BY HAND, and for a single repository usually should be.
# Applying rulesets is a one-time act of administration that a repository
# owner already has the rights for; lending those rights to a workflow via a
# stored ADMIN_TOKEN is the long way round. With `gh auth login` done, this
# needs no arguments at all from inside a clone of the standards repository:
#
#     bash scripts/apply-rulesets.sh                       # preview this repo
#     DRY_RUN=false bash scripts/apply-rulesets.sh         # apply it
#     TARGET_REPO=owner/name bash scripts/apply-rulesets.sh
#
# Placeholders in the JSON are substituted before it is sent:
#   ${DEFAULT_BRANCH}  the target repository's own default branch
#
# The shipped rulesets do NOT use it. They use GitHub's own `~DEFAULT_BRANCH`
# token, which the API resolves per repository and which therefore keeps
# working across a branch rename that happens after this ran. Substitution is
# for a caller supplying their own rulesets directory.
#
# Requires: gh (authenticated, or GH_TOKEN with administration write), jq
# Optional: TARGET_REPO     defaults to the repository gh is pointed at
#           RULESETS_DIR    defaults to ../data/rulesets beside this script
#           DRY_RUN         defaults to TRUE; set false to actually apply
#           REQUIRE_CHECKS  set false to skip the deadlock preflight
# =============================================================================
set -euo pipefail

for tool in gh jq; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "::error title=Rulesets::'${tool}' is required and is not installed."
    exit 1
  fi
done

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RULESETS_DIR="${RULESETS_DIR:-${HERE}/../data/rulesets}"

# Defaulting the target to "whatever gh is pointed at" is what makes a manual
# run a single command. In Actions the caller always passes it explicitly.
if [ -z "${TARGET_REPO:-}" ]; then
  TARGET_REPO="$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null || true)"
fi
if [ -z "$TARGET_REPO" ]; then
  echo "::error title=Rulesets::TARGET_REPO is required, and no repository could be inferred from the current directory."
  exit 1
fi

# Defaults to a PREVIEW, unlike everything else here, which defaults to doing
# what it was asked. This one protects branches, and a wrong ruleset blocks
# every merge in the repository. Being asked twice is the cheaper mistake.
DRY_RUN="$(printf '%s' "${DRY_RUN:-true}" | tr '[:upper:]' '[:lower:]')"
REQUIRE_CHECKS="$(printf '%s' "${REQUIRE_CHECKS:-true}" | tr '[:upper:]' '[:lower:]')"

if [ ! -d "$RULESETS_DIR" ]; then
  echo "::error title=Rulesets::Rulesets directory '$RULESETS_DIR' does not exist."
  exit 1
fi

shopt -s nullglob
FILES=("$RULESETS_DIR"/*.json)
shopt -u nullglob
if [ ${#FILES[@]} -eq 0 ]; then
  echo "::error title=Rulesets::No ruleset JSON found in '${RULESETS_DIR}'."
  exit 1
fi

DEFAULT_BRANCH="$(gh api "repos/${TARGET_REPO}" --jq '.default_branch' 2>/dev/null || true)"
if [ -z "$DEFAULT_BRANCH" ]; then
  echo "::error title=Rulesets::Could not read '${TARGET_REPO}'. Check that it exists, that you are authenticated, and that the token can administer it."
  exit 1
fi
echo "Target:   ${TARGET_REPO} (default branch: ${DEFAULT_BRANCH})"
echo "Rulesets: ${RULESETS_DIR}"
[ "$DRY_RUN" = "true" ] && echo "Mode:     DRY RUN - nothing will be changed."

# Substitution runs through jq, not sed: a branch name may contain characters
# sed would read as syntax, and the result has to stay valid JSON regardless.
render() {
  jq --arg default_branch "$DEFAULT_BRANCH" \
    'walk(if type == "string" then gsub("\\$\\{DEFAULT_BRANCH\\}"; $default_branch) else . end)' \
    < "$1"
}

# --- Preflight: can the required checks ever report? -------------------------
#
# Collect every `<job id> / <job name>` context the rulesets demand, reduce it
# to job ids, and confirm the target declares each one. A called workflow
# reports under its CALLER's job id, which is why the id is the thing to check
# and why those ids are documented as load-bearing.
required_job_ids() {
  local file
  for file in "${FILES[@]}"; do
    render "$file" 2>/dev/null | jq -r '
      (.rules // [])[]
      | select(.type == "required_status_checks")
      | (.parameters.required_status_checks // [])[]
      | .context
    ' 2>/dev/null || true
  done | sed 's| /.*||' | sed '/^$/d' | sort -u
}

# An unlistable workflow directory is NOT the same as "no workflow declares
# these checks", and conflating the two makes this refuse every private
# repository whose token holds administration write but not contents read.
#
# ⚠️ THE LISTING IS HOISTED OUT OF THE FUNCTION ON PURPOSE. It used to set
# WORKFLOWS_READABLE=false from inside `declared_job_ids`, which is invoked
# as `$(declared_job_ids | sort -u)` - a command substitution AND a
# pipeline, so two subshells deep. The assignment never reached this scope,
# the flag always read `true`, and the diagnosis below was dead code. The
# operator was told to fix workflows that were fine.
WORKFLOWS_READABLE=true
workflow_file_names() {
  gh api "repos/${TARGET_REPO}/contents/.github/workflows" \
    --jq '.[] | select(.type == "file") | .name' 2>/dev/null || true
}

declared_job_ids() {
  local names="$1" name
  [ -n "$names" ] || return 0
  while IFS= read -r name; do
    case "$name" in
      *.yml | *.yaml) ;;
      *) continue ;;
    esac
    gh api "repos/${TARGET_REPO}/contents/.github/workflows/${name}" \
      -H 'Accept: application/vnd.github.raw' 2>/dev/null |
      awk '
        /^jobs:/ { in_jobs = 1; next }
        in_jobs && /^[^[:space:]#]/ { in_jobs = 0 }
        in_jobs && match($0, /^  [A-Za-z_][A-Za-z0-9_-]*:/) {
          print substr($0, 3, RLENGTH - 3)
        }
      '
  done <<< "$names"
}

MISSING=''
if [ "$REQUIRE_CHECKS" = "true" ]; then
  WANTED="$(required_job_ids)"
  if [ -n "$WANTED" ]; then
    # Assigned HERE, in the parent, so the flag survives.
    NAMES="$(workflow_file_names)"
    [ -n "$NAMES" ] || WORKFLOWS_READABLE=false
    DECLARED="$(declared_job_ids "$NAMES" | sort -u)"
    MISSING="$(comm -23 <(printf '%s\n' "$WANTED") <(printf '%s\n' "$DECLARED") || true)"
  fi
fi

# An unreadable workflow directory is a token problem, not a repository
# problem, and it gets its own message naming the fix.
if [ -n "$MISSING" ] && [ "$WORKFLOWS_READABLE" != "true" ]; then
  echo "::error title=Rulesets::Could not read the workflows in ${TARGET_REPO}, so the required status checks could not be verified. On a PRIVATE repository the token needs Contents: Read as well as Administration: Read and write - add it to the ADMIN_TOKEN, or set REQUIRE_CHECKS=false to apply without the preflight."
  exit 1
fi

if [ -n "$MISSING" ]; then
  LIST="$(printf '%s' "$MISSING" | tr '\n' ' ')"
  echo "::error title=Required check has no source::The rulesets require status checks from job id(s) [ ${LIST}], and no workflow in ${TARGET_REPO} declares them. Applying this would leave every pull request waiting on a check that never reports. Install the matching stubs first (ci, gitleaks, semantic-pr), or set REQUIRE_CHECKS=false if they are arriving next."
  if [ "$DRY_RUN" != "true" ]; then
    exit 1
  fi
  echo "Continuing the preview; this would have stopped a real run."
fi

# --- Apply -------------------------------------------------------------------

# Snapshot the existing rulesets once. Re-reading per file would race any
# ruleset created earlier in this same run.
EXISTING="$(gh api "repos/${TARGET_REPO}/rulesets" --paginate --jq '.[] | [.id, .name] | @tsv' 2>/dev/null || true)"

applied=0
failed=0

for file in "${FILES[@]}"; do
  base="$(basename "$file")"

  if ! BODY="$(render "$file" 2>/dev/null)"; then
    echo "::error title=Rulesets::${base} is not valid JSON."
    failed=$((failed + 1))
    continue
  fi

  # Shape is checked here rather than left to the API, which answers a bad
  # body with a 422 that names a field but never the file it came from.
  if ! NAME="$(printf '%s' "$BODY" | jq -er '.name | select(type == "string" and length > 0)')"; then
    echo "::error title=Rulesets::${base} has no top-level \"name\", so it cannot be matched or applied."
    failed=$((failed + 1))
    continue
  fi
  if ! printf '%s' "$BODY" | jq -e '.target | . == "branch" or . == "tag" or . == "push"' >/dev/null 2>&1; then
    echo "::error title=Rulesets::${base} has no valid \"target\" (expected branch, tag, or push)."
    failed=$((failed + 1))
    continue
  fi
  if ! printf '%s' "$BODY" | jq -e '.enforcement | . == "active" or . == "evaluate" or . == "disabled"' >/dev/null 2>&1; then
    echo "::error title=Rulesets::${base} has no valid \"enforcement\" (expected active, evaluate, or disabled)."
    failed=$((failed + 1))
    continue
  fi

  ID="$(printf '%s\n' "$EXISTING" | awk -F'\t' -v n="$NAME" '$2 == n {print $1; exit}')"

  if [ "$DRY_RUN" = "true" ]; then
    if [ -n "$ID" ]; then
      echo "[dry run] would UPDATE '${NAME}' (id ${ID})"
    else
      echo "[dry run] would CREATE '${NAME}'"
    fi
    applied=$((applied + 1))
    continue
  fi

  if [ -n "$ID" ]; then
    if printf '%s' "$BODY" | gh api -X PUT "repos/${TARGET_REPO}/rulesets/${ID}" --input - >/dev/null; then
      echo "✅ Updated '${NAME}' (id ${ID})"
      applied=$((applied + 1))
    else
      echo "::error title=Rulesets::Failed to update '${NAME}' (id ${ID})."
      failed=$((failed + 1))
    fi
  else
    if printf '%s' "$BODY" | gh api -X POST "repos/${TARGET_REPO}/rulesets" --input - >/dev/null; then
      echo "✅ Created '${NAME}'"
      applied=$((applied + 1))
    else
      echo "::error title=Rulesets::Failed to create '${NAME}'."
      failed=$((failed + 1))
    fi
  fi
done

if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  {
    echo "### 🛡️ Rulesets"
    echo ""
    if [ "$DRY_RUN" = "true" ]; then
      echo "Dry run: **${applied}** ruleset(s) would be applied to \`${TARGET_REPO}\`. Nothing was changed."
    else
      echo "Applied **${applied}** ruleset(s) to \`${TARGET_REPO}\`."
    fi
    if [ -n "$MISSING" ]; then
      echo ""
      echo "> [!WARNING]"
      echo "> Required status checks come from job id(s) \`$(printf '%s' "$MISSING" | tr '\n' ' ')\`, which no workflow in this repository declares. Applying this would leave every pull request pending forever."
    fi
    [ "$failed" -gt 0 ] && echo "" && echo "**${failed}** failed. See the log above."
  } >> "$GITHUB_STEP_SUMMARY"
fi

if [ "$failed" -gt 0 ]; then
  echo "::error title=Rulesets::${failed} ruleset(s) could not be applied."
  exit 1
fi

if [ "$DRY_RUN" = "true" ]; then
  echo "Done: ${applied} ruleset(s) would be applied. Set DRY_RUN=false to apply them."
else
  echo "Done: ${applied} ruleset(s)."
fi
