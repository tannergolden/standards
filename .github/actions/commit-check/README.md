<!--
title: '✍️ COMMIT MESSAGE CHECK'
description: 'Verifies every human-authored commit in a pull request follows Conventional Commits.'
type: index
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# ✍️ COMMIT MESSAGE CHECK

<a name="top"></a>

**Commit Message Check, called with `uses:` at the step level.**

_One `uses:` line, one job done._

</div>

---

## 💡 What This Folder Is For

[`action.yml`](action.yml) is the `commit-check` composite action: verifies every human-authored commit in a pull request follows Conventional Commits. Another repository calls it as `tannergolden/standards/.github/actions/commit-check@v1`, and this repository's own self-checks as `./.github/actions/commit-check`. It ships [`.github/scripts/commit-check.py`](../../scripts/commit-check.py), found beside it at `$GITHUB_ACTION_PATH`. Its inputs and outputs are documented in `action.yml` itself.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                      | Purpose                                                                              |
| :------------------------- | :----------------------------------------------------------------------------------- |
| [`action.yml`](action.yml) | Verifies every human-authored commit in a pull request follows Conventional Commits. |
| [`README.md`](README.md)   | This file.                                                                           |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**If it ships a file, it lives here.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the terms in [LICENSE](/LICENSE).

</div>
