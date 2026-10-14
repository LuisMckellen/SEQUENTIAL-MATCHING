"""Defensive JSON adapter for the Sequential Matching evaluation harness.

Uses only the public observable state supplied in each request.  It does not
read hidden simulator data or external files.  The current policy delegates
candidate actions to the selected baseline; this module owns validation,
deadline-bounded fallback, deterministic random mode, and protocol safety
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
VALID_MODES = {"method", "greedy", "no_asks", "random"}


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
            value,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError, UnicodeError):
        return None


def _valid_memory(value: Any) -> bool:
    """Memory must be a JSON object that fits the protocol's byte limit."""
    if not isinstance(value, dict):
        return False
    encoded = _json_bytes(value)
    return encoded is not None and len(encoded) <= MAX_JSON_BYTES


def _safe_memory(value: Any) -> dict[str, Any]:
    """Return a validated memory object, otherwise an empty object."""
    return value if _valid_memory(value) else {}


def _empty_response(phase: str, memory: Any = None) -> dict[str, Any]:
    """Create the correctly shaped empty response for a known phase."""
    safe_mem = _safe_memory(memory)
    key = "pairs" if phase == MATCH_PHASE else "asks"
    response = {key: [], "memory": safe_mem}
    encoded = _json_bytes(response)
    # Memory itself can be <= 1 MiB while the enclosing response is over it.
    if encoded is None or len(encoded) > MAX_JSON_BYTES:
        response["memory"] = {}
    return response


def _response_within_limit(response: dict[str, Any]) -> bool:
    encoded = _json_bytes(response)
    return encoded is not None and len(encoded) <= MAX_JSON_BYTES


def _response_key(phase: str) -> str:
    if phase == ASK_PHASE:
        return "asks"
    if phase == MATCH_PHASE:
        return "pairs"
    raise ValueError("unknown policy phase")


def _clean_past_pairs(state: dict[str, Any]) -> set[tuple[str, str]]:
    past: set[tuple[str, str]] = set()
    introductions = state.get("introductions", [])
    if not isinstance(introductions, list):
        return past
    for intro in introductions:
        if not isinstance(intro, dict):
            continue
        a, b = intro.get("user_a"), intro.get("user_b")
        if isinstance(a, str) and isinstance(b, str) and a != b:
            past.add(tuple(sorted((a, b))))
    return past


def _validate_ask_response(
    response: Any, state: dict[str, Any]
) -> tuple[bool, dict[str, Any]]:
    """Validate an ask response atomically, including memory and JSON limits."""
    empty = _empty_response(ASK_PHASE, response.get("memory") if isinstance(response, dict) else None)
    if not isinstance(response, dict) or set(response) != {"asks", "memory"}:
        return False, empty
    if not _valid_memory(response["memory"]):
        return False, empty
    asks = response["asks"]
    if not isinstance(asks, list):
        return False, empty

    members = state.get("members", [])
    if not isinstance(members, list):
        return False, empty
    member_by_id = {
        member.get("member_id"): member
        for member in members
        if isinstance(member, dict) and isinstance(member.get("member_id"), str)
    }
    ask_budget = state.get("ask_budget_remaining", 12)
    if not isinstance(ask_budget, int) or isinstance(ask_budget, bool) or ask_budget < 0:
        return False, empty

    seen_members: set[str] = set()
    total_cost = 0
    for ask in asks:
        if not isinstance(ask, dict) or set(ask) != {"member_id", "field"}:
            return False, empty
        member_id, field = ask.get("member_id"), ask.get("field")
        if not isinstance(member_id, str) or not isinstance(field, str):
            return False, empty
        member = member_by_id.get(member_id)
        if member is None or not member.get("available", False):
            return False, empty
        if member_id in seen_members:
            return False, empty
        seen_members.add(member_id)
        if field not in ["constraints"] + SOFT:
            return False, empty

        fields = member.get("fields", {})
        statuses = member.get("field_status", {})
        if not isinstance(fields, dict) or not isinstance(statuses, dict):
            return False, empty

        if field == "constraints":
            if any(statuses.get(key) == "declined" for key in HARD):
                return False, empty
            if not any(fields.get(key) is None for key in HARD):
                return False, empty
            cost = 3
        else:
            if fields.get(field) is not None or statuses.get(field) == "declined":
                return False, empty
            cost = 1

        total_cost += cost
        if total_cost > ask_budget:
            return False, empty

    sanitized = {"asks": asks, "memory": response["memory"]}
    if not _response_within_limit(sanitized):
        return False, empty
    return True, sanitized


