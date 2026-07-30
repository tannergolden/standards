# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The Conventional Commit type list is encoded five times, not three.

`check-type-parity.py` exists because the list "sits in three copies in
three languages, so drift would be silent and would show up as a commit that
passes one gate and fails another". It compared three:
`scripts/commit-check.py`, `config/commitlint.config.js`, and the
`commit-types` input default in `semantic-pr.yml`.

There are two more, and one of them is the most consequential of the lot:

  semantic-pr.yml `types:`          the PR TITLE gate. The title becomes the
                                    squash commit, and semantic-pr.yml calls
                                    it "the only gate keeping a banned em
                                    dash out of history".
  actions/commit-check/action.yml   the action's own `types` default, used
                                    by anyone calling the action directly.

So adding a type to the three checked places passed parity, and then a pull
request titled with it failed the required title check. The exact failure
the script was written to prevent, in the copy it did not read.
"""

from __future__ import annotations

from conftest import ROOT, load_script

parity = load_script("scripts/check-type-parity.py")

EXPECTED_SOURCES = {
    "scripts/commit-check.py",
    "config/commitlint.config.js",
    ".github/workflows/semantic-pr.yml",
    ".github/workflows/semantic-pr.yml:title-types",
    "actions/commit-check/action.yml",
}


class TestEveryEncodingIsCompared:
    def test_all_five_are_read(self):
        assert set(parity.SOURCES) == EXPECTED_SOURCES, (
            "the parity check does not cover every encoding of the type list"
        )

    def test_each_pattern_still_matches_its_file(self):
        """A pattern that stopped matching would make the check vacuous; the
        script already treats that as an error, and this proves it does."""
        for rel, (pattern, parse) in parity.SOURCES.items():
            types = parity.read(rel, pattern, parse)
            assert types, f"{rel}: pattern matched nothing"
            assert len(types) >= 5, f"{rel}: parsed only {types}"

    def test_they_currently_agree(self):
        assert parity.main() == 0


class TestTheTitleGateIsCovered:
    def test_the_title_list_is_read_from_the_workflow_that_ships(self):
        rel = ".github/workflows/semantic-pr.yml:title-types"
        pattern, parse = parity.SOURCES[rel]
        types = parity.read(rel, pattern, parse)
        assert "feat" in types and "security" in types

    def test_adding_a_type_to_only_the_old_three_is_caught(self, tmp_path, capsys):
        """The exact drift that used to pass.

        Add `deps` everywhere the check USED to look, and leave the title
        gate and the action default alone. The old three-source check saw
        three matching lists and exited 0; a pull request titled
        `deps: bump x` then failed the required title check.
        """
        import shutil

        work = tmp_path / "repo"
        shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(".git", ".pytest_cache"))
        old_list = "feat,fix,docs,style,refactor,perf,test,build,ci,chore,revert,security"
        for rel, before, after in (
            ("scripts/commit-check.py", f'"{old_list}"', f'"{old_list},deps"'),
            (
                "config/commitlint.config.js",
                "        'security',\n",
                "        'security',\n        'deps',\n",
            ),
        ):
            target = work / rel
            target.write_text(
                target.read_text(encoding="utf-8").replace(before, after), encoding="utf-8"
            )
        # The input default is the third of the old three.
        target = work / ".github/workflows/semantic-pr.yml"
        text = target.read_text(encoding="utf-8")
        target.write_text(
            text.replace(f"default: '{old_list}'", f"default: '{old_list},deps'", 1),
            encoding="utf-8",
        )

        drifted = load_script_from(work, "scripts/check-type-parity.py")
        assert drifted.main() == 1, (
            "parity passed with `deps` in the commit gate but not the title gate"
        )
        assert "deps" in capsys.readouterr().out


def load_script_from(root, rel):
    import importlib.util

    path = root / rel
    spec = importlib.util.spec_from_file_location("drifted_parity", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
