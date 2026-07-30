# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The link-check summary step must read the file the action writes.

`config/lychee.toml` set `output = "./lychee.md"` and `ci.yml` guarded its
summary step on `[ -f ./lychee.md ]`. That guard was never true.

lycheeverse/lychee-action always passes `--output` on the command line, and
a CLI flag overrides a config-file key, so lychee never honoured the config
value. The action writes to its own `output` input, whose default is
`./lychee/out.md`. The summary step therefore did nothing on every CI run in
every consuming repository: it looked like a report step and produced no
report.

The fix names the path once, in the workflow, where the action can actually
be told about it.
"""

from __future__ import annotations

import re
import tomllib

import pytest
from conftest import ROOT, load_yaml, workflow_step_shell

CI = ".github/workflows/ci.yml"


@pytest.fixture(scope="module")
def link_step() -> dict:
    steps = load_yaml(CI)["jobs"]["link-checker"]["steps"]
    return next(s for s in steps if "lychee-action" in str(s.get("uses", "")))


class TestTheActionIsToldWhereToWrite:
    def test_the_step_sets_an_output_path(self, link_step):
        """The defect: nothing told the action, so it used its own default."""
        assert "output" in (link_step.get("with") or {}), (
            "the lychee step does not set `output:`, so the action writes to its "
            "own default and the summary step below reads a file that never exists"
        )

    def test_the_summary_reads_that_same_path(self, link_step):
        configured = link_step["with"]["output"].strip()
        shell = workflow_step_shell(CI, "link-checker", "📊 Link Check Summary")
        assert configured in shell, (
            f"the action writes {configured!r} but the summary step reads something else:\n{shell}"
        )

    def test_the_summary_still_guards_on_the_file_existing(self, link_step):
        # A missing report is not a failure: the link check may have been
        # skipped or produced nothing.
        shell = workflow_step_shell(CI, "link-checker", "📊 Link Check Summary")
        assert re.search(r"if \[ -f", shell)


class TestTheConfigNoLongerClaimsToSetIt:
    def test_lychee_toml_does_not_set_output(self):
        """A key the CLI always overrides is a key that lies about itself."""
        config = tomllib.loads((ROOT / "config/lychee.toml").read_text(encoding="utf-8"))
        assert "output" not in config, (
            "config/lychee.toml sets `output`, which the action's own --output flag "
            "always overrides; it reads as configuration and is inert"
        )

    def test_the_config_still_carries_the_settings_that_do_work(self):
        config = tomllib.loads((ROOT / "config/lychee.toml").read_text(encoding="utf-8"))
        assert config, "the shared lychee config is empty"


class TestTheReportIsNotCommitted:
    def test_the_output_path_is_git_ignored(self, link_step):
        configured = link_step["with"]["output"].strip().lstrip("./")
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
        root = configured.split("/")[0]
        assert root in ignored, (
            f"{configured} is written into the tree but {root!r} is not in .gitignore"
        )
