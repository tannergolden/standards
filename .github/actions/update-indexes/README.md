<!--
title: '🗂️ UPDATE MACHINED INDEXES'
description: 'Regenerates, or checks, every machined index in a repository: folder logs, record registers and document lists.'
type: index
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 🗂️ UPDATE MACHINED INDEXES

<a name="top"></a>

**Update Machined Indexes, called with `uses:` at the step level.**

_One `uses:` line, one job done._

</div>

---

## 💡 What This Folder Is For

[`action.yml`](action.yml) is the `update-indexes` composite action: regenerates, or checks, every machined index in a repository: folder logs, record registers and document lists. Another repository calls it as `tannergolden/standards/.github/actions/update-indexes@v1`, and this repository's own self-checks as `./.github/actions/update-indexes`. It ships [`.github/scripts/update-doc-indexes.py`](../../scripts/update-doc-indexes.py), found beside it at `$GITHUB_ACTION_PATH`. Its inputs and outputs are documented in `action.yml` itself.

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

**If it ships a file, it lives here.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
