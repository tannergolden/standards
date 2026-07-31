# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""An unreadable workflow directory is a token problem, and must say so.

`apply-rulesets.sh` refuses to apply a ruleset whose required checks nothing
declares, because a check that never reports blocks every merge. When the
workflow directory cannot be LISTED, that is a different problem with a
different fix, and the script has a message written for it naming the exact
token scope to add.

That message was unreachable. `WORKFLOWS_READABLE=false` was assigned inside
a function invoked as

    DECLARED="$(declared_job_ids | sort -u)"

which is a command substitution AND a pipeline: two subshells. The
assignment never reached the parent, so the flag always read `true` and the
caller got the generic "these job ids are missing" error instead.

The concrete case: a PRIVATE repository whose ADMIN_TOKEN carries
Administration write but not Contents read. The listing 404s, every required
id reads as missing, and the operator is told to fix their workflows when
the workflows are fine.
"""

from __future__ import annotations

import json

SCRIPT = "scripts/apply-rulesets.sh"

CONTENTS = [
    {"type": "file", "name": "checks.yml"},
]
WORKFLOW_YAML = "jobs:\n  ci:\n    uses: x\n  secrets:\n    uses: y\n  pr:\n    uses: z\n"


def run_preflight(run_script, fake_gh, tmp_path, *, listable=True, jobs=WORKFLOW_YAML, dry_run="true"):
    # Ordered most-specific first: the fake takes the first route whose
    # text appears in the call, and every path here contains "repos/o/r".
    if listable:
        fake_gh.route("contents/.github/workflows/", jobs)
        fake_gh.route("contents/.github/workflows", json.dumps(CONTENTS))
    else:
        fake_gh.route("contents/.github/workflows", "", code=1)
    fake_gh.route("rulesets", "[]")
    fake_gh.route("repo view", "o/r")
    fake_gh.route("repos/o/r", json.dumps({"default_branch": "main"}))
    return run_script(
        SCRIPT,
        cwd=tmp_path,
        env=fake_gh.env(GH_TOKEN="t", TARGET_REPO="o/r", DRY_RUN=dry_run),
    )


class TestAnUnlistableDirectoryIsDiagnosedAsSuch:
    def test_it_fails(self, run_script, fake_gh, tmp_path):
        result = run_preflight(run_script, fake_gh, tmp_path, listable=False)
        assert result.returncode != 0, result

    def test_it_names_the_token_scope(self, run_script, fake_gh, tmp_path):
        """The defect: this said the job ids were missing instead."""
        result = run_preflight(run_script, fake_gh, tmp_path, listable=False)
        assert "Contents" in result.output, (
            "an unreadable workflow directory is reported as missing job ids, so the "
            f"operator is told to fix workflows that are fine:\n{result.output}"
        )

    def test_it_does_not_blame_the_workflows(self, run_script, fake_gh, tmp_path):
        result = run_preflight(run_script, fake_gh, tmp_path, listable=False)
        assert "REQUIRE_CHECKS=false" in result.output, (
            "the escape hatch for this exact case is not offered"
        )


class TestARealMissingJobIdIsStillReported:
    def test_a_readable_directory_missing_an_id_fails_differently(
        self, run_script, fake_gh, tmp_path
    ):
        # A real run, because the missing-id branch only warns in a preview.
        result = run_preflight(
            run_script, fake_gh, tmp_path, jobs="jobs:\n  ci:\n    uses: x\n", dry_run="false"
        )
        assert result.returncode != 0, result
        assert "no workflow" in result.output, result.output
        assert "Contents" not in result.output, (
            "a genuinely missing job id is being reported as a token problem"
        )

    def test_a_complete_set_of_ids_passes_the_preflight(self, run_script, fake_gh, tmp_path):
        result = run_preflight(run_script, fake_gh, tmp_path)
        assert result.returncode == 0, result
