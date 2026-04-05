"""
n8n_notifier.py
---------------
Python client that posts events FROM pytest hooks / test code INTO n8n
webhook workflows. Used when you want the framework to push events to n8n
rather than n8n pulling from the webhook server.

Use cases
~~~~~~~~~
* Notify n8n when a test suite starts (so it can update a status board)
* Send individual test failures to n8n in real-time (not just at end)
* Trigger downstream n8n workflows (e.g. "raise Jira ticket on FAIL")
* Heartbeat pings so n8n knows the test runner is alive
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests
from requests.exceptions import RequestException

from utils.logger import get_logger

log = get_logger(__name__)

# ── Config ────────────────────────────────────────────────────────────────
_N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5678")
_N8N_WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "stb-n8n-secret-changeme")
_TIMEOUT = 10  # seconds — never block the test runner for long


class N8NNotifier:
    """
    Sends structured events to n8n webhook triggers.

    All methods are fire-and-forget: they log failures but never
    raise exceptions so that notification issues never break tests.

    Args:
        base_url: n8n instance URL (default: http://localhost:5678)
        secret:   Webhook secret header value.

    Example::

        notifier = N8NNotifier()
        notifier.test_suite_started(markers="regression", total_collected=42)
        # ... tests run ...
        notifier.test_failed("tests/test_foo.py::test_bar", "AssertionError: ...")
        notifier.test_suite_finished(summary={"passed": 40, "failed": 2})
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        secret: Optional[str] = None,
    ) -> None:
        self.base_url = (base_url or _N8N_BASE_URL).rstrip("/")
        self._headers = {
            "Content-Type": "application/json",
            "X-Webhook-Secret": secret or _N8N_WEBHOOK_SECRET,
        }

    # ------------------------------------------------------------------
    # High-level event methods
    # ------------------------------------------------------------------

    def test_suite_started(
        self,
        markers: str = "",
        total_collected: int = 0,
        device: str = "",
        extra: Optional[Dict] = None,
    ) -> None:
        """Notify n8n that a test suite run has begun."""
        self._post(
            path="/webhook/stb-suite-started",
            payload={
                "event": "suite_started",
                "markers": markers,
                "total_collected": total_collected,
                "device": device,
                **(extra or {}),
            },
        )

    def test_suite_finished(
        self,
        summary: Dict[str, Any],
        run_id: str = "",
        extra: Optional[Dict] = None,
    ) -> None:
        """Notify n8n that the suite has finished with a summary."""
        self._post(
            path="/webhook/stb-suite-finished",
            payload={
                "event": "suite_finished",
                "summary": summary,
                "run_id": run_id,
                "has_failures": summary.get("failed", 0) > 0 or summary.get("errors", 0) > 0,
                **(extra or {}),
            },
        )

    def test_failed(
        self,
        test_name: str,
        error_msg: str = "",
        screenshot: Optional[str] = None,
        duration_sec: float = 0.0,
        extra: Optional[Dict] = None,
    ) -> None:
        """
        Notify n8n about a single test failure in real-time.
        This fires immediately when a test fails, useful for fast Slack/email alerts.
        """
        self._post(
            path="/webhook/stb-test-failed",
            payload={
                "event": "test_failed",
                "test_name": test_name,
                "error_msg": error_msg[:500] if error_msg else "",
                "screenshot": screenshot,
                "duration_sec": duration_sec,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **(extra or {}),
            },
        )

    def tile_verified(
        self,
        tile_id: str,
        tile_title: str,
        status: str,
        duration_sec: float = 0.0,
    ) -> None:
        """
        Notify n8n of a tile verification outcome.
        n8n can use this to update the CMS tile record.
        """
        self._post(
            path="/webhook/stb-tile-verified",
            payload={
                "event": "tile_verified",
                "tile_id": tile_id,
                "tile_title": tile_title,
                "status": status,
                "duration_sec": duration_sec,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    def heartbeat(self, message: str = "alive") -> None:
        """Ping n8n to signal the test runner is alive (useful in long runs)."""
        self._post(
            path="/webhook/stb-heartbeat",
            payload={
                "event": "heartbeat",
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _post(self, path: str, payload: Dict[str, Any]) -> None:
        """
        POST payload to an n8n webhook path.
        Silently logs on failure — never raises.
        """
        url = f"{self.base_url}{path}"
        try:
            resp = requests.post(
                url,
                json=payload,
                headers=self._headers,
                timeout=_TIMEOUT,
            )
            log.debug("n8n notify [%s] → %d", path, resp.status_code)
        except RequestException as exc:
            # Never fail a test because n8n is unreachable
            log.debug("n8n notify failed (non-critical): %s — %s", url, exc)


# ── Module-level singleton ────────────────────────────────────────────────
notifier = N8NNotifier()
