<!--
title: '↪️ ESCALATE OR RESOLVE A CI FAILURE, OLD ADDRESS'
description: 'Keeps the old address of the ci-failure-alert action working for a caller pinned to v1, by forwarding every input and output to .github/actions/ci-failure-alert.'
type: index
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# ↪️ ESCALATE OR RESOLVE A CI FAILURE, OLD ADDRESS

<a name="top"></a>

**The old address of Escalate or Resolve a CI Failure.**

_Kept until the next major version._

</div>

---

## 💡 What This Folder Is For

[`action.yml`](action.yml) keeps the old address, `tannergolden/standards/actions/ci-failure-alert@v1`, working for a caller pinned to v1. It declares the same inputs and outputs as the action, which moved to [`.github/actions/ci-failure-alert/`](../../.github/actions/ci-failure-alert/README.md), and forwards every one. Call the new address instead: the forwarder goes at the next major version.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                      | Purpose                                                                                |
| :------------------------- | :------------------------------------------------------------------------------------- |
| [`action.yml`](action.yml) | Opens an issue when a watched workflow fails and closes it when the workflow recovers. |
| [`README.md`](README.md)   | This file.                                                                             |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**Moved, never broken.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
