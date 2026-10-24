<!--
title: '🌿 DISTRIBUTION & WORKFLOW'
description: 'How code moves from a branch to a release: branching, commits, pull requests, CI, testing and versioning, and how these standards release themselves.'
type: index
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 🌿 DISTRIBUTION & WORKFLOW

<a name="top"></a>

**From a branch to a release.**

_One path, every repository._

</div>

---

## 💡 What This Folder Is For

The standards for moving a change through a repository, from its first commit to its release. What each automation does on its own is in [`automation/`](automation/README.md), and every standard is indexed in the [Standards Index](../README.md). How this repository cuts its own release is in [Releasing These Standards](Releasing-These-Standards.md).

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                                                                          | Purpose                                                                                                                                                                                                                              |
| :----------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`automation/`](automation/README.md)                                          | What each automation does for a repository on its own: schedules, code scanning, onboarding, link checks, formatting, template sync and triage.                                                                                      |
| [`Branching-Strategy-&-Workflow.md`](Branching-Strategy-&-Workflow.md)         | The quad-tier branching model and the workflow for moving code to production.                                                                                                                                                        |
| [`Continuous-Integration-&-Delivery.md`](Continuous-Integration-&-Delivery.md) | How CI and delivery are wired, from pull-request checks to release workflows.                                                                                                                                                        |
| [`Conventional-Commits.md`](Conventional-Commits.md)                           | The commit message standard every repository on these standards follows, including the two places it deliberately diverges from the specification.                                                                                   |
| [`Distribution-&-Workflow.md`](Distribution-&-Workflow.md)                     | Overview of the distribution and workflow documentation.                                                                                                                                                                             |
| [`Pull-Requests-&-Code-Reviews.md`](Pull-Requests-&-Code-Reviews.md)           | Pull-request etiquette and the code review rubric.                                                                                                                                                                                   |
| [`README.md`](README.md)                                                       | This file.                                                                                                                                                                                                                           |
| [`Releases-&-Versioning.md`](Releases-&-Versioning.md)                         | How releases are cut, versioned, and published.                                                                                                                                                                                      |
| [`Releasing-These-Standards.md`](Releasing-These-Standards.md)                 | How this repository releases itself with &#x1F3F7;&#xFE0F; Cut Release: choosing the version, what each guard refuses, what a run publishes and prunes, what consumers see, and what a new major involves. Read it before moving v1. |
| [`Testing-Strategy.md`](Testing-Strategy.md)                                   | The layered testing strategy from unit tests to end-to-end validation.                                                                                                                                                               |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**Branch, commit, review, release.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the terms in [LICENSE](/LICENSE).

</div>
