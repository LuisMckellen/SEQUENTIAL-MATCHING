"""Lab 7b: are the learned soft-field weights distinguishable from noise?
Same data as h1.py (seeds 2001-2008, time-correct features, revealed responses only).
(1) Bootstrap over INTRODUCTIONS (both answers to one introduction stay together), 200 refits.
(2) Split-half check: fit on seeds 2001-2004 and 2005-2008 separately; a weight that flips sign is noise.
Usage: PYTHONHASHSEED=0 PYTHONPATH=. python h1_bootstrap.py [n_boot=200]   (~1 min)"""
import sys, random
sys.path.insert(0, '.')
import numpy as np
from sklearn.linear_model import LogisticRegression
from kit import SOFT
import h1

def collect_pairs(seeds):
    """Labels grouped by introduction: returns list of (features list, labels list) per introduction."""
    import random as _r
    from kit import generate, Simulator, baseline_asks
    from runner import feasible_edges
    groups = []
    for s in seeds:
        sim = Simulator(generate(s, 200, 'evaluation', 'development')); snap = {}
        for d in range(60):
            sim.resolve_asks(baseline_asks(sim.observe()))
            st = sim.observe(); mem = {m['member_id']: m for m in st['members']}
            edges = feasible_edges(st); _r.Random(s * 100 + d).shuffle(edges)
            used, pairs = set(), []
            for a, b, key in edges:
                if not used.intersection(key):
                    pairs.append(list(key)); used.update(key)
            for a, b in pairs:
                snap[(a, b, d)] = (h1.feats(mem[a], mem[b]), h1.feats(mem[b], mem[a]))
            sim.advance(pairs)
        for _ in range(40):
            sim.advance([])
        ev = {(e['introduction_id'], e['member_id']): e for e in sim.observe()['feedback'] if e['event'] == 'introduction_response'}
        for i in sim.observe()['introductions']:
            fab, fba = snap[(i['user_a'], i['user_b'], i['assigned_day'])]
            fs, ls = [], []
            for actor, f in ((i['user_a'], fab), (i['user_b'], fba)):
                e = ev.get((i['introduction_id'], actor))
                if e and e['value'] is not None:
                    fs.append(f); ls.append(1 if e['value'] == 'yes' else 0)
            if ls:
                groups.append((s, fs, ls))
    return groups

def fit(groups):
    X = np.array([f for _, fs, _ in groups for f in fs]); y = np.array([l for _, _, ls in groups for l in ls])
    return LogisticRegression(C=1.0).fit(X, y).coef_[0], len(y)

if __name__ == '__main__':
    B = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    groups = collect_pairs(range(2001, 2009))
    names = [f'{k}_{t}' for k in SOFT for t in ('agree', 'disagree')]
    full, n = fit(groups)
    boots = []
    for b in range(B):
        rs = random.Random(b).choices(groups, k=len(groups))
        boots.append(fit(rs)[0])
    boots = np.array(boots)
    lo, hi = np.percentile(boots, 2.5, axis=0), np.percentile(boots, 97.5, axis=0)
    h_a, _ = fit([g for g in groups if g[0] <= 2004]); h_b, _ = fit([g for g in groups if g[0] >= 2005])
    print(f'{n} labels from {len(groups)} introductions; {B} bootstrap refits over introductions')
    print('%-32s %7s %18s %9s %9s  %s' % ('weight', 'full', '95% interval', 'half A', 'half B', 'verdict'))
    for i in np.argsort(-np.abs(full)):
        excl = lo[i] > 0 or hi[i] < 0; same = np.sign(h_a[i]) == np.sign(h_b[i])
        verdict = 'distinguishable' if excl and same else ('interval excludes 0 but halves disagree' if excl else 'not distinguishable from 0')
        print('%-32s %+7.2f  [%+6.2f, %+6.2f] %+9.2f %+9.2f  %s' % (names[i], full[i], lo[i], hi[i], h_a[i], h_b[i], verdict))
