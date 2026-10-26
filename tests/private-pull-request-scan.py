# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Every event is scanned by the toolchain's gitleaks, without the pull request API.

On `pull_request` gitleaks-action listed the pull request's commits through
the API before it scanned anything, and a private repository answers that
only to a token holding `pull-requests: read`. The scan job does not hold
it, so the required secret scan failed every pull request in every private
repository with a 403, and asking for the scope would instead fail, at
startup, every stub that does not grant it. The scan now runs the
environment's gitleaks itself, on the commits the event names, for public
and private repositories alike. These read the step as written, then run it
with a gitleaks that records what it was asked to scan.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess

import pytest
from conftest import load_yaml, requires, workflow_step_shell

GITLEAKS = ".github/workflows/gitleaks.yml"
SCAN = "🔍 Run Gitleaks"

# A stand-in for gitleaks: it writes every argument it was given, one a
# line, and a report where --report-path says, with one finding when
# FAKE_FINDING is set, exiting 2 as gitleaks does with --exit-code 2.
FAKE_GITLEAKS = """#!/usr/bin/env bash
printf '%s\\n' "$@" > "$GITLEAKS_ARGS"
report=""
while [ $# -gt 0 ]; do
  [ "$1" = --report-path ] && report="$2"
  shift
done
if [ -n "${FAKE_FINDING:-}" ]; then
  printf '[{"RuleID":"generic-api-key","File":"app.env","StartLine":3,"Commit":"0123456789abcdef0123"}]' > "$report"
  exit 2
fi
printf '[]' > "$report"
"""


def steps() -> list[dict]:
    return load_yaml(GITLEAKS)["jobs"]["scan"]["steps"]


def the_scan() -> dict:
    return next(step for step in steps() if step.get("name") == SCAN)


class TestTheScanAsWritten:
    def test_the_job_asks_for_no_pull_request_scope(self):
        """A scope the stubs do not grant would fail every one of them at startup."""
        assert load_yaml(GITLEAKS)["jobs"]["scan"]["permissions"] == {"contents": "read", "issues": "write"}

    def test_no_step_calls_the_action(self):
        """The defect: the action's commit listing was refused with a 403."""
        assert not any("gitleaks/gitleaks-action" in str(step.get("uses", "")) for step in steps())

    def test_gitleaks_comes_from_the_toolchain_before_the_scan(self):
        uses = [str(step.get("uses", "")) for step in steps()]
        toolchain = next(i for i, u in enumerate(uses) if u.startswith("tannergolden/environment/.github/actions/toolchain@"))
        assert toolchain < steps().index(the_scan())
        assert "curl" not in the_scan()["run"], "the scan downloads a gitleaks of its own, outside the pins"

    def test_a_pull_request_names_its_own_commits(self):
        scan = the_scan()
        assert scan["env"]["BASE_SHA"] == "${{ github.event.pull_request.base.sha }}"
        assert scan["env"]["HEAD_SHA"] == "${{ github.event.pull_request.head.sha }}"

    def test_the_failure_report_follows(self):
        report = next(step for step in steps() if step.get("name") == "📝 Report Failure")
        assert steps().index(report) > steps().index(the_scan())


def commit(repo, message: str) -> str:
    (repo / "change.txt").write_text(message, encoding="utf-8")
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull}
    subprocess.run(["git", "add", "-A"], cwd=repo, env=env, check=True)
    subprocess.run(["git", "commit", "-q", "-m", f"chore(test): 🌱 {message}", "--no-gpg-sign"], cwd=repo, env=env, check=True)
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()


@requires("jq")
class TestTheScanAsRun:
    @pytest.fixture
    def scan(self, run_shell, git_repo, tmp_path):
        bin_dir = tmp_path / "_bin"
        bin_dir.mkdir()
        tool = bin_dir / "gitleaks"
        tool.write_text(FAKE_GITLEAKS, encoding="utf-8")
        tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
        args_file = tmp_path / "_gitleaks_args"

        def _scan(event: str, payload: dict | None = None, **env: str):
            event_path = tmp_path / "_event.json"
            event_path.write_text(json.dumps(payload or {}), encoding="utf-8")
            result = run_shell(
                workflow_step_shell(GITLEAKS, "scan", SCAN),
                cwd=git_repo,
                env={
                    "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
                    "EVENT": event,
                    "GITHUB_EVENT_PATH": str(event_path),
                    "GITLEAKS_ARGS": str(args_file),
                    "BASE_SHA": "",
                    "HEAD_SHA": "",
                    **env,
                },
            )
            args = args_file.read_text(encoding="utf-8").splitlines() if args_file.exists() else None
            return result, args

        return _scan

    def test_a_pull_request_scans_from_its_base_to_its_head(self, scan):
        result, args = scan("pull_request", BASE_SHA="aaa", HEAD_SHA="bbb")
        assert result.returncode == 0, result
        assert "--log-opts=--no-merges --first-parent aaa..bbb" in args

    def test_a_push_scans_its_own_commits(self, scan, git_repo):
        first, last = commit(git_repo, "first"), commit(git_repo, "last")
        result, args = scan("push", {"commits": [{"id": first}, {"id": last}]})
        assert result.returncode == 0, result
        assert f"--log-opts=--no-merges --first-parent {first}^..{last}" in args

    def test_a_push_that_starts_the_repository_has_no_parent_to_count_from(self, scan, git_repo):
        seed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=git_repo, capture_output=True, text=True, check=True).stdout.strip()
        result, args = scan("push", {"commits": [{"id": seed}]})
        assert result.returncode == 0, result
        assert f"--log-opts=--no-merges --first-parent {seed}" in args

    def test_a_push_without_commits_scans_nothing(self, scan):
        result, args = scan("push", {"commits": []})
        assert result.returncode == 0, result
        assert args is None, "gitleaks ran for a push with nothing in it"

    @pytest.mark.parametrize("event", ["workflow_dispatch", "schedule"])
    def test_a_dispatch_or_the_schedule_scans_the_whole_history(self, scan, event):
        result, args = scan(event)
        assert result.returncode == 0, result
        assert not any(arg.startswith("--log-opts") for arg in args)

    def test_an_event_it_does_not_know_fails(self, scan):
        result, args = scan("release")
        assert result.returncode == 1
        assert "::error" in result.output
        assert args is None

    def test_a_finding_fails_never_shows_the_secret_and_is_summarized(self, scan):
        result, args = scan("schedule", FAKE_FINDING="1")
        assert result.returncode == 2, "a finding must fail the required check"
        assert "--redact" in args, "a finding must never print the secret itself"
        assert "--exit-code" in args and args[args.index("--exit-code") + 1] == "2"
        for part in ("generic-api-key", "`app.env`", "| 3 |", "`0123456789ab`"):
            assert part in result.summary, result.summary

    def test_a_clean_scan_says_so(self, scan):
        result, _ = scan("schedule")
        assert result.returncode == 0, result
        assert "found no secrets" in result.summary
