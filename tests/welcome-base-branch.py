# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The first-time welcome must name the branch pull requests target.

governance.yml's welcome tells a first-time pull request author which base
branch to use, and it named the repository's default branch. Once a project
is ready to distribute, `Release` becomes the default branch while every
pull request still targets `Development`, so the welcome told a newcomer who
had targeted `Development` to target `Release` instead.

A `base-branch` input now names the branch. With none, the welcome names the
default branch as before, so a stub that passes nothing reads as it did. The
assertions are structural: an Actions expression cannot be evaluated outside
Actions, so the test reads the message rather than rendering it.
"""

from __future__ import annotations

import re

import yaml
from conftest import ROOT, load_yaml, workflow_inputs, workflow_on

WORKFLOW = ".github/workflows/governance.yml"


def welcome() -> dict:
    """The inputs of the one step that posts the welcome."""
    steps = load_yaml(WORKFLOW)["jobs"]["onboarding"]["steps"]
    found = [s for s in steps if str(s.get("uses", "")).startswith("actions/first-interaction@")]
    assert len(found) == 1, f"expected one welcome step, found {len(found)}"
    return found[0]["with"]


def stub() -> dict:
    """The stub shown in the workflow's header, parsed as the YAML a consumer copies."""
    lines = (ROOT / WORKFLOW).read_text(encoding="utf-8").split("\n---\n", 1)[0].splitlines()
    start = next(i for i, line in enumerate(lines) if line.rstrip().endswith("adds a stub:"))
    body: list[str] = []
    for line in lines[start + 1:]:
        if line.startswith("#   "):
            body.append(line[4:])
        elif body:
            break
    return yaml.safe_load("\n".join(body))


class TestTheInput:
    def test_it_is_optional_and_empty_by_default(self):
        spec = workflow_inputs(WORKFLOW)["base-branch"]
        assert (spec["type"], spec["required"], spec["default"]) == ("string", False, "")


class TestThePullRequestWelcome:
    def test_it_names_the_input_before_the_default_branch(self):
        """The defect: once `Release` was the default, the welcome named it."""
        lines = [line for line in welcome()["pr_message"].splitlines() if "**Base branch**" in line]
        assert len(lines) == 1, lines
        expressions = [" ".join(e.split()) for e in re.findall(r"\$\{\{(.*?)\}\}", lines[0])]
        assert expressions == ["inputs.base-branch || github.event.repository.default_branch"], lines[0]


class TestTheDocumentedStub:
    def test_its_welcome_names_the_branch_its_trigger_takes(self):
        doc = stub()
        branches = workflow_on(doc)["pull_request_target"]["branches"]
        assert branches, "the stub's pull request trigger names no branch"
        assert doc["jobs"]["governance"]["with"]["base-branch"] in branches
