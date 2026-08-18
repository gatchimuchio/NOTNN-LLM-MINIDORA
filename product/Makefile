PYTHON ?= python3
VENV ?= .venv
BIN := $(VENV)/bin
ifeq ($(OS),Windows_NT)
BIN := $(VENV)/Scripts
endif
.PHONY: dev test lint audit test-all serve doctor bench clean
$(VENV):
	$(PYTHON) -m venv $(VENV)
dev: $(VENV)
	$(BIN)/python -m pip install --upgrade pip
	$(BIN)/python -m pip install -e ".[dev,documents]"
lint:
	$(BIN)/ruff check src tests benchmarks scripts
test:
	$(BIN)/pytest --cov=minidora --cov-report=term-missing
audit:
	$(BIN)/python scripts/verify_product.py
test-all: lint test audit
serve:
	$(BIN)/minidora serve
doctor:
	$(BIN)/minidora doctor
bench:
	$(BIN)/python benchmarks/run_benchmark.py --output benchmark_results --repetitions 300
clean:
	rm -rf $(VENV) .pytest_cache .ruff_cache .coverage coverage.xml htmlcov build dist *.egg-info
