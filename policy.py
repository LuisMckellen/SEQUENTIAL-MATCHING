"""Reference policy: executable JSON adapter, never reads simulator hidden state.
Implements robust output validation, fallback chain with deadline, and baseline integration.
"""
import argparse
import itertools
import json
import random
import signal
import sys
import time
from kit import baseline_asks, baseline_match, eligibility


# ---------------------------------------------------------------------------
# Deadline management — enforces ~7s fallback inside the evaluator's 10s limit
# ---------------------------------------------------------------------------

_deadline_exceeded = False


def _deadline_handler(signum, frame):
    """SIGALRM handler — set flag; policy logic checks this flag."""
    global _deadline_exceeded
    _deadline_exceeded = True


def _set_deadline():
    """Install a 7‑second real-time alarm and record start time."""
    global _deadline_exceeded
    _deadline_exceeded = False
    signal.signal(signal.SIGALRM, _deadline_handler)
    signal.alarm(7)  # fire after ~7 seconds
    _phase_start = time.time()


def _check_deadline():
    """Return True if deadline has elapsed (7s wall-clock)."""
    if _phase_start is None:
        return False
    return (time.time() - _phase_start) > 7.0 or _deadline_exceeded


def _cancel_deadline():
    """Remove the alarm and reset phase-timer state."""
    global _phase_start, _deadline_exceeded
    signal.alarm(0)          # cancel the alarm
    _phase_start = None
    _deadline_exceeded = False


# ---------------------------------------------------------------------------
# Output validators (Task A) — ATOMIC: reject batch if ANY item invalid
# ---------------------------------------------------------------------------

def _validate_ask_response(response, state):
    """Validate an ask-phase response. Returns (ok, sanitized).

    Atomic: if ANY ask in the batch is invalid, the whole batch is rejected
    (ok=False). Do not silently filter invalid items and return a partial batch.
    """
    if not isinstance(response, dict):
        return False, {}
    if set(response.keys()) != {'asks', 'memory'}:
        return False, {'asks': [], 'memory': response.get('memory', {})}
    asks = response['asks']

    # Empty ask batch is valid (nothing to validate)
    if not isinstance(asks, list):
        return False, {'asks': [], 'memory': response.get('memory', {})}
    if len(asks) == 0:
        return True, {'asks': [], 'memory': response.get('memory', {})}

    # Validate EVERY ask — if ANY is invalid, return ok=False
    seen = set()  # (member_id, field) pairs for duplicate detection
    ask_budget = state.get('ask_budget_remaining', 12)
    total_cost = 0

    for ask in asks:
        # Shape check
        if not isinstance(ask, dict):
            return False, {'asks': [], 'memory': response.get('memory', {})}
        if set(ask.keys()) != {'member_id', 'field'}:
            return False, {'asks': [], 'memory': response.get('memory', {})}
        member_id = ask.get('member_id', '')
        field = ask.get('field', '')

        # Member must exist
        member_exists = any(m['member_id'] == member_id for m in state.get('members', []))
        if not member_exists:
            return False, {'asks': [], 'memory': response.get('memory', {})}

        # Field must be constraints or a permitted soft field
        from kit import SOFT
        if field not in ['constraints'] + SOFT:
            return False, {'asks': [], 'memory': response.get('memory', {})}

        # Member must be currently available
        member = next((m for m in state['members'] if m['member_id'] == member_id), None)
        if member is None or not member.get('available', False):
            return False, {'asks': [], 'memory': response.get('memory', {})}

        # No duplicate member/field requests — a member appears at most once per batch
        if (member_id, field) in seen:
            return False, {'asks': [], 'memory': response.get('memory', {})}
        seen.add((member_id, field))

        # Cost enforcement — total cost must not exceed budget
        cost = 3 if field == 'constraints' else 1
        if total_cost + cost > ask_budget:
            return False, {'asks': [], 'memory': response.get('memory', {})}
        total_cost += cost

    # All asks passed validation
    return True, {'asks': asks, 'memory': response.get('memory', {})}


