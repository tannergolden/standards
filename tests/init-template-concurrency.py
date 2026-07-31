# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""A workflow that force-pushes a rewritten tree must not race itself.

`init-template.yml` rewrites identity across a generated repository's whole
tree and force-pushes the result. Its published stub subscribes to `push`,
`create` and `workflow_dispatch`, and `create` and `push` BOTH fire when a
repository is generated from a template.

Neither the workflow nor the stub declared `concurrency`, so two runs
started together. Both found the sentinel present, both rewrote the tree,
and both pushed. The loser's `--force-with-lease` sees a ref that moved
under it and fails, leaving a freshly generated repository half-initialised
in its first minute, with a red check and no obvious cause.

Every prune workflow's published stub carries a concurrency group. This one
writes more than any of them and had none.

WHERE CONCURRENCY BELONGS HERE IS THE STUB, not the reusable workflow. A
called workflow runs in the caller's context, and every writer in this
repository declares its group in the stub it publishes. These tests hold to
that convention rather than introducing a second place to look.
"""

from __future__ import annotations

import re

import pytest
from conftest import ROOT

WORKFLOW = ".github/workflows/init-template.yml"
# Every workflow here that writes to a repository, so a new one cannot be
# added without deciding this question.
WRITERS = [
    WORKFLOW,
    ".github/workflows/prune.yml",
    ".github/workflows/prune-drafts.yml",
    ".github/workflows/prune-releases.yml",
    ".github/workflows/prune-runs.yml",
]


def stub(rel: str) -> str:
    """The commented stub in a workflow's header, which is what a consumer
    copies into their own repository."""
    return (ROOT / rel).read_text(encoding="utf-8").split("\n---\n", 1)[0]


@pytest.mark.parametrize("rel", WRITERS)
class TestAWriterPublishesAConcurrencyGroup:
    def test_the_stub_declares_one(self, rel):
        """The defect: init-template's stub had none, and `create` and
        `push` both fire when a repository is generated."""
        assert re.search(r"^#\s+concurrency:", stub(rel), re.M), (
            f"{rel}'s documented stub carries no concurrency group, so a consumer "
            "copying it verbatim gets none and two triggers race each other"
        )

    def test_it_does_not_cancel_in_progress_runs(self, rel):
        assert re.search(r"^#\s+cancel-in-progress:\s*false", stub(rel), re.M), (
            f"{rel}'s stub cancels in-progress runs; a half-finished write is worse "
            "than a queued one"
        )

    def test_the_group_is_stable_across_the_triggers_that_collide(self, rel):
        match = re.search(r"^#\s+group:\s*(.+)$", stub(rel), re.M)
        assert match, f"{rel}'s stub declares concurrency with no group"
        group = match.group(1)
        assert "github.workflow" in group, (
            f"{rel}: the group must key on the workflow so two triggers of the SAME "
            f"workflow serialise. Got: {group}"
        )
