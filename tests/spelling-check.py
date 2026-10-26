# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The spelling check annotates each typo on its line, then fails on any.

`ci.yml` ran typos through crate-ci's action, which wrote a warning on each
typo's line and failed the job when there was one. The check now runs the
environment's typos itself, and keeps both: a first pass turns typos' JSON
into `::warning` lines, and a second, plain run decides the job. These run
the step with a typos that prints what it is told, then, where the runner
has them, with the real typos and jq.
"""

from __future__ import annotations

import os
import stat

import pytest
from conftest import ROOT, load_yaml, requires, workflow_step_shell

CI = ".github/workflows/ci.yml"
CHECK = "📝 Check Spelling"

# The misspelling every test here finds, put together at run time so that
# typos, run over this repository, finds none in this file.
TYPO = "te" + "h"

# A stand-in for typos: it records each run's arguments, and finds the typo
# on line 3 of docs/a.md when FAKE_TYPO is set, as typos does: one JSON line
# with --format json, a report otherwise, and exit 2 either way.
FAKE_TYPOS = """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$TYPOS_ARGS"
[ -n "${FAKE_TYPO:-}" ] || exit 0
case " $* " in
  *" --format json "*)
    printf '%s\\n' '{"type":"typo","path":"./docs/a.md","line_num":3,"byte_offset":7,"typo":"@TYPO@","corrections":["the"]}'
    ;;
  *) echo 'error: `@TYPO@` should be `the`' ;;
esac
exit 2
""".replace("@TYPO@", TYPO)

WARNING = f'::warning file=docs/a.md,line=3,col=8::"{TYPO}" should be "the".'


def steps() -> list[dict]:
    return load_yaml(CI)["jobs"]["spelling"]["steps"]


class TestTheCheckAsWritten:
    def test_typos_comes_from_the_toolchain_before_the_check(self):
        uses = [str(entry.get("uses", "")) for entry in steps()]
        toolchain = next(i for i, u in enumerate(uses) if u.startswith("tannergolden/environment/.github/actions/toolchain@"))
        names = [entry.get("name") for entry in steps()]
        assert toolchain < names.index(CHECK)
        assert steps()[toolchain]["with"]["tools"] == "binaries"

    def test_the_config_is_the_resolved_one(self):
        check = next(entry for entry in steps() if entry.get("name") == CHECK)
        assert check["env"]["CONFIG"] == "${{ steps.typos-config.outputs.path }}"


@requires("jq")
class TestTheCheckAsRun:
    @pytest.fixture
    def check(self, run_shell, tmp_path):
        bin_dir = tmp_path / "_bin"
        bin_dir.mkdir()
        tool = bin_dir / "typos"
        tool.write_text(FAKE_TYPOS, encoding="utf-8")
        tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
        args = tmp_path / "_typos_args"

        def _check(**env: str):
            result = run_shell(
                workflow_step_shell(CI, "spelling", CHECK),
                env={
                    "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
                    "TYPOS_ARGS": str(args),
                    "CONFIG": "_typos.toml",
                    **env,
                },
            )
            return result, args.read_text(encoding="utf-8").splitlines()

        return _check

    def test_a_typo_is_annotated_on_its_line_and_fails_the_job(self, check):
        result, _ = check(FAKE_TYPO="1")
        assert result.returncode == 2, result
        assert WARNING in result.output

    def test_a_clean_tree_passes_with_no_annotation(self, check):
        result, _ = check()
        assert result.returncode == 0, result
        assert "::warning" not in result.output

    def test_both_runs_read_the_resolved_config(self, check):
        _, runs = check()
        assert runs == [". --config _typos.toml --format json", ". --config _typos.toml"]


@requires("typos")
@requires("jq")
class TestTheRealTypos:
    @pytest.fixture
    def check(self, run_shell, tmp_path):
        tree = tmp_path / "tree"
        (tree / "docs").mkdir(parents=True)

        def _check(text: str):
            (tree / "docs" / "a.md").write_text(text, encoding="utf-8")
            return run_shell(
                workflow_step_shell(CI, "spelling", CHECK),
                cwd=tree,
                env={"CONFIG": str(ROOT / "config/_typos.toml")},
            )

        return _check

    def test_a_typo_is_annotated_on_its_line_and_fails_the_job(self, check):
        result = check(f"Fine line.\nAnother line.\nWe saw {TYPO} cat.\n")
        assert result.returncode == 2, result
        assert WARNING in result.output

    def test_a_clean_tree_passes_with_no_annotation(self, check):
        result = check("Every word here is spelled the way it should be.\n")
        assert result.returncode == 0, result
        assert "::warning" not in result.output
