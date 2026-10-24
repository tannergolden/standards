<!--
title: '🎉 INITIALISE FROM TEMPLATE'
description: 'Rewrites a generated repository''s identity to its new owner and deletes what only the template needs, once, then disables itself.'
type: index
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 🎉 INITIALISE FROM TEMPLATE

<a name="top"></a>

**Initialise From Template, called with `uses:` at the step level.**

_One `uses:` line, one job done._

</div>

---

## 💡 What This Folder Is For

[`action.yml`](action.yml) is the `init-template` composite action: rewrites a generated repository's identity to its new owner and deletes what only the template needs, once, then disables itself. Another repository calls it as `tannergolden/standards/.github/actions/init-template@v1`, and this repository's own self-checks as `./.github/actions/init-template`. It ships [`.github/scripts/init-template.py`](../../scripts/init-template.py), found beside it at `$GITHUB_ACTION_PATH`. Its inputs and outputs are documented in `action.yml` itself.

On a public repository it also deletes the issue form for vulnerability reports, `.github/ISSUE_TEMPLATE/Vulnerability-Report.yaml`, when the template shipped one. Every issue on a public repository is public, so a report filed through it would be published; private vulnerability reporting is the intake there instead, with the form the public template ships for it in `.github/VULNERABILITY_REPORT.yml`. A private repository keeps the issue form. Whether the repository is public is read from the repository object the run already fetches, or from the event that started the run when the API cannot be read; when neither says, the form stays and the run warns. The run summary and the initial commit name the deletion, as they name every other. The form's line in `.github/template-sync` stays as it was, and the first 🔄 Template Sync after it reads the absence as a deletion: it switches the line off and never brings the form back ([Template Sync](../../../docs/distribution/automation/Template-Sync.md#-the-list-githubtemplate-sync)).

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                      | Purpose                                                                                                                           |
| :------------------------- | :-------------------------------------------------------------------------------------------------------------------------------- |
| [`action.yml`](action.yml) | Rewrites a generated repository's identity to its new owner and deletes what only the template needs, once, then disables itself. |
| [`README.md`](README.md)   | This file.                                                                                                                        |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**If it ships a file, it lives here.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the terms in [LICENSE](/LICENSE).

</div>
