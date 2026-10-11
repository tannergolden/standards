# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The initial commit describes the template a repository came from, read from its tree.

Both templates keep their seeds in docs/, so where the seeds sit no longer
tells them apart, as it did while the private template kept them in
.github/docs/. The structure does: only the public template ships src/.
"""

from __future__ import annotations

from conftest import load_script

init = load_script("scripts/init-template.py")


def tree(root, *folders):
    for folder in folders:
        (root / folder).mkdir(parents=True)
    return root


class TestTheShapeIsReadFromTheTree:
    def test_the_public_template_ships_structure_beside_its_seeds(self, tmp_path):
        assert "public golden path" in init.shape_of(tree(tmp_path, "docs/templates", "src", "assets"))

    def test_the_private_template_ships_its_seeds_and_no_structure(self, tmp_path):
        shape = init.shape_of(tree(tmp_path, "docs/templates", "assets"))
        assert "private golden path" in shape
        assert "under docs/" in shape and ".github/docs" not in shape

    def test_a_tree_with_no_seeds_is_named_by_neither(self, tmp_path):
        shape = init.shape_of(tree(tmp_path, "src"))
        assert "golden-path template" in shape
        assert "public" not in shape and "private" not in shape
