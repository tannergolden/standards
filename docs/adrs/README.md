<!--
title: '🧭 ARCHITECTURE DECISIONS'
description: 'Architecture decision records for these standards, one file per decision, each logged with its status, date and evidence.'
type: index
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 🧭 ARCHITECTURE DECISIONS

<a name="top"></a>

**Every significant decision these standards have made, and why, one record each.**

_One decision per record. One row per decision._

</div>

---

## 💡 What This Folder Is For

An architecture decision record (ADR) captures one significant decision: the
context it was made in, the options weighed, and the consequences accepted.
Every record lives in this folder, one file per decision, and the log below is
their index. A record is written for these standards themselves; the decisions
a consuming repository makes live in its own `docs/adrs/`.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log fields=status,date,evidence -->

| Entry                                                                                              | Status   | Date       | Evidence | Purpose                                                                                                                                                                     |
| :------------------------------------------------------------------------------------------------- | :------- | :--------- | :------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`ADR-0001-Actions-And-Scripts-Live-In-Github.md`](ADR-0001-Actions-And-Scripts-Live-In-Github.md) | Accepted | 2026-10-19 | N/A      | The composite actions and their scripts move to .github/actions/ and .github/scripts/, where every repository keeps its own, with a forwarder at each old address until v2. |
| [`README.md`](README.md)                                                                           | -        | -          | -        | This file.                                                                                                                                                                  |

<!-- AUTO-INDEX:END -->

**This log is the decision index, and nobody types its rows.** It is redrawn
from each record's own frontmatter. **Status** is Proposed, Accepted,
Superseded, or Deprecated; **Date** is when the decision was made; **Evidence**
links the research that informed it, or reads N/A.

---

## 🌿 Adding A Decision

- [ ] Copy the
      [ADR template](https://github.com/tannergolden/path/blob/Development/docs/templates/ADR.md)
      into this folder as `ADR-NNNN-Short-Slug.md`, taking the next number.
- [ ] Set `type: record`, `status`, `date`, and `evidence` in its frontmatter,
      and write every section.
- [ ] Land it with the change that carries the decision out.

A later decision supersedes an earlier one rather than rewriting it: mark the
old record **Superseded** and link the new one.

---

<div align="center">

**Write the decision down while the reasons are still fresh.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the terms in [LICENSE](/LICENSE).

</div>
