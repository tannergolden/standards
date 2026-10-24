# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Every setting is compared before it is written, and a skip says why.

`apply-settings.sh` promised "a second run reports `0 change(s)` and makes
one API call", and did not keep it. Dependabot alerts, Dependabot security
updates and private vulnerability reporting were "ensured": written on every
run, counted as "3 ensured" in a plan that also said "0 change(s)", though
GitHub answers a GET on each of them with 204 or 404, which is a comparison.
A setting the repository did not report was planned as a change and sent
anyway. And the shell ran under `set -e`, so the first write GitHub refused
abandoned every write after it, with no summary and no annotation naming
the setting that failed.

The rewrite covers every setting with a standard value - the Actions
policies, the fork policies, retention, generic and AI secret detection,
CodeQL default setup, release immutability - and each of those has a gate:
public-only, private-only, plan-gated, or "only when the repository reports
it". These tests pin each gate, each comparison, and each body sent, on two
levels: the plan functions with a stubbed `gh`, where the body of a write is
visible; and the whole script through the scripted `gh` on PATH, where the
run's verdict, summary, outputs and exit code are.
"""

from __future__ import annotations

import json

import pytest
from conftest import ROOT, load_script, load_yaml

SCRIPT = ".github/scripts/apply-settings.py"
SHIPPED = ROOT / "data/repository-settings.json"
WORKFLOW = ".github/workflows/apply-standards.yml"
ACTION = ".github/actions/apply-settings/action.yml"

module = load_script(SCRIPT)

# A public repository already on the standard, as GET /repos reports it.
REPO_PUBLIC = {
    "full_name": "o/r",
    "visibility": "public",
    "private": False,
    "permissions": {"admin": True, "maintain": True, "push": True, "triage": True, "pull": True},
    "allow_squash_merge": True,
    "allow_merge_commit": False,
    "allow_rebase_merge": False,
    "squash_merge_commit_title": "PR_TITLE",
    "squash_merge_commit_message": "PR_BODY",
    "delete_branch_on_merge": True,
    "allow_auto_merge": True,
    "allow_update_branch": True,
    "web_commit_signoff_required": True,
    "has_issues": True,
    "has_discussions": True,
    "has_wiki": False,
    "has_projects": False,
    "security_and_analysis": {
        "secret_scanning": {"status": "enabled"},
        "secret_scanning_push_protection": {"status": "enabled"},
        "secret_scanning_non_provider_patterns": {"status": "enabled"},
        "secret_scanning_ai_detection": {"status": "enabled"},
    },
}
# The same repository, private, on a plan without Secret Protection: GitHub
# reports no security statuses at all.
REPO_PRIVATE = {**REPO_PUBLIC, "visibility": "private", "private": True, "security_and_analysis": None}

# Every endpoint the shipped file reads, answering as a repository on the
# standard would. A value of None is a 404 (the GET fails); "" is a 204.
HEALTHY = {
    "actions/permissions": {"enabled": True, "allowed_actions": "all", "sha_pinning_required": False},
    "actions/permissions/workflow": {"default_workflow_permissions": "read", "can_approve_pull_request_reviews": True},
    "actions/permissions/fork-pr-contributor-approval": {"approval_policy": "first_time_contributors"},
    "actions/permissions/fork-pr-workflows-private-repos": {
        "run_workflows_from_fork_pull_requests": False,
        "send_write_tokens_to_workflows": False,
        "send_secrets_and_variables": False,
        "require_approval_for_fork_pr_workflows": True,
    },
    "actions/permissions/access": {"access_level": "none"},
    "actions/permissions/artifact-and-log-retention": {"days": 90, "maximum_allowed_days": 90},
    "vulnerability-alerts": "",
    "automated-security-fixes": {"enabled": True, "paused": False},
    "private-vulnerability-reporting": {"enabled": True},
    "code-scanning/default-setup": {"state": "not-configured", "languages": [], "query_suite": "default"},
    "immutable-releases": None,
}


def writes(calls) -> list[str]:
    return [c for c in calls if " -X PUT " in c or " -X PATCH " in c or " -X DELETE " in c]


# --- The plan functions, with a stubbed gh --------------------------------


class StubApi:
    """`gh()` as the plan functions see it: canned answers, recorded calls."""

    def __init__(self, answers: dict):
        self.answers = answers
        self.calls: list[tuple] = []

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
        key = path.replace("repos/o/r", "").lstrip("/")
        if method == "GET" and key in self.answers:
            value = self.answers[key]
            if value is None:
                return module.Response(False, None, "gh: Not Found (HTTP 404)")
            return module.Response(True, value if value != "" else None)
        return module.Response(False, None, "stub: no answer (HTTP 404)")


@pytest.fixture
def plan_with(monkeypatch):
    def _plan(group, settings, repo=REPO_PUBLIC, answers=None):
        api = StubApi({**HEALTHY, **(answers or {})})
        monkeypatch.setattr(module, "gh", api)
        plan = module.Plan()
        ctx = module.Context("o/r", repo, settings, plan)
        getattr(module, f"plan_{group}")(ctx)
        plan.api = api
        return plan

    return _plan


def line(plan, name):
    hits = [ln for ln in plan.lines if f"  {name} " in ln or ln.rstrip().endswith(name)]
    return hits[0] if hits else ""


class TestTheRepositoryObject:
    def test_a_key_the_repository_does_not_report_is_skipped_not_sent(self, plan_with):
        """The defect: an unreported key was planned as a change and sent."""
        plan = plan_with("repository", {"repository": {"pull_request_creation_policy": "all"}})
        assert plan.changed == 0 and plan.skipped == 1
        assert "not reported" in line(plan, "pull_request_creation_policy")
        assert plan.writes == []

    def test_only_the_differences_travel_in_the_patch(self, plan_with):
        plan = plan_with("repository", {"repository": {"has_wiki": False, "has_issues": True, "has_projects": True}})
        assert plan.changed == 1 and plan.unchanged == 2
        assert plan.writes[0][1:4] == ("PATCH", "repos/o/r", {"has_projects": True})


class TestTheActionsPolicies:
    def test_the_permissions_put_keeps_the_allowlist_it_did_not_set(self, plan_with):
        """A PUT replaces the whole policy, so the current allowed_actions
        must travel with the change rather than be reset to the default."""
        plan = plan_with(
            "actions",
            {"actions": {"permissions": {"enabled": True, "sha_pinning_required": False}}},
            answers={"actions/permissions": {"enabled": True, "allowed_actions": "selected", "sha_pinning_required": True}},
        )
        assert plan.changed == 1
        assert plan.writes[0][1:4] == (
            "PUT",
            "repos/o/r/actions/permissions",
            {"enabled": True, "allowed_actions": "selected", "sha_pinning_required": False},
        )

    def test_the_allowlist_only_applies_when_actions_are_selected(self, plan_with):
        plan = plan_with(
            "actions",
            {"actions": {"selected_actions": {"github_owned_allowed": True}}},
        )
        assert plan.skipped == 1 and "allowed_actions is selected" in line(plan, "actions.selected_actions")
        assert not any(path.endswith("selected-actions") for _m, path, _b in plan.api.calls)

    def test_the_allowlist_compares_patterns_regardless_of_order(self, plan_with):
        plan = plan_with(
            "actions",
            {"actions": {"selected_actions": {"patterns_allowed": ["b/*", "a/*"]}}},
            answers={
                "actions/permissions": {"enabled": True, "allowed_actions": "selected", "sha_pinning_required": False},
                "actions/permissions/selected-actions": {"github_owned_allowed": True, "verified_allowed": False, "patterns_allowed": ["a/*", "b/*"]},
            },
        )
        assert plan.changed == 0 and plan.unchanged == 1

    def test_every_differing_key_in_a_policy_is_named_not_just_the_first(self, plan_with):
        """`any()` over a generator stops at the first difference, so a
        policy with two drifted keys named one change and wrote two."""
        plan = plan_with(
            "actions",
            {"actions": {"workflow": {"default_workflow_permissions": "write", "can_approve_pull_request_reviews": True}}},
            answers={"actions/permissions/workflow": {"default_workflow_permissions": "read", "can_approve_pull_request_reviews": False}},
        )
        assert plan.changed == 2, plan.lines
        assert line(plan, "actions.workflow.default_workflow_permissions") and line(plan, "actions.workflow.can_approve_pull_request_reviews")

    def test_the_workflow_token_put_carries_both_keys(self, plan_with):
        plan = plan_with(
            "actions",
            {"actions": {"workflow": {"default_workflow_permissions": "write"}}},
            answers={"actions/permissions/workflow": {"default_workflow_permissions": "read", "can_approve_pull_request_reviews": False}},
        )
        assert plan.writes[0][1:4] == (
            "PUT",
            "repos/o/r/actions/permissions/workflow",
            {"default_workflow_permissions": "write", "can_approve_pull_request_reviews": False},
        )

    def test_fork_approval_is_public_only_and_never_read_on_a_private_repository(self, plan_with):
        plan = plan_with("actions", {"actions": {"fork_pr_contributor_approval": "first_time_contributors"}}, repo=REPO_PRIVATE)
        assert "public repositories only" in line(plan, "actions.fork_pr_contributor_approval")
        assert plan.api.calls == []

    def test_the_private_fork_policy_is_private_only(self, plan_with):
        settings = {"actions": {"fork_pr_workflows_private_repos": {"run_workflows_from_fork_pull_requests": False}}}
        public = plan_with("actions", settings)
        assert "private repositories only" in line(public, "actions.fork_pr_workflows_private_repos")
        private = plan_with(
            "actions",
            settings,
            repo=REPO_PRIVATE,
            answers={
                "actions/permissions/fork-pr-workflows-private-repos": {
                    "run_workflows_from_fork_pull_requests": True,
                    "send_write_tokens_to_workflows": True,
                    "send_secrets_and_variables": False,
                    "require_approval_for_fork_pr_workflows": False,
                }
            },
        )
        assert private.changed == 1
        # All four keys travel: the endpoint requires the first and replaces the rest.
        assert private.writes[0][3] == {
            "run_workflows_from_fork_pull_requests": False,
            "send_write_tokens_to_workflows": True,
            "send_secrets_and_variables": False,
            "require_approval_for_fork_pr_workflows": False,
        }

    def test_outside_access_is_private_only(self, plan_with):
        public = plan_with("actions", {"actions": {"access_level": "none"}})
        assert "private repositories only" in line(public, "actions.access_level")
        private = plan_with("actions", {"actions": {"access_level": "none"}}, repo=REPO_PRIVATE, answers={"actions/permissions/access": {"access_level": "user"}})
        assert private.writes[0][1:4] == ("PUT", "repos/o/r/actions/permissions/access", {"access_level": "none"})

    def test_retention_above_the_repository_maximum_is_skipped_with_the_ceiling(self, plan_with):
        plan = plan_with("actions", {"actions": {"artifact_and_log_retention_days": 400}})
        assert plan.changed == 0
        assert "maximum of 90" in line(plan, "actions.artifact_and_log_retention_days")

    def test_retention_below_it_is_written(self, plan_with):
        plan = plan_with("actions", {"actions": {"artifact_and_log_retention_days": 30}})
        assert plan.writes[0][1:4] == ("PUT", "repos/o/r/actions/permissions/artifact-and-log-retention", {"days": 30})

    def test_cache_limits_skip_where_the_plan_lacks_them_and_tolerate_a_refusal(self, plan_with):
        missing = plan_with("actions", {"actions": {"cache_retention_days": 14}}, answers={"actions/cache/retention-limit": None})
        assert "plan" in line(missing, "actions.cache_retention_days")
        present = plan_with("actions", {"actions": {"cache_retention_days": 14}}, answers={"actions/cache/retention-limit": {"max_cache_retention_days": 7}})
        _name, method, _path, body, _done, tolerant = present.writes[0]
        assert (method, body, tolerant) == ("PUT", {"max_cache_retention_days": 14}, True)

    def test_an_unreadable_policy_is_a_skip_naming_the_likely_cause(self, plan_with):
        plan = plan_with("actions", {"actions": {"workflow": {"default_workflow_permissions": "write"}}}, answers={"actions/permissions/workflow": None})
        assert "Actions enabled" in line(plan, "actions.workflow")
        assert plan.writes == []


class TestTheSecurityFeatures:
    def test_the_free_features_are_switched_on_for_a_public_repository_that_reports_nothing(self, plan_with):
        repo = {**REPO_PUBLIC, "security_and_analysis": None}
        plan = plan_with("security", {"security": {"secret_scanning": True, "secret_scanning_push_protection": True}}, repo=repo)
        assert plan.changed == 2
        bodies = [w[3] for w in plan.writes]
        assert {"security_and_analysis": {"secret_scanning": {"status": "enabled"}}} in bodies
        assert all(w[1:3] == ("PATCH", "repos/o/r") for w in plan.writes)
        assert not any(w[5] for w in plan.writes), "a free feature's refusal is an error, not a warning"

    def test_the_same_features_are_skipped_on_a_private_repository_without_the_plan(self, plan_with):
        plan = plan_with("security", {"security": {"secret_scanning": True}}, repo=REPO_PRIVATE)
        assert plan.changed == 0
        assert "Secret Protection" in line(plan, "secret_scanning")

    def test_a_plan_gated_feature_is_written_only_where_reported_and_tolerantly(self, plan_with):
        unreported = plan_with("security", {"security": {"secret_scanning_ai_detection": True}}, repo={**REPO_PUBLIC, "security_and_analysis": {}})
        assert "not reported" in line(unreported, "secret_scanning_ai_detection")
        reported = plan_with(
            "security",
            {"security": {"secret_scanning_ai_detection": True}},
            repo={**REPO_PUBLIC, "security_and_analysis": {"secret_scanning_ai_detection": {"status": "disabled"}}},
        )
        assert reported.changed == 1 and reported.writes[0][5] is True

    def test_dependabot_alerts_are_compared_through_the_get(self, plan_with):
        """The defect: written on every run and counted as 'ensured'."""
        on = plan_with("security", {"security": {"vulnerability_alerts": True}})
        assert on.changed == 0 and on.writes == []
        off = plan_with("security", {"security": {"vulnerability_alerts": True}}, answers={"vulnerability-alerts": None})
        assert off.writes[0][1:4] == ("PUT", "repos/o/r/vulnerability-alerts", None)

    def test_security_updates_are_compared_and_disabled_with_a_delete(self, plan_with):
        off = plan_with("security", {"security": {"automated_security_fixes": True}}, answers={"automated-security-fixes": None})
        assert off.writes[0][1:3] == ("PUT", "repos/o/r/automated-security-fixes")
        unwanted = plan_with("security", {"security": {"automated_security_fixes": False}})
        assert unwanted.writes[0][1:3] == ("DELETE", "repos/o/r/automated-security-fixes")

    def test_alerts_are_written_before_the_updates_that_need_them(self, plan_with):
        plan = plan_with(
            "security",
            {"security": {"automated_security_fixes": True, "vulnerability_alerts": True}},
            answers={"vulnerability-alerts": None, "automated-security-fixes": None},
        )
        assert [w[2] for w in plan.writes] == ["repos/o/r/vulnerability-alerts", "repos/o/r/automated-security-fixes"]

    def test_private_vulnerability_reporting_is_public_only(self, plan_with):
        plan = plan_with("security", {"security": {"private_vulnerability_reporting": True}}, repo=REPO_PRIVATE)
        assert "public repositories only" in line(plan, "private_vulnerability_reporting")

    def test_default_setup_is_skipped_where_code_scanning_is_unavailable(self, plan_with):
        plan = plan_with("security", {"security": {"code_scanning_default_setup": {"state": "not-configured"}}}, answers={"code-scanning/default-setup": None})
        assert plan.changed == 0 and "Code Security" in line(plan, "code_scanning_default_setup")

    def test_default_setup_is_turned_off_where_it_would_silence_the_stub(self, plan_with):
        plan = plan_with(
            "security",
            {"security": {"code_scanning_default_setup": {"state": "not-configured"}}},
            answers={"code-scanning/default-setup": {"state": "configured", "languages": ["python"], "query_suite": "default"}},
        )
        assert plan.writes[0][1:4] == ("PATCH", "repos/o/r/code-scanning/default-setup", {"state": "not-configured"})


class TestReleaseImmutability:
    def test_a_404_means_off_which_matches_the_standard(self, plan_with):
        plan = plan_with("releases", {"releases": {"immutable": False}})
        assert plan.changed == 0 and plan.unchanged == 1

    def test_an_owner_enforced_setting_is_skipped_not_fought(self, plan_with):
        plan = plan_with("releases", {"releases": {"immutable": False}}, answers={"immutable-releases": {"enabled": True, "enforced_by_owner": True}})
        assert plan.changed == 0 and "enforced" in line(plan, "releases.immutable")

    def test_a_repository_setting_is_turned_off_with_a_delete(self, plan_with):
        plan = plan_with("releases", {"releases": {"immutable": False}}, answers={"immutable-releases": {"enabled": True, "enforced_by_owner": False}})
        assert plan.writes[0][1:3] == ("DELETE", "repos/o/r/immutable-releases")


class TestHttpStatusParsing:
    def test_reads_the_status_gh_reports(self):
        assert module.http_status("gh: Resource not accessible by integration (HTTP 403)") == 403
        assert module.http_status("gh: Conflict (HTTP 409)") == 409

    def test_is_none_without_one(self):
        assert module.http_status("fake gh: no route for: api") is None
        assert module.http_status("") is None


# --- The whole script, through the scripted gh on PATH ---------------------


class World:
    """A repository the script can read and write through `fake_gh`.

    Routes are matched by substring in the order they were added, and
    `repos/o/r` is a substring of every other path, so the longest paths are
    routed first and the repository object last.
    """

    def __init__(self, fake_gh, tmp_path, repo=None):
        self.gh = fake_gh
        self.tmp_path = tmp_path
        self.repo = dict(REPO_PUBLIC if repo is None else repo)
        self.answers = dict(HEALTHY)
        self.refused: list[str] = []

    def answer(self, path, value):
        self.answers[path] = value
        return self

    def refuse(self, method, path):
        self.refused.append(f"-X {method} repos/o/r/{path}")
        return self

    def run(self, run_script, settings=None, dry_run="true", target="o/r", **env):
        for path in sorted(self.answers, key=len, reverse=True):
            value = self.answers[path]
            if value is None:
                self.gh.route(f"-X GET repos/o/r/{path}", "", code=1)
            else:
                self.gh.route(f"-X GET repos/o/r/{path}", "" if value == "" else json.dumps(value))
        for match in self.refused:
            self.gh.route(match, "", code=1)
        for method in ("PUT", "PATCH", "DELETE"):
            self.gh.route(f"-X {method} repos/o/r", "")
        self.gh.route("repo view", json.dumps({"nameWithOwner": "o/r"}))
        self.gh.route("-X GET repos/o/r", json.dumps(self.repo))
        if settings is None:
            settings_file = SHIPPED
        else:
            settings_file = self.tmp_path / "settings.json"
            settings_file.write_text(json.dumps(settings), encoding="utf-8")
        variables = {"GH_TOKEN": "t", "SETTINGS_FILE": str(settings_file), "DRY_RUN": dry_run}
        if target:
            variables["TARGET_REPO"] = target
        variables.update(env)
        return run_script(SCRIPT, cwd=self.tmp_path, env=self.gh.env(**variables))


class TestAHealthyRepositoryIsLeftAlone:
    def test_the_shipped_file_plans_nothing_and_writes_nothing(self, run_script, fake_gh, tmp_path):
        result = World(fake_gh, tmp_path).run(run_script)
        assert result.returncode == 0, result
        assert "Plan: 0 change(s)" in result.stdout
        assert "already matches the published set" in result.summary
        assert writes(fake_gh.calls) == [], writes(fake_gh.calls)
        assert result.outputs["changes"] == "0" and result.outputs["drift"] == "false"

    def test_a_private_repository_skips_the_public_gates_and_passes(self, run_script, fake_gh, tmp_path):
        result = World(fake_gh, tmp_path, repo=REPO_PRIVATE).run(run_script)
        assert result.returncode == 0, result
        assert "Plan: 0 change(s)" in result.stdout
        for name in ("actions.fork_pr_contributor_approval", "private_vulnerability_reporting"):
            assert f"SKIP    {name}" in result.stdout, result.stdout
        assert "SKIP    secret_scanning " in result.stdout
        assert writes(fake_gh.calls) == []

    def test_the_drift_check_passes_on_a_healthy_repository(self, run_script, fake_gh, tmp_path):
        result = World(fake_gh, tmp_path).run(run_script, FAIL_ON_DRIFT="true")
        assert result.returncode == 0, result


class TestADriftedRepository:
    def drifted(self, fake_gh, tmp_path):
        world = World(fake_gh, tmp_path)
        world.repo["has_wiki"] = True
        world.answer("actions/permissions/workflow", {"default_workflow_permissions": "write", "can_approve_pull_request_reviews": True})
        world.answer("vulnerability-alerts", None)
        return world

    def test_a_dry_run_names_every_difference_and_writes_none(self, run_script, fake_gh, tmp_path):
        result = self.drifted(fake_gh, tmp_path).run(run_script)
        assert result.returncode == 0, result
        for expected in ("CHANGE  has_wiki", "CHANGE  actions.workflow.default_workflow_permissions", "CHANGE  vulnerability_alerts"):
            assert expected in result.stdout, result.stdout
        assert "Plan: 3 change(s)" in result.stdout
        assert "Dry run" in result.stdout and "would be applied" in result.summary
        assert writes(fake_gh.calls) == []
        assert result.outputs["changes"] == "3" and result.outputs["drift"] == "true"

    def test_the_drift_check_fails_naming_the_count(self, run_script, fake_gh, tmp_path):
        result = self.drifted(fake_gh, tmp_path).run(run_script, FAIL_ON_DRIFT="true")
        assert result.returncode != 0, result
        assert "::error title=Repository settings::Drift: 3 setting(s)" in result.output
        assert writes(fake_gh.calls) == [], "a drift check must never write"

    def test_a_real_run_writes_each_difference_and_says_so(self, run_script, fake_gh, tmp_path):
        result = self.drifted(fake_gh, tmp_path).run(run_script, dry_run="false")
        assert result.returncode == 0, result
        done = writes(fake_gh.calls)
        assert any("-X PATCH repos/o/r" in c and "actions" not in c for c in done)
        assert any("-X PUT repos/o/r/actions/permissions/workflow" in c for c in done)
        assert any("-X PUT repos/o/r/vulnerability-alerts" in c for c in done)
        assert "Applied **3** change(s)" in result.summary
        assert "A re-run now plans `0 change(s)`" in result.summary

    def test_one_refused_write_does_not_abandon_the_rest(self, run_script, fake_gh, tmp_path):
        """The defect: `set -e` stopped at the first refusal, silently."""
        world = self.drifted(fake_gh, tmp_path).refuse("PUT", "actions/permissions/workflow")
        result = world.run(run_script, dry_run="false")
        assert result.returncode != 0, result
        assert "::error title=Repository settings::Could not apply the Actions workflow-token policy" in result.output
        assert any("-X PUT repos/o/r/vulnerability-alerts" in c for c in writes(fake_gh.calls)), (
            "the write after the refused one was never attempted"
        )
        assert "could not be applied" in result.summary and "Not applied" in result.summary
        assert result.outputs["failed"] == "1"


class TestTheTokenAndTheTarget:
    def test_a_token_without_admin_fails_before_comparing_anything(self, run_script, fake_gh, tmp_path):
        world = World(fake_gh, tmp_path)
        world.repo["permissions"] = {"admin": False, "push": True, "pull": True}
        result = world.run(run_script)
        assert result.returncode != 0, result
        assert "ADMIN_TOKEN" in result.output and "cannot administer" in result.output
        assert not any("actions/permissions" in c for c in fake_gh.calls)

    def test_an_unreadable_repository_is_named(self, run_script, fake_gh, tmp_path):
        fake_gh.route("repos/o/r", "", code=1)
        result = run_script(SCRIPT, cwd=tmp_path, env=fake_gh.env(GH_TOKEN="t", TARGET_REPO="o/r", SETTINGS_FILE=str(SHIPPED)))
        assert result.returncode != 0
        assert "Could not read 'o/r'" in result.output

    def test_the_target_is_inferred_from_the_checkout_when_not_given(self, run_script, fake_gh, tmp_path):
        result = World(fake_gh, tmp_path).run(run_script, target="")
        assert result.returncode == 0, result
        assert "Target:     o/r" in result.stdout
        assert any(c.startswith("repo view") for c in fake_gh.calls)

    def test_the_earlier_flat_actions_keys_still_compare(self, run_script, fake_gh, tmp_path):
        result = World(fake_gh, tmp_path).run(
            run_script,
            settings={"actions": {"default_workflow_permissions": "read", "fork_pr_approval_policy": "first_time_contributors"}},
        )
        assert result.returncode == 0, result
        assert "note: the settings file uses the earlier flat actions key(s)" in result.stdout
        assert "Plan: 0 change(s), 2 already correct" in result.stdout


# --- The shipped file and its wiring ---------------------------------------


class TestEverySettingHasAReason:
    """The file promises "the reason is on the line beside it"."""

    @pytest.fixture
    def document(self):
        return json.loads(SHIPPED.read_text(encoding="utf-8"))

    def test_the_repository_group(self, document):
        assert set(document["repository"]) == set(document["_why"])

    def test_the_actions_group(self, document):
        # A nested key is covered by a reason for itself or for its block:
        # the four private-fork switches are one decision, reasoned once.
        reasons = set(document["_why_actions"])
        unreasoned = []
        for key, value in document["actions"].items():
            inner = value if isinstance(value, dict) else {None: value}
            for name in inner:
                dotted = key if name is None else f"{key}.{name}"
                if dotted not in reasons and key not in reasons:
                    unreasoned.append(dotted)
        assert not unreasoned, f"actions settings without a reason: {unreasoned}"

    def test_the_security_group(self, document):
        assert set(document["security"]) == set(document["_why_security"])

    def test_the_releases_group(self, document):
        assert set(document["releases"]) == set(document["_why_releases"])

    def test_nothing_the_script_refuses_is_published(self, document):
        assert not set(document["repository"]) & module.REFUSED_REPOSITORY_KEYS

    def test_every_group_is_described_in_the_settings_document(self, document):
        text = (ROOT / "docs/operations/Repository-Settings.md").read_text(encoding="utf-8")
        for group in module.GROUPS:
            assert f"`{group}`" in text, f"docs/operations/Repository-Settings.md never names the `{group}` group"


WORKFLOWS = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / ".github/workflows").glob("*.yml"))


class TestTheReadOnlyDefaultCapsNothingHere:
    """The published token default is read-only, which a job never meets if it declares its own.

    A `permissions:` key sets a job's token whatever the repository default
    says, so the default is only what a job gets when it declares nothing.
    The reason beside the setting says every workflow here declares the key
    for every job; these hold it to that, so the default protects a workflow
    that forgets the key rather than breaking one that leaned on write.
    """

    def test_the_shipped_default_is_read(self):
        document = json.loads(SHIPPED.read_text(encoding="utf-8"))
        assert document["actions"]["workflow"]["default_workflow_permissions"] == "read"

    @pytest.mark.parametrize("rel", WORKFLOWS)
    def test_every_job_declares_its_permissions(self, rel):
        undeclared = [job for job, spec in load_yaml(rel)["jobs"].items() if "permissions" not in spec]
        assert not undeclared, (
            f"{rel}: {undeclared} declare no permissions, so they run with the repository default, "
            "which is read-only on the standard"
        )


class TestTheDriftCheckIsWired:
    def test_the_workflow_offers_it_and_hands_it_down(self):
        doc = load_yaml(WORKFLOW)
        inputs = doc.get(True, doc.get("on"))["workflow_call"]["inputs"]
        assert inputs["fail-on-drift"]["default"] is False
        step = next(s for s in doc["jobs"]["settings"]["steps"] if "apply-settings" in (s.get("uses") or ""))
        assert step["with"]["fail-on-drift"] == "${{ inputs.fail-on-drift }}"
        assert step.get("id") == "apply"
        assert doc["jobs"]["settings"]["outputs"]["drift"] == "${{ steps.apply.outputs.drift }}"

    def test_the_action_declares_it_and_its_outputs(self):
        doc = load_yaml(ACTION)
        assert doc["inputs"]["fail-on-drift"]["default"] == "false"
        for name in ("changes", "unchanged", "skipped", "failed", "drift"):
            assert doc["outputs"][name]["value"] == f"${{{{ steps.apply.outputs.{name} }}}}"
        step = doc["runs"]["steps"][0]
        assert step["id"] == "apply"
        assert step["env"]["FAIL_ON_DRIFT"] == "${{ inputs.fail-on-drift }}"
        assert "apply-settings.py" in step["run"]
