# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""What only the template needs never reaches a generated repository, bar a workflow.

A template names each file that serves only itself, one to a line, under
`# --- Only ever in the template` in `.github/template-sync`: its sentinel, and
in the private template the parity contract with everything enforcing it.
Initialisation deletes every one of them, records no baseline for any, and
redraws every folder log from what is left, so a new owner never finds
scaffolding to clear away by hand.

Every one but a workflow file. Init pushes with the workflow token, and
GitHub refuses any push from it that changes a file under .github/workflows/:
deleting the parity workflow cost a repository generated from the private
template its whole initialisation. So that one stays, named for its
owner to delete, and nothing else in its folder changes either - not its
identity, not its folder log.

A stub any repository might adopt is not among them. 🏷️ Cut Release
publishes the template's releases, but the Markdown Kit - generated from the
public template - cuts its own the same way, so it stays wherever the list
files it.

These play that out on real repositories: init's real `main()` with only the
API and the final push faked - the push refused as GitHub refuses it - the
reader it shares with template sync, the template's own check that keeps the
heading safe to act on, and the syncs that come after.
"""

from __future__ import annotations

import subprocess
import sys

import pytest
from conftest import ROOT, TEMPLATE_LIST, load_script

sync = load_script("scripts/template-sync.py")

ONLY = "# --- Only ever in the template ----------------------------------------------"
WORKFLOWS = ".github/workflows/"

# The fixture template, grown into the shape the private one has: a stub
# every repository keeps, files only the template needs - one of them a
# workflow - and three folder logs that name them.
LIST = (
    TEMPLATE_LIST
    .replace("/.github/workflows/checks.yml\n",
             "/.github/scripts/README.md\n/.github/workflows/README.md\n/.github/workflows/checks.yml\n")
    .replace("#/README.md\n#/LICENSE\n", "#/README.md\n#/LICENSE\n#/.github/workflows/cut-release.yml\n")
    .replace("#/.github/TEMPLATE_INIT\n",
             "#/.github/TEMPLATE_INIT\n#/.github/scripts/parity.py\n#/.github/template-parity.yml\n"
             "#/.github/workflows/template-parity.yml\n")
)
# What init deletes, and the workflow it leaves for the owner.
DELETED = [".github/scripts/parity.py", ".github/template-parity.yml"]
LEFT = [".github/workflows/template-parity.yml"]
ONLY_HERE = DELETED + LEFT
FILES = {
    ".github/template-sync": LIST,
    "README.md": ("# Template\n\nReplace this README.\n\n"
                  "<!-- AUTO-INDEX:BEGIN dir=./.github style=log -->\n<!-- AUTO-INDEX:END -->\n"),
    ".github/scripts/README.md": (
        "# Scripts\n\n"
        "<!-- AUTO-INDEX:BEGIN dir=. style=log -->\n<!-- AUTO-INDEX:END -->\n\n"
        "Built with ❤️ by [@tannergolden](https://github.com/tannergolden).\n"
    ),
    ".github/scripts/parity.py": "# Holds the template to its contract.\nprint('parity')\n",
    ".github/workflows/README.md": (
        "# Workflows\n\n"
        "<!-- AUTO-INDEX:BEGIN dir=. style=log -->\n<!-- AUTO-INDEX:END -->\n\n"
        "Built with ❤️ by [@tannergolden](https://github.com/tannergolden).\n"
    ),
    ".github/workflows/cut-release.yml": "# Publishes this repository's releases.\nname: cut release\n",
    ".github/workflows/template-parity.yml": "# Holds the template to its contract.\nname: parity\n",
    ".github/template-parity.yml": "# The contract, as data.\nbaseline: tannergolden/path\n",
}
LOGS = ["README.md", ".github/scripts/README.md", ".github/workflows/README.md"]


def release_with_logs(world, version: str, files: dict) -> str:
    """A release whose folder logs are drawn as the template's own Machined Indexes draws them."""
    world.put(world.template, files)
    world.sync.redraw_indexes(world.template, LOGS)
    return world.release(version)


@pytest.fixture
def shaped(sync_world):
    """The fixture template at v1.0.1, shaped like the real ones, nothing generated yet."""
    release_with_logs(sync_world, "v1.0.1", FILES)
    return sync_world


