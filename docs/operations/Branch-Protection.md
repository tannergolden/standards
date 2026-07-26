<!--
title: '📝 BRANCH PROTECTION'
description: 'Branch protection rules and the rulesets that apply them as code.'
tags: [branch-protection, rulesets, governance, security]
category: docs
-->

<!-- markdownlint-disable MD041 -->
<div align="center">

# 📝 BRANCH PROTECTION

<a name="top"></a>

**Hardening the integration line through strict policy enforcement.**

_PR-only merges. Linear history. Restricted pushes._

</div>

---

> [!TIP]
> **Branch protection is code.** The rules below ship as **three** importable rulesets in
> [`data/rulesets/`](../../data/rulesets/) and are applied through the GitHub API by
> `apply-standards.yml`, matched by name so an existing ruleset is updated rather than
> duplicated.
>
> - **`protect-integration-branches.json`** covers `Experimental` and `Development` (the working lines). Force-push is blocked for everyone **except the repository owner** (the Repository-admin role is a ruleset bypass actor), so the owner can rewrite history on those two branches - most notably to normalize the generation root commit at Day 0.
> - **`protect-promotion-branches.json`** covers `Preview` and `Release` (the promotion lines). Force-push and deletion are blocked for **everyone**: their history is immutable.
> - **`protect-release-tags.json`** covers the `v*.*.*` **tag** namespace: once minted, an exact version tag can be neither moved nor deleted, by anyone - the artifacts your users downloaded stay pointed at the commit they were built from. Creating new tags (which the release automation does) stays unrestricted, and an admin can temporarily disable the ruleset in Settings for genuine emergencies.
> - **The pattern is `v*.*.*`, not `v*`, and that is load-bearing.** A moving major tag like `v1` is *supposed* to be re-pointed at every release in its line - that is the entire mechanism by which a fix reaches consumers. `v*` would protect it too and quietly break every future release. Two dots is what separates the immutable version from the movable major.
>
> Both **branch** rulesets require green CI before any merge (status checks `🧪 Lint, Test & Build`, `🔍 Scan for Secrets`, and `✍️ DCO Sign-Off`). The DCO check runs on every PR and passes automatically for bot-authored commits, so Dependabot and sync PRs are never blocked. If you rename those CI job names, update the `required_status_checks` contexts in **both** rulesets to match. Note: on organization-owned repositories without a (free-tier) `GITLEAKS_LICENSE` secret, the secret-scan check **stays green but scans nothing** - a preflight skips gitleaks with a warning, so add the key to make the gate real.
>
> **How the rulesets arrive.** For a repository you administer, the shortest path is to run the script yourself - you already hold the rights, so there is nothing to store:
>
> ```bash
> gh auth login                                    # once
> bash scripts/apply-rulesets.sh                   # previews; changes nothing
> DRY_RUN=false bash scripts/apply-rulesets.sh     # applies
> ```
>
> Or paste each file into **Settings → Rules → Rulesets → Import a ruleset**; they are already in GitHub's import shape.
>
> To have a **workflow** do it instead, dispatch `apply-standards.yml` with `apply-rulesets: true`. That path needs an `ADMIN_TOKEN` secret, because the workflow is not you: `GITHUB_TOKEN` cannot write rulesets under any permissions, and the job fails with that explanation rather than a bare 403. See [Creating the `ADMIN_TOKEN`](#-creating-the-admin_token) for how to make one.
>
> **Either way it previews first.** A ruleset names required status checks, and a check that nothing can report leaves pull requests *pending* rather than failed - blocking every merge with no error to explain it. The script refuses to apply a ruleset whose checks no workflow in the target declares; `REQUIRE_CHECKS=false` overrides that when the workflows are arriving in the same change.

## 🎯 Our Protection Strategy

We treat our primary branch lines as sacred. By enforcing strict protection rules, we eliminate the risk of accidental regressions and ensure that our delivery pipeline remains predictable and secure.

- **No Direct Pushes**: All changes must flow through a Pull Request (PR).
- **Mandatory Validation**: CI checks must pass before the merge button is enabled.
- **Peer Review**: the shipped ruleset starts at **0 required approvals** (solo maintainers and automation PRs never deadlock); raise it to `1+` as soon as a second maintainer exists.

---

## 🏗️ Branch Governance Matrix

Reviews column = the **recommended team posture** once you have reviewers; the shipped default is `0` everywhere until you harden it.

| Branch Line                 | Intent                       | Recommended Reviews | Critical Gate                     |
| :-------------------------- | :--------------------------- | :-----------------: | :-------------------------------- |
| **`Experimental`**          | Spike sandbox / stable base. |          1          | CI Validation + Review            |
| **`Development`** (Default) | Main integration line.       |          1          | CI Validation (Lint/Test/Build)   |
| **`Preview`**               | Environmental Staging.       |          1          | Approval + Environment Protection |
| **`Release`**               | Production Truth.            |         1+          | Managerial sign-off + Tagging     |

> [!IMPORTANT]
> **Always Squash & Merge.** The rulesets enforce it: `allowed_merge_methods` is `["squash"]` on both branch rulesets, so a linear history is policy rather than etiquette.
>
> Repository *settings* are a separate matter, and initialisation does not touch them: `init-template.yml` rewrites identity, nothing more. Dispatch **🎯 Apply Standards** with `apply-settings: true` to write them, or set them by hand. Either way they are squash-only merges with the pull request title and body as the commit, head branches deleted on merge, auto-merge available, sign-off required on web edits, Issues and Discussions on, the workflow token on Read and write, and the security features on. The full list, with the reason each one is required, is [`data/repository-settings.json`](../../data/repository-settings.json), and the complete map - written, gated, file-carried, or deliberately manual - is [&#x2699;&#xFE0F; Repository Settings](./Repository-Settings.md).
>
> **Settings and rulesets are separate jobs on purpose.** A wrong setting is a checkbox; a wrong ruleset blocks every merge in the repository. Keeping them apart means turning on secret scanning cannot cost you the merge button.
>
> **Leave *Workflow permissions* on "Read and write".** Every stub declares its own ceiling, and that ceiling is capped by this setting: on "read-only" a called workflow asking for `issues: write` fails the run before any job starts, with no log to read. `apply-settings` writes this one too, and puts it back if something narrowed it.

> [!NOTE]
> **Shipped default vs. team hardening.** Both branch rulesets in `data/rulesets/` ship with `required_approving_review_count: 0` - PRs are gated on **green CI only**, so a solo maintainer is never deadlocked approving their own pull requests. The review counts in the matrix above are the **recommended team configuration**: once you have a second maintainer, raise the count (and consider `dismiss_stale_reviews_on_push` and `require_code_owner_review`) by editing the ruleset JSON before you apply it, or afterwards under **Settings → Rules → Rulesets**.

---

## ✅ The "Hardened" Checklist

**Shipped by the ruleset** (active as soon as it is applied):

- [x] **Require a Pull Request**: Direct pushes to long-lived branches are prohibited - for automation too. (One caveat: the Repository-admin bypass on the **integration** ruleset exempts the owner from _every_ rule on `Experimental`/`Development` - PR requirement included - which is what lets the owner normalize the generation root commit at Day 0; `Preview`/`Release` have no bypass actors at all.)
- [x] **Require Status Checks**: `🧪 Lint, Test & Build`, `🔍 Scan for Secrets`, and `✍️ DCO Sign-Off` must be green to merge.
- [x] **Squash-Only Merges**: Linear history; standard merge commits are disabled.
- [x] **No Deletion**: None of the four long-lived branches can be deleted.
- [x] **Force Push - owner-only on the integration line**: `Preview` and `Release` are immutable (force-push blocked for everyone). On `Experimental` and `Development` force-push is blocked for everyone **except the repository owner** (Repository-admin bypass), so the owner can rewrite history there when needed - e.g. normalizing the generation root commit at Day 0.

**Recommended team hardening** (enable as your team grows):

- [ ] **Required Approvals ≥ 1**: Raise `required_approving_review_count` in the ruleset.
- [ ] **Dismiss Stale Approvals**: New commits reset the approval state.
- [ ] **Require Review from CODEOWNERS**: Uncomment and populate `.github/CODEOWNERS` first.
- [ ] **Require Signed Commits**: Verified identity via GPG/SSH for auditability.
- [ ] **Restrict Pushes**: Only designated service accounts or release managers can write to `Release`.

---

## 🔧 Automated Setup (GH CLI)

The JSON in [`data/rulesets/`](../../data/rulesets/) is the source of truth: PR-only, squash-only, deletion blocked, required checks `🧪 Lint, Test & Build` + `🔍 Scan for Secrets` + `✍️ DCO Sign-Off`, 0 required approvals; force-push owner-only on `Experimental`/`Development` and blocked on `Preview`/`Release`.

```bash
# From a clone of the standards repository, with `gh auth login` done.
bash scripts/apply-rulesets.sh                        # preview this repo
DRY_RUN=false bash scripts/apply-rulesets.sh          # apply
TARGET_REPO=owner/name DRY_RUN=false bash scripts/apply-rulesets.sh
```

> [!WARNING]
> **Do not loop `gh api --method POST` over the files.** POST creates, so re-running gives you a second copy of every ruleset under the same name rather than updating the first. The script matches by **name** and switches to `PUT` when the name already exists, which is what makes it safe to run repeatedly - and it never deletes, so rulesets you added yourself survive.

Hardening beyond the shipped default is a settings change, not a new file - for example, raising required approvals to 1 once a second maintainer exists (edit the ruleset in **Settings → Rules → Rulesets**, or adjust `required_approving_review_count` in the JSON before importing).

---

## 🔑 Creating The `ADMIN_TOKEN`

**You only need this for the workflow path.** Running `apply-rulesets.sh` yourself
needs no token at all, because you already hold the rights. The secret exists so a
*workflow* can do it, and the workflow is not you.

**The built-in `GITHUB_TOKEN` can never do this.** Writing a ruleset requires the
repository `administration` permission, which GitHub does not grant to the built-in
token under any `permissions:` block you write. This is a platform restriction, not
a configuration mistake, which is why the job checks for the secret up front and
fails with that sentence rather than a bare `403` that reads like a bug.

### Make the token

A **fine-grained personal access token** is the right choice: it can be limited to
exactly the repositories you name and one permission, which a classic token cannot.

Go to **[Settings → Developer settings → Personal access tokens → Fine-grained
tokens](https://github.com/settings/personal-access-tokens/new)** and fill the form
exactly like this:

| Field                      | Value                                                                 |
| :------------------------- | :-------------------------------------------------------------------- |
| **Token name**             | `apply-standards-generated-repos`                                     |
| **Description**            | see below                                                             |
| **Expiration**             | **30 days**                                                           |
| **Repository access**      | *Only select repositories* → the generated repositories only          |
| **Repository permissions** | **Administration** → **Read and write**; on a PRIVATE repository also **Contents** → **Read** |

Description, which you can paste as-is:

```text
Writes repository settings and branch and tag rulesets through the Apply
Standards workflow, on repositories generated from the templates only.
Administration: Read and write, plus Contents: Read on private repositories.
Read from the ADMIN_TOKEN secret
in each repository it is applied to. Safe to revoke: settings and rulesets
already applied are unaffected, and re-applying only needs a new token.
```

**Select repositories, and select the right ones.** *All repositories* hands a token
that can rewrite branch protection to everything you own, including the templates and
the standards repository itself. Choose *Only select repositories* and pick the ones
**generated from the templates**, which are the only repositories this is ever applied
to. The templates and `standards` are never targets: a template has nothing to protect,
and the standards repository is a publisher whose settings you manage directly.

One token covering the generated repositories you actually run this against is fine,
and easier to revoke than several. Adding a repository to an existing token is a
two-click edit, so start narrow.

**Why Contents: Read, and only on a private repository.** Before writing a
ruleset the run checks that every status check it will require is actually
declared by a workflow here - a required check nothing can report leaves every
pull request pending forever. Reading those workflow files needs no permission
on a public repository and needs `Contents: Read` on a private one. Without it
the preflight sees no workflows at all and refuses to apply, which is the safe
answer to the wrong question; the run says so and names this fix.

**Why the name matters.** GitHub lists your tokens by name on one page across every
repository you own. `admin` or `token` tells you nothing six months later, when the
question is which of five credentials you can safely revoke. Naming it for the job
and the repositories it covers answers that without opening it.

**Why 30 days, and not "No expiration".** Settings and rulesets are applied once
or twice in a repository's whole life: at setup, and again if the standard changes. A
credential that can rewrite branch protection should not outlive the ten minutes of
work it was made for. If it lapses and you need it again, making another takes about
a minute, which is cheaper than carrying a permanent administration token. Choose a
longer window only if you have a scheduled job re-applying them, which nothing
here does.

A GitHub App installation token with the same permission works identically, and is
the better answer for an organisation, where a personal token ties repository
governance to one person's account.

### Store it

In the repository that will run the workflow: **Settings → Secrets and variables →
Actions → New repository secret**, named exactly `ADMIN_TOKEN`.

Store it on the repository being protected, not on the standards repository. The
stub runs in *your* repository, so that is where the secret is read from.

### Then

Dispatch **🎯 Apply Standards** with `apply-settings: true`, `apply-rulesets: true`,
and `dry-run` left **on**. Read the plans, then run it again with `dry-run` off.

> [!NOTE]
> **Labels never need this token.** Applying the taxonomy uses `issues: write` from
> the built-in token, so a repository with no `ADMIN_TOKEN` still gets its labels.
> Only the settings and rulesets jobs are gated.

> [!CAUTION]
> A token with `administration` write can change branch protection, which is the
> control everything else rests on. Scope it to the generated repositories it is
> for, give it only that permission, and revoke it at
> **[Settings → Personal access tokens](https://github.com/settings/tokens)** when
> the work is done. If it leaks, revoking it is the first move and it is instant.

---

## 🧯 Common Policy Failures

| Symptom                                                 | Probable Cause                      | Corrective Action                                                                                                       |
| :------------------------------------------------------ | :---------------------------------- | :---------------------------------------------------------------------------------------------------------------------- |
| **Merge Blocked (Out of Date)**                         | Base branch has advanced.           | Click "Update Branch" in the PR UI.                                                                                     |
| **Check Missing**                                       | CI Job name mismatch.               | Verify the job name in the YAML matches the protection context.                                                         |
| **Force push rejected on `Preview`/`Release`**          | Immutable by policy.                | Expected - promotion branches never accept force-push. Land the change through a PR.                                    |
| **Force push rejected on `Experimental`/`Development`** | Pusher is not the repository owner. | By design: only the Repository-admin (owner) bypasses non-fast-forward there. Others push a topic branch and open a PR. |

---

### 🔗 See also

> [!TIP]
> Every canonical guide is indexed in the [&#x1F4DA; Standards Index](https://github.com/tannergolden/standards/blob/Development/docs/README.md). If you rename or move a file, update every reference to it across the repository to prevent link drift.

---

<div align="center">

**Protected for integrity. Gated for scale.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by the Engineering Team. Distributed under the MIT License.

</div>
