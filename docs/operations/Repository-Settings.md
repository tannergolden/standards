<!--
title: '⚙️ REPOSITORY SETTINGS'
description: 'The complete map of repository settings: what automation writes, what generation sets, what lives in files, and what stays deliberately manual.'
tags: [settings, automation, governance, security]
category: docs
-->

<!-- markdownlint-disable MD041 -->
<div align="center">

# ⚙️ REPOSITORY SETTINGS

<a name="top"></a>

**Every setting is either written by automation or listed here with a reason.**

_Absence is a decision. Never an oversight._

</div>

---

## 🎯 Our Strategic Intent

A repository on these standards should never depend on someone remembering a checkbox. Every setting GitHub exposes falls into exactly one of five buckets: **written by 🎯 Apply Standards**, **set at generation**, **carried by a file in the tree**, **deliberately manual**, or **impossible to automate** because GitHub offers no API for it. This page is the map of all five, so "is that configured?" always has a lookup, never a shrug.

The written set itself lives in [`data/repository-settings.json`](../../data/repository-settings.json) - one value and one reason per line, applied by [`scripts/apply-settings.sh`](../../scripts/apply-settings.sh), which reads before it writes and previews by default. This page does not repeat those reasons; it tells you which bucket everything is in.

---

## 🤖 Written by 🎯 Apply Standards

Dispatch **🎯 Apply Standards** with `apply-settings: true` (and an [`ADMIN_TOKEN`](./Branch-Protection.md#-creating-the-admin_token)). Four endpoint groups, one plan:

| Group                  | Settings                                                                                                                                                                           | Where GitHub shows them            |
| :--------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :--------------------------------- |
| **Merge policy**       | Squash-only (`allow_squash_merge` on, merge and rebase off), pull request title and body as the squash commit, `delete_branch_on_merge`, `allow_auto_merge`, `allow_update_branch` | Settings → General → Pull Requests |
| **Community surfaces** | `has_issues` and `has_discussions` on, `has_wiki` and `has_projects` off, `web_commit_signoff_required` on                                                                         | Settings → General → Features      |
| **Actions policy**     | Workflow token on _Read and write_, Actions may create and approve pull requests, fork workflows from first-time contributors wait for approval                                    | Settings → Actions → General       |
| **Security features**  | Secret scanning + push protection + non-provider patterns, Dependabot alerts + security updates, private vulnerability reporting                                                   | Settings → Advanced Security       |

Rulesets are **not** in this list on purpose: a wrong setting is a checkbox, while a wrong ruleset blocks every merge in the repository, so branch and tag protection is a [separate job with a separate switch](./Branch-Protection.md).

> [!NOTE]
> **A skip is not a failure.** Some security features are gated by visibility or plan - secret scanning needs Advanced Security on a private repository, private vulnerability reporting and the fork pull request approval policy are public-only, non-provider patterns need Secret Protection. The script detects each case and reports `SKIP` with the reason, because a repository that cannot have a feature has not misconfigured anything.

The run is **idempotent and verifiable**: dispatch it again with `dry-run: true` and a healthy repository plans `0 change(s)`. Anything else in that plan is real drift, named line by line in the job's step summary.

---

## 🌱 Set at Generation & Initialisation

These are correct before Apply Standards ever runs, and running it never touches them:

| Concern            | How it is set                                                                                                    |
| :----------------- | :--------------------------------------------------------------------------------------------------------------- |
| **Default branch** | Generated repositories inherit `Development` from the template.                                                  |
| **Identity**       | `init-template.yml` rewrites the licence holder, funding target, documentation footers, and issue-chooser links. |
| **Licence year**   | Stamped to the generation year by initialisation, then static - the year a work was fixed does not move.         |
| **Template flag**  | Repositories created _from_ a template are never templates themselves; `is_template` needs no correction.        |

---

## 📄 Carried by Files, Not Settings

| Concern                        | File                                                                  |
| :----------------------------- | :-------------------------------------------------------------------- |
| **Dependency update cadence**  | `.github/dependabot.yml`                                              |
| **Review routing**             | `.github/CODEOWNERS`                                                  |
| **Vulnerability intake**       | `SECURITY.md`                                                         |
| **Sponsorship links**          | `.github/FUNDING.yml`                                                 |
| **Issue and discussion forms** | `.github/ISSUE_TEMPLATE/`, `.github/DISCUSSION_TEMPLATE/`             |
| **Label taxonomy**             | [`data/labels.yml`](../../data/labels.yml), applied by the labels job |
| **Branch and tag protection**  | [`data/rulesets/`](../../data/rulesets/), applied by the rulesets job |

---

## ✋ Deliberately Manual

Everything writable that the automation refuses to touch is listed in the settings file's own `_excluded` block, each with its reason - identity fields, visibility, archiving, billing-gated security, merge-commit wording for a merge method that is disabled, and project-specific wiring like Pages, webhooks, and collaborators.

Beyond those, four are **hardening options worth doing by hand** when they fit your project:

| Hardening                                | Where                        | When it earns its keep                                                                                                                                                                                                  |
| :--------------------------------------- | :--------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Environment protection for `Preview`** | Settings → Environments      | Once deploys are real: required reviewers and a branch policy are the "Approval + Environment Protection" gate the [branch matrix](./Branch-Protection.md) names. Reviewers are people, so no shared file can set this. |
| **Approval for _all_ external forks**    | Settings → Actions → General | The applied floor covers first-time contributors; raise it via a `settings-file` override (`fork_pr_approval_policy: "all_external_contributors"`) where workflows touch anything sensitive.                            |
| **Action allowlist**                     | Settings → Actions → General | Real hardening with a real maintenance bill; the standards already pin every action by commit SHA.                                                                                                                      |
| **Copilot secret scanning**              | Settings → Advanced Security | Plan-gated AI detection of unstructured secrets; enable where your plan includes it.                                                                                                                                    |

---

## 🚫 No API Exists

GitHub offers no endpoint for these, so no automation - ours or anyone's - can set them:

- **Social preview image** (Settings → General → Social preview).
- **Discussion category curation** beyond what the shipped discussion forms define.
- **Personal notification and watch behaviour**, which is per-user, not per-repository.

---

### 🔗 See also

> [!TIP]
> [🛡️ Branch Protection](./Branch-Protection.md) covers the rulesets half and the `ADMIN_TOKEN` both halves share; [🔒 Security & Secrets](./Security-&-Secrets.md) covers what the security features are _for_.

---

<div align="center">

**Configured by machine. Explained to humans.**

[↑ Back to Top](#top)

</div>