def _validate_match_response(
    response: Any, state: dict[str, Any]
) -> tuple[bool, dict[str, Any]]:
    """Validate a match response atomically, including exact-pair history."""
    empty = _empty_response(MATCH_PHASE, response.get("memory") if isinstance(response, dict) else None)
    if not isinstance(response, dict) or set(response) != {"pairs", "memory"}:
        return False, empty
    if not _valid_memory(response["memory"]):
        return False, empty
    pairs = response["pairs"]
    if not isinstance(pairs, list):
        return False, empty

    members = state.get("members", [])
    if not isinstance(members, list):
        return False, empty
    member_by_id = {
        member.get("member_id"): member
        for member in members
        if isinstance(member, dict) and isinstance(member.get("member_id"), str)
    }
    past_pairs = _clean_past_pairs(state)
    used: set[str] = set()

    for pair in pairs:
        if not isinstance(pair, list) or len(pair) != 2:
            return False, empty
        a, b = pair
        if not isinstance(a, str) or not isinstance(b, str) or a == b:
            return False, empty
        if a in used or b in used:
            return False, empty
        used.update((a, b))

        member_a, member_b = member_by_id.get(a), member_by_id.get(b)
        if member_a is None or member_b is None:
            return False, empty
        if not member_a.get("available", False) or not member_b.get("available", False):
            return False, empty
        if tuple(sorted((a, b))) in past_pairs:
            return False, empty
        try:
            result = eligibility(member_a, member_b)
        except Exception:
            return False, empty
        if not isinstance(result, dict) or result.get("status") != "feasible":
            return False, empty

    sanitized = {"pairs": pairs, "memory": response["memory"]}
    if not _response_within_limit(sanitized):
        return False, empty
    return True, sanitized


def _random_match(state: dict[str, Any]) -> list[list[str]]:
    """Return deterministic random feasible pairs for an identical state."""
    members = [
        member
        for member in state.get("members", [])
        if isinstance(member, dict) and member.get("available", False)
    ]
    past = _clean_past_pairs(state)
    edges: list[tuple[str, str]] = []
    for a, b in itertools.combinations(members, 2):
        aid, bid = a.get("member_id"), b.get("member_id")
        if not isinstance(aid, str) or not isinstance(bid, str) or aid == bid:
            continue
        pair = tuple(sorted((aid, bid)))
        if pair in past:
            continue
        try:
            result = eligibility(a, b)
        except Exception:
            continue
        if isinstance(result, dict) and result.get("status") == "feasible":
            edges.append(pair)

    # Hash canonical observable state rather than Python's process-randomized hash().
    state_bytes = _json_bytes(state)
    digest = hashlib.sha256(state_bytes if state_bytes is not None else b"{}").digest()
    seed = int.from_bytes(digest[:16], "big")
    random.Random(seed).shuffle(edges)

    used: set[str] = set()
    result: list[list[str]] = []
    for a, b in edges:
        if a not in used and b not in used:
            result.append([a, b])
            used.update((a, b))
    return result


# ---------------------------------------------------------------------------
# Our method (mode "method", the default when no --baseline is given).
# Observable state only. Components enter under the Section 6 admission rule;
# see README "Method" for the runs that admitted or cut each one.
# ---------------------------------------------------------------------------

USE_BLOSSOM = True       # L1: whole-pool maximum-weight matching instead of greedy
USE_VALUE_ASKS = False   # L2: cut (loss in sparse MSMI on seeds 1201-1220); list-order asks are kept


def _soft_score(a: dict[str, Any], b: dict[str, Any]) -> int:
    """The supplied baseline's score: number of equal, known soft fields."""
    return sum(a["fields"].get(k) is not None and a["fields"].get(k) == b["fields"].get(k) for k in SOFT)


