<!--
title: '📄 PROVIDE SHARED CONFIG'
description: 'Resolves a shared configuration file to a path, honoring a calling repository override.'
type: index
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 📄 PROVIDE SHARED CONFIG

<a name="top"></a>

**Provide Shared Config, called with `uses:` at the step level.**

_One `uses:` line, one job done._

</div>

---

## 💡 What This Folder Is For

[`action.yml`](action.yml) is the `config` composite action: resolves a shared configuration file to a path, honoring a calling repository override. Another repository calls it as `tannergolden/standards/.github/actions/config@v1`, and this repository's own self-checks as `./.github/actions/config`. It ships [`config`](../../../config), found beside it at `$GITHUB_ACTION_PATH`. Its inputs and outputs are documented in `action.yml` itself.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                      | Purpose                                                                                 |
| :------------------------- | :-------------------------------------------------------------------------------------- |
| [`action.yml`](action.yml) | Resolves a shared configuration file to a path, honoring a calling repository override. |
| [`README.md`](README.md)   | This file.                                                                              |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**If it ships a file, it lives here.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the terms in [LICENSE](/LICENSE).

</div>
