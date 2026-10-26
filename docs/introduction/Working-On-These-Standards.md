<!--
title: '🧰 WORKING ON THESE STANDARDS'
description: 'How to change this repository itself: what a merge reaches, the tools, the local command behind each Self Checks step, what must change together, running a script by hand, and what to do when a check fails. Read it before your first change here.'
type: guide
-->

<!-- markdownlint-disable MD041 -->
<div align="center">

# 🧰 WORKING ON THESE STANDARDS

<a name="top"></a>

**How to change the standards themselves, and prove the change before it ships.**

_Merged is not released._

</div>

---

## 💡 What A Merge Here Reaches

Nothing, until a release. Consumers pin `@v1`
([Consuming These Standards](../../README.md#-consuming-these-standards)), and every reusable
workflow here calls the composite actions at `@v1` too, so a merge to `Development` changes nothing
a consumer runs. A release moves `v1` onto the merged commit, and from then on every repository
pinned to it runs the change on its next workflow run, with no pull request of its own to catch it.
[Releasing These Standards](../distribution/Releasing-These-Standards.md) covers that step.

The proof therefore has to happen here, before the release. **🚦 Self Checks**
([`self-checks.yml`](../../.github/workflows/self-checks.yml)) runs on every pull request, every push
to `Development`, and on Mondays at 04:00 UTC. Any other branch is checked through its pull request,
so a commit does not run the suite once for every branch it is pushed to. It calls what it tests by
local path, `./.github/actions/harden` and `./.github/workflows/codeql.yml`, so it tests the tree
under review rather than the last release.
How each layer resolves is in [Automation Architecture](../technical/internals/Automation-Architecture.md).

---

## ⚙️ Tools

The [development container](../../.devcontainer/README.md) is the environment image,
`ghcr.io/tannergolden/environment:1`, which holds every tool the checks use, at the versions 🚦 Self
Checks installs through the environment's toolchain action, and adds jq for the suite:

| Tool               | Needed by                                                  |
| :----------------- | :--------------------------------------------------------- |
| ruff, pytest       | `make lint`, `make test`                                   |
| PyYAML             | The suite: `tests/conftest.py` imports it                  |
| jq                 | The suite: its fake `gh` applies `--jq` with the real `jq` |
| Prettier           | `make lint-format`                                         |
| actionlint, zizmor | 🧰 Workflows & Actions                                     |

Outside the container, install the same tools with the environment's own installer,
`toolchain/install.sh --user`, from a checkout of
[`tannergolden/environment`](https://github.com/tannergolden/environment), and jq from your system;
`make setup` says which are missing.

> [!IMPORTANT]
> **No file here pins a checker's version.** They are the environment's: move one in
> `tannergolden/environment`, and its next release reaches 🚦 Self Checks, every consumer's checks
> and this container together.

---

## 🚀 Every Check, Run Locally

Each step of 🚦 Self Checks, and the command that runs it on your machine. `make help` lists every
target.

| Job                    | Step                                                                                                                       | Locally                                                                                                        |
| :--------------------- | :------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------- |
| 🧪 Tests               | 🧪 pytest                                                                                                                  | `make test`                                                                                                    |
| 🐍 Scripts             | 🧹 ruff (rules from .ruff.toml)                                                                                            | `make lint`, and `make lint-fix` for what ruff can repair itself                                               |
| 🐍 Scripts             | 🔍 Every script parses                                                                                                     | `python3 -m compileall -q .github/scripts/`, and `bash -n` on each `.sh`                                       |
| 🧰 Workflows & Actions | 🔍 actionlint (Actions semantics)                                                                                          | `actionlint`                                                                                                   |
| 🧰 Workflows & Actions | 🛡️ zizmor (Actions security audit)                                                                                         | `zizmor --no-progress --persona=pedantic --config config/zizmor.yml .github/workflows .github/actions actions` |
| 🎬 Composite Actions   | 🛡️ Harden Runner (smoke test, local path), 📐 Every action.yml is well-formed, 🔗 Every script an action references exists | No target: the checks are Python written inline in `self-checks.yml`                                           |
| 📋 Data & Config       | 📄 Generated documents and the type list are current                                                                       | `make lint-docs`                                                                                               |
| 📋 Data & Config       | 🎨 Formatting matches the published config                                                                                 | `make lint-format`                                                                                             |
| 📋 Data & Config       | 📐 Every YAML and JSON parses                                                                                              | No target: inline in `self-checks.yml`                                                                         |
| 🔓 CodeQL              | Calls `codeql.yml` by local path                                                                                           | On GitHub only                                                                                                 |

The loop before a push:

```bash
make lint
make lint-docs
make lint-format
make test
```

---

## 🌿 What Changes Together

Most changes here have a second half somewhere else. Where a test holds it, the test fails until both
halves land; the rest is held by review.

| When you                                                                           | Also change                                                                                                                                                                                                                                      | Held by                                                                                           |
| :--------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------ |
| Add a reusable workflow                                                            | Its row in [`.github/workflows/README.md`](../../.github/workflows/README.md), the count in the root README's table, and the stub that calls it in its header comment, as the others carry theirs                                                | `tests/documentation-inventories.py`; the count, by review                                        |
| Give a header stub a schedule                                                      | Minute `00`, an hour no other header example takes, and a row in [Automation Schedules](../distribution/automation/Automation-Schedules.md)                                                                                                      | `tests/schedule-documentation.py`; the row, by review                                             |
| Add a composite action                                                             | `.github/actions/<name>/action.yml` with a `README.md` like its siblings', its row in the table of [`.github/actions/README.md`](../../.github/actions/README.md), and the root README's count. No forwarder: it never had an old address        | 🎬 Composite Actions; the folder logs by `make lint-docs`                                         |
| Change an action's inputs or outputs                                               | Its forwarder, `actions/<name>/action.yml`, which declares the same ones and passes each on ([ADR-0001](../adrs/ADR-0001-Actions-And-Scripts-Live-In-Github.md))                                                                                 | Review only                                                                                       |
| Add a script                                                                       | A kebab-case name, the standard library only, and a docstring or leading comment whose first line says what it does: that line is its row in [`.github/scripts/README.md`](../../.github/scripts/README.md). Its tests in `tests/`               | `make lint-docs` for its row; `tests/documented-commands-exist.py` for any `make` target it names |
| Add a file to `data/`                                                              | Its name in [`data/README.md`](../../data/README.md)                                                                                                                                                                                             | `tests/documentation-inventories.py`                                                              |
| Add a repository setting                                                           | Its reason in its group's block (`_why`, `_why_actions`, `_why_security` or `_why_releases`), or the key in `_excluded` with the reason it is left out; a new group is also named in [Repository Settings](../operations/Repository-Settings.md) | `tests/apply-settings-groups.py`                                                                  |
| Rename or restyle a label                                                          | `renamed_from:` on a rename, then `make docs-index` to redraw [Repository Labels](../references/Repository-Labels.md)                                                                                                                            | `make lint-docs`                                                                                  |
| Change the commit type list                                                        | All five copies `check-type-parity.py` names                                                                                                                                                                                                     | `make check-types`, inside `make lint-docs`                                                       |
| Add, move or retitle a document                                                    | Its hidden frontmatter, the folder logs (`make docs-index`), and its row in the hand-curated [Standards Index](../README.md) when it sits under `docs/`                                                                                          | `make lint-docs`; the index row, by review                                                        |
| Rename a required check, remove an input, or change a default so behaviour changes | Nothing in this major: it is breaking, and waits for the next one ([Choosing The Version](../distribution/Releasing-These-Standards.md#-choosing-the-version))                                                                                   | Review only                                                                                       |

---

## 🔧 Running A Script By Hand

The scripts that act on a repository through the API run from a clone, with `gh auth login` done or a
token in the environment. Each names what it reads at the top of the file. **They do not share a
dry-run default**, so check this table before the first run:

| Script                   | Acts on                                                         | With `DRY_RUN` unset | To flip it              |
| :----------------------- | :-------------------------------------------------------------- | :------------------- | :---------------------- |
| `apply-rulesets.sh`      | `TARGET_REPO`, else the repository `gh` points at               | Plans only           | `DRY_RUN=false` applies |
| `apply-settings.py`      | `TARGET_REPO`, else the repository `gh` points at               | Plans only           | `DRY_RUN=false` applies |
| `sync-labels.sh`         | `GITHUB_REPOSITORY`, with `GH_TOKEN` and `LABELS_FILE` required | **Writes**           | `DRY_RUN=true` plans    |
| `prune-deployments.py`   | `GITHUB_REPOSITORY`, with `GITHUB_TOKEN` required               | **Deletes**          | `DRY_RUN=1` plans       |
| `prune-workflow-runs.py` | `GITHUB_REPOSITORY`, with `GITHUB_TOKEN` required               | **Deletes**          | `DRY_RUN=1` plans       |

```bash
bash .github/scripts/apply-rulesets.sh
TARGET_REPO=owner/name DRY_RUN=false bash .github/scripts/apply-rulesets.sh
GITHUB_REPOSITORY=owner/name GITHUB_TOKEN="$(gh auth token)" DRY_RUN=1 python3 .github/scripts/prune-deployments.py
```

Hand a token over on the command line, as the last line does, rather than writing it into a file in
the clone.

---

## 🧯 When A Check Fails

| Failure                                     | Usual cause                                                                 | Fix                                                                                                                                                                     |
| :------------------------------------------ | :-------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 📄 Generated documents: an index is stale   | A document or file added, moved or retitled without a redraw                | `make docs-index`, then commit what it changed                                                                                                                          |
| 📄 Generated documents: frontmatter         | A document without the hidden frontmatter, or with a field it may not carry | The annotation names the file, the line and the problem: [Frontmatter Metadata](../technical/interface/Document-Styling-&-Formatting.md#%EF%B8%8F-frontmatter-metadata) |
| 📄 Generated documents: the type list       | One copy of the commit types changed alone                                  | `make check-types` names the copy that differs                                                                                                                          |
| 🎨 Formatting                               | A file Prettier would rewrite                                               | `npx --yes prettier@3.8.1 --config config/prettierrc.json --ignore-path config/prettierignore --write <file>`                                                           |
| 🧹 ruff                                     | A lint finding in a script or a test                                        | `make lint-fix`, then fix what is left by hand                                                                                                                          |
| 🛡️ zizmor                                   | A security finding in a workflow or an action                               | Fix it. One that does not apply is accepted with its reason beside it: in `config/zizmor.yml`, keyed by file name, or inline as `# zizmor: ignore[<audit>]`             |
| 📐 Every YAML and JSON parses               | A comment or a trailing comma in a JSON file                                | Every JSON file here is strict JSON                                                                                                                                     |
| 🔗 Every script an action references exists | An action names a path under `$GITHUB_ACTION_PATH` that is not there        | The annotation names the action and the path                                                                                                                            |
| 🧪 pytest                                   | A behaviour, or a document a test reads, changed                            | Run the one file, `python3 -m pytest tests/<file>.py`; its docstring says what it protects. [The Test Suite](../technical/internals/Test-Suite.md) has the rest         |

---

## 🔗 See Also

- [Releasing These Standards](../distribution/Releasing-These-Standards.md), for the step after the merge.
- [Automation Architecture](../technical/internals/Automation-Architecture.md), for how a workflow, an
  action and a script fit and the shape each keeps.
- [The Test Suite](../technical/internals/Test-Suite.md), for writing a test.
- [Conventional Commits](../distribution/Conventional-Commits.md), for the commit messages the gates
  here check.

---

<div align="center">

**Prove it here, because nothing downstream will.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by the Engineering Team. Distributed under the terms in [LICENSE](/LICENSE).

</div>
