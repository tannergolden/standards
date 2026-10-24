<!--
title: '📝 BRANCH PROTECTION'
description: 'Branch protection rules and the rulesets that apply them as code.'
type: standard
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
> - **`protect-release-tags.json`** covers the `v*.*.*` **tag** namespace: once minted, an exact version tag can never be moved by a push, by anyone, so what it resolved yesterday it resolves today. It can be deleted, because `release.yml` prunes every version but the latest after each release, and creating tags stays unrestricted, because the release automation creates them. Together those leave one way round the rule: a tag deleted and created again can name another commit. So anyone who wants a pin that outlives the next release, or that nothing can re-point, pins a commit SHA. An admin can temporarily disable the ruleset in Settings for genuine emergencies.
> - **The pattern is `v*.*.*`, not `v*`, and that is load-bearing.** A moving major tag like `v1` is _supposed_ to be re-pointed at every release in its line - that is the entire mechanism by which a fix reaches consumers. `v*` would protect it too and quietly break every future release. Two dots is what separates the version, never re-pointed, from the movable major.
>
> Both **branch** rulesets require green CI before any merge (status checks `🧪 Lint, Test & Build`, `🔍 Scan for Secrets`, and `✍️ DCO Sign-Off`). The DCO check runs on every PR and passes automatically for bot-authored commits, so Dependabot and sync PRs are never blocked. If you rename those CI job names, update the `required_status_checks` contexts in **both** rulesets to match. Every stub behind those checks in the template also triggers on `merge_group`, so a merge queue gets a result from each: CI runs in full on the group, and the secret scan and the DCO check skip there, which GitHub reports as passing. Note: on organization-owned repositories without a (free-tier) `GITLEAKS_LICENSE` secret, the secret-scan check **stays green but scans nothing** - a preflight skips gitleaks with a warning, so add the key to make the gate real.
>
> **How the rulesets arrive.** For a repository you administer, the shortest path is to run the script yourself - you already hold the rights, so there is nothing to store:
>
> ```bash
> gh auth login                                    # once
> bash .github/scripts/apply-rulesets.sh                   # previews; changes nothing
> DRY_RUN=false bash .github/scripts/apply-rulesets.sh     # applies
> ```
>
> Or paste each file into **Settings → Rules → Rulesets → Import a ruleset**; they are already in GitHub's import shape.
>
> To have a **workflow** do it instead, dispatch `apply-standards.yml` with `apply-rulesets: true`. That path needs an `ADMIN_TOKEN` secret, because the workflow is not you: `GITHUB_TOKEN` cannot write rulesets under any permissions, and the job fails with that explanation rather than a bare 403. See [Creating the `ADMIN_TOKEN`](#-creating-the-admin_token) for how to make one.
>
> **Either way it previews first.** A ruleset names required status checks, and a check that nothing can report leaves pull requests _pending_ rather than failed - blocking every merge with no error to explain it. The script refuses to apply a ruleset whose checks no workflow in the target declares; `REQUIRE_CHECKS=false` overrides that when the workflows are arriving in the same change.

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
> Repository _settings_ are a separate matter, and initialisation does not touch them: `init-template.yml` rewrites identity and deletes what only the template needs, and on a public repository the vulnerability issue form, nothing more. Dispatch **🎯 Apply Standards** with `apply-settings: true` to write them, or set them by hand. Either way they are squash-only merges with the pull request title and body as the commit, head branches deleted on merge, auto-merge available, sign-off required on web edits, Issues and Discussions on, every Actions policy under Settings → Actions → General, the security features on where the plan has them, and release immutability off. The full list, with the reason each one is required, is [`data/repository-settings.json`](../../data/repository-settings.json), and the complete map - written, gated, file-carried, or deliberately manual - is [&#x2699;&#xFE0F; Repository Settings](./Repository-Settings.md).
>
> **Settings and rulesets are separate jobs on purpose.** A wrong setting is a checkbox; a wrong ruleset blocks every merge in the repository. Keeping them apart means turning on secret scanning cannot cost you the merge button.
>
> **_Workflow permissions_ stay read-only.** That is GitHub's default for a new repository, and it is only the token a job gets when it declares no permissions. It caps nothing that does: a `permissions:` key in a workflow sets the token for its job whatever the default says, and every stub names the permissions each of its jobs needs. So read-only costs the stubs nothing, and protects a workflow that forgets the key. `apply-settings` writes this one too, and puts it back if something widened it.

> [!NOTE]
> **Shipped default vs. team hardening.** Both branch rulesets in `data/rulesets/` ship with `required_approving_review_count: 0` - PRs are gated on **green CI only**, so a solo maintainer is never deadlocked approving their own pull requests. The review counts in the matrix above are the **recommended team configuration**: once you have a second maintainer, raise the count (and consider `dismiss_stale_reviews_on_push` and `require_code_owner_review`) by editing the ruleset JSON before you apply it, or afterwards under **Settings → Rules → Rulesets**.
>
> **Raise it together with one setting.** `apply-settings` turns on **Allow GitHub Actions to create and approve pull requests**, because with it the built-in token opens the pull requests of auto-format, auto-index and template sync, and approves Dependabot's. At 0 required approvals an approval from a workflow decides nothing. At 1 or more it is a way around review: a workflow can approve a pull request in a reviewer's place. So when you raise the count, turn the setting off with `can_approve_pull_request_reviews: false` in a [`settings-file` override](./Repository-Settings.md#departing-from-the-standard), and add a `BOT_ACCESS_TOKEN`, also as a Dependabot secret, which those workflows use instead. Any workflow that a collaborator with write access pushes can read that secret, and an approval it gives counts as its account's, so make it a machine account's token rather than a maintainer's, require review from code owners, and keep that account out of `.github/CODEOWNERS`, so its approval never satisfies the rule.

---

## ✅ The "Hardened" Checklist

**Shipped by the ruleset** (active as soon as it is applied):

- [x] **Require a Pull Request**: Direct pushes to long-lived branches are prohibited - for automation too. (One caveat: the Repository-admin bypass on the **integration** ruleset exempts the owner from _every_ rule on `Experimental`/`Development` - PR requirement included - which is what lets the owner normalize the generation root commit at Day 0; `Preview`/`Release` have no bypass actors at all.)
- [x] **Require Status Checks**: `🧪 Lint, Test & Build`, `🔍 Scan for Secrets`, and `✍️ DCO Sign-Off` must be green to merge.
- [x] **Squash-Only Merges**: Linear history; standard merge commits are disabled.
- [x] **No Deletion**: None of the four long-lived branches can be deleted.
- [x] **Force Push - owner-only on the integration line**: `Preview` and `Release` are immutable (force-push blocked for everyone). On `Experimental` and `Development` force-push is blocked for everyone **except the repository owner** (Repository-admin bypass), so the owner can rewrite history there when needed - e.g. normalizing the generation root commit at Day 0.

**Recommended team hardening** (enable as your team grows):

- [ ] **Required Approvals ≥ 1**: Raise `required_approving_review_count` in the ruleset, and in the same change turn off Actions' pull request approval, with a machine account's `BOT_ACCESS_TOKEN` in its place and code owner review required (see the note above).
- [ ] **Dismiss Stale Approvals**: New commits reset the approval state.
- [ ] **Require Review from CODEOWNERS**: Uncomment and populate `.github/CODEOWNERS` first.
- [ ] **Require Signed Commits**: Verified identity via GPG/SSH for auditability.
- [ ] **Restrict Pushes**: Only designated service accounts or release managers can write to `Release`.

---

## 🔧 Automated Setup (GH CLI)

The JSON in [`data/rulesets/`](../../data/rulesets/) is the source of truth: PR-only, squash-only, deletion blocked, required checks `🧪 Lint, Test & Build` + `🔍 Scan for Secrets` + `✍️ DCO Sign-Off`, 0 required approvals; force-push owner-only on `Experimental`/`Development` and blocked on `Preview`/`Release`.

```bash
# From a clone of the standards repository, with `gh auth login` done.
bash .github/scripts/apply-rulesets.sh                        # preview this repo
DRY_RUN=false bash .github/scripts/apply-rulesets.sh          # apply
TARGET_REPO=owner/name DRY_RUN=false bash .github/scripts/apply-rulesets.sh
```

> [!WARNING]
> **Do not loop `gh api --method POST` over the files.** POST creates, so re-running gives you a second copy of every ruleset under the same name rather than updating the first. The script matches by **name** and switches to `PUT` when the name already exists, which is what makes it safe to run repeatedly - and it never deletes, so rulesets you added yourself survive.

Hardening beyond the shipped default is a settings change, not a new file - for example, raising required approvals to 1 once a second maintainer exists (edit the ruleset in **Settings → Rules → Rulesets**, or adjust `required_approving_review_count` in the JSON before importing).

---

## 🔑 Creating The `ADMIN_TOKEN`

**You only need this for the workflow path.** Running `apply-rulesets.sh` yourself
needs no token at all, because you already hold the rights. The secret exists so a
_workflow_ can do it, and the workflow is not you.

**The built-in `GITHUB_TOKEN` can never do this.** Writing a ruleset requires the
repository `administration` permission, which GitHub does not grant to the built-in
token under any `permissions:` block you write. This is a platform restriction, not
a configuration mistake, which is why the job checks for the secret up front and
fails with that sentence rather than a bare `403` that reads like a bug.

> [!TIP]
> Making this token is one of only a handful of things you do by hand. The
> whole list, in the order you meet it, is
> [🙋 What You Do By Hand](../introduction/What-You-Do-By-Hand.md).

### Make the token

A **fine-grained personal access token** is the right choice: it carries exactly the
permissions you grant it and reaches only the repositories of the one owner you pick,
which a classic token cannot. A classic token with the `repo` scope can push code to
every repository you can reach, in your account and in every organisation you belong to.

Go to **[Settings → Developer settings → Personal access tokens → Fine-grained
tokens](https://github.com/settings/personal-access-tokens/new)** and fill the form
exactly like this:

| Field                      | Value                                                                 |
| :------------------------- | :-------------------------------------------------------------------- |
| **Token name**             | `apply-standards`                                                     |
| **Description**            | see below                                                             |
| **Resource owner**         | Your account, the owner of the repositories that hold the stub        |
| **Expiration**             | **7 days**                                                            |
| **Repository access**      | **All repositories**                                                  |
| **Repository permissions** | **Administration** → **Read and write**; **Contents** → **Read-only** |
| **Account permissions**    | None                                                                  |

GitHub adds **Metadata** → **Read-only** by itself, and every other permission stays at
**No access**. [This link](https://github.com/settings/personal-access-tokens/new?name=apply-standards&expires_in=7&administration=write&contents=read)
opens the form with the name, the expiration and both permissions filled in, which
leaves the description and the repository access to you.

Description, which you can paste as-is:

```text
Writes repository settings and branch and tag rulesets through the Apply Standards workflow. Reaches all repositories, and is read from the ADMIN_TOKEN secret in each one that holds the Apply Standards stub. Administration: Read and write, plus Contents: Read for private repositories. Safe to revoke: settings and rulesets already applied are unaffected, and re-applying only needs a new token.
```

**Choose All repositories.** One token then reaches every repository that holds the
stub, including any you generate after making it, so the token never needs editing:
a new repository needs only its secret. It reaches everything else you own as well,
`standards` and the templates included, and nothing there can read it, because a
workflow reads only the secrets stored in its own repository and this one is stored
only where the stub runs. What keeps that reach safe is everything else here: two
permissions, seven days, and revoking it the moment the work is done.

**Why Contents: Read.** Before writing a ruleset the run checks that every status
check it will require is actually declared by a workflow here - a required check
nothing can report leaves every pull request pending forever. Reading those workflow
files needs no permission on a public repository and needs `Contents: Read` on a
private one, and _All repositories_ takes in every private repository you own.
Without it the preflight sees no workflows at all and refuses to apply, which is the
safe answer to the wrong question; the run says so and names this fix.

**Why the name matters.** GitHub lists your tokens by name on one page across every
repository you own. `admin` or `token` tells you nothing six months later, when the
question is which of five credentials you can safely revoke. Naming it for the
workflow that reads it answers that without opening it.

**Why 7 days, and not "No expiration".** Settings and rulesets are applied once or
twice in a repository's whole life: at setup, and again if the standard changes. A
credential that can rewrite branch protection on every repository you own should not
outlive the work it was made for, and seven days covers that work with room to spare:
a dry run everywhere, reading the plans, and the real run. If it lapses and you need
it again, making another takes about a minute, which is cheaper than carrying a
permanent administration token. Choose a longer window only if you have a scheduled
job re-applying them, which nothing here does.

A GitHub App installation token with the same permission works identically, and is
the better answer for an organisation, where a personal token ties repository
governance to one person's account.

### Store it

In each repository that holds the stub: **Settings → Secrets and variables →
Actions → New repository secret**, named exactly `ADMIN_TOKEN`. It is the same token
in every one of them. A personal account has no Actions secret its repositories can
share, so each keeps its own copy, and when the token expires its replacement goes
into each of them the same way.

Store it on the repositories being protected, never on the standards repository or a
template: neither is a target. A template has nothing to protect, and the standards
repository is a publisher whose settings you manage directly. The stub runs in _your_
repository, so that is where the secret is read from.

### Then

Dispatch **🎯 Apply Standards** with `apply-settings: true`, `apply-rulesets: true`,
and `dry-run` left **on**. Read the plans, then run it again with `dry-run` off.

> [!NOTE]
> **Labels never need this token.** Applying the taxonomy uses `issues: write` from
> the built-in token, so a repository with no `ADMIN_TOKEN` still gets its labels.
> Only the settings and rulesets jobs are gated.

> [!CAUTION]
> A token with `administration` write can change branch protection, which is the
> control everything else rests on, and with _All repositories_ it can do that on
> every repository you own. Give it only the permissions above, store it only where
> the stub runs, and revoke it at
> **[Settings → Personal access tokens](https://github.com/settings/personal-access-tokens)**
> when the work is done rather than waiting out its seven days. If it leaks, revoking
> it is the first move and it is instant.

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

Built with ❤️ by the Engineering Team. Distributed under the terms in [LICENSE](/LICENSE).

</div>
