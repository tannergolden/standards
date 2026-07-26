<!--
title: '🔐 SECURITY & SECRETS'
description: 'Secret handling, scanning, and incident response for the repository.'
tags: [security, secrets, incident-response, operations]
category: docs
-->

<!-- markdownlint-disable MD041 -->
<div align="center">

# 🔐 SECURITY & SECRETS

<a name="top"></a>

**Hardening the engineering perimeter through zero-trust credential governance.**

_Zero-trust architecture. Ephemeral credentials. Automated oversight._

</div>

---

## 🎯 Our Security Objectives

We prioritize security from the very first commit. Our objective is to minimize the blast radius of any individual credential and ensure that all environmental access is auditable, revocable, and temporary.

- **Zero Leakage**: No secrets in source code, commits, or logs.
- **Least Privilege**: Grant only the minimum permissions required for any specific task.
- **Verified Identity**: Commit signing (GPG/SSH) strongly recommended for all contributors - enforceable via a ruleset once every committer signs (see [Branch Protection](Branch-Protection.md)).
- **Rapid Recovery**: Standardized protocols for immediate rotation and incident response.

---

## 🧱 The Golden Rules of Secrets

1. **Never Commit Secrets**: Use `.env.example` placeholders only.
2. **Prefer OIDC**: Use short-lived tokens via OpenID Connect instead of static cloud keys.
3. **Isolate Environments**: Maintain strictly distinct secrets for `Development`, `Preview`, and `Release`.
4. **Automate Scanning**: Every Pull Request is gated by automated secret detection (on org-owned repositories, add the free `GITLEAKS_LICENSE` secret - without it the gate stays green but scans nothing).

---

## 📦 Where Secrets Live

| Location                 |       Status       | Strategic Use Case                                      |
| :----------------------- | :----------------: | :------------------------------------------------------ |
| **Source Code / PRs**    | 🚫 **PROHIBITED**  | Never treat Git as a storage layer for secrets.         |
| **GitHub Environments**  |  ✅ **APPROVED**   | Store environment-specific secrets with reviewer gates. |
| **Cloud Secret Manager** | ✅ **RECOMMENDED** | Preferred for runtime application configuration.        |
| **Local `.env.local`**   | ⚠️ **RESTRICTED**  | Developer use only. Must be present in `.gitignore`.    |

---

## 🧭 Rotation & Expiry Policy

| Secret Category          | Persistence | Target Lifetime | Rotation Event        |
| :----------------------- | :---------- | :-------------- | :-------------------- |
| **CI/CD Tokens**         | Ephemeral   | 1 Hour          | Automatic per job.    |
| **API Keys (3rd Party)** | Static      | 90 Days         | Calendar-based.       |
| **Database Credentials** | Static      | 6 Months        | Periodic Maintenance. |

> [!IMPORTANT]
> A compromised secret must be rotated **instantly**. Do not wait for a maintenance window if a leak is confirmed.

---

## 🔍 Automated Guardians

| Tool                       | Focus                                                                      | Cycle                             |
| :------------------------- | :------------------------------------------------------------------------- | :-------------------------------- |
| **Gitleaks**               | Secret & Pattern Detection (CI layer).                                     | Every Commit / PR.                |
| **GitHub Secret Scanning** | Platform-native detection + **push protection** (applied by Apply Standards). | Continuous, at the boundary.      |
| **Dependabot**             | Vulnerable Dependencies (SCA).                                             | Continuous.                       |
| **CodeQL**                 | Semantic Security Flaws (SAST).                                            | Every PR / Weekly (public repos). |
| **Harden-Runner**          | Runner Egress Audit.                                                       | Every job run.                    |

> [!NOTE]
> **Disclosure is wired too**: **🎯 Apply Standards** enables **private vulnerability reporting** with `apply-settings`, so coordinated disclosure (Security tab → Report a vulnerability) works once you have run it - see [`SECURITY.md`](https://github.com/tannergolden/.github/blob/Development/SECURITY.md). It is a public-repository feature, and the run says so and skips rather than failing on a private one.
>
> **Initialisation does not do this.** It rewrites identity and nothing else. Until Apply Standards has run with `apply-settings: true`, these are off.

---

## 🧯 Incident Response Protocol

If a secret is inadvertently committed to the repository, follow this immediate containment path:

1. **REVOKE**: Invalidate the compromised credential at the provider level immediately.
2. **ROTATE**: Provision a new secret and update the relevant GitHub Environment.
3. **AUDIT**: Check logs to verify if the compromised secret was used by unauthorized actors.
4. **PREVENT**: Update local `.gitignore` and CI filters to prevent a recurrence.

> [!CAUTION]
> Rewriting Git history to remove a secret is second-order priority. The first priority is always **REVOCATION**. Once a key hit the network, it is public regardless of history purging.

---

### 🔗 See also

> [!TIP]
> Every canonical guide is indexed in the [&#x1F4DA; Standards Index](https://github.com/tannergolden/standards/blob/Development/docs/README.md). If you rename or move a file, update every reference to it across the repository to prevent link drift.

---

<div align="center">

**Identities verified. Perimeter hardened.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by the Engineering Team. Distributed under the MIT License.

</div>
