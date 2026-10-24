# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Deleting a published release is a decision a person makes.

A release page is the changelog for its version, and carries the assets
built for it: the tarball and the SBOM. The stub shown in
`prune-releases.yml`'s header ran on every `release: published` with
`keep: 1`, so publishing one release deleted the page before it as a side
effect, and the template's release stub did the same. The stub is
dispatch-only now, and the dispatch previews until someone turns the dry run
off. The reusable workflow's own inputs and defaults are unchanged: a caller
that forgets `dry-run` still gets a plan rather than a deletion.
"""

from __future__ import annotations

import yaml
from conftest import ROOT, workflow_inputs, workflow_on

PRUNE = ".github/workflows/prune-releases.yml"


def stub(rel: str) -> dict:
    """The stub shown in a workflow's header, parsed as the YAML a consumer copies."""
    lines = (ROOT / rel).read_text(encoding="utf-8").split("\n---\n", 1)[0].splitlines()
    start = next(i for i, line in enumerate(lines) if line.rstrip().endswith("adds a stub:"))
    body: list[str] = []
    for line in lines[start + 1:]:
        if line.startswith("#   "):
            body.append(line[4:])
        elif body:
            break
    return yaml.safe_load("\n".join(body))


class TestTheStub:
    def test_it_runs_only_when_dispatched(self):
        """The defect: a release event deleted the release before it, unasked."""
        assert set(workflow_on(stub(PRUNE))) == {"workflow_dispatch"}

    def test_the_dispatch_previews_until_told_otherwise(self):
        doc = stub(PRUNE)
        assert workflow_on(doc)["workflow_dispatch"]["inputs"]["dry-run"]["default"] is True
        assert doc["jobs"]["prune"]["with"]["dry-run"] == "${{ inputs.dry-run }}"


class TestTheWorkflowKeepsItsDefaults:
    def test_a_caller_that_says_nothing_gets_a_plan(self):
        inputs = workflow_inputs(PRUNE)
        assert inputs["dry-run"]["default"] is True
        assert inputs["keep"]["default"] == 1
        assert inputs["delete-tags"]["default"] is False
