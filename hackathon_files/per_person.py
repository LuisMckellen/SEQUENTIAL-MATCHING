"""Check C: how much history does each person get? (decides whether per-person modelling, H4, can learn)
Counts introductions per served member and answered responses per member, from results.jsonl.
Usage: python per_person.py <experiment> <policy> <family> <seeds>
e.g.   python per_person.py lab9_asking greedy development 1101-1120"""
import sys, json, collections, statistics as st
from runner import parse_seeds
exp, pol, fam, seeds = sys.argv[1], sys.argv[2], sys.argv[3], set(parse_seeds(sys.argv[4]))
recs = {}
for l in open('results.jsonl'):
    r = json.loads(l)
    if r['experiment'] == exp and r['policy'] == pol and r['family'] == fam and r['seed'] in seeds:
        recs[r['seed']] = r                      # last record per seed (duplicates are identical)
counts = []
for r in recs.values():
    c = collections.Counter(p for a, b, _ in r['pairs'] for p in (a, b))
    counts += list(c.values())
dist = collections.Counter(min(k, 5) for k in counts)
print(f'{exp}/{pol}/{fam}: {len(recs)} seeds, {len(counts)} served member-episodes')
print('introductions per served member: mean %.2f, median %d, max %d' % (st.mean(counts), st.median(counts), max(counts)))
print('distribution: ' + ', '.join(f"{'5+' if k == 5 else k}: {100 * v / len(counts):.0f}%" for k, v in sorted(dist.items())))
print('Each introduction gives that member one response label at most, so these are also upper bounds on labels per person.')