def _blossom_match(state: dict[str, Any]) -> list[list[str]]:
    """Maximum-weight matching over every feasible, never-introduced pair (weight 1 + soft score)."""
    members = [m for m in state["members"] if m.get("available")]
    past = _clean_past_pairs(state)
    edges = []
    for a, b in itertools.combinations(members, 2):
        key = tuple(sorted((a["member_id"], b["member_id"])))
        if key in past or eligibility(a, b)["status"] != "feasible":
            continue
        edges.append((key[0], key[1], 1.0 + _soft_score(a, b)))
    degree: dict[str, int] = {}
    for a, b, _ in edges:
        degree[a] = degree.get(a, 0) + 1
        degree[b] = degree.get(b, 0) + 1
    if all(degree[a] == 1 and degree[b] == 1 for a, b, _ in edges):
        # Every feasible pair is isolated, so the maximum-weight matching is all of them.
        # This skips importing networkx (about 0.4 s) on most days.
        return sorted([a, b] for a, b, _ in edges)
    import networkx as nx  # imported lazily; any failure falls back to the greedy baseline

    graph = nx.Graph()
    graph.add_weighted_edges_from(edges)
    return sorted(sorted(p) for p in nx.max_weight_matching(graph))


def _value_asks(state: dict[str, Any]) -> list[dict[str, str]]:
    """Ask constraints of the members whose answer could unlock the most partners."""
    members = state["members"]
    declined = lambda m: any(m["field_status"][k] == "declined" for k in HARD)
    missing = lambda m: any(m["fields"][k] is None for k in HARD)
    candidates = [m for m in members if m.get("available") and missing(m) and not declined(m)]
    known = [m for m in members if not missing(m)]
    unknown = [m for m in members if missing(m) and not declined(m)]
    scored = []
    for m in candidates:
        ok = lambda j: j["member_id"] != m["member_id"] and eligibility(m, j)["status"] != "infeasible"
        score = (sum(1 for j in known if j.get("available") and ok(j))
                 + 0.5 * sum(1 for j in known if ok(j)) + 0.2 * sum(1 for j in unknown if ok(j)))
        scored.append((score, m["member_id"]))
    scored.sort(reverse=True)
    budget = int(state.get("ask_budget_remaining", 0)) // 3
    return [{"member_id": i, "field": "constraints"} for score, i in scored[:budget] if score > 0]


def _method_actions(state: dict[str, Any], phase: str) -> list[Any]:
    if phase == ASK_PHASE:
        return _value_asks(state) if USE_VALUE_ASKS else baseline_asks(state)
    return _blossom_match(state) if USE_BLOSSOM else baseline_match(state)


def _get_actions_for_mode(
    state: dict[str, Any], phase: str, baseline_name: str = "greedy"
) -> list[Any]:
    """Get the selected baseline's actions for the current phase."""
    if baseline_name == "method":
        return _method_actions(state, phase)
    if phase == ASK_PHASE:
        if baseline_name == "no_asks":
            return []
        return baseline_asks(state)
    if phase != MATCH_PHASE:
        raise ValueError("unknown policy phase")
    if baseline_name == "random":
        return _random_match(state)
    # The no_asks baseline suppresses clarification only; matching is greedy.
    return baseline_match(state)


def _fallback_actions(state: dict[str, Any], phase: str, mode: str) -> list[Any]:
    """Safe supplied baseline used only when candidate generation/validation fails."""
    if phase == ASK_PHASE:
        return [] if mode == "no_asks" else baseline_asks(state)
    # Use the simple, deterministic greedy matcher as the safe match fallback.
    return baseline_match(state)


def _try_actions(
    state: dict[str, Any],
    phase: str,
    actions_fn: Callable[[], list[Any]],
    trusted_memory: dict[str, Any],
) -> tuple[list[Any], dict[str, Any]]:
    """Generate, validate, and strictly size-check a candidate inside its timer."""
    actions = actions_fn()
    key = _response_key(phase)
    response = {key: actions, "memory": trusted_memory}
    validator = _validate_ask_response if phase == ASK_PHASE else _validate_match_response
    ok, sanitized = validator(response, state)
    if not ok:
        raise _InvalidResponse("candidate failed validation")
    # Validators check the complete envelope too; serialize once more to ensure
    # the exact final object remains safe if this code is later extended.
    encoded = _json_bytes(sanitized)
    if encoded is None or len(encoded) > MAX_JSON_BYTES:
        raise _InvalidResponse("candidate exceeds the JSON protocol limit")
    return sanitized[key], sanitized["memory"]


