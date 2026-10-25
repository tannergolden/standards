# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""A private repository's pull request is scanned without the pull request API.

On `pull_request` the pinned gitleaks action lists the pull request's commits
through the API before it scans anything, and a private repository answers
that only to a token holding `pull-requests: read`. The scan job does not
hold it, so the required secret scan failed every pull request in every
private repository with a 403. Asking for the scope would instead fail, at
startup, every stub that does not grant it, so a private repository's pull
request is scanned from the checkout by the same gitleaks, pinned by hash.
"""

from __future__ import annotations

import re

from conftest import load_yaml

GITLEAKS = ".github/workflows/gitleaks.yml"
PREFLIGHT = "steps.preflight.outputs.scan == 'true'"
PRIVATE_PULL_REQUEST = "github.event_name == 'pull_request' && github.event.repository.private"


def steps() -> list[dict]:
    return load_yaml(GITLEAKS)["jobs"]["scan"]["steps"]


def the_action() -> dict:
    return next(step for step in steps() if "gitleaks/gitleaks-action@" in str(step.get("uses", "")))


def the_binary() -> dict:
    return next(step for step in steps() if '"${RUNNER_TEMP}/gitleaks" git' in str(step.get("run", "")))


class TestAPrivatePullRequest:
    def test_the_job_asks_for_no_pull_request_scope(self):
        """A scope the stubs do not grant would fail every one of them at startup."""
        assert load_yaml(GITLEAKS)["jobs"]["scan"]["permissions"] == {"contents": "read", "issues": "write"}

    def test_the_action_never_scans_one(self):
        """The defect: the action's commit listing was refused with a 403."""
        assert the_action()["if"].replace(" ", "") == "${{" + f"{PREFLIGHT}&&!({PRIVATE_PULL_REQUEST})".replace(" ", "") + "}}"

    def test_the_binary_scans_one_and_nothing_else(self):
        assert the_binary()["if"].replace(" ", "") == "${{" + f"{PREFLIGHT}&&{PRIVATE_PULL_REQUEST}".replace(" ", "") + "}}"

    def test_the_binary_is_pinned_by_hash(self):
        env = the_binary()["env"]
        assert re.fullmatch(r"\d+\.\d+\.\d+", env["GITLEAKS_VERSION"])
        assert re.fullmatch(r"[0-9a-f]{64}", env["GITLEAKS_SHA256"])
        run = the_binary()["run"]
        assert "sha256sum --check --strict" in run
        assert run.index("sha256sum --check") < run.index("tar -xzf"), "the tarball is unpacked before it is verified"

    def test_the_binary_scans_the_pull_requests_own_commits(self):
        binary = the_binary()
        assert binary["env"]["BASE_SHA"] == "${{ github.event.pull_request.base.sha }}"
        assert binary["env"]["HEAD_SHA"] == "${{ github.event.pull_request.head.sha }}"
        assert "--first-parent ${BASE_SHA}..${HEAD_SHA}" in binary["run"]
        assert "--exit-code 2" in binary["run"], "a finding must fail the step, as it fails the action"
        assert "--redact" in binary["run"], "a finding must never print the secret itself"

    def test_the_failure_report_still_follows_both(self):
        report = next(step for step in steps() if step.get("name") == "📝 Report Failure")
        assert steps().index(report) > steps().index(the_binary()) > steps().index(the_action())
