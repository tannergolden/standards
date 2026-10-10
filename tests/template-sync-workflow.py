# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The workflow, the action and init: the shell around the engine, as shipped.

The engine is tested on its own elsewhere. These test what wraps it, read out
of the files that ship and run with Actions' environment: which job runs
where, what each may write, how the template is found and fetched, how the
action dispatches, how the waiting-files issue is kept, and that init writes
the lock every later sync depends on.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
from typing import ClassVar

import pytest
from conftest import ROOT, SYNC_ENV, TEMPLATE_FILES, load_script, load_yaml, workflow_step_shell

WORKFLOW = ".github/workflows/template-sync.yml"
ACTION = "actions/template-sync/action.yml"
sync = load_script("scripts/template-sync.py")


class TestTheReusableWorkflow:
    def jobs(self):
        return load_yaml(WORKFLOW)["jobs"]

    def test_the_check_runs_only_in_a_template_and_the_sync_only_outside_one(self):
        jobs = self.jobs()
        assert jobs["check"]["if"].replace(" ", "") == "${{github.event.repository.is_template}}"
        assert jobs["sync"]["if"].replace(" ", "") == "${{!github.event.repository.is_template}}"

    def test_each_job_asks_for_what_it_uses_and_nothing_more(self):
        jobs = self.jobs()
        assert jobs["check"]["permissions"] == {"contents": "read"}
        assert jobs["sync"]["permissions"] == {"contents": "write", "issues": "write", "pull-requests": "write"}

    def test_the_published_stub_declares_exactly_the_union_as_its_ceiling(self):
        header = (ROOT / WORKFLOW).read_text(encoding="utf-8").split("\n---\n", 1)[0]
        stub = "\n".join(line[2:] if line.startswith("# ") else line[1:] for line in header.splitlines()
                         if line.startswith("#"))
        ceiling = dict(re.findall(r"^\s+(contents|issues|pull-requests): (read|write)", stub, re.M))
        union: dict[str, str] = {}
        for job in self.jobs().values():
            for scope, level in job["permissions"].items():
                if union.get(scope) != "write":
                    union[scope] = level
        assert ceiling == union

    def test_the_stub_syncs_only_when_the_owner_asks_and_checks_on_every_change(self):
        header = (ROOT / WORKFLOW).read_text(encoding="utf-8").split("\n---\n", 1)[0]
        guard = re.search(r"^#\s+if: (.+)$", header, re.M).group(1)
        assert "github.event.repository.is_template && (github.event_name != 'push'" in guard
        assert "!github.event.repository.is_template && github.event_name == 'workflow_dispatch'" in guard
        # Nobody is ever synced without asking: no schedule, and no event but
        # a manual run reaches the sync job in a generated repository.
        assert "schedule" not in guard
        assert not re.search(r"^#\s+schedule:", header, re.M)

    def test_no_run_block_interpolates_an_expression(self):
        """Every value reaches the shell through env, never pasted into it."""
        for job in self.jobs().values():
            for step in job["steps"]:
                assert "${{" not in step.get("run", ""), f"{step.get('name')}: template injection risk"

    def test_the_template_is_fetched_outside_the_working_tree_and_the_token_is_never_stored(self):
        shell = workflow_step_shell(WORKFLOW, "sync", "📥 Fetch The Template")
        assert '"${RUNNER_TEMP}/template.git"' in shell
        assert "http.extraheader" in shell and "git config" not in shell
        assert "--bare" in shell

    def test_automerge_waits_for_a_clean_sync(self):
        step = next(s for s in self.jobs()["sync"]["steps"] if s.get("uses", "").startswith(
            "tannergolden/standards/actions/open-pr"))
        assert step["with"]["automerge"].replace(" ", "") == (
            "${{inputs.automerge&&steps.sync.outputs.clean=='true'}}")
        assert step["with"]["branch"] == "chore/template-sync"

    def test_workflow_files_follow_what_the_token_can_do(self):
        step = next(s for s in self.jobs()["sync"]["steps"] if s.get("id") == "sync")
        assert step["with"]["workflow-files"] == "auto"
        assert step["with"]["workflow-token"] == "${{ secrets.BOT_ACCESS_TOKEN }}"

    def test_the_sync_is_worked_out_on_the_branch_its_pull_request_targets(self):
        checkout = next(s for s in self.jobs()["sync"]["steps"] if s.get("uses", "").startswith(
            "actions/checkout"))
        assert checkout["with"]["ref"].replace(" ", "") == (
            "${{inputs.base||github.event.repository.default_branch}}")
        assert checkout["with"]["fetch-depth"] == 0

    def test_a_private_template_is_looked_up_with_the_token_that_can_see_it(self):
        resolve = next(s for s in self.jobs()["sync"]["steps"] if s.get("id") == "resolve")
        assert resolve["env"]["GH_TOKEN"].replace(" ", "") == "${{secrets.BOT_ACCESS_TOKEN||github.token}}"

    def test_an_earlier_auto_merge_comes_off_before_a_run_that_did_not_earn_one_pushes(self):
        steps = self.jobs()["sync"]["steps"]
        hold = next(i for i, s in enumerate(steps) if s.get("id") == "hold")
        push = next(i for i, s in enumerate(steps) if s.get("uses", "").startswith(
            "tannergolden/standards/actions/open-pr"))
        assert hold < push
        # Exactly the runs whose own pull request does not ask to merge itself.
        assert steps[hold]["if"].replace(" ", "") == (
            "${{steps.sync.outputs.changed=='true'&&!(inputs.automerge&&steps.sync.outputs.clean=='true')}}")

    def test_a_push_never_takes_the_place_of_a_sync_waiting_its_turn(self):
        header = (ROOT / WORKFLOW).read_text(encoding="utf-8").split("\n---\n", 1)[0]
        group = re.search(r"^#\s+group: (.+)$", header, re.M).group(1)
        assert group == "${{ github.workflow }}-${{ github.ref }}-${{ github.event_name }}"


