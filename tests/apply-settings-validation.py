# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""A settings file that yields nothing, or names what it cannot, must fail.

`settings-file` is a public input of `.github/actions/apply-settings`, wired from
`apply-standards.yml`, so the file is a consumer's and a consumer's mistake
has to be reported, not interpreted. The first version of the script read
its `repository` group out of a process substitution whose failure was
invisible to the shell: valid JSON with no `repository` key, or with it
nested one level deeper, compared nothing, applied nothing, and reported
"Nothing to change: already matches the published set", which says the
repository is correct when nothing was ever looked at.

The rewrite reads every group, so the failure moved rather than vanished: a
key under the wrong group, or misspelled, would simply never be read, and
the run would report a standard applied that it never saw. Both are refused
by name here, along with the handful of keys the script never writes.
"""

from __future__ import annotations

import json

import pytest
from conftest import ROOT, load_script

SCRIPT = ".github/scripts/apply-settings.py"
module = load_script(SCRIPT)

GOOD = {"repository": {"has_issues": True}, "actions": {}}
BAD_FILES = [
    ("no known group", {"settings": {"has_issues": True}}),
    ("repository is null", {"repository": None}),
    ("repository is a list", {"repository": [{"has_issues": True}]}),
    ("every group empty", {"repository": {}, "actions": {}, "security": {}}),
    ("top level is a list", [{"has_issues": True}]),
    ("misspelled group", {"repositry": {"has_issues": True}}),
    ("misspelled actions key", {"actions": {"workflow_permissions": "write"}}),
    ("misspelled security key", {"security": {"secret_scaning": True}}),
    ("security status is not a boolean", {"security": {"secret_scanning": "enabled"}}),
    ("visibility is never written", {"repository": {"private": True}}),
    ("archiving is never written", {"repository": {"archived": True}}),
    ("security statuses belong under security", {"repository": {"security_and_analysis": {}}}),
    ("default setup state is not one of two", {"security": {"code_scanning_default_setup": {"state": "on"}}}),
]


def run_settings(run_script, fake_gh, tmp_path, payload):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    fake_gh.route("repos/o/r", json.dumps({"has_issues": False, "visibility": "public"}))
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
        """The defect: a file yielding nothing reported success."""
        result = run_settings(run_script, fake_gh, tmp_path, payload)
        assert result.returncode != 0, f"{label}: {result}"

    def test_it_does_not_claim_the_repository_already_matches(
        self, run_script, fake_gh, tmp_path, label, payload
    ):
        result = run_settings(run_script, fake_gh, tmp_path, payload)
        assert "already matches" not in result.output, (
            f"{label}: reported the repository as already correct having compared nothing"
        )

    def test_it_is_an_annotation_not_a_traceback(self, run_script, fake_gh, tmp_path, label, payload):
        result = run_settings(run_script, fake_gh, tmp_path, payload)
        assert "Traceback" not in result.output, f"{label}: died with a traceback:\n{result.output}"
        assert "::error title=Repository settings::" in result.output, result.output

    def test_nothing_is_read_from_github(self, run_script, fake_gh, tmp_path, label, payload):
        # The file is refused before the repository is touched: a run that
        # cannot compare anything has no business making calls.
        run_settings(run_script, fake_gh, tmp_path, payload)
        assert fake_gh.calls == [], fake_gh.calls


class TestTheRefusalNamesTheProblem:
    def test_an_unknown_key_is_named(self, tmp_path):
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"actions": {"workflow_permissions": "write"}}), encoding="utf-8")
        with pytest.raises(module.SettingsError, match="workflow_permissions"):
            module.load_settings(path)

    def test_a_refused_key_says_why(self, tmp_path):
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"repository": {"visibility": "public"}}), encoding="utf-8")
        with pytest.raises(module.SettingsError, match="human acts"):
            module.load_settings(path)

    def test_a_missing_file_is_named(self, tmp_path):
        with pytest.raises(module.SettingsError, match="No settings file"):
            module.load_settings(tmp_path / "absent.json")

    def test_invalid_json_is_named(self, tmp_path):
        path = tmp_path / "settings.json"
        path.write_text("{not json", encoding="utf-8")
        with pytest.raises(module.SettingsError, match="not valid JSON"):
            module.load_settings(path)


class TestAUsableFileStillWorks:
    def test_a_well_formed_file_is_accepted(self, run_script, fake_gh, tmp_path):
        result = run_settings(run_script, fake_gh, tmp_path, GOOD)
        assert result.returncode == 0, result

    def test_the_shipped_file_is_well_formed(self):
        settings = module.load_settings(ROOT / "data/repository-settings.json")
        assert settings["repository"], "the shipped settings file has an empty repository object"
        assert set(settings) == set(module.GROUPS), "the shipped file should carry every group"

    def test_the_earlier_flat_actions_keys_are_still_read(self, tmp_path):
        """The first published shape kept three keys flat under `actions`.
        A consumer's override written against it must keep working."""
        path = tmp_path / "settings.json"
        path.write_text(
            json.dumps(
                {
                    "actions": {
                        "default_workflow_permissions": "write",
                        "can_approve_pull_request_reviews": True,
                        "fork_pr_approval_policy": "all_external_contributors",
                    }
                }
            ),
            encoding="utf-8",
        )
        settings = module.load_settings(path)
        assert settings["actions"] == {
            "workflow": {
                "default_workflow_permissions": "write",
                "can_approve_pull_request_reviews": True,
            },
            "fork_pr_contributor_approval": "all_external_contributors",
        }
