"""Lab 13 driver (ANALYSIS ONLY: it runs the oracle ceilings, which read hidden simulator data).

Runs greedy, the five oracle ceilings and the three observable learners on the same worlds and records them
in lab_results/results.jsonl as experiment 'lab13_ceilings'. Resumable: it runs only episodes not yet
recorded and stops after a time budget, so it can be called repeatedly.

Usage (repo root, PYTHONHASHSEED=0, PYTHONPATH=.; needs lab_results/cache/h1c_groups_3001_3130.pkl):
  python hackathon_files/lab13_run_ANALYSIS_ONLY.py [budget_seconds=150]
Then: python hackathon_files/lab13_expected_ANALYSIS_ONLY.py
Seeds 1161-1180 (fresh), families development and cold_start.
"""
import sys, json, time
sys.path.insert(0, '.')
sys.path.insert(0, 'hackathon_files')
from kit import baseline_asks, baseline_match
from runner import run_episode, write
from lab13_learners import LEARNERS
from lab13_ceiling_ANALYSIS_ONLY import ORACLES, make_oracle

EXP = 'lab13_ceilings'
OUT = 'lab_results/results.jsonl'
POLICIES = ['greedy', *ORACLES, *LEARNERS]
PLAN = [(f, s, p) for f in ('development', 'cold_start') for s in range(1161, 1181) for p in POLICIES]


def run_one(family, seed, policy):
    if policy == 'greedy':
        return run_episode(baseline_asks, baseline_match, seed, family)
    if policy in LEARNERS:
        return run_episode(baseline_asks, LEARNERS[policy], seed, family)
    holder = {}
    return run_episode(baseline_asks, make_oracle(policy, holder), seed, family,
                       pre_day=lambda sim: holder.__setitem__('sim', sim))


if __name__ == '__main__':
    budget = float(sys.argv[1]) if len(sys.argv) > 1 else 150
    done = set()
    try:
        for l in open(OUT, encoding='utf-8'):
            if l.strip():
                r = json.loads(l.lstrip('﻿'))
                if r['experiment'] == EXP:
                    done.add((r['family'], r['seed'], r['policy']))
    except FileNotFoundError:
        pass
    todo = [k for k in PLAN if k not in done]
    t0 = time.time(); n = 0
    for f, s, p in todo:
        if time.time() - t0 > budget:
            break
        write(OUT, EXP, p, run_one(f, s, p)); n += 1
    print(f'ran {n}; remaining {len(todo) - n} of {len(PLAN)}')
