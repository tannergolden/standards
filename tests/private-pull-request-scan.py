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
and private repositories alike.

It also stopped following first parents only, which skipped every commit a
pull request merged in from another branch, and it scans a pull request
with its base's allowlist, so a pull request cannot allow its own secret.
These read the step as written, run it with a gitleaks that records what it
was asked to scan, and, where the runner has one, with the real gitleaks.
"""

from __future__ import annotations

import json
import os
import secrets
import stat
import string
import subprocess

import pytest
from conftest import load_yaml, requires, workflow_step_shell

GITLEAKS = ".github/workflows/gitleaks.yml"
SCAN = "🔍 Run Gitleaks"
NONE = "0" * 40

# A stand-in for gitleaks: it writes every argument it was given, one a
# line, and a report where --report-path says, with one finding when
# FAKE_FINDING is set, exiting 2 as gitleaks does with --exit-code 2. It
# refuses anything but a `git` scan of the checkout with a JSON report, so
# a scan that stops asking for one fails here rather than passing.
FAKE_GITLEAKS = """#!/usr/bin/env bash
printf '%s\\n' "$@" > "$GITLEAKS_ARGS"
[ "$1" = git ] && [ "${!#}" = . ] || { echo "fake gitleaks: not a git scan of the checkout: $*" >&2; exit 64; }
report="" format=""
while [ $# -gt 0 ]; do
  case "$1" in
    --report-path) report="$2" ;;
    --report-format) format="$2" ;;
  esac
  shift
done
[ -n "$report" ] && [ "$format" = json ] || { echo "fake gitleaks: no JSON report asked for" >&2; exit 64; }
if [ -n "${FAKE_FINDING:-}" ]; then
  printf '[{"RuleID":"generic-api-key","File":"app.env","StartLine":3,"Commit":"0123456789abcdef0123"}]' > "$report"
  exit 2
fi
printf '[]' > "$report"
"""


def steps() -> list[dict]:
    return load_yaml(GITLEAKS)["jobs"]["scan"]["steps"]


def step(name: str) -> dict:
    return next(entry for entry in steps() if entry.get("name") == name)


def the_scan() -> dict:
    return step(SCAN)


def fake_token() -> str:
    """A token gitleaks recognizes, made here, so no file in this repository holds one."""
    alphabet = string.ascii_letters + string.digits
    return "ghp_" + "".join(secrets.choice(alphabet) for _ in range(36))


class TestTheScanAsWritten:
    def test_the_job_asks_for_no_pull_request_scope(self):
        """A scope the stubs do not grant would fail every one of them at startup."""
        assert load_yaml(GITLEAKS)["jobs"]["scan"]["permissions"] == {"contents": "read", "issues": "write"}

    def test_no_step_calls_the_action(self):
        """The defect: the action's commit listing was refused with a 403."""
        assert not any("gitleaks/gitleaks-action" in str(entry.get("uses", "")) for entry in steps())

    def test_gitleaks_comes_from_the_toolchain_before_the_scan(self):
        uses = [str(entry.get("uses", "")) for entry in steps()]
        toolchain = next(i for i, u in enumerate(uses) if u.startswith("tannergolden/environment/.github/actions/toolchain@"))
        assert toolchain < steps().index(the_scan())
        assert "curl" not in the_scan()["run"], "the scan downloads a gitleaks of its own, outside the pins"

    def test_the_required_check_waits_only_on_the_binaries(self):
        """PyPI or npm being down must not hold up every pull request's required check."""
        toolchain = next(entry for entry in steps() if str(entry.get("uses", "")).startswith("tannergolden/environment/"))
        assert toolchain.get("with", {}).get("tools") == "binaries"

    def test_the_checkout_holds_the_whole_history(self):
        """A range is only as good as the commits the checkout holds."""
        checkout = next(entry for entry in steps() if str(entry.get("uses", "")).startswith("actions/checkout@"))
        assert checkout["with"]["fetch-depth"] == 0

    def test_each_event_names_its_own_commits(self):
        env = the_scan()["env"]
        assert env["BASE_SHA"] == "${{ github.event.pull_request.base.sha }}"
        assert env["HEAD_SHA"] == "${{ github.event.pull_request.head.sha }}"
        assert env["BEFORE"] == "${{ github.event.before }}"
        assert env["AFTER"] == "${{ github.event.after }}"

    def test_no_range_follows_first_parents_only(self):
        """The defect: a commit merged in from another branch was never scanned."""
        assert "--first-parent" not in the_scan()["run"]

    def test_the_failure_report_follows(self):
        assert steps().index(step("📝 Report Failure")) > steps().index(the_scan())


