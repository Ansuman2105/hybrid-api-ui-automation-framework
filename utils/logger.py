"""
logger.py
---------
Centralised logging factory for the STB Automation Framework.

Features
~~~~~~~~
* Colourised console output via colorlog
* Rotating file handler (10 MB cap, 5 backups)
* ISO-8601 timestamps
* Per-module logger names for easy filtering
* Thread-safe (Python's logging module is inherently thread-safe)
"""

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional

import colorlog

from config.config_loader import config

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_LOG_FILE = Path(config.reporting.get("log_file", "logs/automation.log"))
_LOG_LEVEL_STR = config.reporting.get("log_level", "DEBUG").upper()
_LOG_LEVEL = getattr(logging, _LOG_LEVEL_STR, logging.DEBUG)
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_BACKUP_COUNT = 5

_CONSOLE_FORMAT = (
    "%(log_color)s%(asctime)s [%(levelname)-8s] %(name)s:%(lineno)d — %(message)s%(reset)s"
)
_FILE_FORMAT = (
    "%(asctime)s [%(levelname)-8s] %(name)s:%(lineno)d — %(message)s"
)
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

_LOG_COLORS = {
    "DEBUG": "cyan",
    "INFO": "green",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "bold_red",
}

# ---------------------------------------------------------------------------
# Internal: ensure log directory exists
# ---------------------------------------------------------------------------
_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Module-level registry so we never duplicate handlers
# ---------------------------------------------------------------------------
_CONFIGURED: set = set()


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Return a named logger with console + rotating file handlers.

    Args:
        name: Logger name — typically ``__name__`` of the calling module.

    Returns:
        Configured :class:`logging.Logger` instance.

    Example::

        from utils.logger import get_logger
        log = get_logger(__name__)
        log.info("Driver initialised on %s", device_name)
    """
    logger = logging.getLogger(name or "stb_framework")

    # Avoid adding duplicate handlers in pytest's multi-import environment
    if name in _CONFIGURED:
        return logger

    logger.setLevel(_LOG_LEVEL)
    logger.propagate = False  # Don't bubble up to root logger

    # --- Console handler (colourised) ---
    console_handler = colorlog.StreamHandler()
    console_handler.setLevel(_LOG_LEVEL)
    console_handler.setFormatter(
        colorlog.ColoredFormatter(
            _CONSOLE_FORMAT,
            datefmt=_DATE_FORMAT,
            log_colors=_LOG_COLORS,
        )
    )

    # --- Rotating file handler ---
    file_handler = logging.handlers.RotatingFileHandler(
        filename=_LOG_FILE,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(_LOG_LEVEL)
    file_handler.setFormatter(
        logging.Formatter(_FILE_FORMAT, datefmt=_DATE_FORMAT)
    )

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    _CONFIGURED.add(name)

    return logger


# ---------------------------------------------------------------------------
# Convenience: framework-level root logger
# ---------------------------------------------------------------------------
framework_log = get_logger("stb_framework")
