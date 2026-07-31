# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""A dry run must be visible in every job that performs one.

`apply-standards.yml` takes one `dry-run` input and hands it to all three
jobs. Two of them follow it with a '📝 Next Step' note in the run summary
saying the plan was not applied. The label job did not, so the documented
onboarding step, "run 🎯 Apply Standards once for the label taxonomy",
produced a green run, an empty summary, and no labels.

That is the shape of every P0 in this repository's audit: an operation that
did nothing, reporting success, with nothing on the surface to say so.
These tests bind the input's description to its wiring, and require that any
job consuming `dry-run` also reports it.
"""

from __future__ import annotations

import re

import pytest
from conftest import ROOT, load_yaml, workflow_inputs

WORKFLOW = ".github/workflows/apply-standards.yml"
DOC = ".github/workflows/README.md"


@pytest.fixture(scope="module")
def workflow() -> dict:
    return load_yaml(WORKFLOW)


def jobs_consuming_dry_run(workflow: dict) -> set[str]:
    """Job ids that pass `inputs.dry-run` down to anything."""
    found = set()
    for job_id, job in workflow["jobs"].items():
        for step in job.get("steps", []):
            for value in (step.get("with") or {}).values():
                if isinstance(value, str) and "inputs.dry-run" in value:
                    found.add(job_id)
    return found


class TestEveryDryRunIsReported:
    def test_all_three_jobs_consume_it(self, workflow):
        # Guards the premise: if a job stops taking dry-run, the invariant
        # below would pass vacuously for it.
        assert jobs_consuming_dry_run(workflow) == {"labels", "settings", "rulesets"}

    @pytest.mark.parametrize("job_id", ["labels", "settings", "rulesets"])
    def test_the_job_says_so_in_the_summary(self, workflow, job_id):
        """The defect: `labels` applied nothing and reported nothing."""
        steps = workflow["jobs"][job_id]["steps"]
        reporting = [
            s
            for s in steps
            if s.get("if") == "${{ inputs.dry-run }}"
            and "GITHUB_STEP_SUMMARY" in (s.get("run") or "")
        ]
        assert reporting, (
            f"job {job_id!r} consumes dry-run but never reports one. "
            "A run that wrote nothing must not look identical to one that wrote."
        )

    @pytest.mark.parametrize("job_id", ["labels", "settings", "rulesets"])
    def test_the_note_tells_the_reader_how_to_apply(self, workflow, job_id):
        steps = workflow["jobs"][job_id]["steps"]
        notes = " ".join(s.get("run") or "" for s in steps if s.get("if") == "${{ inputs.dry-run }}")
        assert "dry-run: false" in notes


class TestInputDescriptionMatchesWiring:
    def test_description_does_not_understate_its_scope(self, workflow):
        """It read "For settings and rulesets" while also gating labels."""
        described = workflow_inputs(WORKFLOW)["dry-run"]["description"].lower()
        for job_id in jobs_consuming_dry_run(workflow):
            assert job_id in described, (
                f"the dry-run description does not mention {job_id!r}, which it gates"
            )

    def test_default_is_still_safe(self, workflow):
        # Irreversible by default is the right way round; the fix is to
        # report the dry run, never to stop defaulting to one.
        assert workflow_inputs(WORKFLOW)["dry-run"]["default"] is True


class TestDocumentedStubIsHonest:
    """Following the README must produce the outcome the README promises."""

    def test_the_adoption_stub_addresses_dry_run(self):
        text = (ROOT / DOC).read_text(encoding="utf-8")
        # The section that tells a reader to run it for the label taxonomy.
        section = text.split("Then run **🎯 Apply Standards**", 1)
        assert len(section) == 2, f"{DOC}: the adoption prose moved; re-point this test"
        stub = section[1].split("```", 2)[1]
        assert "dry-run" in stub, (
            f"{DOC}: the stub passes no dry-run, so it resolves to the safe default "
            "of true and writes no labels, while the prose says it applies the taxonomy"
        )

    def test_the_prose_says_a_dry_run_writes_nothing(self):
        text = (ROOT / DOC).read_text(encoding="utf-8")
        window = text.split("Then run **🎯 Apply Standards**", 1)[1][:1600]
        assert re.search(r"dry.run", window, re.I), (
            f"{DOC}: nothing near the adoption step warns that the default is a dry run"
        )
