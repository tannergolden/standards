<!--
title: '🧪 TESTS'
description: 'The pytest suite over the scripts, the workflows'' shell and the actions, run by make test and 🚦 Self Checks.'
type: index
keywords: [pytest, testing]
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 🧪 TESTS

<a name="top"></a>

**The suite over everything that ships.**

_Every script, every shell block._

</div>

---

## 💡 What This Folder Is For

`python3 -m pytest` runs every file here (see [`pytest.ini`](../pytest.ini)): the scripts in [`.github/scripts/`](../.github/scripts/README.md), the shell inside the workflows and the actions, and the contracts the documents promise. [`conftest.py`](conftest.py) holds the shared fixtures.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                                                                              | Purpose                                                                                       |
| :--------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------- |
| [`accepted-risk-rationale.py`](accepted-risk-rationale.py)                         | An accepted security finding is only accepted while its reason is true.                       |
| [`apply-settings-groups.py`](apply-settings-groups.py)                             | Every setting is compared before it is written, and a skip says why.                          |
| [`apply-settings-validation.py`](apply-settings-validation.py)                     | A settings file that yields nothing, or names what it cannot, must fail.                      |
| [`apply-standards-dry-run.py`](apply-standards-dry-run.py)                         | A dry run must be visible in every job that performs one.                                     |
| [`auto-format-preconditions.py`](auto-format-preconditions.py)                     | Auto-format must skip when it cannot run, not fail.                                           |
| [`ci-failure-alert-scope.py`](ci-failure-alert-scope.py)                           | The escalator must only escalate runs from the repository it guards.                          |
| [`ci-failure-conclusions.py`](ci-failure-conclusions.py)                           | The escalator must react to every conclusion that means "broken".                             |
| [`ci-stage-resolution.py`](ci-stage-resolution.py)                                 | The primary required check must never report green having run nothing.                        |
| [`cliff-config.py`](cliff-config.py)                                               | The changelog config must use keys git-cliff actually reads.                                  |
| [`commit-identity.py`](commit-identity.py)                                         | Who a commit is by: never an AI, and signed off by its author.                                |
| [`commit-rule-parity.py`](commit-rule-parity.py)                                   | The local commitlint config must reject what the CI gate rejects.                             |
| [`commit-type-parity.py`](commit-type-parity.py)                                   | The Conventional Commit type list is encoded five times, not three.                           |
| [`conftest.py`](conftest.py)                                                       | Shared fixtures for the standards test suite.                                                 |
| [`container-tagging.py`](container-tagging.py)                                     | `latest` must never follow a prerelease, whatever fired the run.                              |
| [`dco-truncation.py`](dco-truncation.py)                                           | A required gate must not pass because it only saw part of the evidence.                       |
| [`doc-index-gate.py`](doc-index-gate.py)                                           | A check that inspected zero files must not report success.                                    |
| [`documentation-inventories.py`](documentation-inventories.py)                     | An inventory that claims to be complete must be complete.                                     |
| [`documented-commands-exist.py`](documented-commands-exist.py)                     | Every `make` command a script here tells someone to run must exist.                           |
| [`draft-prune-scope.py`](draft-prune-scope.py)                                     | The draft prune must only delete drafts this workflow created.                                |
| [`frontmatter-check.py`](frontmatter-check.py)                                     | Every document says what it is before it is opened.                                           |
| [`generated-docs-are-formatter-stable.py`](generated-docs-are-formatter-stable.py) | A generator and the formatter must not fight over the same file.                              |
| [`generators-are-gated.py`](generators-are-gated.py)                               | The generated documents must be checked by something that runs.                               |
| [`harness.py`](harness.py)                                                         | Tests for the test harness itself.                                                            |
| [`init-template-concurrency.py`](init-template-concurrency.py)                     | A workflow that force-pushes a rewritten tree must not race itself.                           |
| [`init-template-removal.py`](init-template-removal.py)                             | What only the template needs never reaches a generated repository, bar a workflow.            |
| [`init-template-shape.py`](init-template-shape.py)                                 | The initial commit describes the template a repository came from, read from its tree.         |
| [`init-template-substitution.py`](init-template-substitution.py)                   | The identity substitutions, which shipped without a gate.                                     |
| [`issue-ops-authorization.py`](issue-ops-authorization.py)                         | Slash commands need a relationship to the repository, not just a slash.                       |
| [`java-selection.py`](java-selection.py)                                           | A non-integer java-version must fall back, not crash the step.                                |
| [`label-registry-parsing.py`](label-registry-parsing.py)                           | The label registry is YAML, so both quoting styles must parse.                                |
| [`label-validation-is-single.py`](label-validation-is-single.py)                   | One validator for the label taxonomy, not two that disagree.                                  |
| [`link-check-summary.py`](link-check-summary.py)                                   | The link-check summary step must read the file the action writes.                             |
| [`machined-blocks.py`](machined-blocks.py)                                         | A block marked with its own hash must still match it.                                         |
| [`machined-folder-logs.py`](machined-folder-logs.py)                               | A folder log is generated from the folder, or it is a list that drifts.                       |
| [`make-setup-probe.py`](make-setup-probe.py)                                       | `make setup` is optional everywhere, so nowhere may assume it exists.                         |
| [`make-target-probes.py`](make-target-probes.py)                                   | Every `make` target probe finds a target that is there, under the shell Actions runs it with. |
| [`npm-publish-probe.py`](npm-publish-probe.py)                                     | The already-published probe must read the registry as the publisher.                          |
| [`prune-deployment-scope.py`](prune-deployment-scope.py)                           | An empty environment name must not widen a destructive prune.                                 |
| [`prune-run-defaults.py`](prune-run-defaults.py)                                   | Two wrappers around one destructive action must not disagree on safety.                       |
| [`README.md`](README.md)                                                           | This file.                                                                                    |
| [`release-callable.py`](release-callable.py)                                       | Cut Release is callable, and a call gets the same guards a dispatch does.                     |
| [`release-guard.py`](release-guard.py)                                             | Cut Release must refuse a commit that is not on the release line.                             |
| [`release-notes-errors.py`](release-notes-errors.py)                               | A hand-written error message must be reachable.                                               |
| [`release-tag-contract.py`](release-tag-contract.py)                               | A repository consumed by tag carries two tags, and four files must agree.                     |
| [`ruleset-preflight.py`](ruleset-preflight.py)                                     | An unreadable workflow directory is a token problem, and must say so.                         |
| [`schedule-documentation.py`](schedule-documentation.py)                           | The schedule page states two rules the repository itself breaks.                              |
| [`script-error-messages.py`](script-error-messages.py)                             | A script must name the problem, not print a Python traceback.                                 |
| [`small-correctness.py`](small-correctness.py)                                     | Three narrow defects, each one an unknown being read as a benign answer.                      |
| [`stub-delivery-docs.py`](stub-delivery-docs.py)                                   | Only one mechanism installs trigger stubs, and the docs must name it.                         |
| [`template-identity-rewrite.py`](template-identity-rewrite.py)                     | Dotfiles are not suffixes, so three entries could never match.                                |
| [`template-sync-decisions.py`](template-sync-decisions.py)                         | Every decision the planner can make, for every situation it can be in.                        |
| [`template-sync-edges.py`](template-sync-edges.py)                                 | The edges review and real use of template sync found, each pinned where it was found.         |
| [`template-sync-list.py`](template-sync-list.py)                                   | The list an owner edits, and git's matcher reading it.                                        |
| [`template-sync-lock.py`](template-sync-lock.py)                                   | The lock is read strictly, and written the same way every time.                               |
| [`template-sync-mapping.py`](template-sync-mapping.py)                             | Template sync through a mapping, for a repository DEFINED as a delta of its template.         |
| [`template-sync-properties.py`](template-sync-properties.py)                       | Template sync under random histories, and the broken designs it rejects.                      |
| [`template-sync-run.py`](template-sync-run.py)                                     | Template sync, end to end, on real repositories.                                              |
| [`template-sync-workflow.py`](template-sync-workflow.py)                           | The workflow, the action and init: the shell around the engine, as shipped.                   |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**Tested here, before a consumer finds it.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
