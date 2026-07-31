<!--
title: '🔗 LINK CHECKER'
description: 'The scheduled link-integrity check for the documentation.'
tags: [links, automation, quality, documentation]
category: docs
-->

<!-- markdownlint-disable MD041 -->
<div align="center">

# 🔗 LINK CHECKER

<a name="top"></a>

**Hardening the documentation graph through automated path verification.**

_Relative Path Integrity. External Status Verification. Scheduled Maintenance._

</div>

---

## 🎯 Our Content Strategy

As a repository increases in complexity, documentation cross-references often drift and break. Our Link Checker automation acts as a quality gate, ensuring that the "these standards" documentation map remains reliable and navigable.

- **Internal Integrity**: Validates that all relative paths point to active markdown files.
- **External Reliability**: Verifies that third-party URLs return an accepted status (2xx, plus allow-listed `403`/`429` for bot-hostile-but-alive sites).
- **Proactive Audits**: Regular weekly scans identify broken links before they are discovered by users.

---

## 🚀 Execution & Triggers

The validation engine runs in three modes:

1. **Continuous**: As a job inside `checks.yml`, it scans on every push and pull request to the long-lived branches.
2. **Scheduled Scan**: Every Sunday at 03:00 UTC it audits the whole repository, catching external links that rotted since the last change.
3. **Manual Override**: Triggerable via the **Actions** tab for instant verification after major documentation rewrites.

---

## ⚙️ Configuration Details

The pipeline utilizes the `lycheeverse/lychee-action` and is orchestrated within the repository's CI/CD layer.

| Setting            | Value                          | Purpose                                                                                                                                     |
| :----------------- | :----------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------ |
| **Workflow**       | `.github/workflows/checks.yml` | Execution logic and reporting.                                                                                                              |
| **Scope**          | `.`                            | Recursive scan of all files.                                                                                                                |
| **Exclusions**     | Set in `config/lychee.toml`    | Self-referential badge raw URLs, GitHub `commit`/`tree`/`blob` deep links, localhost/example hosts, Liquid placeholders, and build folders. |
| **Failure Policy** | **Advisory** (`fail: false`)   | Findings surface in the job summary without blocking CI. Pass `fail-on-broken-links: true` from your stub to make it a hard gate.           |

---

## 🧯 Troubleshooting Failures

If the Link Checker job reports a failure, follow this resolution protocol:

1. **Check Logs**: Inspect the GitHub Action output to identify the specific file and line number.
2. **Internal Path**: If the link is a relative path, ensure the target file exists and the casing is correct.
3. **External URL**: If a remote site is down, update the link or remove it.
4. **False Positives**: `403`/`429` responses are already accepted globally. For a site that fails in another bot-hostile way (e.g. LinkedIn's `999`, or persistent timeouts), add an exclude pattern to `config/lychee.toml` - the workflow deliberately keeps no ignore list of its own.

> [!CAUTION]
> Do not ignore internal links. Internal relative paths must always be accurate to preserve the repository's documentation graph.

### 🔗 See also

> [!TIP]
> Every canonical guide is indexed in the [&#x1F4DA; Standards Index](https://github.com/tannergolden/standards/blob/Development/docs/README.md). If you rename or move a file, update every reference to it across the repository to prevent link drift.

---

<div align="center">

**Navigable content. Verified connections.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by the Engineering Team. Distributed under the MIT License.

</div>
