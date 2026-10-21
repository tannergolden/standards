<!--
title: '🏗️ AUTOMATION INTERNALS'
description: 'How the automation these standards ship is built and tested: the layers a call passes through, the shape of a workflow, an action and a script, and the suite over all of them.'
type: index
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 🏗️ AUTOMATION INTERNALS

<a name="top"></a>

**How the workflows, actions and scripts here are built, and how they are tested.**

_The inside of what every repository calls._

</div>

---

## 💡 What This Folder Is For

This repository's own technical pages: how the automation it publishes is put together, and how the suite in [`tests/`](../../../tests/README.md) tests it. What each automation does for a repository that calls it is in [`distribution/automation/`](../../distribution/automation/README.md), and how to change and release this repository is in [Working On These Standards](../../introduction/Working-On-These-Standards.md).

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                                                      | Purpose                                                                                                                                                                                                                                                                      |
| :--------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`Automation-Architecture.md`](Automation-Architecture.md) | How the automation these standards ship fits together: the layers a call passes through, the ref each one resolves at, where an action finds its files, and the shape every workflow, action and script here keeps. Read it before adding or changing one.                   |
| [`README.md`](README.md)                                   | This file.                                                                                                                                                                                                                                                                   |
| [`Test-Suite.md`](Test-Suite.md)                           | How the pytest suite tests code that mostly lives inside workflow and action YAML: the fixtures that read a step and run it against a scripted gh, the conventions every test file keeps, and how to run part of the suite. Read it before writing or debugging a test here. |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**Built here, called everywhere.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
