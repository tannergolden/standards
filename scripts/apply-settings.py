#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
# =============================================================================
# Apply Repository Settings - the settings half of "set up to standard"
# =============================================================================
# Reads data/repository-settings.json and brings a repository's settings in
# line with it. Rulesets are NOT touched here: they live in data/rulesets/ and
# are applied by apply-rulesets.sh, because branch protection is the change
# that can lock a repository's own automation out of it.
#
# READ BEFORE WRITE, EVERYWHERE. Every setting is compared against what the
# repository reports and only the differences are sent, so a no-op run makes
# no write at all, reports "0 change(s)", and anything else in the plan is a
# real difference. That holds for the Dependabot and vulnerability-reporting
# toggles too, which an earlier version re-sent on every run: GitHub answers
# 204 or 404 to a GET on each of them, which is a comparison.
#
# FOUR GROUPS, ONE PLAN. `repository` is the repository object, one PATCH.
# `actions` is everything under Settings → Actions → General, each key its
# own endpoint. `security` is the Advanced Security page: statuses on the
# repository object, and toggles with endpoints of their own. `releases` is
# the Releases section. The settings file mirrors that shape, and everything
# deliberately NOT written lives in its _excluded block so absence is a
# decision rather than an oversight.
#
# A SKIP IS A FACT, NOT A FAILURE. Some settings are gated on visibility
# (fork approvals are public-only, the private-fork policy private-only),
# some on plan (Secret Protection, Code Security, cache limits), and some a
# repository simply does not report. Each is skipped with the reason on its
# plan line, because a repository that cannot have a feature has not
# misconfigured anything - and a setting the repository does not report is
# never guessed at.
#
# ONE REFUSED WRITE DOES NOT ABANDON THE REST. Each write is attempted on its
# own and reported on its own: a refusal names the setting, the reason and the
# consequence, everything after it is still applied, and the run fails at the
# end. A 409 is the owner's policy refusing the change and is a warning; a
# plan-gated feature GitHub turns down is a warning; anything else is an error.
#
# THE TOKEN IS CHECKED FIRST. The repository object says whether the token
# administers it, so a token that cannot fails here with the fix named,
# rather than as a 403 on the first write.
#
# DRY RUN BY DEFAULT, like apply-rulesets.sh. A caller that forgets the flag
# gets a plan rather than a change. With FAIL_ON_DRIFT=true a dry run also
# fails when the plan is not empty, which makes a scheduled dry run a drift
# check: a healthy repository exits 0 and reports "0 change(s)".
#
# In Actions, the plan is also written to the job's step summary, and the
# counts to the step's outputs, so the verdict is readable without the log.
#
# Usage:
#     python3 scripts/apply-settings.py                  # preview
#     DRY_RUN=false python3 scripts/apply-settings.py    # apply
#     TARGET_REPO=owner/name DRY_RUN=false python3 scripts/apply-settings.py
#
# Requires: gh, authenticated with a token holding administration write.
# Optional: TARGET_REPO     defaults to the repository gh is pointed at
#           SETTINGS_FILE   defaults to ../data/repository-settings.json
#           DRY_RUN         defaults to TRUE; set false to actually apply
#           FAIL_ON_DRIFT   with a dry run: exit 1 when anything would change
# =============================================================================
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys

TITLE = "Repository settings"

GROUPS = ("repository", "actions", "security", "releases")

# Keys the script refuses in ANY settings file. Visibility and archiving are
# human acts with consequences no sync should have; the default branch is
# structure the rulesets stand on; security statuses have a group of their
# own so there is one place that knows how they are gated.
REFUSED_REPOSITORY_KEYS = {
    "private",
    "visibility",
    "archived",
    "default_branch",
    "security_and_analysis",
}