class TestResolvingTheTemplate:
    def run(self, run_shell, fake_gh, tmp_path, **env):
        shell = workflow_step_shell(WORKFLOW, "sync", "resolve")
        base = {"INPUT_TEMPLATE": "", "REPO": "janedoe/widget", "OWNER": "janedoe", "GH_TOKEN": "x"}
        return run_shell(shell, cwd=tmp_path, env=fake_gh.env(**{**base, **env}))

    def test_the_stubs_input_wins(self, run_shell, fake_gh, tmp_path):
        fake_gh.route("users/janedoe", '{"name": "Jane Doe"}')
        result = self.run(run_shell, fake_gh, tmp_path, INPUT_TEMPLATE="someone/else")
        assert result.outputs == {"template": "someone/else", "name": "Jane Doe"}

    def test_the_lock_comes_next(self, run_shell, fake_gh, tmp_path):
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github/template-sync.lock").write_text(json.dumps({"template": "tannergolden/path"}))
        fake_gh.route("users/janedoe", "{}")
        assert self.run(run_shell, fake_gh, tmp_path).outputs["template"] == "tannergolden/path"

    def test_a_lock_that_does_not_parse_is_left_for_the_engine_to_refuse(self, run_shell, fake_gh, tmp_path):
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github/template-sync.lock").write_text("{ not json")
        fake_gh.route("repos/janedoe/widget", '{"template_repository": {"full_name": "tannergolden/path"}}')
        fake_gh.route("users/janedoe", "{}")
        result = self.run(run_shell, fake_gh, tmp_path)
        assert result.returncode == 0, result.output
        assert "Traceback" not in result.output
        assert result.outputs["template"] == "tannergolden/path"

    def test_githubs_own_record_comes_last(self, run_shell, fake_gh, tmp_path):
        fake_gh.route("repos/janedoe/widget", '{"template_repository": {"full_name": "tannergolden/repo"}}')
        fake_gh.route("users/janedoe", "{}")
        assert self.run(run_shell, fake_gh, tmp_path).outputs["template"] == "tannergolden/repo"

    def test_no_template_anywhere_stops_with_the_fix(self, run_shell, fake_gh, tmp_path):
        fake_gh.route("repos/janedoe/widget", '{"template_repository": null}')
        result = self.run(run_shell, fake_gh, tmp_path)
        assert result.returncode == 1
        assert "Pass `template:` in the stub" in result.output


class TestHoldingAnEarlierAutoMerge:
    def test_it_asks_for_the_sync_branch_and_never_fails_the_run(self, run_shell, fake_gh, tmp_path):
        fake_gh.route("pr merge", "no pull request found", code=1)
        result = run_shell(workflow_step_shell(WORKFLOW, "sync", "hold"), cwd=tmp_path,
                           env=fake_gh.env(GH_TOKEN="x", REPO="janedoe/widget"))
        assert result.returncode == 0, result.output
        assert fake_gh.calls == ["pr merge --disable-auto chore/template-sync --repo janedoe/widget"]


class TestTheWorkflowFilePolicy:
    """`auto`: what the pushing token can do decides, read from the token itself."""

    CHECKS = ".github/workflows/checks.yml"
    RELEASED = "name: checks\n# Released in v1.1.0.\njobs:\n  ci:\n    with:\n      lint-command: 'validate'\n"

    @pytest.fixture
    def curl(self, tmp_path):
        """A `curl` that answers with whatever headers a test sets, and logs what it was given."""
        bindir = tmp_path / "_curlbin"
        bindir.mkdir()
        headers, argv, stdin = tmp_path / "_curl_headers", tmp_path / "_curl_argv", tmp_path / "_curl_stdin"
        shim = bindir / "curl"
        shim.write_text(
            "#!/usr/bin/env bash\n"
            f'printf "%s\\n" "$*" >> "{argv}"\n'
            f'cat >> "{stdin}"\n'
            f'[ -f "{headers}" ] || exit 7\n'
            f'cat "{headers}"\n',
            encoding="utf-8",
        )
        shim.chmod(0o755)

        class Curl:
            path = f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}"

            @staticmethod
            def answer(*lines: str) -> None:
                headers.write_text("".join(f"{line}\r\n" for line in ("HTTP/2 200", *lines, "")), encoding="utf-8")

            @staticmethod
            def argv() -> str:
                return argv.read_text(encoding="utf-8") if argv.exists() else ""

            @staticmethod
            def stdin() -> str:
                return stdin.read_text(encoding="utf-8") if stdin.exists() else ""

        return Curl()

    def run(self, run_shell, sync_world, curl, **env):
        sync_world.generate()
        sync_world.release("v1.1.0", {self.CHECKS: self.RELEASED})
        shell = workflow_step_shell(ACTION, None, "sync")
        base = {"GITHUB_ACTION_PATH": str(ROOT / "actions/template-sync"), "MODE": "run",
                "TEMPLATE_DIR": str(sync_world.template), "TEMPLATE": "", "REF": "v1", "WORKFLOW_FILES": "auto",
                "WORKFLOW_TOKEN": "", "OWNER_NAME": "", "REPOSITORY": "a/b", "VERSION": "", "MAP": "",
                "PATH": curl.path, **SYNC_ENV}
        result = run_shell(shell, cwd=sync_world.repo, env={**base, **env})
        assert result.returncode == 0, result.output
        return result, sync_world.text(self.CHECKS) == self.RELEASED

    def test_no_token_holds_workflows_back_without_asking_anyone(self, run_shell, sync_world, curl):
        _, updated = self.run(run_shell, sync_world, curl)
        assert not updated
        assert curl.argv() == ""

    def test_a_classic_token_with_the_workflow_scope_writes_them(self, run_shell, sync_world, curl):
        curl.answer("x-oauth-scopes: repo, workflow")
        _, updated = self.run(run_shell, sync_world, curl, WORKFLOW_TOKEN="ghp_example")
        assert updated

    def test_a_classic_token_without_it_holds_them_back_and_says_so(self, run_shell, sync_world, curl):
        curl.answer("X-OAuth-Scopes: repo, read:org, workflows")
        result, updated = self.run(run_shell, sync_world, curl, WORKFLOW_TOKEN="ghp_example")
        assert not updated
        assert "The token has no workflow scope" in result.output

    def test_a_token_that_names_no_scopes_is_trusted(self, run_shell, sync_world, curl):
        # Fine-grained and App tokens name none: they are made with Workflows write or they are not.
        curl.answer("content-type: application/json")
        _, updated = self.run(run_shell, sync_world, curl, WORKFLOW_TOKEN="github_pat_example")
        assert updated

    def test_an_unreachable_api_trusts_the_token_and_leaves_the_push_to_name_the_cause(
            self, run_shell, sync_world, curl):
        _, updated = self.run(run_shell, sync_world, curl, WORKFLOW_TOKEN="ghp_example")
        assert updated

    def test_the_token_reaches_curl_on_stdin_never_on_its_command_line(self, run_shell, sync_world, curl):
        curl.answer("x-oauth-scopes: workflow")
        self.run(run_shell, sync_world, curl, WORKFLOW_TOKEN="ghp_secretvalue")
        assert "ghp_secretvalue" not in curl.argv()
        assert 'header = "Authorization: Bearer ghp_secretvalue"' in curl.stdin()


