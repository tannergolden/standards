<!--
title: '🗂️ REPOSITORY DATA'
description: 'Rulesets and the label taxonomy applied to a target repository, and the naming contract that keeps branch protection matching.'
tags: [rulesets, labels, branch-protection, governance]
category: docs
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 🗂️ REPOSITORY DATA

<a name="top"></a>

**Configuration applied _to_ a repository, rather than executed _in_ one.**

_Data, not logic._

</div>

---

## 💡 What This Is

Everything else in this repository runs. This folder does not: it is the state a repository is put
into. Rulesets and labels are read from here at the ref they were called at and written to a target
repository through the GitHub API, so nothing is ever copied into a consumer's tree.

That is also the line between this folder and `config/`. Anything **written to** a repository lives
here; anything **read by** a tool during a run lives in `config/`. The labeler rules are read by the
labeler action at run time, so they are configuration, not state.

| File                                         | Applied to                                             |
| :------------------------------------------- | :----------------------------------------------------- |
| `rulesets/protect-integration-branches.json` | Your default branch, plus `Experimental`/`Development` |
| `rulesets/protect-promotion-branches.json`   | `Preview` and `Release`                                |
| `rulesets/protect-release-tags.json`         | Full version tags, making published releases immutable |
| `labels.yml`                                 | The label taxonomy, create-or-update, never pruning    |

> [!NOTE]
> **These do not assume your branch names.** The first ruleset targets `~DEFAULT_BRANCH`, a ref
> selector GitHub resolves to whatever your default branch is actually called, so `main` is covered
> as surely as `Development`. The named branches alongside it are additive and match nothing in a
> repository that does not have them.

---

## ⚠️ The Check-Name Contract

> [!IMPORTANT]
> A called workflow reports its checks as **`<caller job id> / <job name>`**, not under the job name
> alone. The caller's job id is therefore part of branch protection, and renaming it silently
> detaches every required check that names it.

The rulesets here require three checks:

| Required check                  | Comes from        | Stub job id |
| :------------------------------ | :---------------- | :---------- |
| `ci / 🧪 Lint, Test & Build`    | `ci.yml`          | `ci`        |
| `secrets / 🔍 Scan for Secrets` | `gitleaks.yml`    | `secrets`   |
| `pr / ✍️ DCO Sign-Off`          | `semantic-pr.yml` | `pr`        |

So a consuming repository's stub must use exactly those job ids:

```yaml
# .github/workflows/checks.yml - the file name is free; the job ids are not
jobs:
  ci: # <- this id becomes the check-name prefix. Do not rename it.
    uses: tannergolden/standards/.github/workflows/ci.yml@v1
    secrets: inherit
```

A check that never reports is not a check that fails loudly. It is a pull request that waits
forever, which is why the job ids are fixed here rather than left to each repository.

---

## 🏷️ Version Tags Stay Movable

The tag ruleset protects `refs/tags/v*.*.*`, meaning full versions such as `v1.4.2`, and
deliberately leaves bare major tags such as `v1` unprotected.

That is not an oversight. A moving major tag is the entire mechanism behind pinning `@v1`: it has to
be re-pointed at each release, and a ruleset that made it immutable would break the pin it exists to
serve. Immutability belongs to the exact version underneath it, which is the ref anyone who wants
exactness pins instead.

---

## 🧭 Changing Anything Here

- **A ruleset change reaches every repository it is reapplied to.** Tightening a rule tightens it
  everywhere, and the repositories affected will not be the ones you were thinking about.
- **Renaming a label needs `renamed_from:`.** Without it the old label is orphaned in every
  repository that already carries it, taking its issues and pull requests out of every saved filter.
- **Label descriptions stop at 100 characters, names at 50.** The GitHub API rejects longer ones with
  a 422. [`scripts/sync-labels.sh`](../scripts/sync-labels.sh) validates the whole registry - lengths,
  duplicate names, colour format - **before** its first write, so a bad entry fails the run naming the
  offender instead of half-applying the taxonomy.
- **The sync reads before it writes.** A label already matching its declaration is left alone, so a
  no-op run makes zero API calls and reports `N unchanged`. Anything else in that summary is a real
  difference between the registry and the repository. Run it with `DRY_RUN=true` to see the plan
  first.
- **The label reference is generated.** `docs/references/Repository-Labels.md` builds its tables from
  this file via [`scripts/update-label-docs.py`](../scripts/update-label-docs.py), and `self-checks`
  fails on drift. Edit the registry and re-run the script; never edit the tables.
- **The nine GitHub stock labels are byte-identical to a new repository's.** `bug`, `documentation`,
  `duplicate`, `enhancement`, `good first issue`, `help wanted`, `invalid`, `question` and `wontfix`
  carry GitHub's own colours and descriptions, emoji-free. Restyling them would make every repository
  show a diff against a stock one for no gain; the `type:` family is where opinions belong.

---

<div align="center">

**State a repository is put into, never a file it has to keep.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
