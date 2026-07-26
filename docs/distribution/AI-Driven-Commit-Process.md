<!--
title: '🤖 AI-DRIVEN COMMIT PROCESS'
description: 'The protocol for generating Conventional Commits with AI assistance.'
tags: [commits, conventional-commits, ai, git]
category: docs
-->

<!-- markdownlint-disable MD041 -->
<div align="center">

# 🤖 AI-DRIVEN COMMIT PROCESS

<a name="top"></a>

**Optimizing the developer-AI feedback loop for atomic commits.**

_Human-approved. Machine-drafted. Standards-enforced._

</div>

---

## 🎯 Strategic Objective

- Produce **Conventional Commits** automatically while maintaining accuracy and intent.
- Keep commits **small and single-purpose**, with clear `type(scope): summary`.
- Encode **what/why/testing/impact** so release notes and audits are effortless.

---

<strong>🔧 Prerequisites</strong>

- **AI IDE** capable of processing the prompt below.
- **commitlint** with `@commitlint/config-conventional` configured.
- **Husky** (or equivalent) Git hooks enabled to run commitlint locally.
- CI validates the **PR title** as a Conventional Commit and runs tests (per-commit message linting is the optional hard gate described below).

> [!TIP]
> If you need to add tools: `npm i -D @commitlint/cli @commitlint/config-conventional husky lint-staged`.

---

### 🧱 Commit Anatomy (Conventional Commits)

The commit and pull request title should follow this format:

```text
<type>(<scope>): <subject>

<body>

<footers>
```

- **Type**: One of the following: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`, `security`.
- **Scope**: A short identifier for the area of the codebase being changed (e.g., `auth`, `api`, `ui`).
- **Subject**: A brief, descriptive summary of the change, written in lowercase (recommended). The subject may optionally begin with an emoji.
- **Body**: **REQUIRED, on every commit, without exception.** Separated from the subject by one blank line and wrapped at 72 characters. Write full sentences explaining **why** the change was made and why this way rather than the obvious alternative.
- **Punctuation**: Never use an em dash (U+2014) anywhere in a commit message, subject or body. Use a comma, a colon, parentheses, or a spaced hyphen instead. commitlint rejects the character mechanically (the commitlint rule set in `config/commitlint.config.js` encodes it).

#### The Body Is Not Optional

A subject-only commit is not a smaller commit. It is an undocumented one.

The diff already records **what** changed, in more detail and more reliably
than any prose could. Nothing except the body records **why**, and the
reasoning is the only part that cannot be recovered later by reading the
code. A commit that omits it has thrown away the one thing it was uniquely
able to preserve.

This binds every commit that lands in a repository on these standards:

| Commit | Body required |
| :--- | :--- |
| Ordinary human-authored work | Yes |
| The initial commit written at repository generation | Yes, and `scripts/init-template.py` writes one |
| Automated maintenance commits (formatting, licence year, dependency bumps) | Yes, from the workflow that opens them |
| A squash merge | Yes. The pull request body becomes it, so write that body |
| A revert | Yes. State what broke, not only what is being undone |

The only commits exempt are ones no person authored and no person can edit:
merge commits GitHub generates for a merge-queue entry or a web-UI merge.

Where a change is genuinely self-evident, the body still has work to do:
say what you considered and rejected, or what it deliberately does **not**
do. "Obvious" is a property of the author on the day they wrote it, never of
the reader six months later.

#### Emoji Guidelines

While not strictly enforced, we encourage the use of emojis to visually represent the type of change. Here is a recommended mapping:

- `feat`: ✨ / 🆕 / 🚀
- `fix`: 🐛 / 🩹 / 🔧
- `docs`: 📝 / 📚 / 📖
- `style`: 🎨 / 💄 / 🧼
- `refactor`: ♻️ / 🧩 / 🪚
- `perf`: ⚡️ / 🏎️ / 📈
- `test`: 🧪 / 🔬 / 🧫
- `build`: 🏗️ / 🧱 / 📦
- `ci`: 🤖 / ⚙️ / 🕒
- `chore`: 🧹 / 🗂️ / 🪛
- `revert`: ⏪ / 🔙 / ↩️
- `security`: 🔒 / 🛡️ / 🚨

---

### 🧭 When to Commit (and how big)

- **One intent per commit.** Split feature work from refactors or formatting.
- **Green locally first** (`npm run lint && npm test`) so CI won’t fail on style/tests.
- Prefer several **small commits** over a single “kitchen-sink” commit.

---

### 💙 AI IDE: How to Use (Step-by-Step)

1. **Stage changes** you want in the commit: `git add -A` (or stage selectively in VS Code).
2. **Prompt your AI IDE**: Provide the **AI Commit Prompt** below along with your changes.
3. **Provide context** (or let it infer from diffs):
   - What changed and why (ticket/reason)
   - Tests/validation performed
   - Any breaking changes or migrations
4. The AI proposes a **Conventional Commit** (type/scope/summary + body).
5. **Review carefully**, edit for accuracy, and apply.
6. Commit **signed off**: `git commit -s` - the DCO `Signed-off-by:` trailer is mandatory on every human-authored commit, and the required **✍️ DCO Sign-Off** check blocks the merge without it (forgot? `git commit --amend -s --no-edit`, or `git rebase --signoff @{upstream}` for a whole branch).
7. **Push**: `git push -u origin HEAD`.
8. Open a **Pull Request (PR)** into `Development`.

> [!NOTE]
> **The rulesets have your back, not a local hook.** Nothing here installs a git hook, so this protocol is enforced where it cannot be bypassed: the branch rulesets refuse a direct push to a protected branch, and `semantic-pr.yml` re-checks every commit message and sign-off on the pull request itself. A local hook you can disable with `--no-verify` is a convenience, not a control.

> [!CAUTION]
> Treat AI prompts as public text. **Never** include production secrets, PII, or internal proprietary tokens in your generation prompts.

---

### 📋 AI Commit Prompt (copy/paste)

Copy the block below into your AI assistant (Cursor, Antigravity, etc.) to generate compliant commits every time.

```txt
ROLE: Conventional Commit Generator
STYLE: Include exactly one emoji after the colon (house convention -
validators treat the emoji as optional). Use present-tense.
PUNCTUATION: Never use an em dash; use ", ", ": ", or " - " instead.
STRUCTURE: <type>(<scope>): <emoji> <subject>

