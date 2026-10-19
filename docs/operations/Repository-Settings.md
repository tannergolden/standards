<!--
title: '⚙️ REPOSITORY SETTINGS'
description: 'The complete map of repository settings: what automation writes, what generation sets, what lives in files, and what stays deliberately manual.'
type: reference
keywords: [automation, governance, security]
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

A repository on these standards should never depend on someone remembering a checkbox. Every setting GitHub exposes falls into exactly one of five buckets: **written by 🎯 Apply Standards**, **set at generation**, **carried by a file in the tree**, **deliberately manual**, or **impossible to automate** because GitHub offers no API for it. This page is the map of all five, page by page of a repository's Settings, so "is that configured?" always has a lookup, never a shrug.

The written set itself lives in [`data/repository-settings.json`](../../data/repository-settings.json) - one value and one reason per line, applied by [`scripts/apply-settings.py`](../../scripts/apply-settings.py), which reads before it writes and previews by default. This page does not repeat those reasons; it tells you which bucket everything is in, and how a run decides.

---

## 🤖 Written by 🎯 Apply Standards

Dispatch **🎯 Apply Standards** with `apply-settings: true` (and an [`ADMIN_TOKEN`](./Branch-Protection.md#-creating-the-admin_token)). The settings file has four groups, and the run makes one plan of all of them:

| Group        | Settings                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Where GitHub shows them       |
| :----------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :---------------------------- |
| `repository` | Squash-only (`allow_squash_merge` on, merge and rebase off), the pull request title and body as the squash commit, `delete_branch_on_merge`, `allow_auto_merge`, `allow_update_branch`; `has_issues` and `has_discussions` on, `has_wiki` and `has_projects` off; `web_commit_signoff_required` on                                                                                                                                                                                                | Settings → General            |
| `actions`    | Actions on, and **no** SHA-pinning requirement (it would refuse every `@v1` composite action the stubs call); the workflow token on _Read and write_; Actions may create and approve pull requests; on a public repository, fork workflows from first-time contributors wait for approval; on a private one, fork pull requests run no workflows, get no write token and no secrets, and need approval if they ever do; outside workflows get no access to a private repository; 90-day retention | Settings → Actions → General  |
| `security`   | Secret scanning, push protection, non-provider patterns and Copilot secret scanning, each where the repository's plan has it; Dependabot alerts and security updates; private vulnerability reporting; CodeQL default setup **off**, because it disables the `codeql.yml` stub and rejects its uploads                                                                                                                                                                                            | Settings → Advanced Security  |
| `releases`   | Release immutability **off**, because `release-publish.yml` attaches the artifacts after a drafted release is published, which an immutable release refuses                                                                                                                                                                                                                                                                                                                                       | Settings → General → Releases |

Your part is the dispatch and the token - see [🙋 What You Do By Hand](../introduction/What-You-Do-By-Hand.md) for every manual step in one place. Rulesets are **not** in this list on purpose: a wrong setting is a checkbox, while a wrong ruleset blocks every merge in the repository, so branch and tag protection is a [separate job with a separate switch](./Branch-Protection.md).

### How a run decides

- **Everything is compared before it is written.** The repository object is read once; every other setting has an endpoint that reports its current value, including the Dependabot and vulnerability-reporting toggles, where GitHub answers a GET with 204 or 404. Only differences are sent, so a healthy repository plans `0 change(s)` and makes **no write at all**. Anything else in the plan is real drift, named line by line in the job's step summary.
- **A setting the repository does not report is skipped, never guessed at.** It is either newer than what the repository exposes or gated by its plan, and a write would be a guess answered with a 422.
- **The token is checked first.** The repository object says whether the token administers it; one that does not fails before anything is compared, naming `ADMIN_TOKEN` and the permission it lacks, rather than as a 403 on the first write.
- **One refused write does not abandon the rest.** Each change is sent on its own. A refusal is reported with the setting, the reason and the consequence, everything after it is still applied, the summary lists what was not, and the job fails at the end. Two refusals are warnings rather than failures: a `409`, which is the owner's or organization's policy overruling a repository setting, and a plan-gated feature GitHub turns down.

> [!NOTE]
> **A skip is not a failure.** Every gate is a fact about the repository, and the plan line says which:
>
> | Gate                  | Settings                                                                                                                                    |
> | :-------------------- | :------------------------------------------------------------------------------------------------------------------------------------------ |
> | Public only           | Fork pull request approval, private vulnerability reporting                                                                                 |
> | Private only          | The private-fork workflow policy, outside-workflow access                                                                                   |
> | Where the plan has it | Secret scanning and push protection on a private repository (Secret Protection); non-provider patterns and Copilot secret scanning anywhere |
> | Where it is available | CodeQL default setup, which needs a public repository or Code Security                                                                      |
> | Enforced by the owner | Release immutability, when an organization enforces it for every repository                                                                 |

### The drift check

Because a healthy repository plans `0 change(s)`, a dry run is a verifiable control. Pass `fail-on-drift: true` with `dry-run: true` and the settings job fails whenever anything differs, naming every setting, and still writes nothing. A scheduled dispatch of the stub with those two inputs is a weekly proof that the repository is still on the standard; the workflow also exposes the result as its `settings-drift` and `settings-changes` outputs, for a caller that wants to act on it.

```yaml
# In .github/workflows/apply-standards.yml, beside workflow_dispatch:
on:
  schedule:
    - cron: '0 8 * * 1' # Monday 08:00 UTC, after the weekly sweep: a dry run that fails on drift
jobs:
  apply:
    permissions:
      contents: read
      issues: write
    uses: tannergolden/standards/.github/workflows/apply-standards.yml@v1
    with:
      apply-labels: false
      apply-settings: true
      dry-run: true
      fail-on-drift: true
    secrets: inherit
```

### Departing from the standard

A repository that needs a different value names a file of its own with `settings-file`, in the same shape as the published one; it replaces the published set rather than layering on it, so it carries everything it wants applied. Beyond the published keys, a file may set the optional ones the script knows: an action allowlist (`allowed_actions: "selected"` under `actions.permissions`, with a `selected_actions` block), the cache limits (`cache_retention_days`, `cache_storage_limit_gb`), the two new pull request fields and `allow_forking` under `repository`, `code_security` or `advanced_security` under `security` on a repository that pays for them, and the delegated-bypass statuses. What it names is compared and written like everything else; what it misspells is refused by name, and what the script never writes - visibility, archiving, the default branch - is refused with the reason. A file written against the first published shape, with the three Actions keys flat under `actions`, is still read.

---

## 🌱 Set at Generation & Initialisation

These are correct before Apply Standards ever runs, and running it never touches them:

| Concern            | How it is set                                                                                                                                                                                                                                          |
| :----------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Default branch** | Generated repositories inherit `Development` from the template.                                                                                                                                                                                        |
| **Identity**       | `init-template.yml` rewrites the licence holder, funding target, documentation footers, issue-chooser links, and a YAML `author:`, and leaves a sealed block, such as the intelligence block in `AGENTS.md`, as it is.                                 |
| **Licence year**   | Stamped to the generation year by initialisation, then static - the year a work was fixed does not move.                                                                                                                                               |
| **Template flag**  | A repository created _from_ a template starts as an ordinary one. Making it a template of its own is the owner's choice, and [Template Sync](../distribution/automation/Template-Sync.md#-a-template-derived-from-another) keeps it following its own. |

---

## 📄 Carried by Files, Not Settings

| Concern                        | File                                                                  |
| :----------------------------- | :-------------------------------------------------------------------- |
| **Dependency update cadence**  | `.github/dependabot.yml`                                              |
| **Code scanning**              | The `codeql.yml` stub, an advanced setup; default setup stays off     |
| **Review routing**             | `.github/CODEOWNERS`                                                  |
| **Vulnerability intake**       | `SECURITY.md`                                                         |
| **Sponsorship links**          | `.github/FUNDING.yml`                                                 |
| **Issue and discussion forms** | `.github/ISSUE_TEMPLATE/`, `.github/DISCUSSION_TEMPLATE/`             |
| **Label taxonomy**             | [`data/labels.yml`](../../data/labels.yml), applied by the labels job |
| **Branch and tag protection**  | [`data/rulesets/`](../../data/rulesets/), applied by the rulesets job |

---

## 🗺️ The Complete Map

Every page of a repository's Settings, and the bucket each switch on it falls into. **Written** means the settings job writes it; **override** means the script can write it from a `settings-file` but the published set leaves it alone, for the reason in the file's `_excluded` block.

| Settings page             | Switch                                                                                                                                                            | Bucket                                                                          |
| :------------------------ | :---------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------ |
| **General**               | Name, description, website, topics                                                                                                                                | Manual: identity (override for the first three)                                 |
|                           | Social preview                                                                                                                                                    | No API                                                                          |
|                           | Wikis, Issues, Discussions, Projects                                                                                                                              | Written                                                                         |
|                           | Sponsorships                                                                                                                                                      | File: `.github/FUNDING.yml`                                                     |
|                           | Preserve this repository, Include Git LFS objects in archives                                                                                                     | No API                                                                          |
|                           | Pull requests: merge buttons, default commit message, suggest updating branches, auto-merge, auto-delete head branches                                            | Written                                                                         |
|                           | Pull requests on or off; limit pull request creation to collaborators                                                                                             | Manual: the API does not yet report them reliably (override)                    |
|                           | Pushes: limit how many branches and tags one push may update                                                                                                      | No API                                                                          |
|                           | Releases: immutability                                                                                                                                            | Written                                                                         |
|                           | Danger zone: visibility, transfer, archive, delete                                                                                                                | Manual by design, and refused in any settings file                              |
| **Moderation options**    | Interaction limits, pull request creation cap                                                                                                                     | Manual: temporary levers                                                        |
|                           | Code review limits                                                                                                                                                | No API                                                                          |
| **Collaborators**         | People and teams                                                                                                                                                  | Manual: project wiring                                                          |
| **Branches, Tags**        | Classic protection rules                                                                                                                                          | Superseded by the rulesets job                                                  |
| **Rules → Rulesets**      | Branch and tag rulesets                                                                                                                                           | Written by the [rulesets job](./Branch-Protection.md)                           |
| **Actions → General**     | Actions permissions, SHA-pinning requirement                                                                                                                      | Written (the allowlist itself: override)                                        |
|                           | Fork pull request workflows (private), approval for fork workflows (public), workflow permissions, pull request approval, retention, outside access, cache limits | Written (cache limits: override, plan-gated)                                    |
| **Actions → Runners**     | Self-hosted runners and groups                                                                                                                                    | Manual: infrastructure                                                          |
| **Webhooks**              | Hooks                                                                                                                                                             | Manual: project wiring                                                          |
| **Environments**          | Reviewers, wait timers, branch policies                                                                                                                           | Manual: reviewers are people; the first deploy creates the environment it names |
| **Codespaces**            | Prebuilds, secrets                                                                                                                                                | Manual: project wiring                                                          |
| **Pages**                 | Source, custom domain, HTTPS                                                                                                                                      | Manual: project wiring                                                          |
| **Custom properties**     | Values                                                                                                                                                            | Organization-owned repositories only                                            |
| **Advanced Security**     | Code Security, Secret Protection                                                                                                                                  | Manual: billing (override)                                                      |
|                           | Dependency graph                                                                                                                                                  | Written, as a side effect of Dependabot alerts                                  |
|                           | Automatic dependency submission, grouped security updates, Dependabot on Actions runners                                                                          | No API                                                                          |
|                           | Dependabot alerts, Dependabot security updates                                                                                                                    | Written                                                                         |
|                           | Dependabot version updates                                                                                                                                        | File: `.github/dependabot.yml`                                                  |
|                           | CodeQL default setup                                                                                                                                              | Written: off, in favour of the `codeql.yml` stub                                |
|                           | Copilot Autofix, validity checks                                                                                                                                  | No API at repository level: organization security configurations only           |
|                           | Secret scanning, push protection, non-provider patterns, Copilot secret scanning                                                                                  | Written, where the plan has them                                                |
|                           | Delegated bypass and its reviewers                                                                                                                                | Manual: reviewers are people (the status: override)                             |
|                           | Private vulnerability reporting                                                                                                                                   | Written                                                                         |
|                           | Security policy                                                                                                                                                   | File: `SECURITY.md`                                                             |
|                           | Access to alerts                                                                                                                                                  | Manual: people                                                                  |
| **Deploy keys**           | Keys                                                                                                                                                              | Manual: project wiring                                                          |
| **Secrets and variables** | Actions, Codespaces, Dependabot                                                                                                                                   | Manual: project wiring, and never in a file                                     |
| **Autolink references**   | References                                                                                                                                                        | Manual: project wiring                                                          |
| **Email notifications**   | Push notification addresses                                                                                                                                       | No API                                                                          |

---

## ✋ Deliberately Manual

Everything writable that the published set refuses to touch is listed in the settings file's own `_excluded` block, each with its reason - identity fields, visibility, archiving, billing-gated security, merge-commit wording for a merge method that is disabled, the two new pull request fields the API does not yet report reliably, and project-specific wiring like Pages, webhooks, and collaborators.

Beyond those, four are **hardening options worth doing by hand** when they fit your project:

| Hardening                                | Where                                                 | When it earns its keep                                                                                                                                                                                                                                                                                    |
| :--------------------------------------- | :---------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Environment protection for `Preview`** | Settings → Environments                               | Once deploys are real: required reviewers and a branch policy are the "Approval + Environment Protection" gate the [branch matrix](./Branch-Protection.md) names. Reviewers are people, so no shared file can set this.                                                                                   |
| **Approval for _all_ external forks**    | A `settings-file` override                            | The applied floor covers first-time contributors, and a first-time policy is satisfied by one merged typo fix. Set `fork_pr_contributor_approval: "all_external_contributors"` where workflows touch anything sensitive.                                                                                  |
| **Action allowlist**                     | A `settings-file` override                            | Real hardening with a real maintenance bill: every newly pinned action needs the list edited. The standards already pin every third-party action by commit SHA. Set `allowed_actions: "selected"` with a `selected_actions` block; never the SHA-pinning requirement, which refuses the `@v1` composites. |
| **Code Security or Secret Protection**   | Settings → Advanced Security, on a private repository | Paid per committer. Once it is on, the next run switches on every secret scanning feature and the dry run reports it; until then those lines read `SKIP` with the reason.                                                                                                                                 |

---

## 🚫 No API Exists

GitHub offers no repository-level endpoint for these, so no automation - ours or anyone's - can set them:

- **Social preview image** (Settings → General → Social preview).
- **The push policy**: limiting how many branches and tags one push may update, and with it `git push --mirror`.
- **Include Git LFS objects in archives**, and **Preserve this repository**.
- **Code review limits** under Moderation options.
- **Grouped security updates**, **automatic dependency submission** and **Dependabot on Actions runners**, under Advanced Security.
- **Copilot Autofix** and **validity checks** for secret scanning, which are set through an organization's security configurations.
- **Email notifications** for pushes, under Notifications.
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
