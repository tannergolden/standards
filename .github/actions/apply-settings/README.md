<!--
title: '⚙️ APPLY REPOSITORY SETTINGS'
description: 'Brings a repository''s settings in line with the published set, comparing before it writes.'
type: index
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

On a public repository it also writes one Actions event policy, under **Settings → Actions → Policies**: the one that keeps `pull_request_target` for `.github/workflows/governance.yml`, which GitHub's default policy blocks in a public repository, from 2 December 2026 at the latest, unless a policy allows it. The run lists the repository's policies, finds this one by its name and reads it, then creates it when it is absent, updates it in place when its enforcement, workflow paths or allowed events have drifted, and leaves it alone when it matches. A dry run shows that plan, a private repository skips it with a notice, and an endpoint that answers `403` or `404` is skipped as unavailable. [Repository Settings](../../../docs/operations/Repository-Settings.md#the-governance-stubs-event-policy) says why, and why its list of events is the whole of what the stub uses.

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
