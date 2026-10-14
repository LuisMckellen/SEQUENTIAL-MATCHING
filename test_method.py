"""Tests for the method mode in policy.py (the default when policy.py runs without --baseline)."""
import builtins
import json
import os
import subprocess
import sys
import unittest

from kit import generate, Simulator, baseline_asks, baseline_match
import policy

HERE = os.path.dirname(os.path.abspath(__file__))


def run_cli(request, *args):
    proc = subprocess.run([sys.executable, 'policy.py', *args], input=json.dumps(request),
                          capture_output=True, text=True, cwd=HERE, timeout=60)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


class TestMethod(unittest.TestCase):
    def test_ten_days_valid_in_the_simulator(self):
        """Every method action is accepted by the simulator (an invalid one would raise)."""
        sim = Simulator(generate(1181, 200, 'evaluation', 'cold_start'))
        memory = None
        for _ in range(10):
            out = policy.decide({'phase': 'ask', 'state': sim.observe(), 'memory': memory}, 'method')
            sim.resolve_asks(out['asks'])
            out = policy.decide({'phase': 'match', 'state': sim.observe(), 'memory': out['memory']}, 'method')
            sim.advance(out['pairs'])
            memory = out['memory']
            sim.day += 0  # advance() moves the day

    def test_cli_default_is_method_and_baselines_unchanged(self):
        sim = Simulator(generate(1181, 200, 'evaluation', 'development'))
        ask_state = sim.observe()
        req = {'phase': 'ask', 'state': ask_state, 'memory': None}
        self.assertEqual(run_cli(req)['asks'], policy._method_actions(ask_state, 'ask'))
        self.assertEqual(run_cli(req, '--baseline', 'greedy')['asks'], baseline_asks(ask_state))
        self.assertEqual(run_cli(req, '--baseline', 'no_asks')['asks'], [])
        sim.resolve_asks(baseline_asks(ask_state))
        match_state = sim.observe()
        req = {'phase': 'match', 'state': match_state, 'memory': None}
        self.assertEqual(run_cli(req, '--baseline', 'greedy')['pairs'], baseline_match(match_state))
        self.assertEqual(run_cli(req)['pairs'], policy._blossom_match(match_state))

    def test_blossom_never_returns_fewer_score_points_than_greedy(self):
        sim = Simulator(generate(1182, 200, 'evaluation', 'development'))
        sim.resolve_asks(baseline_asks(sim.observe()))
        state = sim.observe()
        members = {m['member_id']: m for m in state['members']}
        weight = lambda pairs: sum(1 + policy._soft_score(members[a], members[b]) for a, b in pairs)
        self.assertGreaterEqual(weight(policy._blossom_match(state)), weight(baseline_match(state)))

    def test_missing_networkx_falls_back_to_greedy(self):
        sim = Simulator(generate(1181, 200, 'evaluation', 'development'))
        sim.resolve_asks(baseline_asks(sim.observe()))
        state = sim.observe()
        real_import = builtins.__import__

        def no_networkx(name, *a, **k):
            if name == 'networkx':
                raise ImportError('no networkx')
            return real_import(name, *a, **k)

        builtins.__import__ = no_networkx
        try:
            out = policy.decide({'phase': 'match', 'state': state, 'memory': None}, 'method')
        finally:
            builtins.__import__ = real_import
        self.assertEqual(out['pairs'], baseline_match(state))

    def test_value_asks_respect_budget_and_declines(self):
        sim = Simulator(generate(1183, 200, 'evaluation', 'sparse'))
        state = sim.observe()
        asks = policy._value_asks(state)
        self.assertLessEqual(3 * len(asks), state['ask_budget_remaining'])
        declined = {m['member_id'] for m in state['members']
                    if any(m['field_status'][k] == 'declined' for k in ('who_to_meet',) if k in m['field_status'])}
        self.assertFalse(declined & {a['member_id'] for a in asks})
        state['ask_budget_remaining'] = 2
        self.assertEqual(policy._value_asks(state), [])


if __name__ == '__main__':
    unittest.main()
