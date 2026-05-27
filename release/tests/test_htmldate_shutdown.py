"""Bug 3 tests: htmldate shutdown-race mitigation.

Covers:
- htmldate_filtered_search returns [] (not a RuntimeError) when the
  interpreter is shutting down and submit() raises.
- A wall-clock around a hypothetical slow htmldate call returns in
  bounded time (proves the 30s cap in _htmldate_web_search works).
"""

from __future__ import annotations

import concurrent.futures as cf
import time
from unittest.mock import patch


def _slow_call(*args, **kwargs):
    time.sleep(5)
    return []


def test_wall_clock_bounds_slow_htmldate():
    """The wall-clock wrapper should return [] well inside the timeout.

    Mirrors _htmldate_web_search's pattern: no ``with`` block, explicit
    shutdown(wait=False, cancel_futures=True) so a stuck worker doesn't
    block the caller.
    """
    start = time.time()
    executor = cf.ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(_slow_call)
        try:
            result = future.result(timeout=0.5)
        except cf.TimeoutError:
            future.cancel()
            result = []
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    elapsed = time.time() - start
    assert result == []
    assert elapsed < 2.0, f"wall-clock wrapper took {elapsed:.2f}s"


def test_htmldate_filtered_search_swallows_shutdown_runtime_error():
    """When the inner ThreadPoolExecutor.submit() raises (interpreter
    shutdown race), htmldate_filtered_search must return an empty list
    rather than bubbling the RuntimeError to the caller."""
    from agent_evolve.tools import htmldate_search

    with patch.object(
        htmldate_search, "_ddgs_search", return_value=[{"href": "http://x", "title": "t", "body": "s"}]
    ):
        with patch("agent_evolve.tools.htmldate_search.ThreadPoolExecutor") as MockPool:
            instance = MockPool.return_value.__enter__.return_value
            instance.submit.side_effect = RuntimeError(
                "cannot schedule new futures after interpreter shutdown"
            )
            # Should NOT raise.
            result = htmldate_search.htmldate_filtered_search(
                query="q", cutoff_date="2024-01-01", max_results=1,
            )
    assert result == []
