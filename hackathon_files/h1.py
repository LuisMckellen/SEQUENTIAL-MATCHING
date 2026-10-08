"""Lab 7: learn which soft-field matches predict a directional Yes.
Plays 8 practice worlds (seeds 2001-2008) with random feasible pairing, saves features
on the assignment day (time-correct), labels from revealed responses only.
Usage: PYTHONHASHSEED=0 PYTHONPATH=. python h1.py [seeds]   -> h1_model.pkl
Default seeds 2001-2008 reproduce the research note. For the build, train on the official
training pools (data_manifest.json): python h1.py 20261000-20261005"""
import sys, random, pickle
sys.path.insert(0, '.')
import numpy as np
from kit import generate, Simulator, baseline_asks, SOFT
from runner import feasible_edges, parse_seeds


def feats(a, b):
    v = []
    for k in SOFT:
        fa, fb = a['fields'].get(k), b['fields'].get(k)
        both = fa is not None and fb is not None
        v += [1.0 if both and fa == fb else 0.0, 1.0 if both and fa != fb else 0.0]
    return v


def collect(seeds, family='development'):
    X, y = [], []
    for s in seeds:
        sim = Simulator(generate(s, 200, 'evaluation', family))
        snap = {}
        for d in range(60):
            sim.resolve_asks(baseline_asks(sim.observe()))
            st = sim.observe(); mem = {m['member_id']: m for m in st['members']}
            edges = feasible_edges(st)
            random.Random(s * 100 + d).shuffle(edges)
            used, pairs = set(), []
            for a, b, key in edges:
                if not used.intersection(key):
                    pairs.append(list(key)); used.update(key)
            for a, b in pairs:
                snap[(a, b, d)] = (feats(mem[a], mem[b]), feats(mem[b], mem[a]))
            sim.advance(pairs)
        for _ in range(40):
            sim.advance([])
        ev = {(e['introduction_id'], e['member_id']): e for e in sim.observe()['feedback']
              if e['event'] == 'introduction_response'}
        for i in sim.observe()['introductions']:
            fab, fba = snap[(i['user_a'], i['user_b'], i['assigned_day'])]
            for actor, f in ((i['user_a'], fab), (i['user_b'], fba)):
                e = ev.get((i['introduction_id'], actor))
                if e and e['value'] is not None:
                    X.append(f); y.append(1 if e['value'] == 'yes' else 0)
    return np.array(X), np.array(y)


if __name__ == '__main__':
    from sklearn.linear_model import LogisticRegression
    seeds = parse_seeds(sys.argv[1]) if len(sys.argv) > 1 else list(range(2001, 2009))
    X, y = collect(seeds)
    m = LogisticRegression(C=1.0).fit(X, y)
    names = [f'{k}_{t}' for k in SOFT for t in ('agree', 'disagree')]
    print(len(y), 'labels, base rate %.3f' % y.mean())
    for n, c in sorted(zip(names, m.coef_[0]), key=lambda t: -abs(t[1])):
        print('%-32s %+.2f' % (n, c))
    pickle.dump(m, open('lab_results/models/h1_model.pkl', 'wb'))
