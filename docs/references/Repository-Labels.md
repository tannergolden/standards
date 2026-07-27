<!--
title: '📝 REPOSITORY LABELS'
description: 'The label taxonomy applied to issues and pull requests, with the meaning, color, and applier of every label.'
tags: [labels, triage, governance, taxonomy]
category: docs
-->

<!-- markdownlint-disable MD041 -->
<div align="center">

# 📝 REPOSITORY LABELS

<a name="top"></a>

**A structured labeling system designed to categorize intent, track lifecycles, and automate release versioning.**

_Systematic categorization. Automated release notes. High-signal triage._

</div>

---

## 🎯 Our Labeling Philosophy

We utilize labels to provide instant visual context and to power our automation engine. Every Issue and Pull Request (PR) must be labeled accurately to ensure it is routed to the correct owners and prioritized correctly in the release cycle.

- **Mandatory Taxonomy**: Every PR requires at least one **SemVer**, **Area**, and **Type** label.
- **Automation Fuel**: Labels trigger CI/CD behaviors and group the auto-generated release notes (versions themselves come from Conventional Commit history, not labels).
- **Visual Clarity**: Color-coded categories allow for rapid scan-ability of the project board.

> [!NOTE]
> The canonical registry is [`data/labels.yml`](../../data/labels.yml) in the standards
> repository. It is applied to a repository through the GitHub API by the governance
> workflow's label sync, create-or-update and never pruning, so labels a repository adds for
> itself survive. Nothing is copied into a consuming tree.

---

## 🤖 Who Applies What

Most labels arrive mechanically - know which ones are yours to set and which the machine owns (a manual change to a machine-owned label is re-asserted on the next event):

| Applier                          | Labels it owns                                                                                                                            |
| :------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------- |
| **Issue forms** (at creation)    | `type: *` and `status: needs triage`; two also declare a fixed `area: *`.                                                                    |
| **Path labeler** (every PR push) | `area: *` from the file paths touched, per [`config/labeler.yml`](../../config/labeler.yml).                                                 |
| **Size labeler** (every PR push) | `size: *` from the changed-lines count.                                                                                                   |
| **Conflict / stale sweeps**      | `status: conflict` on merge-conflict PRs; `status: stale` on long-inactive items.                                                         |
| **CI failure alerts**            | `ci: failure` on the auto-opened issue when a core workflow breaks (removed on recovery).                                                 |
| **Dependabot**                   | `dependencies` on its update PRs.                                                                                                         |
| **Automation PR openers**        | `automated` on machine-authored PRs (the licence-year roll, the doc-index refresh) - stale-exempt, filterable.                               |
| **You (humans)**                 | `priority: *`, `risk: *`, `semver: *`, `status: needs info`, the community trio, and any triage corrections.                              |

---

## 🗂️ The Registry

Every label, by family. **This section is generated** from
[`data/labels.yml`](../../data/labels.yml) by
[`scripts/update-label-docs.py`](../../scripts/update-label-docs.py), and CI fails if it drifts -
edit the registry and re-run the script, never the table. The colours below had already fallen
behind the registry twice before this was mechanised.

> [!IMPORTANT]
> **Every Pull Request must have exactly one `semver:` label.** It declares the change's impact for
> reviewers and groups the entry in the auto-generated release notes. The next version string itself
> is computed by git-cliff from **Conventional Commit history** - the label documents impact, it does
> not drive the bump, so make sure the PR title's type (`feat:`, `fix:`, `!`) matches the label.

### 🎨 What The Colour Means

Colour encodes **severity**, not family; the prefix already encodes family. So `#b60205` is red in
`priority: critical`, `semver: major`, `risk: critical`, `size: extra large` and `type: security`
alike, and that is deliberate - a board scan should surface everything urgent regardless of which
family it came from. Within a family every colour is distinct, because there the colour is the only
thing telling two entries apart.

The nine GitHub stock labels are the exception: they carry GitHub's own colours and descriptions,
byte-for-byte, emoji-free. A repository that never applies this taxonomy should be indistinguishable
from one that did, for those nine.

<!-- BEGIN GENERATED LABELS -->

<!-- Generated by scripts/update-label-docs.py from data/labels.yml.
     Edit the registry, then run the script. Hand edits here are
     overwritten and CI fails on drift. -->

### 🚦 Priority

