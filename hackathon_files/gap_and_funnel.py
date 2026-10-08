"""Slides 9 and 15-16 applied to our runs.
(1) Gap closed: how far each policy moves from greedy toward the perfect-clarification ceiling,
    (policy - greedy) / (ceiling - greedy), paired per seed, with a 95% bootstrap interval.
(2) Failure analysis: where each policy's introductions leave the funnel.
Usage: python gap_and_funnel.py <family> <seeds>     (needs lab9_asking and ceiling_perfect_asks runs
       on the same seeds, made with the runner that records 'stages')"""
import sys, json, random, statistics as st
from runner import parse_seeds, STAGES

family, seeds = sys.argv[1], set(parse_seeds(sys.argv[2]))
rows = [json.loads(l) for l in open('lab_results/results.jsonl')]
rows = [r for r in rows if r['family'] == family and r['seed'] in seeds and
        r['experiment'] in ('lab9_asking', 'ceiling_perfect_asks')]
by = {}
for r in rows:                                   # last record per key wins (duplicates are identical)
    by.setdefault(r['seed'], {})[r['policy']] = r
ceil, base = 'perfect_asks_greedy', 'greedy'
keys = sorted(s for s in by if ceil in by[s] and base in by[s])
print('family', family, '| seeds with greedy + ceiling:', len(keys))
if len(keys) < 2:
    sys.exit('need at least 2 seeds with both greedy and ceiling records')


def boot(d, n=4000):
    m = sorted(st.mean(random.Random(i).choices(d, k=len(d))) for i in range(n))
    return m[int(.025 * n)], m[int(.975 * n) - 1]


metrics = ['feasible_per_day_d0_20', 'coverage', 'mutual_per_100', 'msmi_per_100', 'unserved']
print('\n(1) Ceiling vs greedy (headroom that perfect clarification would add)')
for m in metrics:
    d = [by[k][ceil][m] - by[k][base][m] for k in keys]
    lo, hi = boot(d)
    print('  %-24s greedy %.3f  ceiling %.3f  headroom %+.3f [%+.3f, %+.3f]' % (
        m, st.mean(by[k][base][m] for k in keys), st.mean(by[k][ceil][m] for k in keys), st.mean(d), lo, hi))

print('\n(2) Gap closed toward the ceiling = mean(policy - greedy) / mean(ceiling - greedy)')
for p in sorted({p for k in keys for p in by[k]} - {ceil, base}):
    ks = [k for k in keys if p in by[k]]
    for m in metrics:
        head = st.mean(by[k][ceil][m] - by[k][base][m] for k in ks)
        gain = st.mean(by[k][p][m] - by[k][base][m] for k in ks)
        hlo, hhi = boot([by[k][ceil][m] - by[k][base][m] for k in ks])
        if hlo <= 0 <= hhi:   # METHOD rule 21: no measurable headroom -> a ratio would be noise
            print('  %-12s %-24s headroom not distinguishable from 0 -> gap closed not meaningful' % (p, m)); continue
        if (head < 0) != (m == 'unserved'):   # for 'unserved' lower is better, so the ceiling's headroom is negative
            print('  %-12s %-24s ceiling is worse than greedy here -> gap closed undefined' % (p, m)); continue
        # bootstrap the ratio by resampling seeds
        rat = []
        for i in range(2000):
            s = random.Random(i).choices(ks, k=len(ks))
            h = st.mean(by[k][ceil][m] - by[k][base][m] for k in s)
            g = st.mean(by[k][p][m] - by[k][base][m] for k in s)
            if abs(h) > 1e-9:
                rat.append(g / h)
        rat.sort()
        lo, hi = rat[int(.025 * len(rat))], rat[int(.975 * len(rat)) - 1]
        print('  %-12s %-24s %5.0f%% of the gap [%+.0f%%, %+.0f%%]  (n=%d)' % (p, m, 100 * gain / head, 100 * lo, 100 * hi, len(ks)))

print('\n(3) Where introductions leave the funnel (share of all introductions, pooled over seeds)')
print('  %-20s %6s ' % ('policy', 'intros') + ' '.join('%17s' % s for s in STAGES))
for p in [base] + sorted({p for k in keys for p in by[k]} - {base, ceil}) + [ceil]:
    recs = [by[k][p] for k in keys if p in by[k] and 'stages' in by[k][p]]
    if not recs:
        print('  %-20s (no stage data: rerun with the current runner.py)' % p); continue
    tot = {s: sum(r['stages'][s] for r in recs) for s in STAGES}; n = sum(tot.values())
    assert n == sum(r['assignments'] for r in recs), 'stage counts must add up to assignments'
    print('  %-20s %6d ' % (p, n) + ' '.join('%7d (%5.1f%%)' % (tot[s], 100 * tot[s] / n) for s in STAGES))