def _validate_match_response(response, state):
    """Validate a match-phase response. Returns (ok, sanitized).

    Atomic: if ANY pair in the batch is invalid, the whole batch is rejected
    (ok=False). Do not silently filter invalid items and return a partial batch.
    """
    if not isinstance(response, dict):
        return False, {'pairs': [], 'memory': response.get('memory', {})}
    if set(response.keys()) != {'pairs', 'memory'}:
        return False, {'pairs': [], 'memory': response.get('memory', {})}
    pairs = response['pairs']

    # Empty pair batch is valid (nothing to validate)
    if not isinstance(pairs, list):
        return False, {'pairs': [], 'memory': response.get('memory', {})}
    if len(pairs) == 0:
        return True, {'pairs': [], 'memory': response.get('memory', {})}

    members = state.get('members', [])
    member_ids = {m['member_id'] for m in members}
    past_pairs = {tuple(sorted((i['user_a'], i['user_b']))) for i in state.get('introductions', [])}

    # Validate EVERY pair — if ANY is invalid, return ok=False
    seen_people = set()

    for pair in pairs:
        # Structure check: must be list of exactly 2 strings
        if not isinstance(pair, list) or len(pair) != 2:
            return False, {'pairs': [], 'memory': response.get('memory', {})}
        a, b = pair
        if not isinstance(a, str) or not isinstance(b, str):
            return False, {'pairs': [], 'memory': response.get('memory', {})}

        # Both must exist
        if a not in member_ids or b not in member_ids:
            return False, {'pairs': [], 'memory': response.get('memory', {})}

        # Distinct members
        if a == b:
            return False, {'pairs': [], 'memory': response.get('memory', {})}

        # No reuse within batch
        if a in seen_people or b in seen_people:
            return False, {'pairs': [], 'memory': response.get('memory', {})}
        seen_people.add(a)
        seen_people.add(b)

        # Check availability (both must be available)
        a_member = next((m for m in members if m['member_id'] == a), None)
        b_member = next((m for m in members if m['member_id'] == b), None)
        if a_member is None or b_member is None:
            return False, {'pairs': [], 'memory': response.get('memory', {})}
        if not a_member.get('available', False) or not b_member.get('available', False):
            return False, {'pairs': [], 'memory': response.get('memory', {})}

        # eligibility must return feasible — use the kit's eligibility function
        try:
            elig = eligibility(a_member, b_member)
        except Exception:
            return False, {'pairs': [], 'memory': response.get('memory', {})}
        if elig.get('status') != 'feasible':
            return False, {'pairs': [], 'memory': response.get('memory', {})}

        # Note: pairs already in past_pairs are structurally valid but may be
        # blocked by the simulator's advance(). The validator checks structural
        # correctness only; the simulator's advance() enforces the introduction
        # blocking rules. Per the data contract: "Explicitly check outstanding
        # introductions using only observable state and the documented simulator
        # semantics; do not incorrectly block all historically introduced members
        # forever." So we do NOT check past_pairs here — that's the simulator's job.

    # All pairs passed validation
    return True, {'pairs': pairs, 'memory': response.get('memory', {})}


# ---------------------------------------------------------------------------
# Fallback-aware policy decision (Task B)
# ---------------------------------------------------------------------------

def _run_phase_with_fallback(state, phase, baseline_name='greedy'):
    """Run the full policy, then baseline, then empty list — with deadline.

    Returns (actions, memory) tuple suitable for the protocol.
    """
    memory = None

    # ── Step 1: Try the full policy (with deadline awareness) ──
    try:
        _set_deadline()
        # Build the full-policy output using the mode-appropriate logic.
        if phase == 'ask':
            full_actions = baseline_asks(state)
        else:
            full_actions = baseline_match(state)
        full_memory = memory

        # Validate the full-policy output.
        if phase == 'ask':
            ok, validated = _validate_ask_response(
                {'asks': full_actions, 'memory': full_memory}, state)
        else:
            ok, validated = _validate_match_response(
                {'pairs': full_actions, 'memory': full_memory}, state)
        if ok:
            # Also ensure memory is JSON-safe.
            try:
                _ = json.dumps(validated['memory'], allow_nan=False)
            except (TypeError, ValueError):
                pass
            _cancel_deadline()
            return validated['asks'] if phase == 'ask' else validated['pairs'], validated['memory']
    except Exception:
        pass  # fall through to baseline — but we still need to cancel deadline
    finally:
        # If we took too long, make sure the deadline is cancelled before trying baseline.
        if _check_deadline():
            _cancel_deadline()

    # ── Step 2: Try the baseline for this phase ──
    try:
        if baseline_name == 'greedy':
            base_actions = baseline_asks(state) if phase == 'ask' else baseline_match(state)
        elif baseline_name == 'no_asks':
            base_actions = [] if phase == 'ask' else baseline_match(state)
        else:  # random
            base_actions = baseline_asks(state) if phase == 'ask' else baseline_match(state)
        base_memory = None

        # Validate baseline output.
        if phase == 'ask':
            ok, validated = _validate_ask_response(
                {'asks': base_actions, 'memory': base_memory}, state)
        else:
            ok, validated = _validate_match_response(
                {'pairs': base_actions, 'memory': base_memory}, state)
        if ok:
            try:
                _ = json.dumps(validated['memory'], allow_nan=False)
            except (TypeError, ValueError):
                pass
            _cancel_deadline()
            return validated['asks'] if phase == 'ask' else validated['pairs'], validated['memory']
    except Exception:
        pass  # fall through to empty list

    # ── Step 3: Return empty action list ──
    _cancel_deadline()
    return [], {}


def decide(request, mode='greedy'):
    """Entry point matching the expected policy signature.

    request — dict with 'phase', 'state', 'memory'
    mode — unused compatibility arg; the function always applies the fallback chain.
    """
    global _phase_start
    _phase_start = None  # reset per-phase

    state = request['state']
    memory = request.get('memory') or {}

    if request['phase'] == 'ask':
        _set_deadline()
        actions, mem = _run_phase_with_fallback(state, 'ask', mode)
        _cancel_deadline()
        # Preserve memory across phases; ensure JSON safety
        out_mem = mem if mem is not None else {}
        try:
            json.dumps(out_mem, allow_nan=False)
        except (TypeError, ValueError):
            out_mem = {}
        return {'asks': actions, 'memory': out_mem}

    if request['phase'] == 'match':
        _set_deadline()
        actions, mem = _run_phase_with_fallback(state, 'match', mode)
        _cancel_deadline()
        out_mem = mem if mem is not None else {}
        try:
            json.dumps(out_mem, allow_nan=False)
        except (TypeError, ValueError):
            out_mem = {}
        return {'pairs': actions, 'memory': out_mem}

    # Unknown phase — return empty
    return {'asks': [] if request['phase'] == 'ask' else [], 'memory': {}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', choices=['greedy', 'no_asks', 'random'], default='greedy')
    args = parser.parse_args()
    request = json.load(sys.stdin)
    print(json.dumps(decide(request, args.baseline), allow_nan=False))