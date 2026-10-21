<!--
title: '🎉 INITIALISE FROM TEMPLATE'
description: 'Rewrites a generated repository''s identity to its new owner and deletes what only the template needs, once, then disables itself.'
type: index
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 🎉 INITIALISE FROM TEMPLATE

<a name="top"></a>

**Initialise From Template, called with `uses:` at the step level.**

_One `uses:` line, one job done._

</div>

---

## 💡 What This Folder Is For

[`action.yml`](action.yml) is the `init-template` composite action: rewrites a generated repository's identity to its new owner and deletes what only the template needs, once, then disables itself. Another repository calls it as `tannergolden/standards/.github/actions/init-template@v1`, and this repository's own self-checks as `./.github/actions/init-template`. It ships [`.github/scripts/init-template.py`](../../scripts/init-template.py), found beside it at `$GITHUB_ACTION_PATH`. Its inputs and outputs are documented in `action.yml` itself.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                      | Purpose                                                                                                                           |
| :------------------------- | :-------------------------------------------------------------------------------------------------------------------------------- |
| [`action.yml`](action.yml) | Rewrites a generated repository's identity to its new owner and deletes what only the template needs, once, then disables itself. |
| [`README.md`](README.md)   | This file.                                                                                                                        |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**If it ships a file, it lives here.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
