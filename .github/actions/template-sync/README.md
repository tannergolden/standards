<!--
title: '🔄 TEMPLATE SYNC'
description: 'Syncs a generated repository''s scaffold from its template, checks a template''s sync list, or tracks what waits on the owner.'
type: index
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 🔄 TEMPLATE SYNC

<a name="top"></a>

**Template Sync, called with `uses:` at the step level.**

_One `uses:` line, one job done._

</div>

---

## 💡 What This Folder Is For

[`action.yml`](action.yml) is the `template-sync` composite action: syncs a generated repository's scaffold from its template, checks a template's sync list, or tracks what waits on the owner. Another repository calls it as `tannergolden/standards/.github/actions/template-sync@v1`, and this repository's own self-checks as `./.github/actions/template-sync`. It ships [`.github/scripts/template-sync.py`](../../scripts/template-sync.py), found beside it at `$GITHUB_ACTION_PATH`. Its inputs and outputs are documented in `action.yml` itself.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                      | Purpose                                                                                                                      |
| :------------------------- | :--------------------------------------------------------------------------------------------------------------------------- |
| [`action.yml`](action.yml) | Syncs a generated repository's scaffold from its template, checks a template's sync list, or tracks what waits on the owner. |
| [`README.md`](README.md)   | This file.                                                                                                                   |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**If it ships a file, it lives here.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the terms in [LICENSE](/LICENSE).

</div>
