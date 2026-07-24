<!--
title: '📘 GLOSSARY'
description: 'Definitions for the engineering, Git, and automation terms used throughout the repository.'
tags: [glossary, terminology, reference, definitions]
category: docs
-->

<!-- markdownlint-disable MD041 -->
<div align="center">

# 📘 GLOSSARY

<a name="top"></a>

**The A–Z repository of terms, acronyms, and concepts used across our codebases, documentation, and workflows.**

_Common vocabulary. Defined intent. Consistent communication._

</div>

---

## 🎯 Our Communication Philosophy

We believe that clear, unambiguous language is the foundation of effective engineering. Our goal is to provide a single source of truth for terminology, ensuring that contributors, AI agents, and stakeholders speak the same language when discussing systems, processes, and state.

- **Standardization**: Avoid synonyms; use the defined term for a specific concept.
- **Traceability**: Link concepts to their primary documentation (ADRs, Principles).
- **Inclusivity**: Define acronyms and specialized jargon for rapid onboarding.

---

## 🧭 Alphabetical Index

[A](#a) | [B](#b) | [C](#c) | [D](#d) | [E](#e) | [F](#f) | [G](#g) | [H](#h) | [I](#i) | [J](#j) | [K](#k) | [L](#l) | [M](#m) | [N](#n) | [O](#o) | [P](#p) | [R](#r) | [S](#s) | [T](#t) | [U](#u) | [V](#v) | [W](#w) | [Y](#y) | [Z](#z)

---

## A

- **Accessibility (a11y)**: Inclusive design ensuring software is usable by people with disabilities.
- **actionlint**: The GitHub Actions linter that validates workflow semantics (expressions, needs/outputs, shellcheck on run blocks) in `lint-workflows.yml`.
- **ADR (Architecture Decision Record)**: A document capturing a significant technical choice and its rationale.
- **Artifact**: A build output produced by automation (e.g., compiled bundle, test report).

## B

- **Back-merge**: Merging changes from a promotion branch (e.g., Release) back to a base branch (e.g., Development).
- **Badge Kit**: The self-hosted generator that draws every badge into committed SVGs under `assets/badges/` - no third-party badge service, nothing to rate-limit.
- **Breaking Change**: A backward-incompatible modification that requires a MAJOR version bump.
- **Branch Protection**: Rules that gate pushes/merges to critical integration lines.

## C

- **Check Context**: The exact job name a ruleset requires green before merge (e.g. `🧪 Lint, Test & Build`); renaming the job silently un-requires it, so contexts and job names change together.
- **CI (Continuous Integration)**: Automated validation of every change (Lint, Test, Build).
- **CD (Continuous Delivery)**: Automated promotion of validated builds to staging or production.
- **Conventional Commits**: A structured commit message format for automated release notes.

## D

- **DCO (Developer Certificate of Origin)**: The provenance contract behind the `Signed-off-by:` trailer (`git commit -s`); a required merge check verifies it on every human-authored commit.
- **Devcontainer**: The shipped one-click environment (`.devcontainer/` - Node 22 + Python 3.12, `postCreateCommand: make setup`) for Codespaces and devcontainer-aware editors.
- **DORA Metrics**: KPIs for delivery performance (Lead Time, Deployment Frequency, MTTR, CFR).
- **Draft Release**: The single evolving pre-release git-cliff maintains per branch (superseded drafts are pruned); publishing it triggers the release pipeline.
- **Dry Run**: Executing validation without applying terminal state changes.

## E

- **E2E (End-to-End) Test**: Validating user journeys across the entire technical stack.
- **Environment**: An isolated runtime context (e.g., `preview`, `release`).

## F

- **Fail-closed / Fail-open**: The guardrail failure philosophy - quality gates fail **closed** (a broken gate blocks rather than waving changes through), while session conveniences fail **open** (a broken probe never blocks your work).
- **Feature Flag**: A toggle that enables or disables functionality without deployment.
- **Fork**: A personal copy of a repository used for experimentation or contributions.

## G

- **Gitleaks**: The CI secret scanner behind the required `🔍 Scan for Secrets` check (on org-owned repositories it needs a free `GITLEAKS_LICENSE` secret to actually scan).
- **these standards**: The recommended, standardized workflow for delivering value in this repository.
- **Governance**: The policies and principles that regulate code quality and security.

## H

- **Harden-Runner**: The egress-audit action every CI job runs first, recording each outbound connection the job makes.
- **Hotfix**: An urgent bug fix applied directly to production branches.

## I

- **IaC (Infrastructure as Code)**: Defining environmental resources (Cloud, DB) as versioned code.
- **Idempotency**: The property where an operation can be run multiple times with no additional side effects.

## J

- **Job**: A unit of work in a GitHub Actions workflow containing one or more steps.

## K

- **Key Rotation**: The practice of periodically replacing secrets to limit exposure risk.

## L

- **Linear History**: A git timeline free of merge commits, achieved through rebasing and squashing.
- **Linter**: A tool that analyzes source code to flag programming errors, bugs, or stylistic inconsistencies.

## M

- **Machined Index**: A document list generated between `AUTO-INDEX` markers by `scripts/update-doc-indexes.py --write` and verified by the same script with `--check` in `self-checks` - never hand-edited, so it can never disagree with the tree.
- **Merge**: Combining changes from one branch into another.
- **MTTR (Mean Time to Recovery)**: A DORA metric measuring how quickly a team recovers from failures.

## N

- **Node.js**: A JavaScript runtime used for server-side and tooling applications.
- **NPM**: Node Package Manager for JavaScript dependencies.

## O

- **OIDC (OpenID Connect)**: A protocol for federated authentication used in GitHub Actions.

## P

- **PR (Pull Request)**: The primary mechanism for proposing, reviewing, and validating code changes.
- **Parity**: Similarity between different environments (e.g., Local matching CI).
- **Promotion**: Moving validated code up the long-lived lines (`Experimental` → `Development` → `Preview` → `Release`), each hop a deliberate pull request.
- **Property-Based Testing**: Testing with generated adversarial inputs instead of hand-picked examples (Hypothesis, `fast-check`, `proptest`). Nothing here ships such a suite; wire yours in through `ci.yml`'s `test-command`.
- **Push Protection**: GitHub's platform-level secret blocking at push time - a leaked credential is stopped at the boundary, before it ever lands in history; enabled in code at init.

## R

- **Regression**: A bug that causes a feature to stop functioning after a change.
- **Rebase**: Re-applying commits on top of a new base branch to maintain linear history.
- **Ruleset**: Branch protection as importable JSON (`data/rulesets/`), applied via the API by `apply-rulesets.sh` - PR-only, squash-only, force-push blocked ([&#x1F6E1;&#xFE0F; Branch Protection](../operations/Branch-Protection.md)).

## S

- **SemVer (Semantic Versioning)**: `MAJOR.MINOR.PATCH` versioning logic based on the nature of change.
- **Squash**: Combining multiple commits into a single, cohesive unit during a merge.

## T

- **Tag**: A Git reference pointing to a specific commit, often used for releases.
- **Timeline**: The chronological sequence of commits in a repository.

## U

## V

- **Validation**: The process of ensuring code meets quality and functional requirements (Tests, Lint).
- **vars Context**: A GitHub Actions context for accessing repository variables (e.g., `vars.MY_VARIABLE`).

## W

- **Workflow**: A sequence of automated steps (GitHub Actions) triggered by repository events.

## Y

- **YAML**: A human-readable data format used for GitHub Actions workflows and configurations.

## Z

- **Zero Trust**: A security model that requires verification for every access request.
- **zizmor**: The workflow security auditor (template injection, credential persistence, cache poisoning) run at the pedantic persona in `lint-workflows.yml`.

---

## 🌿 Long-lived Branches

| Branch             | Logical Category | Strategic Purpose                         |
| :----------------- | :--------------- | :---------------------------------------- |
| **`Experimental`** | Sandbox          | CI-only spike line (the stable base).     |
| **`Development`**  | Integration      | The default line where features land.     |
| **`Preview`**      | Staging          | High-fidelity sandbox for E2E validation. |
| **`Release`**      | Production       | The immutable line of stable truth.       |

---

## 🏗️ Conventional Commit Blueprint

```txt
<type>(<scope>): <emoji> <short-summary>

[Rationale / Technical Context]

[Checklist of changes]
```

> **Legend**: ✨ `feat` | 🐛 `fix` | 📝 `docs` | 🎨 `style` | ♻️ `refactor` | ⚡ `perf` | 🧪 `test` | 🧹 `chore` | 📦 `build` | ⚙️ `ci` | ⏪ `revert` | 🔒 `security`

---

### 🔗 See also

> [!TIP]
> Every canonical guide is indexed in the [&#x1F4DA; Standards Index](https://github.com/tannergolden/standards/blob/Development/docs/README.md). If you rename or move a file, update every reference to it across the repository to prevent link drift.

---

<div align="center">

**Standardized for logic. Documented for scale.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by the Engineering Team. Distributed under the MIT License.

</div>
