<!--
title: '↪️ OLD ACTION ADDRESSES'
description: 'Forwarders that keep each composite action''s old address, tannergolden/standards/actions/<name>@v1, working until the next major version.'
type: index
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# ↪️ OLD ACTION ADDRESSES

<a name="top"></a>

**Where the actions used to live.**

_Moved, never broken._

</div>

---

## 💡 What This Folder Is For

Every composite action moved to [`.github/actions/`](../.github/actions/README.md), where every repository keeps its own. A caller pinned to `v1` may still name the old address, so each old folder keeps one `action.yml` that declares the same inputs and outputs and forwards them to the action at its new address. Point every caller at `tannergolden/standards/.github/actions/<name>@v1`: this folder goes at the next major version.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                                                   | Purpose                                                                                                                                                                 |
| :------------------------------------------------------ | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`apply-rulesets/`](apply-rulesets/README.md)           | Keeps the old address of the apply-rulesets action working for a caller pinned to v1, by forwarding every input and output to .github/actions/apply-rulesets.           |
| [`apply-settings/`](apply-settings/README.md)           | Keeps the old address of the apply-settings action working for a caller pinned to v1, by forwarding every input and output to .github/actions/apply-settings.           |
| [`check-frontmatter/`](check-frontmatter/README.md)     | Keeps the old address of the check-frontmatter action working for a caller pinned to v1, by forwarding every input and output to .github/actions/check-frontmatter.     |
| [`ci-failure-alert/`](ci-failure-alert/README.md)       | Keeps the old address of the ci-failure-alert action working for a caller pinned to v1, by forwarding every input and output to .github/actions/ci-failure-alert.       |
| [`commit-check/`](commit-check/README.md)               | Keeps the old address of the commit-check action working for a caller pinned to v1, by forwarding every input and output to .github/actions/commit-check.               |
| [`config/`](config/README.md)                           | Keeps the old address of the config action working for a caller pinned to v1, by forwarding every input and output to .github/actions/config.                           |
| [`dco-check/`](dco-check/README.md)                     | Keeps the old address of the dco-check action working for a caller pinned to v1, by forwarding every input and output to .github/actions/dco-check.                     |
| [`harden/`](harden/README.md)                           | Keeps the old address of the harden action working for a caller pinned to v1, by forwarding every input and output to .github/actions/harden.                           |
| [`init-template/`](init-template/README.md)             | Keeps the old address of the init-template action working for a caller pinned to v1, by forwarding every input and output to .github/actions/init-template.             |
| [`machined-blocks/`](machined-blocks/README.md)         | Keeps the old address of the machined-blocks action working for a caller pinned to v1, by forwarding every input and output to .github/actions/machined-blocks.         |
| [`open-pr/`](open-pr/README.md)                         | Keeps the old address of the open-pr action working for a caller pinned to v1, by forwarding every input and output to .github/actions/open-pr.                         |
| [`prune-deployments/`](prune-deployments/README.md)     | Keeps the old address of the prune-deployments action working for a caller pinned to v1, by forwarding every input and output to .github/actions/prune-deployments.     |
| [`prune-workflow-runs/`](prune-workflow-runs/README.md) | Keeps the old address of the prune-workflow-runs action working for a caller pinned to v1, by forwarding every input and output to .github/actions/prune-workflow-runs. |
| [`sbom/`](sbom/README.md)                               | Keeps the old address of the sbom action working for a caller pinned to v1, by forwarding every input and output to .github/actions/sbom.                               |
| [`setup/`](setup/README.md)                             | Keeps the old address of the setup action working for a caller pinned to v1, by forwarding every input and output to .github/actions/setup.                             |
| [`standards-version/`](standards-version/README.md)     | Keeps the old address of the standards-version action working for a caller pinned to v1, by forwarding every input and output to .github/actions/standards-version.     |
| [`sync-labels/`](sync-labels/README.md)                 | Keeps the old address of the sync-labels action working for a caller pinned to v1, by forwarding every input and output to .github/actions/sync-labels.                 |
| [`template-sync/`](template-sync/README.md)             | Keeps the old address of the template-sync action working for a caller pinned to v1, by forwarding every input and output to .github/actions/template-sync.             |
| [`update-indexes/`](update-indexes/README.md)           | Keeps the old address of the update-indexes action working for a caller pinned to v1, by forwarding every input and output to .github/actions/update-indexes.           |
| [`README.md`](README.md)                                | This file.                                                                                                                                                              |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**Call the new address. This one is on its way out.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the terms in [LICENSE](/LICENSE).

</div>
