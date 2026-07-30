# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""A required gate must not pass because it only saw part of the evidence.

`repos/{repo}/pulls/{n}/commits` is capped by GitHub at 250 commits however
it is paginated. `--paginate` stops because no further `Link: rel="next"`
arrives, and the curl fallback stops for the same reason via its
`[ "$count" -lt 100 ]` break. Neither notices the difference between "that
was all of them" and "that was as many as you are allowed".

So on a pull request with more than 250 commits, an unsigned commit at
position 251 was never examined, and `pr / ✍️ DCO Sign-Off`, a required
status check in both shipped rulesets, printed a green tick reading "all 250
commit(s) carry a Signed-off-by trailer".

This script already fails closed on an API error and on a non-array body.
Truncation is the same class of unknown and now gets the same treatment.
"""

from __future__ import annotations

import json

import pytest

SCRIPT = "scripts/dco-check.sh"


def commits(count, *, signed=True, start=0):
    return [
        {
            "sha": f"{i:040x}",
            "author": {"login": "someone"},
            "parents": [{"sha": "p"}],
            "commit": {
                "message": "feat(x): 🌱 work\n\nBody.\n"
                + ("\nSigned-off-by: A <a@example.invalid>\n" if signed else "")
            },
        }
        for i in range(start, start + count)
    ]


def run_dco(run_script, fake_gh, listed, claimed, tmp_path):
    """`listed` is what the commits endpoint returns; `claimed` is the
    number the pull request itself reports.

    Routed in this order because the fake matches the first route whose
    text appears in the call: the more specific path must come first.
    """
    fake_gh.route("pulls/1/commits", json.dumps(listed))
    fake_gh.route("pulls/1", json.dumps({"commits": claimed}))
    return run_script(
        SCRIPT,
        cwd=tmp_path,
        env=fake_gh.env(
            GH_TOKEN="t",
            REPO="o/r",
            PR_NUMBER="1",
        ),
    )


class TestTruncationIsDetected:
    def test_passes_when_every_commit_was_seen(self, run_script, fake_gh, tmp_path):
        result = run_dco(run_script, fake_gh, commits(3), 3, tmp_path)
        assert result.returncode == 0, result

    def test_fails_when_the_listing_is_short_of_what_the_pr_claims(
        self, run_script, fake_gh, tmp_path
    ):
        """The defect: 250 signed commits listed, 400 on the branch."""
        result = run_dco(run_script, fake_gh, commits(250), 400, tmp_path)
        assert result.returncode != 0, result
        assert "250" in result.output and "400" in result.output

    def test_the_error_names_truncation_rather_than_a_missing_signoff(
        self, run_script, fake_gh, tmp_path
    ):
        result = run_dco(run_script, fake_gh, commits(250), 400, tmp_path)
        assert "250" in result.output
        assert "missing the DCO" not in result.output, (
            "a truncated listing must not be reported as unsigned commits"
        )


class TestExistingBehaviourIsUnchanged:
    def test_still_fails_an_unsigned_commit(self, run_script, fake_gh, tmp_path):
        listed = commits(2) + commits(1, signed=False, start=90)
        result = run_dco(run_script, fake_gh, listed, 3, tmp_path)
        assert result.returncode != 0
        assert "missing the DCO" in result.output

    def test_still_fails_closed_when_the_api_is_unreachable(
        self, run_script, fake_gh, tmp_path
    ):
        fake_gh.route("pulls", "", code=1)
        result = run_script(
            SCRIPT,
            cwd=tmp_path,
            env=fake_gh.env(GH_TOKEN="t", REPO="o/r", PR_NUMBER="1"),
        )
        assert result.returncode != 0