class TestTheActionDispatches:
    def run(self, run_shell, cwd, **env):
        shell = workflow_step_shell(ACTION, None, "sync")
        base = {"GITHUB_ACTION_PATH": str(ROOT / "actions/template-sync"), "MODE": "run", "TEMPLATE_DIR": "",
                "TEMPLATE": "", "REF": "v1", "WORKFLOW_FILES": "true", "OWNER_NAME": "", "REPOSITORY": "a/b",
                "VERSION": "", "MAP": "", **SYNC_ENV}
        return run_shell(shell, cwd=cwd, env={**base, **env})

    def test_an_unknown_mode_is_refused(self, run_shell, tmp_path):
        result = self.run(run_shell, tmp_path, MODE="sync-everything")
        assert result.returncode == 1 and "mode must be 'run', 'check' or 'track'" in result.output

    def test_run_without_a_template_clone_is_refused(self, run_shell, tmp_path):
        result = self.run(run_shell, tmp_path)
        assert result.returncode == 1 and "`template-dir` is empty" in result.output

    def test_check_runs_against_the_checked_out_template(self, run_shell, sync_world):
        assert self.run(run_shell, sync_world.template, MODE="check").returncode == 0

    def test_run_syncs_and_reports_outputs(self, run_shell, sync_world):
        sync_world.generate()
        sync_world.release("v1.1.0", {"scripts/tool.py": "print('v1.1')\n"})
        result = self.run(run_shell, sync_world.repo, TEMPLATE_DIR=str(sync_world.template))
        assert result.returncode == 0, result.output
        assert result.outputs["changed"] == "true" and result.outputs["version"] == "v1.1.0"

    def test_a_mapping_reaches_the_engine(self, run_shell, sync_world, tmp_path):
        # A generated repository handed a mapping is refused for want of the
        # mapping's own lock - which proves the action passed it through.
        sync_world.generate()
        mapping = tmp_path / "map.json"
        mapping.write_text(json.dumps({"format": 1, "name": "📐 Parity", "lock": ".github/parity.lock"}))
        result = self.run(run_shell, sync_world.repo, TEMPLATE_DIR=str(sync_world.template),
                          TEMPLATE="tannergolden/path", MAP=str(mapping))
        assert result.returncode == 1
        assert "There is no .github/parity.lock yet" in result.output


