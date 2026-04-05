"""
config_loader.py
----------------
Centralised configuration management for the STB Automation Framework.
Merges config.json with environment variable overrides from .env.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Resolve project root regardless of where the script is invoked from
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "config.json"
ENV_PATH = PROJECT_ROOT / "config" / ".env"

# Load .env (silently skip if missing — CI/CD injects vars directly)
load_dotenv(dotenv_path=ENV_PATH, override=False)


class ConfigLoader:
    """
    Singleton config loader that reads config.json once and exposes
    convenience accessors for all sub-sections.

    Usage::

        cfg = ConfigLoader()
        print(cfg.device["app_package"])
        print(cfg.api["base_url"])
    """

    _instance: Optional["ConfigLoader"] = None
    _config: Dict[str, Any] = {}

    def __new__(cls) -> "ConfigLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Read config.json from disk and apply env-var overrides."""
        if not CONFIG_PATH.exists():
            raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")

        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            self._config = json.load(fh)

        self._apply_env_overrides()

    def _apply_env_overrides(self) -> None:
        """
        Selectively override config values with environment variables.
        This lets CI/CD pipelines inject runtime values without touching
        the JSON file.
        """
        overrides = {
            ("appium", "server_url"): "APPIUM_SERVER_URL",
            ("device", "device_ip"): "STB_DEVICE_IP",
            ("device", "device_port"): "STB_DEVICE_PORT",
            ("api", "base_url"): "CMS_BASE_URL",
        }

        for (section, key), env_var in overrides.items():
            value = os.getenv(env_var)
            if value is not None:
                self._config.setdefault(section, {})[key] = value

    def _resolve_paths(self) -> None:
        """Convert relative reporting paths to absolute project-rooted paths."""
        reporting = self._config.get("reporting", {})
        for key in ("results_file", "screenshots_dir", "log_file"):
            if key in reporting:
                abs_path = PROJECT_ROOT / reporting[key]
                reporting[key] = str(abs_path)
                # Ensure parent directory exists
                abs_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Dot-notation-style getter.

        Example::

            cfg.get("device", "app_package")
        """
        node = self._config
        for key in keys:
            if not isinstance(node, dict):
                return default
            node = node.get(key, default)
        return node

    @property
    def appium(self) -> Dict[str, Any]:
        return self._config.get("appium", {})

    @property
    def device(self) -> Dict[str, Any]:
        return self._config.get("device", {})

    @property
    def api(self) -> Dict[str, Any]:
        return self._config.get("api", {})

    @property
    def auth(self) -> Dict[str, Any]:
        return self._config.get("auth", {})

    @property
    def reporting(self) -> Dict[str, Any]:
        cfg = self._config.get("reporting", {})
        # Resolve paths lazily on first access
        for key in ("results_file", "screenshots_dir", "log_file"):
            if key in cfg and not os.path.isabs(cfg[key]):
                cfg[key] = str(PROJECT_ROOT / cfg[key])
        return cfg

    @property
    def dashboard(self) -> Dict[str, Any]:
        return self._config.get("dashboard", {})

    @property
    def execution(self) -> Dict[str, Any]:
        return self._config.get("execution", {})

    # ------------------------------------------------------------------
    # Auth helpers — read secrets from env, never from JSON
    # ------------------------------------------------------------------

    @property
    def api_key(self) -> str:
        env_var = self.auth.get("api_key_env", "CMS_API_KEY")
        key = os.getenv(env_var, "")
        if not key:
            raise EnvironmentError(
                f"API key not found. Set the '{env_var}' environment variable."
            )
        return key

    @property
    def cms_credentials(self) -> Dict[str, str]:
        return {
            "username": os.getenv(self.auth.get("username_env", "CMS_USERNAME"), ""),
            "password": os.getenv(self.auth.get("password_env", "CMS_PASSWORD"), ""),
        }


# ---------------------------------------------------------------------------
# Module-level singleton — import this everywhere
# ---------------------------------------------------------------------------
config = ConfigLoader()
