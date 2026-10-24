<!--
title: '🚨 ESCALATE OR RESOLVE A CI FAILURE'
description: 'Opens an issue when a watched workflow fails and closes it when the workflow recovers.'
type: index
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 🚨 ESCALATE OR RESOLVE A CI FAILURE

<a name="top"></a>

**Escalate or Resolve a CI Failure, called with `uses:` at the step level.**

_One `uses:` line, one job done._

</div>

---

## 💡 What This Folder Is For

[`action.yml`](action.yml) is the `ci-failure-alert` composite action: opens an issue when a watched workflow fails and closes it when the workflow recovers. Another repository calls it as `tannergolden/standards/.github/actions/ci-failure-alert@v1`, and this repository's own self-checks as `./.github/actions/ci-failure-alert`. It ships [`.github/scripts/ci-failure-alert.sh`](../../scripts/ci-failure-alert.sh), found beside it at `$GITHUB_ACTION_PATH`. Its inputs and outputs are documented in `action.yml` itself.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                      | Purpose                                                                                |
| :------------------------- | :------------------------------------------------------------------------------------- |
| [`action.yml`](action.yml) | Opens an issue when a watched workflow fails and closes it when the workflow recovers. |
| [`README.md`](README.md)   | This file.                                                                             |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**If it ships a file, it lives here.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the terms in [LICENSE](/LICENSE).

</div>
