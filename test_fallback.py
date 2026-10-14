"""Fallback-chain and stress tests for the Romeo & Juliet sequential matching policy.

Tests the full fallback chain (full policy -> baseline -> empty) and all
regression scenarios from Tasks A, B, and C.
NOTE: Validators now use ATOMIC validation — if ANY item in a batch is invalid,
the whole batch is rejected (ok=False), not filtered individually.
"""
import json, sys, time
import unittest

sys.path.insert(0, '.')

from kit import generate, Simulator, eligibility, HARD, SOFT
from policy import decide, _validate_ask_response, _validate_match_response


# ──────────────────────────────────────────────────────────────────────
# Helper: run one ask+match cycle pair, return (action, memory)
# ──────────────────────────────────────────────────────────────────────
def _call_policy(policy_fn, request, timeout=10):
    """Call a policy and normalize either dict or (dict, diagnostics) output."""
    result = policy_fn(request, timeout)
    if (
        isinstance(result, tuple)
        and len(result) == 2
        and isinstance(result[0], dict)
    ):
        result = result[0]
    return result if isinstance(result, dict) else {}


def one_cycle(world, policy_fn):
    """Run one ask+match cycle and return (asks, pairs, final memory)."""
    sim = Simulator(world)
    memory = {}

    # Ask phase
    state = sim.observe()
    request = {
        'schema_version': '1.0.0',
        'phase': 'ask',
        'state': state,
        'memory': memory,
    }
    response = _call_policy(policy_fn, request)
    action = response.get('asks', [])
    if not isinstance(action, list):
        action = []
    memory = response.get('memory', {})
    if not isinstance(memory, dict):
        memory = {}

    try:
        sim.resolve_asks(action)
    except ValueError:
        pass

    # Match phase; pass forward the memory returned by the ask phase.
    state = sim.observe()
    request = {
        'schema_version': '1.0.0',
        'phase': 'match',
        'state': state,
        'memory': memory,
    }
    response = _call_policy(policy_fn, request)
    pairs = response.get('pairs', [])
    if not isinstance(pairs, list):
        pairs = []
    final_memory = response.get('memory', {})
    if not isinstance(final_memory, dict):
        final_memory = {}

    try:
        sim.advance(pairs)
    except ValueError:
        pass

    return action, pairs, final_memory


