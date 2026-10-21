<!--
title: '🐍 SCRIPTS'
description: 'The helpers the composite actions ship and invoke, and the generators make lint-docs runs; each one says what it does in its docstring or leading comment.'
type: index
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 🐍 SCRIPTS

<a name="top"></a>

**The code behind the actions and the generators.**

_Standard library only, so they run on a bare runner._

</div>

---

## 💡 What This Folder Is For

An action finds its script beside it, at `$GITHUB_ACTION_PATH/../../scripts/`, so a script here ships with every release of these standards. The generators (`update-doc-indexes.py`, `update-label-docs.py`, `check-type-parity.py` and `check-frontmatter.py`) are what `make lint-docs` runs, and [`tests/`](../../tests/README.md) holds the suite over all of them.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                                                      | Purpose                                                                                                                                                                                       |
| :--------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`apply-rulesets.sh`](apply-rulesets.sh)                   | Apply Rulesets - declarative branch and tag protection via the GitHub API                                                                                                                     |
| [`apply-settings.py`](apply-settings.py)                   | Apply Repository Settings - the settings half of "set up to standard"                                                                                                                         |
| [`check-frontmatter.py`](check-frontmatter.py)             | Frontmatter Check - every document says what it is before it is opened                                                                                                                        |
| [`check-standards-version.py`](check-standards-version.py) | Standards Version Check - the one gap a moving major tag leaves open                                                                                                                          |
| [`check-type-parity.py`](check-type-parity.py)             | Assert the Conventional Commit type list is the same in all five places.                                                                                                                      |
| [`ci-failure-alert.sh`](ci-failure-alert.sh)               | CI Failure Alert - mechanical failure escalation                                                                                                                                              |
| [`commit-check.py`](commit-check.py)                       | Commit Message Check - Conventional Commits, enforced per commit                                                                                                                              |
| [`dco-check.sh`](dco-check.sh)                             | DCO Sign-Off Check - mechanical enforcement of the Developer Certificate of Origin contract (https://developercertificate.org), which a repository normally documents in its CONTRIBUTING.md. |
| [`generate-sbom.sh`](generate-sbom.sh)                     | Generate SBOM - a dependency inventory for any ecosystem                                                                                                                                      |
| [`init-template.py`](init-template.py)                     | Initialise From Template - make a generated repository belong to its owner                                                                                                                    |
| [`machined-blocks.py`](machined-blocks.py)                 | Machined Block Check - a block marked with its own hash still matches it                                                                                                                      |
| [`open-pr.sh`](open-pr.sh)                                 | Open-PR - PR-only delivery for automated maintenance changes                                                                                                                                  |
| [`prune-deployments.py`](prune-deployments.py)             | Prune stale and superseded GitHub deployments.                                                                                                                                                |
| [`prune-workflow-runs.py`](prune-workflow-runs.py)         | Prune the Actions run history, keeping only the most recent run(s) per workflow.                                                                                                              |
| [`README.md`](README.md)                                   | This file.                                                                                                                                                                                    |
| [`sync-labels.sh`](sync-labels.sh)                         | Sync Labels - declarative label delivery via the GitHub API                                                                                                                                   |
| [`template-sync.py`](template-sync.py)                     | Template Sync - bring a generated repository's scaffold up to date, on request                                                                                                                |
| [`update-doc-indexes.py`](update-doc-indexes.py)           | Machined documentation indexes - generated, never hand-maintained.                                                                                                                            |
| [`update-label-docs.py`](update-label-docs.py)             | Regenerate the label reference tables from the taxonomy.                                                                                                                                      |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**Each one does one job, and says which.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
