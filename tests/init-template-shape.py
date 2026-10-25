# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The initial commit describes the template a repository came from, read from its tree.

The golden path ships a structure, src/ among it, beside its seeds in
docs/templates/, so that is what names it. Any other tree is described in
general, whatever it holds.
"""

from __future__ import annotations

from conftest import load_script

init = load_script(".github/scripts/init-template.py")

GOLDEN = "This is the golden path."
GENERAL = "golden-path template"


def tree(root, *folders):
    for folder in folders:
        (root / folder).mkdir(parents=True)
    return root


class TestTheShapeIsReadFromTheTree:
    def test_the_golden_path_ships_structure_beside_its_seeds(self, tmp_path):
        shape = init.shape_of(tree(tmp_path, "docs/templates", "src", "assets"))
        assert shape.startswith(GOLDEN)
        assert "src/, tests/, packages/, benchmarks/" in shape

    def test_seeds_with_no_structure_are_described_in_general(self, tmp_path):
        shape = init.shape_of(tree(tmp_path, "docs/templates", "assets"))
        assert GENERAL in shape and GOLDEN not in shape

    def test_a_tree_with_no_seeds_is_described_in_general(self, tmp_path):
        shape = init.shape_of(tree(tmp_path, "src"))
        assert GENERAL in shape and GOLDEN not in shape
