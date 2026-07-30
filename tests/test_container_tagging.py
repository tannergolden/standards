# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""`latest` must never follow a prerelease, whatever fired the run.

The container plan reads prerelease-ness from
`github.event.release.prerelease` alone. On a `workflow_dispatch` run - one
of the two triggers the documented stub declares - there is no `release`
object in the payload, so that value is the empty string and the
`[ "$IS_PRERELEASE" = "true" ]` test is false.

So manually dispatching with `version: v2.0.0-rc.1` resolved
`TAGS="2.0.0-rc.1 latest"` and pushed `latest` at the release candidate.
Every `docker pull <image>` with no tag then gets the RC, which is exactly
what the guard's own comment says must not happen.

The version string is the honest source: a semver prerelease identifier is
part of the version itself, so it is true regardless of which event fired.
"""

from __future__ import annotations

import pytest
from conftest import workflow_step_shell

WORKFLOW = ".github/workflows/publish-package.yml"
STEP = "resolve"


def plan(run_shell, git_repo, *, version="", release_tag="", prerelease="", tags_input=""):
    return run_shell(
        workflow_step_shell(WORKFLOW, "container-plan", STEP),
        cwd=git_repo,
        env={
            "VERSION_INPUT": version,
            "RELEASE_TAG": release_tag,
            "IS_PRERELEASE": prerelease,
            "TAGS_INPUT": tags_input,
            "PLATFORMS": "linux/amd64",
            "REPO": "o/r",
            "DOCKERFILE": "Dockerfile",
            "IMAGE_INPUT": "",
            "REGISTRY": "ghcr.io",
        },
    )


@pytest.fixture
def repo(git_repo):
    (git_repo / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    return git_repo


class TestAReleaseEventIsUnchanged:
    def test_a_stable_release_gets_latest(self, run_shell, repo):
        result = plan(run_shell, repo, release_tag="v2.0.0", prerelease="false")
        assert result.returncode == 0, result
        assert "latest" in result.outputs.get("tags", "")

    def test_a_release_marked_prerelease_does_not(self, run_shell, repo):
        result = plan(run_shell, repo, release_tag="v2.0.0-rc.1", prerelease="true")
        assert result.returncode == 0, result
        assert "latest" not in result.outputs.get("tags", "")


class TestADispatchedPrereleaseDoesNotMoveLatest:
    @pytest.mark.parametrize(
        "version", ["v2.0.0-rc.1", "v1.0.0-beta.2", "v0.9.0-alpha", "v3.0.0-next.1"]
    )
    def test_a_prerelease_version_is_recognised_without_the_event(
        self, run_shell, repo, version
    ):
        """The defect: no release object meant IS_PRERELEASE was empty."""
        result = plan(run_shell, repo, version=version)
        assert result.returncode == 0, result
        assert "latest" not in result.outputs.get("tags", ""), (
            f"dispatching {version} pushed `latest` at a release candidate: "
            f"{result.outputs.get('tags')!r}"
        )

    def test_a_dispatched_stable_version_still_gets_latest(self, run_shell, repo):
        result = plan(run_shell, repo, version="v2.0.0")
        assert "latest" in result.outputs.get("tags", ""), result.outputs

    def test_an_explicit_tag_list_still_wins(self, run_shell, repo):
        result = plan(run_shell, repo, version="v2.0.0-rc.1", tags_input="edge canary")
        assert result.outputs.get("tags") == "edge canary"
