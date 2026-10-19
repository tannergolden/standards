<!--
title: '🧰 SETUP TOOLCHAIN'
description: 'Makes the toolchains a repository uses available, detected from the manifests in its tree.'
type: index
keywords: [github-actions, composite-action]
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 🧰 SETUP TOOLCHAIN

<a name="top"></a>

**Setup Toolchain, called with `uses:` at the step level.**

_One `uses:` line, one job done._

</div>

---

## 💡 What This Folder Is For

[`action.yml`](action.yml) is the `setup` composite action: makes the toolchains a repository uses available, detected from the manifests in its tree. Another repository calls it as `tannergolden/standards/.github/actions/setup@v1`, and this repository's own self-checks as `./.github/actions/setup`. Its inputs and outputs are documented in `action.yml` itself.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                      | Purpose                                                                                    |
| :------------------------- | :----------------------------------------------------------------------------------------- |
| [`action.yml`](action.yml) | Makes the toolchains a repository uses available, detected from the manifests in its tree. |
| [`README.md`](README.md)   | This file.                                                                                 |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**If it ships a file, it lives here.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
