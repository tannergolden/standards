<!--
title: '🔄 TEMPLATE SYNC'
description: 'How a repository generated from a template takes its later fixes when its owner runs the sync: what syncs, how an owner opts out, how conflicts are kept, and what it never does.'
tags: [automation, templates, sync, workflows]
category: docs
-->

<!-- markdownlint-disable MD041 -->
<div align="center">

# 🔄 TEMPLATE SYNC

<a name="top"></a>

**A generated repository that can take the template's later fixes, whenever its owner wants them.**

_On request. Per file. Merged, never overwritten. Every choice yours._

</div>

---

## 💡 What It Does

"Use this template" hands over a copy and then forgets it. Every fix the template gets afterwards -
a workflow stub, a repository script, a seeded document - would stay in the template. Template sync
carries those fixes into a generated repository as **one evolving pull request**, merged with
whatever the owner has changed, and only for the paths the owner leaves it.

> [!IMPORTANT]
> **It runs only when the owner runs it.** The stub has no schedule: the sync starts when somebody
> dispatches **🔄 Template Sync** from the Actions tab, and at no other time. A repository whose
> owner never does is never offered a change, let alone given one - the template's fixes wait,
> released and tagged, until they are wanted.

Four pieces make it up, and each has exactly one author:

| Piece                       | Where                                 | Written by                                                |
| :-------------------------- | :------------------------------------ | :-------------------------------------------------------- |
| The `🔄 Template Sync` stub | `.github/workflows/template-sync.yml` | The template; yours to edit or delete like any stub       |
| The list                    | `.github/template-sync`               | The template's defaults, then your choices                |
| The lock                    | `.github/template-sync.lock`          | Initialisation first, then the sync. Never edited by hand |
| The engine                  | `scripts/template-sync.py`, here      | These standards, called through `actions/template-sync`   |

The engine is called, never copied, like every other piece of logic here: a fix to how syncing works
reaches every repository pinned to `@v1` on its next run.

---

## 🔁 One Sync, Step By Step

1. You dispatch **🔄 Template Sync** from the Actions tab, and the stub calls the reusable workflow.
   Nothing else starts it. Nothing runs before initialisation has finished either: a repository
   still carrying `.github/TEMPLATE_INIT` is left alone.
2. The template is fetched at the major it follows - `v1` by default - as a bare clone outside your
   working tree, so nothing of it can be committed by accident. The sync is worked out on the branch
   it will be proposed against: the default branch, or the stub's `base:`.
3. `.github/template-sync` is redrawn from the template's latest list, keeping every choice you made.
4. Every path the list keeps current is decided on its own, by a three-way merge between the
   template's version when the file last synced, the template's version now, and yours.
5. The result is committed to `chore/template-sync` and proposed as one pull request, labeled
   `automated`. A later run rewrites that branch from your default branch and refreshes the pull
   request's title and description, so a squash merge records the run it merges.
6. One issue, **🔄 Template sync is waiting on you**, stays open while any file waits on you, and
   closes itself on the first run that finds nothing does.

---

## 📋 The List: `.github/template-sync`

The file names **every path the template ships**, in `.gitignore` syntax, read by git's own matcher:

```gitignore
# --- Kept current ---------------------------------------------------------
/.github/workflows/checks.yml
/docs/templates/ADR.md

# --- Yours: seeded once, never synced ------------------------------------
#/README.md
#/LICENSE

# --- Your rules ----------------------------------------------------------
!/docs/templates/**
```

| You want                                             | Do this                                                   |
| :--------------------------------------------------- | :-------------------------------------------------------- |
| To keep a file as your own                           | Put a `#` in front of its line: `#/docs/templates/ADR.md` |
| To keep your lines in a file, and take the rest      | Add `# keep mine: /path/to/file` under **Your rules**     |
| The template to update it again                      | Take the `#` away                                         |
| To stop a whole folder                               | Add `!/docs/templates/**` under **Your rules**            |
| To have a file the template left to you kept current | Take the `#` away from its line                           |
| To stop syncing altogether                           | Delete `.github/workflows/template-sync.yml`              |

How the file is read:

- **A line naming a path keeps it current. `#/path` - a hash with no space - leaves it alone.** A
  line starting `# ` is a note.
- **Your rules come last and win.** Anything you write that the template did not - a pattern, a
  negation, a note of your own - moves under **Your rules** on the next sync and stays there.
- **A deleted line reads as switched off**, and the next sync writes it back with a `#`, so the file
  always shows everything the template ships.
