# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Only one mechanism installs trigger stubs, and the docs must name it.

`.github/workflows/README.md` told the reader "`apply-standards.yml` writes
those files for you". `apply-standards.yml`'s own header says the opposite,
in capitals: "⚠️ IT DOES NOT INSTALL STUBS. It once did, and the trigger
files now ship in the template repositories instead."

The workflow is right. Its three jobs write labels, settings and rulesets
through the API; none of them writes a file into a tree.

A consumer following the README dispatched Apply Standards, got labels, and
got no trigger files. If they had also applied the rulesets, branch
protection then required `ci / 🧪 Lint, Test & Build` from a workflow that
did not exist in their repository, and every pull request waited forever on
a check that could never report.
"""

from __future__ import annotations

import re

from conftest import ROOT, load_yaml

README = ROOT / ".github/workflows/README.md"
APPLY = ".github/workflows/apply-standards.yml"


class TestApplyStandardsIsNotCreditedWithInstallingStubs:
    def test_the_readme_does_not_say_it_writes_them(self):
        """The defect: it did, and the workflow says in capitals it does not."""
        text = README.read_text(encoding="utf-8")
        offending = [
            line
            for line in text.splitlines()
            if "apply-standards" in line and re.search(r"writ(e|es) those files", line)
        ]
        assert not offending, (
            "the README credits apply-standards.yml with installing trigger stubs, "
            f"which its own header denies in capitals: {offending}"
        )

    def test_the_workflow_still_denies_it(self):
        # If this ever stops being true the README should change back, not
        # the test be deleted.
        header = (ROOT / APPLY).read_text(encoding="utf-8").split("\n---\n", 1)[0]
        assert "DOES NOT INSTALL STUBS" in header

    def test_no_job_writes_into_a_tree(self):
        for job in load_yaml(APPLY)["jobs"].values():
            for step in job.get("steps", []):
                run = step.get("run") or ""
                assert "git push" not in run and "git commit" not in run, (
                    f"a job in {APPLY} now writes to a tree; the README claim may be revivable"
                )


class TestTheRealMechanismIsNamedInstead:
    def test_the_reader_is_pointed_at_the_templates(self):
        text = README.read_text(encoding="utf-8")
        section = text.split("A trigger file must live in your repository.", 1)
        assert len(section) == 2, "the adoption rule moved; re-point this test"
        window = section[1][:400]
        assert "template" in window.lower(), (
            "the rule that a stub must exist locally does not say where one comes from"
        )
