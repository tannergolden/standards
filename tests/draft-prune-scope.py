# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The draft prune must only delete drafts this workflow created.

`release-notes.yml` mints exactly one tag shape:

    version=v${BASE_VER}-${BRANCH_NAME}.next

and then pruned superseded drafts with `case "$tag" in v*-"$BRANCH".*)`.
That glob is wider than the namespace the workflow owns. Anything matching
`v<x>-<branch>.<anything>` was deleted, on a weekly unattended schedule.

So a maintainer's hand-written draft tagged `v1.4.0-main.hotfix`, or
`v1.4.0-main.2`, was destroyed by a run that had nothing to do with it, and
release notes are the only changelog there is.

The header of this workflow claims it owns only what it creates. These tests
hold it to that.
"""

from __future__ import annotations

import json

import pytest
from conftest import workflow_step_shell

WORKFLOW = ".github/workflows/release-notes.yml"
STEP = "publish"


def prune(run_shell, fake_gh, tmp_path, tags, branch="main"):
    releases = [{"id": i, "tag_name": t, "draft": True} for i, t in enumerate(tags, 1)]
    # Order matters: the fake takes the first route whose text appears in
    # the call, and a DELETE call also contains "/releases".
    # Order matters: the fake takes the first route whose text appears in
    # the call, and a DELETE call also contains "/releases".
    fake_gh.route("-X DELETE", "")
    fake_gh.route("release create", "")
    fake_gh.route("/releases", json.dumps(releases))
    result = run_shell(
        workflow_step_shell(WORKFLOW, "changelog", STEP),
        cwd=tmp_path,
        env=fake_gh.env(
            GH_TOKEN="t", REPO="o/r", BRANCH=branch, CONTENT="notes",
            TAG="v1.5.0-main.next", HEAD_SHA="abc123",
        ),
    )
    deleted = {
        c.split("/releases/")[1].split()[0]
        for c in fake_gh.calls
        if "-X DELETE" in c and "/releases/" in c
    }
    return result, {t for i, t in enumerate(tags, 1) if str(i) in deleted}


class TestOnlyTheOwnedNamespaceIsDeleted:
    def test_a_superseded_next_draft_is_pruned(self, run_shell, fake_gh, tmp_path):
        result, deleted = prune(run_shell, fake_gh, tmp_path, ["v1.4.0-main.next"])
        assert result.returncode == 0, result
        assert deleted == {"v1.4.0-main.next"}

    @pytest.mark.parametrize(
        "tag",
        [
            "v1.4.0-main.hotfix",
            "v1.4.0-main.2",
            "v1.4.0-main.rc1",
            "v1.4.0-main.next.old",
        ],
    )
    def test_a_hand_written_draft_is_left_alone(self, run_shell, fake_gh, tmp_path, tag):
        """The defect: the glob swallowed anything after the branch name."""
        result, deleted = prune(run_shell, fake_gh, tmp_path, [tag])
        assert result.returncode == 0, result
        assert deleted == set(), f"{tag} was deleted by a prune that does not own it"

    def test_another_branchs_draft_is_left_alone(self, run_shell, fake_gh, tmp_path):
        result, deleted = prune(run_shell, fake_gh, tmp_path, ["v1.4.0-develop.next"])
        assert result.returncode == 0, result
        assert deleted == set(), "a draft belonging to another branch was deleted"

    def test_it_prunes_the_right_one_out_of_a_mixed_list(self, run_shell, fake_gh, tmp_path):
        tags = [
            "v1.4.0-main.next",
            "v1.4.0-main.hotfix",
            "v1.3.0-main.next",
            "v1.4.0-develop.next",
        ]
        result, deleted = prune(run_shell, fake_gh, tmp_path, tags)
        assert result.returncode == 0, result
        assert deleted == {"v1.4.0-main.next", "v1.3.0-main.next"}


class TestTheTagShapeIsStillTheOneMinted:
    def test_the_version_step_mints_a_dot_next_tag(self):
        """The prune may only be as wide as the shape this workflow mints."""
        shell = workflow_step_shell(WORKFLOW, "changelog", "version")
        assert "${BRANCH_NAME}.next" in shell