class TestTheSyncPullRequestStaysCurrent:
    """A later run rewrites the open pull request's title and body, not only its branch.

    A squash merge writes them into history as the commit message, so a pull
    request still describing an earlier run records the wrong version, and
    the wrong list of what waits.
    """

    TITLE = "chore(template): 🔄 sync with tannergolden/path v1.2.0"

    def deliver(self, run_script, fake_gh, repo):
        (repo / "synced.txt").write_text("v1.2.0\n", encoding="utf-8")
        return run_script("scripts/open-pr.sh", cwd=repo, env=fake_gh.env(
            GH_TOKEN="t", BRANCH_PREFIX="chore/template-sync", PR_BASE="main",
            COMMIT_TITLE=self.TITLE, PR_TITLE=self.TITLE, PR_BODY="Needs you: c.txt"))

    @pytest.fixture
    def repo(self, git_repo, tmp_path):
        """The seeded repository, with a remote of its own to push the branch to."""
        remote = tmp_path / "remote.git"
        env = {**os.environ, **SYNC_ENV}
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], env=env, check=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=git_repo, env=env, check=True)
        return git_repo

    def test_an_open_pull_request_takes_this_runs_title_and_body(self, run_script, fake_gh, repo):
        fake_gh.route("pr list", json.dumps([{"number": 7}]))
        fake_gh.route("pr edit", "")
        fake_gh.route("pr comment", "")
        result = self.deliver(run_script, fake_gh, repo)
        assert result.returncode == 0, result.output
        edit = next(c for c in fake_gh.calls if c.startswith("pr edit 7"))
        assert f"--title {self.TITLE} --body Needs you: c.txt" in edit
        assert not any(c.startswith("pr create") for c in fake_gh.calls)

    def test_a_token_that_cannot_edit_it_warns_and_still_delivers(self, run_script, fake_gh, repo):
        fake_gh.route("pr list", json.dumps([{"number": 7}]))
        fake_gh.route("pr edit", "forbidden", code=1)
        fake_gh.route("pr comment", "")
        result = self.deliver(run_script, fake_gh, repo)
        assert result.returncode == 0, result.output
        assert "Could not refresh the title and body of pull request #7" in result.output


LOCK = {
    "format": 1, "template": "tannergolden/path", "version": "v1.2.0", "commit": "", "identity": None,
    "files": {}, "pending": {},
}


