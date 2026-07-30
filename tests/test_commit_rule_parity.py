# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The local commitlint config must reject what the CI gate rejects.

`scripts/commit-check.py` says of `config/commitlint.config.js`: "The two
encode ONE rule set and change together; editing either alone produces a
rule nobody enforces or a gate nothing documents." They did not encode one
rule set. Three rules were enforced in CI and absent locally:

  scope       commit-check.py requires `<type>(<scope>):`; commitlint had no
              `scope-empty` rule, so `docs: update the readme` passed.
  case        commit-check.py requires a lowercase subject; commitlint's
              `subject-case` was level 1 (warn) and banned only `upper-case`,
              so `fix(api): Resolve the crash` passed.
  dashes      commit-check.py bans U+2013 to U+2015; the local plugin banned
              only U+2014, so an en dash passed locally and failed in CI.

A contributor running the published config got a clean local pass and then a
red required check on the same commit, three different ways.

THESE TESTS RUN BOTH IMPLEMENTATIONS. The JavaScript rules are executed with
node against the same messages `problems_for()` is given, and the verdicts
are compared. Asserting on the config's text would only prove a rule was
written down, not that it decides the same way.

The type list has its own checker (`check-type-parity.py`, five sources) and
is not re-tested here.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest
from conftest import ROOT, load_script

CONFIG = ROOT / "config/commitlint.config.js"
commit_check = load_script("scripts/commit-check.py")
TYPES = commit_check.DEFAULT_TYPES.split(",")

requires_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

# Runs every plugin rule in the shipped config against a parsed message and
# reports which ones failed. Kept minimal on purpose: commitlint's own
# parser is a dependency this repository does not carry, and the fields
# these two rules read are unambiguous.
RUNNER = """
const path = process.argv[1];
const message = JSON.parse(process.argv[2]);
const [header, ...rest] = message.split("\\n");
const body = rest.join("\\n").trim();
const m = header.match(/^([a-z]+)(?:\\(([^)]*)\\))?!?: (.*)$/);
const parsed = {
  header,
  body,
  footer: null,
  type: m ? m[1] : null,
  scope: m && m[2] !== undefined ? m[2] : null,
  subject: m ? m[3] : null,
};
import(path).then((mod) => {
  const failed = [];
  for (const [name, rule] of Object.entries(mod.default.plugins[0].rules)) {
    const [ok] = rule(parsed);
    if (!ok) failed.push(name);
  }
  process.stdout.write(JSON.stringify(failed));
});
"""


def js_failures(message: str) -> list[str]:
    """Which plugin rules reject this message, per node."""
    done = subprocess.run(
        ["node", "--input-type=module", "-e", RUNNER, str(CONFIG), json.dumps(message)],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(ROOT),
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def ci_rejects(message: str) -> bool:
    return bool(commit_check.problems_for(message, TYPES, 100))


def commitlint_rule(name: str) -> str | None:
    match = re.search(
        rf"'{re.escape(name)}':\s*(\[.*?\]),\n", CONFIG.read_text(encoding="utf-8"), re.S
    )
    return match.group(1) if match else None


def error_level(name: str) -> int | None:
    raw = commitlint_rule(name)
    return None if raw is None else int(re.search(r"\[\s*(\d)", raw).group(1))


DASHES = [(0x2013, "en dash"), (0x2014, "em dash"), (0x2015, "horizontal bar")]


class TestScopeIsRequiredInBothPlaces:
    def test_ci_rejects_a_missing_scope(self):
        assert ci_rejects("docs: update the readme\n\nBody.")

    def test_commitlint_has_the_rule(self):
        assert commitlint_rule("scope-empty") is not None, (
            "commitlint accepts a scopeless subject that the required check rejects"
        )

    def test_the_rule_is_an_error_not_a_warning(self):
        assert error_level("scope-empty") == 2, "a warning does not fail a local run"

    def test_a_scoped_subject_is_accepted_by_both(self):
        good = "docs(readme): update the readme\n\nBody."
        assert not ci_rejects(good)


SUBJECT_CASES = [
    ("fix(api): resolve the crash", False),
    ("fix(api): 🩹 resolve the crash", False),
    ("fix(api): Resolve the crash", True),
    ("fix(api): RESOLVE the crash", True),
    ("fix(api): 🩹 Resolve the crash", True),
]


class TestSubjectCaseAgrees:
    @pytest.mark.parametrize(("header", "rejected"), SUBJECT_CASES)
    def test_the_ci_gate(self, header, rejected):
        assert ci_rejects(f"{header}\n\nBody.") is rejected

    @requires_node
    @pytest.mark.parametrize(("header", "rejected"), SUBJECT_CASES)
    def test_the_local_config_agrees(self, header, rejected):
        """Both implementations run; the verdicts must match."""
        failed = js_failures(f"{header}\n\nBody.")
        assert ("subject-lowercase" in failed) is rejected, (
            f"node says {failed!r} for {header!r}; the CI gate says rejected={rejected}"
        )

    def test_an_emoji_subject_is_not_treated_as_sentence_case(self):
        """The reason this is a plugin and not `subject-case`: commitlint's
        built-in case detection has no notion of a leading emoji, and the
        house style puts one on most subjects."""
        assert not ci_rejects("feat(auth): ✨ add the login form\n\nBody.")

    @requires_node
    def test_an_emoji_subject_passes_locally_too(self):
        assert "subject-lowercase" not in js_failures("feat(auth): ✨ add the login form\n\nBody.")


class TestTheDashBanCoversTheSameRange:
    @pytest.mark.parametrize(("codepoint", "name"), DASHES)
    def test_the_ci_gate_rejects_it(self, codepoint, name):
        assert ci_rejects(f"fix(api): a subject with {chr(codepoint)} in it\n\nBody.")

    @requires_node
    @pytest.mark.parametrize(("codepoint", "name"), DASHES)
    def test_the_local_config_rejects_it_too(self, codepoint, name):
        message = f"fix(api): a subject with {chr(codepoint)} in it\n\nBody."
        assert "no-banned-dashes" in js_failures(message), (
            f"an {name} (U+{codepoint:04X}) passes locally and fails the required check"
        )

    @requires_node
    def test_an_ordinary_hyphen_is_fine(self):
        assert "no-banned-dashes" not in js_failures("fix(api): a well-formed subject\n\nBody.")

    @requires_node
    def test_a_banned_dash_in_the_body_is_caught(self):
        message = f"fix(api): a clean subject\n\nBody with {chr(0x2014)} in it."
        assert "no-banned-dashes" in js_failures(message)

    def test_the_config_never_contains_a_banned_character_itself(self):
        text = CONFIG.read_text(encoding="utf-8")
        for codepoint, name in DASHES:
            assert chr(codepoint) not in text, f"the config contains a literal {name}"
