"""
conftest.py
-----------
Global pytest fixtures for the STB Automation Framework.

Fixture hierarchy
~~~~~~~~~~~~~~~~~
* ``cms``          — CMSService, function-scoped (new session per test)
* ``stb_driver``   — Appium WebDriver, function-scoped
* ``launcher``     — LauncherPage, function-scoped (depends on stb_driver)
* ``test_context`` — Dict of shared state (tile_id, etc.) per test
* ``record_result``— Auto-use fixture that writes to results.json on teardown

Parallel-safe:  pytest-xdist workers each get their own driver + CMS session
                because the fixtures are function-scoped and use thread-local
                storage in the driver manager.
"""

import time
from typing import Dict, Generator, Optional

import pytest

from api.cms_service import CMSService
from config.config_loader import config
from driver.driver_manager import get_driver, quit_driver
from pages.launcher_page import LauncherPage
from utils.logger import get_logger
from utils.reporter import write_result
from utils.screenshot import capture

log = get_logger("conftest")


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "smoke: fast sanity checks")
    config.addinivalue_line("markers", "regression: full regression suite")
    config.addinivalue_line("markers", "api: pure API tests (no Appium)")
    config.addinivalue_line("markers", "ui: pure UI tests (Appium only)")
    config.addinivalue_line("markers", "hybrid: API + UI combined tests")


def pytest_sessionstart(session):
    """Notify n8n that a test session has started (non-blocking)."""
    try:
        from utils.reporter import clear_results
        clear_results() 
        from n8n.n8n_notifier import notifier
        notifier.test_suite_started(
            markers=getattr(session.config.option, "markexpr", "") or "all",
            device=config.device.get("device_name", "unknown"),
        )
    except Exception:
        pass  # n8n is optional — never block test execution


def pytest_sessionfinish(session, exitstatus):
    """Notify n8n that the session finished with summary stats (non-blocking)."""
    try:
        from n8n.n8n_notifier import notifier
        from utils.reporter import read_results, summarise
        summary = summarise(read_results())
        notifier.test_suite_finished(summary=summary)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# API fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def cms() -> Generator[CMSService, None, None]:
    """
    Provide a CMSService instance for the test, auto-closed on teardown.

    Usage::

        def test_something(cms):
            tile = cms.create_tile(title="Test Tile")
    """
    service = CMSService()
    log.debug("[fixture] CMSService created.")
    yield service
    service.close()
    log.debug("[fixture] CMSService closed.")


# ---------------------------------------------------------------------------
# UI fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def stb_driver(request):
    """
    Provide an Appium WebDriver connected to the STB.

    The ``--device-ip`` and ``--device-port`` CLI options allow overriding
    the device target at runtime (useful in CI pipelines).

    Usage::

        def test_ui(stb_driver):
            stb_driver.press_keycode(3)  # HOME
    """
    override: Optional[Dict] = {}

    # Allow CLI overrides: pytest --device-ip=192.168.1.200
    device_ip = request.config.getoption("--device-ip", default=None)
    device_port = request.config.getoption("--device-port", default=None)
    if device_ip:
        override["device_ip"] = device_ip
    if device_port:
        override["device_port"] = int(device_port)

    driver = get_driver(device_override=override or None)
    log.debug("[fixture] Appium driver ready: session=%s", driver.session_id)

    yield driver

    quit_driver()
    log.debug("[fixture] Appium driver quit.")


@pytest.fixture(scope="function")
def launcher(stb_driver, request) -> LauncherPage:
    """
    Provide a ``LauncherPage`` instance, already waiting for the launcher
    to finish loading.

    Usage::

        def test_navigation(launcher):
            launcher.navigate("right", "enter")
    """
    page = LauncherPage(
        driver=stb_driver,
        test_name=request.node.nodeid,
    )
    page.wait_for_launcher()
    return page


# ---------------------------------------------------------------------------
# Shared test context
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def test_context() -> Dict:
    """
    A plain dict for tests to store shared state (e.g. created tile IDs)
    that need to be accessible across steps and teardown logic.

    Usage::

        def test_hybrid(test_context, cms):
            tile = cms.create_tile("My Tile")
            test_context["tile_id"] = tile["id"]
    """
    return {}


# ---------------------------------------------------------------------------
# Result recording (auto-use)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function", autouse=True)
def record_result(request, stb_driver=None):
    """
    Auto-use fixture that records test outcome to ``reports/results.json``
    regardless of pass/fail.

    Captures a screenshot on failure if ``screenshot_on_failure`` is enabled
    in config.
    """
    start_time = time.monotonic()
    screenshot_path: Optional[str] = None

    yield  # ← test runs here

    duration = time.monotonic() - start_time
    outcome = getattr(request.node, "rep_call", None)

    if outcome is None:
        # Test was skipped or setup failed
        status = "SKIP"
        error_msg = None
    elif outcome.failed:
        status = "FAIL"
        error_msg = str(outcome.longrepr)[:1000] if outcome.longrepr else None

        # Screenshot on failure
        if config.execution.get("screenshot_on_failure", True):
            try:
                driver = request.node.funcargs.get("stb_driver")
                if driver:
                    screenshot_path = capture(driver, request.node.nodeid)
            except Exception as exc:
                log.warning("Could not capture failure screenshot: %s", exc)
    else:
        status = "PASS"
        error_msg = None

    write_result(
        test_name=request.node.nodeid,
        status=status,
        duration_sec=duration,
        device=config.device.get("device_name", "unknown"),
        screenshot=screenshot_path,
        error_msg=error_msg,
        tags=[m.name for m in request.node.iter_markers()],
    )


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Attach the call phase report to the node so ``record_result`` can read it."""
    outcome = yield
    report = outcome.get_result()
    if report.when == "call":
        item.rep_call = report


# ---------------------------------------------------------------------------
# CLI options
# ---------------------------------------------------------------------------

def pytest_addoption(parser):
    """Register custom CLI flags."""
    parser.addoption(
        "--device-ip",
        action="store",
        default=None,
        help="Override STB device IP address",
    )
    parser.addoption(
        "--device-port",
        action="store",
        default=None,
        help="Override STB ADB port (default: 5555)",
    )
    parser.addoption(
        "--env",
        action="store",
        default="staging",
        help="Target environment: dev | staging | prod",
    )
