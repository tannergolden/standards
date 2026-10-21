<!--
title: '⬆️ STANDARDS VERSION CHECK'
description: 'Opens one issue when a newer major of the shared standards is published.'
type: index
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# ⬆️ STANDARDS VERSION CHECK

<a name="top"></a>

**Standards Version Check, called with `uses:` at the step level.**

_One `uses:` line, one job done._

</div>

---

## 💡 What This Folder Is For

[`action.yml`](action.yml) is the `standards-version` composite action: opens one issue when a newer major of the shared standards is published. Another repository calls it as `tannergolden/standards/.github/actions/standards-version@v1`, and this repository's own self-checks as `./.github/actions/standards-version`. It ships [`.github/scripts/check-standards-version.py`](../../scripts/check-standards-version.py), found beside it at `$GITHUB_ACTION_PATH`. Its inputs and outputs are documented in `action.yml` itself.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                      | Purpose                                                                  |
| :------------------------- | :----------------------------------------------------------------------- |
| [`action.yml`](action.yml) | Opens one issue when a newer major of the shared standards is published. |
| [`README.md`](README.md)   | This file.                                                               |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**If it ships a file, it lives here.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
