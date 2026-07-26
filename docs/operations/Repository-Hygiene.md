<!--
title: '🧩 REPOSITORY HYGIENE'
description: 'Practices that keep the repository clean and healthy over time.'
tags: [hygiene, maintenance, governance, structure]
category: docs
-->

<!-- markdownlint-disable MD041 -->
<div align="center">

# 🧩 REPOSITORY HYGIENE

<a name="top"></a>

**Maintaining a zero-noise engineering canvas through structural discipline.**

_Structured layout. Clean history. Zero-noise philosophy._

</div>

---

## 🎯 Our Strategic Intent

A clean repository is a fast repository. We prioritize organization and automation to ensure that contributors spend their time solving problems rather than fighting technical drift or cluttered environments.

- **Predictability**: Every file has a designated home.
- **Consistency**: Branching, naming, and commit styles are non-negotiable.
- **Noise Reduction**: We aggressively exclude binaries, build artifacts, and transient state from the source of truth.

---

## 🏗️ Standard Repository Topology

We adhere to a standardized structure so that any developer - or agent - can navigate the project within seconds of cloning. This is the shipped layout; add `src/`, `tests/`, `packages/`, and `benchmarks/` as your project grows (all four are pre-reserved in the template's layout):

```txt
/ (repo root)
├── .github/
│   ├── workflows/         # 22 reusable definitions + this repository's own self-* triggers
│   ├── dependabot.yml     # Keeps every pinned action current. Read only from the owning repo
│   └── CODEOWNERS         # Read only from the owning repo
├── actions/               # 17 composite actions, each shipping the files it needs
├── config/                # Tool configuration read BY a tool during a run
├── data/                  # Rulesets and the label taxonomy, written TO a repository
├── docs/                  # The standards themselves, followed by link
├── scripts/               # Helpers the composite actions ship and invoke
└── README.md, LICENSE, .ruff.toml, .editorconfig, .gitattributes, .gitignore
```

> [!IMPORTANT]
> **Two script homes, one rule.** `.github/scripts/` holds helpers executed only by workflows; `scripts/` holds everything a human or agent invokes (Makefile targets, `npm test`, session hooks). The split is load-bearing: anything a human or a build file invokes must keep a stable path, because those callers live in your repository and nothing updates them for you - while a helper called only by a workflow can move freely, since the workflow that calls it moves with it.

---

## 📌 The Root Manifest - Why Each Root File Is Root-Locked

The root is deliberately minimal: everything relocatable already lives in `config/` (prettier, commitlint, git-cliff, typos, lychee, labeler, zizmor). Each remaining root file is pinned there by a mechanical constraint - do not "tidy" these into folders:

| Root file                                                               | Locked by                                                                                                                                                                                                                      |
| :---------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `README.md`, `LICENSE`                                                  | GitHub renders both from the root; licensing detection requires it.                                                                                                                                                            |
| `Makefile`, `package.json`, `package-lock.json`                         | Build-tool discovery (`make`, npm) starts at the root; both are stable anchors everything else may reference.                                                                                                          |
| `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.cursorrules`, `.windsurfrules` | Every AI tool discovers its instruction file at the repository root.                                                                                                                                                           |
| `.gitignore`, `.gitattributes`                                          | Git resolves both from the tree root.                                                                                                                                                                                          |
| `.editorconfig`                                                         | Editors search upward and stop at `root = true` - must sit at the top.                                                                                                                                                         |
| `.nvmrc`                                                                | `nvm`/`fnm` and `setup-node` read it from the root by convention.                                                                                                                                                              |
| `.npmrc`                                                                | npm reads project config only from the package root.                                                                                                                                                                           |
| `_typos.toml`                                                           | The `typos` binary searches upward for root-level names only - verified empirically; it does not look inside `config/`.                                                                                                        |
| `lychee.toml`                                                           | lychee auto-discovers at the working directory; moving it would strand derived repos whose copy (yours-tier) never migrates.                                                                                                   |
| `.prettierignore`                                                       | Prettier auto-discovers it at the root; the invocations in `package.json` live in your repository and nothing updates them for you to pass an alternate path.                                                                               |
| `profile/`                                                              | GitHub renders the account profile only from a root-level `profile/` in an owner's `.github` home repository - content for that account's `.github` home repository only; a repository generated from the template has no use for it, and `init-template` removes it. |

---

## 🧱 The Mandatory Root Layer

Every fork or new project seeded from this standards-based repository must maintain these core artifacts to remain compliant with our delivery standards.

| File              | Purpose                       | Why it Matters                                        |
| :---------------- | :---------------------------- | :---------------------------------------------------- |
| **`README.md`**   | First contact and navigation. | Orients new contributors instantly.                   |
| **`LICENSE`**     | Legal governance.             | Defines how the code can be consumed.                 |
| **`SECURITY.md`** | Responsibility disclosure.    | Provides a path for ethical vulnerability reporting.  |
| **`CODEOWNERS`**  | Review accountability.        | Ensures changes are routed to the right experts.      |
| **`.gitignore`**  | Noise cancellation.           | Prevents secrets and artifacts from leaking into Git. |

---

## 🔤 Naming & Structural Conventions

| Asset Category      | Naming Convention              | Example                          |
| :------------------ | :----------------------------- | :------------------------------- |
| **Source & Config** | Kebab-case (all lowercase)     | `user-profile.ts`, `data-layer/` |
| **Test Files**      | Mirror source + `.test` suffix | `user-profile.test.ts`           |
| **Docs (`docs/`)**  | Capitalized-Kebab              | `Repository-Hygiene.md`          |
| **Env Templates**   | Suffix with `.example`         | `.env.example`                   |
| **Branches**        | `type/short-descriptive-slug`  | `feat/auth-magic-links`          |

> [!NOTE]
> Documentation uses Capitalized-Kebab names (every hyphen-separated word capitalized, never spaces or underscores) - the binding spec is [Document Styling & Formatting](../technical/interface/Document-Styling-&-Formatting.md). Everything executable or importable stays kebab-case, with one interpreter exception: a Python file that must be importable uses snake_case, the language's own convention, because a module name cannot contain a hyphen.

---

## 🤖 Automated Enforcement (Hooks)

We utilize **Husky** to ensure that code hygiene is enforced before it ever reaches the remote repository.

- **Pre-commit**: Auto-formats **fully staged** files with Prettier (via `config/prettierrc.json`) and restages them - partially staged files are deliberately skipped so the hook never commits changes you did not stage.
- **Commit-msg**: Enforces the [&#x1F916; AI-Driven Commit Process](../distribution/AI-Driven-Commit-Process.md).
- **CI Required Checks**: Blocks merges if the branch deviates from formatting or testing standards.

---

## 🔐 The Zero-Leakage Policy

- **Environment Isolation**: Local secrets MUST live in `.env.local` (Git-ignored).
- **Template Baseline**: Supply only non-sensitive placeholders in `.env.example`.
- **Secret Scanning**: Our CI pipeline will fail any PR containing confirmed credentials or tokens.

> [!CAUTION]
> If a secret is committed, it is considered compromised. Revoke the key immediately, rotate it, and follow the [Troubleshooting](Troubleshooting.md) guide for cleanup.

---

## 🔄 Ongoing Maintenance Schedule

| Cadence          | Action                                       | Responsibility                                          |
| :--------------- | :------------------------------------------- | :------------------------------------------------------ |
| **On merge**     | Delete merged head branches.                 | GitHub setting: **Automatically delete head branches**. |
| **Weekly**       | Triage open issues and label staleness.      | Automated (`governance.yml`).                           |
| **Monthly**      | Prune unused artifacts and update ADR index. | Maintainer.                                             |

---

## 📄 The Copyright Year Is Fixed At Generation

**REQUIRED.** A repository's `LICENSE` carries the year it was generated, and
that year never changes afterwards. Nothing rolls it, on a schedule or
otherwise.

`init-template` stamps it once, replacing the template's own year with the
year the new repository was created, in the same substitution that writes the
new owner's name. From that moment it is a fact about the repository, not a
setting to maintain.

This is deliberate, and it is the opposite of a common habit:

- **A copyright notice records when a work was published**, not what today's
  date is. Advancing it every January states something untrue about a project
  that has not been republished.
- **The year in a notice does not set or extend the term.** Copyright runs
  from actual creation or publication as a matter of fact. Rolling the year
  buys nothing and costs a pull request, a review, and a commit in every
  repository, twice a year, forever.
- **A year that moves is a year nobody can trust.** If it always says the
  current year, it tells a reader nothing they could not get from a calendar.

If a project genuinely is republished with substantial new work and you want
that reflected, widen it to a range by hand once: `Copyright (c) 2026-2029
<holder>`. That is an editorial decision about the work, and it belongs to a
person rather than a cron.

> [!IMPORTANT]
> Keep `Copyright (c) <4-digit year> <holder>` intact as a contiguous string
> in any template. That exact shape is what generation matches to restamp. A
> `[year]` placeholder does not match and would survive, unreplaced, into
> every repository generated from it.

---

### 🔗 See also

> [!TIP]
> Every canonical guide is indexed in the [&#x1F4DA; Standards Index](https://github.com/tannergolden/standards/blob/Development/docs/README.md). If you rename or move a file, update every reference to it across the repository to prevent link drift.

---

<div align="center">

**Structured for speed. Tidy for scale.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by the Engineering Team. Distributed under the MIT License.

</div>
