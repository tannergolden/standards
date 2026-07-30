<!--
title: '📚 STANDARDS INDEX'
description: 'The index of every engineering standard published by this repository, grouped by the part of the lifecycle it governs.'
tags: [standards, documentation, index, engineering]
category: docs
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 📚 STANDARDS INDEX

<a name="top"></a>

**Every standard published here, grouped by the part of the lifecycle it governs.**

_The rule and the gate that enforces it, in one place._

</div>

---

## 💡 How To Read These

Each document is a **standard**, not a suggestion. Where a standard is mechanically enforced, the
workflow or action that enforces it lives in this same repository, so a rule and its gate version
together and can never drift apart.

Repositories follow these documents **by link**. Nothing here is copied into a consuming
repository, which is why a correction lands once and reaches everything.

---

## 🌿 Distribution & Workflow

How work moves from a branch to a release.

| Standard                                                                               | Covers                                                |
| :------------------------------------------------------------------------------------- | :---------------------------------------------------- |
| [Distribution & Workflow](distribution/Distribution-&-Workflow.md)                     | Section overview                                      |
| [Branching Strategy & Workflow](distribution/Branching-Strategy-&-Workflow.md)         | The branch model every trigger keys on                |
| [Conventional Commits](distribution/Conventional-Commits.md)                           | The commit message standard, and where it is enforced |
| [Pull Requests & Code Reviews](distribution/Pull-Requests-&-Code-Reviews.md)           | Review rubric and etiquette                           |
| [Continuous Integration & Delivery](distribution/Continuous-Integration-&-Delivery.md) | How the pipelines are wired                           |
| [Testing Strategy](distribution/Testing-Strategy.md)                                   | The layered testing contract                          |
| [Releases & Versioning](distribution/Releases-&-Versioning.md)                         | Cutting, versioning, and publishing releases          |

---

## 🤖 Automation

What each workflow does, and when it runs.

| Standard                                                                                    | Covers                               |
| :------------------------------------------------------------------------------------------ | :----------------------------------- |
| [Automation Schedules](distribution/automation/Automation-Schedules.md)                     | Every cron, in one table             |
| [CodeQL Analysis](distribution/automation/CodeQL-Analysis.md)                               | Static analysis security scanning    |
| [Semantic PRs & Auto-Formatting](distribution/automation/Semantic-PRs-&-Auto-Formatting.md) | Title enforcement and formatting     |
| [Triage & Labeling](distribution/automation/Triage-&-Labeling.md)                           | Automated triage, sizing, and labels |
| [Link Checker](distribution/automation/Link-Checker.md)                                     | Scheduled link-integrity checks      |
| [Contributor Onboarding](distribution/automation/Contributor-Onboarding.md)                 | The first-time contributor flow      |

---

## 🛡️ Operations & Security

The guardrails, and what to do when one trips.

| Standard                                                     | Covers                                      |
| :----------------------------------------------------------- | :------------------------------------------ |
| [Operations & Security](operations/Operations-&-Security.md) | Section overview                            |
| [Branch Protection](operations/Branch-Protection.md)         | Protection rules, applied as code           |
| [Repository Settings](operations/Repository-Settings.md)     | Every setting mapped: written or explained  |
| [Security & Secrets](operations/Security-&-Secrets.md)       | Secret handling, scanning, and response     |
| [Dependency Management](operations/Dependency-Management.md) | Update cadence and supply-chain safety      |
| [Repository Hygiene](operations/Repository-Hygiene.md)       | Keeping a repository clean over time        |
| [Troubleshooting](operations/Troubleshooting.md)             | First-responder guide for pipeline failures |

---

## ⚙️ Contracts

The interfaces a consuming repository is expected to satisfy.

| Standard                                                                              | Covers                                             |
| :------------------------------------------------------------------------------------ | :------------------------------------------------- |
| [What You Do By Hand](introduction/What-You-Do-By-Hand.md)                            | Every step automation cannot take for you          |
| [Guiding Principles](introduction/Guiding-Principles.md)                              | The engineering principles behind every other rule |
| [Environment & Technologies](introduction/Environment-&-Technologies.md)              | The language-agnostic `make` interface CI assumes  |
| [Document Styling & Formatting](technical/interface/Document-Styling-&-Formatting.md) | The binding documentation specification            |
| [Repository Labels](references/Repository-Labels.md)                                  | The label taxonomy and who applies each one        |

---

## 📖 Reference

Fast lookups and background.

| Reference                                                 | Covers                                 |
| :-------------------------------------------------------- | :------------------------------------- |
| [References](references/References.md)                    | Index of the reference material        |
| [Glossary](references/Glossary.md)                        | Terms used across every standard       |
| [Reference Library](library/Reference-Library.md)         | Index of the educational guides        |
| [GitHub Concepts Recap](library/GitHub-Concepts-Recap.md) | The mental model behind the workflow   |
| [Git Commands](library/Git-Commands.md)                   | Copy-paste commands for the daily loop |
| [Learning & Development](library/Learning.md)             | Curated resources for the toolchain    |

---

<div align="center">

**One rule, one gate, one place to read both.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