class TestTheWaitingFilesIssue:
    def run(self, run_shell, fake_gh, tmp_path, pending: dict | None):
        if pending is not None:
            (tmp_path / ".github").mkdir(exist_ok=True)
            (tmp_path / ".github/template-sync.lock").write_text(json.dumps({**LOCK, "pending": pending}))
        script = f'exec python3 "{ROOT}/scripts/template-sync.py" track --repository janedoe/widget --version v1.2.0'
        return run_shell(script, cwd=tmp_path, env=fake_gh.env(GH_TOKEN="x"))

    WAITING: ClassVar[dict] = {".github/workflows/checks.yml": {"version": "v1.2.0", "reason": "conflict"}}

    def test_a_waiting_file_opens_one_issue(self, run_shell, fake_gh, tmp_path):
        fake_gh.route("issue list", "[]")
        fake_gh.route("label create", "")
        fake_gh.route("issue create", "https://github.com/janedoe/widget/issues/7")
        result = self.run(run_shell, fake_gh, tmp_path, self.WAITING)
        assert result.returncode == 0, result.output
        created = next(c for c in fake_gh.calls if c.startswith("issue create"))
        assert "🔄 Template sync is waiting on you" in created and "--label automated" in created
        # The fake logs one call per line, so a multi-line body continues on the lines after it.
        log = "\n".join(fake_gh.calls)
        assert "`.github/workflows/checks.yml`" in log and "same part of it" in log

    def test_an_open_issue_is_redrawn_not_duplicated(self, run_shell, fake_gh, tmp_path):
        fake_gh.route("issue list", json.dumps([{"number": 7, "title": "🔄 Template sync is waiting on you"}]))
        fake_gh.route("issue edit", "")
        self.run(run_shell, fake_gh, tmp_path, self.WAITING)
        assert any(c.startswith("issue edit 7") for c in fake_gh.calls)
        assert not any(c.startswith("issue create") for c in fake_gh.calls)

    def test_another_issue_with_a_different_title_is_left_alone(self, run_shell, fake_gh, tmp_path):
        fake_gh.route("issue list", json.dumps([{"number": 3, "title": "Something else"}]))
        fake_gh.route("label create", "")
        fake_gh.route("issue create", "ok")
        self.run(run_shell, fake_gh, tmp_path, self.WAITING)
        assert not any(c.startswith("issue edit 3") for c in fake_gh.calls)

    def test_nothing_waiting_closes_it(self, run_shell, fake_gh, tmp_path):
        fake_gh.route("issue list", json.dumps([{"number": 7, "title": "🔄 Template sync is waiting on you"}]))
        fake_gh.route("issue close", "")
        self.run(run_shell, fake_gh, tmp_path, {})
        close = next(c for c in fake_gh.calls if c.startswith("issue close 7"))
        assert "as of v1.2.0" in close

    def test_nothing_waiting_and_no_issue_does_nothing_more(self, run_shell, fake_gh, tmp_path):
        fake_gh.route("issue list", "[]")
        self.run(run_shell, fake_gh, tmp_path, {})
        assert [c.split()[1] for c in fake_gh.calls] == ["list"]

    def test_an_api_failure_warns_and_never_fails_the_run(self, run_shell, fake_gh, tmp_path):
        fake_gh.route("issue list", "boom", code=1)
        result = self.run(run_shell, fake_gh, tmp_path, self.WAITING)
        assert result.returncode == 0
        assert "::warning title=Template sync::Could not list issues" in result.output


