# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The schedule page states two rules the repository itself breaks.

It opens with "Every workflow in this repository is reusable: it declares
`on: workflow_call` and nothing else, so it carries no cron of its own and
cannot fire on its own". `self-checks.yml` declares `push`, `pull_request`,
`schedule` and `workflow_dispatch`, and its `0 4 * * 1` is the only cron
that actually fires in this repository. `release.yml` is dispatch-only.
`docs/README.md` bills this page as "Every cron, in one table", and the one
real cron was the one missing from it.

Then "The On-The-Hour Rule": every recurring cron fires at minute `00` and
each takes a distinct off-peak hour. The example shipped in
`prune-runs.yml`'s header is `30 6 * * 1`, which breaks both halves at
once - minute 30, and hour 6 already taken by `prune.yml`. A consumer
copying it lands a schedule violating the rule they were just told to
follow, and stacks it into the collision the staggering paragraph exists to
prevent.
"""

from __future__ import annotations

import re

from conftest import ROOT, load_yaml, workflow_on

PAGE = ROOT / "docs/distribution/automation/Automation-Schedules.md"
WORKFLOWS = ROOT / ".github/workflows"


def stub_crons() -> dict[str, str]:
    """The example cron in each published workflow's header stub."""
    found = {}
    for path in sorted(WORKFLOWS.glob("*.yml")):
        for match in re.finditer(r"^#.*cron:\s*'([^']+)'", path.read_text(encoding="utf-8"), re.M):
            found[path.name] = match.group(1)
    return found


class TestTheReusableClaimIsQualified:
    def test_local_workflows_are_not_described_as_reusable(self):
        """The defect: two files in this directory contradict all four
        clauses of that sentence."""
        text = PAGE.read_text(encoding="utf-8")
        local = [
            p.name
            for p in WORKFLOWS.glob("*.yml")
            if "workflow_call" not in workflow_on(load_yaml(f".github/workflows/{p.name}"))
        ]
        assert local, "no local workflows any more; this test can go"
        claim = re.search(r"Every workflow in this repository is \*\*reusable\*\*", text)
        assert not claim, (
            f"the page claims every workflow here is reusable, and these are not: {sorted(local)}"
        )

    def test_the_only_real_cron_is_in_the_table(self):
        text = PAGE.read_text(encoding="utf-8")
        doc = load_yaml(".github/workflows/self-checks.yml")
        schedule = workflow_on(doc)["schedule"][0]["cron"]
        assert "self-checks" in text, (
            "the page bills itself as every cron in one table and omits the only one "
            f"that fires here ({schedule})"
        )


class TestTheOnTheHourRuleHolds:
    def test_every_example_cron_fires_on_the_hour(self):
        offenders = {
            name: cron for name, cron in stub_crons().items() if not cron.startswith("0 ")
        }
        assert not offenders, (
            f"the page requires minute 00 and these shipped examples do not: {offenders}"
        )

    def test_no_two_example_crons_share_an_hour(self):
        by_hour: dict[str, list[str]] = {}
        for name, cron in stub_crons().items():
            by_hour.setdefault(cron.split()[1], []).append(name)
        clashes = {hour: names for hour, names in by_hour.items() if len(names) > 1}
        assert not clashes, (
            f"the page requires a distinct off-peak hour each and these collide: {clashes}"
        )
