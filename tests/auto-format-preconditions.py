# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Auto-format must skip when it cannot run, not fail.

The Prettier path guards carefully for a lockfile, skipping with a warning
when `package-lock.json` is absent, and never guarded for prettier itself
being a dependency of the calling repository. `npx --no-install` refuses to
fetch by design, so it fails hard when prettier is not in the tree that
`npm ci` just installed.

A repository with a `package.json` and a lockfile but no prettier - a Go or
Python project carrying package.json for a documentation toolchain, or one
that formats with something else and forgot to pass `format-command` - got a
red '🖌️ Code Style Formatter' run on EVERY push to its integration branch,
forever, for a workflow whose own header calls itself "a safety net".

The remediation text made it worse: it told the reader to check
`package-lock.json`, which was present and correct.
"""

from __future__ import annotations

import json

from conftest import workflow_step_shell

WORKFLOW = ".github/workflows/auto-format.yml"


def install(run_shell, tmp_path, manifest=None, lockfile=True, prettier=True):
    if manifest is not None:
        (tmp_path / "package.json").write_text(json.dumps(manifest), encoding="utf-8")
    if lockfile:
        (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
    # A fake npm: `ci` succeeds, and `ls prettier` reports what the tree has.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    npm = bin_dir / "npm"
    npm.write_text(
        "#!/usr/bin/env bash\n"
        'case "$1" in\n'
        "  ci) exit 0 ;;\n"
        f"  ls) exit {0 if prettier else 1} ;;\n"
        "  *) exit 0 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    npm.chmod(0o755)
    import os

    return run_shell(
        workflow_step_shell(WORKFLOW, "format", "install"),
        cwd=tmp_path,
        env={"PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"},
    )


class TestTheInstallStepDecidesWhetherPrettierCanRun:
    def test_ready_when_a_lockfile_and_prettier_are_present(self, run_shell, tmp_path):
        result = install(run_shell, tmp_path, manifest={"devDependencies": {"prettier": "3"}})
        assert result.returncode == 0, result
        assert result.outputs.get("ready") == "true", result

    def test_not_ready_without_a_lockfile(self, run_shell, tmp_path):
        result = install(run_shell, tmp_path, manifest={}, lockfile=False)
        assert result.returncode == 0, result
        assert result.outputs.get("ready") == "false"
        assert "lock" in result.output.lower()

    def test_not_ready_when_prettier_is_not_a_dependency(self, run_shell, tmp_path):
        """The defect: this went on to `npx --no-install prettier` and died."""
        result = install(run_shell, tmp_path, manifest={}, prettier=False)
        assert result.returncode == 0, result
        assert result.outputs.get("ready") == "false", result
        assert "prettier" in result.output.lower()

    def test_the_skip_is_a_warning_not_a_failure(self, run_shell, tmp_path):
        result = install(run_shell, tmp_path, manifest={}, prettier=False)
        assert "::warning" in result.output
        assert "::error" not in result.output


class TestTheRemediationTextNamesTheRightCause:
    def test_it_mentions_a_missing_prettier_dependency(self):
        shell = workflow_step_shell(WORKFLOW, "format", "📝 Report Failure (Format)")
        assert "prettier" in shell.lower()
        assert "format-command" in shell, (
            "the failure tips do not mention the input that makes this workflow "
            "work for a repository that formats with something other than Prettier"
        )
