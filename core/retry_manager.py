"""Retry and Fault-Tolerance Manager for Autonomous Faceless Shorts Factory.

Provides exponential backoff, jitter, retry budget tracking, and error classification
for rendering, LLM generation, API calls, and uploads.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Callable, Optional, TypeVar

logger = logging.getLogger("factory.retry_manager")

T = TypeVar("T")


class NonRetryableError(Exception):
    """Exception indicating an unrecoverable failure that should not be retried."""
    pass


class RetryManager:
    """Manages backoff and retry budget across pipeline stages."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay_seconds: float = 2.0,
        max_delay_seconds: float = 60.0,
        jitter_factor: float = 0.25,
    ):
        self.max_retries = max_retries
        self.base_delay_seconds = base_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.jitter_factor = jitter_factor

    def calculate_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with random jitter."""
        exponential = self.base_delay_seconds * (2 ** (attempt - 1))
        delay = min(self.max_delay_seconds, exponential)
        jitter = delay * self.jitter_factor * (random.random() * 2 - 1)
        return max(0.5, delay + jitter)

    def execute_with_retry(
        self,
        operation_name: str,
        func: Callable[[], T],
        max_attempts: Optional[int] = None,
        on_retry: Optional[Callable[[int, Exception, float], None]] = None,
    ) -> T:
        """Execute a callable with automated retry on transient failures."""
        attempts_limit = max_attempts if max_attempts is not None else self.max_retries
        attempt = 1

        while True:
            try:
                return func()
            except NonRetryableError as nre:
                logger.error("Non-retryable error in operation '%s': %s", operation_name, nre)
                raise
            except Exception as exc:
                if attempt >= attempts_limit:
                    logger.error(
                        "Operation '%s' exceeded maximum retry budget (%d attempts). Final error: %s",
                        operation_name,
                        attempts_limit,
                        exc,
                    )
                    raise

                delay = self.calculate_delay(attempt)
                logger.warning(
                    "Operation '%s' failed on attempt %d/%d (%s). Retrying in %.2fs...",
                    operation_name,
                    attempt,
                    attempts_limit,
                    exc,
                    delay,
                )
                if on_retry:
                    try:
                        on_retry(attempt, exc, delay)
                    except Exception as cb_err:
                        logger.error("Error executing retry callback: %s", cb_err)

                time.sleep(delay)
                attempt += 1
