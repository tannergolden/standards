<!--
title: '📐 ENGINEERING STANDARDS'
description: 'Documented engineering standards, plus the reusable workflows and composite actions that enforce them for any toolchain. Called, never copied, so a fix lands once and reaches every repository pinned to it.'
type: index
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 📐 ENGINEERING STANDARDS

<a name="top"></a>

**The rules every repository on this account follows, and the automation that enforces them.**

_Called, never copied._

</div>

---

## 💡 What It Is

The conventions every repository on this account follows, and the reusable workflows, composite
actions and scripts that enforce them. A repository holds a short trigger stub and **calls** this
one; the logic, the scripts and the linter configuration live here, so a fix lands once and reaches
everything pinned to it.

Community health files are not here: [`tannergolden/.github`](https://github.com/tannergolden/.github)
serves them account-wide, and the two repositories never overlap.

- **Status**: Active, on the `v1` line.

---

## 🚀 Quick Start

A stub in your repository calls a workflow here, pinned to the moving major tag:

```yaml
jobs:
  ci:
    uses: tannergolden/standards/.github/workflows/ci.yml@v1
    secrets: inherit
```

GitHub only runs a workflow that lives in the repository being pushed to, so the stub is the one
file ever copied. A repository generated from the golden path template,
[`tannergolden/path`](https://github.com/tannergolden/path), starts with every stub already written.

---

## 📖 Using It

### 🌿 Consuming These Standards

**Pin a tag, never a branch.**

| Pin            | Meaning                                                              |
| :------------- | :------------------------------------------------------------------- |
| `@v1`          | Moving major tag. The normal choice                                  |
| `@v1.9.0`      | The release just cut. Pruned, tag and page, when the next one is cut |
| `@<commit>`    | Immutable. For anyone who wants exactness                            |
| `@Development` | Never pin this. It is the development line                           |

**Nothing here assumes your project**: not your language, your branch names or your account. CI
runs the command you give it, or a Makefile target of that name, and fails rather than report a
check that checked nothing. No workflow has a required input or secret.

Some job ids are part of the contract: a called workflow reports its checks as
`<your job id> / <job name>`, so branch protection depends on them.
[`data/README.md`](data/README.md) fixes those ids and says what breaks when one changes.

Follow the documents the same way: **link to them, do not copy them**. Start at the
[standards index](docs/README.md), and at [`.github/workflows/README.md`](.github/workflows/README.md)
for every workflow and the stubs that call it.

---

## 📦 What's Inside

| Path                                                | Purpose                                                                                                                                                                |
| :-------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`.github/workflows/`](.github/workflows/README.md) | 24 reusable workflows, called with `uses:` at the job level, plus three local to this repository: `self-checks.yml`, `self-dependabot.yml` and `intelligence-sync.yml` |
| [`.github/actions/`](.github/actions/README.md)     | 19 composite actions, called with `uses:` at the step level                                                                                                            |
| [`actions/`](actions/README.md)                     | Forwarders that keep each action's old address working until the next major version                                                                                    |
| [`data/`](data/README.md)                           | Rulesets, the label taxonomy and the repository settings, written **to** a repository                                                                                  |
| [`config/`](config/README.md)                       | Linter and tooling configuration, read **by** a tool during a run                                                                                                      |
| [`docs/`](docs/README.md)                           | The standards themselves, followed by link. Start at the standards index                                                                                               |
| [`.github/scripts/`](.github/scripts/README.md)     | Helpers the actions above ship and invoke                                                                                                                              |

---

## 🤝 Getting Involved

- **Questions**: [`SUPPORT.md`](https://github.com/tannergolden/.github/blob/Development/SUPPORT.md)
  says where to ask.
- **A bug or an idea**: open an issue from one of the forms.
- **A change**: read [Working On These Standards](docs/introduction/Working-On-These-Standards.md)
  first. A change here reaches every consumer the moment a tag moves, so a standard and its gate
  change together, and anything that renames a required check waits for the next major.
- **A release**: [Releasing These Standards](docs/distribution/Releasing-These-Standards.md), before
  moving `v1`.

---

## 🛡️ Security

Report a vulnerability privately, never in an issue:
[`SECURITY.md`](https://github.com/tannergolden/.github/blob/Development/SECURITY.md) says how, and
how fast a fix follows.

---

## ⚖️ Licence

The standards are released under the terms in [LICENSE](/LICENSE).

---

<div align="center">

**One source for the rules. One source for the gates.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the terms in [LICENSE](/LICENSE).

</div>
