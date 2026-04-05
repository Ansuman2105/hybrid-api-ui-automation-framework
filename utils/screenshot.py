"""
screenshot.py
-------------
Screenshot capture helper for the STB Automation Framework.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.config_loader import config
from utils.logger import get_logger

log = get_logger(__name__)

_SCREENSHOTS_DIR = Path(
    config.reporting.get("screenshots_dir", "reports/screenshots")
)
_SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def capture(driver, test_name: str = "screenshot") -> Optional[str]:
    """
    Take a screenshot from the Appium driver and save it to disk.

    Args:
        driver:     Active Appium WebDriver instance.
        test_name:  Used as part of the filename for easy identification.

    Returns:
        Relative path to the saved screenshot, or ``None`` on failure.
    """
    if driver is None:
        log.warning("Screenshot skipped — driver is None.")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = test_name.replace("::", "__").replace("/", "_")
    filename = f"{safe_name}_{timestamp}.png"
    filepath = _SCREENSHOTS_DIR / filename

    try:
        driver.save_screenshot(str(filepath))
        rel_path = str(filepath.relative_to(Path.cwd())) if filepath.is_absolute() else str(filepath)
        log.info("Screenshot saved: %s", filepath)
        return rel_path
    except Exception as exc:
        log.error("Failed to capture screenshot: %s", exc)
        return None