def _run_phase_with_fallback(
    state: dict[str, Any],
    phase: str,
    baseline_name: str,
    incoming_memory: dict[str, Any],
) -> tuple[list[Any], dict[str, Any]]:
    """Run primary and safe-baseline stages within one total decision budget.

    The absolute deadline bounds the whole chain. The primary stage has a
    shorter slice so time remains for a bounded baseline fallback and final
    serialization. If either stage hangs, its signal interrupts it on Linux.
    """
    started = time.monotonic()
    deadline = started + TOTAL_DECISION_SECONDS
    memory = _safe_memory(incoming_memory)

    primary_seconds = min(
        PRIMARY_STAGE_SECONDS,
        max(0.0, deadline - time.monotonic() - FALLBACK_STAGE_SECONDS - FINAL_RESERVE_SECONDS),
    )
    try:
        actions, out_memory = _run_limited(
            lambda: _try_actions(
                state, phase,
                lambda: _get_actions_for_mode(state, phase, baseline_name),
                memory,
            ),
            primary_seconds,
        )
        return actions, out_memory
    except _DeadlineError:
        pass
    except Exception:
        # A candidate exception/timeout is recoverable; proceed only if enough
        # of the absolute budget remains for the fallback and output envelope.
        pass

    remaining = deadline - time.monotonic()
    fallback_seconds = min(
        FALLBACK_STAGE_SECONDS,
        max(0.0, remaining - FINAL_RESERVE_SECONDS),
    )
    if fallback_seconds > 0:
        try:
            return _run_limited(
                lambda: _try_actions(
                    state, phase,
                    lambda: _fallback_actions(state, phase, baseline_name),
                    memory,
                ),
                fallback_seconds,
            )
        except _DeadlineError:
            pass
        except Exception:
            pass

    # Preserve validated input memory through failure when the complete response
    # still fits. If not, return a minimal response valid under the 1 MiB cap.
    fallback = _empty_response(phase, memory)
    return fallback[_response_key(phase)], fallback["memory"]


def decide(request: Any, mode: str = "greedy") -> dict[str, Any]:
    """Evaluate one request and always return a bounded, protocol-shaped object."""
    phase = request.get("phase") if isinstance(request, dict) else None
    if phase not in (ASK_PHASE, MATCH_PHASE):
        # The protocol specifies only ask/match; use the safe ask envelope for
        # malformed/unknown requests because a phase-specific envelope is unknown.
        return _empty_response(ASK_PHASE)

    raw_request = _json_bytes(request)
    if raw_request is None or len(raw_request) > MAX_JSON_BYTES:
        return _empty_response(phase)

    state = request.get("state")
    if not isinstance(state, dict):
        return _empty_response(phase, request.get("memory"))

    mode = mode if mode in VALID_MODES else "greedy"
    incoming_memory = _safe_memory(request.get("memory"))
    actions, memory = _run_phase_with_fallback(
        state, phase, mode, incoming_memory
    )
    response = {_response_key(phase): actions, "memory": memory}
    encoded = _json_bytes(response)
    if encoded is None or len(encoded) > MAX_JSON_BYTES:
        response = _empty_response(phase, incoming_memory)
    # Final guard: the CLI writes these strict bytes directly; no NaN/Infinity
    # can leak through and no complete response can exceed the protocol cap.
    encoded = _json_bytes(response)
    if encoded is None or len(encoded) > MAX_JSON_BYTES:
        response = _empty_response(phase)
    return response


def _parse_strict_json(raw: bytes) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError("non-finite JSON token: " + value)
    return json.loads(raw.decode("utf-8"), parse_constant=reject_constant)


def _emit(response: dict[str, Any]) -> None:
    encoded = _json_bytes(response)
    if encoded is None or len(encoded) > MAX_JSON_BYTES:
        encoded = b'{"asks":[],"memory":{}}'
    sys.stdout.buffer.write(encoded + b"\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--baseline", choices=sorted(VALID_MODES), default="method"
    )
    args = parser.parse_args(argv)

    # Read at most LIMIT+1 bytes to enforce the request size before parsing.
    try:
        raw = sys.stdin.buffer.read(MAX_JSON_BYTES + 1)
    except Exception:
        _emit(_empty_response(ASK_PHASE))
        return 0

    if len(raw) > MAX_JSON_BYTES:
        _emit(_empty_response(ASK_PHASE))
        return 0

    try:
        request = _parse_strict_json(raw)
    except (UnicodeError, ValueError, TypeError, RecursionError):
        _emit(_empty_response(ASK_PHASE))
        return 0

    phase = request.get("phase") if isinstance(request, dict) else None
    response = decide(request, args.baseline)
    if phase not in (ASK_PHASE, MATCH_PHASE):
        response = _empty_response(ASK_PHASE)
    _emit(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
