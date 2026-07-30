<!--
title: '🧩 COMPOSITE ACTIONS'
description: 'Step-level building blocks called with uses:, and the rule that decides what belongs here rather than in a workflow.'
tags: [actions, composite, reusable, github-actions]
category: docs
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

---

## 📦 What's Here

| Action                | Ships                     | Does                                                                          |
| :-------------------- | :------------------------ | :---------------------------------------------------------------------------- |
| `harden`              |                           | Pins the runner-hardening action in one place, and posts the job notice       |
| `setup`               |                           | Makes the toolchains a repository uses available, detected from its manifests |
| `config`              | `config/*`                | Hands a workflow a shared config file, honoring a caller override             |
| `dco-check`           | `scripts/dco-check.sh`    | Verifies the sign-off trailer on every human commit in a pull request         |
| `commit-check`        | `scripts/commit-check.py` | Verifies every human commit message follows Conventional Commits              |
| `open-pr`             | `scripts/open-pr.sh`      | Delivers automation changes as one evolving pull request                      |
| `sync-labels`         | `data/labels.yml`, script | Applies the label taxonomy, create-or-update, never pruning                   |
| `apply-rulesets`      | `data/rulesets/*`, script | Creates or updates branch and tag rulesets, matched by name                   |
| `sbom`                | script                    | Writes a dependency inventory for any ecosystem, not just npm                 |
| `init-template`       | script                    | Rewrites a generated repository's identity to its new owner, once             |
| `standards-version`   | script                    | Opens one issue when a newer major of these standards is published            |
| `ci-failure-alert`    | script                    | Opens an issue when a watched workflow fails, closes it on recovery           |
| `prune-deployments`   | script                    | Deletes superseded deployments, keeping the current successful one            |
| `prune-workflow-runs` | script                    | Deletes old runs, keeping recent history and anything in flight               |
| `apply-settings`      | script                    | Brings a repository's settings in line with the published set                 |

---

## 🌿 Calling One Directly

Actions are usable on their own, not only through the workflows here. Pin a tag, never a branch:

```yaml
steps:
  - uses: tannergolden/standards/actions/harden@v1
    with:
      egress-policy: audit

  - uses: tannergolden/standards/actions/setup@v1
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