- **The last match wins**, exactly as in a `.gitignore`. Start every pattern with `/`, or it matches
  that name in every folder.
- **A new file the template adds arrives as a new line** in the same pull request as the file itself,
  so nothing lands unannounced.

> [!WARNING]
> **A deleted list is restored, not obeyed.** Deleting `.github/template-sync` might mean "stop", so
> the next sync writes it back with the template's defaults and syncs nothing else that run. To stop,
> delete the stub.

---

## 🔀 How Each File Is Decided

The third column is the heading the file is listed under in the pull request.

| The template...      | Your copy...                      | In the pull request                                                 |
| :------------------- | :-------------------------------- | :------------------------------------------------------------------ |
| changed it           | is untouched                      | ✅ Updated to the template's version                                |
| changed it           | changed elsewhere                 | 🔀 Merged with your changes: both kept                              |
| changed it           | changed the same lines            | ⚠️ Needs you: yours untouched, the template's change shown          |
| changed it           | changed the same lines, kept mine | 🧷 Merged, your lines kept where you both changed them              |
| added it             | does not exist                    | 🆕 Added, in your identity                                          |
| added it             | already exists, different         | ⚠️ Needs you: yours untouched                                       |
| removed it           | is untouched                      | 🗑️ Removed, as the template removed it                              |
| removed it           | was changed                       | 📌 Kept as yours after the template removed it                      |
| moved it             | is untouched or merges            | 🚚 Moved by the template, your changes with it                      |
| moved it             | was switched off or deleted       | Stays off at the new path                                           |
| -                    | is deleted                        | 🙈 Switched off, because you deleted it: recorded, never re-created |
| -                    | was deleted, and switched back on | ♻️ Switched back on and restored                                    |
| reshaped its list    | is switched off                   | ✋ Held off, as you chose: your choice is written back by name      |
| changed a workflow   | -                                 | ⏸️ Waiting on a token, until one that can write workflows exists    |
| ships an unsafe path | -                                 | ⛔ Skipped as unsafe: never written                                 |
| -                    | is switched off                   | Never touched                                                       |

**Every file keeps its own baseline** - the template version it last merged from - in the lock. A
file that did not merge keeps the baseline it had, so its change is offered again on every run until
it lands. That is why merging a sync pull request with a conflict still in it is safe: nothing is
lost, and the issue keeps the file in view.

A conflict settles once the lines the template changed read as the template has them, or once the
file is switched off. Make that change on your default branch, never on `chore/template-sync`: each
run rewrites the sync branch from the default branch, and what was committed to it goes with it.

**A line you made your own can stay yours.** A command in `checks.yml`, say, is a choice, and
switching the whole stub off to keep it would cost every later fix to the rest of it. Add a note
under **Your rules** naming the file - `# keep mine: /.github/workflows/checks.yml` - and from the
next sync on, wherever you and the template both changed the same lines, yours stand: the
template's other changes to the file still arrive, its change to your lines is shown in the pull
request and not applied, and nothing waits on you. Delete the note to be asked again. It is the
owner's alone - a note above **Your rules** is the template's and decides nothing - and it names one
file exactly, never a pattern.

**A choice survives the template reshaping its list.** When a template folds the lines for several
files into one pattern, or splits one, a file you had switched off stays off: the sync writes the
choice back by name under **Your rules** and reports it as held off.

**A machined index is never merged.** The rows inside an `AUTO-INDEX` block are
drawn from the files beside it, and a redraw re-pads every row when one longer entry arrives - so a
folder log you never touched by hand still reads as changed after you add one file. Only the prose
and markers around a block are compared and merged; the rows are yours as they stood, and once a
sync has written anything, every block in every file it keeps current is redrawn from the tree it
leaves, by the same indexer 🗂️ Machined Indexes runs. Its pull request needs no index fix after it.

**In `.gitignore`, other ignore files and `.gitattributes`, two additions in one place are kept.**
Both appending to the end of `.gitignore` is the commonest change either side makes, and git calls
it a conflict only because both landed after the same line. The template's lines go first and
yours last, so yours still win, as git reads these files; an entry both added is kept once, where
you put it. A change to a line either side started from is still a conflict, so a pattern you
deleted never comes back this way.

**A release that changes nothing you would see opens no pull request.** Forgetting a file you had
switched off, or the template redrawing only its own index rows, is bookkeeping: it is written to
the lock with the next change that matters. A file you had already brought up to date by hand is
not bookkeeping - its baseline moves, so the template's next edit to those lines merges cleanly.

