"""Lab 6 (responsiveness) and Lab 10 (Thompson sampling) on per-person reply rates.
Per-person reply rate and Yes-tendency from released feedback only, shrunk to the pool
mean with a prior worth PRIOR observations (METHOD 20: rerun with 2, 4, 8).
Usage: PYTHONHASHSEED=0 PYTHONPATH=. python h4.py <family> <seeds> [prior=4]
Writes results.jsonl, experiment='h4_resp_prior<k>'."""
import sys, math, random, hashlib
sys.path.insert(0, '.')
import numpy as np
from kit import baseline_asks, baseline_match
from runner import feasible_edges, run_episode, write, parse_seeds
from h1 import feats
from h1eval import model, greedy_on, blossom_on

lg = lambda p: math.log(p / (1 - p))
sg = lambda z: 1 / (1 + math.exp(-z))
PRIOR = 4.0


def person_stats(state, k):
    resp, yes = {}, {}
    for e in state['feedback']:
        if e['event'] not in ('introduction_response', 'second_meeting_intention'):
            continue
        r = resp.setdefault(e['member_id'], [0, 0]); r[1] += 1
        if e['value'] is not None:
            r[0] += 1
            if e['event'] == 'introduction_response':
                y = yes.setdefault(e['member_id'], [0, 0]); y[1] += 1; y[0] += e['value'] == 'yes'
    R = sum(v[0] for v in resp.values()); N = sum(v[1] for v in resp.values())
    Y = sum(v[0] for v in yes.values()); NY = sum(v[1] for v in yes.values())
    m_r = (R + 8) / (N + 10) if N else .8
    m_y = min(max((Y + 2) / (NY + 4) if NY else .5, .05), .95)
    return resp, yes, m_r, m_y


def scored(state, thompson=False, k=None):
    k = PRIOR if k is None else k
    E = feasible_edges(state)
    if not E:
        return []
    resp, yes, m_r, m_y = person_stats(state, k)
    # Thompson: one draw per person per day, seeded from observable state (reproducible).
    tag = state['members'][0]['pool_id'] + '-' + str(state['day'])
    rng = random.Random(int(hashlib.md5(tag.encode()).hexdigest(), 16) % (2 ** 32))
    draws = {}

    def rho(i):
        r, n = resp.get(i, [0, 0])
        a, b = r + k * m_r, (n - r) + k * (1 - m_r)
        if not thompson:
            return a / (a + b)
        if i not in draws:
            draws[i] = rng.betavariate(a, b)
        return draws[i]

    def off(i):
        y, n = yes.get(i, [0, 0])
        return lg((y + k * m_y) / (n + k)) - lg(m_y)

    F = np.array([feats(a, b) for a, b, _ in E] + [feats(b, a) for a, b, _ in E])
    p = model().predict_proba(F)[:, 1]; n = len(E); out = []
    for i, (a, b, key) in enumerate(E):
        A, B = a['member_id'], b['member_id']
        pa, pb = sg(lg(p[i]) + off(A)), sg(lg(p[n + i]) + off(B))
        out.append(((rho(A) * rho(B)) ** 2 * pa * pb, key))
    return out


POLICIES = {
    'greedy': baseline_match,
    'resp_greedy': lambda s: greedy_on(scored(s)),
    'resp_mwm': lambda s: blossom_on(scored(s)),
    'resp_thompson': lambda s: blossom_on(scored(s, thompson=True)),
}

if __name__ == '__main__':
    family, seeds = sys.argv[1], parse_seeds(sys.argv[2])
    if len(sys.argv) > 3:
        PRIOR = float(sys.argv[3])
    exp_name = 'h4_resp_prior%g' % PRIOR
    for seed in seeds:
        for name, match in POLICIES.items():
            write('results.jsonl', exp_name, name, run_episode(baseline_asks, match, seed, family))
        print('done seed', seed, flush=True)
