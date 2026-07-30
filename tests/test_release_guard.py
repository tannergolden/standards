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


def validate(run_shell, cwd, version="v1.4.0", default_branch="main", **env):
    return run_shell(
        workflow_step_shell(RELEASE, "release", STEP),
        cwd=cwd,
        env={"VERSION": version, "DEFAULT_BRANCH": default_branch, **env},
    )


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
    def test_rejects_a_malformed_version(self, run_shell, released, bad):
        assert validate(run_shell, released, version=bad).returncode != 0

    def test_accepts_a_well_formed_version(self, run_shell, released):
        result = validate(run_shell, released)
        assert result.returncode == 0, result
        assert result.outputs.get("major") == "v1"

    def test_refuses_a_version_already_tagged(self, run_shell, released):
        subprocess.run(["git", "tag", "v1.4.0"], cwd=released, check=True)
        result = validate(run_shell, released)
        assert result.returncode != 0
        assert "already exists" in result.output


class TestTheCommitMustBeOnTheReleaseLine:
    def test_accepts_a_commit_on_the_default_branch(self, run_shell, released):
        assert validate(run_shell, released).returncode == 0

    def test_accepts_an_older_commit_on_the_default_branch(self, run_shell, released):
        """Re-cutting from an earlier merged commit is legitimate."""
        commit_on(released, "main", "feat(x): 🌱 newer")
        subprocess.run(
            ["git", "update-ref", "refs/remotes/origin/main", "HEAD"], cwd=released, check=True
        )
        subprocess.run(["git", "checkout", "-q", "HEAD~1"], cwd=released, check=True)
        assert validate(run_shell, released).returncode == 0

    def test_refuses_an_unmerged_branch(self, run_shell, released):
        """The defect: `v1` could be force-moved onto unreviewed code."""
        commit_on(released, "feat/not-merged")
        result = validate(run_shell, released)
        assert result.returncode != 0, result
        assert "default branch" in result.output.lower()

    def test_refuses_when_the_default_branch_is_unknown(self, run_shell, released):
        """Failing closed: an unresolvable base is not a pass."""
        result = validate(run_shell, released, default_branch="nonexistent")
        assert result.returncode != 0, result
