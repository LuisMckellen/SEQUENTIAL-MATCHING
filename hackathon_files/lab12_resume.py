"""Resumable driver for Lab 12: runs only the (family, seed, policy) episodes not yet in results.jsonl,
and stops after a time budget so it can be called repeatedly. Same episodes, same records as lab12_waiting.py.
Usage: PYTHONHASHSEED=0 PYTHONPATH=. python hackathon_files/lab12_resume.py [budget_seconds=150]"""
import sys, json, time
sys.path.insert(0, '.')
sys.path.insert(0, 'hackathon_files')
from kit import baseline_asks
from runner import run_episode, write
from lab12_waiting import POLICIES

PLAN = ([(f, s, p) for f in ('development', 'cold_start') for s in range(1121, 1141) for p in POLICIES] +
        [(f, s, p) for f in ('development', 'cold_start') for s in range(1141, 1161)
         for p in ('greedy', 'learned_tau0', 'learned_tau0.12_pure')])

if __name__ == '__main__':
    budget = float(sys.argv[1]) if len(sys.argv) > 1 else 150
    done = set()
    for l in open('results.jsonl', encoding='utf-8'):
        if l.strip():
            r = json.loads(l.lstrip('﻿'))
            if r['experiment'] == 'lab12_waiting':
                done.add((r['family'], r['seed'], r['policy']))
    todo = [k for k in PLAN if k not in done]
    t0 = time.time(); n = 0
    for f, s, p in todo:
        if time.time() - t0 > budget:
            break
        write('results.jsonl', 'lab12_waiting', p, run_episode(baseline_asks, POLICIES[p], s, f)); n += 1
    print(f'ran {n}; remaining {len(todo) - n} of {len(PLAN)}')
