#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
# =============================================================================
# CI Failure Alert - mechanical failure escalation
# =============================================================================
# Invoked by ops-ci-failure-alert.yml when a core workflow completes on a
# long-lived branch. Opens a labeled issue on failure (deduped per workflow)
# and closes it automatically when the same workflow recovers. Requires:
#   GH_TOKEN, WORKFLOW_NAME, CONCLUSION, BRANCH, RUN_URL, HEAD_SHA
# =============================================================================
set -euo pipefail

LABEL='ci: failure'
TITLE="🚨 CI failing on ${BRANCH}: ${WORKFLOW_NAME}"

# Take the first match in bash rather than `| head -n 1`: under pipefail,
# head closing the pipe early can SIGPIPE gh and fail the whole script.
# Pass the title through the environment and read it as env.TITLE inside jq,
# never interpolated into the filter: a workflow name containing a double-quote
# would otherwise produce an invalid jq program, and the unguarded assignment
# would then abort the whole alert under set -e.
#
# A genuine lookup FAILURE (auth/API) and a no-match are different: no match
# is exit 0 with empty output (a fresh issue is opened, correct), while a
# non-zero exit means the dedup check itself failed - warn, because we may
# open a duplicate escalation issue this run rather than commenting on the
# existing one.
if ! existing=$(TITLE="$TITLE" gh issue list --state open --label "$LABEL" --json number,title \
  --jq '.[] | select(.title == env.TITLE) | .number'); then
  echo "::warning::Could not list existing failure issues (gh/API error); a duplicate escalation issue may be opened this run."
  existing=""
fi
existing="${existing%%$'\n'*}"

if [ "$CONCLUSION" = "failure" ]; then
  BODY="**Workflow:** ${WORKFLOW_NAME}
**Branch:** \`${BRANCH}\`
**Commit:** ${HEAD_SHA}
**Run:** ${RUN_URL}

This issue was opened automatically because a core workflow failed on a long-lived branch. It will be closed automatically when the workflow succeeds again."
  if [ -n "$existing" ]; then
    gh issue comment "$existing" --body "Still failing: ${RUN_URL} (commit ${HEAD_SHA})" \
      || echo "::warning::Could not comment on escalation issue #$existing (gh/API error); the issue is still open and tracking the failure."
    echo "Commented on existing issue #$existing"
  else
    # Self-sufficient labeling: in a derived repository the label sync may
    # not have run yet, and `gh issue create --label` fails outright on a
    # missing label - the escalation itself must never be the thing that
    # breaks. --force makes this an update when the label already exists.
    gh label create "$LABEL" --color 'b60205' \
      --description '🚨 A core workflow is failing on a long-lived branch (opened/closed automatically).' \
      --force >/dev/null 2>&1 || true
    gh label create 'priority: high' --color 'd93f0b' \
      --description '🛑 Blocking. Blocks a release or significant functionality. Needs attention very soon.' \
      --force >/dev/null 2>&1 || true
    if ! gh issue create --title "$TITLE" --label "$LABEL" --label 'priority: high' --body "$BODY"; then
      echo "::error title=CI failure alert::Failed to open the CI-failure escalation issue for '${WORKFLOW_NAME}' on '${BRANCH}' - verify GH_TOKEN has issues: write. The failure is NOT being tracked."
      exit 1
    fi
    echo "Opened new failure issue"
  fi
elif [ "$CONCLUSION" = "success" ] && [ -n "$existing" ]; then
  # A failed close leaves a stale "CI failing" issue open after recovery; the
  # next successful run re-attempts it (existing is found again), so warn
  # rather than fail the recovery run.
  gh issue close "$existing" --comment "Resolved: ${WORKFLOW_NAME} succeeded on \`${BRANCH}\` - ${RUN_URL}" \
    || echo "::warning::Could not close resolved escalation issue #$existing (gh/API error); it will be retried on the next successful run."
  echo "Closed issue #$existing"
else
  echo "Nothing to do (conclusion=$CONCLUSION, open issue=${existing:-none})"
fi