class TestInitWritesTheLock:
    def test_the_generation_lock_lands_in_inits_own_commit(self, sync_world, monkeypatch):
        """init's real main(), with only the API and the final push faked."""
        init = load_script("scripts/init-template.py")
        sync_world.generate(init=False)
        repo = sync_world.repo
        root_tree = sync_world.sync.tree(repo, "HEAD")

        def api(path, token):
            if path == "repos/janedoe/widget":
                return {"template_repository": {"full_name": "tannergolden/path"}}
            return {"name": "Jane Doe", "id": 42}

        real_run = subprocess.run

        def fake_run(args, *a, **kw):
            if isinstance(args, list) and args[:2] == ["git", "push"]:
                return subprocess.CompletedProcess(args, 0, "", "")
            return real_run(args, *a, **kw)

        monkeypatch.setattr(init, "api", api)
        monkeypatch.setattr(init.subprocess, "run", fake_run)
        monkeypatch.chdir(repo)
        for key, value in {"GH_TOKEN": "x", "REPO": "janedoe/widget", "OWNER": "janedoe",
                           "DEFAULT_BRANCH": "main", "IS_TEMPLATE": "false"}.items():
            monkeypatch.setenv(key, value)
        assert init.main() == 0

        committed = sync_world.git(repo, "show", "HEAD:.github/template-sync.lock")
        lock = sync_world.sync.load_lock(committed)
        assert lock.template == "tannergolden/path"
        year = datetime.datetime.now(tz=datetime.timezone.utc).year
        assert lock.identity == sync_world.sync.Identity("janedoe", "janedoe/widget", "Jane Doe", year)
        for path, entry in root_tree.items():
            if path != sync_world.sync.SENTINEL:
                assert lock.files[path].blob == entry.sha, f"{path} not recorded as generated"
        assert sync_world.read(".github/TEMPLATE_INIT") is None
        assert "[@janedoe]" in sync_world.text("docs/guide.md")

    def test_a_template_without_a_list_gets_no_lock(self, sync_world, monkeypatch, tmp_path):
        init = load_script("scripts/init-template.py")
        sync_world.release("v1.0.1", {".github/template-sync": None})
        sync_world.generate(init=False)
        monkeypatch.setattr(init, "api", lambda path, token: {})
        real_run = subprocess.run
        monkeypatch.setattr(init.subprocess, "run", lambda args, *a, **kw: subprocess.CompletedProcess(
            args, 0, "", "") if args[:2] == ["git", "push"] else real_run(args, *a, **kw))
        monkeypatch.chdir(sync_world.repo)
        for key, value in {"GH_TOKEN": "x", "REPO": "janedoe/widget", "OWNER": "janedoe",
                           "DEFAULT_BRANCH": "main", "IS_TEMPLATE": "false"}.items():
            monkeypatch.setenv(key, value)
        assert init.main() == 0
        assert sync_world.read(".github/template-sync.lock") is None


class TestInitialised:
    """init's per-file rule, which template sync imports rather than copies."""

    init = load_script("scripts/init-template.py")
    KW: ClassVar[dict] = {"owner": "janedoe", "repo": "janedoe/widget", "display": "Jane Doe",
                          "template_owner": "tannergolden", "year": 2027}

    def call(self, path, data):
        return self.init.initialised(path, data, **self.KW)

    def test_a_crlf_file_with_nothing_to_rewrite_keeps_every_byte(self):
        data = b"line one\r\nline two\r\n"
        assert self.call("notes.md", data) is data

    def test_a_crlf_file_that_is_rewritten_comes_out_lf_as_init_writes_it(self):
        data = b"by [@tannergolden](https://github.com/tannergolden)\r\n"
        assert self.call("notes.md", data) == b"by [@janedoe](https://github.com/janedoe)\n"

    @pytest.mark.parametrize("path", ["build/notes.md", "vendor/x/notes.md", "node_modules/a.md", "dist/a.md"])
    def test_the_folders_init_skips_are_skipped(self, path):
        data = b"[@tannergolden](https://github.com/tannergolden)\n"
        assert self.call(path, data) is data

    @pytest.mark.parametrize("path", ["logo.png", "archive.tar.gz", "Makefile"])
    def test_files_init_does_not_consider_are_untouched(self, path):
        data = b"tannergolden\n"
        assert self.call(path, data) is data

    def test_invalid_utf8_is_untouched(self):
        data = b"\xff\xfe tannergolden\n"
        assert self.call("notes.md", data) is data

    @pytest.mark.parametrize("name", ["LICENSE", "CODEOWNERS", ".gitignore"])
    def test_named_files_are_considered(self, name):
        assert self.call(name, b"@tannergolden\n") == b"@janedoe\n"

    def test_it_agrees_with_what_main_does_to_the_template(self, tmp_path):
        """Every default template file, through initialised(), is what init's loop writes."""
        for rel, content in TEMPLATE_FILES.items():
            data = content.encode()
            out = self.call(rel, data)
            expected = self.init.rewrite(content, **{**self.KW}) if self.init.considered(
                __import__("pathlib").PurePosixPath(rel)) else content
            assert out == (expected.encode() if expected != content else data), rel


def test_the_action_is_the_only_caller_of_the_script_path(tmp_path):
    """The script travels with the action; the workflow must reach it through the action."""
    text = (ROOT / WORKFLOW).read_text(encoding="utf-8")
    assert "scripts/template-sync.py" not in text
    assert os.path.isfile(ROOT / "scripts/template-sync.py")
