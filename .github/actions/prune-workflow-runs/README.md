<!--
title: '🧹 PRUNE WORKFLOW RUNS'
description: 'Deletes old workflow runs, keeping recent ones and anything tied to recent commits.'
type: index
keywords: [github-actions, composite-action]
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 🧹 PRUNE WORKFLOW RUNS

<a name="top"></a>

**Prune Workflow Runs, called with `uses:` at the step level.**

_One `uses:` line, one job done._

</div>

---

## 💡 What This Folder Is For

[`action.yml`](action.yml) is the `prune-workflow-runs` composite action: deletes old workflow runs, keeping recent ones and anything tied to recent commits. Another repository calls it as `tannergolden/standards/.github/actions/prune-workflow-runs@v1`, and this repository's own self-checks as `./.github/actions/prune-workflow-runs`. It ships [`.github/scripts/prune-workflow-runs.py`](../../scripts/prune-workflow-runs.py), found beside it at `$GITHUB_ACTION_PATH`. Its inputs and outputs are documented in `action.yml` itself.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                      | Purpose                                                                             |
| :------------------------- | :---------------------------------------------------------------------------------- |
| [`action.yml`](action.yml) | Deletes old workflow runs, keeping recent ones and anything tied to recent commits. |
| [`README.md`](README.md)   | This file.                                                                          |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**If it ships a file, it lives here.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
