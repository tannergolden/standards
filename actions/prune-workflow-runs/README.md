<!--
title: '↪️ PRUNE WORKFLOW RUNS, OLD ADDRESS'
description: 'Keeps the old address of the prune-workflow-runs action working for a caller pinned to v1, by forwarding every input and output to .github/actions/prune-workflow-runs.'
type: index
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# ↪️ PRUNE WORKFLOW RUNS, OLD ADDRESS

<a name="top"></a>

**The old address of Prune Workflow Runs.**

_Kept until the next major version._

</div>

---

## 💡 What This Folder Is For

[`action.yml`](action.yml) keeps the old address, `tannergolden/standards/actions/prune-workflow-runs@v1`, working for a caller pinned to v1. It declares the same inputs and outputs as the action, which moved to [`.github/actions/prune-workflow-runs/`](../../.github/actions/prune-workflow-runs/README.md), and forwards every one. Call the new address instead: the forwarder goes at the next major version.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                      | Purpose                                                                             |
| :------------------------- | :---------------------------------------------------------------------------------- |
| [`action.yml`](action.yml) | Deletes old workflow runs, keeping recent ones and anything tied to recent commits. |
| [`README.md`](README.md)   | This file.                                                                          |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**Moved, never broken.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
