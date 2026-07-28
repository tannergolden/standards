<!--
title: '🌿 CONVENTIONAL COMMITS'
description: 'The commit message standard every repository on these standards follows, including the two places it deliberately diverges from the specification.'
tags: [commits, conventional-commits, git, standards]
category: docs
-->

<!-- markdownlint-disable MD041 -->
<div align="center">

# 🌿 CONVENTIONAL COMMITS

<a name="top"></a>

**Atomic commits with a stated reason, in a format machines can read and humans can navigate.**

_The diff already records what changed. Only the author can record why._

</div>

---

## 🎯 Strategic Objective

- Produce **Conventional Commits** that carry intent, not just a file list.
- Keep commits **small and single-purpose**, with a clear `type(scope): subject`.
- Encode **what, why, testing and impact**, so release notes and audits are effortless.

Two rules below are **stricter than the Conventional Commits specification**, deliberately, and both are enforced mechanically: the scope is required, and the body is required. A third sits outside that specification altogether, because it governs **who** a commit is by rather than what it says, and it is a convention rather than a gate. Everything else follows the specification as written.

---

### 🧱 Commit Anatomy

```text
<type>(<scope>): <subject>

<body>

<footers>
```

- **Type**: one of `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`, `security`.
- **Scope**: a short identifier for the area changed (`auth`, `api`, `ui`). **REQUIRED, and enforced** by `scripts/commit-check.py`. The specification treats the scope as optional; this standard does not, because `docs: add the seed` repeated across a hundred commits answers "where?" nowhere, while `docs(templates): add the seed` makes the log navigable. Use the area actually touched: `workflows`, `scripts`, `docs`, `deps`, `readme`, `config`, `operations`.
- **Subject**: a brief summary in lowercase, imperative mood. It may begin with an emoji.
- **Body**: **REQUIRED, on every commit, without exception.** One blank line after the subject, wrapped at 72 characters. Full sentences explaining **why** this change, and why this way rather than the obvious alternative.
- **Author**: the repository owner, always. An AI agent that contributed is recorded as a co-author and never as the author. See [Who The Commit Is By](#-who-the-commit-is-by).
- **Punctuation**: never an em dash (U+2014), in a subject or a body. Use a comma, a colon, parentheses, or a spaced hyphen. The rule is mechanical, encoded in `config/commitlint.config.js`.

---

### 📏 The Body Is Not Optional

A subject-only commit is not a smaller commit. It is an undocumented one.

The diff already records **what** changed, in more detail and more reliably
than any prose could. Nothing except the body records **why**, and the
reasoning is the only part that cannot be recovered later by reading the
code. A commit that omits it has thrown away the one thing it was uniquely
able to preserve.

This binds every commit that lands in a repository on these standards:

| Commit                                                       | Body required                                             |
| :----------------------------------------------------------- | :-------------------------------------------------------- |
| Ordinary human-authored work                                 | Yes                                                       |
| The initial commit written at repository generation          | Yes, and `scripts/init-template.py` writes one            |
| Automated maintenance commits (formatting, dependency bumps) | Yes, from the workflow that opens them                    |
| A squash merge                                               | Yes. The pull request body becomes it, so write that body |
| A revert                                                     | Yes. State what broke, not only what is being undone      |

The only commits exempt are ones no person authored and no person can edit:
merge commits GitHub generates for a merge-queue entry or a web-UI merge.

Where a change is genuinely self-evident, the body still has work to do:
say what you considered and rejected, or what it deliberately does **not**
do. "Obvious" is a property of the author on the day they wrote it, never of
the reader six months later.

---

### ✍️ Who The Commit Is By

**The author is the repository owner. An AI agent that contributed is a co-author, never the author.**

| Field              | Who                                                    | Set by                                            |
| :----------------- | :----------------------------------------------------- | :------------------------------------------------ |
| Author             | The person the change belongs to                       | `user.name` and `user.email`, or `--author`       |
| `Co-Authored-By:`  | Every additional contributor, an AI agent included     | A trailer in the body, one line per contributor   |
| `Signed-off-by:`   | The person certifying the DCO                          | `git commit -s`                                   |

The trailer appears only when an agent actually contributed. A commit written by hand carries none, and adding one to look thorough is a false record in the one place a false record is permanent.

**Why the author field rather than only the trailer.** `git blame`, `git shortlog` and the contributor graph all read the author. An agent in that field puts a tool where a person should be, so the history reports that nobody owns the change and offers nobody to ask about it six months later. The sign-off says the same thing from the other direction: the DCO is a certification a person makes about work they are accountable for, and a process cannot make it. Nothing about the agent's part is lost by moving it, because GitHub reads `Co-Authored-By:` and renders that contributor on the commit and in the contribution graph.

> [!IMPORTANT]
> **This repository got it wrong before the rule was written down, which is why the rule exists.** Five commits on `Development` carry `Co-Authored-By:` for an agent while being **authored** by that same agent. Each one claims the agent as an additional contributor and simultaneously records it as the only one. The trailer was right and the field was wrong, and nothing reported the contradiction because nothing reads the author field.

An agent sets the identity once, before its first commit in a repository:

```bash
git config user.name 'Tanner Golden'
git config user.email '24684994+tannergolden@users.noreply.github.com'
```

Every commit then carries the trailer in its body, above the sign-off:

```text
docs(distribution): 📝 record who a commit is by

The body, wrapped at 72 characters, saying why this change and why this
way rather than the obvious alternative.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Signed-off-by: Tanner Golden <24684994+tannergolden@users.noreply.github.com>
```

Where the identity cannot be configured, set it per commit instead:

```bash
git commit -s --author='Tanner Golden <24684994+tannergolden@users.noreply.github.com>'
```

> [!NOTE]
> **Use the account's GitHub noreply address, not a personal one.** It is the address the contribution graph resolves, and it keeps a private inbox out of a history that is public and permanent. A commit is not redactable: a rewrite replaces the object and leaves the original reachable by SHA for anyone who already has it.

---

### 🎭 Emoji Mapping

Not enforced, and encouraged. One emoji after the colon reads well in a long log:

| Type       | Emoji    | Type       | Emoji    |
| :--------- | :------- | :--------- | :------- |
| `feat`     | ✨ 🆕 🚀 | `ci`       | 🤖 ⚙️ 🕒 |
| `fix`      | 🐛 🩹 🔧 | `chore`    | 🧹 🗂️ 🪛 |
| `docs`     | 📝 📚 📖 | `perf`     | ⚡️ 🏎️ 📈 |
| `style`    | 🎨 💄 🧼 | `test`     | 🧪 🔬 🧫 |
| `refactor` | ♻️ 🧩 🪚 | `build`    | 🏗️ 🧱 📦 |
| `revert`   | ⏪ 🔙 ↩️ | `security` | 🔒 🛡️ 🚨 |

---

### 🧭 When To Commit, And How Big

- **One intent per commit.** Split feature work from refactors and from formatting.
- **Green locally first**, so CI does not fail on something your own machine already knew about. The commands are whatever your project's `Makefile` or task runner defines.
- Prefer several **small commits** over one kitchen-sink commit.

---

### 🚀 The Commit Workflow

1. **Stage** what belongs in this commit, not everything you touched today.
2. **Write the message**: `type(scope): subject`, a blank line, then the body.
3. **Credit whoever contributed**: a `Co-Authored-By:` trailer per additional contributor, an AI agent included. The author field stays the repository owner.
4. **Sign off**: `git commit -s` adds the `Signed-off-by` trailer. The required **✍️ DCO Sign-Off** check blocks the merge without it. Forgot? `git commit --amend -s --no-edit`, or `git rebase --signoff @{upstream}` for a whole branch.
5. **Push**: `git push -u origin HEAD`.
6. **Open a pull request** into `Development`.

> [!NOTE]
> **The rulesets have your back, not a local hook.** Nothing here installs a git hook, so this protocol is enforced where it cannot be bypassed: the branch rulesets refuse a direct push to a protected branch, and `semantic-pr.yml` re-checks every commit message and sign-off on the pull request itself. A local hook you can disable with `--no-verify` is a convenience, not a control.

---

### 🧩 Branch Prefix Maps To Type

| Branch prefix  | Likely `type`              | Example subject                                   |
| :------------- | :------------------------- | :------------------------------------------------ |
| `feat/*`       | `feat`                     | `feat(auth): ✨ add passwordless sign-in`         |
| `bugfix/*`     | `fix`                      | `fix(payments): 🐛 handle webhook retries`        |
| `hotfix/*`     | `fix!` (breaking) or `fix` | `fix!(api): 🐛 sanitize headers to prevent crash` |
| `docs/*`       | `docs`                     | `docs(readme): 📝 add setup instructions`         |
| `experiment/*` | `feat` or `refactor`       | `refactor(search): ♻️ spike on vector index`      |
| `chore/*`      | `chore` or `refactor`      | `chore(repo): 🔧 align tsconfig across packages`  |

A map, not a rule. `feat` versus `fix` is a judgement about the change, and the branch name is only a hint about it.

---

### ✅ Good And Bad, With The Reason

**Good:**

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

**Bad:**

```text
fix(auth): 🐛 fix login bug
```

Two failures, and the missing body is the worse one. "fix login bug" restates
the type and the scope without adding anything, and the reader is left with a
diff and no account of which bug, how it presented, or why this fix rather
than another. Nothing here survives the moment its author forgets it.

**The same change, written:**

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

### 🔗 Where It Is Enforced

- **CI, per pull request**: `semantic-pr.yml` validates the **pull request title**. On a squash merge the title becomes the commit that lands, so this is the gate on what reaches the default branch.
- **CI, per commit**: the same workflow's `✍️ Commit Messages` job validates **every human-authored commit** in the pull request. This covers a repository that merges or rebases instead of squashing, where each message lands on the default branch in its own right. Bot-authored and merge commits are exempt, matching the DCO check exactly.
- **Local, optional**: `config/commitlint.config.js` encodes the same rules for anyone running commitlint in a Node toolchain. It is not required, and nothing in CI depends on it. The CI gate reads commits through the GitHub API instead, because the workflow runs on `pull_request_target` and installing packages from the pull request's own manifest would hand an elevated token to whoever opened it.
- **Changelogs**: `release-notes.yml` parses the resulting history with git-cliff to draft notes automatically.
- **Authorship: nowhere.** `scripts/commit-check.py` reads the message and never the author field, so the rule above is a convention rather than a gate. It is stated here because the failure it prevents is invisible: a commit authored by an agent looks correct in every log that shows only the subject, and the contradiction is visible only to somebody who thinks to run `git log --format='%an'`.

> [!IMPORTANT]
> **One rule set, three encodings.** The type list is written out in `scripts/commit-check.py`, in `config/commitlint.config.js`, and as the `commit-types` default in `semantic-pr.yml`. Changing one without the others produces a rule nobody enforces, or a message that passes one gate and fails another. This repository publishes its workflows rather than running them on itself, so nothing catches that automatically: run `python3 scripts/check-type-parity.py` before touching any of the three.

---

### 🧰 Do And Do Not

**Do**

- Keep the subject imperative and present tense: "add", "fix", "remove".
- Write the **why** in the body. It is required, not encouraged.
- Credit an AI agent that contributed with a `Co-Authored-By:` trailer.
- Mark **BREAKING CHANGE** explicitly in a footer.

**Do not**

- Combine unrelated changes into one commit.
- Ship a subject-only commit, however small the change looks.
- Let an AI agent author a commit. It is a co-author; the owner is the author.
- Add a `Co-Authored-By:` trailer for an agent that did not contribute.
- Use an em dash anywhere in the message. The gate rejects it.
- Paste secrets, tokens or personal data into a message. History is forever, and a rewrite is not a redaction.

---

### 🆘 Troubleshooting

| Symptom                               | Likely cause              | Fix                                                                      |
| :------------------------------------ | :------------------------ | :----------------------------------------------------------------------- |
| Message check fails on a pull request | Wrong type or format      | Adjust to `type(scope): subject`; the type list is above                 |
| Rejected for a missing scope          | Scope omitted             | This standard requires it. `docs:` becomes `docs(readme):`               |
| Subject too long or noisy             | Detail in the wrong place | Keep the subject under 72 characters and move the detail into the body   |
| Missing breaking-change notice        | Impact not stated         | Add a `BREAKING CHANGE:` footer with details                             |
| DCO check fails                       | No sign-off trailer       | `git commit --amend -s --no-edit`, or `git rebase --signoff @{upstream}` |
| The log shows an agent as the author  | Agent identity configured | Set `user.name` and `user.email` to the owner, then `git commit --amend --reset-author`. Already pushed? Leave it and fix the identity, or rewrite deliberately |
| Em dash rejected                      | Character in the message  | Replace with a comma, a colon, parentheses, or a spaced hyphen           |

---

### 🔗 See also

> [!TIP]
> Every canonical guide is indexed in the [&#x1F4DA; Standards Index](https://github.com/tannergolden/standards/blob/Development/docs/README.md). If you rename or move a file, update every reference to it across the repository to prevent link drift.

---

<div align="center">

**Small commits. Stated reasons.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by the Engineering Team. Distributed under the MIT License.

</div>
