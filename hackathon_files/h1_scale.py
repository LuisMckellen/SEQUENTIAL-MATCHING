"""Lab 7c: with enough rollouts, does the acceptance model find real structure?

Lab 7b showed 1,049 labels (8 rollouts) are too few: no weight could be trusted. Labels are
cheap, because the simulator can generate as many training worlds as we declare. This script:
  1. Collects time-correct labels from random-feasible rollouts on a FRESH declared seed block
     (same rules as h1.py: features frozen on the assignment day, revealed responses only).
  2. Bootstraps over EPISODES (whole seeds). People never cross episodes, so this also accounts
     for the same person appearing in several labels (Lab 7b resampled introductions, which
     ignores that and gives intervals that are too narrow).
  3. Split-half check: first half of the seeds vs second half; a weight must keep its sign.
  4. Learning curve: how interval width and the number of trusted weights change with rollouts.

Verdict per weight: "distinguishable" only if the episode-bootstrap interval excludes 0 AND both
halves agree in sign. The script never reads hidden simulator data.

Usage (from the repo root, PYTHONHASHSEED=0, PYTHONPATH=.):
  python hackathon_files\\h1_scale.py 3001-3130            (collect + analyse, ~5-10 min)
  python hackathon_files\\h1_scale.py 3001-3130 200        (n_boot, default 200)
Labels are cached in lab_results/cache/h1c_groups_<first>_<last>.pkl, so re-running the analysis is fast.
Seeds 3001-3130 are a new block: never used for any other experiment.
"""
import sys, os, random, pickle, time
sys.path.insert(0, '.')
import numpy as np
from sklearn.linear_model import LogisticRegression
from kit import SOFT
from runner import parse_seeds
from h1_bootstrap import collect_pairs

NAMES = [f'{k}_{t}' for k in SOFT for t in ('agree', 'disagree')]


def fit(groups):
    X = np.array([f for _, fs, _ in groups for f in fs])
    y = np.array([l for _, _, ls in groups for l in ls])
    return LogisticRegression(C=1.0, max_iter=1000).fit(X, y).coef_[0], len(y)


def analyse(groups, seeds, B, tag):
    by_seed = {}
    for g in groups:
        by_seed.setdefault(g[0], []).append(g)
    seeds = [s for s in seeds if s in by_seed]
    full, n = fit(groups)
    boots = []
    for b in range(B):
        pick = random.Random(b).choices(seeds, k=len(seeds))
        boots.append(fit([g for s in pick for g in by_seed[s]])[0])
    boots = np.array(boots)
    lo, hi = np.percentile(boots, 2.5, axis=0), np.percentile(boots, 97.5, axis=0)
    half = len(seeds) // 2
    h_a, _ = fit([g for s in seeds[:half] for g in by_seed[s]])
    h_b, _ = fit([g for s in seeds[half:] for g in by_seed[s]])
    verdicts = []
    for i in range(len(full)):
        excl = lo[i] > 0 or hi[i] < 0
        same = np.sign(h_a[i]) == np.sign(h_b[i])
        verdicts.append('distinguishable' if excl and same else
                        ('interval excludes 0 but halves disagree' if excl else 'not distinguishable from 0'))
    return dict(tag=tag, n=n, intros=len(groups), seeds=len(seeds), full=full, lo=lo, hi=hi,
                h_a=h_a, h_b=h_b, verdicts=verdicts, halves=(seeds[:half], seeds[half:]))


def show(r):
    a, b = r['halves']
    print(f"\n== {r['tag']}: {r['n']} labels from {r['intros']} introductions, {r['seeds']} rollouts ==")
    print(f"   bootstrap over episodes; halves = seeds {a[0]}-{a[-1]} vs {b[0]}-{b[-1]}")
    print('%-32s %7s %18s %8s %8s  %s' % ('weight', 'full', '95% interval', 'half A', 'half B', 'verdict'))
    for i in np.argsort(-np.abs(r['full'])):
        print('%-32s %+7.2f  [%+6.2f, %+6.2f] %+8.2f %+8.2f  %s' % (
            NAMES[i], r['full'][i], r['lo'][i], r['hi'][i], r['h_a'][i], r['h_b'][i], r['verdicts'][i]))


if __name__ == '__main__':
    seeds = parse_seeds(sys.argv[1]) if len(sys.argv) > 1 else list(range(3001, 3131))
    B = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    cache = f'lab_results/cache/h1c_groups_{seeds[0]}_{seeds[-1]}.pkl'
    if os.path.exists(cache):
        groups = pickle.load(open(cache, 'rb'))
        print(f'loaded {cache}')
    else:
        t = time.time(); groups = []
        for k in range(0, len(seeds), 10):
            chunk = seeds[k:k + 10]
            groups += collect_pairs(chunk)
            print(f'  collected seeds {chunk[0]}-{chunk[-1]}  ({time.time() - t:.0f}s)', flush=True)
        pickle.dump(groups, open(cache, 'wb'))
    final = analyse(groups, seeds, B, 'ALL ROLLOUTS')
    show(final)
    print('\n== Learning curve (episode bootstrap, same verdict rule) ==')
    print('%9s %8s %22s %18s' % ('rollouts', 'labels', 'mean interval width', 'distinguishable'))
    for k in [8, 16, 32, 64, len(seeds)]:
        if k > len(seeds):
            continue
        sub = set(seeds[:k])
        r = final if k == len(seeds) else analyse([g for g in groups if g[0] in sub], seeds[:k], B, f'first {k}')
        width = float(np.mean(r['hi'] - r['lo']))
        dist = [NAMES[i] for i, v in enumerate(r['verdicts']) if v == 'distinguishable']
        print('%9d %8d %22.2f %18d   %s' % (k, r['n'], width, len(dist), ', '.join(dist)))