def initialise(world, monkeypatch, tmp_path) -> tuple[str, str]:
    """init's real main() in the generated repository, with only the API and the final push faked.

    The push is refused as GitHub refuses it: init pushes with the workflow
    token, and a push that changes anything under .github/workflows/ is
    turned away whatever the job's permissions - which is how a repository
    generated from the private template stayed uninitialised.

    Returns the commit message it wrote and the step summary it left.
    """
    init = load_script("scripts/init-template.py")
    generated = world.git(world.repo, "rev-parse", "HEAD").strip()

    def api(path, token):
        if path == "repos/janedoe/widget":
            return {"template_repository": {"full_name": "tannergolden/path"}}
        return {"name": "Jane Doe", "id": 42}

    real_run = subprocess.run

    def fake_run(args, *a, **kw):
        if isinstance(args, list) and args[:2] == ["git", "push"]:
            touched = world.git(world.repo, "diff", "--name-only", generated, "HEAD", "--", WORKFLOWS).split()
            if touched:
                return subprocess.CompletedProcess(args, 1, "", (
                    " ! [remote rejected] HEAD -> main (refusing to allow a GitHub App to create or update "
                    f"workflow `{touched[0]}` without `workflows` permission)"))
            return subprocess.CompletedProcess(args, 0, "", "")
        return real_run(args, *a, **kw)

    summary = tmp_path / "summary.md"
    monkeypatch.setattr(init, "api", api)
    monkeypatch.setattr(init.subprocess, "run", fake_run)
    monkeypatch.chdir(world.repo)
    for key, value in {"GH_TOKEN": "x", "REPO": "janedoe/widget", "OWNER": "janedoe", "DEFAULT_BRANCH": "main",
                       "IS_TEMPLATE": "false", "GITHUB_STEP_SUMMARY": str(summary)}.items():
        monkeypatch.setenv(key, value)
    assert init.main() == 0
    return world.git(world.repo, "log", "-1", "--format=%B"), summary.read_text(encoding="utf-8")


def committed(world) -> set[str]:
    return set(world.sync.tree(world.repo, "HEAD"))


class TestReadingTheHeading:
    """The one reader init and template sync share, as git's matcher reads the list."""

    def test_it_names_each_file_listed_under_the_heading(self):
        paths = [".github/TEMPLATE_INIT", *ONLY_HERE, ".github/workflows/cut-release.yml", "docs/guide.md"]
        assert sync.template_only(LIST, paths) == {".github/TEMPLATE_INIT", *ONLY_HERE}

    def test_a_stub_any_repository_may_adopt_is_not_among_them(self):
        assert ".github/workflows/cut-release.yml" not in sync.template_only(
            LIST, [".github/workflows/cut-release.yml"])

    @pytest.mark.parametrize("line", ["#/.github/**", "#/.github/*.yml", "#/.github/", "#/.github"])
    def test_a_pattern_or_a_folder_under_the_heading_takes_nothing(self, line):
        """`#/.github` reads as the folder and everything in it, so it is no safer than `#/**`."""
        text = f"# --- Kept current\n/docs/guide.md\n\n{ONLY}\n{line}\n\n# --- Your rules ---\n"
        assert sync.template_only(text, [".github/template-parity.yml", ".github/workflows/x.yml"]) == set()

    def test_a_later_line_naming_the_same_file_takes_it_back(self):
        text = f"{ONLY}\n#/notes.md\n\n# --- Yours\n#/notes.md\n\n# --- Your rules ---\n"
        assert sync.template_only(text, ["notes.md"]) == set()

    def test_your_rules_never_decide_it(self):
        """The heading is the template's: one an owner writes under Your rules deletes nothing."""
        text = f"# --- Kept current\n/docs/guide.md\n\n# --- Your rules ---\n{ONLY}\n#/docs/guide.md\n"
        assert sync.template_only(text, ["docs/guide.md"]) == set()

    def test_another_heading_is_only_a_heading(self):
        text = "# --- Template only\n#/.github/template-parity.yml\n\n# --- Your rules ---\n"
        assert sync.template_only(text, [".github/template-parity.yml"]) == set()

    @pytest.mark.parametrize("text", [None, ""])
    def test_no_list_names_nothing(self, text):
        assert sync.template_only(text, [".github/TEMPLATE_INIT"]) == set()


