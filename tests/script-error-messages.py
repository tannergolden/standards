# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""A script must name the problem, not print a Python traceback.

Every script here reports failures as `::error title=…` naming the cause and
the fix. Two did not, and both failed on ordinary input:

  update-label-docs.py     `label["description"]` raises KeyError on a
                           registry entry with no description. The GitHub
                           labels API permits one, and the file is
                           hand-edited, so this is a typo away at any time.
  check-standards-version  `os.environ["GH_TOKEN"]` raises KeyError when a
                           consumer's stub omits `secrets: inherit`, in a
                           workflow whose whole job is to post a friendly
                           advisory notice.

A traceback in an Actions log tells the reader which line of somebody else's
code blew up. It does not tell them what to change.
"""

from __future__ import annotations

import pathlib

import pytest
from conftest import load_script

label_docs = load_script("scripts/update-label-docs.py")

LABEL_DOCS = "scripts/update-label-docs.py"
VERSION_CHECK = "scripts/check-standards-version.py"

INCOMPLETE = [
    ("no description", "- name: 'area: infra'\ncolor: '0e8a16'\n"),
    ("no colour", "- name: 'area: infra'\ndescription: 'Infra.'\n"),
]


class TestTheLabelRegistryIsValidated:
    """The script reads a fixed path, so its functions are called directly."""

    @pytest.mark.parametrize(("label", "registry"), INCOMPLETE)
    def test_an_incomplete_entry_is_named(self, tmp_path, label, registry, capsys):
        """The defect: a raw KeyError naming no entry at all."""
        path = pathlib.Path(tmp_path / "labels.yml")
        path.write_text(registry, encoding="utf-8")
        with pytest.raises(SystemExit) as exit_info:
            label_docs.render(label_docs.load(path))
        assert exit_info.value.code not in (0, None), f"{label}: did not fail"
        message = str(exit_info.value.code) + capsys.readouterr().out
        assert "area: infra" in message, f"the failing entry is not named: {message}"

    def test_a_complete_entry_is_not_rejected(self, tmp_path):
        """Validation must reject the incomplete, not the merely unfamiliar.
        (`render` groups by family and emits nothing for an unknown one, so
        the assertion is on acceptance rather than on output.)"""
        path = pathlib.Path(tmp_path / "labels.yml")
        path.write_text(
            "- name: 'area: infra'\ncolor: '0e8a16'\ndescription: 'Infra.'\n", encoding="utf-8"
        )
        entries = label_docs.load(path)
        assert entries == [{"name": "area: infra", "color": "0e8a16", "description": "Infra."}]
        label_docs.render(entries)

    def test_the_shipped_registry_still_renders(self):
        from conftest import ROOT

        assert label_docs.render(label_docs.load(ROOT / "data" / "labels.yml"))


class TestTheVersionCheckReportsMissingEnvironment:
    @pytest.mark.parametrize("missing", ["GH_TOKEN", "REPO"])
    def test_it_names_the_variable(self, run_script, tmp_path, missing):
        """The defect: KeyError with a traceback, in an advisory workflow."""
        env = {"GH_TOKEN": "t", "REPO": "o/r"}
        del env[missing]
        result = run_script(VERSION_CHECK, cwd=tmp_path, env=env)
        assert result.returncode != 0, result
        assert "Traceback" not in result.output, (
            f"a missing {missing} dies with a traceback:\n{result.output}"
        )
        assert missing in result.output, f"the error does not name {missing}"

    def test_it_points_at_the_fix(self, run_script, tmp_path):
        result = run_script(VERSION_CHECK, cwd=tmp_path, env={"REPO": "o/r"})
        assert "secrets" in result.output.lower() or "inherit" in result.output.lower()
