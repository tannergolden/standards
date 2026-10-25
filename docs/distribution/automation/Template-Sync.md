<!--
title: '🔄 TEMPLATE SYNC'
description: 'How a repository generated from a template takes its later fixes when its owner runs the sync: what syncs, how an owner opts out, how conflicts are kept, and what it never does.'
type: guide
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

| Piece                       | Where                                    | Written by                                                      |
| :-------------------------- | :--------------------------------------- | :-------------------------------------------------------------- |
| The `🔄 Template Sync` stub | `.github/workflows/template-sync.yml`    | The template; yours to edit or delete like any stub             |
| The list                    | `.github/template-sync`                  | The template's defaults, then your choices                      |
| The lock                    | `.github/template-sync.lock`             | Initialisation first, then the sync. Never edited by hand       |
| The engine                  | `.github/scripts/template-sync.py`, here | These standards, called through `.github/actions/template-sync` |

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

# --- Only ever in the template -------------------------------------------
#/.github/TEMPLATE_INIT

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
- **What the template keeps for itself never arrives.** A file named under
  `# --- Only ever in the template` - the sentinel, a contract only the template is held to - was
  deleted by initialisation and has no baseline here, so no sync offers it. Its line stays,
  switched off: take the `#` away and the next sync adds it. A workflow file is the one exception:
  GitHub lets the workflow token change nothing under `.github/workflows/`, so initialisation leaves
  it in place, names it, and you delete it. No sync touches it while its line is off.
- **On a public repository the vulnerability issue form goes too.** Every issue on a public
  repository is public, so initialisation deletes `.github/ISSUE_TEMPLATE/Vulnerability-Report.yaml`
  there. Unlike a file the template keeps for itself, its line stays on and it keeps a baseline, so
  the first sync reads its absence as your deletion: it lists it under 🙈 Switched off, because you
  deleted it, writes its line back with a `#`, and never re-creates it. Take the `#` away, should the
  repository go private, and the next sync restores it.

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

**A sealed block is never merged either.** A block marked `<!-- NAME:BEGIN sha256:<hash> -->`, such
as the `INTELLIGENCE` block tannergolden/intelligence delivers into `AGENTS.md`, belongs to the
machine that sealed it, which rewrites it and its marker line on every release. So the whole block,
marker line included, is taken out of all three sides, the rest of the file merges, and the block
comes back exactly as your repository holds it. Your own sync keeps it current; Template Sync never
offers the template's copy of it, and never conflicts over it.

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
> change, and no later run ever sees it again. Replaying a template's real history showed
> it happening in most histories that met a conflict. Per-file baselines are the fix, and the test
> suite carries a mutation test that fails if the design ever regresses.

### Your identity, not the template author's

Initialisation rewrote the template author's identity in your repository - the licence holder, the
documentation footers, the contact links, and a YAML `author:` naming the template's author. Template sync
passes every template file through **init's own function** before merging, with the identity init
recorded in the lock, so a new file arrives with your name in its footer and an unchanged one never
looks like your edit. References to repositories on the template's account - `tannergolden/standards`
above all - are addresses and stay as they are, and so does everything inside a sealed block: its
words belong to the machine that sealed it.

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

| Without a `BOT_ACCESS_TOKEN`                                                 | With one                         |
| :--------------------------------------------------------------------------- | :------------------------------- |
| Files under `.github/workflows/` wait, named in the PR and issue             | They arrive like any other file  |
| The pull request's checks wait until someone with write access approves them | CI runs on it                    |
| A **private** template cannot be fetched at all                              | It can, if the token can read it |

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

| Suite                               | What it holds                                                                              |
| :---------------------------------- | :----------------------------------------------------------------------------------------- |
| `tests/template-sync-decisions.py`  | Every combination of baseline, template and owner state against six safety rules           |
| `tests/template-sync-run.py`        | Each promise above, played out end to end                                                  |
| `tests/template-sync-list.py`       | The list's redraw rules, and git's matcher on hostile path names                           |
| `tests/template-sync-lock.py`       | Every way a lock can be wrong, refused                                                     |
| `tests/template-sync-properties.py` | Random template histories against random owners, and the bad designs they catch            |
| `tests/template-sync-edges.py`      | The cases review and real use found: edits, deletions, choices, indexes, ignores           |
| `tests/template-sync-mapping.py`    | A mapped sync: relocations, replaced text, exclusions, and its own lock and list           |
| `tests/template-sync-workflow.py`   | The workflow, the action, the token policy, the issue, and init's first lock               |
| `tests/init-template-removal.py`    | What init deletes, the workflows it leaves alone, and every sync after it                  |
| `tests/init-template-visibility.py` | The vulnerability issue form init deletes from a public repository, and the syncs after it |

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
contract was written out as. A template derived from another syncs this way, through its
`.github/template-derive.json`, as the next section sets out. A mapping changes four things:

