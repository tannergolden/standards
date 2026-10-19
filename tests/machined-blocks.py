# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""A block marked with its own hash must still match it.

The INTELLIGENCE block in a repository's AGENTS.md is rendered by
tannergolden/intelligence and replaced on every sync. A hand edit inside it
is overwritten without a word, so `machined-blocks.py` fails the pull
request that makes one. The hash rule here must match the renderer's to the
byte, or every delivered block reads as edited: CRLF counts as LF, and the
blank lines a formatter adds around the block do not count at all.
"""

from __future__ import annotations

import hashlib
import subprocess

from conftest import load_script

blocks = load_script(".github/scripts/machined-blocks.py")

RULES = "## Working rules\n\n- SEC-001: Never put a credential in a file.\n"


def region(block: str, name: str = "INTELLIGENCE") -> str:
    """A block between its markers, laid out as tannergolden/intelligence renders it."""
    digest = hashlib.sha256(block.encode("utf-8")).hexdigest()
    return f"<!-- {name}:BEGIN sha256:{digest} -->\n\n{block}\n<!-- {name}:END -->\n"


def run_in(repo, files: dict[str, str], run_script):
    for rel, text in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    return run_script(".github/scripts/machined-blocks.py", cwd=repo)


class TestTheHash:
    def test_a_delivered_block_matches(self):
        assert blocks.problems("AGENTS.md", f"# Agents\n\n{region(RULES)}\n## Commands\n") == []

    def test_a_hand_edit_is_caught_on_its_line(self):
        text = "# Agents\n\n" + region(RULES).replace("credential", "secret")
        (found,) = blocks.problems("AGENTS.md", text)
        assert found[0] == 3
        assert "edited by hand" in found[1]

    def test_line_endings_and_padding_do_not_count_as_edits(self):
        crlf = region(RULES).replace("\n", "\r\n")
        padded = region(RULES).replace("-->\n\n", "-->\n\n\n\n")
        assert blocks.problems("AGENTS.md", crlf) == []
        assert blocks.problems("AGENTS.md", padded) == []

    def test_any_marker_name_with_a_hash_is_checked(self):
        knowledge = region("## Facts\n\n- One maintainer.\n", "INTELLIGENCE:KNOWLEDGE")
        assert blocks.problems("x.md", knowledge) == []
        assert blocks.problems("x.md", knowledge.replace("One", "Two"))

    def test_a_second_block_of_the_same_name_is_caught(self):
        (found,) = blocks.problems("AGENTS.md", region(RULES) + "\n" + region(RULES))
        assert "a second INTELLIGENCE block" in found[1]

    def test_a_block_shown_in_a_code_fence_is_an_example(self):
        example = "# How it looks\n\n```markdown\n" + region(RULES).replace("credential", "x") + "```\n"
        assert blocks.problems("README.md", example) == []


class TestTheGate:
    def test_a_repository_without_blocks_passes(self, git_repo, run_script):
        result = run_in(git_repo, {"README.md": "# Readme\n"}, run_script)
        assert result.returncode == 0, result.output
        assert "none in this repository" in result.output

    def test_delivered_blocks_pass(self, git_repo, run_script):
        result = run_in(git_repo, {"AGENTS.md": f"# Agents\n\n{region(RULES)}"}, run_script)
        assert result.returncode == 0, result.output
        assert "all 1 match" in result.output

    def test_an_edited_block_fails_with_an_annotation(self, git_repo, run_script):
        edited = f"# Agents\n\n{region(RULES)}".replace("credential", "secret")
        result = run_in(git_repo, {"docs/AGENTS.md": edited}, run_script)
        assert result.returncode == 1, result.output
        assert "::error file=docs/AGENTS.md,line=3,title=Machined block::" in result.output

    def test_untracked_files_are_not_read(self, git_repo, run_script):
        (git_repo / "scratch.md").write_text(region(RULES).replace("credential", "x"), encoding="utf-8")
        result = run_script(".github/scripts/machined-blocks.py", cwd=git_repo)
        assert result.returncode == 0, result.output


class TestTheWiring:
    def test_ci_runs_the_action(self):
        from conftest import ROOT

        assert "uses: tannergolden/standards/.github/actions/machined-blocks@v1" in (
            ROOT / ".github/workflows/ci.yml"
        ).read_text(encoding="utf-8")

    def test_the_action_runs_the_script(self):
        from conftest import ROOT, load_yaml

        action = load_yaml(".github/actions/machined-blocks/action.yml")
        run = action["runs"]["steps"][0]["run"]
        assert "../../scripts/machined-blocks.py" in run
        assert (ROOT / ".github/scripts/machined-blocks.py").is_file()
