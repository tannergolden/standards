# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""An empty environment name must not widen a destructive prune.

`prune.yml` splits deployment pruning in two, and threads the SAME input
into both halves: the pages job takes `pages-environment` as its allowlist,
the app job takes it as its denylist. `prune-deployments.py` documents an
empty allowlist as "prune everything", which is right for a script called
directly and wrong for what the pages job means by it.

So a consumer with no documentation site, setting `pages-environment: ''`
because they have none, got the opposite of what they asked for on both
sides at once: the PAGES job pruned every environment including production,
and the app job stopped excluding anything.

The script's contract is unchanged and pinned here. The job that cannot mean
"everything" no longer runs when it has nothing to scope to.
"""

from __future__ import annotations

import pytest
from conftest import load_script, load_yaml, workflow_inputs

WORKFLOW = ".github/workflows/prune.yml"
prune = load_script("scripts/prune-deployments.py")


class TestTheScriptContractIsUnchanged:
    """Documented at scripts/prune-deployments.py, lines 17-21."""

    def test_an_allowlist_selects_only_those(self):
        assert prune.in_scope("github-pages", only={"github-pages"}, exclude=set())
        assert not prune.in_scope("production", only={"github-pages"}, exclude=set())

    def test_a_denylist_selects_everything_else(self):
        assert not prune.in_scope("github-pages", only=set(), exclude={"github-pages"})
        assert prune.in_scope("production", only=set(), exclude={"github-pages"})

    def test_neither_means_every_environment(self):
        assert prune.in_scope("production", only=set(), exclude=set())

    def test_an_allowlist_beats_a_denylist(self):
        assert prune.in_scope("a", only={"a"}, exclude={"a"})


@pytest.fixture(scope="module")
def pages_job() -> dict:
    return load_yaml(WORKFLOW)["jobs"]["deployments-pages"]


class TestThePagesJobCannotBecomeGlobal:
    def test_it_does_not_run_without_an_environment_to_scope_to(self, pages_job):
        """The defect: an empty allowlist meant every environment."""
        assert "inputs.pages-environment" in pages_job["if"], (
            "the pages prune runs with an empty allowlist, which the script "
            f"reads as 'prune everything'. Condition is: {pages_job['if']}"
        )
        assert "!=" in pages_job["if"] or "== ''" in pages_job["if"]

    def test_it_still_only_runs_when_pruning_is_asked_for(self, pages_job):
        assert "inputs.prune-deployments" in pages_job["if"]

    def test_it_still_scopes_to_the_named_environment(self, pages_job):
        step = next(s for s in pages_job["steps"] if "prune-deployments" in str(s.get("uses", "")))
        assert step["with"]["only"] == "${{ inputs.pages-environment }}"


class TestTheInputDocumentsWhatEmptyMeans:
    def test_the_description_says_empty_disables_it(self):
        description = workflow_inputs(WORKFLOW)["pages-environment"]["description"].lower()
        assert "empty" in description, (
            "nothing tells a caller what an empty pages-environment does, and it "
            "changes the scope of a destructive job on both sides"
        )

    def test_it_still_defaults_to_the_github_environment(self):
        assert workflow_inputs(WORKFLOW)["pages-environment"]["default"] == "github-pages"
