<!--
title: '⚙️ APPLY REPOSITORY SETTINGS'
description: 'Brings a repository''s settings in line with the published set, comparing before it writes.'
type: index
keywords: [github-actions, composite-action]
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# ⚙️ APPLY REPOSITORY SETTINGS

<a name="top"></a>

**Apply Repository Settings, called with `uses:` at the step level.**

_One `uses:` line, one job done._

</div>

---

## 💡 What This Folder Is For

[`action.yml`](action.yml) is the `apply-settings` composite action: brings a repository's settings in line with the published set, comparing before it writes. Another repository calls it as `tannergolden/standards/.github/actions/apply-settings@v1`, and this repository's own self-checks as `./.github/actions/apply-settings`. It ships [`data/repository-settings.json`](../../../data/repository-settings.json), [`.github/scripts/apply-settings.py`](../../scripts/apply-settings.py), found beside it at `$GITHUB_ACTION_PATH`. Its inputs and outputs are documented in `action.yml` itself.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                      | Purpose                                                                                    |
| :------------------------- | :----------------------------------------------------------------------------------------- |
| [`action.yml`](action.yml) | Brings a repository's settings in line with the published set, comparing before it writes. |
| [`README.md`](README.md)   | This file.                                                                                 |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**If it ships a file, it lives here.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
