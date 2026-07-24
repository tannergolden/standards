<!--
title: '📝 ENVIRONMENT & TECHNOLOGIES'
description: 'Environment setup and the language-agnostic tooling contract every stack must satisfy.'
tags: [environment, setup, tooling, onboarding]
category: docs
-->

<!-- markdownlint-disable MD041 -->
<div align="center">

# 📝 ENVIRONMENT & TECHNOLOGIES

<a name="top"></a>

**Defining the portable and reproducible engineering foundation.**

_Reproducible runtimes. Automated tooling. AI-assisted development._

</div>

---

## 🎯 Core Directive

We prioritize **Process over Products**. Whether you use Node, Python, Rust, or Go, all local operations must be mapped to the standardized `make` interface to ensure Continuous Integration (CI) parity.

> [!IMPORTANT]
> Use the exact tool versions pinned in the repository's configuration files (e.g., `.nvmrc`, `.python-version`). Always prefer version managers over direct system installs to avoid technical drift.

---

## 🏗️ Technology Pillars

### 🤖 AI-Native Development

We embrace AI assistants as core team members. You may use any AI app builder or IDE (e.g., Google Antigravity, Cursor, Lovable) provided they adhere to the project's governing principles.

- **Human Oversight**: Humans remain the final architects, reviewers, and approvers.
- **Workflow Integrity**: AI tools must follow the established [&#x1F916; AI-Driven Commit Process](../distribution/AI-Driven-Commit-Process.md).

### 🌐 Modern Web Standards

Build with high-performance frameworks (React, Vue, Svelte) and deploy to backend-agnostic hosting (Vercel, Firebase, AWS).

- **Security**: Mandatory HTTPS, secure headers, and environment-level secret management.

### 📱 Cross-Platform Mobile

Deliver high-fidelity iOS and Android applications from a single codebase using Flutter or Capacitor.

---

## 📋 Standard Support Matrix

| Category               | Standard Requirement                | Purpose                            |
| :--------------------- | :---------------------------------- | :--------------------------------- |
| **Operating System**   | macOS / Linux / Windows (WSL)       | Unified workstation environment.   |
| **Version Control**    | Git ≥ 2.40                          | Canonical source control.          |
| **Command Interface**  | **Makefile**                        | Standardized task entry point.     |
| **Runtime Management** | Version Managers (nvm, pyenv, etc.) | Isolated, reproducible runtimes.   |
| **Editor / IDE**       | VS Code / Cursor                    | Recommended development workspace. |

---

## 🧪 Stack Implementation Patterns

| Technology  | Setup Command                     | Test Command    | Pinning Mechanism     |
| :---------- | :-------------------------------- | :-------------- | :-------------------- |
| **Node.js** | `npm ci`                          | `npm test`      | `.nvmrc`              |
| **Python**  | `pip install -r requirements.txt` | `pytest`        | `.python-version`     |
| **Go**      | `go mod download`                 | `go test ./...` | `go.mod`              |
| **Rust**    | `cargo fetch`                     | `cargo test`    | `rust-toolchain.toml` |

---

## ⚒️ Universal Makefile Commands

Every project standardized on this system must implement the following `make` targets to allow CI automation to function without language-specific logic.

| Command               | Standard Lifecycle Purpose                                       |
| :-------------------- | :--------------------------------------------------------------- |
| **`make setup`**      | Install all dependencies and configure local hooks.              |
| **`make dev`**        | Start the local development server or emulators.                 |
| **`make lint`**       | Run static analysis, formatting, and style checks.               |
| **`make lint-docs`**  | Audit every document against the docs law (a required CI gate).  |
| **`make test`**       | Execute the primary automated test suite (Unit/Integration).     |
| **`make build`**      | Compile, bundle, or containerize for production.                 |
| **`make deploy`**     | Promote the current artifact to a specific environment.          |

> [!TIP]
> **Instant environment, two ways.** A devcontainer in your own repository gives you a one-click reproducible environment in Codespaces or any devcontainer-aware editor. The shipped one is deliberately language-neutral; add the toolchain features your project needs.

---

## 🔐 Environment & Secret Management

- **Local Work**: Copy `.env.example` → `.env.local`. Never commit local secrets.
- **CI/CD**: Secrets are stored in **GitHub Actions Environments** with mandatory reviewer gates.
- **Rotation**: Rotate production secrets immediately if exposed in logs or prompts.

> [!CAUTION]
> Never paste production secrets or proprietary data into AI IDE prompts. Treat prompts as semi-public text.

---

## 🆘 Troubleshooting Paradigms

| Symptom             | Probable Cause                        | Corrective Action                       |
| :------------------ | :------------------------------------ | :-------------------------------------- |
| **CI/Local Drift**  | Version mismatch or missing lockfile. | Check pinning file; run `make setup`.   |
| **Missing Modules** | Dependencies not synchronized.        | Run `make setup`; check `PATH`.         |
| **Rejected Push**   | Protection rule violation.            | Open a Pull Request into `Development`. |
| **Broken Hooks**    | Improper Husky setup.                 | `chmod +x .husky/*`; run `make setup`.  |

---

### 🔗 See also

> [!TIP]
> Every canonical guide is indexed in the [&#x1F4DA; Standards Index](https://github.com/tannergolden/standards/blob/Development/docs/README.md). If you rename or move a file, update every reference to it across the repository to prevent link drift.

---

<div align="center">

**Standardized tools. Unbounded velocity.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by the Engineering Team. Distributed under the MIT License.

</div>
