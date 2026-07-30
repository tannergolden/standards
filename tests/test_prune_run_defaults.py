# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Two wrappers around one destructive action must not disagree on safety.

`prune.yml` and `prune-runs.yml` both call `actions/prune-workflow-runs`,
and both expose the same two protections with OPPOSITE defaults:

  prune.yml        keep-recent-days: 0   keep-recent-commits: 35
  prune-runs.yml   keep-recent-days: 7   keep-recent-commits: 0

`scripts/prune-workflow-runs.py` says of them "either may be 0 to disable
it; both may be on at once". They protect different things.
KEEP_RECENT_COMMITS matches a run's `head_sha` against the last N
DEFAULT-BRANCH commits, so it protects nothing on a pull request branch.
KEEP_RECENT_DAYS is a time window and protects any commit-triggered run.

So under `prune.yml`'s defaults, on its documented weekly schedule, a run on
an open pull request had no protection but the single newest run per
workflow. Two callers of one action, one of which quietly offers less
safety than the other, is the kind of divergence nobody notices until the
history is gone.
"""

from __future__ import annotations

import pytest
from conftest import load_script, workflow_inputs

WRAPPERS = [".github/workflows/prune.yml", ".github/workflows/prune-runs.yml"]
prune = load_script("scripts/prune-workflow-runs.py")


class TestBothProtectionsAreOnByDefault:
    @pytest.mark.parametrize("rel", WRAPPERS)
    def test_the_day_window_is_enabled(self, rel):
        """The defect: prune.yml shipped 0, disabling the window."""
        value = workflow_inputs(rel)["keep-recent-days"]["default"]
        assert value >= 7, (
            f"{rel} disables the day window (keep-recent-days: {value}), so a run on an "
            "open pull request is protected by nothing but the per-workflow keep"
        )

    @pytest.mark.parametrize("rel", WRAPPERS)
    def test_the_commit_window_is_enabled(self, rel):
        value = workflow_inputs(rel)["keep-recent-commits"]["default"]
        assert value >= 1, f"{rel} disables the commit window (keep-recent-commits: {value})"

    def test_the_two_wrappers_agree(self):
        keys = ("keep", "keep-recent-days", "keep-recent-commits")
        defaults = [
            {k: workflow_inputs(rel)[k]["default"] for k in keys} for rel in WRAPPERS
        ]
        assert defaults[0] == defaults[1], (
            f"the two wrappers of one destructive action disagree: {defaults}"
        )


class TestTheDescriptionsMatchTheDefaults:
    @pytest.mark.parametrize("rel", WRAPPERS)
    def test_no_description_claims_a_disabled_protection_is_the_one_in_force(self, rel):
        """`prune-runs.yml` said "the day window is the protection here"
        while `prune.yml` said the opposite about the same pair."""
        text = workflow_inputs(rel)["keep-recent-commits"]["description"].lower()
        assert "0 by default" not in text, f"{rel} still describes a default it no longer has"


class TestTheScriptStillSupportsBoth:
    def test_zero_disables_a_window(self):
        assert prune.KEEP_RECENT_DAYS is not None

    def test_the_two_protections_are_independent(self):
        # Documented at scripts/prune-workflow-runs.py: "both may be on at
        # once". If that ever stopped being true, aligning the defaults
        # would be the wrong fix.
        source = (prune.__doc__ or "").lower()
        assert "both may be on at once" in source
