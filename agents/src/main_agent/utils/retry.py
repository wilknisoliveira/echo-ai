"""Retry engine for LLM calls with exponential backoff and jitter."""

import logging
import random
import time
from collections.abc import Callable
from typing import TypeVar

import httpx
import requests
from openrouter.errors import (
    BadGatewayResponseError,
    InternalServerResponseError,
    ProviderOverloadedResponseError,
    ServiceUnavailableResponseError,
    TooManyRequestsResponseError,
)

logger = logging.getLogger(__name__)

MAX_RETRIES: int = 3
INITIAL_DELAY: float = 1.0
BACKOFF_FACTOR: float = 2.0
MAX_DELAY: float = 60.0
JITTER: bool = True


T = TypeVar("T")


def _is_transient(exc: BaseException) -> bool:
    if isinstance(
        exc,
        (
            TooManyRequestsResponseError,
            ServiceUnavailableResponseError,
            BadGatewayResponseError,
            InternalServerResponseError,
            ProviderOverloadedResponseError,
        ),
    ):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 503) or (
            500 <= exc.response.status_code < 600
        )
    if isinstance(exc, requests.HTTPError):
        if exc.response is not None:
            return exc.response.status_code in (429, 503) or (
                500 <= exc.response.status_code < 600
            )
        return True
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return True
    return False


def _get_delay(attempt: int) -> float:
    delay = min(INITIAL_DELAY * (BACKOFF_FACTOR ** (attempt - 1)), MAX_DELAY)
    if JITTER:
        delay *= 0.75 + random.random() * 0.5
    return delay


def retry_llm_call(fn: Callable[[], T]) -> T:
    """Execute an LLM call with exponential backoff retry.

    Raises the last exception if all retries are exhausted.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = fn()
            if attempt > 1:
                logger.info(
                    "LLM call succeeded on attempt %d/%d", attempt, MAX_RETRIES
                )
            return result
        except Exception as e:
            if _is_transient(e) and attempt < MAX_RETRIES:
                delay = _get_delay(attempt)
                logger.warning(
                    "LLM call failed (attempt %d/%d): %s. Retrying in %.1fs...",
                    attempt,
                    MAX_RETRIES,
                    e,
                    delay,
                )
                time.sleep(delay)
            elif attempt >= MAX_RETRIES:
                logger.error(
                    "LLM call failed after %d attempts: %s", MAX_RETRIES, e
                )
                raise
            else:
                logger.error("LLM call failed (non-transient): %s", e)
                raise

    raise AssertionError("unreachable")
