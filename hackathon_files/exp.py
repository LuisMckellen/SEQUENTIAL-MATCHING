"""Lab 9: does question order matter?  greedy vs value-based asks (+ blossom variants).
Usage: PYTHONHASHSEED=0 PYTHONPATH=. python exp.py <family> <seeds> [policies]
Writes results.jsonl, experiment='lab9_asking'."""
import sys
sys.path.insert(0, '.')
import networkx as nx
from kit import baseline_asks, baseline_match, eligibility, HARD, SOFT
from runner import feasible_edges, run_episode, write, parse_seeds


def soft_score(a, b):
    return sum(a['fields'].get(k) is not None and a['fields'].get(k) == b['fields'].get(k) for k in SOFT)


def blossom(state, maxcard=False):
    G = nx.Graph()
    for a, b, key in feasible_edges(state):
        G.add_edge(key[0], key[1], weight=1.0 + soft_score(a, b))
    return [sorted(p) for p in nx.max_weight_matching(G, maxcardinality=maxcard)]


def voi_asks(state):
    """Rank unresolved, available, non-declined members by how many partners an answer could unlock."""
    mem = state['members']
    blocked = lambda m: any(m['field_status'][k] == 'declined' for k in HARD)
    missing = lambda m: any(m['fields'][k] is None for k in HARD)
    cands = [m for m in mem if m['available'] and missing(m) and not blocked(m)]
    known = [m for m in mem if not missing(m)]
    unknown = [m for m in mem if missing(m) and not blocked(m)]
    scored = []
    for m in cands:
        ok = lambda j: j['member_id'] != m['member_id'] and eligibility(m, j)['status'] != 'infeasible'
        avail_known = sum(1 for j in known if j['available'] and ok(j))
        all_known = sum(1 for j in known if ok(j))
        unk = sum(1 for j in unknown if ok(j))
        scored.append((avail_known + 0.5 * all_known + 0.2 * unk, m['member_id']))
    scored.sort(reverse=True)
    return [{'member_id': i, 'field': 'constraints'} for s, i in scored[:state['ask_budget_remaining'] // 3] if s > 0]


POLICIES = {
    'greedy': (baseline_asks, baseline_match),
    'voi_greedy': (voi_asks, baseline_match),
    'voi_mwm': (voi_asks, lambda s: blossom(s)),
    'voi_maxcard': (voi_asks, lambda s: blossom(s, maxcard=True)),
}

if __name__ == '__main__':
    family, seeds = sys.argv[1], parse_seeds(sys.argv[2])
    names = sys.argv[3].split(',') if len(sys.argv) > 3 else list(POLICIES)
    for seed in seeds:
        for name in names:
            ask, match = POLICIES[name]
            write('results.jsonl', 'lab9_asking', name, run_episode(ask, match, seed, family))
        print('done seed', seed, flush=True)