class TestInitDeletesWhatOnlyTheTemplateNeeds:
    def test_every_file_under_the_heading_but_a_workflow_is_gone_from_its_first_commit(
            self, shaped, monkeypatch, tmp_path):
        shaped.generate(init=False)
        initialise(shaped, monkeypatch, tmp_path)
        files = committed(shaped)
        for path in [*DELETED, ".github/TEMPLATE_INIT"]:
            assert path not in files, f"{path} only serves the template and must not reach a generated repository"
        assert shaped.clean()

    def test_everything_else_arrives_and_cut_release_is_kept(self, shaped, monkeypatch, tmp_path):
        shaped.generate(init=False)
        initialise(shaped, monkeypatch, tmp_path)
        files = committed(shaped)
        assert ".github/workflows/cut-release.yml" in files, "a stub any repository may adopt is never deleted"
        shipped = set(shaped.sync.tree(shaped.template, "v1")) - {*DELETED, ".github/TEMPLATE_INIT"}
        assert shipped <= files

    def test_the_list_still_names_them_switched_off(self, shaped, monkeypatch, tmp_path):
        shaped.generate(init=False)
        initialise(shaped, monkeypatch, tmp_path)
        assert shaped.text(".github/template-sync") == LIST

    def test_the_lock_records_no_baseline_for_them(self, shaped, monkeypatch, tmp_path):
        shaped.generate(init=False)
        root_tree = shaped.sync.tree(shaped.repo, "HEAD")
        initialise(shaped, monkeypatch, tmp_path)
        lock = shaped.sync.load_lock(shaped.git(shaped.repo, "show", "HEAD:.github/template-sync.lock"))
        for path, entry in root_tree.items():
            if path in ONLY_HERE or path == ".github/TEMPLATE_INIT":
                assert path not in lock.files, f"{path} was never this repository's, so it has no baseline"
            else:
                assert lock.files[path].blob == entry.sha, f"{path} not recorded as generated"

    def test_the_commit_and_the_summary_name_each_one(self, shaped, monkeypatch, tmp_path):
        shaped.generate(init=False)
        message, summary = initialise(shaped, monkeypatch, tmp_path)
        deleted, left = message.split("It could not delete")
        for path in DELETED:
            assert f"- {path}\n" in deleted
            assert f"`{path}`" in summary.split("**Left for you to delete:**")[0]
        for path in LEFT:
            assert f"- {path}\n" in left.split("Already wired")[0]
            assert f"`{path}`" in summary.split("**Left for you to delete:**")[1]
        assert "cut-release" not in message
        assert "TEMPLATE_INIT" not in message.split("Already wired")[0], "the sentinel is not news"
        assert "| Deleted, only the template needs them | 2 |" in summary
        assert "| Left for you to delete, workflow files only the template needs | 1 |" in summary

    def test_the_run_warns_of_each_workflow_it_left(self, shaped, monkeypatch, tmp_path, capsys):
        shaped.generate(init=False)
        initialise(shaped, monkeypatch, tmp_path)
        out = capsys.readouterr().out
        for path in LEFT:
            assert f"::warning title=Initialisation::{path} serves only the template" in out
        for path in DELETED:
            assert f"::warning title=Initialisation::{path}" not in out

    def test_a_template_with_nothing_of_its_own_says_nothing_about_it(self, sync_world, monkeypatch, tmp_path):
        sync_world.generate(init=False)
        message, summary = initialise(sync_world, monkeypatch, tmp_path)
        assert "only ever served the template" not in message
        assert "| Deleted, only the template needs them | 0 |" in summary
        assert "Left for you" not in summary
        assert set(sync_world.sync.tree(sync_world.template, "v1")) - {".github/TEMPLATE_INIT"} <= committed(sync_world)

    def test_the_list_and_the_lock_survive_a_list_that_names_them(self, sync_world, monkeypatch, tmp_path):
        """A template whose check never ran can still name them; a generated repository syncs through them."""
        sync_world.release("v1.0.1", {".github/template-sync": TEMPLATE_LIST.replace(
            "#/.github/TEMPLATE_INIT\n", "#/.github/TEMPLATE_INIT\n#/.github/template-sync\n")})
        sync_world.generate(init=False)
        initialise(sync_world, monkeypatch, tmp_path)
        assert ".github/template-sync" in committed(sync_world)
        assert ".github/template-sync.lock" in committed(sync_world)

    def test_a_template_without_a_list_deletes_only_the_sentinel(self, sync_world, monkeypatch, tmp_path):
        sync_world.release("v1.0.1", {".github/template-sync": None, **{p: FILES[p] for p in ONLY_HERE}})
        sync_world.generate(init=False)
        initialise(sync_world, monkeypatch, tmp_path)
        files = committed(sync_world)
        assert ".github/TEMPLATE_INIT" not in files
        assert set(ONLY_HERE) <= files, "with no list, nothing says what only the template needs"