- **Paths and text are the contract's.** A folder can be relocated, text the contract replaces -
  a footer - is replaced, and excluded paths never arrive. Nothing passes through init's identity
  rewrite: both repositories belong to the same owner.
- **It keeps its own lock**, named by the mapping, so it never touches `.github/template-sync.lock`.
- **The repository's own list is amended, not redrawn**: a file that arrives gains its line, and one
  that leaves loses it, so the list still names every file the repository ships.
- **A file deleted here is drift, not a choice.** It is reported as needing you, and its baseline
  is kept, until the contract records the difference. The issue is named after the mapping, so a
  mapping named 🔄 Template Sync opens **🔄 Template Sync is waiting on you**.

---

## 🧬 A Template Derived From Another

The golden path template, the one named `path`, follows no template itself. A repository generated
from it can be made a template of its own - a vault, a kit, a service skeleton - and still take
the golden path template's fixes. It runs both jobs: its `check`
keeps its own list whole, since that list is the one its own generated repositories read, and a
dispatch of **🔄 Template Sync** syncs it from the template it came from, as a mapped sync.

- **Its derivation is a mapping**, kept in `.github/template-derive.json` in the format above, with
  `.github/template-derive.lock` as its lock and `.github/template-sync` as its own list. It
  excludes what this template removed, relocates what it moved and replaces what it reworded.
- **Every other file of the template it came from arrives**, merged with this template's own
  changes, and a file that arrives gains a line in its list copying that template's choice, so its
  own generated repositories keep it current, or leave it to their owners, as the golden path does.
- **Record its lock once**, at the commit the repository was generated from, while every file that
  template ships is still here:
  `template-sync.py lock --template OWNER/REPO --map .github/template-derive.json --template-dir DIR --ref SHA`.
  Name both files under **Only ever in the template** in its list, so nothing generated from it
  inherits them.
- **Without the mapping, a template never syncs.** An ordinary sync redraws a list from the
  template's, which would fold this template's own lines under Your rules; the sync job stops
  instead and says what to write.
- **The rest of its workflows run as they do anywhere else.** The stubs that are silent in a
  template are silent only in the golden path template, so a derived template keeps its
  checks, its governance and its maintenance. Initialisation and `release.yml` stay silent in every
  template: a template never initialises itself, and it releases with **🏷️ Cut Release**, which its
  own generated repositories follow.

---

## 🧰 For Template Authors

- **Name every file you ship in `.github/template-sync`.** The `check` job in the template's own
  `🔄 Template Sync` fails on a file the list does not name, and says which line to add.
- **Anchor every entry with `/`**, write `#/path` for a file each owner keeps, and leave
  **Your rules** empty: that section is the owner's.
- **Remove a file's line when you remove the file.** A line naming nothing fails the check.
- **Name what only the template needs under `# --- Only ever in the template`**, one file to a line,
  switched off. Initialisation deletes each of them from every generated repository, leaves them
  out of its lock and redraws every folder log from what is left; the check refuses a line there
  that is switched on or names anything but one file. It changes nothing under
  `.github/workflows/`, because GitHub refuses the workflow token any push that does: a workflow
  listed there stays, named for each owner to delete, no identity in that folder is rewritten, and
  its log is never redrawn. Keep such a workflow inert outside the template with a guard that
  names it, such as `github.event.repository.is_template && github.event.repository.name == 'path'`,
  since `is_template` is true in a derived template too. A stub any repository might adopt -
  🏷️ Cut Release, which a kit consumed by tag uses too - belongs with the owner's files instead,
  where it arrives and stays.
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

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the terms in [LICENSE](/LICENSE).

</div>
