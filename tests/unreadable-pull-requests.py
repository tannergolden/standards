# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""A pull request list the API refuses must not fail the run that asks for it.

A repository can turn pull requests off. Its API then answers 404 for every
pull request, Dependabot's included, though Dependabot still opens them and
`pull_request_target` still fires for each. Two jobs failed on that answer
in every repository set up this way:

- governance.yml's triage: the size labeler stopped the job on the 404,
  and the failure step blamed the labeler config or the token.
- release-notes.yml, and release-publish.yml after it: the shared changelog
  thanks contributors by GitHub username, git-cliff reads them through the
  pull request list, and it stops the whole draft when the list is refused.
  A private repository refuses it too, with a 403, because neither job asks
  for a pull-request scope: asking would fail every caller that grants none,
  at startup.

Each job now asks the API one question first. Triage skips its labels with
a warning that names the cause, but only on a 404: any other error still
reaches the labeling steps, which report it. The release jobs run git-cliff
offline, which keeps everything but the names, and the template leaves out
the thanks when there is no one to thank.
"""

from __future__ import annotations

import pytest
import tomllib
from conftest import ROOT, load_yaml, workflow_step_shell

GOVERNANCE = ".github/workflows/governance.yml"
RELEASE_JOBS = [
    (".github/workflows/release-notes.yml", "changelog"),
    (".github/workflows/release-publish.yml", "release"),
]
GATED = "${{ steps.readable.outputs.readable == 'true' }}"


def ask_for_the_list(run_shell, fake_gh, rel, job, answer, code):
    fake_gh.route("pulls?state=closed&per_page=1", answer, code)
    return run_shell(
        workflow_step_shell(rel, job, "remote"),
        env=fake_gh.env(GH_TOKEN="token", REPO="owner/repo"),
    )


def ask_for_the_pull_request(run_shell, fake_gh, answer, code):
    fake_gh.route("repos/owner/repo/pulls/7", answer, code)
    return run_shell(
        workflow_step_shell(GOVERNANCE, "triage", "readable"),
        env=fake_gh.env(GH_TOKEN="token", REPO="owner/repo", NUMBER="7"),
    )


@pytest.mark.parametrize(("rel", "job"), RELEASE_JOBS)
class TestTheReleaseJobsDraftWithoutTheList:
    def test_a_readable_list_keeps_git_cliff_online(self, run_shell, fake_gh, rel, job):
        result = ask_for_the_list(run_shell, fake_gh, rel, job, "[]", 0)
        assert result.returncode == 0, result
        assert result.outputs == {"offline": ""}, result.outputs
        assert "::notice" not in result.output

    @pytest.mark.parametrize(
        ("answer", "status"),
        [
            ("gh: Not Found (HTTP 404)", "HTTP 404"),
            ("gh: Resource not accessible by integration (HTTP 403)", "HTTP 403"),
        ],
    )
    def test_a_refused_list_runs_git_cliff_offline(
        self, run_shell, fake_gh, rel, job, answer, status
    ):
        """The defect: git-cliff stopped the whole draft over the names."""
        result = ask_for_the_list(run_shell, fake_gh, rel, job, answer, 1)
        assert result.returncode == 0, result
        assert result.outputs == {"offline": "--offline"}, result.outputs
        assert "::notice" in result.output and status in result.output, result.output

    def test_every_git_cliff_run_follows_the_question(self, rel, job):
        """A git-cliff step added later must not reach for the list unasked."""
        steps = load_yaml(rel)["jobs"][job]["steps"]
        asked = [s.get("id") for s in steps].index("remote")
        runs = [(i, s) for i, s in enumerate(steps) if "git-cliff-action" in s.get("uses", "")]
        assert runs, f"{rel}: no git-cliff step found"
        for i, step in runs:
            assert i > asked, f"{rel}: {step['name']} runs before the list is asked for"
            assert "${{ steps.remote.outputs.offline }}" in step["with"]["args"], (
                f"{rel}: {step['name']} ignores the answer, and stops on a refused list"
            )


class TestTriageOfAnUnreadablePullRequest:
    def test_a_readable_pull_request_is_labeled(self, run_shell, fake_gh):
        result = ask_for_the_pull_request(run_shell, fake_gh, '{"number": 7}', 0)
        assert result.returncode == 0, result
        assert result.outputs == {"readable": "true"}, result.outputs
        assert "::warning" not in result.output

    def test_a_404_skips_the_labels_and_names_the_cause(self, run_shell, fake_gh):
        """The defect: the size labeler failed the job on the 404."""
        result = ask_for_the_pull_request(run_shell, fake_gh, "gh: Not Found (HTTP 404)", 1)
        assert result.returncode == 0, result
        assert result.outputs == {"readable": "false"}, result.outputs
        assert "::warning" in result.output, result.output
        assert "turned off" in result.output

    @pytest.mark.parametrize(
        "answer",
        [
            "gh: Resource not accessible by integration (HTTP 403)",
            "gh: Server Error (HTTP 502)",
            "gh: API rate limit exceeded (HTTP 429)",
            "error connecting to api.github.com",
        ],
    )
    def test_any_other_error_still_reaches_the_labeling_steps(self, run_shell, fake_gh, answer):
        """Only a 404 means the pull request is hidden; the rest must still fail loudly."""
        result = ask_for_the_pull_request(run_shell, fake_gh, answer, 1)
        assert result.returncode == 0, result
        assert result.outputs == {"readable": "true"}, result.outputs
        assert "::warning" not in result.output

    def test_every_labeling_step_waits_on_the_answer(self):
        steps = load_yaml(GOVERNANCE)["jobs"]["triage"]["steps"]
        asked = [s.get("id") for s in steps].index("readable")
        assert "checkout" in steps[asked + 1].get("uses", ""), (
            "the question must come before the checkout, so a hidden pull request costs no clone"
        )
        for step in steps[asked + 1 :]:
            if step.get("if") == "${{ failure() }}":
                continue
            assert step.get("if") == GATED, f"{step['name']} runs on a pull request it cannot read"


class TestTheThanksNeedsSomeoneToThank:
    def test_the_contributor_section_sits_inside_the_guard(self):
        """Offline, git-cliff has no names, and the heading would thank no one."""
        body = tomllib.loads((ROOT / "config/cliff.toml").read_text(encoding="utf-8"))[
            "changelog"
        ]["body"]
        opened = body.index("{%- if github.contributors | length > 0 %}")
        closed = body.index("{%- endif %}", opened)
        for part in ("---", "### 👥 Contributors", "{% for contributor in github.contributors %}"):
            at = body.index(part, opened)
            assert opened < at < closed, f"{part!r} is outside the guard"
