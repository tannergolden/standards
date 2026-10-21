<!--
title: '🧩 COMPOSITE ACTIONS'
description: 'Step-level building blocks called with uses:, and the rule that decides what belongs here rather than in a workflow.'
type: index
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 🧩 COMPOSITE ACTIONS

<a name="top"></a>

**Step-level pieces, called with `uses:` inside a job.**

_If it ships a file, it lives here._

</div>

---

## 💡 Why These Exist Separately

A **reusable workflow** and a **composite action** look interchangeable until you need a file. They
are not:

|                                        | Reusable workflow          | Composite action                          |
| :------------------------------------- | :------------------------- | :---------------------------------------- |
| Called at                              | Job level                  | Step level                                |
| `actions/checkout` gives you           | The **calling** repository | Nothing implicit                          |
| Its own repository's files             | **Unreachable**            | Fetched with it, at `$GITHUB_ACTION_PATH` |
| Can define jobs, permissions, matrices | Yes                        | No                                        |

That third row decides everything. A reusable workflow cannot read the config or script published
beside it, because its checkout resolves to whoever called it. A composite action can, because
GitHub fetches the whole repository alongside it.

So the rule is simple: **anything that has to ship a file with it is an action.** Everything that
only describes jobs is a workflow.

The actions moved here from a root `actions/` folder, where a forwarder keeps each old address
working for a caller pinned to `v1` until the next major version
([`actions/`](../../actions/README.md), [ADR-0001](../../docs/adrs/ADR-0001-Actions-And-Scripts-Live-In-Github.md)).

---

## 📦 What's Here

| Action                | Ships                                   | Does                                                                                                  |
| :-------------------- | :-------------------------------------- | :---------------------------------------------------------------------------------------------------- |
| `harden`              |                                         | Pins the runner-hardening action in one place, and posts the job notice                               |
| `setup`               |                                         | Makes the toolchains a repository uses available, detected from its manifests                         |
| `config`              | `config/*`                              | Hands a workflow a shared config file, honoring a caller override                                     |
| `dco-check`           | `.github/scripts/dco-check.sh`          | Verifies the sign-off trailer on every human commit in a pull request                                 |
| `commit-check`        | `.github/scripts/commit-check.py`       | Verifies every human commit message follows Conventional Commits                                      |
| `open-pr`             | `.github/scripts/open-pr.sh`            | Delivers automation changes as one evolving pull request                                              |
| `sync-labels`         | `data/labels.yml`, script               | Applies the label taxonomy, create-or-update, never pruning                                           |
| `apply-rulesets`      | `data/rulesets/*`, script               | Creates or updates branch and tag rulesets, matched by name                                           |
| `sbom`                | script                                  | Writes a dependency inventory for any ecosystem, not just npm                                         |
| `init-template`       | script                                  | Rewrites a generated repository's identity and deletes what only the template needs, once             |
| `standards-version`   | script                                  | Opens one issue when a newer major of these standards is published                                    |
| `ci-failure-alert`    | script                                  | Opens an issue when a watched workflow fails, closes it on recovery                                   |
| `prune-deployments`   | script                                  | Deletes superseded deployments, keeping the current successful one                                    |
| `prune-workflow-runs` | script                                  | Deletes old runs, keeping recent history and anything in flight                                       |
| `apply-settings`      | `data/repository-settings.json`, script | Brings every repository setting with a standard value in line with the published set, comparing first |
| `update-indexes`      | script                                  | Regenerates, or checks, every machined index in a repository                                          |
| `machined-blocks`     | script                                  | Fails when a block marked with its own hash, such as `INTELLIGENCE`, was edited by hand               |
| `check-frontmatter`   | script                                  | Checks every document opens with the hidden frontmatter the documentation standard defines            |
| `template-sync`       | script                                  | Brings a generated repository up to date with its template, on request; checks a template's list      |

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                                                   | Purpose                                                                                                                           |
| :------------------------------------------------------ | :-------------------------------------------------------------------------------------------------------------------------------- |
| [`apply-rulesets/`](apply-rulesets/README.md)           | Creates or updates the published branch and tag rulesets on a repository, matched by name.                                        |
| [`apply-settings/`](apply-settings/README.md)           | Brings a repository's settings in line with the published set, comparing before it writes.                                        |
| [`check-frontmatter/`](check-frontmatter/README.md)     | Verifies every Markdown document opens with the hidden frontmatter the documentation standard defines.                            |
| [`ci-failure-alert/`](ci-failure-alert/README.md)       | Opens an issue when a watched workflow fails and closes it when the workflow recovers.                                            |
| [`commit-check/`](commit-check/README.md)               | Verifies every human-authored commit in a pull request follows Conventional Commits.                                              |
| [`config/`](config/README.md)                           | Resolves a shared configuration file to a path, honoring a calling repository override.                                           |
| [`dco-check/`](dco-check/README.md)                     | Verifies the Signed-off-by trailer on every human-authored commit in a pull request.                                              |
| [`harden/`](harden/README.md)                           | Audits or blocks runner egress, and posts the job notice.                                                                         |
| [`init-template/`](init-template/README.md)             | Rewrites a generated repository's identity to its new owner and deletes what only the template needs, once, then disables itself. |
| [`machined-blocks/`](machined-blocks/README.md)         | Verifies every hash-marked block in the repository still matches the hash its marker carries.                                     |
| [`open-pr/`](open-pr/README.md)                         | Commits working-tree changes to a fixed branch and opens or updates one evolving pull request.                                    |
| [`prune-deployments/`](prune-deployments/README.md)     | Deletes superseded deployments, keeping the current successful one per environment.                                               |
| [`prune-workflow-runs/`](prune-workflow-runs/README.md) | Deletes old workflow runs, keeping recent ones and anything tied to recent commits.                                               |
| [`sbom/`](sbom/README.md)                               | Writes a CycloneDX or SPDX dependency inventory for any ecosystem, from the checked-out tree.                                     |
| [`setup/`](setup/README.md)                             | Makes the toolchains a repository uses available, detected from the manifests in its tree.                                        |
| [`standards-version/`](standards-version/README.md)     | Opens one issue when a newer major of the shared standards is published.                                                          |
| [`sync-labels/`](sync-labels/README.md)                 | Applies the shared label taxonomy to a repository, create-or-update, never pruning.                                               |
| [`template-sync/`](template-sync/README.md)             | Syncs a generated repository's scaffold from its template, checks a template's sync list, or tracks what waits on the owner.      |
| [`update-indexes/`](update-indexes/README.md)           | Regenerates, or checks, every machined index in a repository: folder logs, record registers and document lists.                   |
| [`README.md`](README.md)                                | This file.                                                                                                                        |

<!-- AUTO-INDEX:END -->

---

## 🌿 Calling One Directly

Actions are usable on their own, not only through the workflows here. Pin a tag, never a branch:

```yaml
steps:
  - uses: tannergolden/standards/.github/actions/harden@v1
    with:
      egress-policy: audit

  - uses: tannergolden/standards/.github/actions/setup@v1
```

> [!NOTE]
> The workflows in this repository reference these actions at the **major** tag. Pinning a workflow
> to an exact version freezes its logic while the actions it calls follow the `v1` line. Pin a commit
> SHA if you need every layer frozen.

---

<div align="center">

**Anything that ships a file is an action. Everything else is a workflow.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
