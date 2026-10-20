<!--
title: '🔬 THE TEST SUITE'
description: 'How the pytest suite tests code that mostly lives inside workflow and action YAML: the fixtures that read a step and run it against a scripted gh, the conventions every test file keeps, and how to run part of the suite. Read it before writing or debugging a test here.'
type: guide
keywords: [pytest, fixtures, conftest, fake gh, workflow step shell, run shell, kebab-case]
-->

<!-- markdownlint-disable MD041 -->
<div align="center">

# 🔬 THE TEST SUITE

<a name="top"></a>

**How a test here runs the shell that actually ships, with nothing reaching the network.**

_Read the step, run the step._

</div>

---

## 💡 Testing Code That Lives In YAML

Most of what these standards do is shell in `run:` blocks, inside reusable workflows and composite
actions, and a test cannot import a `run:` block. Moving that shell into scripts would break the
layering in [Automation Architecture](Automation-Architecture.md), because a reusable workflow cannot
reach a script published beside it. So the suite never copies the shell:
[`tests/conftest.py`](../../../tests/conftest.py) reads the `run:` block out of the file that ships
and runs it as Actions would. Editing a step without its test fails the test, and renaming a step fails
it too, rather than leaving the step untested.

`python3 -m pytest`, which `make test` and 🚦 Self Checks both run, collects every file in
[`tests/`](../../../tests/README.md). `tests/harness.py` tests the fixtures themselves, so a fixture
that stops working fails there first instead of letting every test that uses it pass.

---

## 🧰 The Fixtures

`run_shell`, `run_script`, `fake_gh`, `git_repo` and `sync_world` are fixtures a test takes as
arguments. The rest are functions it imports with `from conftest import ...`. Each one that takes a
file takes its path relative to the repository root, so a test never depends on the directory it runs
from.

| You want to                   | Use                                                            | What it does                                                                                                                                                                                                                                                                                                                                                                  |
| :---------------------------- | :------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Read one step's shell         | `workflow_step_shell(path, job_id, step)`                      | Matches the step's `id`, then its `name`; `job_id=None` reads a composite action. Raises when the step is gone or has no `run:`. Carries the command line Actions would use: `bash -e` with no `shell:`, `bash --noprofile --norc -eo pipefail` for `shell: bash`                                                                                                             |
| Run it                        | `run_shell(script, cwd=None, env=None, shell=None)`            | Runs in a temporary directory, with the environment cleared to `PATH`, `LANG`, a temporary `HOME`, the runner's files and the `env` it is given, and stops a step after 120 seconds. The result carries `returncode`, `stdout`, `stderr`, `output` (both together), `outputs` (`$GITHUB_OUTPUT`), `summary`, `exported` (`$GITHUB_ENV`) and `path_additions` (`$GITHUB_PATH`) |
| Run a whole script            | `run_script(path, cwd=None, env=None)`                         | `bash` for a `.sh`, `python3` otherwise, through `run_shell`                                                                                                                                                                                                                                                                                                                  |
| Call one function in a script | `load_script(path)`                                            | Imports a hyphenated script as a module                                                                                                                                                                                                                                                                                                                                       |
| Answer `gh`                   | `fake_gh`                                                      | `route(match, stdout, code=0)` answers any call whose arguments contain `match`, `calls` lists what was asked, and `env(**extra)` is the environment that reaches the fake. An unrouted call exits 1 with `no route`, and `--jq` is applied with the real `jq`                                                                                                                |
| Work in a git repository      | `git_repo`                                                     | A repository on `main` with one commit, made with a git config of its own                                                                                                                                                                                                                                                                                                     |
| Test template sync            | `sync_world`                                                   | Real git repositories: a template released at `v1.0.0`, ready to generate a repository from and sync it                                                                                                                                                                                                                                                                       |
| Read a workflow               | `load_yaml(path)`, `workflow_on(doc)`, `workflow_inputs(path)` | `workflow_on` reads `on:`, which YAML 1.1 parses as the key `True`                                                                                                                                                                                                                                                                                                            |
| Skip when a tool is missing   | `requires(tool)`                                               | A skip marker, for a tool the runner normally provides                                                                                                                                                                                                                                                                                                                        |

---

## 🧪 A Test, Start To Finish

This test holds Cut Release's forward-only guard. It reads the `check` step of the `release` job, gives
it a repository whose default branch contains the commit, answers the one API call the step makes, and
reads the annotation the step printed. The fake applies the step's own `--jq` to the canned release
list, so the filter is under test too.

```python
# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Cut Release must refuse a version older than the latest release."""

import json

from conftest import workflow_step_shell


def test_refuses_an_older_version(run_shell, fake_gh, git_repo):
    run_shell("git update-ref refs/remotes/origin/main HEAD", cwd=git_repo)
    fake_gh.route("releases", json.dumps([{"tag_name": "v1.9.0", "draft": False}]))
    result = run_shell(
        workflow_step_shell(".github/workflows/release.yml", "release", "check"),
        cwd=git_repo,
        env=fake_gh.env(VERSION="v1.2.0", DEFAULT_BRANCH="main",
                        GH_TOKEN="t", GITHUB_REPOSITORY="o/r"),
    )
    assert result.returncode != 0, result
    assert "not newer than the current release" in result.output
```

`tests/release-guard.py` holds the same guard, and the rest of the step, case by case.

---

## 📏 What Every Test File Keeps

- **A kebab-case name** for the behaviour it holds, such as `release-guard.py`.
  [`pytest.ini`](../../../pytest.ini) collects every `*.py` under `tests/` and imports each with
  `--import-mode=importlib`, which is what lets a hyphenated name load. A run that collects nothing
  fails.
- **The SPDX lines, then a module docstring** that says what the file protects and the defect that
  made it necessary.
- **A guarded premise.** A test that checks every member of a set also asserts the set is not empty,
  so it cannot pass by checking nothing. `documented-commands-exist.py` asserts that the scripts still
  name at least one `make` target before it checks each one.
- **No network.** Every `gh` call goes to `fake_gh`, which puts its scripted `gh` first on `PATH`.
  `run_shell` clears the environment and points `HOME` at the test's own directory, so a step run
  without the fake finds none of your credentials.
- **No warnings, no surprise passes.** `filterwarnings = error` turns a warning into a failure, and
  `xfail_strict = true` fails a test marked to fail that passes instead.

---

## 🚀 Running Part Of It

```bash
make test
python3 -m pytest tests/release-guard.py
python3 -m pytest tests/release-guard.py -k unmerged
python3 -m pytest "tests/release-guard.py::TestVersionFormat"
```

A failing file's docstring says what it protects, which is usually the fastest way to tell a broken
change from a test that needs to move with it.

---

## 🔗 See Also

- [`tests/README.md`](../../../tests/README.md), the log of every test file and what each holds.
- [Working On These Standards](../../introduction/Working-On-These-Standards.md), for what to do when
  🚦 Self Checks fails.
- [Testing Strategy](../../distribution/Testing-Strategy.md), the testing standard for the
  repositories that follow these standards, which is a different subject.

---

<div align="center">

**A test that reads the shipped step cannot drift from it.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by the Engineering Team. Distributed under the MIT License.

</div>
