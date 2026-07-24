#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
#
# Refreshes the copyright year across a repository's license records: the
# root LICENSE, and every file carrying an SPDX-FileCopyrightText header
# for the project holder. A REUSE.toml, where a repository has one, is
# covered by that same header sweep rather than as a special case.
#
# The holder is an anchor, not a wildcard. Only headers naming COPYRIGHT_
# HOLDER are rewritten, so vendored assets that declare a different holder
# of their own (fonts, third-party sources) never match and are left
# untouched. Rewriting those would misattribute somebody else's copyright.
#
# Idempotent: a no-op when every year is already current, so the calling
# pull-request flow proposes a change only when something actually moved.
#
# COPYRIGHT_HOLDER may be left empty, in which case the holder is resolved
# from the repository owner's display name (falling back to their login).
# That makes this correct for anyone's repository without configuration.
#

set -euo pipefail

COPYRIGHT_HOLDER="${COPYRIGHT_HOLDER:-}"
if [ -z "$COPYRIGHT_HOLDER" ]; then
  OWNER="${GITHUB_REPOSITORY_OWNER:-${GITHUB_REPOSITORY%%/*}}"
  if [ -n "$OWNER" ] && command -v gh >/dev/null 2>&1; then
    COPYRIGHT_HOLDER="$(gh api "users/${OWNER}" --jq '.name // empty' 2>/dev/null || true)"
  fi
  COPYRIGHT_HOLDER="${COPYRIGHT_HOLDER:-${OWNER:-}}"
  if [ -z "$COPYRIGHT_HOLDER" ]; then
    echo "::error::Could not resolve a copyright holder. Pass copyright-holder explicitly."
    exit 1
  fi
  echo "Resolved copyright holder from the repository owner: ${COPYRIGHT_HOLDER}"
fi

CURRENT_YEAR=$(date +'%Y')

# The holder appears inside two extended regular expressions below, so any
# regex metacharacter in the name has to be neutralized first.
# shellcheck disable=SC2016  # The $ and & here are sed regex syntax, not
# shell expansions, so the single quotes are deliberate.
HOLDER_RE=$(printf '%s' "$COPYRIGHT_HOLDER" | sed -E 's/[][\.*^$(){}?+|\/]/\\&/g')

# Rewrite a file's content through sed while preserving its mode and inode
# (a plain `mv` from a mktemp file would drop the executable bit off the
# scripts this sweep touches). Writes only when the content actually changes.
apply_sed() {
  local expr="$1" file="$2" tmp
  [[ -f "$file" ]] || return 0
  tmp=$(mktemp)
  sed -E "$expr" "$file" >"$tmp"
  if ! cmp -s "$tmp" "$file"; then
    cat "$tmp" >"$file"
  fi
  rm -f "$tmp"
}

# 1) The root LICENSE - the copyright of record.
if [[ -f LICENSE ]]; then
  apply_sed "s/(Copyright \\(c\\) )([0-9]{4}-)?(\\[year\\]|[0-9]{4})/\\1\\2$CURRENT_YEAR/" LICENSE
  echo "Checked the year in LICENSE (target $CURRENT_YEAR)."
else
  echo "::warning::No LICENSE file found, so the copyright year was not updated there. SPDX headers elsewhere in the tree are still processed." >&2
fi

# 2) Every SPDX-FileCopyrightText header naming the holder, in both the
#    comment form ("SPDX-FileCopyrightText: 2026 <holder>") and the
#    assignment form ('SPDX-FileCopyrightText = "2026 <holder>"'). The
#    trailing holder anchor keeps other holders untouched.
COUNT=0
# git grep exits 1 when there are simply no matches (fine) and >1 on a real
# error (not a git repo, git failure). Capture the exit code so a real
# failure surfaces as a warning instead of silently yielding "0 files" and a
# clean exit - that would be a false success hiding un-updated headers.
if FILES=$(git grep -lE "SPDX-FileCopyrightText[[:space:]]*[:=].*${HOLDER_RE}" -- .); then
  :
else
  rc=$?
  if [ "$rc" -gt 1 ]; then
    echo "::warning::git grep failed (exit $rc); no SPDX headers were scanned this run - the copyright year may be stale." >&2
  fi
  FILES=""
fi
if [ -n "$FILES" ]; then
  while IFS= read -r file; do
    apply_sed \
      "s/(SPDX-FileCopyrightText[[:space:]]*[:=][[:space:]]*\"?)(\\[year\\]|[0-9]{4})( ${HOLDER_RE})/\\1$CURRENT_YEAR\\3/" \
      "$file"
    COUNT=$((COUNT + 1))
  done <<< "$FILES"
fi

echo "Checked the copyright year in $COUNT SPDX header file(s) (target $CURRENT_YEAR)."

# Run-specific facts for the calling workflow's commit message (no-op
# outside Actions): the target year and how many files actually changed.
if [ -n "${GITHUB_OUTPUT:-}" ]; then
  CHANGED=$(git status --porcelain | wc -l | tr -d ' ')
  {
    echo "year=$CURRENT_YEAR"
    echo "changed=$CHANGED"
    echo "scanned=$COUNT"
  } >> "$GITHUB_OUTPUT"
fi
