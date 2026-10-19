# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Every `make` target probe finds a target that is there, under the shell
Actions runs it with.

The probe asks make for its own database, `make -np`, and greps it for the
target. Under pipefail, which `shell: bash` turns on and a step can turn on
with `set -o pipefail`, two things make that pipeline lie. `grep -q` stops
reading at its first match, so make dies writing the rest of its database;
and a dry run whose default goal cannot be made exits non-zero on its own.
Either read a declared target as missing, and the step went on as if it
were absent: `.github/actions/setup` never ran `make setup`, and
`publish-package.yml` would publish a package without running `make build`.

So every probing step is found by its text rather than listed, and runs
under the shell its own file gives it.
"""

from __future__ import annotations

import re

import pytest
from conftest import ROOT, load_yaml, workflow_step_shell

PROBE = re.compile(r"make -np\b.*?\|\s*grep -qE '\^(?P<target>[A-Za-z0-9_.-]+):'")


def _run_steps():
    files = sorted(ROOT.glob(".github/workflows/*.yml")) + sorted(ROOT.glob(".github/actions/*/action.yml"))
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        doc = load_yaml(rel)
        if "runs" in doc:  # a composite action
            groups = {None: doc["runs"].get("steps") or []}
        else:
            groups = {job: spec.get("steps") or [] for job, spec in (doc.get("jobs") or {}).items()}
        for job, steps in groups.items():
            for step in steps:
                if "run" in step:
                    yield rel, job, step


def _code(run: str) -> str:
    """A `run:` block without its comment lines, which may quote the probe."""
    return "\n".join(line for line in run.splitlines() if not line.lstrip().startswith("#"))


SITES = [
    pytest.param(rel, job, step.get("id") or step["name"], m["target"], id=f"{rel}:{m['target']}")
    for rel, job, step in _run_steps()
    for m in PROBE.finditer(_code(step["run"]))
]


def test_every_make_database_probe_is_covered():
    """A probe written in a form the pattern misses must fail here, rather
    than drop out of the tests below without anyone noticing."""
    written = sum(_code(step["run"]).count("make -np") for _, _, step in _run_steps())
    assert written == len(SITES), f"{written} `make -np` probes, {len(SITES)} recognized"
    found = {(param.values[0], param.values[3]) for param in SITES}
    assert (".github/actions/setup/action.yml", "setup") in found
    assert (".github/workflows/publish-package.yml", "build") in found


@pytest.mark.parametrize(("rel", "job", "step", "target"), SITES)
class TestEveryProbeFindsADeclaredTarget:
    def test_runs_a_declared_target(self, run_shell, tmp_path, rel, job, step, target):
        """The defect: under pipefail an ordinary Makefile read as having no
        such target, because make was still writing when grep stopped."""
        (tmp_path / "Makefile").write_text(
            f"all:\n\t@true\n\n{target}:\n\t@echo ran-{target}\n", encoding="utf-8"
        )
        result = run_shell(workflow_step_shell(rel, job, step), cwd=tmp_path, env={"COMMAND": ""})
        assert result.returncode == 0, result
        assert f"ran-{target}" in result.stdout, result

    def test_runs_it_when_the_default_goal_cannot_be_made(
        self, run_shell, tmp_path, rel, job, step, target
    ):
        """`-n` dry-runs the default goal, and make exits non-zero when that
        goal cannot be made, though the database it printed still declares
        the target. This fails the same way on every run, not by timing."""
        (tmp_path / "Makefile").write_text(
            f"all: no-such-input\n\n{target}:\n\t@echo ran-{target}\n", encoding="utf-8"
        )
        result = run_shell(workflow_step_shell(rel, job, step), cwd=tmp_path, env={"COMMAND": ""})
        assert result.returncode == 0, result
        assert f"ran-{target}" in result.stdout, result

    def test_skips_a_target_that_is_not_declared(self, run_shell, tmp_path, rel, job, step, target):
        """Answering through grep alone must not make every target look declared."""
        (tmp_path / "Makefile").write_text("all:\n\t@true\n\nother:\n\t@true\n", encoding="utf-8")
        result = run_shell(workflow_step_shell(rel, job, step), cwd=tmp_path, env={"COMMAND": ""})
        assert result.returncode == 0, result
        assert f"ran-{target}" not in result.output
        assert "No rule to make target" not in result.output
