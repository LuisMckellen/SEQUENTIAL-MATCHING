"""Lab 13 learners: policies that use ONLY the observable state and released feedback (no hidden data).

Every learner allocates greedily by its score, with the supplied list-order asks, so the only thing that
differs from greedy is the score. Scores estimate the pair-dependent part of the chance of a qualifying
outcome: both people reply (twice: to the introduction and to the second-meeting question) and both say Yes.

  L_resp     reply rates learned from feedback:   r_A^2 * r_B^2 * pA * pB
  L_resp_ts  the same with reply rates SAMPLED from their posterior (Thompson sampling)
  L_people   L_resp plus each person's Yes tendency learned from their own answers

r_i  = posterior-mean reply rate: (k_i + m * r_pool) / (n_i + m), where k_i of n_i reply opportunities were
       answered (introduction responses and second-meeting answers, only once their deadline has passed or
       they arrived); r_pool is the pooled rate this episode, shrunk to a weak default; m = 4 observations.
pA   = P(A says Yes to B) from the Lab 7c soft-field model (130 random-feasible rollouts, observable features).
Yes tendency: y_i = (yes_i + m * y_pool) / (answers_i + m); pA is shifted by logit(y_A) - logit(y_pool).
Defaults r = 0.75 and y = 0.5 with weight 10 are hand-set and only matter before any feedback exists.
"""
import sys, math, hashlib, random
sys.path.insert(0, '.')
sys.path.insert(0, 'hackathon_files')
import numpy as np
from runner import feasible_edges
from h1 import feats
from lab12_waiting import model

M = 4.0
R_DEFAULT, Y_DEFAULT, W_DEFAULT = 0.75, 0.5, 10.0


def logit(p):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def sigmoid(z):
    return 1 / (1 + math.exp(-z))


def person_stats(state):
    """Reply and Yes counts per member from released feedback only."""
    n, k, ans, yes = {}, {}, {}, {}
    for e in state['feedback']:
        if e['event'] not in ('introduction_response', 'second_meeting_intention'):
            continue
        i = e['member_id']
        if e['value'] is not None:
            n[i] = n.get(i, 0) + 1; k[i] = k.get(i, 0) + 1
        elif e.get('missing_reason') == 'no_response':
            n[i] = n.get(i, 0) + 1
        if e['event'] == 'introduction_response' and e['value'] in ('yes', 'no'):
            ans[i] = ans.get(i, 0) + 1; yes[i] = yes.get(i, 0) + (e['value'] == 'yes')
    N, K = sum(n.values()), sum(k.values()); A, Y = sum(ans.values()), sum(yes.values())
    r_pool = (K + W_DEFAULT * R_DEFAULT) / (N + W_DEFAULT)
    y_pool = (Y + W_DEFAULT * Y_DEFAULT) / (A + W_DEFAULT)
    return n, k, ans, yes, r_pool, y_pool


def directional(E):
    if not E:
        return [], []
    F = np.array([feats(a, b) for a, b, _ in E] + [feats(b, a) for a, b, _ in E])
    p = model().predict_proba(F)[:, 1]; n = len(E)
    return p[:n], p[n:]


def greedy_on(scores):
    used, out = set(), []
    for s, key in sorted(scores, reverse=True):
        if not used.intersection(key):
            out.append(list(key)); used.update(key)
    return out


def make_learner(kind):
    def match(state):
        E = feasible_edges(state)
        if not E:
            return []
        n, k, ans, yes, r_pool, y_pool = person_stats(state)
        pab, pba = directional(E)
        day = state['day']

        def r_of(i):
            ni, ki = n.get(i, 0), k.get(i, 0)
            if kind == 'L_resp_ts':
                h = int.from_bytes(hashlib.sha256(f'{day}|{i}'.encode()).digest()[:8], 'big')
                return random.Random(h).betavariate(M * r_pool + ki, M * (1 - r_pool) + (ni - ki))
            return (ki + M * r_pool) / (ni + M)

        def shift(i):
            if kind != 'L_people':
                return 0.0
            y = (yes.get(i, 0) + M * y_pool) / (ans.get(i, 0) + M)
            return logit(y) - logit(y_pool)

        scores = []
        for idx, (a, b, key) in enumerate(E):
            ia, ib = a['member_id'], b['member_id']
            pa = sigmoid(logit(pab[idx]) + shift(ia)); pb = sigmoid(logit(pba[idx]) + shift(ib))
            scores.append(((r_of(ia) * r_of(ib)) ** 2 * pa * pb, key))
        return greedy_on(scores)
    return match


LEARNERS = {name: make_learner(name) for name in ('L_resp', 'L_resp_ts', 'L_people')}
