"""Lab 7d: does the learned acceptance model rank directional Yes better than greedy's score?

Greedy (kit.baseline_match) scores a pair by the number of soft fields both people have answered
equally. This script compares three scores on HELD-OUT rollouts (seeds never used for training):
  greedy  = count of equal soft fields (the supplied baseline's score)
  L8      = logistic model trained on the first 8 training rollouts (Lab 7 size, ~1,050 labels)
  Lfull   = logistic model trained on all training rollouts in the h1_scale.py cache
Metric: AUC for "this person says Yes", over revealed responses only (a no-response is not a No).
Intervals: 95% bootstrap over held-out EPISODES, paired (same resample for every score).
This is a proxy test: better ranking of Yes does not by itself mean more MSMI, because scarcity
limits how many introductions a ranking can change (Preliminary evidence, section 1).

Usage (repo root, PYTHONHASHSEED=0, PYTHONPATH=.), after h1_scale.py has built its cache:
  python hackathon_files\\h1_holdout.py 3001-3130 3131-3150            (~2 min, development)
  python hackathon_files\\h1_holdout.py 3001-3130 3131-3150 shift      (held-out worlds from another family)
"""
import sys, os, random, pickle
sys.path.insert(0, '.')
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from runner import parse_seeds
from h1_bootstrap import collect_pairs


def xy(groups):
    X = np.array([f for _, fs, _ in groups for f in fs]); y = np.array([l for _, _, ls in groups for l in ls])
    return X, y


def scores(groups, models):
    X, y = xy(groups)
    out = {'greedy': X[:, 0::2].sum(axis=1)}          # agree indicators sit at even positions
    for name, m in models.items():
        out[name] = m.decision_function(X)
    return out, y


if __name__ == '__main__':
    train = parse_seeds(sys.argv[1]) if len(sys.argv) > 1 else list(range(3001, 3131))
    test = parse_seeds(sys.argv[2]) if len(sys.argv) > 2 else list(range(3131, 3151))
    family = sys.argv[3] if len(sys.argv) > 3 else 'development'
    assert not set(train) & set(test), 'held-out seeds overlap training seeds'
    tr = pickle.load(open(f'h1c_groups_{train[0]}_{train[-1]}.pkl', 'rb'))
    cache = f'h1c_groups_{test[0]}_{test[-1]}' + ('' if family == 'development' else '_' + family) + '.pkl'
    if os.path.exists(cache):
        te = pickle.load(open(cache, 'rb'))
    else:
        te = collect_pairs(test, family); pickle.dump(te, open(cache, 'wb'))
    first8 = set(train[:8])
    models = {'L8': LogisticRegression(C=1.0, max_iter=1000).fit(*xy([g for g in tr if g[0] in first8])),
              'Lfull': LogisticRegression(C=1.0, max_iter=1000).fit(*xy(tr))}
    by_seed = {}
    for g in te:
        by_seed.setdefault(g[0], []).append(g)
    seeds = sorted(by_seed)
    s_all, y_all = scores(te, models)
    auc = {k: roc_auc_score(y_all, v) for k, v in s_all.items()}
    boots = {k: [] for k in ('greedy', 'L8', 'Lfull', 'Lfull-greedy', 'Lfull-L8')}
    for b in range(200):
        pick = random.Random(b).choices(seeds, k=len(seeds))
        s, y = scores([g for sd in pick for g in by_seed[sd]], models)
        a = {k: roc_auc_score(y, v) for k, v in s.items()}
        for k in ('greedy', 'L8', 'Lfull'):
            boots[k].append(a[k])
        boots['Lfull-greedy'].append(a['Lfull'] - a['greedy']); boots['Lfull-L8'].append(a['Lfull'] - a['L8'])
    print(f'held-out ({family}): {len(y_all)} revealed responses from {len(te)} introductions, {len(seeds)} rollouts '
          f'(seeds {seeds[0]}-{seeds[-1]}); Yes rate {y_all.mean():.3f}')
    print(f'training: {len(xy(tr)[1])} labels ({len(train)} rollouts); L8 uses the first 8 rollouts')
    for k in ('greedy', 'L8', 'Lfull'):
        lo, hi = np.percentile(boots[k], [2.5, 97.5])
        print(f'AUC {k:7s} {auc[k]:.3f}  [{lo:.3f}, {hi:.3f}]')
    for k, base in (('Lfull-greedy', 'greedy'), ('Lfull-L8', 'L8')):
        d = auc['Lfull'] - auc[base]; lo, hi = np.percentile(boots[k], [2.5, 97.5])
        print(f'diff {k:12s} {d:+.3f}  [{lo:+.3f}, {hi:+.3f}]')
