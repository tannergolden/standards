<!--
title: '🔄 TEMPLATE SYNC'
description: 'How a repository generated from a template keeps receiving its fixes: what syncs, how an owner opts out, how conflicts are kept, and what it never does.'
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

| Piece                       | Where                                 | Written by                                              |
| :-------------------------- | :------------------------------------ | :------------------------------------------------------ |
| The `🔄 Template Sync` stub | `.github/workflows/template-sync.yml` | The template; yours to edit or delete like any stub     |
| The list                    | `.github/template-sync`               | The template's defaults, then your choices              |
| The lock                    | `.github/template-sync.lock`          | The sync alone. Never edited by hand                    |
| The engine                  | `scripts/template-sync.py`, here      | These standards, called through `actions/template-sync` |

The engine is called, never copied, like every other piece of logic here: a fix to how syncing works
reaches every repository pinned to `@v1` on its next run.

---

## 🔁 One Sync, Step By Step

1. You dispatch **🔄 Template Sync** from the Actions tab, and the stub calls the reusable workflow.
   Nothing else starts it. Nothing runs before initialisation has finished either: a repository
   still carrying `.github/TEMPLATE_INIT` is left alone.
2. The template is fetched at the major it follows - `v1` by default - as a bare clone outside your
   working tree, so nothing of it can be committed by accident.
3. `.github/template-sync` is redrawn from the template's latest list, keeping every choice you made.
4. Every path the list keeps current is decided on its own, by a three-way merge between the
   template's version when the file last synced, the template's version now, and yours.
5. The result is committed to `chore/template-sync` and proposed as one pull request, labeled
   `automated`, which later runs update in place.
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

| The template...    | Your copy...                | Outcome                                                   |
| :----------------- | :-------------------------- | :-------------------------------------------------------- |
| changed it         | is untouched                | ✅ Updated to the template's version                      |
| changed it         | changed elsewhere           | 🔀 Merged: both changes kept                              |
| changed it         | changed the same lines      | ⚠️ Conflict: yours untouched, the template's change shown |
| changed it         | is deleted                  | 🙈 Switched off in the list, recorded, never re-created   |
| added it           | does not exist              | 🆕 Added, in your identity                                |
| added it           | already exists, different   | ⚠️ Conflict: yours untouched                              |
| removed it         | is untouched                | 🗑️ Removed                                                |
| removed it         | was changed                 | 📌 Kept, as yours from now on                             |
| moved it           | is untouched or merges      | 🚚 Moved, your changes with it                            |
| moved it           | was switched off or deleted | Stays off at the new path                                 |
| changed a workflow | -                           | ⏸️ Waits for a `BOT_ACCESS_TOKEN`, then arrives           |
| -                  | is switched off             | Never touched                                             |

**Every file keeps its own baseline** - the template version it last merged from - in the lock. A
file that did not merge keeps the baseline it had, so its change is offered again on every run until
it lands. That is why merging a sync pull request with a conflict still in it is safe: nothing is
lost, and the issue keeps the file in view.

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
- **Re-create a file you deleted**, under its old name or a new one.
- **Touch a path the template does not ship**, or one your list leaves alone.
- **Write `.github/TEMPLATE_INIT`**, whatever a list says: it would re-run initialisation.
- **Write through a symlink, outside the repository, or over a symlink or submodule of yours.**
- **Push to your branch.** It proposes; you merge.
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
pull request, and keep the issue. `BOT_ACCESS_TOKEN` is the same secret every automation pull request
here uses: a PAT with the `repo` and `workflow` scopes, or a fine-grained token with **Contents**,
**Pull requests**, **Issues** and **Workflows** write on your repository - plus **Contents** read on
the template, when the template is private.

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
| `tests/template-sync-workflow.py`   | The workflow, the action, the issue, and init writing the first lock             |

The random histories carry an **oracle that does not ask the engine**: every line is a unique token,
so "did the template's change arrive" is a set question. Each known-bad design - one baseline per
repository, no identity rewrite, reinstalling deletions, conflict markers, ignoring the list, judging
removed files by the new list - is patched in by a mutation test, and must be caught.

```bash
python3 -m pytest tests/template-sync-*.py
TEMPLATE_SYNC_SEEDS=2000 python3 -m pytest tests/template-sync-properties.py -k random_history
```

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

| Symptom                                                                 | Cause, and the fix                                                                                 |
| :---------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------- |
| "has not published `v1` yet"                                            | The template has no release. Cut one there                                                         |
| "has not been initialised yet"                                          | `.github/TEMPLATE_INIT` is still here. Let init run, or dispatch it                                |
| Workflow files keep waiting                                             | No `BOT_ACCESS_TOKEN`, or one without the workflow scope                                           |
| "Could not fetch" a private template                                    | `BOT_ACCESS_TOKEN` cannot read the template                                                        |
| A conflict is reported on every run                                     | It is waiting on you: apply the change, or put a `#` in front of the file                          |
| "says this repository syncs from X, and the workflow names Y"           | The stub's `template` input and the lock disagree. Make them agree                                 |
| The lock is refused                                                     | It was edited by hand. Restore it from history                                                     |
| "the template no longer has the version this file was last synced from" | The template's history was rewritten. Make the file match the template's version, or switch it off |

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
