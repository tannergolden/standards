# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The identity substitutions, which shipped without a gate.

`init-template.py` rewrites the template author's identity to the new
owner's. One of its rules replaces the `OWNER/REPOSITORY` placeholder that
the issue chooser's contact links carry, because GitHub substitutes nothing
in a contact link and there is no expression syntax there to do it with.

NOTHING TESTED THAT RULE, and both templates went on to describe it
incorrectly for months - the public one telling new owners the chooser link
was "left visibly wrong on purpose" and something they must fix by hand,
the private one claiming an inherited chooser gets rewritten locally. Two
documents drifted in opposite directions away from one untested line.

The rules also have to NOT fire in one place: `tannergolden/standards` is
the shared repository every generated repository calls, and it is correct
for everyone. A blanket handle replace would rewrite it and point every
workflow at a repository that does not exist.
"""

from __future__ import annotations

from conftest import load_script

init = load_script("scripts/init-template.py")

OWNER = "newowner"
REPO = "newowner/newproject"
TEMPLATE_OWNER = "tannergolden"


def rewrite(text: str, *, display: str = "New Owner", year: int = 2031) -> str:
    """The shipped rule set, applied with a consistent new identity."""
    return init.rewrite(
        text,
        owner=OWNER,
        repo=REPO,
        display=display,
        template_owner=TEMPLATE_OWNER,
        year=year,
    )


class TestTheContactLinkPlaceholder:
    """The rule with no gate, and the one both templates documented wrongly."""

    def test_the_placeholder_becomes_the_new_repository(self):
        assert rewrite("url: 'https://github.com/OWNER/REPOSITORY/discussions'") == (
            f"url: 'https://github.com/{REPO}/discussions'"
        )

    def test_a_contact_link_in_a_chooser_is_rewritten_in_place(self):
        """The shape the templates actually ship, rather than a bare token.

        Deliberately NOT read from a sibling checkout of the template: a
        test that skips whenever the other repository is absent would skip
        on every CI run, which is the coverage this rule already had.
        """
        chooser = (
            "blank_issues_enabled: false\n"
            "contact_links:\n"
            "  - name: '\U0001f4ac Questions'\n"
            "    url: 'https://github.com/OWNER/REPOSITORY/discussions'\n"
            "    about: 'How-to questions belong in Discussions.'\n"
        )
        result = rewrite(chooser)
        assert f"https://github.com/{REPO}/discussions" in result
        assert "OWNER/REPOSITORY" not in result

    def test_every_occurrence_goes_not_just_the_first(self):
        text = "a OWNER/REPOSITORY b OWNER/REPOSITORY"
        assert rewrite(text) == f"a {REPO} b {REPO}"


class TestTheSharedStandardsPathSurvives:
    """The handle is an identity to rewrite AND part of a path that must not
    change. Getting this wrong points every generated workflow at nothing."""

    def test_a_workflow_reference_is_left_alone(self):
        uses = f"uses: {TEMPLATE_OWNER}/standards/.github/workflows/ci.yml@v1"
        assert rewrite(uses) == uses

    def test_a_bare_handle_beside_one_is_still_rewritten(self):
        text = f"@{TEMPLATE_OWNER} owns {TEMPLATE_OWNER}/standards"
        assert rewrite(text) == f"@{OWNER} owns {TEMPLATE_OWNER}/standards"

    def test_the_guard_sentinel_does_not_survive_into_the_output(self):
        assert "\x00" not in rewrite(f"{TEMPLATE_OWNER}/standards and {TEMPLATE_OWNER}")


class TestTheLicenceHolder:
    def test_the_holder_and_the_year_are_both_restamped(self):
        assert rewrite("Copyright (c) 2026 Tanner Golden", display="New Owner", year=2031) == (
            "Copyright (c) 2031 New Owner"
        )

    def test_a_year_range_is_replaced_whole(self):
        assert rewrite("Copyright (c) 2024-2026 Tanner Golden", year=2031) == (
            "Copyright (c) 2031 New Owner"
        )

    def test_a_display_name_containing_a_backreference_is_taken_literally(self):
        """A display name is arbitrary user input; `\\1` in it must not be
        read as a group reference."""
        assert rewrite("Copyright (c) 2026 Tanner Golden", display=r"\1 Corp") == (
            r"Copyright (c) 2031 \1 Corp"
        )


class TestItLeavesUnrelatedTextAlone:
    def test_text_with_no_identity_in_it_is_returned_unchanged(self):
        text = "# A heading\n\nSome prose about nothing in particular.\n"
        assert rewrite(text) == text
