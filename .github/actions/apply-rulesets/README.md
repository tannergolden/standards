<!--
title: '🛡️ APPLY RULESETS'
description: 'Creates or updates the published branch and tag rulesets on a repository, matched by name.'
type: index
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 🛡️ APPLY RULESETS

<a name="top"></a>

**Apply Rulesets, called with `uses:` at the step level.**

_One `uses:` line, one job done._

</div>

---

## 💡 What This Folder Is For

[`action.yml`](action.yml) is the `apply-rulesets` composite action: creates or updates the published branch and tag rulesets on a repository, matched by name. Another repository calls it as `tannergolden/standards/.github/actions/apply-rulesets@v1`, and this repository's own self-checks as `./.github/actions/apply-rulesets`. It ships [`data/rulesets`](../../../data/rulesets), [`.github/scripts/apply-rulesets.sh`](../../scripts/apply-rulesets.sh), found beside it at `$GITHUB_ACTION_PATH`. Its inputs and outputs are documented in `action.yml` itself.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                      | Purpose                                                                                    |
| :------------------------- | :----------------------------------------------------------------------------------------- |
| [`action.yml`](action.yml) | Creates or updates the published branch and tag rulesets on a repository, matched by name. |
| [`README.md`](README.md)   | This file.                                                                                 |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**If it ships a file, it lives here.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the terms in [LICENSE](/LICENSE).

</div>
