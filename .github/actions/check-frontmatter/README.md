<!--
title: '🗂️ FRONTMATTER CHECK'
description: 'Verifies every Markdown document opens with the hidden frontmatter the documentation standard defines.'
type: index
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 🗂️ FRONTMATTER CHECK

<a name="top"></a>

**Frontmatter Check, called with `uses:` at the step level.**

_One `uses:` line, one job done._

</div>

---

## 💡 What This Folder Is For

[`action.yml`](action.yml) is the `check-frontmatter` composite action: verifies every Markdown document opens with the hidden frontmatter the documentation standard defines. Another repository calls it as `tannergolden/standards/.github/actions/check-frontmatter@v1`, and this repository's own self-checks as `./.github/actions/check-frontmatter`. It ships [`.github/scripts/check-frontmatter.py`](../../scripts/check-frontmatter.py), found beside it at `$GITHUB_ACTION_PATH`. Its inputs and outputs are documented in `action.yml` itself.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                      | Purpose                                                                                                |
| :------------------------- | :----------------------------------------------------------------------------------------------------- |
| [`action.yml`](action.yml) | Verifies every Markdown document opens with the hidden frontmatter the documentation standard defines. |
| [`README.md`](README.md)   | This file.                                                                                             |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**If it ships a file, it lives here.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
