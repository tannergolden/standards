<!--
title: '✍️ DCO SIGN-OFF CHECK'
description: 'Verifies the Signed-off-by trailer on every human-authored commit in a pull request.'
type: index
keywords: [github-actions, composite-action]
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# ✍️ DCO SIGN-OFF CHECK

<a name="top"></a>

**DCO Sign-Off Check, called with `uses:` at the step level.**

_One `uses:` line, one job done._

</div>

---

## 💡 What This Folder Is For

[`action.yml`](action.yml) is the `dco-check` composite action: verifies the Signed-off-by trailer on every human-authored commit in a pull request. Another repository calls it as `tannergolden/standards/.github/actions/dco-check@v1`, and this repository's own self-checks as `./.github/actions/dco-check`. It ships [`.github/scripts/dco-check.sh`](../../scripts/dco-check.sh), found beside it at `$GITHUB_ACTION_PATH`. Its inputs and outputs are documented in `action.yml` itself.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                      | Purpose                                                                              |
| :------------------------- | :----------------------------------------------------------------------------------- |
| [`action.yml`](action.yml) | Verifies the Signed-off-by trailer on every human-authored commit in a pull request. |
| [`README.md`](README.md)   | This file.                                                                           |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**If it ships a file, it lives here.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
