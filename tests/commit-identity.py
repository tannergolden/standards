# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Who a commit is by: never an AI, and signed off by its author.

The DCO check counts `Signed-off-by:` lines and never asks whose they are,
so a commit an agent authored and signed off in its own name passed every
gate. `docs/distribution/Conventional-Commits.md` says an AI is always a
co-author and never the author, and that the person contributing a commit
signs it off. `commit-check.py` now reads both: the author from the API's
commit record, the sign-offs from the message.

The documented fallback used to be `git commit -s --author=<you>`, and `-s`
signs off as the COMMITTER, which in an agent session is the agent. These
cases are the commits that recipe produced.
"""

from __future__ import annotations

import pytest
from conftest import load_script

commit_check = load_script(".github/scripts/commit-check.py")

ADA = ("Ada Lovelace", "00000000+ada@users.noreply.github.com")
CLAUDE = ("Claude", "noreply@anthropic.com")


def commit(author: tuple[str, str], message: str, login: str = "ada", parents: int = 1) -> dict:
    return {
        "sha": "abcdef1234567",
        "author": {"login": login},
        "parents": [{}] * parents,
        "commit": {"author": {"name": author[0], "email": author[1]}, "message": message},
    }


def body(*trailers: str) -> str:
    return "fix(api): resolve the crash\n\nWhy it changed.\n\n" + "\n".join(trailers)


class TestTheAuthor:
    def test_a_person_with_their_own_sign_off_passes(self):
        assert commit_check.identity_problems(commit(ADA, body(f"Signed-off-by: {ADA[0]} <{ADA[1]}>"))) == []

    def test_an_ai_author_is_rejected(self):
        found = commit_check.identity_problems(commit(CLAUDE, body("Signed-off-by: Claude <noreply@anthropic.com>")))
        assert found and "its author is an AI" in found[0]

    def test_the_ai_credited_as_co_author_is_the_rule_not_a_problem(self):
        message = body("Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>", f"Signed-off-by: {ADA[0]} <{ADA[1]}>")
        assert commit_check.identity_problems(commit(ADA, message)) == []


class TestTheSignOff:
    def test_the_old_recipe_signed_off_as_the_agent_and_is_caught(self):
        """`git commit -s --author=<you>` in an agent session: Ada authors, Claude signs."""
        message = body("Signed-off-by: Claude <noreply@anthropic.com>")
        assert commit_check.problems_for(message, commit_check.DEFAULT_TYPES.split(","), 100)
        assert commit_check.identity_problems(commit(ADA, message))

    def test_a_sign_off_that_is_not_the_authors_is_rejected(self):
        found = commit_check.identity_problems(commit(ADA, body("Signed-off-by: Someone Else <someone@example.com>")))
        assert found and "no sign-off is its author's" in found[0]
        assert "--trailer 'Signed-off-by: Ada Lovelace" in found[0]

    def test_a_second_persons_sign_off_beside_the_authors_is_fine(self):
        message = body(f"Signed-off-by: {ADA[0]} <{ADA[1]}>", "Signed-off-by: Grace Hopper <grace@example.com>")
        assert commit_check.identity_problems(commit(ADA, message)) == []

    def test_the_email_compares_without_case(self):
        message = body(f"Signed-off-by: {ADA[0]} <{ADA[1].upper()}>")
        assert commit_check.identity_problems(commit(ADA, message)) == []

    def test_no_sign_off_at_all_is_the_dco_checks_to_report(self):
        assert commit_check.identity_problems(commit(ADA, body())) == []


class TestTheGateRunsItOnEveryHumanCommit:
    @pytest.fixture
    def gate(self, monkeypatch, tmp_path):
        def run(commits):
            monkeypatch.setattr(commit_check, "fetch_commits", lambda: commits)
            monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary.md"))
            return commit_check.main()
        return run

    def test_an_ai_authored_commit_fails_the_gate(self, gate):
        assert gate([commit(CLAUDE, body("Signed-off-by: Claude <noreply@anthropic.com>"))]) == 1

    def test_bots_and_merges_stay_exempt(self, gate):
        bot = commit(CLAUDE, body(), login="intelligence-sync[bot]")
        merge = commit(CLAUDE, "Merge branch 'x'", parents=2)
        assert gate([bot, merge]) == 0

    def test_a_clean_branch_passes(self, gate):
        assert gate([commit(ADA, body(f"Signed-off-by: {ADA[0]} <{ADA[1]}>"))]) == 0
