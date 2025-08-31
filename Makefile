.DEFAULT_GOAL := help
SOURCE_DIR = ./diskcache
PY_VERSIONS = 3.7 3.8 3.9 3.10 3.11 3.12 3.13 3.14 3.13t 3.14t pypy@3.9 pypy@3.10 pypy@3.11
export UV_MANAGED_PYTHON ?= 1

##@ CI/CD
.PHONY: build
build: ## Build
	uv build

.PHONY: cov
cov: ## Run tests with coverage
	uv run pytest -n auto --cov-report=term-missing --cov-config=pyproject.toml --cov=diskcache

##@ Quality
.PHONY: test
test: ## Run tests in current Python
	uv run pytest -n auto

.PHONY: test-orig
test-orig: ## Run tests in current Python
	uv run pytest\
    -n auto\
    --cov-branch\
    --cov-fail-under=98\
    --cov-report=term-missing\
    --cov=diskcache\
    --doctest-glob="*.rst"\
    --ignore docs/case-study-web-crawler.rst\
    --ignore docs/sf-python-2017-meetup-talk.rst\
    --ignore tests/issue_85.py

# .PHONY: tests
# tests: ## Run tests in all supporte Python versions
# 	uv run --isolated -p 3.9 pytest -n auto
# 	uv run --isolated -p 3.10 pytest -n auto
# 	uv run --isolated -p 3.11 pytest -n auto
# 	uv run --isolated -p 3.12 pytest -n auto
# 	uv run --isolated -p 3.13 pytest -n auto
# 	uv run --isolated -p 3.14 pytest -n auto
# 	uv run --isolated -p 3.13t pytest -n auto
# 	uv run --isolated -p 3.14t pytest -n auto
# 	uv run --isolated -p pypy@3.9 pytest -n auto
# 	uv run --isolated -p pypy@3.10 pytest -n auto
# 	uv run --isolated -p pypy@3.11 pytest -n auto
# #	uv run --isolated -p graalpy pytest

.PHONY: tests
tests: ## Run tests in all supporte Python versions
	for py_v in $(PY_VERSIONS); do \
		uv run --isolated -p $$py_v pytest -n auto; \
	done

.PHONY: check
check: ## Run all checks 
	-uvx mypy ${SOURCE_DIR}
	uvx ruff check ${SOURCE_DIR}

.PHONY: ruff-check
ruff-check: ## Lint using ruff
	uvx ruff check ${SOURCE_DIR}

.PHONY: type-check
type-check: ## Type check with
	-uvx ty check ${SOURCE_DIR}
	-uvx pyrefly check ${SOURCE_DIR}
	uvx mypy ${SOURCE_DIR}

.PHONY: format
format: ## Format files using ruff format
	uvx ruff format ${SOURCE_DIR}

.PHONY: bench
bench: ## run benchmarks
	uv run --isolated --group benchmark benchmarks/benchmark_core.py

.PHONY: bench-kv
bench-kv: ## run benchmarks kv
	uv run --isolated --group benchmark python -m IPython benchmarks/benchmark_kv_store.py

.PHONY: docs
docs: ## build docs
	cd docs && $(MAKE) html

##@ Utility
.PHONY: clean
clean: ## Delete all temporary files
	rm -rf .pytest_cache
	rm -rf **/.pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf __pycache__
	rm -rf **/__pycache__
	rm -rf build
	rm -rf dist
	rm -f .coverage

.PHONY: install
install: install-uv ## Install virtual environment
	uv sync --frozen

.PHONY: install-uv
install-uv: ## Install uv
	@command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh

.PHONY: update-uv
update-uv: ## Update uv
	uv self update

.PHONY: help
help:  ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make <target>\033[36m\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
