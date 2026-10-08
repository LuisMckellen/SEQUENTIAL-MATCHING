"""Lab 12: does waiting help? (H5, the reserve threshold)

Same scorer, same asks, same seeds; the ONLY change is the reserve. Pair value V(A,B) = P(A says Yes)
x P(B says Yes) from the acceptance model trained on the Lab 7c cache (seeds 3001-3130, observable
features only). Greedy allocation on V. A pair is skipped today if

    V(A,B) - tau_A(t) - tau_B(t) <= 0,   tau_i(t) = tau0 * (59 - t)/59 * (1 - eta * [i never introduced])

with eta = 1 (no reserve for people never introduced, which protects coverage) and the note's values
rule: a pair is never skipped if it is either person's ONLY feasible option today.

Policies (experiment 'lab12_waiting'):
  greedy              supplied baseline_match (for reference: does the learned score reach outcomes?)
  learned_tau0        learned score, no reserve (always match)        <- the H5 baseline
  learned_tau0.10     reserve that skips pairs with a KNOWN weak value (V below about 0.20 early on)
  learned_tau0.12     aggressive reserve: also skips pairs whose value is just the default (about 0.224)
  learned_tau0.12_pure  the same reserve WITHOUT the two protections (eta = 0, only options not protected):
                      pure waiting, to measure what waiting itself costs or gains
Why these levels: most pairs have few known soft fields, so V sits at the model's default of about 0.224;
only pairs with known disagreements fall below it. tau0 = 0.10 targets those; 0.12 also holds back the
default pairs between previously introduced people early in the episode (real waiting).

Usage (repo root, PYTHONHASHSEED=0, PYTHONPATH=.; needs lab_results/cache/h1c_groups_3001_3130.pkl from Lab 7c):
  Step 1, fresh seeds 1121-1140, all five policies (~10 min per family):
    python hackathon_files\\lab12_waiting.py development 1121-1140
    python hackathon_files\\lab12_waiting.py cold_start 1121-1140
  Step 2, replication on NEW seeds 1141-1160, the three policies that matter (~6 min per family):
    python hackathon_files\\lab12_waiting.py development 1141-1160 "greedy,learned_tau0,learned_tau0.12_pure"
    python hackathon_files\\lab12_waiting.py cold_start 1141-1160 "greedy,learned_tau0,learned_tau0.12_pure"
  Optional third argument: a QUOTED comma-separated policy list (unquoted, PowerShell splits it).
Then, per seed block and pooled:
  python hackathon_files\\summ.py lab12_waiting learned_tau0 1121-1140   (H5: reserve vs always match)
  python hackathon_files\\summ.py lab12_waiting greedy 1121-1140         (H1: learned score vs greedy)
  ... the same with 1141-1160 and with 1121-1160
Seeds 1121-1160 are fresh: never used for any earlier experiment.
"""
import sys, pickle
sys.path.insert(0, '.')
import numpy as np
from sklearn.linear_model import LogisticRegression
from kit import baseline_asks, baseline_match
from runner import feasible_edges, run_episode, write, parse_seeds
from h1 import feats

CACHE = 'lab_results/cache/h1c_groups_3001_3130.pkl'
_MODEL = None


def model():
    global _MODEL
    if _MODEL is None:
        g = pickle.load(open(CACHE, 'rb'))
        X = np.array([f for _, fs, _ in g for f in fs]); y = np.array([l for _, _, ls in g for l in ls])
        _MODEL = LogisticRegression(C=1.0, max_iter=1000).fit(X, y)
    return _MODEL


def scored(state):
    E = feasible_edges(state)
    if not E:
        return []
    F = np.array([feats(a, b) for a, b, _ in E] + [feats(b, a) for a, b, _ in E])
    p = model().predict_proba(F)[:, 1]; n = len(E)
    return [(p[i] * p[n + i], key) for i, (a, b, key) in enumerate(E)]


def reserve_policy(tau0, eta=1.0, protect_only_option=True):
    def match(state):
        S = scored(state); t = state['day']
        seen = {p for i in state['introductions'] for p in (i['user_a'], i['user_b'])}
        deg = {}
        for _, (a, b) in S:
            deg[a] = deg.get(a, 0) + 1; deg[b] = deg.get(b, 0) + 1
        tau = lambda i: tau0 * (59 - t) / 59 * (1 - eta * (i not in seen))
        only = (lambda k: deg[k[0]] == 1 or deg[k[1]] == 1) if protect_only_option else (lambda k: False)
        kept = [(s, k) for s, k in S if only(k) or s - tau(k[0]) - tau(k[1]) > 0]
        used, out = set(), []
        for s, k in sorted(kept, reverse=True):
            if not used.intersection(k):
                out.append(list(k)); used.update(k)
        return out
    return match


POLICIES = {
    'greedy': baseline_match,
    'learned_tau0': reserve_policy(0.0),
    'learned_tau0.10': reserve_policy(0.10),
    'learned_tau0.12': reserve_policy(0.12),
    'learned_tau0.12_pure': reserve_policy(0.12, eta=0.0, protect_only_option=False),
}

if __name__ == '__main__':
    family, seeds = sys.argv[1], parse_seeds(sys.argv[2])
    names = sys.argv[3].split(',') if len(sys.argv) > 3 else list(POLICIES)
    for seed in seeds:
        for name in names:
            match = POLICIES[name]
            write('lab_results/results.jsonl', 'lab12_waiting', name, run_episode(baseline_asks, match, seed, family))
        print('done seed', seed, flush=True)
