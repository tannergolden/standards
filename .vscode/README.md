<!--
title: '⚙️ EDITOR SETTINGS'
description: 'The VS Code settings and extension recommendations this repository shares, and why every other file in this folder stays out of git.'
type: index
keywords: [vscode, configuration, onboarding]
-->

<div align="center">

# ⚙️ EDITOR SETTINGS

<a name="top"></a>

**The VS Code defaults every contributor shares, and the line git draws around them.**

_Shared on purpose. Personal by default._

</div>

---

## 💡 What This Folder Is For

VS Code reads this folder when it opens the repository, inside the
[development container](../.devcontainer/README.md) as much as outside it.
What is committed here is what everyone working on these standards should
get: format on save, a final newline, and a short list of extensions for the
Python scripts and the Markdown documents.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                                | Purpose                                                                                                                     |
| :----------------------------------- | :-------------------------------------------------------------------------------------------------------------------------- |
| [`extensions.json`](extensions.json) | The extensions VS Code offers on opening: the editor basics, Markdown, TOML, and Python with Ruff for the scripts.          |
| [`README.md`](README.md)             | This file.                                                                                                                  |
| [`settings.json`](settings.json)     | Format and fix on save, a final newline, no trailing whitespace, no telemetry, and the words the spell checker should know. |

<!-- AUTO-INDEX:END -->

`make docs-index` redraws this log, from what each file says about itself. Read
the next section before you add one. 🚦 Self Checks fails a push that leaves it
stale.

---

## 🌿 What Git Keeps Here

> [!IMPORTANT]
> **Everything in this folder is ignored except what `.gitignore` names.** It
> keeps `extensions.json`, `settings.json`, `launch.json`, `tasks.json`, and
> this README. Any other file is silently left out by `git add`, with no warning
> and no error, which is how a personal setting stays personal.

`launch.json` (debug configurations) and `tasks.json` (build, test, and run
tasks) are tracked so a team can share them, but neither ships, because both
depend on the language. Add them once the project has something to launch.

Markdown lint rules do not live here. They are in `.markdownlint.json` at the
root, where the editor extension and a command-line run read the same file.

Both JSON files here are strict JSON, with no comments, because 🚦 Self Checks
parses every JSON file in the repository as JSON. What a comment would have
said is in the log above.

---

<div align="center">

**Commit what the team shares. Keep what is yours.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by the Engineering Team. Distributed under the terms in [LICENSE](../LICENSE).

</div>
