# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""A public repository never keeps the issue form that would publish a vulnerability.

The public template ships `.github/ISSUE_TEMPLATE/Vulnerability-Report.yaml`,
an issue form for security reports, which is the intake a private repository
needs: an issue there is as private as the repository. On a public
repository every issue is public, so a vulnerability filed through that form
is published the moment it is filed, and the form's own warning to use
SECURITY.md instead is the only thing standing in the way. Private
vulnerability reporting is the intake there.

So initialisation deletes the form when the repository it initialises is
public, reading the visibility from the repository object it already
fetches, or from the event that started the run when the API cannot be
read. When neither says, the form stays and the run warns: deleting it from
a private repository would leave that repository no intake at all.

Its line in `.github/template-sync` stays switched on, and the first sync
after initialisation reads the absence as the owner's deletion: it switches
the line off and never brings the form back, until someone takes the `#`
away. These play that out on real repositories, with init's real `main()`
and only the API and the final push faked.
"""

from __future__ import annotations

import json
import subprocess

import pytest
from conftest import TEMPLATE_LIST, load_script

init = load_script(".github/scripts/init-template.py")

FORM = ".github/ISSUE_TEMPLATE/Vulnerability-Report.yaml"
LOG = ".github/ISSUE_TEMPLATE/README.md"
LIST = TEMPLATE_LIST.replace(
    "/.github/workflows/checks.yml\n",
    f"/{LOG}\n/{FORM}\n/.github/workflows/checks.yml\n",
)
FILES = {
    ".github/template-sync": LIST,
    LOG: "# Issue Forms\n\n<!-- AUTO-INDEX:BEGIN dir=. style=log fields=name -->\n<!-- AUTO-INDEX:END -->\n",
    FORM: (
        "name: 'Vulnerability Report'\n"
        "description: 'PRIVATE repos only: report suspected vulnerabilities here.'\n"
        "body:\n"
        "  - type: textarea\n"
        "    attributes:\n"
        "      label: 'What is vulnerable'\n"
    ),
}
PUBLIC = {"visibility": "public", "private": False}
PRIVATE = {"visibility": "private", "private": True}


@pytest.fixture
def world(sync_world):
    """The fixture template at v1.0.1, shipping the form and a folder log naming it."""
    sync_world.put(sync_world.template, FILES)
    sync_world.sync.redraw_indexes(sync_world.template, [LOG])
    sync_world.release("v1.0.1")
    return sync_world


def initialise(world, monkeypatch, tmp_path, *, repository: dict, event: dict | None = None) -> tuple[str, str]:
    """init's real main() in the generated repository, with only the API and the final push faked.

    `repository` is what the API says of the repository, besides the
    template it came from; `event` is the payload of the event that started
    the run, or none at all. Returns the commit message and the step summary.
    """
    def api(path, token):
        if path == "repos/janedoe/widget":
            return {"template_repository": {"full_name": "tannergolden/path"}, **repository}
        return {"name": "Jane Doe", "id": 42}

    real_run = subprocess.run

    def fake_run(args, *a, **kw):
        if isinstance(args, list) and args[:2] == ["git", "push"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        return real_run(args, *a, **kw)

    summary = tmp_path / "summary.md"
    monkeypatch.setattr(init, "api", api)
    monkeypatch.setattr(init.subprocess, "run", fake_run)
    monkeypatch.chdir(world.repo)
    for key, value in {"GH_TOKEN": "x", "REPO": "janedoe/widget", "OWNER": "janedoe", "DEFAULT_BRANCH": "main",
                       "IS_TEMPLATE": "false", "GITHUB_STEP_SUMMARY": str(summary)}.items():
        monkeypatch.setenv(key, value)
    # A run under Actions has an event of its own; the tests choose theirs.
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
    if event is not None:
        payload = tmp_path / "event.json"
        payload.write_text(json.dumps(event), encoding="utf-8")
        monkeypatch.setenv("GITHUB_EVENT_PATH", str(payload))
    assert init.main() == 0
    return world.git(world.repo, "log", "-1", "--format=%B"), summary.read_text(encoding="utf-8")


def committed(world) -> set[str]:
    return set(world.sync.tree(world.repo, "HEAD"))


class TestAPublicRepository:
    def test_the_form_is_gone_from_its_first_commit(self, world, monkeypatch, tmp_path):
        world.generate(init=False)
        initialise(world, monkeypatch, tmp_path, repository=PUBLIC)
        assert FORM not in committed(world), "a public repository would publish every report filed through it"
        assert world.clean()

    def test_the_commit_and_the_summary_say_so(self, world, monkeypatch, tmp_path):
        world.generate(init=False)
        message, summary = initialise(world, monkeypatch, tmp_path, repository=PUBLIC)
        body = message.split("Already wired")[0]
        assert "This repository is public" in body and f"- {FORM}\n" in body
        assert "switches the line off" in body
        assert "| Deleted, issue forms a public repository would publish reports through | 1 |" in summary
        assert f"`{FORM}`" in summary.split("**Deleted, as this repository is public:**")[1]

    def test_the_folder_log_no_longer_names_it(self, world, monkeypatch, tmp_path):
        world.generate(init=False)
        assert "[`Vulnerability-Report.yaml`]" in world.text(LOG), "the fixture's log should name it to begin with"
        initialise(world, monkeypatch, tmp_path, repository=PUBLIC)
        assert "[`Vulnerability-Report.yaml`]" not in world.text(LOG)

    def test_init_leaves_its_line_in_the_list_as_it_was(self, world, monkeypatch, tmp_path):
        world.generate(init=False)
        initialise(world, monkeypatch, tmp_path, repository=PUBLIC)
        assert world.text(".github/template-sync") == LIST

    def test_without_a_list_it_promises_no_sync(self, world, monkeypatch, tmp_path):
        world.release("v1.0.2", {".github/template-sync": None})
        world.generate(init=False)
        message, summary = initialise(world, monkeypatch, tmp_path, repository=PUBLIC)
        assert FORM not in committed(world)
        assert "This repository is public" in message
        assert "Template Sync reads it" not in message and "switches its line off" not in summary


@pytest.mark.parametrize("repository", [PRIVATE, {"visibility": "internal", "private": True}])
class TestARepositoryThatIsNotPublic:
    def test_the_form_stays_and_nothing_is_said_of_it(self, world, monkeypatch, tmp_path, repository):
        world.generate(init=False)
        message, summary = initialise(world, monkeypatch, tmp_path, repository=repository)
        assert world.text(FORM) == FILES[FORM]
        assert "is public" not in message and "Vulnerability-Report" not in summary


class TestWhereTheVisibilityComesFrom:
    def test_the_event_answers_when_the_api_cannot(self, world, monkeypatch, tmp_path):
        world.generate(init=False)
        initialise(world, monkeypatch, tmp_path, repository={}, event={"repository": {"private": False}})
        assert FORM not in committed(world)

    def test_the_api_answers_first(self, world, monkeypatch, tmp_path):
        world.generate(init=False)
        initialise(world, monkeypatch, tmp_path, repository=PRIVATE, event={"repository": {"private": False}})
        assert FORM in committed(world)

    def test_with_neither_the_form_stays_and_the_run_warns(self, world, monkeypatch, tmp_path, capsys):
        """Deleting it from a private repository would leave no intake, so nothing is guessed."""
        world.generate(init=False)
        message, summary = initialise(world, monkeypatch, tmp_path, repository={})
        assert world.text(FORM) == FILES[FORM]
        assert f"::warning title=Initialisation::Could not tell whether this repository is public, so {FORM} stays." in (
            capsys.readouterr().out)
        assert f"**Kept, visibility unknown:** `{FORM}`" in summary
        assert "is public" not in message

    @pytest.mark.parametrize(("repository", "visibility"), [
        ({"visibility": "public"}, "public"),
        ({"visibility": "internal", "private": True}, "internal"),
        ({"private": True}, "private"),
        ({"private": False}, "public"),
        ({"visibility": "secret"}, None),
        ({}, None),
        (None, None),
    ])
    def test_a_repository_object_is_read_by_either_field(self, repository, visibility):
        assert init.visibility_of(repository) == visibility


class TestAPublicRepositoryWithoutTheForm:
    def test_nothing_is_deleted_or_said(self, sync_world, monkeypatch, tmp_path, capsys):
        sync_world.generate(init=False)
        message, summary = initialise(sync_world, monkeypatch, tmp_path, repository=PUBLIC)
        assert "is public" not in message and "Vulnerability-Report" not in summary
        assert "Vulnerability-Report" not in capsys.readouterr().out


class TestTheSyncsThatFollow:
    def initialised(self, world, monkeypatch, tmp_path):
        world.generate(init=False)
        initialise(world, monkeypatch, tmp_path, repository=PUBLIC)

    def test_the_first_sync_switches_its_line_off_and_leaves_it_deleted(self, world, monkeypatch, tmp_path):
        self.initialised(world, monkeypatch, tmp_path)
        result = world.run_sync()
        assert world.outcomes(result)[FORM] == "owner-deleted"
        assert world.read(FORM) is None, "the sync brought back the form init deleted"
        assert f"#/{FORM}\n" in world.text(".github/template-sync")
        assert world.lock().files[FORM].deleted

    def test_a_release_that_changes_the_form_brings_nothing_back(self, world, monkeypatch, tmp_path):
        self.initialised(world, monkeypatch, tmp_path)
        world.run_sync()
        world.release("v1.1.0", {FORM: FILES[FORM] + "  - type: checkboxes\n"})
        result = world.run_sync()
        assert world.outcomes(result).get(FORM, "not-synced") == "not-synced"
        assert world.read(FORM) is None

    def test_taking_the_hash_away_brings_it_back(self, world, monkeypatch, tmp_path):
        """A repository made private later wants its intake back, and asks for it in the list."""
        self.initialised(world, monkeypatch, tmp_path)
        world.run_sync()
        listed = world.text(".github/template-sync").replace(f"#/{FORM}\n", f"/{FORM}\n")
        world.owner({".github/template-sync": listed})
        result = world.run_sync()
        assert world.outcomes(result)[FORM] == "restored"
        assert world.text(FORM) == FILES[FORM]