def git(repo, *args: str) -> str:
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull}
    return subprocess.run(["git", *args], cwd=repo, env=env, capture_output=True, text=True, check=True).stdout.strip()


def commit(repo, message: str, files: dict[str, str] | None = None) -> str:
    for name, text in (files or {"change.txt": message}).items():
        (repo / name).write_text(text, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", f"chore(test): 🌱 {message}", "--no-gpg-sign")
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def scan_with(run_shell, git_repo, tmp_path):
    """Runs the scan step in the test repository, with whichever gitleaks PATH finds first."""

    def _scan(event: str, payload: dict | None = None, **env: str):
        event_path = tmp_path / "_event.json"
        event_path.write_text(json.dumps(payload or {}), encoding="utf-8")
        return run_shell(
            workflow_step_shell(GITLEAKS, "scan", SCAN),
            cwd=git_repo,
            env={
                "EVENT": event,
                "GITHUB_EVENT_PATH": str(event_path),
                "BASE_SHA": "",
                "HEAD_SHA": "",
                "BEFORE": "",
                "AFTER": "",
                **env,
            },
        )

    return _scan


@requires("jq")
class TestTheScanAsRun:
    @pytest.fixture
    def scan(self, scan_with, tmp_path):
        bin_dir = tmp_path / "_bin"
        bin_dir.mkdir()
        tool = bin_dir / "gitleaks"
        tool.write_text(FAKE_GITLEAKS, encoding="utf-8")
        tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
        args_file = tmp_path / "_gitleaks_args"

        def _scan(event: str, payload: dict | None = None, **env: str):
            result = scan_with(
                event,
                payload,
                PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
                GITLEAKS_ARGS=str(args_file),
                **env,
            )
            args = args_file.read_text(encoding="utf-8").splitlines() if args_file.exists() else None
            return result, args

        return _scan

    def test_the_command_is_a_redacted_scan_that_fails_on_a_finding(self, scan, tmp_path):
        result, args = scan("schedule")
        assert result.returncode == 0, result
        report = str(tmp_path / "_runner_temp" / "gitleaks.json")
        assert args == ["git", "--redact", "--verbose", "--exit-code", "2",
                        "--report-format", "json", "--report-path", report, "."]

    def test_a_pull_request_scans_from_its_base_to_its_head(self, scan):
        result, args = scan("pull_request", BASE_SHA="aaa", HEAD_SHA="bbb")
        assert result.returncode == 0, result
        assert "--log-opts=--no-merges aaa..bbb" in args

    def test_a_pull_request_is_scanned_with_its_bases_allowlist(self, scan, git_repo):
        base = commit(git_repo, "the base's allowlist", {".gitleaksignore": "from-the-base\n"})
        head = commit(git_repo, "the pull request's own", {
            ".gitleaksignore": "from-the-pull-request\n",
            ".gitleaks.toml": "[allowlist]\npaths = ['''.*''']\n",
        })
        result, args = scan("pull_request", BASE_SHA=base, HEAD_SHA=head)
        assert result.returncode == 0, result
        assert (git_repo / ".gitleaksignore").read_text(encoding="utf-8") == "from-the-base\n"
        assert not (git_repo / ".gitleaks.toml").exists(), "the pull request's own config was scanned with"
        assert f"--log-opts=--no-merges {base}..{head}" in args

    def test_a_push_scans_from_where_the_branch_was(self, scan, git_repo):
        before = git(git_repo, "rev-parse", "HEAD")
        commit(git_repo, "first")
        after = commit(git_repo, "last")
        result, args = scan("push", {"commits": [{"id": after}]}, BEFORE=before, AFTER=after)
        assert result.returncode == 0, result
        assert f"--log-opts=--no-merges {before}..{after}" in args

    def test_a_new_branch_scans_from_its_first_commit(self, scan, git_repo):
        first, last = commit(git_repo, "first"), commit(git_repo, "last")
        result, args = scan("push", {"commits": [{"id": first}, {"id": last}]}, BEFORE=NONE, AFTER=last)
        assert result.returncode == 0, result
        assert f"--log-opts=--no-merges {first}^..{last}" in args

    def test_a_force_push_from_a_commit_no_branch_holds_scans_from_its_first(self, scan, git_repo):
        first, last = commit(git_repo, "first"), commit(git_repo, "last")
        gone = "1234567890abcdef1234567890abcdef12345678"
        result, args = scan("push", {"commits": [{"id": first}, {"id": last}]}, BEFORE=gone, AFTER=last)
        assert result.returncode == 0, result
        assert f"--log-opts=--no-merges {first}^..{last}" in args

    def test_a_push_that_starts_the_repository_has_no_parent_to_count_from(self, scan, git_repo):
        seed = git(git_repo, "rev-parse", "HEAD")
        result, args = scan("push", {"commits": [{"id": seed}]}, BEFORE=NONE, AFTER=seed)
        assert result.returncode == 0, result
        assert f"--log-opts=--no-merges {seed}" in args

    def test_a_new_branch_without_new_commits_scans_nothing(self, scan, git_repo):
        tip = git(git_repo, "rev-parse", "HEAD")
        result, args = scan("push", {"commits": []}, BEFORE=NONE, AFTER=tip)
        assert result.returncode == 0, result
        assert args is None, "gitleaks ran for a push with nothing new in it"

    def test_a_push_that_deletes_its_branch_scans_nothing(self, scan, git_repo):
        tip = git(git_repo, "rev-parse", "HEAD")
        result, args = scan("push", {"commits": []}, BEFORE=tip, AFTER=NONE)
        assert result.returncode == 0, result
        assert args is None

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

    def test_a_finding_fails_and_is_summarized(self, scan):
        result, _ = scan("schedule", FAKE_FINDING="1")
        assert result.returncode == 2, "a finding must fail the required check"
        for part in ("generic-api-key", "`app.env`", "| 3 |", "`0123456789ab`"):
            assert part in result.summary, result.summary

    def test_a_clean_scan_says_so(self, scan):
        result, _ = scan("schedule")
        assert result.returncode == 0, result
        assert "found no secrets" in result.summary


@requires("gitleaks")
@requires("jq")
class TestTheScanWithTheRealGitleaks:
    """The flags and ranges above, as the gitleaks the toolchain pins reads them."""

    def test_a_secret_merged_in_from_another_branch_is_found_and_never_shown(self, scan_with, git_repo):
        token = fake_token()
        base = git(git_repo, "rev-parse", "HEAD")
        git(git_repo, "checkout", "-q", "-b", "side")
        commit(git_repo, "a token on a side branch", {"config.env": f"TOKEN={token}\n"})
        git(git_repo, "checkout", "-q", "-b", "feature", base)
        commit(git_repo, "the pull request's own change")
        git(git_repo, "merge", "-q", "--no-ff", "--no-edit", "side")
        head = git(git_repo, "rev-parse", "HEAD")

        result = scan_with("pull_request", BASE_SHA=base, HEAD_SHA=head)
        assert result.returncode == 2, result
        assert "github-pat" in result.summary and "`config.env`" in result.summary, result.summary
        assert token not in result.output and token not in result.summary

    def test_a_pull_request_cannot_allow_its_own_secret(self, scan_with, git_repo):
        base = git(git_repo, "rev-parse", "HEAD")
        leak = commit(git_repo, "a token", {"config.env": f"TOKEN={fake_token()}\n"})
        commit(git_repo, "and an allowlist entry for it", {".gitleaksignore": f"{leak}:config.env:github-pat:1\n"})
        head = git(git_repo, "rev-parse", "HEAD")
        # The entry is real: gitleaks run on the pull request's own checkout
        # honours it.
        honoured = subprocess.run(
            ["gitleaks", "git", "--no-banner", "--exit-code", "2", f"--log-opts={base}..{head}", "."],
            cwd=git_repo, capture_output=True, text=True,
        )
        assert honoured.returncode == 0, honoured.stdout + honoured.stderr

        result = scan_with("pull_request", BASE_SHA=base, HEAD_SHA=head)
        assert result.returncode == 2, "the pull request's own allowlist hid its secret"

    def test_a_push_scans_what_it_added(self, scan_with, git_repo):
        before = git(git_repo, "rev-parse", "HEAD")
        after = commit(git_repo, "a token", {"config.env": f"TOKEN={fake_token()}\n"})
        result = scan_with("push", {"commits": [{"id": after}]}, BEFORE=before, AFTER=after)
        assert result.returncode == 2, result

    def test_a_clean_pull_request_passes(self, scan_with, git_repo):
        base = git(git_repo, "rev-parse", "HEAD")
        head = commit(git_repo, "nothing secret")
        result = scan_with("pull_request", BASE_SHA=base, HEAD_SHA=head)
        assert result.returncode == 0, result
        assert "found no secrets" in result.summary
