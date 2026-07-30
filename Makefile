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
# target is a one-line call into `scripts/`, so this file cannot drift away
# from what the scripts actually do, and CI runs the same entry points a
# contributor does rather than its own private copy of them.
#
# `ci.yml` resolves a stage to `make <stage>` when a repository defines one,
# so these names are the ones a consuming repository would use too. This
# repository is gated by `self-checks.yml` rather than by `ci.yml`, but the
# names stay aligned deliberately.
#
# ---

RUFF_VERSION ?= 0.15.8
PYTEST_VERSION ?= 9.1.1

.PHONY: help setup lint lint-fix lint-docs test docs-index check-types

help: ## Show the available targets
	@grep -hE '^[a-z][a-z-]*:.*?## ' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup: ## Install the pinned development tools
	pip install --quiet "ruff==$(RUFF_VERSION)" "pytest==$(PYTEST_VERSION)"

lint: ## Lint the Python scripts, with the rules declared in .ruff.toml
	ruff check .

lint-fix: ## Apply the lint fixes ruff can make automatically
	ruff check --fix .

# The generators are the gate. Each reports drift and changes nothing, so
# this target is safe to run anywhere and is what CI calls.
lint-docs: ## Fail when a generated document or the commit-type list has drifted
	python3 scripts/update-doc-indexes.py --check
	python3 scripts/update-label-docs.py --check
	python3 scripts/check-type-parity.py

test: ## Run the test suite
	python3 -m pytest

docs-index: ## Regenerate every machined index and label table in place
	python3 scripts/update-doc-indexes.py --write
	python3 scripts/update-label-docs.py

check-types: ## Check the Conventional Commit type list agrees everywhere
	python3 scripts/check-type-parity.py
