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

The rules also have to NOT fire on a repository address. `tannergolden/standards`,
`tannergolden/intelligence` and `tannergolden/markdown` are the shared
repositories every generated repository calls, and they are correct for
everyone. A blanket handle replace would rewrite them and point every
workflow and every link to the kit at a repository that does not exist.

FOR A LONG TIME ONLY A LIST OF NAMES WAS SPARED. The template's own "third
route" remote, and the private template's links to its public sibling and to
the account's `.github`, were still rewritten to the new owner's account,
where none of them exist. The lines below are copied from the templates as
they ship, so a rule that breaks one of them fails here.
"""

from __future__ import annotations

import pytest
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


class TestEverySharedRepositorySurvives:
    """The Markdown Kit is shared too: the templates' assets/ READMEs link it,
    and a rewritten link would send a new owner to a kit that does not exist."""

    def test_a_link_to_each_shared_repository_is_left_alone(self):
        for name in ("standards", "intelligence", "markdown"):
            link = f"[{name}](https://github.com/{TEMPLATE_OWNER}/{name}/blob/Development/README.md)"
            assert rewrite(link) == link, name


class TestEveryRepositoryAddressSurvives:
    """A repository on the template owner's account exists there and nowhere
    else, whichever repository it is. Each line here is one the templates ship
    and one the old rule broke."""

    @pytest.mark.parametrize(
        "line",
        [
            # The agent instruction publisher, linked from both READMEs.
            "| **[`tannergolden/intelligence`](https://github.com/tannergolden/intelligence)** "
            "| one workflow stub | a release moving a tag, with no pull request |",
            # The "third route": a remote pointing back at the template itself.
            "> git remote add template https://github.com/tannergolden/path",
            "> git remote add template https://github.com/tannergolden/repo",
            # The private template, comparing itself with its public sibling.
            "|                    | [`tannergolden/path`](https://github.com/tannergolden/path) "
            "(public) | This one (private)                               |",
            "baseline: tannergolden/path",
            # The account's health files: an address, and kept as one.
            "Inherited from [`tannergolden/.github`](https://github.com/tannergolden/.github)",
        ],
    )
    def test_a_shipped_line_naming_a_repository_is_left_alone(self, line):
        assert rewrite(line) == line

    def test_an_address_is_kept_whole_rather_than_by_prefix(self):
        """In `<owner>/<owner>` the second handle is a repository NAME, and a
        rule that protected only the `<owner>/` part would rewrite it."""
        text = f"{TEMPLATE_OWNER}/{TEMPLATE_OWNER} and {TEMPLATE_OWNER}/pathfinder"
        assert rewrite(text) == text

    def test_a_deep_link_into_a_repository_survives(self):
        text = f"https://github.com/{TEMPLATE_OWNER}/standards/blob/Development/README.md"
        assert rewrite(text) == text

    def test_punctuation_after_an_address_is_untouched(self):
        text = f"See `{TEMPLATE_OWNER}/repo`, ({TEMPLATE_OWNER}/path) or {TEMPLATE_OWNER}/standards."
        assert rewrite(text) == text


class TestTheHandleOnItsOwnIsStillTheOwnersIdentity:
    """The other side of the line: everything that names the ACCOUNT moves to
    the new owner, including when it shares a line with an address."""

    def test_the_documentation_footer_is_rewritten(self):
        footer = (
            f"Built with ❤️ by [@{TEMPLATE_OWNER}](https://github.com/{TEMPLATE_OWNER}). "
            "Distributed under the MIT License."
        )
        assert rewrite(footer) == (
            f"Built with ❤️ by [@{OWNER}](https://github.com/{OWNER}). "
            "Distributed under the MIT License."
        )

    def test_the_funding_target_is_rewritten(self):
        line = f"github: [{TEMPLATE_OWNER}] # Replace with your GitHub username or organization"
        assert rewrite(line) == f"github: [{OWNER}] # Replace with your GitHub username or organization"

    def test_a_codeowners_entry_is_rewritten(self):
        assert rewrite(f"*                           @{TEMPLATE_OWNER}") == (
            f"*                           @{OWNER}"
        )

    def test_an_identity_beside_an_address_still_moves(self):
        text = f"[`{TEMPLATE_OWNER}/path`](https://github.com/{TEMPLATE_OWNER}/path) by @{TEMPLATE_OWNER}"
        assert rewrite(text) == (
            f"[`{TEMPLATE_OWNER}/path`](https://github.com/{TEMPLATE_OWNER}/path) by @{OWNER}"
        )

    def test_a_trailing_slash_with_no_name_is_the_profile_not_an_address(self):
        assert rewrite(f"https://github.com/{TEMPLATE_OWNER}/ ") == f"https://github.com/{OWNER}/ "

    def test_a_team_or_package_scope_follows_the_owner(self):
        """`@<owner>/<name>` is a namespace of the owner's, not a repository."""
        assert rewrite(f"/docs/ @{TEMPLATE_OWNER}/maintainers") == f"/docs/ @{OWNER}/maintainers"


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
