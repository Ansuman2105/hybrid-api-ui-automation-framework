from typing import Optional
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from utils.logger import get_logger
import time

log = get_logger(__name__)


class LauncherPage:

    # Stable locator from Inspector
    _LOC_GUEST_NAME = (AppiumBy.ID, "com.jio.stb.hotellauncher:id/header_title1")

    def __init__(self, driver: webdriver.Remote) -> None:
        self.driver = driver

    # 🔥 Robust launcher wait (STB safe)
    def wait_for_launcher(self, timeout: int = 40) -> None:
        log.info("Waiting for launcher...")

        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(self._LOC_GUEST_NAME)
            )

            # Extra small wait for text rendering (VERY IMPORTANT for STB)
            time.sleep(2)

            log.info("✅ Launcher ready.")

        except TimeoutException:
            log.error("❌ Launcher did not load in time")
            log.debug(self.driver.page_source[:1000])
            raise

    # 🔥 Smart text extraction (handles empty/delay issues)
    def get_guest_name_from_ui(self, timeout: int = 15) -> Optional[str]:
        try:
            el = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(self._LOC_GUEST_NAME)
            )

            # Retry logic for delayed text rendering
            for i in range(3):
                text = el.text.strip()

                if text:
                    log.info("✅ UI text found: '%s'", text)
                    return text

                log.warning("Text empty, retrying... (%d/3)", i + 1)
                time.sleep(1)

            # Fallback → try attribute (some STB use content-desc)
            alt_text = el.get_attribute("content-desc")
            if alt_text:
                log.info("✅ Fallback content-desc: '%s'", alt_text)
                return alt_text.strip()

            log.warning("⚠️ Text still empty after retries")
            return None

        except TimeoutException:
            log.error("❌ Guest name element not found")
            log.debug(self.driver.page_source[:1000])
            return None

    # 🎮 STB-specific focus helper (VERY USEFUL)
    def ensure_focus(self):
        log.info("Ensuring focus on screen...")
        try:
            self.driver.press_keycode(20)  # DPAD_DOWN
            time.sleep(1)
            self.driver.press_keycode(19)  # DPAD_UP
            time.sleep(1)
        except Exception as e:
            log.warning("Focus adjustment failed: %s", e)