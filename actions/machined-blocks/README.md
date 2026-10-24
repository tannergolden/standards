<!--
title: '↪️ MACHINED BLOCK CHECK, OLD ADDRESS'
description: 'Keeps the old address of the machined-blocks action working for a caller pinned to v1, by forwarding every input and output to .github/actions/machined-blocks.'
type: index
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# ↪️ MACHINED BLOCK CHECK, OLD ADDRESS

<a name="top"></a>

**The old address of Machined Block Check.**

_Kept until the next major version._

</div>

---

## 💡 What This Folder Is For

[`action.yml`](action.yml) keeps the old address, `tannergolden/standards/actions/machined-blocks@v1`, working for a caller pinned to v1. It declares the same inputs and outputs as the action, which moved to [`.github/actions/machined-blocks/`](../../.github/actions/machined-blocks/README.md), and forwards every one. Call the new address instead: the forwarder goes at the next major version.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                      | Purpose                                                                                       |
| :------------------------- | :-------------------------------------------------------------------------------------------- |
| [`action.yml`](action.yml) | Verifies every hash-marked block in the repository still matches the hash its marker carries. |
| [`README.md`](README.md)   | This file.                                                                                    |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**Moved, never broken.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the terms in [LICENSE](/LICENSE).

</div>
