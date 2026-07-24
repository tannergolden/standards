<!--
title: '📦 DEPENDENCY MANAGEMENT'
description: 'How dependencies are updated, reviewed, and kept secure.'
tags: [dependencies, dependabot, security, supply-chain]
category: docs
-->

<!-- markdownlint-disable MD041 -->
<div align="center">

# 📦 DEPENDENCY MANAGEMENT

<a name="top"></a>

**Securing the software supply chain through deterministic lifecycle management.**

_Deterministic installs. Automated auditing. Managed updates._

</div>

---

## 🎯 Our Strategic Objective

We treat third-party code as a first-class citizen of our architecture. Our objective is to maintain a lean, secure, and up-to-date dependency graph that maximizes developer velocity without compromising the production perimeter.

- **Parity**: Identical installation behavior across local, CI, and production environments.
- **Vigilance**: Continuous monitoring for vulnerabilities (SCA) and licensing risks.
- **Freshness**: Frequent, small updates to avoid "dependency debt" and breaking transitions.

---

## 🧱 Package Classification

| Field                 | Purpose                                  | Lifecycle                      |
| :-------------------- | :--------------------------------------- | :----------------------------- |
| **`dependencies`**    | Runtime code required for app execution. | Ships to production.           |
| **`devDependencies`** | Tooling for build, test, and style.      | Excluded from release bundles. |
| **`engines`**         | Runtime version requirements (Node.js).  | Enforced by the build engine.  |

> [!IMPORTANT]
> **Use `npm ci`, not `npm install`, in CI and production.** It performs a deterministic install based strictly on `package-lock.json` and fails loudly if the lockfile and manifest disagree.

---

## 🗓️ Managed Update Cadence

| Cadence        | Update Scope               | Primary Actor               |
| :------------- | :------------------------- | :-------------------------- |
| **Continuous** | Critical Security Patches. | Dependabot security alerts. |
| **Weekly**     | Minor & Patch Updates.     | Dependabot (Mon 07:00 UTC). |
| **As Needed**  | Major Version Bumps.       | Maintainer review.          |

---

## 🔐 Supply Chain Guardrails

1. **Lockfile Discipline**: Never manually edit `package-lock.json`.
2. **Provenance**: Prefer packages that provide build-integrity attestations.
3. **Registry Trust**: Default to the public NPM registry; avoid unverified private mirrors.
4. **License Filter**: Proactively block dependencies with restrictive licenses (e.g., GPL-3.0) for client-side distribution.

---

## 🤖 Automation Layer

**Dependabot** watches the GitHub Actions this repository pins, via
[`.github/dependabot.yml`](../../.github/dependabot.yml). There is no npm or pip
entry, because there is no `package.json` and no Python dependency file to
watch - an ecosystem pointing at a manifest that is not there produces a
standing error on the Dependabot tab rather than being quietly ignored.

Two entries cover it: the workflows directory, and the composite actions.

<details>
<summary>Click to view the shipped configuration</summary>

```yaml
updates:
  - package-ecosystem: 'github-actions'
    directory: '/'
    schedule: { interval: 'weekly', day: 'monday', time: '07:00' }
    commit-message: { prefix: 'build', include: 'scope' }
    groups:
      github-actions:
        patterns: ['*']

  # A glob, so a new action is covered the day it is added.
  - package-ecosystem: 'github-actions'
    directories: ['/actions/*']
    schedule: { interval: 'weekly', day: 'monday', time: '07:00' }
    commit-message: { prefix: 'build', include: 'scope' }
```

</details>

> [!IMPORTANT]
> **Every update is a Conventional Commit.** `commit-message.prefix` titles
> Dependabot's pull requests `build(deps): ...` instead of its default
> `Bump x from 1 to 2`. On a squash merge the title becomes the commit that
> lands, so without it every merged update writes a non-conforming message into
> permanent history - and git-cliff, which builds the changelog by parsing those
> messages, drops them **silently** rather than reporting a problem. Dependency
> updates would simply be missing from the release notes.
>
> `build` is the Conventional Commits type for changes to the build system or
> external dependencies. Set it on every ecosystem you add.

> [!TIP]
> **Name action directories with a glob, not a list.** Composite actions are not
> discovered through the workflows directory, so their folders need naming
> separately - and a hand-written list falls behind the tree without telling
> anyone. `'/actions/*'` cannot.

> [!NOTE]
> Because every action is pinned to a full commit SHA, the `github-actions` ecosystem is what keeps those pins current - Dependabot bumps the SHA and the version comment together.

---

## 🧯 Troubleshooting Dependency Drift

| Symptom                 | Probable Cause                          | Corrective Action                         |
| :---------------------- | :-------------------------------------- | :---------------------------------------- |
| **`ERESOLVE` Conflict** | Incompatible version ranges.            | Audit `package-lock.json` for duplicates. |
| **Local/CI Mismatch**   | `npm install` used instead of `npm ci`. | Clean `node_modules` and run `npm ci`.    |
| **Native Module Error** | Missing build tools (node-gyp).         | Install `build-essential` or Xcode tools. |

---

### 🔗 See also

> [!TIP]
> Every canonical guide is indexed in the [&#x1F4DA; Standards Index](https://github.com/tannergolden/standards/blob/Development/docs/README.md). If you rename or move a file, update every reference to it across the repository to prevent link drift.

---

<div align="center">

**Deterministic installs. Lean infrastructure.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by the Engineering Team. Distributed under the MIT License.

</div>
