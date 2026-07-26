<!--
title: '🙋 WHAT YOU DO BY HAND'
description: 'Every step automation cannot take for you, in the order you meet them, from generating a repository to signing a commit.'
tags: [onboarding, setup, manual, checklist]
category: docs
-->

<!-- markdownlint-disable MD041 -->
<div align="center">

# 🙋 WHAT YOU DO BY HAND

<a name="top"></a>

**The short list of things only a person can do.**

_Everything else is already wired._

</div>

---

## 🎯 Our Strategic Intent

Almost everything here happens without you: workflows arrive by link, settings and rulesets are written by a dispatch, indexes regenerate themselves. What remains is the handful of acts that need a human - because they need a credential no workflow may hold, a decision no file can make, or a judgement about your project that no template can guess.

This is that list, in the order you meet it. If a step is not here, you should not be doing it by hand.

---

## 1️⃣ At Generation

| Step                      | Why it is yours                                                                                                                                                                                                  |
| :------------------------ | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Choose the visibility** | The toggle is on the generate form and defaults to public. It cannot be changed later without consequences - and the private template ships a proprietary licence, which does not belong on a public repository. |
| **Choose the name**       | It becomes the licence holder line, the documentation footers, and the initial commit subject.                                                                                                                   |

> [!WARNING]
> **Visibility is the one irreversible-feeling choice.** Generating the private template into a public repository publishes an "all rights reserved" licence to the world. Check the toggle before you click.

Initialisation then runs on its own: it rewrites the template author's identity to yours, stamps the licence year to the current year, removes its own sentinel, and rewrites the first commit into a Conventional Commit describing what arrived. **You do nothing.**

---

## 2️⃣ The Admin Token

Two of the three 🎯 Apply Standards jobs need a credential the built-in `GITHUB_TOKEN` can never have. Making it is yours, once:

| Field                      | Value                                                                               |
| :------------------------- | :---------------------------------------------------------------------------------- |
| **Token name**             | `apply-standards-generated-repos`                                                   |
| **Expiration**             | 30 days                                                                             |
| **Repository access**      | _Only select repositories_ → the ones generated from the templates                  |
| **Repository permissions** | **Administration: Read and write**; on a PRIVATE repository also **Contents: Read** |

Then add it to the repository as a secret named exactly `ADMIN_TOKEN`.

The full form, the paste-ready description, and why each value is what it is: [🛡️ Branch Protection → Creating the `ADMIN_TOKEN`](../operations/Branch-Protection.md#-creating-the-admin_token).

> [!IMPORTANT]
> **`Contents: Read` is not optional on a private repository.** Before writing a ruleset the run checks that every status check it will require is actually declared by a workflow here. Reading those files needs no permission when the repository is public and needs `Contents: Read` when it is not - without it the check sees nothing, assumes the worst, and refuses to apply.

---

## 3️⃣ Apply the Standards

Dispatch **🎯 Apply Standards** from the Actions tab. Settings first, protection second - a wrong setting is a checkbox, a wrong ruleset blocks every merge.

1. Run it with `apply-settings: true` and `dry-run` left **on**. Read the plan in the job summary.
2. Run it again with `dry-run` **off**.
3. Repeat for `apply-rulesets: true`.

> [!TIP]
> **The dispatch form resets its toggles if you change the branch dropdown afterwards.** Set the branch first, the toggles last, or you will get a dry run you did not ask for. The summary always states which it was.

A healthy repository re-planned in dry run reports `0 change(s)`. Anything else is real drift. What each setting is and why: [⚙️ Repository Settings](../operations/Repository-Settings.md).

---

## 4️⃣ Make CI Real

**CI fails until you do this, deliberately.** `checks.yml` ships without lint, test, or build commands, because a check that checks nothing reports green to branch protection and protects nothing.

Open `.github/workflows/checks.yml` and give it your project's real commands. Until then, a red ❌ on your first commit is the system working, not a fault.

---

## 5️⃣ Sign Your Commits

Verified commits are a repository standard, and signing is inherently local - the key must never leave your machine.

```bash
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_signing_ed25519.pub
git config --global commit.gpgsign true
```

Then register the **public** half on GitHub as a **Signing key** (Settings → SSH and GPG keys). Full walkthrough: [🌿 Git Commands](../library/Git-Commands.md).

> [!CAUTION]
> **An authentication key and a signing key are different registrations of the same file.** A key registered only for authentication will sign commits that GitHub then shows as Unverified. Register it under _Signing keys_ as well.
>
> **Check the global config, not just the repository.** A `user.signingkey` set in one clone does not exist in the next one, and a placeholder left in the global config (`YOUR_GPG_KEY_ID`) fails every signing attempt with a confusing error.

---

## 6️⃣ The Rest of the First Five Minutes

| Step                                             | Notes                                                                                                                                                       |
| :----------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Confirm `CODEOWNERS`**                         | The public template ships every rule commented out, because a rule naming an owner without write access is a GitHub error. Uncomment and name a real owner. |
| **Replace the README**                           | It describes the template, not your project.                                                                                                                |
| **Keep the account `.github` repository public** | Only for private repositories: GitHub will not serve inherited community health files from a private `.github`.                                             |

Optional hardening you may want later - environment protection, approval for all external forks, an action allowlist - is listed with the reasoning in [⚙️ Repository Settings → Deliberately Manual](../operations/Repository-Settings.md).

---

## 🚫 What You Never Do By Hand

Reach for these and you are fighting the automation, not using it:

- **Editing a workflow stub's `permissions:` or `uses:` ref.** The ceiling is verified against the release; changing it usually breaks the run at startup, with no log.
- **Copying a standard into your repository.** Follow it by link, or it goes stale the moment you paste it.
- **Updating the licence year.** It is the year of generation, and it stays there.
- **Applying rulesets or settings through the GitHub UI.** Dispatch the workflow so the repository and the published set agree.

---

### 🔗 See also

> [!TIP]
> [🛡️ Branch Protection](../operations/Branch-Protection.md) for the token and the rulesets, [⚙️ Repository Settings](../operations/Repository-Settings.md) for what gets written, [🌿 Git Commands](../library/Git-Commands.md) for signing.

---

<div align="center">

**A short list, on purpose.**

[↑ Back to Top](#top)

</div>
