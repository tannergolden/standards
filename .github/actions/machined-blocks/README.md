<!--
title: '🧠 MACHINED BLOCK CHECK'
description: 'Verifies every hash-marked block in the repository still matches the hash its marker carries.'
type: index
keywords: [github-actions, composite-action]
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 🧠 MACHINED BLOCK CHECK

<a name="top"></a>

**Machined Block Check, called with `uses:` at the step level.**

_One `uses:` line, one job done._

</div>

---

## 💡 What This Folder Is For

[`action.yml`](action.yml) is the `machined-blocks` composite action: verifies every hash-marked block in the repository still matches the hash its marker carries. Another repository calls it as `tannergolden/standards/.github/actions/machined-blocks@v1`, and this repository's own self-checks as `./.github/actions/machined-blocks`. It ships [`.github/scripts/machined-blocks.py`](../../scripts/machined-blocks.py), found beside it at `$GITHUB_ACTION_PATH`. Its inputs and outputs are documented in `action.yml` itself.

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

**If it ships a file, it lives here.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