class TestNothingUnderTheWorkflowsChanges:
    """GitHub refuses the workflow token every change there, so init makes none.

    A repository generated from the private template failed exactly here:
    init deleted the parity workflow and redrew the log beside it, and the
    push of the whole initialisation was refused.
    """

    def test_init_pushes_no_change_under_github_workflows(self, shaped, monkeypatch, tmp_path):
        shaped.generate(init=False)
        generated = shaped.git(shaped.repo, "rev-parse", "HEAD").strip()
        initialise(shaped, monkeypatch, tmp_path)
        assert shaped.git(shaped.repo, "rev-list", "--count", "HEAD").strip() == "1", "the initial commit is amended"
        assert shaped.git(shaped.repo, "diff", "--name-only", generated, "HEAD", "--", WORKFLOWS) == ""

    def test_a_workflow_only_the_template_needs_stays_as_generated(self, shaped, monkeypatch, tmp_path):
        shaped.generate(init=False)
        initialise(shaped, monkeypatch, tmp_path)
        for path in LEFT:
            assert shaped.text(path) == FILES[path]

    def test_a_workflow_file_keeps_the_identity_the_template_wrote(self, shaped, monkeypatch, tmp_path):
        shaped.generate(init=False)
        initialise(shaped, monkeypatch, tmp_path)
        assert "[@tannergolden](https://github.com/tannergolden)" in shaped.text(".github/workflows/README.md")
        assert "[@janedoe](https://github.com/janedoe)" in shaped.text(".github/scripts/README.md")

    def test_the_log_beside_the_workflows_is_never_redrawn_even_when_stale(self, shaped, monkeypatch, tmp_path):
        """Init could not push the redraw, so it makes none. Machined Indexes redraws it, given a token that can."""
        stale = FILES[".github/workflows/README.md"]  # its log never drawn
        shaped.release("v1.0.2", {".github/workflows/README.md": stale})
        shaped.generate(init=False)
        initialise(shaped, monkeypatch, tmp_path)
        assert shaped.text(".github/workflows/README.md") == stale


class TestEveryFolderLogIsRedrawn:
    def test_no_log_names_a_file_that_is_gone_and_the_lock_is_logged(self, shaped, monkeypatch, tmp_path):
        shaped.generate(init=False)
        initialise(shaped, monkeypatch, tmp_path)
        scripts = shaped.text(".github/scripts/README.md")
        assert "[`parity.py`]" not in scripts
        root = shaped.text("README.md")
        for gone in ("[`TEMPLATE_INIT`]", "[`template-parity.yml`]"):
            assert gone not in root
        assert "[`template-sync.lock`](.github/template-sync.lock)" in root
        # The workflow left for its owner is still there, so its log still names it.
        workflows = shaped.text(".github/workflows/README.md")
        assert "[`template-parity.yml`]" in workflows
        assert "[`cut-release.yml`]" in workflows and "[`checks.yml`]" in workflows

    def test_the_logs_are_what_machined_indexes_would_draw(self, shaped, monkeypatch, tmp_path):
        shaped.generate(init=False)
        initialise(shaped, monkeypatch, tmp_path)
        check = subprocess.run([sys.executable, str(ROOT / "scripts/update-doc-indexes.py"), "--tree", "--check"],
                               cwd=shaped.repo, capture_output=True, text=True, check=False)
        assert check.returncode == 0, check.stdout + check.stderr

    def test_the_words_around_a_log_are_still_rewritten_into_the_owner(self, shaped, monkeypatch, tmp_path):
        shaped.generate(init=False)
        initialise(shaped, monkeypatch, tmp_path)
        assert "[@janedoe](https://github.com/janedoe)" in shaped.text(".github/scripts/README.md")