| Label | Colour | Meaning |
| :---- | :----- | :------ |
| `priority: critical` | `#b60205` | 🚨 Urgent. Production outage, severe crash, or security breach. Must be fixed immediately. |
| `priority: high` | `#d93f0b` | 🛑 Blocking. Blocks a release or significant functionality. Needs attention very soon. |
| `priority: medium` | `#fbca04` | 🟡 Normal. Standard scheduled work. Important but does not block a release. |
| `priority: low` | `#0e8a16` | 🟢 Optional. Nice-to-have features or cosmetic tweaks. Pick up when time permits. |

### 📦 Semantic Versioning

| Label | Colour | Meaning |
| :---- | :----- | :------ |
| `semver: major` | `#b60205` | 💥 Breaking Change. Incompatible API changes. Bumps MAJOR version. |
| `semver: minor` | `#1d76db` | 🎉 New Feature. Backward-compatible functionality. Bumps MINOR version. |
| `semver: patch` | `#0e8a16` | 🩹 Bug Fix. Backward-compatible fix. Bumps PATCH version. |
| `semver: none` | `#bfdadc` | 👻 Internal. Changes to tests, CI, or docs that do not require a version bump. |

### ☢️ Risk

| Label | Colour | Meaning |
| :---- | :----- | :------ |
| `risk: critical` | `#b60205` | ☢️ Extremely high risk. Likely to cause outages or break core functionality. |
| `risk: high` | `#d93f0b` | 🔥 High chance of side effects. Requires extensive regression testing. |
| `risk: medium` | `#fbca04` | 🌩️ Moderate risk. Changes logic that could impact other components. |
| `risk: low` | `#0e8a16` | 🌤️ Minimal risk. Unlikely to cause regressions or side effects. |
| `risk: none` | `#c2e0c6` | 🏳️ Zero risk. Changes to documentation, comments, or formatting only. |

### 📋 Status & Lifecycle

| Label | Colour | Meaning |
| :---- | :----- | :------ |
| `status: needs triage` | `#f9d0c4` | 🔍 New issue waiting for a maintainer to validate and categorize it. |
| `status: ready` | `#0e8a16` | ✅ Triaged and specified; ready for someone to pick up. |
| `status: needs info` | `#f7c6c7` | 🗣️ Waiting on the author for details; a reply un-sticks it, silence lets it go stale. |
| `status: in progress` | `#c5def5` | 🏗️ A contributor is actively working on this task. |
| `status: needs review` | `#bfd4f2` | 👀 Code is written and the Pull Request is waiting for peer review. |
| `status: blocked` | `#e99695` | ⛔ Work cannot proceed due to external factors or dependencies. |
| `status: on hold` | `#fbca04` | ⏸️ Intentionally paused; work is deferred for now. |
| `status: conflict` | `#d93f0b` | 🔀 The pull request has merge conflicts that must be resolved. |
| `status: stale` | `#fef2c0` | 🕸️ Inactive for a long period; will be closed if no further activity occurs. |
| `status: awaiting release` | `#5319e7` | 🚢 Merged and waiting for the next release; the fix exists but is not published yet. |

### 🚨 Continuous Integration

| Label | Colour | Meaning |
| :---- | :----- | :------ |
| `ci: failure` | `#b60205` | 🚨 A core workflow is failing on a long-lived branch (opened/closed automatically). |

### 👚 Size

| Label | Colour | Meaning |
| :---- | :----- | :------ |
| `size: extra small` | `#c2e0c6` | 🐜 Tiny change. Likely a one-line fix, typo correction, or config tweak. |
| `size: small` | `#0e8a16` | 🔹 Small task. Straightforward work that takes a few hours. |
| `size: medium` | `#fbca04` | 🔶 Medium task. Standard feature or bug fix taking a few days. |
| `size: large` | `#d93f0b` | 🟥 Large task. Significant logic changes or new feature implementation. |
| `size: extra large` | `#b60205` | 🦕 Massive task. High complexity; implies the issue should probably be broken down. |

### 🏷️ Change Types

