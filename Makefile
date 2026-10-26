# --- Developer Entry Points ---
#
# Five documents, the contributor-welcome message this repository posts to
# first-time contributors, and two script docstrings all told the reader to
# run `make lint`, `make test`, `make lint-docs`, `make docs-index` and
# `make check-types`. None of them existed. Following the instructions
# produced "No targets specified and no makefile found".
#
# That mattered more than a broken command usually would, because
# `check-type-parity.py` says plainly that there is no CI job to hang it on
# and `make check-types` is how you run it. The only protection against the
# commit-type list drifting was a command that did not exist.
#
# WHAT BELONGS HERE: the commands a person or a gate runs. No logic. Every
# target is a one-line call into `.github/scripts/`, so this file cannot drift away
# from what the scripts actually do, and CI runs the same entry points a
# contributor does rather than its own private copy of them.
#
# `ci.yml` resolves a stage to `make <stage>` when a repository defines one,
# so these names are the ones a consuming repository would use too. This
# repository is gated by `self-checks.yml` rather than by `ci.yml`, but the
# names stay aligned deliberately.
#
# ---

.PHONY: help setup lint lint-fix lint-docs lint-format test docs-index check-types

help: ## Show the available targets
	@grep -hE '^[a-z][a-z-]*:.*?## ' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

# Every checker comes from tannergolden/environment, at the version its
# toolchain pins: the development container is its image, and CI installs
# the same toolchain. Nothing here pins one, so this only says what is missing.
setup: ## Check ruff, pytest and Prettier are on PATH, as the development container has them
	@missing=""; for tool in ruff pytest prettier; do command -v $$tool >/dev/null 2>&1 || missing="$$missing $$tool"; done; \
	if [ -n "$$missing" ]; then \
		echo "Missing:$$missing. Work in the development container, or run toolchain/install.sh --user from a checkout of tannergolden/environment." >&2; \
		exit 1; \
	fi

lint: ## Lint the Python scripts, with the rules declared in .ruff.toml
	ruff check .

lint-fix: ## Apply the lint fixes ruff can make automatically
	ruff check --fix .

# The generators are the gate. Each reports drift and changes nothing, so
# this target is safe to run anywhere and is what CI calls.
lint-docs: ## Fail when a generated document, a document's frontmatter or the commit-type list has drifted
	python3 .github/scripts/update-doc-indexes.py --check --tree
	python3 .github/scripts/update-label-docs.py --check
	python3 .github/scripts/check-frontmatter.py
	python3 .github/scripts/check-type-parity.py

lint-format: ## Check formatting against the published Prettier config
	prettier --config config/prettierrc.json --ignore-path config/prettierignore --check "**/*.{md,yml,yaml,json,js}"

test: ## Run the test suite
	python3 -m pytest

docs-index: ## Regenerate every machined index and label table in place
	python3 .github/scripts/update-doc-indexes.py --tree --write
	python3 .github/scripts/update-label-docs.py

check-types: ## Check the Conventional Commit type list agrees everywhere
	python3 .github/scripts/check-type-parity.py
