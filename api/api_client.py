"""
api_client.py
-------------
Base HTTP client for all CMS / backend API interactions.

Features
~~~~~~~~
* Shared ``requests.Session`` with connection pooling
* Bearer-token and API-key authentication
* Automatic retry with exponential back-off (via tenacity)
* Structured error handling and logging
* Timeout enforcement on every request
"""

import os
from typing import Any, Dict, Optional
from wsgiref import headers

import requests
from requests import Response, Session
from requests.adapters import HTTPAdapter
from requests.exceptions import (
    ConnectionError,
    HTTPError,
    RequestException,
    Timeout,
)
from urllib3.util.retry import Retry

from config.config_loader import config
from utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_DEFAULT_TIMEOUT = config.api.get("timeout", 30)
_RETRY_ATTEMPTS = config.api.get("retry_attempts", 3)
_RETRY_DELAY = config.api.get("retry_delay", 2)

# HTTP status codes that warrant an automatic retry
_RETRY_STATUS_CODES = (429, 500, 502, 503, 504)


class APIClient:
    """
    Reusable HTTP client wrapping ``requests.Session``.

    Args:
        base_url:    Override the ``config.json`` base URL.
        api_key:     Override the API key (defaults to env var).
        extra_headers: Additional headers merged with defaults.

    Example::

        client = APIClient()
        resp = client.post("/tiles", json={"title": "My Tile"})
        resp.raise_for_status()
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.base_url = (base_url or config.api["base_url"]).rstrip("/")
        self._session = self._build_session(api_key, extra_headers)
        log.debug("APIClient initialised: base_url=%s", self.base_url)

    # ------------------------------------------------------------------
    # Session factory
    # ------------------------------------------------------------------

    def _build_session(
        self,
        api_key: Optional[str],
        extra_headers: Optional[Dict[str, str]],
    ) -> Session:
        session = requests.Session()

        # --- Default headers ---
        default_headers = dict(config.api.get("headers", {}))

        # Resolve API key
        resolved_key = api_key or os.getenv(
            config.auth.get("api_key_env", "CMS_API_KEY"), ""
        )
        if resolved_key:
            default_headers["Authorization"] = f"Bearer {resolved_key}"
            default_headers["X-API-Key"] = resolved_key

        if extra_headers:
            default_headers.update(extra_headers)

        session.headers.update(default_headers)

        # --- Retry adapter ---
        retry_strategy = Retry(
            total=_RETRY_ATTEMPTS,
            backoff_factor=_RETRY_DELAY,
            status_forcelist=_RETRY_STATUS_CODES,
            allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20,
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    # ------------------------------------------------------------------
    # HTTP verb wrappers
    # ------------------------------------------------------------------

    def get(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        **kwargs,
    ) -> Response:
        return self._request("GET", endpoint, params=params, **kwargs)

    def post(
        self,
        endpoint: str,
        json: Optional[Dict] = None,
        data: Optional[Any] = None,
        **kwargs,
    ) -> Response:
        return self._request("POST", endpoint, json=json, data=data, **kwargs)

    def put(
        self,
        endpoint: str,
        json: Optional[Dict] = None,
        **kwargs,
    ) -> Response:
        return self._request("PUT", endpoint, json=json, **kwargs)

    def patch(
        self,
        endpoint: str,
        json: Optional[Dict] = None,
        **kwargs,
    ) -> Response:
        return self._request("PATCH", endpoint, json=json, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> Response:
        return self._request("DELETE", endpoint, **kwargs)

    # ------------------------------------------------------------------
    # Core request dispatcher
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        endpoint: str,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> Response:
        """
        Dispatch an HTTP request and handle common failure modes.

        Args:
            method:   HTTP verb.
            endpoint: Path appended to ``base_url`` (leading slash optional).
            timeout:  Override default timeout.

        Returns:
            :class:`requests.Response`

        Raises:
            requests.exceptions.HTTPError: On 4xx/5xx after exhausting retries.
            requests.exceptions.ConnectionError: If server unreachable.
            requests.exceptions.Timeout: If request exceeds timeout.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        effective_timeout = timeout or _DEFAULT_TIMEOUT

        log.debug("→ %s %s  kwargs=%s", method, url, {k: v for k, v in kwargs.items() if k != "json"})

        try:
            print("FINAL URL:", url)
            print("HEADERS:", headers)
            response = self._session.request(
                method=method,
                url=url,
                timeout=effective_timeout,
                **kwargs,
            )
            log.debug(
                "← %s %s  status=%d  len=%d",
                method, url, response.status_code, len(response.content),
            )
            response.raise_for_status()
            return response

        except HTTPError as exc:
            log.error(
                "HTTP error %s %s: %s — body: %s",
                method, url, exc, exc.response.text[:500] if exc.response else "",
            )
            raise
        except Timeout:
            log.error("Request timed out after %ds: %s %s", effective_timeout, method, url)
            raise
        except ConnectionError as exc:
            log.error("Connection error %s %s: %s", method, url, exc)
            raise
        except RequestException as exc:
            log.error("Request failed %s %s: %s", method, url, exc)
            raise

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying connection pool."""
        self._session.close()
        log.debug("APIClient session closed.")

    def __enter__(self) -> "APIClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()
