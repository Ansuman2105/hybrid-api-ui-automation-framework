"""
retry.py
--------
Retry decorator and helpers built on top of ``tenacity``.

Provides a unified ``@retry_on_failure`` decorator that works for both
API calls and UI interactions, with configurable attempts and delay.
"""

import functools
import time
from typing import Callable, Tuple, Type

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    after_log,
)

from utils.logger import get_logger

log = get_logger(__name__)


def retry_on_failure(
    attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    Decorator — retries the wrapped function up to *attempts* times,
    with exponential back-off starting at *delay* seconds.

    Args:
        attempts:   Maximum number of total attempts (including first).
        delay:      Initial wait time between retries (seconds).
        backoff:    Multiplier applied to delay on each retry.
        exceptions: Tuple of exception types that trigger a retry.

    Example::

        @retry_on_failure(attempts=3, delay=2, exceptions=(RequestException,))
        def call_cms_api():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc: Exception = RuntimeError("Unreachable")
            wait = delay
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt < attempts:
                        log.warning(
                            "[Retry %d/%d] %s raised %s: %s — retrying in %.1fs",
                            attempt, attempts, func.__name__,
                            type(exc).__name__, exc, wait,
                        )
                        time.sleep(wait)
                        wait *= backoff
                    else:
                        log.error(
                            "[Retry %d/%d] %s failed permanently: %s",
                            attempt, attempts, func.__name__, exc,
                        )
            raise last_exc
        return wrapper
    return decorator
