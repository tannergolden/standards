<!--
title: '🏷️ SYNC LABELS'
description: 'Applies the shared label taxonomy to a repository, create-or-update, never pruning.'
type: index
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 🏷️ SYNC LABELS

<a name="top"></a>

**Sync Labels, called with `uses:` at the step level.**

_One `uses:` line, one job done._

</div>

---

## 💡 What This Folder Is For

[`action.yml`](action.yml) is the `sync-labels` composite action: applies the shared label taxonomy to a repository, create-or-update, never pruning. Another repository calls it as `tannergolden/standards/.github/actions/sync-labels@v1`, and this repository's own self-checks as `./.github/actions/sync-labels`. It ships [`data/labels.yml`](../../../data/labels.yml), [`.github/scripts/sync-labels.sh`](../../scripts/sync-labels.sh), found beside it at `$GITHUB_ACTION_PATH`. Its inputs and outputs are documented in `action.yml` itself.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                      | Purpose                                                                             |
| :------------------------- | :---------------------------------------------------------------------------------- |
| [`action.yml`](action.yml) | Applies the shared label taxonomy to a repository, create-or-update, never pruning. |
| [`README.md`](README.md)   | This file.                                                                          |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**If it ships a file, it lives here.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the terms in [LICENSE](/LICENSE).

</div>
