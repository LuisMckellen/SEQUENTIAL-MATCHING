"""Lab 3: how many choices exist? Feasible-graph diagnostic at scale (observable state only).
Runs the supplied baseline and logs, every day: available members, members with all hard
fields known, new feasible pairs, matchable members (>= 1 option) and their mean options.
Usage: PYTHONHASHSEED=0 PYTHONPATH=. python diagnose_graph.py <family> <seeds>
Writes graph.jsonl (experiment='graph_diag') and prints a per-family summary."""
import sys, json, collections, statistics as st
sys.path.insert(0, '.')
from kit import generate, Simulator, baseline_asks, baseline_match, HARD
from runner import feasible_edges, env_meta, parse_seeds


def diagnose(seed, family):
    sim = Simulator(generate(seed, 200, 'evaluation', family))
    days = []
    for d in range(60):
        sim.resolve_asks(baseline_asks(sim.observe()))
        s = sim.observe()
        E = feasible_edges(s); deg = collections.Counter()
        for a, b, k in E:
            deg[k[0]] += 1; deg[k[1]] += 1
        avail = [m for m in s['members'] if m['available']]
        known = [m for m in avail if all(m['fields'][k] is not None for k in HARD)]
        days.append({'day': d, 'available': len(avail), 'hard_known': len(known), 'feasible_pairs': len(E),
                     'matchable': len(deg), 'mean_options': (sum(deg.values()) / len(deg)) if deg else 0.0})
        sim.advance(baseline_match(s))
    return days


if __name__ == '__main__':
    family, seeds = sys.argv[1], parse_seeds(sys.argv[2])
    per_seed = []
    for seed in seeds:
        days = diagnose(seed, family)
        rec = {'experiment': 'graph_diag', 'family': family, 'seed': seed, 'days': days, 'env': env_meta()}
        with open('lab_results/graph.jsonl', 'a') as f:
            f.write(json.dumps(rec) + '\n')
        fp = [d['feasible_pairs'] for d in days]
        mo = [d['mean_options'] for d in days if d['matchable']]
        share_m = [d['matchable'] / d['available'] for d in days if d['available']]
        per_seed.append((st.mean(fp), max(fp), sum(x == 0 for x in fp) / len(fp),
                         st.mean(mo) if mo else 0.0, st.mean(share_m)))
        print('seed', seed, 'mean feasible pairs/day %.1f, max %d, zero-days %.0f%%, options per matchable %.2f, '
              'share of available with >=1 option %.0f%%' % (per_seed[-1][0], per_seed[-1][1], 100 * per_seed[-1][2],
                                                             per_seed[-1][3], 100 * per_seed[-1][4]), flush=True)
    cols = list(zip(*per_seed))
    rng = lambda c: '%.2f (range %.2f-%.2f)' % (st.mean(c), min(c), max(c))
    print('\nSUMMARY', family, 'n_seeds =', len(per_seed))
    print(' feasible pairs per day:      ', rng(cols[0]))
    print(' share of zero-pair days:     ', rng(cols[2]))
    print(' options per matchable person:', rng(cols[3]))
    print(' share of available matchable:', rng(cols[4]))
