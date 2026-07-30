# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""A settings file that yields nothing must fail, not report success.

The whole `repository` group is driven by

    done < <(jq -r '.repository | to_entries[] ...' "$SETTINGS_FILE")

A failure inside a process substitution is invisible to both `set -e` and
`pipefail`: the loop simply reads zero lines. Nothing validated that the
file had a `.repository` object at all.

`settings-file` is a public input of `actions/apply-settings`, wired from
`apply-standards.yml`. A consumer passing valid JSON with no top-level
`repository` key, or with it nested one level deeper, got a jq error on
stderr that nothing acted on, zero settings applied, `CHANGED=0`, and a
GREEN '⚙️ Apply Repository Settings' job reporting "Nothing to change:
already matches the published set".

Which is the worst possible message: it says the repository is already
correct, when in fact nothing was ever compared.
"""

from __future__ import annotations

import json

import pytest
from conftest import ROOT

SCRIPT = "scripts/apply-settings.sh"

GOOD = {"repository": {"has_issues": True}, "actions": {}, "toggles": []}
BAD_FILES = [
    ("no repository key", {"settings": {"has_issues": True}}),
    ("repository is null", {"repository": None}),
    ("repository is a list", {"repository": [{"has_issues": True}]}),
    ("repository is empty", {"repository": {}}),
    ("top level is a list", [{"has_issues": True}]),
]


def run_settings(run_script, fake_gh, tmp_path, payload):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    fake_gh.route("repos/o/r", json.dumps({"has_issues": False}))
    return run_script(
        SCRIPT,
        cwd=tmp_path,
        env=fake_gh.env(
            GH_TOKEN="t",
            TARGET_REPO="o/r",
            SETTINGS_FILE=str(path),
            DRY_RUN="true",
        ),
    )


@pytest.mark.parametrize(("label", "payload"), BAD_FILES)
class TestAnUnusableSettingsFileFails:
    def test_it_exits_non_zero(self, run_script, fake_gh, tmp_path, label, payload):
        """The defect: every one of these reported success."""
        result = run_settings(run_script, fake_gh, tmp_path, payload)
        assert result.returncode != 0, f"{label}: {result}"

    def test_it_does_not_claim_the_repository_already_matches(
        self, run_script, fake_gh, tmp_path, label, payload
    ):
        result = run_settings(run_script, fake_gh, tmp_path, payload)
        assert "already matches" not in result.output, (
            f"{label}: reported the repository as already correct having compared nothing"
        )

    def test_the_error_names_the_file(self, run_script, fake_gh, tmp_path, label, payload):
        result = run_settings(run_script, fake_gh, tmp_path, payload)
        assert "settings.json" in result.output or "repository" in result.output.lower()


class TestAUsableFileStillWorks:
    def test_a_well_formed_file_is_accepted(self, run_script, fake_gh, tmp_path):
        result = run_settings(run_script, fake_gh, tmp_path, GOOD)
        assert result.returncode == 0, result

    def test_the_shipped_file_is_well_formed(self):
        payload = json.loads((ROOT / "data/repository-settings.json").read_text(encoding="utf-8"))
        assert isinstance(payload.get("repository"), dict)
        assert payload["repository"], "the shipped settings file has an empty repository object"
