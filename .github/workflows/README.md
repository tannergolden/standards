<!--
title: '⚙️ REUSABLE WORKFLOWS'
description: 'Every callable workflow, the stub that calls it, and what any repository needs to adopt them.'
tags: [workflows, reusable, ci-cd, adoption]
category: docs
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# ⚙️ REUSABLE WORKFLOWS

<a name="top"></a>

**Every workflow published here, and the stub that calls it.**

_Your repository holds triggers. The logic lives here._

</div>

---

## 🚀 Adopting These In Any Repository

Nothing here assumes your language, your branch names, or your account. Five things are worth
knowing before the first stub.

**1. Pin a tag.** `@v1` moves with each release in the v1 line and is the normal choice. `@v1.4.2` is
immutable. Never pin `@Development`.

**2. Three job ids are fixed.** A called workflow reports its checks as `<your job id> / <job name>`,
so branch protection depends on the id you write in your stub. If you apply the published rulesets,
use `ci`, `secrets`, and `pr`. Full explanation in [`data/README.md`](../../data/README.md).

**3. Tell CI how to build.** `ci.yml` runs your command, or a Makefile target of the same name, or
nothing. If nothing resolves it **fails on purpose**, because a check that checked nothing still
reports green to branch protection.

```yaml
jobs:
  ci:
    uses: tannergolden/standards/.github/workflows/ci.yml@v1
    with:
      lint-command: 'golangci-lint run'
      test-command: 'go test ./...'
      build-command: 'go build ./...'
```

**4. Secrets are opt-in.** Workflows that take secrets declare them optional; add `secrets: inherit`
where a workflow lists any. Without them the workflow degrades and says so rather than failing.

