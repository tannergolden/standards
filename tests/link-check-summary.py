# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The link-check summary step must read the file lychee writes.

`config/lychee.toml` set `output = "./lychee.md"` and `ci.yml` guarded its
summary step on `[ -f ./lychee.md ]`. That guard was never true: lychee took
its `--output` from the command line, and a CLI flag overrides a config-file
key, so lychee never honoured the config value and the summary step did
nothing on every CI run in every consuming repository.

The path is named once, in the workflow, as `REPORT`: the link check writes
it and the summary reads it. The check now runs lychee itself, from the
environment's toolchain, and keeps what the lychee action did: a Markdown
report, a failure when no link was found at all, and a failure on broken
links only when `fail-on-broken-links` says so.
"""

from __future__ import annotations

import os
import re
import stat

import pytest
import tomllib
from conftest import ROOT, load_yaml, requires, workflow_step_shell

CI = ".github/workflows/ci.yml"
CHECK = "🔗 Link Check"
SUMMARY = "📊 Link Check Summary"

# A stand-in for lychee: it records its arguments, writes the summary table
# lychee 0.24 writes, cells padded the same way, with the total it is told,
# where --output says, and exits as it is told.
FAKE_LYCHEE = """#!/usr/bin/env bash
printf '%s\\n' "$@" > "$LYCHEE_ARGS"
out=""
while [ $# -gt 0 ]; do
  [ "$1" = --output ] && out="$2"
  shift
done
{
  printf '# Summary\\n\\n| Status         | Count |\\n|----------------|-------|\\n'
  printf '| 🔍 Total       | %-5s |\\n' "${FAKE_TOTAL:-5}"
  printf '| 🚫 Errors      | %-5s |\\n' "${FAKE_ERRORS:-0}"
} > "$out"
exit "${FAKE_EXIT:-0}"
"""


def steps() -> list[dict]:
    return load_yaml(CI)["jobs"]["link-checker"]["steps"]


@pytest.fixture(scope="module")
def link_step() -> dict:
    return next(s for s in steps() if s.get("name") == CHECK)


class TestTheReportIsNamedOnce:
    def test_the_check_writes_its_report_to_report(self, link_step):
        """The defect: nothing told lychee, so it wrote somewhere else."""
        assert link_step["env"]["REPORT"]
        assert '--output "$REPORT"' in link_step["run"]

    def test_the_summary_reads_that_same_path(self, link_step):
        summary = next(s for s in steps() if s.get("name") == SUMMARY)
        assert summary["env"]["REPORT"] == link_step["env"]["REPORT"]
        assert '"$REPORT"' in workflow_step_shell(CI, "link-checker", SUMMARY)

    def test_the_summary_still_guards_on_the_file_existing(self):
        # A missing report is not a failure: the link check may have been
        # skipped or produced nothing.
        shell = workflow_step_shell(CI, "link-checker", SUMMARY)
        assert re.search(r"if \[ -f", shell)


class TestTheConfigNoLongerClaimsToSetIt:
    def test_lychee_toml_does_not_set_output(self):
        """A key the CLI always overrides is a key that lies about itself."""
        config = tomllib.loads((ROOT / "config/lychee.toml").read_text(encoding="utf-8"))
        assert "output" not in config, (
            "config/lychee.toml sets `output`, which the workflow's --output flag "
            "always overrides; it reads as configuration and is inert"
        )

    def test_the_config_still_carries_the_settings_that_do_work(self):
        config = tomllib.loads((ROOT / "config/lychee.toml").read_text(encoding="utf-8"))
        assert config, "the shared lychee config is empty"


class TestTheReportIsNotCommitted:
    def test_the_output_path_is_git_ignored(self, link_step):
        configured = link_step["env"]["REPORT"].strip().lstrip("./")
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
        root = configured.split("/")[0]
        assert root in ignored, (
            f"{configured} is written into the tree but {root!r} is not in .gitignore"
        )


class TestLycheeRunsAsTheActionRanIt:
    def test_it_comes_from_the_toolchain_before_the_check(self, link_step):
        uses = [str(step.get("uses", "")) for step in steps()]
        toolchain = next(i for i, u in enumerate(uses) if u.startswith("tannergolden/environment/.github/actions/toolchain@"))
        assert toolchain < steps().index(link_step)

    @pytest.fixture
    def check(self, run_shell, tmp_path):
        bin_dir = tmp_path / "_bin"
        bin_dir.mkdir()
        tool = bin_dir / "lychee"
        tool.write_text(FAKE_LYCHEE, encoding="utf-8")
        tool.chmod(tool.stat().st_mode | stat.S_IEXEC)

        def _check(fail: str, **env: str):
            return run_shell(
                workflow_step_shell(CI, "link-checker", CHECK),
                env={
                    "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
                    "LYCHEE_ARGS": str(tmp_path / "_lychee_args"),
                    "CONFIG": "lychee.toml",
                    "FAIL": fail,
                    "REPORT": "./lychee.md",
                    **env,
                },
            )

        return _check

    def test_it_runs_as_the_action_ran_it(self, check, tmp_path):
        assert check("true").returncode == 0
        args = (tmp_path / "_lychee_args").read_text(encoding="utf-8").splitlines()
        assert args == ["--mode", "task", "--format", "markdown", "--output", "./lychee.md",
                        "--config", "lychee.toml", "--root-dir", ".", "."]

    def test_broken_links_fail_when_asked_to(self, check):
        assert check("true", FAKE_EXIT="2").returncode == 2

    def test_broken_links_pass_when_not(self, check):
        assert check("false", FAKE_EXIT="2").returncode == 0

    def test_no_links_at_all_fail_either_way(self, check):
        result = check("false", FAKE_TOTAL="0")
        assert result.returncode == 1
        assert "::error" in result.output

    def test_a_clean_check_passes_and_leaves_its_report(self, check, tmp_path):
        assert check("true").returncode == 0
        assert (tmp_path / "lychee.md").is_file()

    def test_a_total_that_ends_in_zero_is_not_empty(self, check):
        assert check("true", FAKE_TOTAL="10").returncode == 0


@requires("lychee")
class TestTheRealLychee:
    """The same step, run by the lychee the toolchain pins, on links it can check offline."""

    @pytest.fixture
    def check(self, run_shell, tmp_path):
        tree = tmp_path / "tree"
        tree.mkdir()

        def _check(fail: str, pages: dict[str, str]):
            for name, text in pages.items():
                (tree / name).write_text(text, encoding="utf-8")
            result = run_shell(
                workflow_step_shell(CI, "link-checker", CHECK),
                cwd=tree,
                env={"CONFIG": str(ROOT / "config/lychee.toml"), "FAIL": fail, "REPORT": "./lychee.md"},
            )
            report = tree / "lychee.md"
            return result, report.read_text(encoding="utf-8") if report.exists() else ""

        return _check

    def test_a_link_that_resolves_passes(self, check):
        result, report = check("true", {"README.md": "See [the guide](guide.md).\n", "guide.md": "# Guide\n"})
        assert result.returncode == 0, result
        assert re.search(r"Total\s+\|\s+1\s", report), report

    def test_a_broken_link_fails_only_when_asked_to(self, check):
        pages = {"README.md": "See [the guide](missing.md).\n"}
        broken, report = check("true", pages)
        assert broken.returncode != 0, broken
        assert "missing.md" in report
        advisory, _ = check("false", pages)
        assert advisory.returncode == 0, advisory

    def test_a_tree_with_no_links_fails_either_way(self, check):
        for fail in ("true", "false"):
            result, report = check(fail, {"README.md": "# Nothing to follow\n"})
            assert result.returncode == 1, (fail, result, report)
            assert "found no links at all" in result.output
