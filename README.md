<!--
title: '📐 ENGINEERING STANDARDS'
description: 'Reusable GitHub Actions workflows and composite actions for any language or toolchain. Called, never copied, so a fix lands once and reaches every repository pinned to it.'
tags: [github-actions, reusable-workflows, ci-cd, engineering-standards]
category: docs
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 📐 ENGINEERING STANDARDS

<a name="top"></a>

**The rules every repository on this account follows, and the automation that enforces them.**

_Called, never copied._

</div>

---

## 💡 What This Repository Is

Every repository on this account gets its pipelines, guardrails, and conventions by **calling**
this repository, never by copying from it.

A consuming repository holds a short trigger stub. The logic, the scripts, the linter
configuration, and the standards themselves live here, so a fix lands once and reaches everything
that points at it.

```yaml
jobs:
  ci:
    uses: tannergolden/standards/.github/workflows/ci.yml@v1
    secrets: inherit
```

That stub has to live in your repository, because **GitHub only runs a workflow that is in the
repository being pushed to**. It is the one file ever copied, and `apply-standards.yml` writes it for
you, pinned and pointed at your own default branch.

> [!IMPORTANT]
> **Logic is never delivered by copying.** A trigger is not logic: it names events and nothing else,
> so it has nothing to drift out of date. If a consumer would have to paste anything with behavior in
> it into their own tree to benefit, it does not belong in this repository. That rule is what keeps
> this from becoming a scaffold that ages the moment it is used.

---

## 📦 What's Inside

| Path                                                | Purpose                                                                  |
| :-------------------------------------------------- | :----------------------------------------------------------------------- |
| [`.github/workflows/`](.github/workflows/README.md) | 22 reusable workflows, called with `uses:` at the job level              |
| [`actions/`](actions/README.md)                     | 15 composite actions, called with `uses:` at the step level              |
| [`data/`](data/README.md)                           | Rulesets and the label taxonomy, written **to** a repository             |
| `config/`                                           | Linter and tooling configuration, read **by** a tool during a run        |
| `docs/`                                             | The standards themselves, followed by link. Start at the standards index |
| `scripts/`                                          | Helpers the actions above ship and invoke                                |

The two `uses:` mechanisms are not interchangeable, and the difference decides where a thing lives.
A **reusable workflow** is checked out against the **calling** repository, so it can operate on your
tree but cannot see its own. A **composite action** is fetched with its whole repository, so it can
ship code and configuration beside it. Anything that carries a script or a config file is therefore
an action; anything that describes jobs is a workflow.

This repository holds itself to the same standards, in two layers. Its `self-*` stubs call these
workflows exactly the way yours will, which proves the published path works end to end. A separate
`self-checks` reads the working tree with no tag involved, which is the only thing that can check a
change **to** an action, since every other path resolves a pin and would test the released copy
rather than the diff.

---

## 🌿 Consuming These Standards

**Pin a tag, never a branch.** Nothing published here executes in your repository until you move
the pin.

| Pin            | Meaning                                           |
| :------------- | :------------------------------------------------ |
| `@v1`          | Moving major tag. The normal choice               |
| `@v1.4.2`      | Immutable release. For anyone who wants exactness |
| `@Development` | Never pin this. It is the development line        |

**Nothing here assumes your project.** Not your language, not your branch names, not your account.
CI runs the command you give it, or a Makefile target of that name, and fails outright if neither
exists rather than reporting a green check that checked nothing. Rulesets target `~DEFAULT_BRANCH`,
so `main` is protected as surely as anything else. No workflow has a required input or a required
secret; each one degrades and says what it skipped.

Start at [`.github/workflows/README.md`](.github/workflows/README.md) for the full list, the gate
set every repository installs by default, and the operations and publishing stubs you add by name.

Some job ids are part of the contract, not a matter of taste. A called workflow reports its checks
as `<your job id> / <job name>`, so branch protection depends on the id you give the job in your
stub. Those ids are fixed in [`data/README.md`](data/README.md), along with what breaks when one
changes.

> [!NOTE]
> Workflows here reference their own composite actions at the **major** tag. Pinning `@v1.4.2` freezes
> the workflow logic exactly, while the actions it calls track the `v1` line. If you need every layer
> frozen, pin a commit SHA.

Follow the documentation the same way: **link to it, do not copy it**. A standard duplicated into
your repository is a standard that starts going stale immediately.

---

## 🛡️ What Does _Not_ Live Here

Community health files, meaning the code of conduct, contributing guide, governance charter,
security policy, support guide, and the issue, discussion, and pull request templates, are served
account-wide by [`tannergolden/.github`](https://github.com/tannergolden/.github). The two
repositories never overlap.

Files GitHub only reads from the repository that owns them, such as `dependabot.yml`, `CODEOWNERS`,
`.editorconfig`, and `.gitattributes`, cannot be shared by any mechanism and are always local.

---

## 🧭 Contributing

Changes here reach every consuming repository the moment a tag moves, so treat each one as a
production change:

- **A standard and its gate change together.** Editing a rule without updating the workflow that
  enforces it produces a rule nobody enforces.
- **Additive over restrictive.** Tightening a rule tightens it everywhere at once.
- **Version deliberately.** Anything that changes a required check name is a breaking change for
  every consumer's branch protection.

---

<div align="center">

**One source for the rules. One source for the gates.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
