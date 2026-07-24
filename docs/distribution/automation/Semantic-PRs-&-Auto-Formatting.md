<!--
title: '✨ SEMANTIC PRS & AUTO-FORMATTING'
description: 'Pull-request title enforcement and automatic formatting workflows.'
tags: [semantic-pr, formatting, automation, conventional-commits]
category: docs
-->

<!-- markdownlint-disable MD041 -->
<div align="center">

# ✨ SEMANTIC PRS & AUTO-FORMATTING

<a name="top"></a>

**Enforcing semantic clarity and aesthetic consistency through invisible automation.**

_Conventional Commits. Automated Styling. Pull Request Integrity._

</div>

---

## 🎯 Strategic Objective

Maintaining a clean history and a consistent code style is difficult at scale without automation. These workflows act as invisible "Quality Guards" that allow developers to focus on logic while the infrastructure handles the semantics.

- **Traceable History**: Enforces [Conventional Commits](https://www.conventionalcommits.org/) for every Pull Request.
- **Consistent Aesthetics**: Automatically formats the tree to the project standard (Prettier, via the committed `config/prettierrc.json`).
- **Automated Remediation**: Fixes formatting issues automatically without requiring manual developer action.

---

## 🧭 Automation Components

This layer is composed of two primary workflows:

### 1. Semantic PR Gatekeeper

Ensures that the title of every Pull Request matches the conventional pattern required for automated changelog generation and versioning (em dashes are rejected outright - squash titles become commits, and the Output Rules ban the character) - and, in companion jobs, that the source branch follows the naming law and every human commit carries its DCO sign-off.

- **Workflow**: `.github/workflows/semantic-pr.yml` (Standalone for high visibility)
- **Pattern**: `type(scope): description` (e.g., `feat(auth): add login support`)
- **Branch naming**: a companion `branch-name` job in the same workflow enforces `<type>/<topic>` on the PR's source branch (19 accepted prefixes - see `AGENTS.md`).
- **DCO sign-off**: a companion `dco` job verifies the `Signed-off-by:` trailer mandated by CONTRIBUTING on every human-authored commit. Exemptions are per **commit**, never per PR: bot-authored commits and merge commits pass individually while the job still runs on every PR (a required check must never skip itself). The check reads commits through the API and never executes PR code, and it **fails closed**: `gh api` is the primary client with a retrying direct-HTTPS fallback, and if both clients fail the gate fails rather than passing blind.
- **Impact**: Blocks the "Merge" button if the title, the branch name, or a missing sign-off is non-compliant.

### 2. Auto-Formatter

Monitors the codebase for style drift and proposes corrections - without ever writing to a protected branch.

- **Workflow**: `.github/workflows/auto-format.yml` (Standalone for on-demand execution)
- **Execution**: Runs on each push to `Development` (drift can only appear when the branch changes - zero idle runs), or on demand via `workflow_dispatch`.
- **Remediation**: Runs Prettier repository-wide and, when drift exists, **opens a pull request** targeting `Development` (via `.github/scripts/open-fix-pr.sh`). Long-lived branches are PR-only for automation exactly as they are for humans.
- **Layered defense**: drift is rare by design - agent edits are formatted by the Claude Code hook, local commits by the husky pre-commit hook, and CI rejects unformatted changes via `make lint`. This workflow is the safety net for edits that bypass all three (e.g. the GitHub web editor).

---

## 🚀 Trigger Mechanism

| Workflow        | Event                                                                                     | Outcome                                             |
| :-------------- | :---------------------------------------------------------------------------------------- | :-------------------------------------------------- |
| **Semantic PR** | `pull_request_target` (opened, edited, synchronized) - so fork PRs can receive the status | Passes/Fails the PR check.                          |
| **Auto-Format** | `push` to `Development` / `workflow_dispatch`                                             | Opens a PR with formatting fixes when drift exists. |

---

## ⚙️ Configuration Details

- **Semantic PR Lib**: Uses `amannn/action-semantic-pull-request`.
- **Formatting Engine**: Prettier, configured by the committed [`config/prettierrc.json`](../../../config/prettierrc.json) - the workflow, the pre-commit hook, and `make lint` all invoke it with `--config config/prettierrc.json`, so every layer formats identically.

---

## 🧯 Troubleshooting

If the Semantic PR check fails:

1. **Edit PR Title**: Click "Edit" on the PR page and update the title to follow Conventional Commits.
2. **Re-run**: The check will automatically re-run once the title is updated.

If an Auto-Formatting pull request appears:

1. **Review & Merge**: The PR contains only Prettier output; merge it through the normal gates once CI is green.
2. **Pending Checks**: If required checks stay pending, the PR was opened with the default `GITHUB_TOKEN` (which cannot trigger workflows). Re-run checks manually, or configure a `BOT_ACCESS_TOKEN` secret so automation PRs run CI automatically.
3. **Local Linting**: Run `make lint` locally before pushing to ensure you are seeing what the CI sees.

### 🔗 See also

> [!TIP]
> Every canonical guide is indexed in the [&#x1F4DA; Standards Index](https://github.com/tannergolden/standards/blob/Development/docs/README.md). If you rename or move a file, update every reference to it across the repository to prevent link drift.

---

<div align="center">

**Traceable history. Standardized aesthetics.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by the Engineering Team. Distributed under the MIT License.

</div>
