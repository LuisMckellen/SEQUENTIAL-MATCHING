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
_phase_start = None


class _DeadlineError(Exception):
    pass


def _deadline_handler(signum, frame):
    """SIGALRM handler — interrupt execution."""
    raise _DeadlineError("deadline exceeded")


def _set_deadline():
    """Install a 7‑second real-time alarm and record start time."""
    global _deadline_exceeded, _phase_start
    _deadline_exceeded = False
    signal.signal(signal.SIGALRM, _deadline_handler)
    signal.alarm(7)  # fire after ~7 seconds
    _phase_start = time.monotonic()


def _check_deadline():
    """Return True if deadline has elapsed."""
    global _phase_start
    if _phase_start is None:
        return False
    return (time.monotonic() - _phase_start) > 7.0 or _deadline_exceeded


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
    seen_members = set()  # each member appears at most once
    ask_budget = state.get('ask_budget_remaining', 12)
    total_cost = 0
    from kit import SOFT, HARD

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
        if field not in ['constraints'] + SOFT:
            return False, {'asks': [], 'memory': response.get('memory', {})}

        # Member must be currently available
        member = next((m for m in state['members'] if m['member_id'] == member_id), None)
        if member is None or not member.get('available', False):
            return False, {'asks': [], 'memory': response.get('memory', {})}

        # Each member appears at most once per ask batch
        if member_id in seen_members:
            return False, {'asks': [], 'memory': response.get('memory', {})}
        seen_members.add(member_id)

        # No duplicate member/field requests
        if (member_id, field) in seen:
            return False, {'asks': [], 'memory': response.get('memory', {})}
        seen.add((member_id, field))

        # Constraints bundle validity
        f = member.get('fields', {})
        fs = member.get('field_status', {})
        if field == 'constraints':
            any_hard_declined = any(fs.get(k) == 'declined' for k in HARD)
            if any_hard_declined:
                return False, {'asks': [], 'memory': response.get('memory', {})}
            has_unknown_hard = any(f.get(k) is None and fs.get(k) != 'declined' for k in HARD)
            if not has_unknown_hard:
                return False, {'asks': [], 'memory': response.get('memory', {})}
        else:
            if f.get(field) is not None:
                return False, {'asks': [], 'memory': response.get('memory', {})}
            if fs.get(field) == 'declined':
                return False, {'asks': [], 'memory': response.get('memory', {})}

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

        # Reject exact pairs already introduced
        pair_key = tuple(sorted((a, b)))
        if pair_key in past_pairs:
            return False, {'pairs': [], 'memory': response.get('memory', {})}

    # All pairs passed validation
    return True, {'pairs': pairs, 'memory': response.get('memory', {})}


# ---------------------------------------------------------------------------
# Fallback-aware policy decision (Task B)
# ---------------------------------------------------------------------------

def _get_actions_for_mode(state, phase, baseline_name='greedy'):
    """Get actions according to baseline mode."""
    if phase == 'ask':
        if baseline_name == 'no_asks':
            return []
        # greedy and random use baseline_asks behavior for asks
        return baseline_asks(state)
    else:  # match phase
        if baseline_name == 'random':
            # Use random feasible behavior
            members = [m for m in state['members'] if m['available']]
            import itertools
            from kit import eligibility
            past = {tuple(sorted((i['user_a'], i['user_b']))) for i in state['introductions']}
            edges = []
            for a, b in itertools.combinations(members, 2):
                key = tuple(sorted((a['member_id'], b['member_id'])))
                if key in past or eligibility(a, b)['status'] != 'feasible':
                    continue
                edges.append(key)
            # Randomize edges
            import random as r
            r.shuffle(edges)
            used = set()
            out = []
            for pair in edges:
                if not used.intersection(pair):
                    out.append(list(pair))
                    used.update(pair)
            return out
        else:
            # greedy (and default)
            return baseline_match(state)


def _run_phase_with_fallback(state, phase, baseline_name='greedy'):
    """Run the full policy, then baseline, then empty list — with deadline.

    Returns (actions, memory) tuple suitable for the protocol.
    """
    memory = {}

    # ── Step 1: Try the full policy (with deadline awareness) ──
    try:
        _set_deadline()
        full_actions = _get_actions_for_mode(state, phase, baseline_name)
        full_memory = memory

        # Validate the full-policy output.
        if phase == 'ask':
            ok, validated = _validate_ask_response(
                {'asks': full_actions, 'memory': full_memory}, state)
        else:
            ok, validated = _validate_match_response(
                {'pairs': full_actions, 'memory': full_memory}, state)
        if ok:
            try:
                _ = json.dumps(validated['memory'], allow_nan=False)
            except (TypeError, ValueError, OverflowError):
                pass  # fall through to baseline
            else:
                _cancel_deadline()
                return validated['asks'] if phase == 'ask' else validated['pairs'], validated['memory']
    except _DeadlineError:
        pass  # fall through to baseline
    except Exception:
        pass  # fall through to baseline
    finally:
        _cancel_deadline()

    # ── Step 2: Try the baseline for this phase ──
    try:
        base_actions = _get_actions_for_mode(state, phase, baseline_name)
        base_memory = {}

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
            except (TypeError, ValueError, OverflowError):
                pass
            _cancel_deadline()
            return validated['asks'] if phase == 'ask' else validated['pairs'], validated['memory']
    except _DeadlineError:
        pass
    except Exception:
        pass  # fall through to empty list

    # ── Step 3: Return empty action list ──
    _cancel_deadline()
    return [], {}


def decide(request, mode='greedy'):
    """Entry point matching the expected policy signature.

    request — dict with 'phase', 'state', 'memory'
    mode — baseline mode (greedy|no_asks|random)
    """
    global _phase_start
    _phase_start = None  # reset per-phase

    try:
        state = request['state']
    except Exception:
        return {'asks': [], 'memory': {}}
    memory = request.get('memory') or {}

    if request['phase'] == 'ask':
        try:
            actions, mem = _run_phase_with_fallback(state, 'ask', mode)
        except _DeadlineError:
            return {'asks': [], 'memory': {}}
        except Exception:
            return {'asks': [], 'memory': {}}
        out_mem = mem if mem is not None else {}
        try:
            json.dumps(out_mem, allow_nan=False)
        except (TypeError, ValueError, OverflowError):
            out_mem = {}
        return {'asks': actions, 'memory': out_mem}

    if request['phase'] == 'match':
        try:
            actions, mem = _run_phase_with_fallback(state, 'match', mode)
        except _DeadlineError:
            return {'pairs': [], 'memory': {}}
        except Exception:
            return {'pairs': [], 'memory': {}}
        out_mem = mem if mem is not None else {}
        try:
            json.dumps(out_mem, allow_nan=False)
        except (TypeError, ValueError, OverflowError):
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