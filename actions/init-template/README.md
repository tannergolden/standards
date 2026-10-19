<!--
title: '↪️ INITIALISE FROM TEMPLATE, OLD ADDRESS'
description: 'Keeps the old address of the init-template action working for a caller pinned to v1, by forwarding every input and output to .github/actions/init-template.'
type: index
keywords: [github-actions, forwarder]
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# ↪️ INITIALISE FROM TEMPLATE, OLD ADDRESS

<a name="top"></a>

**The old address of Initialise From Template.**

_Kept until the next major version._

</div>

---

## 💡 What This Folder Is For

[`action.yml`](action.yml) keeps the old address, `tannergolden/standards/actions/init-template@v1`, working for a caller pinned to v1. It declares the same inputs and outputs as the action, which moved to [`.github/actions/init-template/`](../../.github/actions/init-template/README.md), and forwards every one. Call the new address instead: the forwarder goes at the next major version.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                      | Purpose                                                                                                                           |
| :------------------------- | :-------------------------------------------------------------------------------------------------------------------------------- |
| [`action.yml`](action.yml) | Rewrites a generated repository's identity to its new owner and deletes what only the template needs, once, then disables itself. |
| [`README.md`](README.md)   | This file.                                                                                                                        |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**Moved, never broken.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