> [!IMPORTANT]
> **One baseline per repository would lose changes, and only across two runs.** A run with twenty
> clean updates and one conflict gets merged; a single baseline then sits past the conflicted
> change, and no later run ever sees it again. Replaying the real history of both templates showed
> it happening in most histories that met a conflict. Per-file baselines are the fix, and the test
> suite carries a mutation test that fails if the design ever regresses.

### Your identity, not the template author's

Initialisation rewrote the template author's identity in your repository - the licence holder, the
documentation footers, the contact links. Template sync passes every template file through
**init's own function** before merging, with the identity init recorded in the lock, so a new file
arrives with your name in its footer and an unchanged one never looks like your edit. References to
repositories on the template's account - `tannergolden/standards` above all - are addresses and
stay as they are.

---

## 🛡️ What It Never Does

- **Write a conflict marker.** A conflict leaves your file byte for byte as it was.
- **Re-create a file you deleted**, under its old name or a new one - unless you take the `#` off
  its line again.
- **Go backwards.** A repository generated from a commit newer than the release it follows - between
  a merge to the template and the release after it - is told so, and changed only once the template
  releases past it.
- **Touch a path the template does not ship**, or one your list leaves alone.
- **Write `.github/TEMPLATE_INIT`**, whatever a list says: it would re-run initialisation.
- **Write through a symlink, outside the repository, or over a symlink or submodule of yours.**
- **Push to your branch.** It proposes; you merge - unless the stub sets `automerge: true`, which
  merges a sync with nothing waiting once its checks pass. A run with something waiting takes back
  any auto-merge an earlier run turned on.
- **Trust a lock it cannot validate.** A malformed lock stops the run with a sentence naming the
  problem, before anything is planned.

---

## 🔑 Tokens

| Without a `BOT_ACCESS_TOKEN`                                     | With one                         |
| :--------------------------------------------------------------- | :------------------------------- |
| Files under `.github/workflows/` wait, named in the PR and issue | They arrive like any other file  |
| The pull request cannot trigger required checks                  | CI runs on it                    |
| A **private** template cannot be fetched at all                  | It can, if the token can read it |

The default `GITHUB_TOKEN` can do everything else: read a public template, push the branch, open the
pull request - once **Allow GitHub Actions to create and approve pull requests** is on, which 🎯
Apply Standards' `apply-settings` sets - and keep the issue. `BOT_ACCESS_TOKEN` is the same secret
every automation pull request here uses: a PAT with the `repo` and `workflow` scopes, or a
fine-grained token with **Contents**, **Pull requests**, **Issues** and **Workflows** write on your
repository - plus **Contents** read on the template, when the template is private.

**What the token can do is read from the token.** A classic PAT names its scopes, so one without
`workflow` is treated like no token for workflow files: they wait, and everything else arrives. A
fine-grained token names none and is trusted to have **Workflows** write; without it, GitHub refuses
the push and the run fails, saying so.

---

## 🏷️ Versions

A template publishes releases with **🏷️ Cut Release**: `vX.Y.Z` for the version, and the moving `vX`
that generated repositories follow. Template sync follows `v1` unless the stub says otherwise:

```yaml
uses: tannergolden/standards/.github/workflows/template-sync.yml@v1
with:
  ref: 'v2'
```

A new major of a template is a breaking change to the scaffold, so it is never followed on its own:
moving `ref` is a decision. Until a template has published its first `v1`, the sync reports that
there is nothing to sync to yet and succeeds.

Every option the stub can pass, under `with:`:

| Input       | Default                                  | What it does                                                                       |
| :---------- | :--------------------------------------- | :--------------------------------------------------------------------------------- |
| `ref`       | `v1`                                     | The template tag to follow                                                         |
| `automerge` | `false`                                  | Merges the pull request once its checks pass - only when nothing in it waits       |
| `base`      | The repository's default branch          | The branch the sync is worked out on, and its pull request targets                 |
| `template`  | The lock, then GitHub's record of origin | The template, as `owner/repo`, for a repository GitHub does not know the source of |

---

## 🧪 How It Is Tested

The engine is tested here, on real git repositories, with no network:

