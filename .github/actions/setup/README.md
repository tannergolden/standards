<!--
title: '🧰 SETUP TOOLCHAIN'
description: 'Makes the toolchains a repository uses available, detected from the manifests in its tree.'
type: index
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 🧰 SETUP TOOLCHAIN

<a name="top"></a>

**Setup Toolchain, called with `uses:` at the step level.**

_One `uses:` line, one job done._

</div>

---

## 💡 What This Folder Is For

[`action.yml`](action.yml) is the `setup` composite action: makes the toolchains a repository uses available, detected from the manifests in its tree. Another repository calls it as `tannergolden/standards/.github/actions/setup@v1`, and this repository's own self-checks as `./.github/actions/setup`. Its inputs and outputs are documented in `action.yml` itself.

A repository that keeps `.github/scripts/requirements.txt`, as the golden path template does for the scripts its own checks run, gets Python at the `python-version` input and that file installed with `python -m pip install --requirement`, right after Python is set up and whatever `install` says. In `ci.yml` that is before the setup command, lint, test and build, so a script such as the template's `validate-repository.py` imports what it names rather than whatever the runner image happens to carry.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                      | Purpose                                                                                    |
| :------------------------- | :----------------------------------------------------------------------------------------- |
| [`action.yml`](action.yml) | Makes the toolchains a repository uses available, detected from the manifests in its tree. |
| [`README.md`](README.md)   | This file.                                                                                 |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**If it ships a file, it lives here.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
