# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Every checker comes from the environment's toolchain, at the version it pins.

The checks used to install each tool their own way: typos and lychee through
their actions, gitleaks through its action and a tarball, actionlint built
with `go install`, zizmor and the self-checks' ruff and pytest from pip, and
Prettier through `npx`. Each was a version pinned here, in a different file,
that nothing held to the environment image every repository's container
runs. Now every job that runs one installs the toolchain through
`tannergolden/environment/.github/actions/toolchain`, and these keep any of
the old ways from coming back.
"""

from __future__ import annotations

import pytest
from conftest import ROOT, load_yaml

TOOLCHAIN = "tannergolden/environment/.github/actions/toolchain@v1"

# Each job that runs one of the toolchain's tools, with the step that does.
USERS = [
    (".github/workflows/ci.yml", "spelling", "📝 Check Spelling"),
    (".github/workflows/ci.yml", "link-checker", "🔗 Link Check"),
    (".github/workflows/gitleaks.yml", "scan", "🔍 Run Gitleaks"),
    (".github/workflows/lint-workflows.yml", "lint", "🔍 actionlint (Actions semantics)"),
    (".github/workflows/lint-workflows.yml", "lint", "🛡️ zizmor (Actions security audit)"),
    (".github/workflows/self-checks.yml", "tests", "🧪 pytest"),
    (".github/workflows/self-checks.yml", "scripts", "🧹 ruff (rules from .ruff.toml)"),
    (".github/workflows/self-checks.yml", "workflows", "🔍 actionlint (Actions semantics)"),
    (".github/workflows/self-checks.yml", "workflows", "🛡️ zizmor (Actions security audit)"),
    (".github/workflows/self-checks.yml", "data", "🎨 Formatting matches the published config"),
]

# The ways a tool used to arrive. Any of them back in a workflow or an action
# is a second copy of a version, outside the environment's pins.
OLD_WAYS = [
    "crate-ci/typos@",
    "lycheeverse/lychee-action@",
    "gitleaks/gitleaks-action@",
    "go install github.com/rhysd/actionlint",
    "zizmor==",
    "ruff==",
    "pytest==",
    "prettier@",
    "releases/download/v${GITLEAKS_VERSION}",
]


def published() -> list:
    files = sorted((ROOT / ".github" / "workflows").glob("*.y*ml"))
    files += sorted((ROOT / ".github" / "actions").glob("*/action.y*ml"))
    files += sorted((ROOT / "actions").glob("*/action.y*ml"))
    return files


@pytest.mark.parametrize(("workflow", "job", "step"), USERS, ids=[f"{w.split('/')[-1]}:{j}:{s}" for w, j, s in USERS])
def test_the_toolchain_is_installed_before_the_tool_runs(workflow, job, step):
    steps = load_yaml(workflow)["jobs"][job]["steps"]
    names = [entry.get("name") for entry in steps]
    assert step in names, f"{workflow}: job {job!r} has no step {step!r}; have {names}"
    toolchain = [i for i, entry in enumerate(steps) if entry.get("uses") == TOOLCHAIN]
    assert toolchain, f"{workflow}: job {job!r} runs a checker without installing the toolchain"
    assert toolchain[0] < names.index(step), f"{workflow}: {step!r} runs before the toolchain is installed"


@pytest.mark.parametrize("path", published(), ids=lambda p: str(p.relative_to(ROOT)))
def test_no_tool_arrives_any_other_way(path):
    text = path.read_text(encoding="utf-8")
    for way in OLD_WAYS:
        assert way not in text, f"{path.relative_to(ROOT)} installs a checker with {way!r}, outside the toolchain"


def test_every_job_calls_the_same_release():
    refs = set()
    for path in published():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "tannergolden/environment/" in line and "uses:" in line:
                refs.add(line.split("uses:", 1)[1].split("#", 1)[0].strip())
    assert refs == {TOOLCHAIN}, f"the toolchain is called at more than one ref: {sorted(refs)}"
