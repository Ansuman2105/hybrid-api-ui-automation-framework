"""
reporter.py
-----------
Thread-safe, append-safe JSON reporter for the STB Automation Framework.

Schema per result entry
~~~~~~~~~~~~~~~~~~~~~~~
{
    "test_name":    str,
    "status":       "PASS" | "FAIL" | "ERROR" | "SKIP",
    "duration_sec": float,
    "timestamp":    str  (ISO-8601),
    "device":       str,
    "screenshot":   str | null,
    "error_msg":    str | null,
    "tags":         list[str]
}
"""

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.config_loader import config
from utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------
_RESULTS_FILE = Path(config.reporting.get("results_file", "reports/results.json"))
_RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)

# One lock per process — safe for pytest-xdist workers via file-level locking
_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def write_result(
    test_name: str,
    status: str,
    duration_sec: float,
    device: str = "",
    screenshot: Optional[str] = None,
    error_msg: Optional[str] = None,
    tags: Optional[List[str]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Append a single test result to ``reports/results.json``.

    The function is *append-safe*: it reads the current file, appends the
    new record, then writes the whole list back atomically via a temp-file
    rename.  This prevents corruption when multiple pytest-xdist workers
    write simultaneously (each holds a thread lock and retries on
    ``JSONDecodeError``).

    Args:
        test_name:    Fully-qualified pytest node id or human-readable name.
        status:       One of PASS / FAIL / ERROR / SKIP.
        duration_sec: Wall-clock execution time in seconds.
        device:       Device name / IP for traceability.
        screenshot:   Relative path to screenshot file (or None).
        error_msg:    Exception message if status is FAIL/ERROR.
        tags:         Optional list of test tags/markers.
        extra:        Any additional key-value pairs to include.
    """
    record: Dict[str, Any] = {
        "test_name": test_name,
        "status": status.upper(),
        "duration_sec": round(duration_sec, 3),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device": device or config.device.get("device_name", "unknown"),
        "screenshot": screenshot,
        "error_msg": error_msg,
        "tags": tags or [],
    }
    if extra:
        record.update(extra)

    _append_to_file(record)
    log.info("Result recorded: [%s] %s (%.2fs)", status.upper(), test_name, duration_sec)


def _append_to_file(record: Dict[str, Any]) -> None:
    """Read → append → write-back with thread locking and retry."""
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        with _LOCK:
            try:
                existing: List[Dict] = _read_results()
                existing.append(record)
                _write_results(existing)
                return
            except (json.JSONDecodeError, OSError) as exc:
                log.warning(
                    "Write attempt %d/%d failed: %s", attempt, max_retries, exc
                )
                if attempt == max_retries:
                    log.error("Failed to persist result after %d attempts.", max_retries)
                    raise
                time.sleep(0.1 * attempt)


def _read_results() -> List[Dict]:
    """Return existing results list or empty list if file absent/empty."""
    if not _RESULTS_FILE.exists() or _RESULTS_FILE.stat().st_size == 0:
        return []
    with open(_RESULTS_FILE, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_results(results: List[Dict]) -> None:
    """Atomic write via temp file + rename (POSIX guarantee)."""
    tmp = _RESULTS_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)
    tmp.replace(_RESULTS_FILE)


def read_results() -> List[Dict]:
    """Public read accessor for the dashboard and utilities."""
    with _LOCK:
        return _read_results()


def clear_results() -> None:
    """Reset the results file (useful for a fresh test run)."""
    with _LOCK:
        _write_results([])
    log.info("Results file cleared: %s", _RESULTS_FILE)


def summarise(results: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """
    Return a summary dict from the results list.

    Returns::

        {
            "total": int,
            "passed": int,
            "failed": int,
            "errors": int,
            "skipped": int,
            "pass_pct": float,
        }
    """
    data = results if results is not None else read_results()
    total = len(data)
    passed = sum(1 for r in data if r.get("status") == "PASS")
    failed = sum(1 for r in data if r.get("status") == "FAIL")
    errors = sum(1 for r in data if r.get("status") == "ERROR")
    skipped = sum(1 for r in data if r.get("status") == "SKIP")
    pass_pct = round((passed / total * 100), 1) if total else 0.0

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
        "pass_pct": pass_pct,
    }
