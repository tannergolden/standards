# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Every required check passes on a merge group, where there is no pull request.

A merge queue asks every required check to report on the merge group as
well as on the pull request, so the template's stubs behind all three now
trigger on `merge_group`. The gitleaks action the scan ran then took push,
pull_request, workflow_dispatch and schedule and exited 1 on anything else,
as the scan that replaced it still does, so on `merge_group` the required
secret scan failed every queued pull request. The scan is skipped there
instead: GitHub reports a job skipped inside a called workflow as Success,
which a required check accepts, and only a skipped CALLER job leaves the
check unreported.

The sign-off check moved from `pull_request_target` to `pull_request` with
the same change, since it only reads through the API, and on a merge group
every one of its checks skips the same way.
"""

from __future__ import annotations

import re

import yaml
from conftest import ROOT, load_yaml, workflow_on

GITLEAKS = ".github/workflows/gitleaks.yml"
SEMANTIC = ".github/workflows/semantic-pr.yml"
CI = ".github/workflows/ci.yml"
NEEDS_A_PULL_REQUEST = "github.event.pull_request.number"


def header(rel: str) -> str:
    """The commented header of a workflow, its stub included."""
    return (ROOT / rel).read_text(encoding="utf-8").split("\n---\n", 1)[0]


def stub(rel: str) -> dict:
    """The stub shown in a workflow's header, parsed as the YAML a consumer copies."""
    lines = header(rel).splitlines()
    start = next(i for i, line in enumerate(lines) if line.rstrip().endswith("adds a stub:"))
    body: list[str] = []
    for line in lines[start + 1:]:
        if line.startswith("#   "):
            body.append(line[4:])
        elif body:
            break
    return yaml.safe_load("\n".join(body))


class TestTheSecretScan:
    def test_it_is_skipped_on_a_merge_group_and_nowhere_else(self):
        """The defect: gitleaks exited 1 on `merge_group`, failing the required check."""
        condition = load_yaml(GITLEAKS)["jobs"]["scan"]["if"]
        assert condition.replace(" ", "") == "${{github.event_name!='merge_group'}}"

    def test_the_check_keeps_its_name(self):
        assert load_yaml(GITLEAKS)["jobs"]["scan"]["name"] == "🔍 Scan for Secrets"

    def test_its_stub_triggers_on_a_merge_group(self):
        assert re.search(r"^#\s+merge_group:", header(GITLEAKS), re.M), (
            "the stub shown in gitleaks.yml's header never reports to a merge queue"
        )


class TestTheSignOffCheck:
    def test_its_stub_runs_on_pull_request_and_merge_group(self):
        """It reads only through the API, so the read-only token of `pull_request` is enough."""
        on = workflow_on(stub(SEMANTIC))
        assert set(on) == {"pull_request", "merge_group"}
        assert on["pull_request"]["types"] == ["opened", "edited", "synchronize", "reopened"]

    def test_every_check_in_it_waits_for_a_pull_request(self):
        """A merge group carries none, so each check skips there, and a skipped job passes."""
        for job_id, job in load_yaml(SEMANTIC)["jobs"].items():
            if NEEDS_A_PULL_REQUEST in str(job.get("if", "")):
                continue
            checks = [
                step for step in job["steps"]
                if "/actions/harden@" not in str(step.get("uses", "")) and "failure()" not in str(step.get("if", ""))
            ]
            assert checks, f"{job_id} checks nothing"
            assert all(NEEDS_A_PULL_REQUEST in str(step.get("if", "")) for step in checks), (
                f"{job_id} runs a check on an event with no pull request, which a merge group is"
            )

    def test_the_required_check_keeps_its_name(self):
        assert load_yaml(SEMANTIC)["jobs"]["dco"]["name"] == "✍️ DCO Sign-Off"


class TestTheBuildCheck:
    def test_its_stub_triggers_on_a_merge_group(self):
        assert "merge_group" in workflow_on(stub(CI))
