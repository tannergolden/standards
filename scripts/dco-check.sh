#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
# =============================================================================
# DCO Sign-Off Check - mechanical enforcement of the Developer Certificate
# of Origin contract (https://developercertificate.org), which a repository
# normally documents in its CONTRIBUTING.md. That guide is often INHERITED
# from an account's .github repository rather than carried locally, so this
# script deliberately links the certificate itself rather than guessing at
# a path inside whichever repository it is running in.
# =============================================================================
# Invoked through actions/dco-check on every pull request. Every
# human-authored commit in the PR must carry a `Signed-off-by:` trailer
# (git commit -s).
# Exempt by contract: commits whose GitHub author is a [bot] account
# (Dependabot - it carries its own provenance and never signs off).
# Human-attributed automation commits are NOT exempt - they map to the
# login of whoever triggered them, so all of them sign off mechanically
# (--signoff) like any human commit. Also exempt:
# MERGE commits
# (the "Update branch" button and merging the base into a topic branch
# create unsigned merges authored by whoever clicked - the certificate
# covers authored changes, not mechanical merges; the canonical DCO check
# draws the same line). Fails CLOSED on API errors: a gate that passes
# when GitHub is unreachable is not a gate. Requires:
#   GH_TOKEN, REPO, PR_NUMBER
# =============================================================================
set -euo pipefail

offenders=()
total=0

# Capture first, parse second: a failure inside process substitution is
# invisible to `set -e`/pipefail and would silently pass the gate.
# The author login is "-" (never empty) when the commit email is not
# linked to a GitHub account: bash treats tab as WHITESPACE IFS, so an
# empty field between two tabs would collapse and shift every later
# field left - flagging a signed-off commit as an offender and letting
# a real merge commit slip past the parents check.
JQ_ROWS='.[] | [.sha, (.author.login // "-"), ((.parents // []) | length), ((.commit.message // "") | split("\n") | map(select(startswith("Signed-off-by:"))) | length)] | @tsv'

# Two clients, one contract. `gh api` is the primary; when it cannot reach the
# endpoint (observed July 2026: persistent HTTP 503s for gh on hosted runners
# against pulls/{n}/commits while a plain HTTPS client succeeded in the same
# job window), fall back to curl with retries - GitHub's own 503 text says to
# resubmit. The fallback preserves EXACTLY the gate's semantics: same endpoint,
# same jq row shape, and still FAILS CLOSED if both clients exhaust their
# attempts. Resilience here means trying harder, never passing blind.
fetch_commits_tsv() {
  local tsv=""
  if tsv="$(gh api -X GET "repos/${REPO}/pulls/${PR_NUMBER}/commits" --paginate \
    --jq "$JQ_ROWS" 2>/dev/null)"; then
    printf '%s' "$tsv"
    return 0
  fi
  echo "::warning::gh could not list the PR's commits - retrying via direct HTTPS." >&2
  local page=1 rows="" resp="" count="" delay ok
  while :; do
    ok=false
    for delay in 0 3 7 15; do
      sleep "$delay"
      if resp="$(curl -sSf --max-time 30 \
        -A "dco-check" \
        -H "Authorization: Bearer ${GH_TOKEN}" \
        -H "Accept: application/vnd.github+json" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        "https://api.github.com/repos/${REPO}/pulls/${PR_NUMBER}/commits?per_page=100&page=${page}")"; then
        ok=true
        break
      fi
    done
    [ "$ok" = true ] || return 1
    # A non-array body (proxy error page, rate-limit object) must fail closed,
    # never parse as zero offenders.
    count="$(jq 'if type == "array" then length else error("not an array") end' <<< "$resp" 2>/dev/null)" || return 1
    rows+="$(jq -r "$JQ_ROWS" <<< "$resp")"$'\n'
    [ "$count" -lt 100 ] && break
    page=$((page + 1))
  done
  printf '%s' "$rows"
  return 0
}

commits_tsv="$(fetch_commits_tsv)" || {
  echo "::error title=DCO sign-off::Unable to list the PR's commits (GitHub API failure via gh AND direct HTTPS) - failing closed."
  exit 1
}

# One TSV row per commit: sha, author login ("-" when unmapped), parent
# count, and the number of Signed-off-by trailers in the message.
# --paginate covers PRs larger than one API page.
while IFS=$'\t' read -r sha login parents signoffs; do
  [ -n "$sha" ] || continue
  total=$((total + 1))
  case "$login" in
    *"[bot]") continue ;; # bot-authored: exempt by contract
  esac
  if [ "${parents:-1}" -ge 2 ]; then
    continue # merge commit: exempt by contract (see header)
  fi
  if [ "${signoffs:-0}" -eq 0 ]; then
    offenders+=("$sha")
  fi
done <<< "$commits_tsv"

if [ "${#offenders[@]}" -eq 0 ]; then
  echo "✅ DCO: all ${total} commit(s) carry a Signed-off-by trailer (or are bot-authored)."
  exit 0
fi

echo "::error title=DCO sign-off::${#offenders[@]} of ${total} commit(s) are missing the DCO Signed-off-by trailer."
{
  echo "### ✍️ DCO Sign-Off Check Failed"
  echo ""
  echo "The [Developer Certificate of Origin](https://developercertificate.org/) is a mandated contract (see CONTRIBUTING.md): every commit must be signed off with \`git commit -s\`."
  echo ""
  echo "**Commits missing \`Signed-off-by:\`**"
  for sha in "${offenders[@]}"; do
    echo "- \`${sha}\`"
  done
  echo ""
  echo "**Fix it:**"
  echo '```bash'
  echo "# Sign off every commit on this branch, then update the PR:"
  echo "git rebase --signoff @{upstream}"
  echo "git push --force-with-lease"
  echo '```'
  echo "For a single commit, \`git commit --amend -s --no-edit\` also works."
} >> "$GITHUB_STEP_SUMMARY"
exit 1
