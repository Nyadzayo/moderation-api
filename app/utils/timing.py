"""Timing utilities for measuring processing time."""

import time
from contextlib import contextmanager
from typing import Generator


@contextmanager
def timer() -> Generator[dict, None, None]:
    """
    Context manager to measure elapsed time.

    Yields:
        dict: Dictionary with 'elapsed_ms' key updated with elapsed time in milliseconds

    Example:
        >>> with timer() as t:
        ...     # do something
        ...     pass
        >>> print(t['elapsed_ms'])
    """
    result = {"elapsed_ms": 0}
    start = time.perf_counter()
    try:
        yield result
    finally:
        end = time.perf_counter()
        result["elapsed_ms"] = int((end - start) * 1000)


def get_current_timestamp_iso() -> str:
    """
    Get current timestamp in ISO 8601 UTC format.

    Returns:
        str: Current timestamp (e.g., '2025-09-29T22:10:05.123Z')
    """
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"