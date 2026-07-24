<!--
title: '📝 GIT COMMANDS'
description: 'Copy-paste Git commands for the branching, syncing, and release flows used here.'
tags: [git, commands, reference, cli]
category: docs
-->

<!-- markdownlint-disable MD041 -->
<div align="center">

# 📝 GIT COMMANDS

<a name="top"></a>

**A high-signal, copy-paste guide for everyday workflows within these standards ecosystem.**

_Linear history. Conventional commits. Automated validation._

</div>

---

## 🎯 Our Strategic Workflow

We utilize an **Experimental → Development → Preview → Release** promotion path. All contributions flow through Pull Requests (PRs) and are validated by Continuous Integration (CI) before merging.

- **Squash & Merge**: We keep the timeline clean by squashing feature commits into a single, high-signal entry.
- **Convention First**: Every commit must follow the [&#x1F916; AI-Driven Commit Process](../distribution/AI-Driven-Commit-Process.md).
- **Signed Off, Always**: Every human commit carries the DCO trailer (`git commit -s`) - the required `✍️ DCO Sign-Off` check blocks merges without it.
- **Protected Pipelines**: Direct pushes to our primary branches are prohibited.

---

## 🧭 Initial Orientation

Setting up your workspace to match repository standards.

```bash
# Global configuration for repository alignment
git config --global init.defaultBranch Development
git config --global pull.ff only
git config --global fetch.prune true

# Synchronize local state with remote truth
git fetch --all --prune
git switch Development
git pull --ff-only
```

---

## 🔏 Verified Commit Identity (Signing)

We strongly recommend GPG or SSH signing for all commits - it adds the "Verified" badge on GitHub and makes authorship auditable. The shipped rulesets do not enforce it (so solo and automation flows never stall); teams can flip on **Require signed commits** in the branch rulesets once every contributor has a key configured.

### 1. Local Configuration (SSH Recommended)

SSH signing is the modern, simpler alternative to GPG.

```bash
# 1. Instruct Git to use SSH for signing
git config --global commit.gpgsign true
git config --global gpg.format ssh

# 2. Point to your SSH public key
# Replace path with your actual key (e.g., ~/.ssh/id_ed25519.pub)
git config --global user.signingkey /path/to/your/key.pub
```

### 2. GitHub GUI Signing

Ensure your GitHub account is configured to sign commits made via the web interface.

1.  Go to **Settings** > **SSH and GPG keys**.
2.  Check **Sign commits with my SSH keys** (or GPG).
3.  Under **Commit signing**, ensure your key is added and verified.

---

## 🔄 The Contributor's Daily Loop

Small, reviewable changes starting from the `Development` line.

| Step          | Action                               | Logic                                                                                 |
| :------------ | :----------------------------------- | :------------------------------------------------------------------------------------ |
| **1. Sync**   | `git switch Development && git pull` | Start from the latest integration state.                                              |
| **2. Branch** | `git switch -c feat/your-slug`       | Create an isolated topic branch (`<type>/<topic>` - the branch-name gate checks it).  |
| **3. Stage**  | `git add -p`                         | Review every line before staging (interactive).                                       |
| **4. Commit** | `git commit -s`                      | Apply [Conventional Commits](https://www.conventionalcommits.org/), signed off (DCO). |
| **5. Verify** | `make lint && make test`             | See what CI will see before CI sees it.                                               |
| **6. Push**   | `git push -u origin HEAD`            | Deliver to GitHub for review and validation.                                          |

---

## 🏗️ Commit Anatomy

Standardized messaging for automated releases and notes.

```txt
<type>(<scope>): <emoji> <short-subject>

[Optional Body Paragraph]

[Optional Footer / Ticket Reference]
```

> **Types**: `feat` ✨ | `fix` 🐛 | `docs` 📝 | `style` 🎨 | `refactor` ♻️ | `perf` ⚡️ | `test` 🧪 | `chore` 🧹 | `build` 📦 | `ci` ⚙️ | `revert` ⏪ | `security` 🔒

---

## ✍️ DCO Sign-Off (Required)

The `Signed-off-by:` trailer is a required merge gate on every human-authored commit. `git commit -s` adds it automatically; these are the repairs when one is missing:

```bash
# Forgot -s on the last commit? Amend it in place:
git commit --amend -s --no-edit

# A whole branch of unsigned commits? Sign them all, then update the PR:
git rebase --signoff @{upstream}
git push --force-with-lease

# Make -s automatic per repository (never think about it again):
git config alias.cs "commit -s"
```

---

## 🚑 Emergency: The Hotfix Path

Addressing production incidents directly from the `Release` branch.

```bash
# Branch from the production baseline
git fetch origin
git switch -c hotfix/ticket-123 origin/Release

# Apply fix, verify, and deliver (signed off - the DCO gate applies here too)
git commit -s -m "fix(api): 🩹 resolve critical cache leak"
git push -u origin HEAD

# POST-MERGE: Always back-merge Release -> Development
```

---

## 🔧 Maintenance & Repair

Keeping your branch synchronized and your history clean.

- **Rebase on Base**: `git fetch origin && git rebase origin/Development`
- **Squash (last 3)**: `git rebase -i HEAD~3`
- **Oops (Undo Commit)**: `git reset --soft HEAD~1` (keeps changes staged)
- **Hard Reset**: `git reset --hard origin/Development` (Destructive! wipes local changes)
- **Lost a commit?**: `git reflog` lists every recent HEAD position - `git switch -c rescue <sha>` recovers it.

---

## 🔃 There Is No Sync Branch To Review

Updates to the shared standards do not arrive as a pull request, because nothing
is copied into your repository to update. Your workflows call
`tannergolden/standards@v1`, and moving that tag is the delivery mechanism -
the next run simply uses the new logic.

What that leaves you to review is a **major** version, which never arrives on
its own: `standards-version.yml` opens one issue when `v2` is published and
changes nothing. To see what a version did before adopting it:

```bash
gh release view v2 --repo tannergolden/standards
git diff v1..v2 --stat   # inside a clone of the standards repository
```

### 🔗 See also

> [!TIP]
> Every canonical guide is indexed in the [&#x1F4DA; Standards Index](https://github.com/tannergolden/standards/blob/Development/docs/README.md). If you rename or move a file, update every reference to it across the repository to prevent link drift.

---

<div align="center">

**Master the command. Control the flow.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by the Engineering Team. Distributed under the MIT License.

</div>
