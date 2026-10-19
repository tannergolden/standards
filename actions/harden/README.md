<!--
title: '↪️ HARDEN RUNNER, OLD ADDRESS'
description: 'Keeps the old address of the harden action working for a caller pinned to v1, by forwarding every input and output to .github/actions/harden.'
type: index
keywords: [github-actions, forwarder]
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# ↪️ HARDEN RUNNER, OLD ADDRESS

<a name="top"></a>

**The old address of Harden Runner.**

_Kept until the next major version._

</div>

---

## 💡 What This Folder Is For

[`action.yml`](action.yml) keeps the old address, `tannergolden/standards/actions/harden@v1`, working for a caller pinned to v1. It declares the same inputs and outputs as the action, which moved to [`.github/actions/harden/`](../../.github/actions/harden/README.md), and forwards every one. Call the new address instead: the forwarder goes at the next major version.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                      | Purpose                                                   |
| :------------------------- | :-------------------------------------------------------- |
| [`action.yml`](action.yml) | Audits or blocks runner egress, and posts the job notice. |
| [`README.md`](README.md)   | This file.                                                |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**Moved, never broken.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
