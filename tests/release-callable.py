# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Cut Release is callable, and a call gets the same guards a dispatch does.

Two repositories consumed by tag had copied `release.yml` to get a moving
major, because the shared publisher never writes one. A copy stops
receiving the guards, which is the whole reason the standard says called,
never copied. So the file took a `workflow_call` trigger, and this holds
it to the promise: the call's inputs are the dispatch's inputs with the
same defaults, plus what a calling repository knows about itself, and the
candidate step refuses a missing file and runs the check it is handed.
"""

from __future__ import annotations

from conftest import load_yaml, workflow_on, workflow_step_shell

RELEASE = ".github/workflows/release.yml"
STEP = "🧪 Verify The Release Candidate"


class TestTheCallMatchesTheDispatch:
    def test_every_dispatch_input_is_a_call_input_with_the_same_default(self):
        on = workflow_on(load_yaml(RELEASE))
        dispatch = on["workflow_dispatch"]["inputs"]
        call = on["workflow_call"]["inputs"]
        for name, spec in dispatch.items():
            assert name in call, f"workflow_call lacks the dispatch input {name!r}"
            assert call[name].get("default") == spec.get("default"), name
            assert call[name].get("required", False) == spec.get("required", False), name

    def test_the_call_adds_only_what_the_caller_knows(self):
        on = workflow_on(load_yaml(RELEASE))
        extra = set(on["workflow_call"]["inputs"]) - set(on["workflow_dispatch"]["inputs"])
        assert extra == {"required-files", "check-command"}
        for name in extra:
            assert on["workflow_call"]["inputs"][name].get("default") == "", name

    def test_the_standards_only_check_is_gated_on_this_repository(self):
        doc = load_yaml(RELEASE)
        step = next(s for s in doc["jobs"]["release"]["steps"] if s.get("name") == "🔗 Verify Internal References Resolve")
        assert "github.repository == 'tannergolden/standards'" in step["if"]

    def test_no_top_level_concurrency_so_a_call_can_start(self):
        """A called workflow with top-level `concurrency` fails at startup,
        with no job and no log: the first two consumer cuts died that way.
        The group lives on the release job instead."""
        doc = load_yaml(RELEASE)
        assert "concurrency" not in doc
        assert doc["jobs"]["release"]["concurrency"]["cancel-in-progress"] is False

    def test_the_prune_is_named_in_full_so_a_call_from_elsewhere_resolves_it(self):
        prune = load_yaml(RELEASE)["jobs"]["prune"]
        assert prune["uses"].startswith("tannergolden/standards/.github/workflows/prune-releases.yml@")


class TestTheCandidateStep:
    def test_a_missing_required_file_refuses_the_release(self, run_shell, tmp_path):
        (tmp_path / "action.yml").write_text("name: x\n", encoding="utf-8")
        result = run_shell(
            workflow_step_shell(RELEASE, "release", STEP),
            cwd=tmp_path,
            env={"REQUIRED_FILES": "action.yml src/kit.py", "CHECK_COMMAND": ""},
        )
        assert result.returncode != 0
        assert "src/kit.py does not exist at this commit" in result.output

    def test_the_check_command_runs_and_its_failure_is_the_releases(self, run_shell, tmp_path):
        ok = run_shell(
            workflow_step_shell(RELEASE, "release", STEP),
            cwd=tmp_path,
            env={"REQUIRED_FILES": "", "CHECK_COMMAND": "echo proven && test 1 = 1"},
        )
        assert ok.returncode == 0 and "proven" in ok.output
        bad = run_shell(
            workflow_step_shell(RELEASE, "release", STEP),
            cwd=tmp_path,
            env={"REQUIRED_FILES": "", "CHECK_COMMAND": "false"},
        )
        assert bad.returncode != 0

    def test_nothing_to_prove_passes_and_says_so(self, run_shell, tmp_path):
        result = run_shell(
            workflow_step_shell(RELEASE, "release", STEP),
            cwd=tmp_path,
            env={"REQUIRED_FILES": "", "CHECK_COMMAND": ""},
        )
        assert result.returncode == 0
        assert "No check-command given" in result.output
