# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""A major update in any commit of a Dependabot pull request holds all of it.

dependabot/fetch-metadata reads the head commit's first metadata block
alone. A pull request from a multi-ecosystem group, the one a month that
covers every ecosystem a repository has, can carry more than one block, so a
major in any other passed as the head's patch, and was approved and queued
to merge with it. The automerge job now reads every commit's message before
it approves anything, and goes ahead only on an explicit `false`: a list it
could not read approves nothing.
"""

from __future__ import annotations

import json

from conftest import load_yaml, workflow_step_shell

AUTOMERGE = ".github/workflows/dependabot-automerge.yml"
JOB = "dependabot"


def message(*updates: tuple[str, str]) -> str:
    """A Dependabot commit message, its metadata block in the shape it writes."""
    rows = "".join(
        f"- dependency-name: {name}\n"
        "  dependency-version: 2.0.0\n"
        "  dependency-type: direct:production\n"
        f"  update-type: version-update:semver-{level}\n"
        for name, level in updates
    )
    return (
        "build(deps): bump the dependencies group with 2 updates\n\n"
        f"---\nupdated-dependencies:\n{rows}...\n\n"
        "Signed-off-by: dependabot[bot] <support@github.com>\n"
    )


def check(run_shell, fake_gh, answer: str, update_type: str = "", code: int = 0):
    fake_gh.route("repos/owner/repo/pulls/7/commits", answer, code)
    return run_shell(
        workflow_step_shell(AUTOMERGE, JOB, "major"),
        env=fake_gh.env(
            GH_TOKEN="token", REPO="owner/repo", PR_NUMBER="7", UPDATE_TYPE=update_type
        ),
    )


def commits(*messages: str) -> str:
    return json.dumps([{"commit": {"message": text}} for text in messages])


def step(named: str) -> dict:
    steps = load_yaml(AUTOMERGE)["jobs"][JOB]["steps"]
    return next(s for s in steps if named in s.get("name", ""))


class TestEveryCommitIsRead:
    def test_a_major_behind_the_head_commit_holds_the_pull_request(self, run_shell, fake_gh):
        """The defect: the head's patch was all the metadata showed."""
        answer = commits(message(("actions/checkout", "major")), message(("pyyaml", "patch")))
        result = check(run_shell, fake_gh, answer, "version-update:semver-patch")
        assert result.returncode == 0, result
        assert result.outputs == {"found": "true"}, result.outputs

    def test_a_major_in_a_later_block_of_one_message_holds_it(self, run_shell, fake_gh):
        both = message(("pyyaml", "patch")) + "\n" + message(("actions/checkout", "major"))
        result = check(run_shell, fake_gh, commits(both), "version-update:semver-patch")
        assert result.returncode == 0, result
        assert result.outputs == {"found": "true"}, result.outputs

    def test_patch_and_minor_updates_go_ahead(self, run_shell, fake_gh):
        answer = commits(message(("actions/checkout", "minor"), ("pyyaml", "patch")))
        result = check(run_shell, fake_gh, answer, "version-update:semver-minor")
        assert result.returncode == 0, result
        assert result.outputs == {"found": "false"}, result.outputs

    def test_a_major_the_metadata_found_still_counts(self, run_shell, fake_gh):
        """A block with no update type: fetch-metadata works it out from the versions."""
        bare = "build(deps): bump actions/checkout from 4.2.2 to 6.0.0\n"
        result = check(run_shell, fake_gh, commits(bare), "version-update:semver-major")
        assert result.returncode == 0, result
        assert result.outputs == {"found": "true"}, result.outputs

    def test_a_list_it_cannot_read_approves_nothing(self, run_shell, fake_gh):
        result = check(run_shell, fake_gh, "gh: Server Error (HTTP 502)", code=1)
        assert result.returncode != 0, result
        assert "found" not in result.outputs, result.outputs


class TestOnlyAnExplicitFalseGoesAhead:
    def test_approval_and_auto_merge_wait_on_an_explicit_false(self):
        for named in ("Approve Dependabot PR", "Enable Auto-Merge"):
            assert step(named)["if"] == "${{ steps.major.outputs.found == 'false' }}", named

    def test_a_found_major_is_flagged_for_a_person(self):
        flag = step("Flag Major Update for Human Review")
        assert flag["if"] == "${{ steps.major.outputs.found == 'true' }}"

    def test_the_commits_are_read_before_anything_is_approved(self):
        steps = load_yaml(AUTOMERGE)["jobs"][JOB]["steps"]
        ids = [s.get("id") for s in steps]
        assert ids.index("major") < ids.index("approve")