| Label | Colour | Meaning |
| :---- | :----- | :------ |
| `type: security` | `#b60205` | 🔒 Security fixes, patches, or vulnerability resolution. |
| `type: tests` | `#c2e0c6` | 🧪 Adding, updating, or fixing unit/integration/E2E tests. |
| `type: documentation` | `#0052cc` | 📚 Improvements or additions to documentation/READMEs. |
| `type: chore` | `#bfdadc` | 🔧 Routine maintenance, dependency updates, or build scripts. |
| `type: refactor` | `#c5def5` | ♻️ Code changes that improve structure or quality without changing behavior. |
| `type: performance` | `#fbca04` | ⚡ Improvements to speed, memory usage, or resource optimization. |
| `type: discussion` | `#d4c5f9` | 💬 Requires conversation or a decision before coding begins. |
| `type: release` | `#5319e7` | 🚀 Tasks specifically related to shipping a new version or deploying. |
| `type: accessibility` | `#006b75` | ♿ Fixes or features to ensure A11y compliance. |
| `type: bug` | `#d73a4a` | 🐛 An unexpected problem or unintended behavior in the code. |
| `type: feature` | `#1d76db` | ✨ A request for new functionality or capability. |
| `type: feedback` | `#fef2c0` | 💡 General feedback, suggestions, or impressions from users. |
| `type: build` | `#e4e669` | 🏗️ Build system, packaging, or external dependency changes. |
| `type: ci` | `#bfd4f2` | ⚙️ CI configuration, workflows, or pipeline changes. |
| `type: style` | `#f9d0c4` | 🎨 Formatting and whitespace only; no change to behaviour. |
| `type: revert` | `#e99695` | ⏪ Reverts an earlier change; the commit undone is named in the body. |
| `type: deprecation` | `#d93f0b` | ⚠️ Still works today, scheduled for removal in a future major; the warning before the break. |

### 🏗️ Technical Areas

| Label | Colour | Meaning |
| :---- | :----- | :------ |
| `area: infrastructure` | `#006b75` | 🧱 Core infrastructure, cloud resources, CI/CD pipelines, or hosting. |
| `area: dx` | `#c5def5` | 💻 Developer Experience: Tooling, scripts, and workflows to improve productivity. |
| `area: governance` | `#5319e7` | ⚖️ Licenses, code of conduct, security policies, and contribution guidelines. |
| `area: frontend` | `#bfdadc` | 🌐 Client-side code, web interface, or browser logic. |
| `area: backend` | `#008672` | ⚙️ Server-side logic, databases, or API endpoints. |
| `area: mobile` | `#1d76db` | 📱 iOS, Android, or React Native specific code. |
| `area: ui/ux` | `#fef2c0` | 🎨 Visual design, CSS styling, or user experience flows. |
| `area: database` | `#fbca04` | 🗄️ SQL queries, schema changes, or migrations. |
| `area: api` | `#bfd4f2` | 📡 REST or GraphQL interface definitions. |
| `area: analytics` | `#d4c5f9` | 📈 Tracking, data logging, or business intelligence. |
| `area: i18n` | `#0052cc` | 🌍 Internationalization, translations, or localization. |

### 🤝 GitHub Defaults & Community

| Label | Colour | Meaning |
| :---- | :----- | :------ |
| `bug` | `#d73a4a` | Something isn't working |
| `enhancement` | `#a2eeef` | New feature or request |
| `documentation` | `#0075ca` | Improvements or additions to documentation |
| `invalid` | `#e4e669` | This doesn't seem right |
| `duplicate` | `#cfd3d7` | This issue or pull request already exists |
| `wontfix` | `#ffffff` | This will not be worked on |
| `automated` | `#c0a062` | 🤖 Opened by repository automation (sync, formatting, refresh) - stale-exempt and ready to merge. |
| `dependencies` | `#0052cc` | 📦 Pull requests that update a dependency file (usually created by bots). |
| `regression` | `#b60205` | 📉 Worked in an earlier release and does not now; a fix should add a test. |
| `upstream` | `#5319e7` | ⬆️ The cause is in a dependency; tracked here, fixed there. |
| `pinned` | `#1d76db` | 📌 Never auto-close. The stale sweep skips anything carrying this. |
| `good first issue` | `#7057ff` | Good for newcomers |
| `help wanted` | `#008672` | Extra attention is needed |
| `question` | `#d876e3` | Further information is requested |

_71 labels._ The registry is [`data/labels.yml`](../../data/labels.yml).

<!-- END GENERATED LABELS -->

---

### 🔗 See also

> [!TIP]
> Every canonical guide is indexed in the [&#x1F4DA; Standards Index](https://github.com/tannergolden/standards/blob/Development/docs/README.md). If you rename or move a file, update every reference to it across the repository to prevent link drift.

---

<div align="center">

**Categorized for clarity. Labeled for scale.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by the Engineering Team. Distributed under the MIT License.

</div>
