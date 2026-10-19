<!--
title: '↪️ UPDATE MACHINED INDEXES, OLD ADDRESS'
description: 'Keeps the old address of the update-indexes action working for a caller pinned to v1, by forwarding every input and output to .github/actions/update-indexes.'
type: index
keywords: [github-actions, forwarder]
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# ↪️ UPDATE MACHINED INDEXES, OLD ADDRESS

<a name="top"></a>

**The old address of Update Machined Indexes.**

_Kept until the next major version._

</div>

---

## 💡 What This Folder Is For

[`action.yml`](action.yml) keeps the old address, `tannergolden/standards/actions/update-indexes@v1`, working for a caller pinned to v1. It declares the same inputs and outputs as the action, which moved to [`.github/actions/update-indexes/`](../../.github/actions/update-indexes/README.md), and forwards every one. Call the new address instead: the forwarder goes at the next major version.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                      | Purpose                                                                                                         |
| :------------------------- | :-------------------------------------------------------------------------------------------------------------- |
| [`action.yml`](action.yml) | Regenerates, or checks, every machined index in a repository: folder logs, record registers and document lists. |
| [`README.md`](README.md)   | This file.                                                                                                      |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**Moved, never broken.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