| Suite                               | What it holds                                                                    |
| :---------------------------------- | :------------------------------------------------------------------------------- |
| `tests/template-sync-decisions.py`  | Every combination of baseline, template and owner state against six safety rules |
| `tests/template-sync-run.py`        | Each promise above, played out end to end                                        |
| `tests/template-sync-list.py`       | The list's redraw rules, and git's matcher on hostile path names                 |
| `tests/template-sync-lock.py`       | Every way a lock can be wrong, refused                                           |
| `tests/template-sync-properties.py` | Random template histories against random owners, and the bad designs they catch  |
| `tests/template-sync-edges.py`      | The cases review and real use found: edits, deletions, choices, indexes, ignores |
| `tests/template-sync-mapping.py`    | A mapped sync: relocations, replaced text, exclusions, and its own lock and list |
| `tests/template-sync-workflow.py`   | The workflow, the action, the token policy, the issue, and init's first lock     |

The random histories carry an **oracle that does not ask the engine**: every line is a unique token,
so "did the template's change arrive" is a set question. Each known-bad design - one baseline per
repository, no identity rewrite, reinstalling deletions, conflict markers, ignoring the list, judging
removed files by the new list - is patched in by a mutation test, and must be caught.

```bash
python3 -m pytest tests/template-sync-*.py
TEMPLATE_SYNC_SEEDS=2000 python3 -m pytest tests/template-sync-properties.py -k random_history
```

---

## 🗺️ A Mapping

A repository that is not generated from its template, but keeps itself in step with one by contract,
syncs through a **mapping** instead of a list: the action's `map:` input names a JSON file the
contract was written out as. `tannergolden/repo` does this with `tannergolden/path`, through its 📐
Template Parity contract. A mapping changes four things:

- **Paths and text are the contract's.** Folders are relocated, text the contract replaces - a
  footer - is replaced, and excluded paths never arrive. Nothing passes through init's identity
  rewrite: both repositories belong to the same owner.
- **It keeps its own lock**, named by the mapping, so it never touches `.github/template-sync.lock`.
- **The repository's own list is amended, not redrawn**: a file that arrives gains its line, and one
  that leaves loses it, so the list still names every file the repository ships.
- **A file deleted here is drift, not a choice.** It is reported as needing you, and its baseline
  is kept, until the contract records the difference. The issue is named after the mapping: **📐
  Template Parity Sync is waiting on you**.

---

## 🧰 For Template Authors

- **Name every file you ship in `.github/template-sync`.** The `check` job in the template's own
  `🔄 Template Sync` fails on a file the list does not name, and says which line to add.
- **Anchor every entry with `/`**, write `#/path` for a file each owner keeps, and leave
  **Your rules** empty: that section is the owner's.
- **Remove a file's line when you remove the file.** A line naming nothing fails the check.
- **Release with 🏷️ Cut Release.** Generated repositories follow the moving major, so a merge to the
  default branch reaches nobody until a release moves it.

---

## 🩺 Troubleshooting

| Symptom                                                                 | Cause, and the fix                                                                                                                                                    |
| :---------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "has not published `v1` yet"                                            | The template has no release. Cut one there                                                                                                                            |
| "has not been initialised yet"                                          | `.github/TEMPLATE_INIT` is still here. Let init run, or dispatch it                                                                                                   |
| Workflow files keep waiting                                             | No `BOT_ACCESS_TOKEN`, or a classic one without the `workflow` scope                                                                                                  |
| "Failed to push branch 'chore/template-sync'"                           | A fine-grained `BOT_ACCESS_TOKEN` without **Workflows** write, or branch protection on the branch                                                                     |
| "Could not fetch" the template                                          | `BOT_ACCESS_TOKEN` cannot read it: a private template needs read access, and an expired token fails even for a public one. Renew it, or delete it                     |
| "Could not open the pull request"                                       | Turn on **Allow GitHub Actions to create and approve pull requests**, or set a `BOT_ACCESS_TOKEN`                                                                     |
| "already holds a newer version"                                         | It was generated after the template's last release. Nothing to do until the next one                                                                                  |
| A conflict is reported on every run                                     | It is waiting on you: make the lines match the template's on your default branch, add `# keep mine: /path` for it under Your rules, or put a `#` in front of the file |
| "says this repository syncs from X, and the workflow names Y"           | The stub's `template` input and the lock disagree. Make them agree                                                                                                    |
| The lock is refused                                                     | It was edited by hand. Restore it from history                                                                                                                        |
| "the template no longer has the version this file was last synced from" | The template's history was rewritten. Make the file match the template's version, or switch it off                                                                    |

### 🔗 See also

> [!TIP]
> Every canonical guide is indexed in the [&#x1F4DA; Standards Index](../../README.md). If you
> rename or move a file, update every reference to it across the repository to prevent link drift.

---

<div align="center">

**One copy at the start. Every fix after it, when you want it. Nothing you did not choose.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
