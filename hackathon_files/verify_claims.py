"""Check numeric claims in the v11 research note against observable state and committed files.
Reads NO hidden simulator data (no truth, bias or response rates): only sim.observe(), results.jsonl,
graph.jsonl and the organisers' supplied examples/baseline_results/*.json.
Usage (repo root): PYTHONHASHSEED=0 PYTHONPATH=. python hackathon_files/verify_claims.py"""
import sys, json, time, statistics as st
sys.path.insert(0, '.')
from kit import generate, Simulator, HARD, baseline_asks, baseline_match
from runner import run_episode

def rng(xs, pct=True):
    f = (lambda v: '%.0f%%' % (100 * v)) if pct else (lambda v: '%.1f' % v)
    return '%s (range %s-%s, n=%d)' % (f(st.mean(xs)), f(min(xs)), f(max(xs)), len(xs))

SEEDS = range(1101, 1121)

# C1: share of members with at least one declined hard field (whole world, observed after all arrivals)
print('C1  declined hard field  | note: 33% of members, 42% under cold_start')
for fam in ['development', 'cold_start', 'sparse']:
    shares = []
    for seed in SEEDS:
        sim = Simulator(generate(seed, 200, 'evaluation', fam))
        for _ in range(21):
            sim.advance([])                      # arrivals end by day 20; no exits before day 22
        ms = sim.observe()['members']
        assert len(ms) == 200
        shares.append(sum(any(m['field_status'][k] == 'declined' for k in HARD) for m in ms) / len(ms))
    print('    %-12s %s' % (fam, rng(shares)))

# C2: supplied greedy on development 1001-1015, from results.jsonl (experiment h1_learned)
rows = [json.loads(l) for l in open('lab_results/results.jsonl', encoding='utf-8')]
g = [r for r in rows if r['experiment'] == 'h1_learned' and r['policy'] == 'greedy'
     and r['family'] == 'development' and 1001 <= r['seed'] <= 1015]
print('\nC2  supplied greedy, development 1001-1015, n=%d' % len(g))
print('    introductions/episode  | note: about 92       | %s' % rng([r['assignments'] for r in g], False))
print('    coverage               | note: about 0.38     | %.3f' % st.mean(r['coverage'] for r in g))
m = st.mean(r['mutual_per_100'] for r in g); s = st.mean(r['msmi_per_100'] for r in g)
print('    mutual/MSMI event ratio | note: about 15x      | %.1fx (%.2f vs %.2f per 100)' % (m / s, m, s))
print('    MSMI events/episode    | note: about one      | %.2f' % st.mean(r['msmi'] for r in g))

# C3: graph diagnostic, development 1101-1120, from graph.jsonl
gr = [r for r in (json.loads(l) for l in open('lab_results/graph.jsonl', encoding='utf-8')) if r['family'] == 'development']
days = [d for r in gr for d in r['days']]
print('\nC3  graph, development 1101-1120, n_seeds=%d, %d seed-days' % (len(gr), len(days)))
av = sorted(d['available'] for d in days); hk = [d['hard_known'] for d in days]
print('    available per day      | note: about 150      | median %d (range %d-%d)' % (av[len(av)//2], av[0], av[-1]))
print('    of them, all hard known| note: 50-106         | range %d-%d' % (min(hk), max(hk)))
fp = [d['feasible_pairs'] for d in days]
print('    feasible pairs per day | note: 0-29           | range %d-%d, mean %.2f' % (min(fp), max(fp), st.mean(fp)))
mo = [d['mean_options'] for d in days if d['matchable']]
print('    options per matchable  | note: 1.0-1.9        | range %.2f-%.2f (per day)' % (min(mo), max(mo)))

# C4: organisers' supplied baseline files (public seed 101, one episode per family)
print('\nC4  supplied baseline files (organisers, seed 101)')
for n in ['greedy', 'no_asks', 'random']:
    o = json.load(open('examples/baseline_results/%s.json' % n, encoding='utf-8'))['summary']['overall']
    print('    %-8s MSMI/100 %.2f  coverage %.3f' % (n, o['msmi_per_100_arrived_members'], o['coverage']))
print('    note: baselines score 0.25-0.5 MSMI/100; removing clarification cuts coverage 0.41 -> 0.17')

# C5: runtime of one full in-process episode (greedy, development seed 1101)
t = time.perf_counter(); run_episode(baseline_asks, baseline_match, 1101, 'development')
print('\nC5  one in-process episode | note: about 5 s      | %.1f s' % (time.perf_counter() - t))