ACTIONS_KEYS = {
    "permissions",
    "selected_actions",
    "workflow",
    "fork_pr_contributor_approval",
    "fork_pr_workflows_private_repos",
    "access_level",
    "artifact_and_log_retention_days",
    "cache_retention_days",
    "cache_storage_limit_gb",
}
# The first published shape of the file kept these three flat under
# `actions`. A consumer's override written against it is still read.
LEGACY_ACTIONS_KEYS = {
    "default_workflow_permissions": ("workflow", "default_workflow_permissions"),
    "can_approve_pull_request_reviews": ("workflow", "can_approve_pull_request_reviews"),
    "fork_pr_approval_policy": ("fork_pr_contributor_approval", None),
}
PERMISSION_KEYS = ("enabled", "allowed_actions", "sha_pinning_required")
SELECTED_KEYS = ("github_owned_allowed", "verified_allowed", "patterns_allowed")
WORKFLOW_KEYS = ("default_workflow_permissions", "can_approve_pull_request_reviews")
PRIVATE_FORK_KEYS = (
    "run_workflows_from_fork_pull_requests",
    "send_write_tokens_to_workflows",
    "send_secrets_and_variables",
    "require_approval_for_fork_pr_workflows",
)

# Statuses on the repository object's security_and_analysis block.
SECURITY_STATUS_KEYS = {
    "advanced_security",
    "code_security",
    "secret_scanning",
    "secret_scanning_push_protection",
    "secret_scanning_non_provider_patterns",
    "secret_scanning_ai_detection",
    "secret_scanning_delegated_alert_dismissal",
    "secret_scanning_delegated_bypass",
}
# Free on every public repository, so a public repository that does not
# report one can still have it switched on. Everything else in the set above
# is written only where the repository already reports the feature.
FREE_ON_PUBLIC = {"secret_scanning", "secret_scanning_push_protection"}
# Toggles with endpoints of their own: a GET that answers 204/200 or 404.
SECURITY_TOGGLE_KEYS = {
    "vulnerability_alerts",
    "automated_security_fixes",
    "private_vulnerability_reporting",
}
SECURITY_KEYS = SECURITY_STATUS_KEYS | SECURITY_TOGGLE_KEYS | {"code_scanning_default_setup"}
DEFAULT_SETUP_KEYS = (
    "state",
    "query_suite",
    "languages",
    "threat_model",
    "runner_type",
    "runner_label",
)
RELEASES_KEYS = {"immutable"}

HTTP_STATUS = re.compile(r"\(HTTP (\d{3})\)")


def error(message: str) -> None:
    print(f"::error title={TITLE}::{message}")


def warning(message: str) -> None:
    print(f"::warning title={TITLE}::{message}")


def truthy(value: str | None, default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("1", "true", "yes")


def http_status(stderr: str) -> int | None:
    """The HTTP status `gh api` reports on failure, when it reports one."""
    match = HTTP_STATUS.search(stderr or "")
    return int(match.group(1)) if match else None


def show(value) -> str:
    """A setting's value as the plan prints it: strings bare, the rest JSON."""
    if value is None:
        return "unreported"
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True)


class SettingsError(Exception):
    """A settings file the script refuses, with the sentence that says why."""


class Response:
    def __init__(self, ok: bool, data=None, stderr: str = ""):
        self.ok = ok
        self.data = data
        self.stderr = stderr or ""
        self.status = http_status(self.stderr)

    @property
    def reason(self) -> str:
        lines = [ln.strip() for ln in self.stderr.splitlines() if ln.strip()]
        return (lines[-1] if lines else "no reason given")[:200]


