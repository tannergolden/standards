# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Every required check passes on a merge group, where there is no pull request.

A merge queue asks every required check to report on the merge group as
well as on the pull request, so the template's stubs behind all three now
trigger on `merge_group`. The pinned gitleaks action takes push,
pull_request, workflow_dispatch and schedule and exits 1 on anything else,
so on `merge_group` the required secret scan failed every queued pull
request. The scan is skipped there instead: GitHub reports a job skipped
inside a called workflow as Success, which a required check accepts, and
only a skipped CALLER job leaves the check unreported.
"""

from __future__ import annotations

import re

from conftest import ROOT, load_yaml

GITLEAKS = ".github/workflows/gitleaks.yml"


def header(rel: str) -> str:
    """The commented header of a workflow, its stub included."""
    return (ROOT / rel).read_text(encoding="utf-8").split("\n---\n", 1)[0]


class TestTheSecretScan:
    def test_it_is_skipped_on_a_merge_group_and_nowhere_else(self):
        """The defect: gitleaks exited 1 on `merge_group`, failing the required check."""
        condition = load_yaml(GITLEAKS)["jobs"]["scan"]["if"]
        assert condition.replace(" ", "") == "${{github.event_name!='merge_group'}}"

    def test_the_check_keeps_its_name(self):
        assert load_yaml(GITLEAKS)["jobs"]["scan"]["name"] == "🔍 Scan for Secrets"

    def test_its_stub_triggers_on_a_merge_group(self):
        assert re.search(r"^#\s+merge_group:", header(GITLEAKS), re.M), (
            "the stub shown in gitleaks.yml's header never reports to a merge queue"
        )
