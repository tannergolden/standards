<!--
title: '👋 CONTRIBUTOR ONBOARDING'
description: 'The automated welcome flow for first-time contributors.'
tags: [onboarding, automation, community, contributors]
category: docs
-->

<!-- markdownlint-disable MD041 -->
<div align="center">

# 👋 CONTRIBUTOR ONBOARDING

<a name="top"></a>

**Automating hospitality to accelerate contributor success.**

_Community Hospitality. Automated Mentorship. Frictionless Start._

</div>

---

## 🎯 Strategic Objective

The first interaction with a repository determines a contributor's long-term success. Our onboarding automation ensures that every new member feels welcomed, informed, and empowered to follow project standards.

- **Instant Feedback**: Provides immediate acknowledgement of new issues and PRs.
- **Guided Navigation**: Points contributors toward the Agent Guidelines and [Contributing Rules](https://github.com/tannergolden/.github/blob/Development/CONTRIBUTING.md).
- **Quality Insurance**: Offers a friendly "Quick Check" list to help contributors succeed on their first attempt.

---

## 🧭 Interaction Logic

The automation distinguishes between Issues and Pull Requests to provide contextual guidance:

### 1. The Issue Welcome

When a first-time reporter opens an issue, the bot:

- Expresses gratitude for the feedback.
- Encourages them to check existing documentation.
- Validates that a maintainer will review the report shortly.

### 2. The PR Welcome

When a first-time contributor opens a Pull Request, the bot:

- Celebrates the new contribution.
- Reminds the author of the **Conventional Commit PR title** contract and the base branch (`Development`).
- Flags the **DCO sign-off** (`git commit -s`) as a required check.
- Encourages a local `make lint && make test` run, and the Draft-until-CI-is-green habit.

---

## 🚀 Execution Mechanism

Orchestrated by `.github/workflows/governance.yml`:

- **Events**: Subscribes to `pull_request_target` (`opened`, `synchronize`, `reopened`) and `issues` (`opened`, `edited`); the welcome job itself gates on the `opened` action **plus a newcomer check** (author association `NONE`/`FIRST_TIME_CONTRIBUTOR`/`FIRST_TIMER`, never bots), so maintainers and automation are not greeted.
- **Logic Engine**: Powered by `actions/first-interaction`.
- **Permissions**: Requires `write` access to issues and pull requests to post comments.

---

## ⚙️ Configuration Details

| Trigger         | Custom Message                  | Target Documentation                                                                     |
| :-------------- | :------------------------------ | :--------------------------------------------------------------------------------------- |
| **First Issue** | Friendly thanks + context       | [Contributing](https://github.com/tannergolden/.github/blob/Development/CONTRIBUTING.md) |
| **First PR**    | Celebration + Quality Checklist | [Contributing](https://github.com/tannergolden/.github/blob/Development/CONTRIBUTING.md) |

---

## 🧯 Troubleshooting

If the welcome message fails to post:

1. **Permissions**: The `GITHUB_TOKEN` must have the `write` permission for both `issues` and `pull-requests`.
2. **Action Version**: Ensure the workflow is using `actions/first-interaction@v3` (the stable API).
3. **Forks**: The use of `pull_request_target` is deliberate - it allows the bot to post on PRs coming from external forks.

### 🔗 See also

> [!TIP]
> Every canonical guide is indexed in the [&#x1F4DA; Standards Index](https://github.com/tannergolden/standards/blob/Development/docs/README.md). If you rename or move a file, update every reference to it across the repository to prevent link drift.

---

<div align="center">

**Built for code. Scaled for community.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by the Engineering Team. Distributed under the MIT License.

</div>
