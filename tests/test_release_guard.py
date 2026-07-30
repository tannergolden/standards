# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Cut Release must refuse a commit that is not on the release line.

`release.yml` is the most consequential workflow here: it force-moves `v1`,
and every repository pinned to `@v1` executes whatever that tag points at on
their next run, with no pull request on their side to notice.

Its trigger is a bare `workflow_dispatch` with no branch restriction, and
the job never checked which ref it had been handed. `actions/checkout` takes
the dispatch ref, `git tag` tags that ref's HEAD, and the major tag is force
pushed onto it. Anyone with write access could therefore publish from an
unmerged branch, and the audit trail would show a normal release.

The guard is an ancestry test rather than a branch-name test: what matters
is that the commit being published is already on the default branch, not
what the ref selector happened to be called.
"""

from __future__ import annotations

import json
import subprocess

import pytest
from conftest import workflow_step_shell

RELEASE = ".github/workflows/release.yml"
STEP = "check"


@pytest.fixture
def released(git_repo):
    """A repository whose `origin/main` is a real remote-tracking ref."""
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/main", "HEAD"],
        cwd=git_repo,
        check=True,
    )
    return git_repo


@pytest.fixture
def validate(run_shell, fake_gh):
    """Run the validation step with a repository that has no releases yet.

    The step reads the published release list to check the version moves
    forward, so every case needs `gh` answered. An empty list is the
    neutral setup: it exercises the format, ancestry and already-tagged
    checks without the ordering check having an opinion.
    """

    def _validate(cwd, version="v1.4.0", default_branch="main", **env):
        fake_gh.route("releases", "[]")
        return run_shell(
            workflow_step_shell(RELEASE, "release", STEP),
            cwd=cwd,
            env=fake_gh.env(
                VERSION=version,
                DEFAULT_BRANCH=default_branch,
                GH_TOKEN="t",
                GITHUB_REPOSITORY="o/r",
                **env,
            ),
        )

    return _validate


def commit_on(repo, branch, message="feat(x): 🌱 work"):
    subprocess.run(["git", "checkout", "-q", "-B", branch], cwd=repo, check=True)
    # A branch name may contain '/', which is not a file name.
    (repo / f"{branch.replace('/', '-')}.txt").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", message, "--no-gpg-sign"], cwd=repo, check=True
    )


class TestVersionFormat:
    """Unchanged behaviour, pinned so the new guard cannot regress it."""

    @pytest.mark.parametrize("bad", ["1.4.0", "v1.4", "v1.4.0-rc.1", "vX.Y.Z", "", "v1.4.0 "])
    def test_rejects_a_malformed_version(self, validate, released, bad):
        assert validate(released, version=bad).returncode != 0

    def test_accepts_a_well_formed_version(self, validate, released):
        result = validate(released)
        assert result.returncode == 0, result
        assert result.outputs.get("major") == "v1"

    def test_refuses_a_version_already_tagged(self, validate, released):
        subprocess.run(["git", "tag", "v1.4.0"], cwd=released, check=True)
        result = validate(released)
        assert result.returncode != 0
        assert "already exists" in result.output


class TestTheCommitMustBeOnTheReleaseLine:
    def test_accepts_a_commit_on_the_default_branch(self, validate, released):
        assert validate(released).returncode == 0

    def test_accepts_an_older_commit_on_the_default_branch(self, validate, released):
        """Re-cutting from an earlier merged commit is legitimate."""
        commit_on(released, "main", "feat(x): 🌱 newer")
        subprocess.run(
            ["git", "update-ref", "refs/remotes/origin/main", "HEAD"], cwd=released, check=True
        )
        subprocess.run(["git", "checkout", "-q", "HEAD~1"], cwd=released, check=True)
        assert validate(released).returncode == 0

    def test_refuses_an_unmerged_branch(self, validate, released):
        """The defect: `v1` could be force-moved onto unreviewed code."""
        commit_on(released, "feat/not-merged")
        result = validate(released)
        assert result.returncode != 0, result
        assert "default branch" in result.output.lower()

    def test_refuses_when_the_default_branch_is_unknown(self, validate, released):
        """Failing closed: an unresolvable base is not a pass."""
        result = validate(released, default_branch="nonexistent")
        assert result.returncode != 0, result


class TestTheVersionMustMoveForward:
    """`--latest` and the major-tag move do not check ordering themselves.

    `gh release create --latest` marks whatever it is given as the latest
    release, and `git tag -f v1` moves the major pointer onto it. Publishing
    a version older than the current one therefore moves both backwards, and
    every repository pinned to `@v1` downgrades on its next run.

    Keeping the tags (see test_release_tag_contract.py) closed the common
    path into this, since an already-published version is caught by the
    existing tag check. It does not close the case where the tag is absent:
    a historic cleanup, an imported repository, or a typo in a new line.
    """

    def _released(self, run_shell, repo, tags, version="v1.4.0", fake_gh=None):
        # The real API shape: a list of release objects. The fake applies
        # the step's own `--jq` to it, so the filter is under test too.
        fake_gh.route(
            "releases",
            json.dumps([{"tag_name": tag, "draft": False} for tag in tags]),
        )
        return run_shell(
            workflow_step_shell(RELEASE, "release", STEP),
            cwd=repo,
            env=fake_gh.env(
                VERSION=version,
                DEFAULT_BRANCH="main",
                GH_TOKEN="t",
                GITHUB_REPOSITORY="o/r",
            ),
        )

    def test_accepts_the_first_release(self, run_shell, released, fake_gh):
        assert self._released(run_shell, released, [], fake_gh=fake_gh).returncode == 0

    def test_accepts_a_newer_version(self, run_shell, released, fake_gh):
        result = self._released(run_shell, released, ["v1.3.9"], "v1.4.0", fake_gh)
        assert result.returncode == 0, result

    def test_orders_numerically_not_lexically(self, run_shell, released, fake_gh):
        # v1.10.0 is newer than v1.9.0; a string comparison says otherwise.
        result = self._released(run_shell, released, ["v1.9.0"], "v1.10.0", fake_gh)
        assert result.returncode == 0, result

    def test_refuses_an_older_version(self, run_shell, released, fake_gh):
        result = self._released(run_shell, released, ["v1.9.0"], "v1.2.0", fake_gh)
        assert result.returncode != 0, result
        assert "older" in result.output.lower() or "newer" in result.output.lower()

    def test_refuses_a_lexically_larger_but_older_version(self, run_shell, released, fake_gh):
        result = self._released(run_shell, released, ["v1.10.0"], "v1.9.0", fake_gh)
        assert result.returncode != 0, result

    def test_fails_closed_when_the_release_list_cannot_be_read(
        self, run_shell, released, fake_gh
    ):
        fake_gh.route("releases", "", code=1)
        result = run_shell(
            workflow_step_shell(RELEASE, "release", STEP),
            cwd=released,
            env=fake_gh.env(
                VERSION="v1.4.0",
                DEFAULT_BRANCH="main",
                GH_TOKEN="t",
                GITHUB_REPOSITORY="o/r",
            ),
        )
        assert result.returncode != 0, result
