<!--
title: '🐳 DEVELOPMENT CONTAINER'
description: 'The development container for working on these standards: the environment image, with every tool the checks run at the versions CI installs, and jq for the suite.'
type: index
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
Code, or a Codespace - and this folder decides what you get: the environment
image, `ghcr.io/tannergolden/environment:1`. It holds git, Python, Node.js
and every tool the checks run, at the versions 🚦 Self Checks installs through
the environment's toolchain action, and jq is added when the container is
created, for the suite's fake `gh`. So `make test`, `make lint` and
`make lint-format` run here as they run in CI.

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

- Nothing here pins a checker. The image and 🚦 Self Checks take every version
  from the same toolchain, in `tannergolden/environment`, so they agree once
  this container runs the release Self Checks does. It keeps the image it
  pulled until it pulls `:1` again, and a release moves the action's `v1`
  minutes before it publishes the image.
- jq comes from Ubuntu's archive when the container is created, as the
  image's own system packages do.
- A new image reaches this container after
  `docker pull ghcr.io/tannergolden/environment:1` and a rebuild.
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

Built with ❤️ by the Engineering Team. Distributed under the terms in [LICENSE](/LICENSE).

</div>