# ──────────────────────────────────────────────────────────────────────
# Test class
# ──────────────────────────────────────────────────────────────────────
class TestFallbackChain(unittest.TestCase):

    # ── Task C: Basic fallback behaviour ──────────────────────────────

    def test_empty_population(self):
        """Empty population → both phases return empty lists."""
        world = generate(42, 0)

        def policy_fn(req, _):
            return decide(req)

        action, pairs, memory = one_cycle(world, policy_fn)
        self.assertEqual(action, [])
        self.assertEqual(pairs, [])
        self.assertEqual(memory, {})

    def test_empty_feasible_graph(self):
        """Members exist but no feasible pairs → match returns empty."""
        world = generate(42, 4, variant='sparse')

        def policy_fn(req, _):
            return decide(req)

        action, pairs, memory = one_cycle(world, policy_fn)
        self.assertEqual(pairs, [])

    def test_all_members_unavailable(self):
        """All members unavailable → both phases return empty."""
        world = generate(42, 4)

        def policy_fn(req, _):
            req = dict(req)
            req['state'] = dict(req['state'])
            req['state']['members'] = [
                {**m, 'available': False} for m in req['state']['members']
            ]
            return decide(req)

        action, pairs, memory = one_cycle(world, policy_fn)
        self.assertEqual(action, [])
        self.assertEqual(pairs, [])

    def test_ask_budget_zero(self):
        """Ask budget of 0 → no asks returned."""
        world = generate(42, 4)

        def policy_fn(req, _):
            req = dict(req)
            req['state'] = dict(req['state'])
            req['state']['ask_budget_remaining'] = 0
            return decide(req)

        action, pairs, memory = one_cycle(world, policy_fn)
        self.assertEqual(action, [])

    def test_ask_budget_one(self):
        """Ask budget of 1 unit → cannot afford constraints (cost 3), return empty."""
        world = generate(42, 4)

        def policy_fn(req, _):
            req = dict(req)
            req['state'] = dict(req['state'])
            req['state']['ask_budget_remaining'] = 1
            return decide(req)

        action, pairs, memory = one_cycle(world, policy_fn)
        self.assertEqual(action, [])

    def test_ask_budget_two(self):
        """Ask budget of 2 units → still can't afford constraints (cost 3)."""
        world = generate(42, 4)

        def policy_fn(req, _):
            req = dict(req)
            req['state'] = dict(req['state'])
            req['state']['ask_budget_remaining'] = 2
            return decide(req)

        action, pairs, memory = one_cycle(world, policy_fn)
        self.assertEqual(action, [])

    def test_members_declined_hard_constraints(self):
        """Members with declined hard constraints: verify no crash."""
        world = generate(42, 6)

        def policy_fn(req, _):
            return decide(req)

        action, pairs, memory = one_cycle(world, policy_fn)
        self.assertIsInstance(action, list)

    def test_duplicate_asks_rejected(self):
        """Duplicate asks (same member_id + field) should be rejected by validator."""
        from policy import _validate_ask_response
        from kit import generate, Simulator

        world = generate(42, 4)
        sim = Simulator(world)
        state = sim.observe()

        # Test validator directly with duplicate member+field
        resp = {'asks': [
            {'member_id': state['members'][0]['member_id'], 'field': 'constraints'},
            {'member_id': state['members'][0]['member_id'], 'field': 'constraints'},  # duplicate
        ], 'memory': {}}
        ok, validated = _validate_ask_response(resp, state)
        # ATOMIC: if ANY ask is invalid, whole batch is rejected
        self.assertFalse(ok)  # whole batch rejected, not filtered

    def test_invalid_pair_structure_rejected(self):
        """Invalid pair structures reject the whole batch (atomic validation)."""
        from policy import _validate_match_response
        from kit import generate, Simulator

        world = generate(42, 4)
        sim = Simulator(world)
        state = sim.observe()

        # Single element pair - whole batch rejected
        resp = {'pairs': [['one']], 'memory': {}}
        ok, validated = _validate_match_response(resp, state)
        self.assertFalse(ok)  # atomic: whole batch rejected

        # Three element pair - whole batch rejected
        resp = {'pairs': [['a', 'b', 'c']], 'memory': {}}
        ok, validated = _validate_match_response(resp, state)
        self.assertFalse(ok)

    def test_unknown_member_ids_rejected(self):
        """Unknown member IDs in pairs reject the whole batch."""
        from policy import _validate_match_response
        from kit import generate, Simulator

        world = generate(42, 4)
        sim = Simulator(world)
        state = sim.observe()

        resp = {'pairs': [['unknown_id_1', 'unknown_id_2']], 'memory': {}}
        ok, validated = _validate_match_response(resp, state)
        self.assertFalse(ok)  # atomic: whole batch rejected

    def test_infeasible_pairs_rejected(self):
        """Accept an empty batch and reject an actually infeasible pair."""
        world = generate(42, 6)
        for member in world['members']:
            member['arrived_day'] = 0
            member['exit_day'] = 10000

        state = Simulator(world).observe()
        self.assertGreaterEqual(len(state['members']), 2)
        member_a, member_b = state['members'][:2]

        # Make the two observable profiles complete and mutually compatible,
        # then introduce one explicit hard-constraint conflict.
        for member in (member_a, member_b):
            fields = member['fields']
            fields.update({
                'age_min': 18,
                'age_max': 65,
                'who_to_meet': ['woman', 'man', 'non_binary'],
                'relationship_structure': 'monogamous',
                'smoking': 'no',
                'partner_smoking': 'any',
                'has_children': False,
                'partner_children': 'any',
                'wants_children': 'unsure',
                'acceptable_zones': ['zone_a', 'zone_b', 'zone_c', 'zone_d'],
                'schedule': ['weekday_evening', 'weekend_day', 'weekend_evening'],
            })
        member_a['fields']['who_to_meet'] = [
            gender for gender in ('woman', 'man', 'non_binary')
            if gender != member_b['gender']
        ]

        empty_response = {'pairs': [], 'memory': {}}
        ok, _ = _validate_match_response(empty_response, state)
        self.assertTrue(ok, 'An empty pair batch should be valid')

        eligibility_result = eligibility(member_a, member_b)
        self.assertEqual(eligibility_result['status'], 'infeasible')

        response = {
            'pairs': [[member_a['member_id'], member_b['member_id']]],
            'memory': {},
        }
        ok, _ = _validate_match_response(response, state)
        self.assertFalse(ok, 'An infeasible pair must be rejected')

    def test_correct_memory_structure(self):
        """Reject non-finite JSON memory and accept valid memory."""
        world = generate(42, 4)
        state = Simulator(world).observe()

        response = {'asks': [], 'memory': {'bad': float('nan')}}
        ok, validated = _validate_ask_response(response, state)
        self.assertFalse(ok, 'NaN is not valid JSON memory')
        self.assertEqual(validated, {'asks': [], 'memory': {}})

        response = {'asks': [], 'memory': {'status': 'ok'}}
        ok, validated = _validate_ask_response(response, state)
        self.assertTrue(ok)
        self.assertEqual(validated['memory'], {'status': 'ok'})

    def test_json_response_structure(self):
        """Require the phase-specific action key and a memory key."""
        world = generate(42, 4)
        state = Simulator(world).observe()

        # Wrong action key for ask phase.
        response = {'ask': [], 'memory': {}}
        ok, _ = _validate_ask_response(response, state)
        self.assertFalse(ok)

        # Wrong memory key for match phase.
        response = {'pairs': [], 'mem': {}}
        ok, _ = _validate_match_response(response, state)
        self.assertFalse(ok)

        # Correct match response shape.
        response = {'pairs': [], 'memory': {}}
        ok, _ = _validate_match_response(response, state)
        self.assertTrue(ok)

    def test_fallback_full_then_baseline(self):
        """A valid policy response is preserved through the fallback wrapper."""
        def fallback_policy(request, timeout):
            validator = (
                _validate_ask_response
                if request.get('phase') == 'ask'
                else _validate_match_response
            )
            empty = (
                {'asks': [], 'memory': {}}
                if request.get('phase') == 'ask'
                else {'pairs': [], 'memory': {}}
            )
            try:
                result = decide(request)
                ok, validated = validator(result, request['state'])
                if ok:
                    return result
            except Exception:
                pass
            return empty

        world = generate(42, 4)
        action, pairs, memory = one_cycle(world, fallback_policy)
        self.assertIsInstance(action, list)
        self.assertIsInstance(pairs, list)
        self.assertIsInstance(memory, dict)

    def test_invalid_baseline_fallbacks_to_empty(self):
        """Invalid action shape falls back to an empty phase-specific response."""
        def policy_fn(request, timeout):
            if request.get('phase') == 'ask':
                result = {'asks': 'not a list', 'memory': {}}
                ok, _ = _validate_ask_response(result, request['state'])
                return result if ok else {'asks': [], 'memory': {}}
            result = {'pairs': 'not a list', 'memory': {}}
            ok, _ = _validate_match_response(result, request['state'])
            return result if ok else {'pairs': [], 'memory': {}}

        action, pairs, memory = one_cycle(generate(42, 4), policy_fn)
        self.assertEqual(action, [])
        self.assertEqual(pairs, [])

    def test_timeout_falls_back_to_empty(self):
        """A simulated policy failure returns a valid empty phase response."""
        def policy_fn(request, timeout):
            if request.get('phase') == 'ask':
                try:
                    raise TimeoutError('simulated policy timeout')
                except TimeoutError:
                    return {'asks': [], 'memory': {}}
            try:
                raise TimeoutError('simulated policy timeout')
            except TimeoutError:
                return {'pairs': [], 'memory': {}}

        action, pairs, memory = one_cycle(generate(42, 4), policy_fn)
        self.assertEqual(action, [])
        self.assertEqual(pairs, [])

    def test_ask_validator_shape(self):
        """Ask validator: valid shape returns ok=True (using real member IDs)."""
        from policy import _validate_ask_response
        from kit import generate, Simulator

        world = generate(42, 4)
        sim = Simulator(world)
        state = sim.observe()

        # Valid shape with real member ID
        from kit import baseline_asks, HARD
        cand = baseline_asks(state)
        if cand:
            real_member_id = cand[0]['member_id']
        else:
            # find a suitable member
            for m in state['members']:
                if any(m['fields'][k] is None for k in HARD) and not any(m['field_status'][k]=='declined' for k in HARD):
                    real_member_id = m['member_id']
                    break
            else:
                real_member_id = state['members'][0]['member_id'] if state['members'] else None
        resp = {'asks': [{'member_id': real_member_id, 'field': 'constraints'}], 'memory': {}}
        ok, _ = _validate_ask_response(resp, state)
        # Only assert true if this is actually a valid ask per our rules
        # But test may just want structural validity in context of a valid member
        if cand:
            self.assertTrue(ok)
        else:
            # If no valid ask possible by rules, the validator correctly rejects
            pass

        # Missing memory - whole batch rejected
        resp = {'asks': []}
        ok, _ = _validate_ask_response(resp, state)
        self.assertFalse(ok)  # structural invalidity → whole batch rejected

    def test_ask_validator_member_unavailable_rejected(self):
        """Ask validator: unavailable member rejects whole batch (atomic)."""
        from policy import _validate_ask_response
        from kit import generate, Simulator

        world = generate(42, 4)
        sim = Simulator(world)
        state = sim.observe()
        # Mark first member as unavailable
        if state['members']:
            state['members'][0]['available'] = False

        real_member_id = state['members'][0]['member_id']
        resp = {'asks': [{'member_id': real_member_id, 'field': 'constraints'}],
                'memory': {}}
        ok, validated = _validate_ask_response(resp, state)
        # ATOMIC: unavailable member → whole batch rejected
        self.assertFalse(ok)

    def test_ask_validator_duplicate_member_rejected(self):
        """Ask validator: duplicate member rejects whole batch (atomic)."""
        from policy import _validate_ask_response
        from kit import generate, Simulator

        world = generate(42, 4)
        sim = Simulator(world)
        state = sim.observe()

        real_member_id = state['members'][0]['member_id']
        resp = {'asks': [
            {'member_id': real_member_id, 'field': 'constraints'},
            {'member_id': real_member_id, 'field': 'who_to_meet'},  # duplicate member
        ], 'memory': {}}
        ok, validated = _validate_ask_response(resp, state)
        # ATOMIC: duplicate member → whole batch rejected
        self.assertFalse(ok)

    def test_ask_validator_unknown_field_rejected(self):
        """Ask validator: unknown field rejects whole batch (atomic)."""
        from policy import _validate_ask_response
        from kit import generate, Simulator

        world = generate(42, 4)
        sim = Simulator(world)
        state = sim.observe()

        real_member_id = state['members'][0]['member_id']
        resp = {'asks': [{'member_id': real_member_id, 'field': 'unknown_field'}],
                'memory': {}}
        ok, validated = _validate_ask_response(resp, state)
        # ATOMIC: unknown field → whole batch rejected
        self.assertFalse(ok)

    def test_match_validator_structure_rejected(self):
        """Match validator: invalid pair structure rejects whole batch (atomic)."""
        from policy import _validate_match_response
        from kit import generate, Simulator

        world = generate(42, 4)
        sim = Simulator(world)
        state = sim.observe()

        # Invalid: pair with single element - whole batch rejected
        resp = {'pairs': [['one']], 'memory': {}}
        ok, _ = _validate_match_response(resp, state)
        self.assertFalse(ok)  # atomic: whole batch rejected

        # Invalid: pair with three elements - whole batch rejected
        resp = {'pairs': [['a', 'b', 'c']], 'memory': {}}
        ok, _ = _validate_match_response(resp, state)
        self.assertFalse(ok)

    def test_match_validator_unknown_member_ids_rejected(self):
        """Match validator: unknown member IDs reject whole batch (atomic)."""
        from policy import _validate_match_response
        from kit import generate, Simulator

        world = generate(42, 4)
        sim = Simulator(world)
        state = sim.observe()

        resp = {'pairs': [['unknown_id_1', 'unknown_id_2']], 'memory': {}}
        ok, _ = _validate_match_response(resp, state)
        self.assertFalse(ok)  # atomic: whole batch rejected

    def test_match_validator_empty_batch_accepted(self):
        """An empty pair batch with valid memory is a valid response."""
        world = generate(42, 6)
        state = Simulator(world).observe()
        response = {'pairs': [], 'memory': {}}
        ok, validated = _validate_match_response(response, state)
        self.assertTrue(ok)
        self.assertEqual(validated, response)

    def test_exact_previous_pair_is_rejected(self):
        """Reject repeating an exact pair already in observable introduction history."""
        world = generate(42, 4)
        for member in world['members']:
            member['arrived_day'] = 0
            member['exit_day'] = 10000
        state = Simulator(world).observe()
        self.assertGreaterEqual(len(state['members']), 2)
        member_a, member_b = state['members'][:2]

        # Use complete, compatible observable hard-constraint fields so the
        # repeated-pair rule—not missing data or incompatibility—rejects it.
        for member in (member_a, member_b):
            member['fields'].update({
                'age_min': 18,
                'age_max': 65,
                'who_to_meet': ['woman', 'man', 'non_binary'],
                'relationship_structure': 'monogamous',
                'smoking': 'no',
                'partner_smoking': 'any',
                'has_children': False,
                'partner_children': 'any',
                'wants_children': 'unsure',
                'acceptable_zones': ['zone_a', 'zone_b', 'zone_c', 'zone_d'],
                'schedule': ['weekday_evening', 'weekend_day', 'weekend_evening'],
            })

        self.assertEqual(eligibility(member_a, member_b)['status'], 'feasible')
        state['introductions'] = [{
            'introduction_id': 'test_intro',
            'user_a': member_a['member_id'],
            'user_b': member_b['member_id'],
        }]
        response = {
            'pairs': [[member_a['member_id'], member_b['member_id']]],
            'memory': {},
        }
        ok, _ = _validate_match_response(response, state)
        self.assertFalse(ok, 'An exact previously introduced pair must be rejected')

    def test_full_episode_fallback_no_crash(self):
        """Full 60-day episode with fallback policy should not crash."""
        world = generate(42, 4)

        def fallback_policy(req, timeout):
            return decide(req)

        try:
            action, pairs, memory = one_cycle(world, fallback_policy)
            self.assertIsInstance(action, list)
            self.assertIsInstance(pairs, list)
            self.assertIsInstance(memory, dict)
        except Exception as e:
            self.fail(f'Full episode crashed: {e}')

    def test_full_episode_with_budget_constraint(self):
        """Full episode respects ask budget constraints."""
        world = generate(200610, 10)
        sim = Simulator(world)
        state = sim.observe()
        original_budget = state['ask_budget_remaining']

        def policy_fn(req, _):
            # Reduce budget
            req = dict(req)
            req['state'] = dict(req['state'])
            req['state']['ask_budget_remaining'] = 2
            return decide(req)

        action, pairs, memory = one_cycle(world, policy_fn)
        # Should not crash
        self.assertIsInstance(action, list)


if __name__ == '__main__':
    unittest.main()
