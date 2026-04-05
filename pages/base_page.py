"""
base_page.py
------------
Abstract base class for all Page Object Model (POM) classes.

Provides
~~~~~~~~
* Explicit-wait wrappers (find_element, wait_for_visible, etc.)
* DPAD key-press helpers for STB remote navigation
* Assertion helpers that auto-capture screenshots on failure
* Logging of every interaction for full traceability
"""

from typing import Optional, Tuple

from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.config_loader import config
from utils.logger import get_logger
from utils.screenshot import capture

log = get_logger(__name__)

# Android KeyEvent codes for STB DPAD remote
_KEYCODE = {
    "up":     19,
    "down":   20,
    "left":   21,
    "right":  22,
    "enter":  23,   # DPAD_CENTER / OK
    "back":   4,
    "home":   3,
    "menu":   82,
    "search": 84,
    "play":   126,
    "pause":  127,
    "stop":   86,
}


class BasePage:
    """
    Base class shared by all STB page objects.

    Args:
        driver:        Active Appium WebDriver instance.
        test_name:     Passed through for screenshot naming on failures.
        explicit_wait: Override the default explicit wait in seconds.
    """

    def __init__(
        self,
        driver: webdriver.Remote,
        test_name: str = "unknown",
        explicit_wait: Optional[int] = None,
    ) -> None:
        self.driver = driver
        self.test_name = test_name
        self._wait_secs = explicit_wait or config.device.get("explicit_wait", 20)
        self._wait = WebDriverWait(driver, self._wait_secs)

    # ------------------------------------------------------------------
    # Element finders
    # ------------------------------------------------------------------

    def find(
        self, by: str, value: str, timeout: Optional[int] = None
    ) -> WebElement:
        """
        Wait for an element to be present and return it.

        Args:
            by:      Locator strategy (e.g. ``AppiumBy.XPATH``).
            value:   Locator value.
            timeout: Override default explicit wait.

        Raises:
            TimeoutException: If element not found within timeout.
        """
        wait = WebDriverWait(self.driver, timeout or self._wait_secs)
        log.debug("Finding element [%s = %s]", by, value)
        return wait.until(EC.presence_of_element_located((by, value)))

    def find_visible(
        self, by: str, value: str, timeout: Optional[int] = None
    ) -> WebElement:
        """Wait for element to be *visible* (present + displayed)."""
        wait = WebDriverWait(self.driver, timeout or self._wait_secs)
        log.debug("Waiting for visibility [%s = %s]", by, value)
        return wait.until(EC.visibility_of_element_located((by, value)))

    def find_all(self, by: str, value: str) -> list:
        """Return all matching elements (no wait)."""
        return self.driver.find_elements(by, value)

    def is_visible(self, by: str, value: str, timeout: int = 5) -> bool:
        """Return True if element is visible within timeout, else False."""
        try:
            self.find_visible(by, value, timeout=timeout)
            return True
        except (TimeoutException, NoSuchElementException):
            return False

    def is_present(self, by: str, value: str, timeout: int = 5) -> bool:
        """Return True if element exists in DOM within timeout."""
        try:
            self.find(by, value, timeout=timeout)
            return True
        except (TimeoutException, NoSuchElementException):
            return False

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def click(self, by: str, value: str) -> None:
        """Find and click an element."""
        element = self.find_visible(by, value)
        log.debug("Clicking [%s = %s]", by, value)
        element.click()

    def get_text(self, by: str, value: str) -> str:
        """Return the text content of a visible element."""
        return self.find_visible(by, value).text

    # ------------------------------------------------------------------
    # DPAD / Remote navigation
    # ------------------------------------------------------------------

    def press_key(self, key_name: str) -> None:
        """
        Send a single DPAD / remote keypress via ADB keyevent.

        Args:
            key_name: One of ``up``, ``down``, ``left``, ``right``,
                      ``enter``, ``back``, ``home``, ``menu``,
                      ``search``, ``play``, ``pause``, ``stop``.

        Raises:
            ValueError: If ``key_name`` is not recognised.
        """
        keycode = _KEYCODE.get(key_name.lower())
        if keycode is None:
            raise ValueError(
                f"Unknown key '{key_name}'. Valid keys: {list(_KEYCODE.keys())}"
            )
        log.debug("Pressing key: %s (keycode=%d)", key_name, keycode)
        self.driver.press_keycode(keycode)

    def navigate(self, *directions: str) -> None:
        """
        Send a sequence of DPAD keypresses.

        Example::

            page.navigate("right", "right", "down", "enter")
        """
        for direction in directions:
            self.press_key(direction)

    def press_back(self) -> None:
        self.press_key("back")

    def press_home(self) -> None:
        self.press_key("home")

    def press_enter(self) -> None:
        self.press_key("enter")

    # ------------------------------------------------------------------
    # Screenshot & assertion helpers
    # ------------------------------------------------------------------

    def screenshot(self, suffix: str = "") -> Optional[str]:
        """Capture a screenshot and return its path."""
        name = f"{self.test_name}{'_' + suffix if suffix else ''}"
        return capture(self.driver, name)

    def assert_visible(self, by: str, value: str, message: str = "") -> None:
        """
        Assert that an element is visible, capturing a screenshot on failure.

        Args:
            by:      Locator strategy.
            value:   Locator value.
            message: Human-readable description used in the failure message.

        Raises:
            AssertionError: With screenshot path embedded in the message.
        """
        visible = self.is_visible(by, value)
        if not visible:
            shot = self.screenshot(suffix="assert_failure")
            raise AssertionError(
                f"Element not visible: [{by}={value}] "
                f"{'— ' + message if message else ''}. "
                f"Screenshot: {shot}"
            )

    # ------------------------------------------------------------------
    # App lifecycle
    # ------------------------------------------------------------------

    def launch_app(self) -> None:
        """Activate the app under test (brings foreground if backgrounded)."""
        pkg = config.device.get("app_package")
        log.info("Activating app: %s", pkg)
        self.driver.activate_app(pkg)

    def background_app(self, seconds: int = 3) -> None:
        """Send the app to background for *seconds*, then restore."""
        log.debug("Sending app to background for %ds", seconds)
        self.driver.background_app(seconds)

    def reset_app(self) -> None:
        """Terminate and relaunch the app (clean state)."""
        pkg = config.device.get("app_package")
        log.info("Resetting app: %s", pkg)
        self.driver.terminate_app(pkg)
        self.driver.activate_app(pkg)
