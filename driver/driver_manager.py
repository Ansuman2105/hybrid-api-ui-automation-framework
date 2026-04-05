"""
driver_manager.py
-----------------
Appium WebDriver factory and lifecycle manager for STB devices.
"""

import subprocess
import threading
import time
from typing import Optional

from appium import webdriver
from appium.options.common import AppiumOptions
from selenium.common.exceptions import WebDriverException

from config.config_loader import config
from utils.logger import get_logger

log = get_logger(__name__)

_thread_local = threading.local()


# ============================================================
# 🔥 AUTO DEVICE DETECTION (NO HARDCODE)
# ============================================================

def _get_connected_devices():
    try:
        result = subprocess.check_output(["adb", "devices"]).decode()
        devices = []

        for line in result.splitlines():
            if "device" in line and "offline" not in line and ":" in line:
                devices.append(line.split()[0])

        return devices

    except Exception as e:
        log.error("Failed to get connected devices: %s", e)
        return []


# ============================================================
# PUBLIC METHODS
# ============================================================

def get_driver(device_override: Optional[dict] = None) -> webdriver.Remote:
    existing: Optional[webdriver.Remote] = getattr(_thread_local, "driver", None)

    if existing is not None:
        try:
            _ = existing.session_id
            log.debug("Reusing existing Appium session.")
            return existing
        except WebDriverException:
            log.warning("Stale session detected — creating new one.")
            _thread_local.driver = None

    driver = _create_driver(device_override)
    _thread_local.driver = driver
    return driver


def quit_driver() -> None:
    driver: Optional[webdriver.Remote] = getattr(_thread_local, "driver", None)

    if driver:
        try:
            driver.quit()
            log.info("Appium session terminated.")
        except Exception as e:
            log.warning("Error quitting driver: %s", e)
        finally:
            _thread_local.driver = None


# ============================================================
# INTERNAL METHODS
# ============================================================

def _resolve_device(dev: dict, override: Optional[dict]):
    import os

    # Priority 1: CLI override
    if override and override.get("device_ip"):
        dev["device_ip"] = override["device_ip"]
        dev["device_port"] = override.get("device_port", 5555)
        log.info("Using device from CLI: %s", dev["device_ip"])

    # Priority 2: ENV
    elif os.getenv("DEVICE_IP"):
        dev["device_ip"] = os.getenv("DEVICE_IP")
        dev["device_port"] = int(os.getenv("DEVICE_PORT", 5555))
        log.info("Using device from ENV: %s", dev["device_ip"])

    # Priority 3: AUTO-DETECT 🔥
    else:
        devices = _get_connected_devices()

        if not devices:
            raise RuntimeError("No connected devices found via ADB")

        selected = devices[0]
        ip, port = selected.split(":")

        dev["device_ip"] = ip
        dev["device_port"] = int(port)

        log.info("Auto-selected device: %s", selected)

    return dev


def _build_capabilities(dev: dict) -> AppiumOptions:
    options = AppiumOptions()

    options.platform_name = dev["platform_name"]
    options.automation_name = dev["automation_name"]

    options.load_capabilities(
        {
            "appium:deviceName": dev["device_name"],
            "appium:udid": f"{dev['device_ip']}:{dev['device_port']}",

            "appium:appPackage": dev["app_package"],
            "appium:appActivity": "com.jio.stb.hotellauncher.ui.NavigationMainActivity",

            "appium:noReset": True,
            "appium:newCommandTimeout": 120,

            "appium:uiautomator2ServerInstallTimeout": 120000,
            "appium:uiautomator2ServerLaunchTimeout": 120000,

            "appium:disableWindowAnimation": True,
            "appium:ignoreUnimportantViews": True,
        }
    )

    log.debug("Capabilities: %s", options.to_capabilities())
    return options


def _connect_adb(device_ip: str, device_port: int):
    target = f"{device_ip}:{device_port}"

    try:
        result = subprocess.run(
            ["adb", "connect", target],
            capture_output=True,
            text=True,
            timeout=15,
        )

        output = result.stdout.strip()
        log.info("ADB connect [%s]: %s", target, output)

        if "offline" in output.lower():
            log.warning("Device offline, retrying...")
            subprocess.run(["adb", "disconnect", target])
            time.sleep(2)
            subprocess.run(["adb", "connect", target])

        return True

    except Exception as e:
        log.error("ADB error: %s", e)
        return False


def _create_driver(device_override: Optional[dict] = None) -> webdriver.Remote:
    dev = config.device.copy()

    # 🔥 Resolve device dynamically
    dev = _resolve_device(dev, device_override)

    # Connect ADB
    if not _connect_adb(dev["device_ip"], dev["device_port"]):
        raise RuntimeError(f"Could not connect to STB {dev['device_ip']}")

    options = _build_capabilities(dev)

    server_url = config.appium["server_url"]

    log.info("Connecting to Appium at %s...", server_url)

    driver = webdriver.Remote(
        command_executor=server_url,
        options=options,
    )

    driver.implicitly_wait(10)

    log.info("Session started: %s", driver.session_id)

    # ============================================================
    # 🔥 STB WAKE + LAUNCH FIX
    # ============================================================

    try:
        driver.press_keycode(26)  # POWER
        time.sleep(2)
        driver.press_keycode(3)   # HOME
        time.sleep(2)

        log.info("Device wake-up done")
    except Exception as e:
        log.warning("Wake-up failed: %s", e)

    try:
        driver.execute_script("mobile: startActivity", {
            "appPackage": "com.jio.stb.hotellauncher",
            "appActivity": "com.jio.stb.hotellauncher.ui.NavigationMainActivity"
        })
        log.info("Launcher started")
    except Exception as e:
        log.warning("Launch failed: %s", e)

    time.sleep(3)

    try:
        log.debug("Current Activity: %s", driver.current_activity)
    except:
        pass

    return driver