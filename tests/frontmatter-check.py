# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""Every document says what it is before it is opened.

Document Styling & Formatting asks each Markdown document to open with a
hidden block of a few flat fields: a title, a description that says when to
read it, a type from six, and optionally keywords and a status. An agent
routes by that block, so `check-frontmatter.py` fails the one that breaks
it. The rules here and the rules in the specification are the same rules:
the last class reads the specification's own tables, so neither can change
without the other.
"""

from __future__ import annotations

import subprocess

from conftest import ROOT, load_script

check = load_script(".github/scripts/check-frontmatter.py")
SPEC = ROOT / "docs/technical/interface/Document-Styling-&-Formatting.md"


def doc(*fields: str, body: str = "# Title\n") -> str:
    return "<!--\n" + "\n".join(fields) + "\n-->\n\n" + body


GOOD = (
    "title: '🧭 A GUIDE'",
    "description: 'How a thing is done, and when to read this before doing it.'",
    "type: guide",
)


def messages(text: str, path: str = "docs/Guide.md") -> list[str]:
    return [message for _line, message in check.problems(path, text)]


class TestTheForm:
    def test_a_document_with_the_three_required_fields_passes(self):
        assert messages(doc(*GOOD)) == []

    def test_a_fenced_block_is_caught_because_github_shows_it(self):
        fenced = "---\n" + "\n".join(GOOD) + "\n---\n\n# Title\n"
        (found,) = messages(fenced)
        assert "fenced with ---" in found

    def test_a_document_without_frontmatter_is_caught(self):
        (found,) = messages("# Title\n\nBody.\n")
        assert found.startswith("no frontmatter")

    def test_the_opener_must_stand_alone_on_the_first_line(self):
        assert "alone on the first line" in messages("<!-- title: 'X'\n-->\n")[0]
        assert "no frontmatter" in messages("\n" + doc(*GOOD))[0]

    def test_nested_or_continued_values_are_not_fields(self):
        found = messages(doc(*GOOD, "keywords:", "  - nested"))
        assert any("is not a field" in m for m in found)

    def test_crlf_line_endings_read_as_lf(self):
        assert messages(doc(*GOOD).replace("\n", "\r\n")) == []


class TestTheFields:
    def test_each_required_field_is_named_when_missing(self):
        found = messages(doc("title: 'X'"))
        assert "missing description" in found and "missing type" in found

    def test_the_retired_fields_say_what_replaced_them(self):
        found = messages(doc(*GOOD, "tags: [a, b, c, d]", "category: docs"))
        assert any(m.startswith("tags is retired") and "keywords" in m for m in found)
        assert any(m.startswith("category is retired") for m in found)

    def test_a_field_outside_the_standard_is_caught(self):
        (found,) = messages(doc(*GOOD, "author: 'Someone'"))
        assert found.startswith("author is not a frontmatter field")
        assert "only a record or a template adds fields" in found

    def test_type_comes_from_the_six(self):
        for kind in check.TYPES:
            fields = [f for f in GOOD if not f.startswith("type")] + [f"type: {kind}"]
            assert messages(doc(*fields)) == [], kind
        (found,) = messages(doc(*GOOD[:2], "type: tutorial"))
        assert "type is 'tutorial'" in found

    def test_a_description_that_repeats_the_title_is_caught(self):
        (found,) = messages(doc("title: '🧭 A GUIDE'", "description: 'A guide.'", "type: guide"))
        assert "repeats the title" in found

    def test_status_is_left_out_while_a_document_holds(self):
        (found,) = messages(doc(*GOOD, "status: active"))
        assert "leave status out" in found
        for status in ("draft", "deprecated", "archived"):
            assert messages(doc(*GOOD, f"status: {status}")) == []

    def test_a_decision_record_keeps_its_own_statuses_and_fields(self):
        record = ("title: '📄 ADR-0001 ONE DECISION'", "description: 'Why this was chosen.'",
                  "type: record")
        assert messages(doc(*record, "status: 'Accepted'", "date: '2026-10-19'",
                            "evidence: 'N/A'")) == []
        (found,) = messages(doc(*GOOD, "status: 'Accepted'"))
        assert "status is 'Accepted'" in found

    def test_a_record_adds_the_fields_its_kind_needs_and_nothing_else_does(self):
        idea = ("title: 'A FASTER BUILD'", "description: 'One idea, scored, and where it stands.'",
                "type: record", "lifecycle: 'raw'", "elo: 1500")
        assert messages(doc(*idea)) == []
        (found,) = messages(doc(*GOOD, "verified: '2026-10-19'"))
        assert found.startswith("verified is not a frontmatter field")

    def test_a_template_keeps_its_placeholders(self):
        template = ("title: '📄 ADR TEMPLATE'", "description: 'The form for one decision.'",
                    "type: template", "status: '[Proposed | Accepted | Superseded | Deprecated]'",
                    "date: '[YYYY-MM-DD]'")
        assert messages(doc(*template)) == []

    def test_keywords_are_a_short_lowercase_list(self):
        assert messages(doc(*GOOD, "keywords: [layout, root files, ci-cd]")) == []
        assert "is a list" in messages(doc(*GOOD, "keywords: layout"))[0]
        assert "holds 9 terms" in messages(doc(*GOOD, "keywords: [a, b, c, d, e, f, g, h, i]"))[0]
        assert "not lowercase" in messages(doc(*GOOD, "keywords: [Layout]"))[0]
        assert "appears twice" in messages(doc(*GOOD, "keywords: [a, a]"))[0]
        assert "is empty" in messages(doc(*GOOD, "keywords: []"))[0]

    def test_each_problem_is_reported_on_its_line(self):
        ((line, _message),) = check.problems("x.md", doc(*GOOD, "status: active"))
        assert line == 5


class TestWhatIsExempt:
    def test_files_a_loader_or_github_reads_as_they_are(self):
        skills = {"skills/develop"}
        for path in (".github/pull_request_template.md", ".github/ISSUE_TEMPLATE/bug.md",
                     "skills/develop/SKILL.md", "skills/develop/references/notes.md",
                     ".claude/agents/reviewer.md", "x.agent.md", "a.instructions.md",
                     "tests/fixtures/sample/README.md"):
            assert check.exempt(path, skills), path
        for path in ("README.md", ".github/ISSUE_TEMPLATE/README.md", "docs/skills.md"):
            assert not check.exempt(path, skills), path

    def test_an_agent_definition_named_in_its_fence_is_its_loaders(self):
        assert check.loader_fence("---\nname: worker\ndescription: Does one change.\n---\n")
        assert not check.loader_fence("---\ntitle: 'A note'\n---\n")

    def test_an_agent_instruction_file_may_go_without(self):
        assert messages("# Notes for Claude\n", "CLAUDE.md") == []
        assert messages("<!-- markdownlint-disable MD041 -->\n# Agents\n", "AGENTS.md") == []
        assert messages(doc(*GOOD, "tags: [a]"), "AGENTS.md")


def run_in(repo, files: dict[str, str], run_shell, mode: str | None = None, untracked: dict | None = None):
    for rel, text in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    for rel, text in (untracked or {}).items():
        (repo / rel).write_text(text, encoding="utf-8")
    flag = f" --mode {mode}" if mode else ""
    return run_shell(f'exec python3 "{ROOT}/.github/scripts/check-frontmatter.py"{flag}', cwd=repo)


class TestTheGate:
    def test_a_repository_that_follows_the_standard_passes(self, git_repo, run_shell):
        result = run_in(git_repo, {"README.md": doc(*GOOD)}, run_shell)
        assert result.returncode == 0, result.output
        assert "all 1 document(s)" in result.output

    def test_enforce_fails_with_an_annotation(self, git_repo, run_shell):
        result = run_in(git_repo, {"docs/Guide.md": "# Guide\n"}, run_shell)
        assert result.returncode == 1, result.output
        assert "::error file=docs/Guide.md,line=1,title=Frontmatter::no frontmatter" in result.output
        assert "Frontmatter Check Failed" in result.summary

    def test_warn_reports_and_passes(self, git_repo, run_shell):
        result = run_in(git_repo, {"docs/Guide.md": "# Guide\n"}, run_shell, mode="warn")
        assert result.returncode == 0, result.output
        assert "::warning file=docs/Guide.md,line=1,title=Frontmatter::" in result.output

    def test_generated_files_and_untracked_files_are_not_read(self, git_repo, run_shell):
        files = {".gitattributes": "drawn/** linguist-generated=true\n",
                 "drawn/Page.md": "# Drawn by a generator\n",
                 "README.md": doc(*GOOD)}
        result = run_in(git_repo, files, run_shell, untracked={"scratch.md": "# Not tracked\n"})
        assert result.returncode == 0, result.output


class TestTheWiring:
    def test_ci_runs_the_action_with_the_input(self):
        text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        assert "uses: tannergolden/standards/.github/actions/check-frontmatter@v1" in text
        assert "mode: ${{ inputs.frontmatter }}" in text

    def test_the_input_reports_without_failing_by_default(self):
        from conftest import workflow_inputs

        assert workflow_inputs(".github/workflows/ci.yml")["frontmatter"]["default"] == "warn"

    def test_the_action_runs_the_script_and_lint_docs_runs_it_here(self):
        from conftest import load_yaml

        action = load_yaml(".github/actions/check-frontmatter/action.yml")
        assert "../../scripts/check-frontmatter.py" in action["runs"]["steps"][0]["run"]
        assert "python3 .github/scripts/check-frontmatter.py" in (ROOT / "Makefile").read_text(encoding="utf-8")


class TestTheSpecificationAgrees:
    def section(self) -> str:
        text = SPEC.read_text(encoding="utf-8")
        start = text.index("## 🗂️ Frontmatter Metadata")
        return text[start:text.index("\n## ", start + 1)]

    def test_every_type_has_its_row_and_no_other_does(self):
        rows = [line for line in self.section().splitlines() if line.startswith("| `")]
        listed = {line.split("`")[1] for line in rows}
        assert set(check.TYPES) <= listed
        assert listed - set(check.TYPES) == {"title", "description", "type", "keywords", "status"}

    def test_the_statuses_and_the_records_own_fields_are_named(self):
        section = self.section()
        for word in (*check.STATUSES, "date", "evidence", "verified", "focus", "decision"):
            assert f"`{word}`" in section, word
        for status in check.DECISION_STATUSES:
            assert f"`{status.capitalize()}`" in section, status
        assert f"Up to {['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight'][check.MAX_KEYWORDS]}" in section
