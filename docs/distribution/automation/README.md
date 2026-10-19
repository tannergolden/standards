<!--
title: '🤖 AUTOMATION'
description: 'What each automation does for a repository on its own: schedules, code scanning, onboarding, link checks, formatting, template sync and triage.'
type: index
keywords: [automation, github-actions]
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 🤖 AUTOMATION

<a name="top"></a>

**What runs without being asked.**

_Every schedule, written down._

</div>

---

## 💡 What This Folder Is For

One page for each automation these standards ship, saying what it does, when it runs, and what it asks of you. The workflows themselves are in [`.github/workflows/`](../../../.github/workflows/README.md).

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                                                                    | Purpose                                                                                                                                                                           |
| :----------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`Automation-Schedules.md`](Automation-Schedules.md)                     | The recommended cadence for every scheduled workflow, and why the schedule lives in your repository rather than this one.                                                         |
| [`CodeQL-Analysis.md`](CodeQL-Analysis.md)                               | How the CodeQL static-analysis security workflow operates.                                                                                                                        |
| [`Contributor-Onboarding.md`](Contributor-Onboarding.md)                 | The automated welcome flow for first-time contributors.                                                                                                                           |
| [`Link-Checker.md`](Link-Checker.md)                                     | The scheduled link-integrity check for the documentation.                                                                                                                         |
| [`README.md`](README.md)                                                 | This file.                                                                                                                                                                        |
| [`Semantic-PRs-&-Auto-Formatting.md`](Semantic-PRs-&-Auto-Formatting.md) | Pull-request title enforcement and automatic formatting workflows.                                                                                                                |
| [`Template-Sync.md`](Template-Sync.md)                                   | How a repository generated from a template takes its later fixes when its owner runs the sync: what syncs, how an owner opts out, how conflicts are kept, and what it never does. |
| [`Triage-&-Labeling.md`](Triage-&-Labeling.md)                           | Automated triage, sizing, and labeling of issues and pull requests.                                                                                                               |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**It runs. You know why.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
