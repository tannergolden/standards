# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""A check that inspected zero files must not report success.

`update-doc-indexes.py` walks `DOCS = "docs"`, a CWD-relative literal.
`os.walk` on a path that does not exist yields nothing and raises nothing,
so `hosts` was empty, `stale_files` was empty, and `--check` printed
"✅ Doc indexes check passed - every machined index matches the tree" and
exited 0.

Run from the wrong directory, or in a consuming repository that adopted the
generator without a `docs/` folder, the gate the styling spec lists as
enforcement inspected nothing and said everything was fine. That is the same
shape as the CI stage probe and the label dry run: an operation that did
nothing, reporting success.
"""

from __future__ import annotations

import pytest
from conftest import ROOT

SCRIPT = "scripts/update-doc-indexes.py"


def run_in(run_script, cwd, *args):
    return run_script(SCRIPT, cwd=cwd, env={"ARGS": " ".join(args)})


class TestAMissingDocsFolderIsAnError:
    def test_check_fails_when_there_is_no_docs_folder(self, run_shell, tmp_path):
        """The defect: this printed a green tick over zero files."""
        result = run_shell(f"python3 {ROOT / SCRIPT} --check", cwd=tmp_path)
        assert result.returncode != 0, result
        assert "docs" in result.output

    def test_write_fails_the_same_way(self, run_shell, tmp_path):
        result = run_shell(f"python3 {ROOT / SCRIPT} --write", cwd=tmp_path)
        assert result.returncode != 0, result

    def test_the_message_names_the_missing_directory(self, run_shell, tmp_path):
        result = run_shell(f"python3 {ROOT / SCRIPT} --check", cwd=tmp_path)
        assert "does not exist" in result.output.lower()

    def test_an_empty_docs_folder_is_not_an_error(self, run_shell, tmp_path):
        """Present but empty is a real state: a repository may have the
        folder and no markdown in it yet. Only ABSENT is unanswerable."""
        (tmp_path / "docs").mkdir()
        result = run_shell(f"python3 {ROOT / SCRIPT} --check", cwd=tmp_path)
        assert result.returncode == 0, result


class TestTheRealTreeStillPasses:
    def test_check_passes_here(self, run_shell):
        result = run_shell(f"python3 {ROOT / SCRIPT} --check", cwd=ROOT)
        assert result.returncode == 0, result
        assert "passed" in result.stdout

    def test_it_actually_inspected_files(self, run_shell):
        """Guards against the fix trading one silent pass for another."""
        result = run_shell(f"python3 {ROOT / SCRIPT} --check", cwd=ROOT)
        assert "0 file" not in result.stdout


class TestArgumentsAreStillRequired:
    def test_neither_flag_is_rejected(self, run_shell, tmp_path):
        (tmp_path / "docs").mkdir()
        assert run_shell(f"python3 {ROOT / SCRIPT}", cwd=tmp_path).returncode != 0

    @pytest.mark.parametrize("flag", ["--check", "--write"])
    def test_each_flag_is_accepted(self, run_shell, tmp_path, flag):
        (tmp_path / "docs").mkdir()
        assert run_shell(f"python3 {ROOT / SCRIPT} {flag}", cwd=tmp_path).returncode == 0
