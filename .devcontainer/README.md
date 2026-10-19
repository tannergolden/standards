<!--
title: '🐳 DEVELOPMENT CONTAINER'
description: 'The development container for working on these standards: Python, Node, and the test tools at the versions CI pins.'
type: index
keywords: [devcontainer, development-environment, configuration, onboarding]
-->

<div align="center">

# 🐳 DEVELOPMENT CONTAINER

<a name="top"></a>

**A container that runs every check CI runs.**

_The same tools, at the same versions._

</div>

---

## 💡 What This Folder Is For

Open the repository in a dev container - <kbd>Reopen in Container</kbd> in VS
Code, or a Codespace - and this folder decides what you get: an Ubuntu base
image, git, the common shell utilities, Python for the scripts, Node for
Prettier, and pytest and ruff at the versions 🚦 Self Checks pins, so
`make test` and `make lint` run here as they run in CI.

`.gitattributes` marks this folder `export-ignore`, so `git archive` leaves it
out of a source tarball. It is for developing these standards, not for shipping
them.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                                    | Purpose                                    |
| :--------------------------------------- | :----------------------------------------- |
| [`devcontainer.json`](devcontainer.json) | Development container for these standards. |
| [`README.md`](README.md)                 | This file.                                 |

<!-- AUTO-INDEX:END -->

`make docs-index` redraws this log, from what each file says about itself. 🚦
Self Checks fails a push that leaves it stale.

---

## ⚙️ Keeping It In Step

- The pytest and ruff versions in `postCreateCommand` are the ones
  `PYTEST_VERSION` and `RUFF_VERSION` pin in 🚦 Self Checks and the Makefile.
  Change all three together, or the container checks something CI does not.
- Prettier runs through `npx` at the version the Makefile pins, so Node is all
  the container needs for it.
- Rebuild the container after any change here.

> [!NOTE]
> **There is no `settings` block, deliberately.** VS Code reads
> [`.vscode/settings.json`](../.vscode/settings.json) inside the container like
> anywhere else, so a copy here would be a second source of truth, and the copy
> that drifts is always the one nobody remembers.

`devcontainer.json` is strict JSON, with no comments, because 🚦 Self Checks
parses every JSON file in the repository as JSON.

---

<div align="center">

**The same checks, wherever you open it.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by the Engineering Team. Distributed under the terms in [LICENSE](../LICENSE).

</div>
