# ============================================================
# STB Launcher Hybrid Automation Framework — Makefile
# ============================================================
# Usage: make <target>
# Prerequisites: Python 3.11+, Appium Server running, ADB in PATH

.PHONY: help install env-check \
        test test-smoke test-api test-ui test-hybrid test-regression \
        test-parallel test-rerun \
        dashboard report clean

PYTHON   := python3
PYTEST   := pytest
STREAMLIT := streamlit
RESULTS  := reports/results.json

# ── Help ─────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  STB Automation Framework — Available Commands"
	@echo "  ════════════════════════════════════════════"
	@echo ""
	@echo "  Setup"
	@echo "  ─────"
	@echo "  make install        Install all Python dependencies"
	@echo "  make env-check      Validate environment (adb, appium, python)"
	@echo ""
	@echo "  Test Execution"
	@echo "  ──────────────"
	@echo "  make test           Run ALL tests"
	@echo "  make test-smoke     Run smoke tests only"
	@echo "  make test-api       Run API-only tests (no Appium needed)"
	@echo "  make test-ui        Run UI-only tests"
	@echo "  make test-hybrid    Run hybrid (API + UI) tests"
	@echo "  make test-regression Run full regression suite"
	@echo "  make test-parallel  Run tests in parallel (2 workers)"
	@echo "  make test-rerun     Run tests with 3 reruns on failure"
	@echo ""
	@echo "  Dashboard & Reporting"
	@echo "  ─────────────────────"
	@echo "  make dashboard      Launch Streamlit dashboard"
	@echo "  make report         Print summary of last results.json"
	@echo ""
	@echo "  Maintenance"
	@echo "  ───────────"
	@echo "  make clean          Remove .pyc, __pycache__, old reports"
	@echo ""

# ── Setup ────────────────────────────────────────────────────────────────────
install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	@echo "✓ Dependencies installed."

env-check:
	@echo "── Python ──────────────────────────────────"
	@$(PYTHON) --version
	@echo "── ADB ─────────────────────────────────────"
	@adb version 2>/dev/null || echo "⚠  adb not found — install Android SDK Platform Tools"
	@echo "── Appium ──────────────────────────────────"
	@appium --version 2>/dev/null || echo "⚠  appium not found — run: npm install -g appium"
	@echo "── Pytest ──────────────────────────────────"
	@$(PYTEST) --version
	@echo "── Streamlit ───────────────────────────────"
	@$(STREAMLIT) --version
	@echo "✓ Environment check complete."

# ── Test execution ────────────────────────────────────────────────────────────
test:
	$(PYTEST) tests/ -v

test-smoke:
	$(PYTEST) tests/ -m smoke -v

test-api:
	$(PYTEST) tests/ -m api -v

test-ui:
	$(PYTEST) tests/ -m ui -v

test-hybrid:
	$(PYTEST) tests/ -m hybrid -v

test-regression:
	$(PYTEST) tests/ -m regression -v

test-parallel:
	$(PYTEST) tests/ -n 2 -v

test-rerun:
	$(PYTEST) tests/ --reruns 3 --reruns-delay 2 -v

# ── Dashboard ────────────────────────────────────────────────────────────────
dashboard:
	$(STREAMLIT) run dashboard/dashboard.py --server.port 8501 --server.headless true

# ── Reporting ────────────────────────────────────────────────────────────────
report:
	@$(PYTHON) -c "\
import json, sys; \
data = json.load(open('$(RESULTS)')); \
total = len(data); \
passed = sum(1 for r in data if r['status']=='PASS'); \
failed = sum(1 for r in data if r['status']=='FAIL'); \
errors = sum(1 for r in data if r['status']=='ERROR'); \
pct = round(passed/total*100,1) if total else 0; \
print(f'Total: {total}  Passed: {passed}  Failed: {failed}  Errors: {errors}  Pass%%: {pct}%%')"

# ── Maintenance ───────────────────────────────────────────────────────────────
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null; true
	@echo "✓ Cleaned build artefacts."
