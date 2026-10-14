"""Reference policy: executable JSON adapter, never reads simulator hidden state.

This version keeps the fallback strategy defensive and cross-platform safe:
- malformed payloads are rejected without crashing,
- the runtime deadline is disabled on platforms without SIGALRM,
- the policy falls back cleanly to baseline or [] before the evaluator times out.
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
# Deadline management
# ---------------------------------------------------------------------------

_deadline_exceeded = False
_phase_start = None


class _DeadlineError(Exception):
    pass


def _deadline_supported():
    return hasattr(signal, 'SIGALRM') and hasattr(signal, 'alarm')


def _deadline_handler(signum, frame):
    """Raise an exception when the process exceeds the hard deadline."""
    raise _DeadlineError('deadline exceeded')


def _set_deadline():
    """Install a 7-second deadline when the platform supports it."""
    global _deadline_exceeded, _phase_start
    _deadline_exceeded = False
    _phase_start = time.monotonic()
    if not _deadline_supported():
        return
    signal.signal(signal.SIGALRM, _deadline_handler)
    signal.alarm(7)


def _check_deadline():
    """Return True when the deadline has elapsed."""
    global _phase_start
    if _phase_start is None or not _deadline_supported():
        return False
    return (time.monotonic() - _phase_start) > 7.0 or _deadline_exceeded


def _cancel_deadline():
    global _phase_start, _deadline_exceeded
    if _deadline_supported():
        signal.alarm(0)
    _phase_start = None
    _deadline_exceeded = False


def _safe_memory(value):
    if isinstance(value, dict):
        return value
    return {}


# ---------------------------------------------------------------------------
# Atomic validators: reject the entire batch on the first invalid item.
# ---------------------------------------------------------------------------


def _validate_ask_response(response, state):
    """Validate an ask-phase response.

    Atomic: if ANY ask in the batch is invalid, the whole batch is rejected.
    """
    if not isinstance(response, dict):
        return False, {'asks': [], 'memory': {}}

    if set(response.keys()) != {'asks', 'memory'}:
        return False, {'asks': [], 'memory': _safe_memory(response.get('memory'))}

    asks = response['asks']
    if not isinstance(asks, list):
        return False, {'asks': [], 'memory': _safe_memory(response.get('memory'))}
    if len(asks) == 0:
        return True, {'asks': [], 'memory': _safe_memory(response.get('memory'))}

    seen = set()
    seen_members = set()
    ask_budget = state.get('ask_budget_remaining', 12)
    total_cost = 0

    from kit import SOFT, HARD

    for ask in asks:
        if not isinstance(ask, dict):
            return False, {'asks': [], 'memory': _safe_memory(response.get('memory'))}
        if set(ask.keys()) != {'member_id', 'field'}:
            return False, {'asks': [], 'memory': _safe_memory(response.get('memory'))}

        member_id = ask.get('member_id')
        field = ask.get('field')
        if not isinstance(member_id, str) or not isinstance(field, str):
            return False, {'asks': [], 'memory': _safe_memory(response.get('memory'))}

        member_exists = any(m.get('member_id') == member_id for m in state.get('members', []))
        if not member_exists:
            return False, {'asks': [], 'memory': _safe_memory(response.get('memory'))}

        if field not in ['constraints'] + SOFT:
            return False, {'asks': [], 'memory': _safe_memory(response.get('memory'))}

        member = next((m for m in state['members'] if m.get('member_id') == member_id), None)
        if member is None or not member.get('available', False):
            return False, {'asks': [], 'memory': _safe_memory(response.get('memory'))}

        if member_id in seen_members:
            return False, {'asks': [], 'memory': _safe_memory(response.get('memory'))}
        seen_members.add(member_id)

        if (member_id, field) in seen:
            return False, {'asks': [], 'memory': _safe_memory(response.get('memory'))}
        seen.add((member_id, field))

        fields = member.get('fields', {})
        field_status = member.get('field_status', {})
        if field == 'constraints':
            any_hard_declined = any(field_status.get(k) == 'declined' for k in HARD)
            if any_hard_declined:
                return False, {'asks': [], 'memory': _safe_memory(response.get('memory'))}
            has_unknown_hard = any(fields.get(k) is None and field_status.get(k) != 'declined' for k in HARD)
            if not has_unknown_hard:
                return False, {'asks': [], 'memory': _safe_memory(response.get('memory'))}
        else:
            if fields.get(field) is not None:
                return False, {'asks': [], 'memory': _safe_memory(response.get('memory'))}
            if field_status.get(field) == 'declined':
                return False, {'asks': [], 'memory': _safe_memory(response.get('memory'))}

        total_cost += 3 if field == 'constraints' else 1
        if total_cost > ask_budget:
            return False, {'asks': [], 'memory': _safe_memory(response.get('memory'))}

    return True, {'asks': asks, 'memory': _safe_memory(response.get('memory'))}


def _validate_match_response(response, state):
    """Validate a match-phase response.

    Atomic: if ANY pair in the batch is invalid, the whole batch is rejected.
    """
    if not isinstance(response, dict):
        return False, {'pairs': [], 'memory': {}}

    if set(response.keys()) != {'pairs', 'memory'}:
        return False, {'pairs': [], 'memory': _safe_memory(response.get('memory'))}

    pairs = response['pairs']
    if not isinstance(pairs, list):
        return False, {'pairs': [], 'memory': _safe_memory(response.get('memory'))}
    if len(pairs) == 0:
        return True, {'pairs': [], 'memory': _safe_memory(response.get('memory'))}

    members = state.get('members', [])
    member_ids = {m['member_id'] for m in members if isinstance(m, dict) and 'member_id' in m}
    past_pairs = {tuple(sorted((i['user_a'], i['user_b']))) for i in state.get('introductions', []) if isinstance(i, dict) and 'user_a' in i and 'user_b' in i}

    seen_people = set()
    for pair in pairs:
        if not isinstance(pair, list) or len(pair) != 2:
            return False, {'pairs': [], 'memory': _safe_memory(response.get('memory'))}
        a, b = pair
        if not isinstance(a, str) or not isinstance(b, str):
            return False, {'pairs': [], 'memory': _safe_memory(response.get('memory'))}
        if a not in member_ids or b not in member_ids:
            return False, {'pairs': [], 'memory': _safe_memory(response.get('memory'))}
        if a == b:
            return False, {'pairs': [], 'memory': _safe_memory(response.get('memory'))}
        if a in seen_people or b in seen_people:
            return False, {'pairs': [], 'memory': _safe_memory(response.get('memory'))}
        seen_people.add(a)
        seen_people.add(b)

        a_member = next((m for m in members if m.get('member_id') == a), None)
        b_member = next((m for m in members if m.get('member_id') == b), None)
        if a_member is None or b_member is None:
            return False, {'pairs': [], 'memory': _safe_memory(response.get('memory'))}
        if not a_member.get('available', False) or not b_member.get('available', False):
            return False, {'pairs': [], 'memory': _safe_memory(response.get('memory'))}

        try:
            elig = eligibility(a_member, b_member)
        except Exception:
            return False, {'pairs': [], 'memory': _safe_memory(response.get('memory'))}
        if elig.get('status') != 'feasible':
            return False, {'pairs': [], 'memory': _safe_memory(response.get('memory'))}

        pair_key = tuple(sorted((a, b)))
        if pair_key in past_pairs:
            return False, {'pairs': [], 'memory': _safe_memory(response.get('memory'))}

    return True, {'pairs': pairs, 'memory': _safe_memory(response.get('memory'))}


# ---------------------------------------------------------------------------
# Fallback-aware policy decision
# ---------------------------------------------------------------------------


def _get_actions_for_mode(state, phase, baseline_name='greedy'):
    if phase == 'ask':
        if baseline_name == 'no_asks':
            return []
        return baseline_asks(state)

    if baseline_name == 'random':
        members = [m for m in state['members'] if m['available']]
        past = {tuple(sorted((i['user_a'], i['user_b']))) for i in state['introductions']}
        edges = []
        for a, b in itertools.combinations(members, 2):
            key = tuple(sorted((a['member_id'], b['member_id'])))
            if key in past or eligibility(a, b)['status'] != 'feasible':
                continue
            edges.append(key)
        random.Random(17 + state['day']).shuffle(edges)
        used = set()
        out = []
        for pair in edges:
            if not used.intersection(pair):
                out.append(list(pair))
                used.update(pair)
        return out

    return baseline_match(state)


def _run_phase_with_fallback(state, phase, baseline_name='greedy'):
    """Run full policy, then baseline, then empty list, with a platform-safe deadline."""
    memory = {}

    try:
        _set_deadline()
        full_actions = _get_actions_for_mode(state, phase, baseline_name)
        if phase == 'ask':
            ok, validated = _validate_ask_response({'asks': full_actions, 'memory': memory}, state)
            full_result = validated['asks'] if ok else []
        else:
            ok, validated = _validate_match_response({'pairs': full_actions, 'memory': memory}, state)
            full_result = validated['pairs'] if ok else []
        if ok:
            try:
                json.dumps(validated.get('memory', {}), allow_nan=False)
            except (TypeError, ValueError, OverflowError):
                pass
            else:
                _cancel_deadline()
                return full_result, validated.get('memory', {})
    except _DeadlineError:
        pass
    except Exception:
        pass
    finally:
        _cancel_deadline()

    try:
        base_actions = _get_actions_for_mode(state, phase, baseline_name)
        if phase == 'ask':
            ok, validated = _validate_ask_response({'asks': base_actions, 'memory': {}}, state)
            if ok:
                return validated['asks'], validated.get('memory', {})
        else:
            ok, validated = _validate_match_response({'pairs': base_actions, 'memory': {}}, state)
            if ok:
                return validated['pairs'], validated.get('memory', {})
    except _DeadlineError:
        pass
    except Exception:
        pass

    return [], {}


def decide(request, mode='greedy'):
    """Entry point matching the expected policy signature.

    request is expected to have 'phase', 'state', and optional 'memory'.
    """
    try:
        state = request['state']
    except Exception:
        return {'asks': [], 'memory': {}}

    memory = request.get('memory') or {}
    if request.get('phase') == 'ask':
        try:
            actions, mem = _run_phase_with_fallback(state, 'ask', mode)
        except _DeadlineError:
            return {'asks': [], 'memory': {}}
        except Exception:
            return {'asks': [], 'memory': {}}

        try:
            json.dumps(mem, allow_nan=False)
        except (TypeError, ValueError, OverflowError):
            mem = {}
        return {'asks': actions, 'memory': mem}

    if request.get('phase') == 'match':
        try:
            actions, mem = _run_phase_with_fallback(state, 'match', mode)
        except _DeadlineError:
            return {'pairs': [], 'memory': {}}
        except Exception:
            return {'pairs': [], 'memory': {}}

        try:
            json.dumps(mem, allow_nan=False)
        except (TypeError, ValueError, OverflowError):
            mem = {}
        return {'pairs': actions, 'memory': mem}

    return {'asks': [], 'memory': memory}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', choices=['greedy', 'no_asks', 'random'], default='greedy')
    args = parser.parse_args()
    request = json.load(sys.stdin)
    print(json.dumps(decide(request, args.baseline), allow_nan=False))
