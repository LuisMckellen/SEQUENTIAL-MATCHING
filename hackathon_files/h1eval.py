"""Lab 6: learned score vs the supplied greedy baseline (greedy and blossom allocation).
Usage: PYTHONHASHSEED=0 PYTHONPATH=. python h1eval.py <family> <seeds>
Writes results.jsonl, experiment='h1_learned'. Run h1.py first."""
import sys, pickle
sys.path.insert(0, '.')
import numpy as np, networkx as nx
from kit import baseline_asks, baseline_match
from runner import feasible_edges, run_episode, write, parse_seeds
from h1 import feats

_MODEL = None
def model():
    global _MODEL
    if _MODEL is None:
        _MODEL = pickle.load(open('lab_results/models/h1_model.pkl', 'rb'))
    return _MODEL


def scored(state):
    E = feasible_edges(state)
    if not E:
        return []
    F = np.array([feats(a, b) for a, b, _ in E] + [feats(b, a) for a, b, _ in E])
    p = model().predict_proba(F)[:, 1]; n = len(E)
    return [(p[i] * p[n + i], key) for i, (a, b, key) in enumerate(E)]


def greedy_on(scores):
    used, out = set(), []
    for s, key in sorted(scores, reverse=True):
        if not used.intersection(key):
            out.append(list(key)); used.update(key)
    return out


def blossom_on(scores):
    G = nx.Graph()
    for s, key in scores:
        G.add_edge(*key, weight=s)
    return [sorted(p) for p in nx.max_weight_matching(G)]


POLICIES = {
    'greedy': baseline_match,
    'learned_greedy': lambda s: greedy_on(scored(s)),
    'learned_mwm': lambda s: blossom_on(scored(s)),
}

if __name__ == '__main__':
    family, seeds = sys.argv[1], parse_seeds(sys.argv[2])
    for seed in seeds:
        for name, match in POLICIES.items():
            write('lab_results/results.jsonl', 'h1_learned', name, run_episode(baseline_asks, match, seed, family))
        print('done seed', seed, flush=True)
