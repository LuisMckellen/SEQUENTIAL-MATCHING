"""Defensive JSON adapter for the Sequential Matching evaluation harness.

Uses only the public observable state supplied in each request.  It does not
read hidden simulator data or external files.  The current policy delegates
candidate actions to the selected baseline; this module owns validation,
deadline-bounded fallback, deterministic random mode, and protocol safety.
Python >= 3.10; standard library only (plus the repository's kit.py).
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
import signal
import sys
import time
from typing import Any, Callable

from kit import HARD, SOFT, baseline_asks, baseline_match, eligibility


MAX_JSON_BYTES = 1024 * 1024
# The evaluator kills invocations at 10s. Leave a margin for output and process exit.
TOTAL_DECISION_SECONDS = 6.5
PRIMARY_STAGE_SECONDS = 4.5
FALLBACK_STAGE_SECONDS = 1.4
FINAL_RESERVE_SECONDS = 0.3

ASK_PHASE = "ask"
MATCH_PHASE = "match"
VALID_MODES = {"greedy", "no_asks", "random"}


class _DeadlineError(Exception):
    """Raised when a bounded policy stage runs out of time."""


class _InvalidResponse(Exception):
    """Raised internally when a candidate response fails validation."""


def _deadline_supported() -> bool:
    """Whether the current platform supports interrupting calls with SIGALRM."""
    return all(
        hasattr(signal, name)
        for name in ("SIGALRM", "ITIMER_REAL", "setitimer", "getitimer")
    )


def _deadline_handler(_signum: int, _frame: Any) -> None:
    raise _DeadlineError("policy stage deadline exceeded")


def _run_limited(fn: Callable[[], Any], timeout_seconds: float) -> Any:
    """Run ``fn`` under a stage alarm, restoring any prior alarm/handler.

    The evaluator runs this policy on Linux, where SIGALRM interrupts CPU-bound
    Python loops. On platforms without SIGALRM this function can only detect an
    overrun after the call returns; the external process timeout remains the
    hard limit there.
    """
    if timeout_seconds <= 0:
        raise _DeadlineError("no time remains for policy stage")

    if not _deadline_supported():
        started = time.monotonic()
        result = fn()
        if time.monotonic() - started > timeout_seconds:
            raise _DeadlineError("policy stage deadline exceeded")
        return result

    old_handler = signal.getsignal(signal.SIGALRM)
    old_remaining, old_interval = signal.getitimer(signal.ITIMER_REAL)
    started = time.monotonic()
    signal.signal(signal.SIGALRM, _deadline_handler)
    signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
    try:
        return fn()
    finally:
        elapsed = time.monotonic() - started
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        signal.signal(signal.SIGALRM, old_handler)
        # Restore a pre-existing timer with its remaining duration adjusted for
        # the time spent inside this call. Never resurrect an expired timer.
        if old_remaining > elapsed:
            signal.setitimer(
                signal.ITIMER_REAL, old_remaining - elapsed, old_interval
            )


def _json_bytes(value: Any) -> bytes | None:
    """Return strict, deterministic UTF-8 JSON bytes, or None if invalid."""
    try:
        return json.dumps(
