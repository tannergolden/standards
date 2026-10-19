<!--
title: '🧭 ADR-0001: ACTIONS AND SCRIPTS LIVE IN .GITHUB'
description: 'The composite actions and their scripts move to .github/actions/ and .github/scripts/, where every repository keeps its own, with a forwarder at each old address until v2.'
type: record
keywords: [repository-layout, composite-action, forwarder, migration]
status: 'Accepted'
date: '2026-10-19'
evidence: 'N/A'
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 🧭 ADR-0001: ACTIONS AND SCRIPTS LIVE IN .GITHUB

<a name="top"></a>

**The actions and their scripts move into `.github/`, with a forwarder at each old address.**

_Every repository the same shape. No caller broken on the way._

</div>

---

## 📋 Meta Information

> [!NOTE]
> **Status**, **Date**, and **Evidence** live in the frontmatter above and feed the
> [ADR index](README.md).

| Attribute     | Specification                                         |
| :------------ | :---------------------------------------------------- |
| **Deciders**  | The repositories' owner                               |
| **Consulted** | The AI agent that carried out the move                |
| **Informed**  | Every repository that calls an action from these ones |

---

## 🎯 Context & Problem Statement

Both golden path templates keep a repository's composite actions in
`.github/actions/<name>/` and its own scripts in `.github/scripts/`, and every
repository generated from them follows. These standards were the outlier: their
19 actions sat in a root `actions/` folder and their scripts in a root
`scripts/`, so the repository that writes the layout rule broke it.

The actions are called by address, `tannergolden/standards/actions/<name>@v1`,
from the reusable workflows here and from repositories that call one directly.
`v1` moves with every release, so deleting the old folder would break every such
caller at the next release, including callers outside this account.

---

## 🏗️ Considered Options

1. **Move within v1, with forwarders**: move the actions and scripts, and leave
   at each old `actions/<name>/action.yml` a forwarder that declares the same
   inputs and outputs and passes them to the action at its new address.
2. **Move and release v2**: cleaner, but every repository has to move every
   stub to `@v2` at once, for a folder move.
3. **Leave them at the root**, as the one exception to the layout.

---

## ✅ Decision Outcome

**Chosen Option**: Option 1, move within v1, with forwarders.

### Rationale For Selection

It is the only option that matches the templates without breaking a caller. A
caller pinned to `v1` keeps working through the forwarder until it moves to the
new address, and the reusable workflows here call the new address from the
release that carries the move. Each action still finds its script at
`$GITHUB_ACTION_PATH/../../scripts/`, which is now `.github/scripts/`, and the
shared `config/` and `data/` folders one level further up.

### What Changed

| Was                                                        | Is now                                                        |
| :--------------------------------------------------------- | :------------------------------------------------------------ |
| `actions/<name>/action.yml`                                | `.github/actions/<name>/action.yml`, each with a README       |
| `scripts/`                                                 | `.github/scripts/`                                            |
| `tannergolden/standards/actions/<name>@v1` in every caller | `tannergolden/standards/.github/actions/<name>@v1`            |
| `<standards>/scripts/update-doc-indexes.py`, run by hand   | `<standards>/.github/scripts/update-doc-indexes.py`           |
| -                                                          | A forwarder at each old `actions/<name>/action.yml`, until v2 |

---

## 📈 Consequence Matrix

| Category         | Impact / Consequence                                                                                   |
| :--------------- | :----------------------------------------------------------------------------------------------------- |
| **Positive (+)** | These standards follow their own layout rule, and no caller breaks                                     |
| **Negative (-)** | 19 forwarders to keep in step with their actions' inputs and outputs until v2                          |
| **Neutral (~)**  | A hand-run path to a script changes once, and `config/` and `data/` stay at the root as shared folders |

**At the next major version**, delete `actions/`, and drop it from the
self-checks and the release's reference check.

---

## 🔗 See Also

- [Repository Hygiene](../operations/Repository-Hygiene.md), the layout rule
- [`.github/actions/`](../../.github/actions/README.md) and the forwarders in
  [`actions/`](../../actions/README.md)

---

<div align="center">

**Moved, never broken.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