class TestTheSyncsThatFollow:
    def test_the_first_sync_at_the_same_version_changes_nothing(self, shaped, monkeypatch, tmp_path):
        shaped.generate(init=False)
        initialise(shaped, monkeypatch, tmp_path)
        result = shaped.run_sync()
        assert not result.changed
        assert "owner-deleted" not in shaped.outcomes(result).values(), "init's deletion is not the owner's"

    def test_a_release_that_changes_them_brings_none_back(self, shaped):
        shaped.generate()
        release_with_logs(shaped, "v1.1.0", {p: FILES[p] + "# revised\n" for p in ONLY_HERE})
        result = shaped.run_sync()
        for path in DELETED:
            assert shaped.read(path) is None
        for path in LEFT:
            assert shaped.text(path) == FILES[path], "the workflow left for its owner is theirs, not the sync's"
        for path in ONLY_HERE:
            assert shaped.outcomes(result).get(path, "not-synced") == "not-synced"
        assert not result.changed, "nothing the owner would see changed"

    def test_a_release_that_changes_a_log_merges_around_the_redrawn_rows(self, shaped):
        shaped.generate()
        revised = FILES[".github/scripts/README.md"].replace("# Scripts\n", "# Scripts\n\nEvery tool.\n")
        release_with_logs(shaped, "v1.1.0", {".github/scripts/README.md": revised})
        result = shaped.run_sync()
        assert shaped.outcomes(result)[".github/scripts/README.md"] == "updated"
        text = shaped.text(".github/scripts/README.md")
        assert "Every tool." in text and "[`parity.py`]" not in text

    def test_taking_the_hash_off_one_brings_it_back_as_new(self, shaped):
        shaped.generate()
        listed = shaped.text(".github/template-sync").replace(
            "#/.github/template-parity.yml\n", "/.github/template-parity.yml\n")
        shaped.owner({".github/template-sync": listed})
        result = shaped.run_sync()
        assert shaped.outcomes(result)[".github/template-parity.yml"] == "added"
        assert shaped.read(".github/template-parity.yml") is not None


class TestALockRecoveredLater:
    def test_it_leaves_them_out_and_still_finds_every_log(self, shaped, monkeypatch):
        """Recovered from init's own first commit, whose logs init redrew."""
        monkeypatch.setenv("GITHUB_REPOSITORY_OWNER", "janedoe")
        monkeypatch.setenv("GITHUB_REPOSITORY", "janedoe/widget")
        shaped.generate(lock=False)
        revised = FILES[".github/scripts/README.md"].replace("# Scripts\n", "# Scripts\n\nEvery tool.\n")
        release_with_logs(shaped, "v1.1.0", {".github/scripts/README.md": revised})
        result = shaped.sync.run(shaped.repo, shaped.template, ref="v1.0.1", template="tannergolden/path",
                                 name="Jane Doe")
        lock = result.lock
        template = shaped.sync.tree(shaped.template, "v1.0.1")
        for path in LOGS:
            assert lock.files[path].blob == template[path].sha, f"{path} lost its baseline"
        for path in ONLY_HERE:
            assert path not in lock.files
        shaped.commit(shaped.repo, "recovered lock")
        after = shaped.run_sync()
        assert shaped.outcomes(after)[".github/scripts/README.md"] == "updated"


class TestTheTemplatesOwnCheck:
    """The heading is acted on in every generated repository, so the template's check keeps it safe."""

    def check_with(self, world, text: str) -> list[str]:
        world.release("v1.0.2", {".github/template-sync": text})
        return world.sync.check(world.template)

    def test_the_shaped_template_passes(self, shaped):
        assert shaped.sync.check(shaped.template) == []

    def test_a_line_switched_on_under_the_heading_fails(self, shaped):
        problems = self.check_with(shaped, LIST.replace("#/.github/template-parity.yml", "/.github/template-parity.yml"))
        assert any("switched on under" in p and "#/.github/template-parity.yml" in p for p in problems), problems

    def test_a_pattern_under_the_heading_fails(self, shaped):
        problems = self.check_with(shaped, LIST.replace(
            "#/.github/template-parity.yml\n#/.github/workflows/template-parity.yml\n",
            "#/.github/*parity.yml\n#/.github/workflows/template-parity.yml\n"))
        assert any("is a pattern under" in p for p in problems), problems

    def test_a_folder_under_the_heading_fails(self, shaped):
        problems = self.check_with(shaped, LIST.replace("#/.github/template-parity.yml\n", "#/.github\n"))
        assert any("`#/.github` names a file the template does not ship" in p for p in problems), problems