**5. A trigger file must live in your repository.** GitHub will not run a `workflow_call` definition
that lives somewhere else. Generating from a template installs every stub for you; adding one by
hand is a copy-paste of the `uses:` block. **🎯 Apply Standards** does not write them - it applies
labels, settings and rulesets through the API and never touches your tree. See
[Getting Them Running](#-getting-them-running).

---

## 📦 The Workflows

### Gates

| Workflow             | Job name                  | Notes                                                                     |
| :------------------- | :------------------------ | :------------------------------------------------------------------------ |
| `ci.yml`             | `🧪 Lint, Test & Build`   | Required check. Also spelling, links, dependency review                   |
| `gitleaks.yml`       | `🔍 Scan for Secrets`     | Required check. Full history                                              |
| `semantic-pr.yml`    | `✍️ DCO Sign-Off`         | Required check, plus title, branch-name and per-commit message validation |
| `lint-workflows.yml` | `🧰 Actionlint + zizmor`  | Workflows are code with credentials attached                              |
| `codeql.yml`         | `🔍 Analyze (<language>)` | Languages detected, not declared. Public repositories                     |

### Operations

| Workflow                   | Does                                                                               |
| :------------------------- | :--------------------------------------------------------------------------------- |
| `governance.yml`           | Welcomes newcomers, labels pull requests, ages out and locks threads, syncs labels |
| `auto-format.yml`          | Repairs formatting drift as a pull request. Any formatter                          |
| `issue-ops.yml`            | `/assign`, `/unassign`, `/label` slash commands                                    |
| `ci-failure-alert.yml`     | Opens an issue when a watched workflow fails, closes it on recovery                |
| `dependabot-automerge.yml` | Approves and queues patch and minor updates. Majors need a human                   |
| `apply-standards.yml`      | Writes the label taxonomy and, opt-in, the rulesets                                |
| `init-template.yml`        | Claims a generated repository for its new owner, once, then goes inert             |
| `standards-version.yml`    | Opens one issue when a newer major exists. Never edits a pin                       |

### Pruning and release

| Workflow              | Does                                                                                                                       |
| :-------------------- | :------------------------------------------------------------------------------------------------------------------------- |
| `prune.yml`           | Scheduled sweep: superseded deployments and old workflow runs                                                              |
| `prune-drafts.yml`    | Deletes every draft release. Dispatch only, deliberately separate                                                          |
| `prune-releases.yml`  | ⚠️ Deletes PUBLISHED releases a newer one supersedes. `dry-run` defaults true; `delete-tags` breaks every full-version pin |
| `prune-runs.yml`      | Deletes old workflow runs, with a day window and a recent-commit window                                                    |
| `release-notes.yml`   | Maintains one evolving draft release per branch                                                                            |
| `release-publish.yml` | Builds, packages, attests, and publishes. Attaches an SBOM                                                                 |
| `publish-package.yml` | Publishes to npm, PyPI, crates.io, or any OCI registry. Each opt-in. Containers go multi-arch natively                     |
| `preview-deploy.yml`  | Builds and deploys to a preview environment                                                                                |

> [!IMPORTANT]
> **`release-publish.yml` and `publish-package.yml` do different jobs.** The first cuts a
> GitHub Release with a tarball attached, which is the whole deliverable for a project consumed by
> tag. The second pushes to the registry people actually install from. A library needs both; a
> repository whose deliverable is a tag needs only the first.

---

## 🌿 Getting Them Running

The shared workflows cannot fire on their own. **GitHub only runs a workflow that lives in the
repository being pushed to**, so a small trigger file has to exist in yours. That file is the one
thing ever copied; everything behind the `uses:` stays here.

### The fast way

Generate your repository from the public template,
[tannergolden/path](https://github.com/tannergolden/path), and every trigger workflow arrives
installed, grouped, and pinned to `@v1`: twelve files covering the checks, governance, the release
chain, maintenance, and the standards lifecycle. The optional ones carry an `is_template` guard, so
they are silent in the template and come alive in the repository generated from it.

Then run **🎯 Apply Standards** once for the label taxonomy and, when you are ready for branch
protection, the rulesets:

```yaml
# .github/workflows/apply-standards.yml
name: '🎯 Apply Standards'
on:
  workflow_dispatch:
    inputs:
      dry-run:
        type: boolean
        default: true
permissions: {}
jobs:
  apply:
    permissions:
      contents: read # check the calling repository out when labels-file names a file in it
      issues: write # apply the label taxonomy
    uses: tannergolden/standards/.github/workflows/apply-standards.yml@v1
    with:
      dry-run: ${{ inputs.dry-run }}
    secrets: inherit
```

> [!IMPORTANT]
> **`dry-run` defaults to `true`, and it covers labels as well as settings and rulesets.** A stub
> that passes nothing therefore plans and writes nothing, on all three. That default is the right
> way round for a ruleset, which can block every merge in the repository, so the first dispatch is
> deliberately a plan. **Uncheck `dry-run` on the second dispatch to actually apply the taxonomy.**
> Every job says which it did in the run summary.

> [!WARNING]
> **The `permissions:` on a calling job is a ceiling, not a grant.** A called workflow can never
> hold more than the job that called it, so a scope missing here fails the whole run _before the
> first job starts_ - no job, no step, no log, just a run marked `startup_failure`. Leaving the
> block off does not mean "no ceiling": it means the repository's **default** token permissions
> become the ceiling, and on a repository set to read-only that silently caps every write scope.
> Every calling job therefore names the union of what the workflow it calls asks for, and the
> templates ship a `verify-stubs.yml` that proves it stays that way.

**No trigger workflow names your default branch.** A branch name written into a trigger goes stale
the instant somebody renames the branch, and the workflow then stops firing silently - no error,
just nothing. The checks resolve it at run time instead: a pull request always runs, and a direct
push runs only when the ref is the repository's own default branch, whatever it happens to be
called. That also stops a branch with an open pull request running every check twice.

### The manual way

Copy what you want from a template repository's `.github/workflows/` -
[tannergolden/path](https://github.com/tannergolden/path/tree/Development/.github/workflows) carries
the full set, already pinned to `@v1`. No token needed.

### Either way, do two things before merging

1. **Tell `checks.yml` how your project builds** via `lint-command`, `test-command`, `build-command`, or
   a Makefile with those targets. With neither, the job fails on purpose.
2. **Do not rename the job ids.** `ci`, `secrets`, and `pr` are what the rulesets expect.

---

## 🔬 Validating A Change Here

This repository publishes these workflows and calls two of them on itself, both by local path, so
nothing here resolves `@v1` against its own tree. `self-checks.yml` calls `codeql.yml`, and
`self-dependabot.yml` calls `dependabot-automerge.yml` (a separate file because a `workflow_call`
workflow has no trigger of its own and cannot call itself). In both, the workflow that runs is the
one in the diff under review, while the actions inside it resolve their published pins exactly as
they would for a consumer.

Check a change against the working tree before it ships: `actionlint` over `.github/workflows/`,
`shellcheck` over `scripts/`, `ruff` over the Python, and the generators under `scripts/` run with
`--check`. Reading the tree directly is the only way to validate a change **to** an action, since
every published path resolves a pin and would exercise the released copy rather than the diff.

---

## ⚠️ Things That Will Surprise You Once

- **A skipped required check never concludes.** It does not pass, it waits. That is why the DCO job
  has no bot skip: an all-bot pull request would deadlock instead of passing.
- **CodeQL, dependency review, and Scorecard publishing need a public repository** (or Advanced
  Security). They skip rather than fail, so a private repository does not go permanently red.
- **The default `GITHUB_TOKEN` cannot push workflow files** and cannot trigger required checks on
  pull requests it opens. Automation degrades gracefully and says which limit it hit.
- **Rulesets need an admin token.** The default token cannot write them regardless of the
  permissions a job requests.
- **`uses: ./...` does not work inside a reusable workflow.** A relative path resolves against the
  _calling_ repository's checkout, which is why every internal reference here is absolute and pinned.

---

<div align="center">

**Triggers are yours. Logic is shared. Neither is copied.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
