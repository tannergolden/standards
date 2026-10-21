<!--
title: '🧾 GENERATE SBOM'
description: 'Writes a CycloneDX or SPDX dependency inventory for any ecosystem, from the checked-out tree.'
type: index
-->

<!-- markdownlint-disable MD041 -->

<div align="center">

# 🧾 GENERATE SBOM

<a name="top"></a>

**Generate SBOM, called with `uses:` at the step level.**

_One `uses:` line, one job done._

</div>

---

## 💡 What This Folder Is For

[`action.yml`](action.yml) is the `sbom` composite action: writes a CycloneDX or SPDX dependency inventory for any ecosystem, from the checked-out tree. Another repository calls it as `tannergolden/standards/.github/actions/sbom@v1`, and this repository's own self-checks as `./.github/actions/sbom`. It ships [`.github/scripts/generate-sbom.sh`](../../scripts/generate-sbom.sh), found beside it at `$GITHUB_ACTION_PATH`. Its inputs and outputs are documented in `action.yml` itself.

---

## 📝 File Log

<!-- AUTO-INDEX:BEGIN dir=. style=log -->

| Entry                      | Purpose                                                                                       |
| :------------------------- | :-------------------------------------------------------------------------------------------- |
| [`action.yml`](action.yml) | Writes a CycloneDX or SPDX dependency inventory for any ecosystem, from the checked-out tree. |
| [`README.md`](README.md)   | This file.                                                                                    |

<!-- AUTO-INDEX:END -->

---

<div align="center">

**If it ships a file, it lives here.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by [@tannergolden](https://github.com/tannergolden). Distributed under the MIT License.

</div>
