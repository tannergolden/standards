# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Dotfiles are not suffixes, so three entries could never match.

`TEXT_SUFFIXES` listed `.editorconfig`, `.gitignore` and `.gitattributes`
alongside real suffixes, and the filter tested `path.suffix not in
TEXT_SUFFIXES`. For a leading-dot name `PurePath(".gitignore").suffix` is
`''`, not `'.gitignore'` - the whole name is the STEM. So those three
entries matched nothing, ever, and a generated repository kept the template
owner's handle verbatim in all three files while the action's commit body
claimed it had rewritten every identity the template stamped.
"""

from __future__ import annotations

import pytest
from conftest import load_script

init = load_script("scripts/init-template.py")

DOTFILES = [".editorconfig", ".gitignore", ".gitattributes"]
ORDINARY = ["README.md", "config.yml", "script.py", "LICENSE", "CODEOWNERS"]
BINARY = ["logo.png", "archive.tar.gz", "font.woff2"]


def considered(name: str) -> bool:
    """Would the rewrite look inside a file of this name?"""
    from pathlib import PurePath

    path = PurePath(name)
    return path.suffix in init.TEXT_SUFFIXES or path.name in init.TEXT_NAMES


class TestDotfilesAreMatchedByName:
    @pytest.mark.parametrize("name", DOTFILES)
    def test_the_rewrite_considers_them(self, name):
        """The defect: `.gitignore` has no suffix, so it never matched."""
        assert considered(name), f"{name} is never rewritten, so it keeps the template's identity"

    @pytest.mark.parametrize("name", DOTFILES)
    def test_they_are_not_listed_as_suffixes(self, name):
        assert name not in init.TEXT_SUFFIXES, (
            f"{name} is in TEXT_SUFFIXES, where it can never match a real path"
        )


class TestOrdinaryFilesStillMatch:
    @pytest.mark.parametrize("name", ORDINARY)
    def test_they_are_considered(self, name):
        assert considered(name)

    @pytest.mark.parametrize("name", BINARY)
    def test_binaries_are_not(self, name):
        assert not considered(name)


class TestEverySuffixEntryIsAPlausibleSuffix:
    def test_none_of_them_are_whole_file_names(self):
        """Guards the class of mistake rather than the three instances."""
        bogus = sorted(s for s in init.TEXT_SUFFIXES if s.count(".") != 1 or not s.startswith("."))
        assert not bogus, f"entries in TEXT_SUFFIXES that cannot be a suffix: {bogus}"
