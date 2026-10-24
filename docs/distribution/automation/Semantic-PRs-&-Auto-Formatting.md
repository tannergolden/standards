<!--
title: '✨ SEMANTIC PRS & AUTO-FORMATTING'
description: 'Pull-request title enforcement and automatic formatting workflows.'
type: guide
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

- **Workflow**: `.github/workflows/semantic-pr.yml` (the `title` job)
- **Pattern**: `type(scope): description` (e.g., `feat(auth): add login support`)
- **Branch naming**: a companion `branch-name` job in the same workflow enforces `<type>/<topic>` on the PR's source branch (18 accepted prefixes, set by the workflow's `branch-prefixes` input, plus the `agent-prefixes` compatibility list).
- **DCO sign-off**: a companion `dco` job verifies the `Signed-off-by:` trailer mandated by CONTRIBUTING on every human-authored commit. Exemptions are per **commit**, never per PR: bot-authored commits and merge commits pass individually while the job still runs on every PR, so a person's commit on a bot's branch is still checked. The check reads commits through the API and never executes PR code, and it **fails closed**: `gh api` is the primary client with a retrying direct-HTTPS fallback, and if both clients fail the gate fails rather than passing blind.
- **Impact**: Blocks the "Merge" button if the title, the branch name, or a missing sign-off is non-compliant.

### 2. Auto-Formatter

Monitors the codebase for style drift and proposes corrections - without ever writing to a protected branch.

- **Workflow**: `.github/workflows/auto-format.yml` (Standalone for on-demand execution)
- **Execution**: Runs on each push to `Development` (drift can only appear when the branch changes - zero idle runs), or on demand via `workflow_dispatch`.
- **Remediation**: Runs Prettier repository-wide and, when drift exists, **opens a pull request** targeting `Development` (via the `open-pr` composite action). Long-lived branches are PR-only for automation exactly as they are for humans.
- **Layered defense**: where the `ci` job's lint includes a format check, such as a `make lint` that runs one, CI rejects unformatted changes, so drift only reaches the default branch when something bypassed that check, or when there was none. The hooks the golden path template ships check commit messages and secrets, not formatting, so a repository that wants drift caught before a commit wires a format hook of its own; this workflow is the safety net either way, and the only one that covers an edit made in the GitHub web editor.

---

## 🚀 Trigger Mechanism

| Workflow        | Event                                                                     | Outcome                                                                                        |
| :-------------- | :------------------------------------------------------------------------ | :--------------------------------------------------------------------------------------------- |
| **Semantic PR** | `pull_request` (opened, edited, synchronize, reopened), and `merge_group` | Passes/Fails the PR check; in a merge queue every check skips, which GitHub reports as passing |
| **Auto-Format** | `push` to `Development` / `workflow_dispatch`                             | Opens a PR with formatting fixes when drift exists.                                            |

> [!NOTE]
> **Why `pull_request`, and not `pull_request_target`.** Every job reads the pull request through the
> API and checks nothing out, so the read-only token a fork's pull request gets is all it needs. The
> write token of `pull_request_target` would go unused, and GitHub's default policy blocks that
> event in a public repository, from 2 December 2026 at the latest, unless a policy allows it.
> Under `pull_request` the stub runs as the pull request has it, so a fork can edit it: review a
> change to a workflow file before you approve its run, as for every other check. On a public
> repository an outside contributor's runs wait for that approval, so the check starts once it is
> given.

---

## ⚙️ Configuration Details

- **Semantic PR Lib**: Uses `amannn/action-semantic-pull-request`.
- **Formatting Engine**: Prettier, configured by the committed [`config/prettierrc.json`](../../../config/prettierrc.json) - the workflow hands it that file unless a repository names its own with `prettier-config`, and this repository's `make lint-format` checks against the same file, so both format identically.

---

## 🧯 Troubleshooting

If the Semantic PR check fails:

1. **Edit PR Title**: Click "Edit" on the PR page and update the title to follow Conventional Commits.
2. **Re-run**: The check will automatically re-run once the title is updated.

If an Auto-Formatting pull request appears:

1. **Review & Merge**: The PR contains only Prettier output; merge it through the normal gates once CI is green.
2. **Pending Checks**: If required checks are waiting, the PR was opened with the default `GITHUB_TOKEN`, and GitHub starts no checks on such a PR by itself. Approve the waiting runs from the PR, or configure a `BOT_ACCESS_TOKEN` secret so automation PRs run CI automatically.
3. **Local Linting**: Run `make lint` locally before pushing to ensure you are seeing what the CI sees.

### 🔗 See also

> [!TIP]
> Every canonical guide is indexed in the [&#x1F4DA; Standards Index](https://github.com/tannergolden/standards/blob/Development/docs/README.md). If you rename or move a file, update every reference to it across the repository to prevent link drift.

---

<div align="center">

**Traceable history. Standardized aesthetics.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by the Engineering Team. Distributed under the terms in [LICENSE](/LICENSE).

</div>
