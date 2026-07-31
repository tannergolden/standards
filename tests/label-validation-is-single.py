# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""One validator for the label taxonomy, not two that disagree.

`actions/sync-labels` carried an inline '🔍 Validate taxonomy' step that
re-implemented, with a line-oriented regex and no YAML parser, checks
`scripts/sync-labels.sh` already performs before its first write.

They disagreed. YAML escapes a single quote by doubling it, so a
description written `'…isn''t…'` is two characters longer as raw text than
as a parsed value. A description of exactly 100 characters containing one
apostrophe was reported by the inline step as 101 and blocked the entire
sync, for a taxonomy the real validator accepts.

The script also checks strictly more: name length against GitHub's limit,
case-insensitive duplicates (GitHub treats names case-insensitively for
uniqueness, so two entries differing only in case collide on the second
write), a missing description, and a `renamed_from` naming the label itself.

Keeping the weaker copy meant a second place to look and a second place to
be wrong.
"""

from __future__ import annotations

import pytest
from conftest import ROOT, load_yaml

ACTION = "actions/sync-labels/action.yml"
SCRIPT = ROOT / "scripts/sync-labels.sh"


def step_names() -> list[str]:
    return [s.get("name", "") for s in load_yaml(ACTION)["runs"]["steps"]]


class TestThereIsOnlyOneValidator:
    def test_the_action_no_longer_re_implements_it(self):
        """The defect: a regex copy that disagreed with the real one."""
        assert not any("Validate taxonomy" in name for name in step_names()), (
            f"the action still validates the taxonomy itself: {step_names()}"
        )

    def test_the_action_still_runs_the_script(self):
        steps = load_yaml(ACTION)["runs"]["steps"]
        assert any("sync-labels.sh" in (s.get("run") or "") for s in steps)


class TestTheSurvivingValidatorChecksMore:
    @pytest.mark.parametrize(
        "rule",
        [
            "MAX_NAME",  # name length
            "MAX_DESC",  # description length
            "duplicate",  # case-insensitive collision
            "no description",  # a missing description
            "renamed_from names the label itself",
        ],
    )
    def test_it_covers_what_the_inline_copy_did_and_more(self, rule):
        assert rule in SCRIPT.read_text(encoding="utf-8"), (
            f"the surviving validator does not check {rule!r}; removing the inline copy "
            "would lose a check"
        )

    def test_it_runs_before_anything_is_written(self):
        text = SCRIPT.read_text(encoding="utf-8")
        validate = text.index("Validate the whole registry before writing anything")
        first_write = text.index("Read the repository's current labels")
        assert validate < first_write

    def test_it_parses_yaml_rather_than_matching_lines(self):
        assert "yaml" in SCRIPT.read_text(encoding="utf-8").lower()
