# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Every `make` command a script here tells someone to run must exist.

The script docstrings named `make check-types`, `make docs-index` and
`make lint-docs` as the way to work on this repository. There was no
Makefile, so following them produced "No targets specified and no makefile
found".

It mattered more than a wrong command usually does. `check-type-parity.py`
states plainly that there is no CI job to hang it on and that
`make check-types` is how you run it, so the only thing standing between
the commit-type list and silent drift was a command nobody could run.

TWO KINDS OF `make` REFERENCE LIVE IN THIS REPOSITORY, and only one of them
is this test's business. A `make build` named in a workflow or in `docs/`
refers to the CONSUMING repository's Makefile, which is the entire point of
the stage-resolution contract and which this repository cannot vouch for. A
`make check-types` in a script docstring instructs whoever is working HERE.
Only the second kind is checked, so the test does not manufacture failures
out of the published standards telling other people to have a build target.
"""

from __future__ import annotations

import re

import pytest
from conftest import ROOT

MAKEFILE = ROOT / "Makefile"

# Backtick-quoted only. Unquoted "make" in prose is the English verb, and
# "make sure", "make it", "make the" are not commands.
REFERENCE = re.compile(r"`make ([a-z][a-z-]*)`")

# SCOPED TO `scripts/` ON PURPOSE. A `make build` named in a workflow or in
# docs/ refers to the CONSUMING repository's Makefile, which is the whole
# point of the stage-resolution contract, and this repository cannot vouch
# for it. The script docstrings are different: they instruct whoever is
# working on THIS repository, so a target they name has to exist HERE.
SEARCHED = ("scripts/*.py", "scripts/*.sh")


def declared_targets() -> set[str]:
    text = MAKEFILE.read_text(encoding="utf-8")
    phony = re.search(r"^\.PHONY:\s*(.+)$", text, re.M)
    declared = set(phony.group(1).split()) if phony else set()
    declared |= set(re.findall(r"^([a-z][a-z-]*):", text, re.M))
    return declared


def referenced() -> dict[str, list[str]]:
    """Every `make <target>` a script tells the reader to run, and where."""
    found: dict[str, list[str]] = {}
    for pattern in SEARCHED:
        for path in sorted(ROOT.glob(pattern)):
            for number, line in enumerate(
                path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
            ):
                for match in REFERENCE.finditer(line):
                    found.setdefault(match.group(1), []).append(
                        f"{path.relative_to(ROOT)}:{number}"
                    )
    return found


class TestTheMakefileExists:
    def test_it_is_there(self):
        assert MAKEFILE.is_file(), "documents across this repository tell people to run make"

    def test_it_declares_the_targets_the_standards_name(self):
        # `ci.yml` resolves a stage to `make <stage>`, so these names are
        # the ones a consuming repository would use; keeping them aligned
        # here is deliberate rather than incidental.
        assert {"lint", "test", "lint-docs", "docs-index", "check-types"} <= declared_targets()

    def test_the_scripts_reference_at_least_one(self):
        # Guards the premise: if the docstrings stop naming any target, the
        # check below would pass having checked nothing.
        assert referenced(), "no script names a `make` command any more; re-point this test"

    def test_every_target_is_phony(self):
        """None of these produce a file of their own name, and a directory
        of that name must never make one look satisfied."""
        text = MAKEFILE.read_text(encoding="utf-8")
        phony = set(re.search(r"^\.PHONY:\s*(.+)$", text, re.M).group(1).split())
        rules = set(re.findall(r"^([a-z][a-z-]*):", text, re.M))
        assert rules <= phony, f"not declared .PHONY: {sorted(rules - phony)}"


class TestNothingNamesAMissingTarget:
    def test_every_documented_command_resolves(self):
        declared = declared_targets()
        missing = {
            target: where for target, where in referenced().items() if target not in declared
        }
        assert not missing, "documented `make` commands with no such target: " + "; ".join(
            f"{target} (named at {', '.join(where)})" for target, where in sorted(missing.items())
        )

    @pytest.mark.parametrize("target", ["lint", "test", "lint-docs", "docs-index", "check-types"])
    def test_the_named_targets_are_actually_reachable(self, run_shell, target):
        """`make -n` here is asking make itself, which is the one place that
        question is the right one to ask."""
        result = run_shell(f'make -n {target} >/dev/null 2>&1; echo "rc=$?"', cwd=ROOT)
        assert "rc=0" in result.stdout, f"make -n {target} failed: {result}"
