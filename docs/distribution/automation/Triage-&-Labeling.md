<!--
title: '🚦 TRIAGE & LABELING'
description: 'Automated triage, sizing, and labeling of issues and pull requests.'
tags: [triage, labels, automation, issues]
category: docs
-->

<!-- markdownlint-disable MD041 -->
<div align="center">

# 🚦 TRIAGE & LABELING

<a name="top"></a>

**Categorizing at scale to optimize the integrator's cognitive load.**

_Intelligent routing. Size Estimation. Conflict detection._

</div>

---

## 🎯 Our Management Strategy

We rely on automated triage to keep the repository organized without manual toil. By categorizing work as it enters the system, we enable maintainers and AI agents to prioritize effectively and resolve blockers instantly.

- **Instant Recognition**: Every PR and Issue is labeled within seconds of creation.
- **Reviewer Guidance**: Size labels provide reviewers with an instant context of the required effort.
- **Conflict Vigilance**: Active detection of divergent history prevents stall in the integration pipeline.

---

## 🏗️ Automated Capabilities

### 1. Intelligent Pull Request Labeling

- **Area Identification**: Labels are applied based on the directory path of modified files (e.g., `area: backend`, `area: database`).
- **Workload Estimation**: PRs are quantified by line change counts on the five-step scale from `size: extra small` to `size: extra large`.
- **Conflict Alerts**: Automatically applies `status: conflict` and notifies the author if the branch diverges from the integration line.

### 2. Issue Triage & Routing

- **Classification**: Automatically separates `type: feature` requests from `type: bug` reports based on standard templates.

---

## ⚙️ Core Configuration

The logic for our triage system resides in these infrastructure files:

| Layer        | Configuration Path                     | Purpose                                                  |
| :----------- | :------------------------------------- | :------------------------------------------------------- |
| **Logic**    | `.github/workflows/governance.yml` | The primary orchestration workflow.                      |
| **Area Map** | `.github/labeler.yml`                  | Maps repository paths to `area:` labels.                 |
| **Registry** | `.github/labels.yml`                   | The canonical label set, synced by the `label-sync` job. |

> [!NOTE]
> **The intake surface belongs to your repository.** The issue forms, discussion templates and `release.yml` are copied in when a repository is generated from the template and are yours to edit from that point - nothing reaches back to change them. What stays shared is the label registry itself: `data/labels.yml` here is applied over the GitHub API by the governance workflow's `label-sync` job, create-or-update only, so labels you add by hand survive. Run **🎯 Apply Standards** once to provision the taxonomy, and the forms can apply labels from the very first issue.

---

## ⚡ Execution Hooks

- **Pull Requests**: Triggered on `opened`, `synchronize`, and `reopened` - the triage job labels **PRs only**.
- **Issues**: Labeled by the **issue forms themselves** at creation (each form declares its labels, e.g. `type: bug` + `status: needs triage`); the workflow's issue events serve the first-time-contributor welcome, not labeling.

> [!TIP]
> Labeler-managed labels are **re-asserted on every push**: the path labeler runs with `sync-labels: true`, so a manual override of an `area:` label (or a size label) is reverted on the next `synchronize` event. To override durably, adjust the path map in `.github/labeler.yml` (fork it via `.template-sync-ignore` if you restructure), or use labels outside the managed map - those are never touched.

### 🔗 See also

> [!TIP]
> Every canonical guide is indexed in the [&#x1F4DA; Standards Index](https://github.com/tannergolden/standards/blob/Development/docs/README.md). If you rename or move a file, update every reference to it across the repository to prevent link drift.

---

<div align="center">

**Intelligent routing. High-velocity triage.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by the Engineering Team. Distributed under the MIT License.

</div>
