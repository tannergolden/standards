<!--
title: '🕒 AUTOMATION SCHEDULES'
description: 'The recommended cadence for every scheduled workflow, and why the schedule lives in your repository rather than this one.'
tags: [automation, schedules, workflows, cron]
category: docs
-->

<!-- markdownlint-disable MD041 -->
<div align="center">

# 🕒 AUTOMATION SCHEDULES

<a name="top"></a>

**A predictable cadence for repository maintenance.**

_Staggered, off-peak, and yours to change._

</div>

---

## ⚠️ The Schedule Is Not Set Here

Every workflow **published** here is **reusable**: it declares `on: workflow_call` and nothing else,
so it carries no cron of its own and cannot fire on its own. Two files in that directory are local to
this repository rather than published - `release.yml`, which is dispatch-only, and `self-checks.yml`,
which carries the one cron that actually fires here and is listed below with the rest.

**The `schedule:` block lives in your stub, in your repository.** That is the only place GitHub
looks. The table below is the recommended cadence that the template repositories' stubs and the example
in each workflow header already use, not a setting you inherit. Change a cron in your stub and it changes,
with nothing to sync back here.

---

## 🚦 Recommended Cadence

| Workflow, job                | Recommended (UTC) | Why that slot                                              |
| :--------------------------- | :---------------- | :--------------------------------------------------------- |
| `checks.yml`, weekly sweep   | Weekly, Mon 03:00 | CodeQL and the secret scan over code nothing touched       |
| `governance.yml`             | Weekly, Mon 04:00 | Start-of-week triage, stale sweep, locking, labels         |
| `self-checks.yml` (local)    | Weekly, Mon 04:00 | This repository's own gate, so a moving upstream is caught |
| `release.yml`, `notes`       | Weekly, Mon 05:00 | One evolving draft, refreshed before the week opens        |
| `maintenance.yml`, `prune`   | Weekly, Mon 06:00 | Housekeeping, after the jobs that create the runs          |
| `lifecycle.yml`, `standards` | Weekly, Mon 07:00 | Last of the weekly sweep, and it usually does nothing      |

Everything else is **event driven** and needs no schedule:

| Trigger                      | Workflows                                                     |
| :--------------------------- | :------------------------------------------------------------ |
| Push and pull request        | `checks.yml`, `auto-format.yml`, `verify-stubs.yml`           |
| Pull request, issue, comment | `governance.yml`; `dependabot-automerge.yml` on PRs only      |
| Another workflow finishing   | `ci-failure-alert.yml`                                        |
| Release published            | `release.yml` - the `publish` and `prune-releases` jobs       |
| Push to a preview branch     | `preview-deploy.yml`                                          |
| Manual dispatch only         | `apply-standards.yml`; the `package` and `prune-drafts` tasks |
| Repository generated         | `lifecycle.yml` - the `init` job, once                        |

> [!NOTE]
> **Draft-release deletion is dispatch-only on purpose.** It deletes releases, and a destructive
> action nobody chose to run is a different risk from a tidy-up nobody notices. It is a `task`
> choice in `maintenance.yml`'s dispatch form, and no schedule can reach it - give it one and you
> have removed that distinction.

---

## 🧭 The On-The-Hour Rule

Every recurring cron fires at minute `00`, never a jittered minute, and each one takes a distinct
off-peak hour. When you add or retune a schedule: keep the minute at `00`, pick an hour that
suits the job, stagger it clear of the others, and record it above. Two crons can share a workflow
file - each job checks `github.event.schedule` for the cron that fired, so a file carrying more
than one schedule routes each cron to the job that asked for it.

The staggering is not superstition. Several of these call the same API surface, and starting them
together means competing for the same rate limit at the same instant.

---

## 🛡️ Nothing Scheduled Pushes To A Protected Branch

Workflows that produce changes propose them as a pull request and merge through the same gates as a
human change. That covers `auto-format.yml`.
`release-notes.yml` is the one exception in form rather than principle: it maintains a single
evolving **draft** release, which publishes nothing until somebody presses publish.

---

## ⏳ The 60-Day Platform Clock

GitHub **automatically disables every scheduled workflow in a public repository after 60 days
without repository activity**, with one warning email first.

A repository running `dependabot-automerge.yml` usually stays alive on its own, since weekly
dependency pull requests merging on green CI count as activity. One that genuinely goes cold will
have its crons stopped until somebody re-enables them from the Actions tab.

This is platform behaviour, not something these standards configure, and no setting here can opt out
of it.

---

## 🔄 Where The Truth Lives

The `schedule` block in **your** stub is the source of truth for when anything runs. This page is a
convenience summary of the recommended cadence; live history is in your repository's **Actions**
tab.

### 🔗 See also

> [!TIP]
> Every canonical guide is indexed in the [&#x1F4DA; Standards Index](../../README.md). If you
> rename or move a file, update every reference to it across the repository to prevent link drift.

---

<div align="center">

**Predictable cadence. Set where it runs, not where it is written.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
