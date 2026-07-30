# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""A hand-written error message must be reachable.

`release-notes.yml` computes a base version with

    BASE_VER=$(printf '%s' "$NEXT_VER" | grep -oE '...' | head -n 1)

and then checks `[ -z "$BASE_VER" ]` to emit a specific annotation. Under
`set -euo pipefail` that check is unreachable: when grep matches nothing the
pipeline's status is 1, the assignment inherits it, and `set -e` exits the
step first. The operator saw a step that failed with no output instead of
the message written for exactly this case.

`release-publish.yml:247` does the same computation and DOES carry the
`|| true` that keeps its guard reachable, so the two copies of one idea had
drifted apart.
"""

from __future__ import annotations

import pytest
from conftest import workflow_step_shell

SITES = [
    (".github/workflows/release-notes.yml", "changelog", "version", "NEXT_VER"),
    (".github/workflows/release-publish.yml", "release", "version", "NEXT_VER"),
]


@pytest.mark.parametrize(("rel", "job", "step", "var"), SITES)
class TestTheGuardIsReachable:
    def test_unparseable_output_reaches_the_written_error(
        self, run_shell, tmp_path, rel, job, step, var
    ):
        """The defect: pipefail killed the step before the message ran."""
        result = run_shell(
            workflow_step_shell(rel, job, step),
            cwd=tmp_path,
            env={var: "no version anywhere in this text", "REF_NAME": "main", "MANUAL_TAG": ""},
        )
        assert result.returncode != 0, result
        assert "::error" in result.output, (
            f"{rel} failed with no annotation; the hand-written guard never ran:\n{result.output}"
        )
        assert "base version" in result.output.lower()

    def test_a_parseable_version_still_works(self, run_shell, git_repo, rel, job, step, var):
        # A real repository: the publish variant resolves branches with git
        # before it gets to the version arithmetic.
        result = run_shell(
            workflow_step_shell(rel, job, step),
            cwd=git_repo,
            env={var: "1.5.0", "REF_NAME": "Development", "MANUAL_TAG": ""},
        )
        assert result.returncode == 0, result
        assert any("1.5.0" in v for v in result.outputs.values()), result.outputs
