# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""A release carries the licence its assets were released under.

`📦 Package Artifacts` attached a build tarball, a README and an SBOM, and
no licence. A tarball holds the build output alone, and the licence in git
can change after a release, so a downloaded asset said nothing about the
terms it came under. OpenSSF's baseline, OSPS-LE-03.02, asks for the licence
in a LICENSE or COPYING file beside the release assets.

These run the step that ships against a scratch repository.
"""

from __future__ import annotations

import pytest
from conftest import workflow_step_shell

WORKFLOW = ".github/workflows/release-publish.yml"
SETTINGS = {"TAG_NAME": "v1.2.3", "ARTIFACT_PATH": "dist", "SBOM_FORMAT": "spdx-json"}


def package(run_shell, repo, files: dict):
    for name, text in files.items():
        (repo / name).write_text(text, encoding="utf-8")
    shell = workflow_step_shell(WORKFLOW, "release", "package")
    return run_shell(shell, cwd=repo, env=SETTINGS)


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / "repo"
    path.mkdir()
    return path


class TestTheLicenceTravelsWithTheAssets:
    @pytest.mark.parametrize("name", ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"])
    def test_the_licence_file_is_attached_under_its_own_name(self, run_shell, repo, name):
        result = package(run_shell, repo, {name: "MIT License\n"})
        assert result.returncode == 0, result
        assert (repo / "release" / name).read_text(encoding="utf-8") == "MIT License\n"

    def test_only_one_is_attached_when_several_exist(self, run_shell, repo):
        result = package(run_shell, repo, {"LICENSE": "MIT\n", "COPYING": "GPL\n"})
        assert result.returncode == 0, result
        assert (repo / "release" / "LICENSE").exists()
        assert not (repo / "release" / "COPYING").exists()

    def test_a_repository_without_one_still_releases(self, run_shell, repo):
        result = package(run_shell, repo, {})
        assert result.returncode == 0, result
        assert not any(p.name.startswith(("LICENSE", "COPYING")) for p in (repo / "release").iterdir())


class TestTheReadmeStillTravelsClean:
    def test_internal_blocks_are_stripped_from_the_attached_copy(self, run_shell, repo):
        readme = "# Kit\n<!-- internal:start -->\nsecret plans\n<!-- internal:end -->\nUse it.\n"
        result = package(run_shell, repo, {"README.md": readme})
        assert result.returncode == 0, result
        attached = (repo / "release" / "README.md").read_text(encoding="utf-8")
        assert "secret plans" not in attached
        assert "Use it." in attached
