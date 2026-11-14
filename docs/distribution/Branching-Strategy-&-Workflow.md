<!--
title: '🌿 BRANCHING STRATEGY & WORKFLOW'
description: 'The quad-tier branching model and the workflow for moving code to production.'
type: standard
-->

<!-- markdownlint-disable MD041 -->
<div align="center">

# 🌿 BRANCHING STRATEGY & WORKFLOW

<a name="top"></a>

**Architecting the path from local development to production stability.**

_Linear integration. Intentional promotion. Zero-downtime philosophy._

</div>

---

## 🎯 Our Strategic Model

We use a quad-tier long-lived branch architecture to isolate work-in-progress from user-facing environments. This structure follows a lineal promotion path: `Experimental` (the stable base) → `Development` → `Preview` → `Release`. This ensures that each stage of the lifecycle has a dedicated environment for validation. A repository generated from the template starts with one long-lived branch, `Development`, as its default; `Preview` and `Release` are created when the project is ready to distribute, and `Release` then becomes the default ([Opening The Release Line](#opening-the-release-line)). `Experimental` is optional: a project creates it from `Development` only when it wants a stable base beneath it.

> [!IMPORTANT]
> **All day-to-day integration targets `Development`, whichever branch is the default.** `Development` is the default until the project is ready to distribute; from then on `Release` is, so a visitor lands on the newest release rather than on work in progress. Direct pushes to long-lived branches are strictly prohibited.

---

## 🏗️ Branch Architecture

<strong>🧱 Branch Types (what they're for)</strong>

| Branch                               | Purpose                                 | Who writes                    | How it changes                                                       | Deploy target       |
| ------------------------------------ | --------------------------------------- | ----------------------------- | -------------------------------------------------------------------- | ------------------- |
| **`Experimental`** (Optional)        | Stable base                             | Nobody directly (via PR only) | Integration from upstream or core architecture shifts                | Sandbox             |
| **`Development`** (Default at first) | High-velocity integration line          | Nobody directly (via PR only) | **Promoted** from `Experimental`; Merges feat/bugfix branches        | Default environment |
| **`Preview`**                        | Staging for validation and UAT          | Nobody directly (via PR only) | **Promoted** from `Development`; critical bugfix PRs allowed         | Preview environment |
| **`Release`** (Default once created) | Production line; tagged versions        | Nobody directly (via PR only) | **Promoted** from `Preview`; emergency hotfix PRs allowed            | Production          |
| `feat/*`                             | New work (feature flags encouraged)     | Authors of the feature        | Rebase/merge with `Development` until ready; then PR → `Development` | None                |
| `bugfix/*`                           | Fixes for issues discovered pre-release | Authors of the fix            | PR → `Development` (or `Preview` if needed)                          | None                |
| `hotfix/*`                           | Emergency production fixes              | Release managers + owners     | PR → `Release` (then back-merge)                                     | Production          |
| `experiment/*`                       | Prototypes/spikes                       | Authors                       | PR → `Development` (guarded behind flags)                            | None                |

---

<strong>🔀 Naming & Commit Style</strong>

- Branch names:
  `feat/<topic>`, `bugfix/<ticket>`, `hotfix/<ticket>`, `experiment/<idea>`, `chore/<task>`.
  A prefix states what the work **is**, which is why no tool or vendor name
  belongs in the list.
- One exception, and it is compatibility rather than convention: an automated
  coding tool that opens a pull request names the branch after itself, does not
  read this standard, and offers no setting to change it. Those prefixes are
  accepted through a separate `agent-prefixes` input so the convention above
  stays about intent. Failing such a branch would punish the author for their
  tool's naming, and renaming it by hand breaks the tool's own tracking.
- Conventional Commits (for readable history & automated notes):
  `feat(auth): add passwordless sign-in`, `fix(payments): handle webhook retries`, `chore(deps): bump firebase`.

---

<strong>🧭 Allowed Flows (what can merge where)</strong>

| From           | To            | Allowed? | Notes                                         |
| -------------- | ------------- | :------: | --------------------------------------------- |
| `feat/*`       | `Development` |    ✅    | Primary path for new work (via PR)            |
| `bugfix/*`     | `Development` |    ✅    | Usual fix path (via PR)                       |
| `bugfix/*`     | `Preview`     |    ⚠️    | Only if needed to unblock a release candidate |
| `experiment/*` | `Development` |    ✅    | Keep behind feature flags                     |
| `Experimental` | `Development` |    ✅    | **Promotion** / Base sync via PR              |
| `Development`  | `Preview`     |    ✅    | **Promotion** via PR after checks             |
| `Preview`      | `Release`     |    ✅    | **Promotion** with approval; tag after        |
| `hotfix/*`     | `Release`     |    ✅    | Emergency only; back-merge required           |
| `Release`      | `Preview`     |    🔁    | Optional back-merge if diverged               |
| `Release`      | `Development` |    🔁    | **Required** after hotfix or tag              |
| `Preview`      | `Development` |    🔁    | Back-merge after release as needed            |

Legend: ✅ allowed • ⚠️ restricted • 🔁 back-merge

---

<strong>🗺️ Lifecycle Diagram (high-level)</strong>

```mermaid
flowchart LR
    subgraph "Human Developers"
        F[feat/*]
        B[bugfix/*]
    end

    subgraph "AI Agents"
        J[agent/topic-a]
        A[agent/topic-b]
    end

    subgraph "Protected Environments"
        Exp[Experimental]
        Dev[Development]
        Prev[Preview]
        Rel[Release]
    end

    F --> Dev
    B --> Dev
    J -- "PR" --> Dev
    A -- "PR" --> Dev
    Exp -- "Promotion PR" --> Dev
    Dev -- "Promotion PR" --> Prev
    Prev -- "Authorized Promotion" --> Rel
    Rel -- "Back-merge" --> Dev
```

---

<strong>✅ Branch Protection (the shipped ruleset)</strong>

| Rule                                                | Development | Experimental |  Preview  |  Release  |
| --------------------------------------------------- | :---------: | :----------: | :-------: | :-------: |
| Require PR before merge (squash-only)               |     ✅      |      ✅      |    ✅     |    ✅     |
| Required checks (build, dependencies, secrets, DCO) |     ✅      |      ✅      |    ✅     |    ✅     |
| Restrict pushes (no direct push, no deletion)       |     ✅      |      ✅      |    ✅     |    ✅     |
| Restrict force-push (see note)                      | owner-only  |  owner-only  |    ✅     |    ✅     |
| Required reviews                                    |  0 shipped  |  0 shipped   | 0 shipped | 0 shipped |

> [!NOTE]
> **Force-push is owner-only on the integration line.** `Preview` and `Release` are force-push-immutable for everyone. On `Development` and `Experimental` force-push is blocked for everyone **except the repository owner** (the integration ruleset grants the Repository-admin role a full ruleset bypass - which, among other things, permits the force-push), which is what lets the owner normalize the generation root commit at Day 0. See [Branch Protection](../operations/Branch-Protection.md) for the two shipped rulesets.

> [!NOTE]
> **Why 0 reviews ship**: solo maintainers and automation PRs (dependency bumps, the formatting sweep) must never deadlock - CI still gates every merge. **Recommended hardening as the team grows**: raise required reviews to ≥1 (code owners for risky changes on `Preview`, release-manager approval on `Release`), require branches to be up to date with the base, and enable signed commits.

> [!TIP]
> Keep local commands and CI identical to avoid "works on my machine". Whatever your project runs for lint, test and build, CI should invoke exactly that, which is why `ci.yml` takes the commands rather than assuming them.

---

<strong>🚦 Everyday Developer Flow</strong>

### 1. The Starting Line

```bash
git switch Development && git pull --ff-only
git switch -c feat/topic-name
```

### 2. High-Frequency Integration

Keep your topic branch fresh by rebasing on `Development` regularly. This minimizes conflict debt.

```bash
git fetch origin
git rebase origin/Development
git push --force-with-lease
```

### 3. The PR Process

> [!TIP]
> Use **Squash Merges** for all PRs into `Development`. This collapses your working history into a single, high-signal commit that follows [Conventional Commits](https://www.conventionalcommits.org).

---

<strong>🚢 Promotion & Tagging</strong>

1. **Promotion**: Move `Development` → `Preview` via PR.
2. **Validation**: Perform QA and E2E checks on the Preview URL.
3. **Delivery**: Promote `Preview` → `Release`.
4. **Versioning**: Create an annotated tag (e.g., `v1.2.0`) and generate the release notes.
5. **Synchronization**: Back-merge `Release` into `Development`.

---

<a name="opening-the-release-line"></a>

<strong>🌱 Opening The Release Line</strong>

A new repository has one long-lived branch, `Development`, and the topic branches cut from it. `Preview` and `Release` wait until the owner judges the project ready to distribute: before then there is nothing to stage and nothing released to show. At that point the owner, in this order:

1. **Creates `Preview`** from the newest `Development`, and validates it there.
2. **Creates `Release`** from the newest `Preview`.
3. **Makes `Release` the default branch.** The default branch is what a visitor meets first: the repository's front page and README, a clone, a download. From then on that is the newest release, not work in progress.
4. **Confirms that `Development`, `Preview` and `Release` are protected** and cannot be deleted.

Several stubs, and Dependabot, follow the default branch instead of naming `Development`, so they are pointed at `Development` first, in a pull request into it, and both new branches start with the change. The steps in full, with that list: [🙋 What You Do By Hand](../introduction/What-You-Do-By-Hand.md#ready-to-distribute).

> [!IMPORTANT]
> **Once `Release` is the default, pick `Development` as the base of every new pull request.** GitHub preselects the default branch, and the flows above have not changed: new work goes to `Development`.

---

<strong>🔧 Hotfix Protocol (production incident)</strong>

1. Create `hotfix/<ticket>` from `Release`.
2. Minimal fix; add tests; open PR → `Release`.
3. After merge, **tag patch** (e.g., `v1.2.1`) and **back-merge** into `Development` (and `Preview` if needed).
4. Consider a follow-up `bugfix/` to refactor if the change was rushed.

> [!CAUTION]
> Don't batch unrelated fixes in a hotfix PR. Keep scope tiny to minimize blast radius and simplify rollback.

---

<strong>🧨 Conflict & Divergence Handling</strong>

- Prefer **rebase** to keep topic branches linear: `git rebase origin/Development` → fix → `git push --force-with-lease`.
- After release, if `Preview` diverged, **back-merge** from `Release` or re-promote `Development → Preview`.

---

<strong>🧰 Useful Commands (copy/paste)</strong>

### Topic Branch Synchronization

```bash
git fetch origin
git rebase origin/Development
git push --force-with-lease
```

### Opening a Pull Request

Open a Pull Request targeting `Development`. Ensure the description links to relevant issues and clearly states the risk profile.

---

<strong>🧪 Quality Gates (what must be green)</strong>

- **Lint**: `make lint` (Prettier check) passes.
- **Tests**: `make test` passes.
- **Build**: `make build` succeeds.
- **Security**: CodeQL analysis, Gitleaks secret scan, and Dependency Review report no new findings.
- **Hygiene**: the PR title follows Conventional Commits; spell check and link check are clean.

---

<strong>❓ Frequently Asked Questions (FAQ)</strong>

- **Why does the default branch move from `Development` to `Release`?**
  The default branch is what a visitor sees first. Until the project is ready to distribute, every pull request goes to `Development` and nothing has been released, so `Development` is the default. After that, most visitors come for what was released, so they land on `Release`, and contributors pick `Development` as their base.

- **When can I merge to `Preview` directly?**
  Rarely - only critical fixes to unblock a release candidate.

- **Do we allow merge commits?**
  No - squash is the **only** merge method. The rulesets allow nothing else on the four protected branches, and init disables merge commits and rebase-merges repository-wide, so the option never even appears in the merge button.

---

### 🔗 See also

> [!TIP]
> Every canonical guide is indexed in the [&#x1F4DA; Standards Index](https://github.com/tannergolden/standards/blob/Development/docs/README.md). If you rename or move a file, update every reference to it across the repository to prevent link drift.

---

<div align="center">

**Branching for velocity. Merging for integrity.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by the Engineering Team. Distributed under the terms in [LICENSE](/LICENSE).

</div>
