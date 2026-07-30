# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The generated documents must be checked by something that runs.

Three documents claimed CI enforcement that did not exist.
`update-doc-indexes.py` says an index "can never disagree with the tree";
`docs/references/Repository-Labels.md` says "CI fails if it drifts";
`check-type-parity.py` names the three files it keeps in step. No job
anywhere invoked any of them, and the drift they promised to catch had
already shipped: `--check` on the doc indexes exited 1 on a clean checkout.

These tests require the gate to exist and to be reachable, and re-run the
generators so a stale committed file fails here rather than in a consumer's
copy of the standards.
"""

from __future__ import annotations

import pytest
from conftest import ROOT, load_yaml

SELF_CHECKS = ".github/workflows/self-checks.yml"

GENERATORS = [
    "scripts/update-doc-indexes.py",
    "scripts/update-label-docs.py",
    "scripts/check-type-parity.py",
]


def all_run_blocks() -> str:
    doc = load_yaml(SELF_CHECKS)
    return "\n".join(
        step.get("run") or ""
        for job in doc["jobs"].values()
        for step in job.get("steps", [])
    )


class TestTheGateExists:
    def test_self_checks_runs_the_generator_gate(self):
        assert "make lint-docs" in all_run_blocks(), (
            "no job runs the generators, so every 'CI fails if it drifts' claim is false"
        )

    def test_the_gate_target_covers_every_generator(self):
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        target = makefile.split("lint-docs:", 1)[1].split("\n\n", 1)[0]
        for generator in GENERATORS:
            assert generator in target, f"`make lint-docs` does not run {generator}"


class TestNothingHasDrifted:
    @pytest.mark.parametrize("generator", GENERATORS)
    def test_the_generator_reports_no_drift(self, run_shell, generator):
        flag = "" if generator.endswith("check-type-parity.py") else " --check"
        result = run_shell(f"python3 {ROOT / generator}{flag}", cwd=ROOT)
        assert result.returncode == 0, result
