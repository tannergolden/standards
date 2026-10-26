# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Every checker comes from the environment's toolchain, at the version it pins.

The checks used to install each tool their own way: typos and lychee through
their actions, gitleaks through its action and a tarball, actionlint built
with `go install`, zizmor and the self-checks' ruff and pytest from pip, and
Prettier through `npx`. Each was a version pinned here, in a different file,
that nothing held to the environment's image. Now every job that runs one
installs the toolchain through
`tannergolden/environment/.github/actions/toolchain`, naming only the part
it runs, and these keep any of the old ways from coming back.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import ROOT, load_yaml

TOOLCHAIN = "tannergolden/environment/.github/actions/toolchain@v1"

# The part of the toolchain each tool comes in.
PART = {
    "typos": "binaries",
    "lychee": "binaries",
    "gitleaks": "binaries",
    "actionlint": "binaries",
    "zizmor": "python",
    "pytest": "python",
    "ruff": "python",
    "prettier": "node",
}

# Each job that runs one of the toolchain's tools, with the step that does.
USERS = [
    (".github/workflows/ci.yml", "spelling", "📝 Check Spelling", "typos"),
    (".github/workflows/ci.yml", "link-checker", "🔗 Link Check", "lychee"),
    (".github/workflows/gitleaks.yml", "scan", "🔍 Run Gitleaks", "gitleaks"),
    (".github/workflows/lint-workflows.yml", "lint", "🔍 actionlint (Actions semantics)", "actionlint"),
    (".github/workflows/lint-workflows.yml", "lint", "🛡️ zizmor (Actions security audit)", "zizmor"),
    (".github/workflows/self-checks.yml", "tests", "🧪 pytest", "pytest"),
    (".github/workflows/self-checks.yml", "scripts", "🧹 ruff (rules from .ruff.toml)", "ruff"),
    (".github/workflows/self-checks.yml", "workflows", "🔍 actionlint (Actions semantics)", "actionlint"),
    (".github/workflows/self-checks.yml", "workflows", "🛡️ zizmor (Actions security audit)", "zizmor"),
    (".github/workflows/self-checks.yml", "data", "🎨 Formatting matches the published config", "prettier"),
]

# The ways a tool used to arrive. Any of them back in a workflow, an action,
# a test or a document is a second copy of a version, outside the
# environment's pins.
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


def anywhere() -> list:
    """Every file a contributor or a check reads a command from, but this one."""
    files = [*published(), ROOT / "Makefile"]
    files += sorted(path for path in (ROOT / "tests").glob("*.py") if path.resolve() != Path(__file__).resolve())
    files += sorted((ROOT / "docs").rglob("*.md"))
    return files


def toolchain_step(workflow: str, job: str) -> tuple[int, dict]:
    steps = load_yaml(workflow)["jobs"][job]["steps"]
    found = [(i, entry) for i, entry in enumerate(steps) if entry.get("uses") == TOOLCHAIN]
    assert found, f"{workflow}: job {job!r} runs a checker without installing the toolchain"
    return found[0]


@pytest.mark.parametrize(("workflow", "job", "step", "tool"), USERS, ids=[f"{w.split('/')[-1]}:{j}:{t}" for w, j, s, t in USERS])
def test_the_toolchain_is_installed_before_the_tool_runs(workflow, job, step, tool):
    names = [entry.get("name") for entry in load_yaml(workflow)["jobs"][job]["steps"]]
    assert step in names, f"{workflow}: job {job!r} has no step {step!r}; have {names}"
    index, _ = toolchain_step(workflow, job)
    assert index < names.index(step), f"{workflow}: {step!r} runs before the toolchain is installed"


@pytest.mark.parametrize(("workflow", "job", "step", "tool"), USERS, ids=[f"{w.split('/')[-1]}:{j}:{t}" for w, j, s, t in USERS])
def test_the_job_asks_for_the_part_its_tool_comes_in(workflow, job, step, tool):
    _, entry = toolchain_step(workflow, job)
    parts = {part.strip() for part in str(entry.get("with", {}).get("tools", "all")).split(",")}
    assert parts & {PART[tool], "all"}, f"{workflow}: job {job!r} runs {tool} but installs only {sorted(parts)}"


def test_the_jobs_people_wait_on_fetch_only_the_binaries():
    """A required check, or one every pull request runs, waits on no more hosts than its tool needs."""
    for workflow, job in ((".github/workflows/gitleaks.yml", "scan"), (".github/workflows/ci.yml", "spelling"),
                          (".github/workflows/ci.yml", "link-checker")):
        _, entry = toolchain_step(workflow, job)
        assert entry.get("with", {}).get("tools") == "binaries", f"{workflow}: job {job!r}"


@pytest.mark.parametrize("path", anywhere(), ids=lambda p: str(p.relative_to(ROOT)))
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