Paragraph 1: 2-4 sentences explaining what, why, and the impact.
The <thing> includes:
- Bulleted list of key technical edits (max 6).

TYPES: feat, fix, docs, style, refactor, perf, test, build, ci,
chore, revert, security.
RECENCY: Scan DIFF bottom -> top. Prefer code over docs.
```

---

### 🧩 Smart Defaults (mapping branch → type)

| Branch prefix  | Likely `type`              | Example summary                                   |
| -------------- | -------------------------- | ------------------------------------------------- |
| `feat/*`       | `feat`                     | `feat(auth): ✨ add passwordless sign-in`         |
| `bugfix/*`     | `fix`                      | `fix(payments): 🐛 handle webhook retries`        |
| `hotfix/*`     | `fix!` (breaking) or `fix` | `fix!(api): 🐛 sanitize headers to prevent crash` |
| `docs/*`       | `docs`                     | `docs(readme): 📝 add setup instructions`         |
| `experiment/*` | `feat` or `refactor`       | `refactor(search): ♻️ spike on vector index`      |
| `chore/*`      | `chore` or `refactor`      | `chore(repo): 🔧 align tsconfig across packages`  |

> [!TIP]
> The AI can infer type/scope from diffs and branch names - **you** make the final call.

---

### ✅ Good vs. Bad Examples

#### Good Example

```text
feat(auth): ✨ add passwordless sign-in via magic links

Motivation: Reduce login friction for mobile-first users. This change introduces
secure, token-masked email links that bypass traditional password entry. Users
experience a safer, faster authentication flow compatible with existing MFA.

The sign-in feature includes:
- Secure token issuance and validation logic.
- Email delivery integration via SendGrid.
- Automated expiry enforcement (15 minutes).
- Integration tests for happy and failure paths.
```

#### Bad Example

```text
fix(auth): 🐛 fix login bug
```

Two failures, and the missing body is the worse one. "fix login bug" restates
the type and the scope without adding anything, and the reader is left with a
diff and no account of which bug, how it presented, or why this fix rather
than another. Nothing here survives the moment its author forgets it.

```text
fix(auth): 🐛 accept sign-in tokens issued seconds before a clock skew

Tokens carry an issued-at stamp checked against the server clock. A user
whose device ran marginally ahead produced a token dated in the future,
which the validator rejected as not yet valid, so sign-in failed on
correct credentials and reported nothing useful.

Allows sixty seconds of forward skew rather than syncing clocks, because
the client's clock is not ours to fix and the exposure is bounded by the
same expiry that already applies.
```

---

### 🔗 Commitlint & CI Integration

- **CI, per pull request**: `semantic-pr.yml` validates the **PR title**. On a squash merge the title becomes the commit that lands, so this is the gate on what reaches the default branch.
- **CI, per commit**: the same workflow's `✍️ Commit Messages` job validates **every human-authored commit** in the pull request. This is what covers a repository that merges or rebases instead of squashing, where each message lands on the default branch in its own right. Bot-authored and merge commits are exempt, matching the DCO check exactly.
- **Local, optional**: `config/commitlint.config.js` encodes the same rules for anyone running commitlint in a Node toolchain. It is not required, and nothing in CI depends on it - the CI gate reads commits through the GitHub API instead, because the workflow runs on `pull_request_target` and installing packages from the pull request's own manifest would hand an elevated token to whoever opened it.
- **Changelogs**: `release-notes.yml` parses the resulting history with git-cliff to draft notes automatically.

> [!IMPORTANT]
> **One rule set, two encodings.** The CI gate (`scripts/commit-check.py`) and the local commitlint config express the same standard. Changing one without the other produces a rule nobody enforces, or a gate nothing documents.

**The shipped config** (`config/commitlint.config.js`, excerpt - the full type list lives in the file):

```js
export default {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [2, 'always', ['feat', 'fix', 'docs' /* …9 more */]],
    'subject-empty': [2, 'never'],
    'type-empty': [2, 'never'],
  },
};
```

Every commit on a pull request is already linted by the `✍️ Commit Messages` job described above - no extra step is needed, and none should be added to `ci.yml`, which runs on `pull_request` rather than `pull_request_target` and would duplicate the gate under weaker conditions.

---

### 🧪 Testing Hooks (preflight)

Add to `package.json` (example):

```jsonc
{
  "scripts": {
    "precommit": "lint-staged",
    "test:ci": "vitest run",
    "lint": "eslint .",
  },
  "lint-staged": {
    "*.{ts,tsx,js,jsx}": ["eslint --fix", "vitest related --run"],
  },
}
```

> [!NOTE]
> Keep local commands and CI identical: `npm ci` → `npm run lint` → `npm test -- --ci` → `npm run build`.

---

### 🧰 DOs & DON’Ts

#### DO

- Keep the **summary** imperative/present: “add”, “fix”, “remove” / “Adds…”.
- Write the **why** in the body. It is required, not encouraged; see above.
- Mark **BREAKING CHANGE** explicitly in footers.

#### DON’T

- Don’t paste raw diff lines or secrets into prompts or bodies.
- Don’t combine unrelated changes into one commit.
- Don’t ship a subject-only commit, however small the change looks.
- Don’t rely on AI output without reading it.
- Don’t use em dashes anywhere in the message: commitlint rejects them.

---

### 🆘 Troubleshooting

| Symptom                        | Likely Cause              | Fix                                                                                                    |
| ------------------------------ | ------------------------- | ------------------------------------------------------------------------------------------------------ |
| Commitlint fails on PR         | Wrong `type`/format       | Adjust to `type(scope): summary`; see config.                                                          |
| “Message too long” or noisy    | AI added excess detail    | Keep subject ≤72 chars; move detail into body; enforce 2–4 sentences in paragraph.                     |
| Wrong `type` suggested         | Branch/diff misleading    | Override manually; `feat` vs `fix` is your call.                                                       |
| Missing breaking change notice | Prompt lacked impact info | Add `BREAKING CHANGE:` footer with details.                                                            |
| Hook didn’t run                | Husky not set up          | Ensure `.husky/commit-msg` calls commitlint; run `npm run prepare` if needed.                          |
| Incorrect AI Naming            | LLM drifted from rules    | Ask your AI Assistant to "fix the naming and follow the official AI Driven Commit Process guidelines". |

---

### 🔗 See also

> [!TIP]
> Every canonical guide is indexed in the [&#x1F4DA; Standards Index](https://github.com/tannergolden/standards/blob/Development/docs/README.md). If you rename or move a file, update every reference to it across the repository to prevent link drift.

---

<div align="center">

**Committing with intent. Automating for clarity.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by the Engineering Team. Distributed under the MIT License.

</div>