def gh(method: str, path: str, body=None) -> Response:
    """One `gh api` call, the method always spelled out.

    `gh` carries the token and the host, so this runs wherever `gh auth
    login` has been done or GH_TOKEN is set, and the tests can put a scripted
    `gh` on PATH. A failed call never raises: the caller decides whether a
    404 is "not enabled", a 409 is "the owner's policy", or an error.
    """
    args = ["gh", "api", "-X", method, path]
    payload = None
    if body is not None:
        args += ["--input", "-"]
        payload = json.dumps(body)
    proc = subprocess.run(args, input=payload, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return Response(False, None, proc.stderr)
    text = proc.stdout.strip()
    if not text:
        return Response(True, None)
    try:
        return Response(True, json.loads(text))
    except json.JSONDecodeError:
        return Response(True, text)


# --- The settings file ----------------------------------------------------


def expect_object(value, where: str) -> dict:
    if not isinstance(value, dict):
        raise SettingsError(f"'{where}' must be a JSON object, and is {type(value).__name__}.")
    return value


def expect_bool(value, where: str) -> bool:
    if not isinstance(value, bool):
        raise SettingsError(f"'{where}' must be true or false, and is {show(value)}.")
    return value


def expect_int(value, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SettingsError(f"'{where}' must be a whole number, and is {show(value)}.")
    return value


def expect_str(value, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise SettingsError(f"'{where}' must be a non-empty string, and is {show(value)}.")
    return value


def unknown(keys, allowed, where: str) -> None:
    extra = sorted(k for k in keys if k not in allowed)
    if extra:
        raise SettingsError(
            f"'{where}' has key(s) this script does not know: {', '.join(extra)}. "
            f"It applies {', '.join(sorted(allowed))}; see data/repository-settings.json."
        )


def load_settings(path: pathlib.Path) -> dict:
    """Read, validate and normalise a settings file, or refuse it.

    ⚠️ REFUSE RATHER THAN INTERPRET. `settings-file` is a public input, so
    this is a caller's file and a caller's mistake to be told about. A file
    that yields nothing to compare used to produce a green run saying the
    repository "already matches the published set", which is the worst
    available message: it reports the repository as correct having compared
    nothing. A key under the wrong group, or misspelled, is refused by name
    for the same reason: silently ignoring it would report a standard as
    applied that was never read.
    """
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SettingsError(f"No settings file at {path}.") from None
    except json.JSONDecodeError as exc:
        raise SettingsError(f"{path} is not valid JSON: {exc}.") from None

    document = expect_object(document, str(path))
    unknown((k for k in document if not k.startswith("_")), GROUPS, str(path))
    settings = {}

    repository = document.get("repository")
    if repository is not None:
        repository = expect_object(repository, "repository")
        refused = sorted(k for k in repository if k in REFUSED_REPOSITORY_KEYS)
        if refused:
            raise SettingsError(
                f"'repository' carries {', '.join(refused)}, which this script never writes: "
                "visibility, archiving and the default branch are human acts, and security "
                "statuses belong under 'security', where their gates are known."
            )
        settings["repository"] = dict(repository)

    actions = document.get("actions")
    if actions is not None:
        actions = dict(expect_object(actions, "actions"))
        moved = []
        for old, (new, inner) in LEGACY_ACTIONS_KEYS.items():
            if old not in actions:
                continue
            value = actions.pop(old)
            if inner is None:
                actions[new] = value
            else:
                actions.setdefault(new, {})
                expect_object(actions[new], f"actions.{new}")[inner] = value
            moved.append(old)
        if moved:
            print(
                f"note: the settings file uses the earlier flat actions key(s) {', '.join(moved)}; "
                "read as actions.workflow and actions.fork_pr_contributor_approval."
            )
        unknown(actions, ACTIONS_KEYS, "actions")
        if "permissions" in actions:
            unknown(expect_object(actions["permissions"], "actions.permissions"), PERMISSION_KEYS, "actions.permissions")
        if "selected_actions" in actions:
            unknown(expect_object(actions["selected_actions"], "actions.selected_actions"), SELECTED_KEYS, "actions.selected_actions")
        if "workflow" in actions:
            unknown(expect_object(actions["workflow"], "actions.workflow"), WORKFLOW_KEYS, "actions.workflow")
        if "fork_pr_contributor_approval" in actions:
            expect_str(actions["fork_pr_contributor_approval"], "actions.fork_pr_contributor_approval")
        if "fork_pr_workflows_private_repos" in actions:
            block = expect_object(actions["fork_pr_workflows_private_repos"], "actions.fork_pr_workflows_private_repos")
            unknown(block, PRIVATE_FORK_KEYS, "actions.fork_pr_workflows_private_repos")
            for key, value in block.items():
                expect_bool(value, f"actions.fork_pr_workflows_private_repos.{key}")
        if "access_level" in actions:
            expect_str(actions["access_level"], "actions.access_level")
        for key in ("artifact_and_log_retention_days", "cache_retention_days", "cache_storage_limit_gb"):
            if key in actions:
                expect_int(actions[key], f"actions.{key}")
        settings["actions"] = actions

    security = document.get("security")
    if security is not None:
        security = expect_object(security, "security")
        unknown(security, SECURITY_KEYS, "security")
        for key, value in security.items():
            if key == "code_scanning_default_setup":
                block = expect_object(value, "security.code_scanning_default_setup")
                unknown(block, DEFAULT_SETUP_KEYS, "security.code_scanning_default_setup")
                if block.get("state") not in ("configured", "not-configured"):
                    raise SettingsError(
                        "'security.code_scanning_default_setup.state' must be configured or not-configured."
                    )
            else:
                expect_bool(value, f"security.{key}")
        settings["security"] = dict(security)

    releases = document.get("releases")
    if releases is not None:
        releases = expect_object(releases, "releases")
        unknown(releases, RELEASES_KEYS, "releases")
        for key, value in releases.items():
            expect_bool(value, f"releases.{key}")
        settings["releases"] = dict(releases)

    if not any(settings.values()):
        raise SettingsError(
            f"'{path}' names nothing to apply: it needs at least one non-empty group out of "
            f"{', '.join(GROUPS)}; see data/repository-settings.json."
        )
    return settings


# --- The plan ---------------------------------------------------------------


class Plan:
    """Every comparison's outcome, and the writes a real run performs.

    A write is data (method, path, body) rather than a closure, so a dry run
    can prove it performed none and a test can read exactly what would be
    sent. `tolerant` marks a write whose refusal is a warning: a plan-gated
    feature GitHub turns down leaves the repository as it was, which is a
    fact about the plan, not a failed run.
    """

    def __init__(self):
        self.lines: list[str] = []
        self.changed = 0
        self.unchanged = 0
        self.skipped = 0
        self.writes: list[tuple] = []

    def change(self, name: str, have, want) -> None:
        self.lines.append(f"  CHANGE  {name:<40} {show(have)} -> {show(want)}")
        self.changed += 1

    def skip(self, name: str, reason: str) -> None:
        self.lines.append(f"  SKIP    {name:<40} {reason}")
        self.skipped += 1

    def same(self) -> None:
        self.unchanged += 1

    def write(self, name: str, method: str, path: str, body, done: str, tolerant: bool = False) -> None:
        self.writes.append((name, method, path, body, done, tolerant))

    def compare(self, name: str, have, want) -> bool:
        """Record one comparison; True when it differs."""
        if have == want:
            self.same()
            return False
        self.change(name, have, want)
        return True

    def compare_each(self, prefix: str, have: dict, want: dict) -> bool:
        """Record every key's comparison; True when any differs.

        Every key, not the first that differs: `any()` over a generator
        stops there, and the plan would then name one change while the
        write carried two.
        """
        differs = False
        for key, value in want.items():
            differs = self.compare(f"{prefix}.{key}", have.get(key), value) or differs
        return differs


class Context:
    def __init__(self, repo_name: str, repo: dict, settings: dict, plan: Plan):
        self.repo_name = repo_name
        self.repo = repo
        self.settings = settings
        self.plan = plan
        self.visibility = repo.get("visibility") or ("private" if repo.get("private") else "public")
        self.is_public = self.visibility == "public"

    def path(self, suffix: str = "") -> str:
        return f"repos/{self.repo_name}" + (f"/{suffix}" if suffix else "")


# --- repository: the repository object -------------------------------------


def plan_repository(ctx: Context) -> None:
    want = ctx.settings.get("repository") or {}
    patch = {}
    for key, value in want.items():
        # A key the repository does not report is skipped, never written. It
        # is either newer than what this repository exposes or gated by its
        # plan, and either way a PATCH would be a guess answered with a 422.
        if key not in ctx.repo:
            ctx.plan.skip(key, "not reported by this repository")
            continue
        if ctx.plan.compare(key, ctx.repo[key], value):
            patch[key] = value
    if patch:
        ctx.plan.write("repository settings", "PATCH", ctx.path(), patch, "Applied repository settings.")


# --- actions: Settings → Actions → General ----------------------------------


def merged(have: dict, want: dict, keys) -> dict:
    """A PUT body carrying every key the endpoint knows.

    These endpoints replace the whole policy on PUT, so a body naming only
    the changed key could reset the others to their defaults. The current
    value travels for everything the file does not set.
    """
    body = {k: have[k] for k in keys if k in have}
    body.update(want)
    return body


def plan_actions(ctx: Context) -> None:
    actions = ctx.settings.get("actions") or {}
    plan = ctx.plan
    effective_allowed = None

    want = actions.get("permissions")
    if want:
        current = gh("GET", ctx.path("actions/permissions"))
        if not current.ok or not isinstance(current.data, dict):
            plan.skip("actions.permissions", "could not be read; is Actions enabled here?")
        else:
            effective_allowed = want.get("allowed_actions") or current.data.get("allowed_actions")
            if plan.compare_each("actions.permissions", current.data, want):
                body = merged(current.data, want, PERMISSION_KEYS)
                body.setdefault("enabled", True)
                plan.write("the Actions permissions policy", "PUT", ctx.path("actions/permissions"), body, "Applied the Actions permissions policy.")

    want = actions.get("selected_actions")
    if want:
        if effective_allowed is None:
            current = gh("GET", ctx.path("actions/permissions"))
            if current.ok and isinstance(current.data, dict):
                effective_allowed = current.data.get("allowed_actions")
        if effective_allowed != "selected":
            plan.skip("actions.selected_actions", "only applies when allowed_actions is selected")
        else:
            current = gh("GET", ctx.path("actions/permissions/selected-actions"))
            if not current.ok or not isinstance(current.data, dict):
                plan.skip("actions.selected_actions", "could not be read")
            else:
                differs = False
                for key, value in want.items():
                    have = current.data.get(key)
                    if key == "patterns_allowed":
                        have, value = sorted(have or []), sorted(value or [])
                    differs |= plan.compare(f"actions.selected_actions.{key}", have, value)
                if differs:
                    plan.write("the allowed actions", "PUT", ctx.path("actions/permissions/selected-actions"), merged(current.data, want, SELECTED_KEYS), "Applied the allowed actions.")

    want = actions.get("workflow")
    if want:
        current = gh("GET", ctx.path("actions/permissions/workflow"))
        if not current.ok or not isinstance(current.data, dict):
            plan.skip("actions.workflow", "could not be read; is Actions enabled here?")
        elif plan.compare_each("actions.workflow", current.data, want):
            plan.write("the Actions workflow-token policy", "PUT", ctx.path("actions/permissions/workflow"), merged(current.data, want, WORKFLOW_KEYS), "Applied the Actions workflow-token policy.")

    want = actions.get("fork_pr_contributor_approval")
    if want:
        # A private repository cannot be forked by an outside contributor, so
        # GitHub refuses this endpoint outright there.
        if not ctx.is_public:
            plan.skip("actions.fork_pr_contributor_approval", "public repositories only")
        else:
            current = gh("GET", ctx.path("actions/permissions/fork-pr-contributor-approval"))
            if not current.ok or not isinstance(current.data, dict):
                plan.skip("actions.fork_pr_contributor_approval", "could not be read; not available here")
            elif plan.compare("actions.fork_pr_contributor_approval", current.data.get("approval_policy"), want):
                plan.write("the fork pull request approval policy", "PUT", ctx.path("actions/permissions/fork-pr-contributor-approval"), {"approval_policy": want}, "Applied the fork pull request approval policy.")

    want = actions.get("fork_pr_workflows_private_repos")
    if want:
        if ctx.is_public:
            plan.skip("actions.fork_pr_workflows_private_repos", "private repositories only")
        else:
            current = gh("GET", ctx.path("actions/permissions/fork-pr-workflows-private-repos"))
            if not current.ok or not isinstance(current.data, dict):
                plan.skip("actions.fork_pr_workflows_private_repos", "could not be read; not available here")
            elif plan.compare_each("actions.fork_pr_workflows_private_repos", current.data, want):
                plan.write("the private-fork workflow policy", "PUT", ctx.path("actions/permissions/fork-pr-workflows-private-repos"), merged(current.data, want, PRIVATE_FORK_KEYS), "Applied the private-fork workflow policy.")

    want = actions.get("access_level")
    if want:
        if ctx.is_public:
            plan.skip("actions.access_level", "private repositories only")
        else:
            current = gh("GET", ctx.path("actions/permissions/access"))
            if not current.ok or not isinstance(current.data, dict):
                plan.skip("actions.access_level", "could not be read; not available here")
            elif plan.compare("actions.access_level", current.data.get("access_level"), want):
                plan.write("the outside-workflow access level", "PUT", ctx.path("actions/permissions/access"), {"access_level": want}, "Applied the outside-workflow access level.")

    want = actions.get("artifact_and_log_retention_days")
    if want is not None:
        current = gh("GET", ctx.path("actions/permissions/artifact-and-log-retention"))
        if not current.ok or not isinstance(current.data, dict):
            plan.skip("actions.artifact_and_log_retention_days", "could not be read; is Actions enabled here?")
        else:
            ceiling = current.data.get("maximum_allowed_days")
            if isinstance(ceiling, int) and want > ceiling:
                plan.skip("actions.artifact_and_log_retention_days", f"{want} days is above this repository's maximum of {ceiling}")
            elif plan.compare("actions.artifact_and_log_retention_days", current.data.get("days"), want):
                plan.write("the artifact and log retention", "PUT", ctx.path("actions/permissions/artifact-and-log-retention"), {"days": want}, "Applied the artifact and log retention.")

    for key, endpoint, field, label in (
        ("cache_retention_days", "actions/cache/retention-limit", "max_cache_retention_days", "the cache retention limit"),
        ("cache_storage_limit_gb", "actions/cache/storage-limit", "max_cache_size_gb", "the cache storage limit"),
    ):
        want = actions.get(key)
        if want is None:
            continue
        current = gh("GET", ctx.path(endpoint))
        if not current.ok or not isinstance(current.data, dict):
            plan.skip(f"actions.{key}", "not available on this repository's plan")
        elif plan.compare(f"actions.{key}", current.data.get(field), want):
            plan.write(label, "PUT", ctx.path(endpoint), {field: want}, f"Applied {label}.", tolerant=True)


# --- security: the Advanced Security page -----------------------------------


def plan_security(ctx: Context) -> None:
    security = ctx.settings.get("security") or {}
    plan = ctx.plan
    reported = ctx.repo.get("security_and_analysis") or {}

    for key in sorted(k for k in security if k in SECURITY_STATUS_KEYS):
        want = "enabled" if security[key] else "disabled"
        have = (reported.get(key) or {}).get("status")
        if have == want:
            plan.same()
            continue
        # An unreported feature is one the plan does not have, except for the
        # two every public repository gets for free, which are simply off.
        if have is None:
            if key in FREE_ON_PUBLIC and ctx.is_public and want == "enabled":
                pass
            elif key in FREE_ON_PUBLIC:
                plan.skip(key, "needs GitHub Secret Protection on a private repository")
                continue
            else:
                plan.skip(key, "not reported by this repository's plan")
                continue
        plan.change(key, have, want)
        plan.write(
            key,
            "PATCH",
            ctx.path(),
            {"security_and_analysis": {key: {"status": want}}},
            f"Set {key} to {want}.",
            tolerant=key not in FREE_ON_PUBLIC,
        )

    want = security.get("vulnerability_alerts")
    if want is not None:
        # 204 when on, 404 when off: the GET itself is the comparison.
        have = gh("GET", ctx.path("vulnerability-alerts")).ok
        if plan.compare("vulnerability_alerts", have, want):
            plan.write("Dependabot alerts", "PUT" if want else "DELETE", ctx.path("vulnerability-alerts"), None, f"{'Enabled' if want else 'Disabled'} Dependabot alerts.")

    want = security.get("automated_security_fixes")
    if want is not None:
        current = gh("GET", ctx.path("automated-security-fixes"))
        have = bool(current.ok and isinstance(current.data, dict) and current.data.get("enabled"))
        if plan.compare("automated_security_fixes", have, want):
            plan.write("Dependabot security updates", "PUT" if want else "DELETE", ctx.path("automated-security-fixes"), None, f"{'Enabled' if want else 'Disabled'} Dependabot security updates.")

    want = security.get("private_vulnerability_reporting")
    if want is not None:
        if not ctx.is_public:
            plan.skip("private_vulnerability_reporting", "public repositories only")
        else:
            current = gh("GET", ctx.path("private-vulnerability-reporting"))
            if not current.ok or not isinstance(current.data, dict):
                plan.skip("private_vulnerability_reporting", "could not be read; not available here")
            elif plan.compare("private_vulnerability_reporting", bool(current.data.get("enabled")), want):
                plan.write("private vulnerability reporting", "PUT" if want else "DELETE", ctx.path("private-vulnerability-reporting"), None, f"{'Enabled' if want else 'Disabled'} private vulnerability reporting.")

    want = security.get("code_scanning_default_setup")
    if want:
        current = gh("GET", ctx.path("code-scanning/default-setup"))
        if not current.ok or not isinstance(current.data, dict):
            plan.skip("code_scanning_default_setup", "code scanning is not available here: a public repository, or GitHub Code Security on a private one")
        else:
            differs = False
            for key, value in want.items():
                have = current.data.get(key)
                if key == "languages":
                    have, value = sorted(have or []), sorted(value or [])
                differs |= plan.compare(f"code_scanning_default_setup.{key}", have, value)
            if differs:
                plan.write("the code scanning default setup", "PATCH", ctx.path("code-scanning/default-setup"), dict(want), "Applied the code scanning default setup.")


# --- releases: Settings → General → Releases --------------------------------


def plan_releases(ctx: Context) -> None:
    releases = ctx.settings.get("releases") or {}
    plan = ctx.plan
    want = releases.get("immutable")
    if want is not None:
        current = gh("GET", ctx.path("immutable-releases"))
        data = current.data if current.ok and isinstance(current.data, dict) else {}
        have = bool(data.get("enabled"))
        if have != want and data.get("enforced_by_owner"):
            plan.skip("releases.immutable", "enforced by the repository's owner, which a repository setting cannot change")
        elif plan.compare("releases.immutable", have, want):
            plan.write("release immutability", "PUT" if want else "DELETE", ctx.path("immutable-releases"), None, f"{'Enabled' if want else 'Disabled'} release immutability.")


# --- Reporting ----------------------------------------------------------------


def write_summary(repo_name: str, plan: Plan, verdict: str, failures: list[str]) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(f"### ⚙️ Repository settings: `{repo_name}`\n\n```text\n")
        for line in plan.lines:
            fh.write(line + "\n")
        fh.write(f"Plan: {plan.changed} change(s), {plan.unchanged} already correct, {plan.skipped} skipped.\n")
        fh.write("```\n\n" + verdict + "\n")
        if failures:
            fh.write("\n**Not applied:**\n\n")
            for item in failures:
                fh.write(f"- {item}\n")


def write_outputs(plan: Plan, failed: int) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(f"changes={plan.changed}\n")
        fh.write(f"unchanged={plan.unchanged}\n")
        fh.write(f"skipped={plan.skipped}\n")
        fh.write(f"failed={failed}\n")
        fh.write(f"drift={'true' if plan.changed else 'false'}\n")


def main() -> int:
    here = pathlib.Path(__file__).resolve().parent
    settings_file = pathlib.Path(os.environ.get("SETTINGS_FILE") or here / ".." / "data" / "repository-settings.json")
    dry_run = truthy(os.environ.get("DRY_RUN"), default=True)
    fail_on_drift = truthy(os.environ.get("FAIL_ON_DRIFT"), default=False)

    try:
        settings = load_settings(settings_file)
    except SettingsError as exc:
        error(f"{exc} Nothing was compared and nothing would be applied.")
        return 1

    repo_name = (os.environ.get("TARGET_REPO") or "").strip()
    if not repo_name:
        # "Whatever gh is pointed at" is what makes a hand-run one command.
        # In Actions the caller always passes it explicitly.
        found = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
            capture_output=True,
            text=True,
            check=False,
        )
        repo_name = found.stdout.strip() if found.returncode == 0 else ""
    if not repo_name:
        error("TARGET_REPO is required, and no repository could be inferred from the current directory.")
        return 1

    # One read of the repository, reused for every comparison that follows.
    current = gh("GET", f"repos/{repo_name}")
    if not current.ok or not isinstance(current.data, dict):
        error(
            f"Could not read '{repo_name}'. Check that it exists, that you are authenticated, "
            f"and that the token can administer it. ({current.reason})"
        )
        return 1
    repo = current.data

    # The repository object says what the token may do here. A token without
    # admin fails now, with the fix, instead of as a 403 on the first write.
    permissions = repo.get("permissions")
    if isinstance(permissions, dict) and permissions.get("admin") is False:
        error(
            f"The token cannot administer '{repo_name}', so none of its settings can be written. "
            "Store a token with Administration: Read and write on this repository as the "
            "ADMIN_TOKEN secret; see docs/operations/Branch-Protection.md."
        )
        return 1

    plan = Plan()
    ctx = Context(repo_name, repo, settings, plan)

    print(f"Target:     {repo_name} ({ctx.visibility})")
    print(f"Settings:   {settings_file}")
    if dry_run:
        print("Mode:       DRY RUN - nothing will be changed.")
    print()

    plan_repository(ctx)
    plan_actions(ctx)
    plan_security(ctx)
    plan_releases(ctx)

    for line in plan.lines:
        print(line)
    print()
    print(f"Plan: {plan.changed} change(s), {plan.unchanged} already correct, {plan.skipped} skipped.")

    if plan.changed == 0:
        print("Nothing to do.")
        write_summary(repo_name, plan, f"Nothing to change: `{repo_name}` already matches the published set.", [])
        write_outputs(plan, 0)
        return 0

    if dry_run:
        write_outputs(plan, 0)
        if fail_on_drift:
            write_summary(repo_name, plan, f"Drift: **{plan.changed}** setting(s) in `{repo_name}` differ from the published set. Nothing was changed.", [])
            error(
                f"Drift: {plan.changed} setting(s) in {repo_name} differ from the published set; "
                "the plan above names each one. Nothing was changed. Dispatch 🎯 Apply Standards "
                "with dry-run off to bring them back."
            )
            return 1
        print("Dry run: nothing was changed. Set DRY_RUN=false to apply this plan.")
        write_summary(repo_name, plan, f"Dry run: **{plan.changed}** change(s) would be applied to `{repo_name}`. Nothing was changed.", [])
        return 0

    print()
    failures: list[str] = []
    refused = 0
    for name, method, path, body, done, tolerant in plan.writes:
        result = gh(method, path, body)
        if result.ok:
            print(done)
            continue
        if result.status == 409:
            # The owner's policy decides this one, and a repository setting
            # cannot overrule it. Said once, counted as left alone.
            warning(f"Could not apply {name} to {repo_name}: the owner's policy prevents it ({result.reason}). It was left as it was; everything else was still applied.")
            refused += 1
        elif tolerant:
            warning(f"Could not apply {name} to {repo_name}: not available on this repository's plan ({result.reason}). It was left as it was; everything else was still applied.")
            refused += 1
        else:
            error(f"Could not apply {name} to {repo_name}: {result.reason}. It was left as it was; everything after it was still attempted.")
            failures.append(f"{name}: {result.reason}")

    write_outputs(plan, len(failures))
    if failures:
        write_summary(repo_name, plan, f"**{len(failures)}** of {plan.changed} change(s) could not be applied to `{repo_name}`; the rest were.", failures)
        return 1
    applied = plan.changed - refused
    write_summary(repo_name, plan, f"Applied **{applied}** change(s) to `{repo_name}`. A re-run now plans `0 change(s)`.", [])
    print()
    print("Done. Rulesets are a separate act: see scripts/apply-rulesets.sh.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
