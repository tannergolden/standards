<!--
title: '🧹 PRUNE DEPLOYMENTS'
description: 'Deletes superseded deployments, keeping the current successful one per environment.'
type: index
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 🧹 PRUNE DEPLOYMENTS

<a name="top"></a>

**Prune Deployments, called with `uses:` at the step level.**

_One `uses:` line, one job done._

</div>

---

## 💡 What This Folder Is For

[`action.yml`](action.yml) is the `prune-deployments` composite action: deletes superseded deployments, keeping the current successful one per environment. Another repository calls it as `tannergolden/standards/.github/actions/prune-deployments@v1`, and this repository's own self-checks as `./.github/actions/prune-deployments`. It ships [`.github/scripts/prune-deployments.py`](../../scripts/prune-deployments.py), found beside it at `$GITHUB_ACTION_PATH`. Its inputs and outputs are documented in `action.yml` itself.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                      | Purpose                                                                             |
| :------------------------- | :---------------------------------------------------------------------------------- |
| [`action.yml`](action.yml) | Deletes superseded deployments, keeping the current successful one per environment. |
| [`README.md`](README.md)   | This file.                                                                          |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**If it ships a file, it lives here.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
