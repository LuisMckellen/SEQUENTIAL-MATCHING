"""Paired comparison vs greedy for the r2_admission runs.
Usage: python hackathon_files/round2_summary.py <seeds> [experiment]
Per family and policy: mean diff vs greedy with a 95% bootstrap interval over seeds (5000 resamples), W/T/L."""
import json, random, sys
sys.path.insert(0, 'hackathon_files')
from runner import parse_seeds

seeds = set(parse_seeds(sys.argv[1]))
exp = sys.argv[2] if len(sys.argv) > 2 else 'r2_admission'
rows = {}
for line in open('lab_results/results.jsonl'):
    r = json.loads(line)
    if r.get('experiment') == exp and r['seed'] in seeds:
        rows[(r['policy'], r['family'], r['seed'])] = r
metrics = ['mutual_acceptances', 'msmi', 'coverage', 'dates', 'ask_cost']
rng = random.Random(20261014)
print(f'{exp}, seeds {sys.argv[1]}; funnel violations: {sum(not r["funnel_ok"] for r in rows.values())}; records {len(rows)}')
for fam in sorted({k[1] for k in rows}):
    for pol in sorted({k[0] for k in rows} - {'greedy'}):
        ss = sorted(s for s in seeds if (pol, fam, s) in rows and ('greedy', fam, s) in rows)
        out = []
        for m in metrics:
            d = [rows[(pol, fam, s)][m] - rows[('greedy', fam, s)][m] for s in ss]
            if not d:
                continue
            boots = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(5000))
            w, t, l = sum(x > 0 for x in d), sum(x == 0 for x in d), sum(x < 0 for x in d)
            out.append(f'{m} {sum(d)/len(d):+.3f} [{boots[124]:+.3f},{boots[4874]:+.3f}] {w}/{t}/{l}')
        print(f'{fam:12s} {pol:12s} n={len(ss):2d} | ' + ' | '.join(out))
