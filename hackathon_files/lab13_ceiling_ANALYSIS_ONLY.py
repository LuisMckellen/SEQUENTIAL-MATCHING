"""Lab 13 ceilings: ANALYSIS ONLY. These rankers READ HIDDEN SIMULATOR DATA (true traits, true profiles,
and in one case the random draws themselves). They measure how much any ranking could possibly add over
greedy; nothing here may ever be used by a policy.

Each oracle ranks today's feasible pairs by part of the true chance of a qualifying outcome and allocates
greedily, with the supplied list-order asks, so only the ranking differs from greedy:

  O_resp      true reply rates only                 (r_A r_B)^2
  O_people    true person traits: reply rate, Yes tendency, second-meeting tendency (no profile fit)
  O_profile   complete true profiles only (soft-field fit, relationship goal), no person traits
  O_full      everything above; pair chemistry integrated out (its expectation)
  O_foresight perfect foresight: knows today's random draws, i.e. which introductions would succeed
              (chemistry and luck included). An absolute upper bound for ranking, not a target.

The formulas mirror kit.Simulator._prob and the second-meeting rule in kit.Simulator.advance; they were read
from the public source for experiment design only.
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'hackathon_files')
import math
import numpy as np
from kit import rand_for
from runner import feasible_edges

NODES, WEIGHTS = np.polynomial.hermite_e.hermegauss(9)
WEIGHTS = WEIGHTS / math.sqrt(2 * math.pi)
SHARED_SD = 0.45
FIELDS = {'relationship_goal': .7, 'relationship_pace': .4, 'lifestyle': .25, 'conversations': .2}
FIELDS_SHIFT = {'relationship_goal': .25, 'relationship_pace': .8, 'lifestyle': -.25, 'conversations': .5}


def sig(z):
    return 1 / (1 + np.exp(-z))


def accept_logit(variant, day, a, b, use_bias=True, use_fit=True):
    w = FIELDS_SHIFT if variant == 'shift' else FIELDS
    fit = sum(v * (1 if a['truth'][k] == b['truth'][k] else -.5) for k, v in w.items()) if use_fit else 0.0
    drift = -.5 if variant == 'drift' and day >= 35 else 0.0
    return -.25 + (a['bias'] if use_bias else 0.0) + fit + drift


def second_logit(a, b, use_bias=True, use_goal=True):
    goal = .4 * (a['truth']['relationship_goal'] == b['truth']['relationship_goal']) if use_goal else 0.0
    return .15 + (a['second_bias'] if use_bias else 0.0) + goal


def chain(variant, day, a, b, use_resp=True, use_bias=True, use_fit=True):
    """Pair-dependent part of P(qualifying outcome), chemistry integrated out."""
    s = SHARED_SD * NODES
    la, lb = accept_logit(variant, day, a, b, use_bias, use_fit), accept_logit(variant, day, b, a, use_bias, use_fit)
    sa, sb = second_logit(a, b, use_bias, use_fit), second_logit(b, a, use_bias, use_fit)
    e = float(np.sum(WEIGHTS * sig(la + s) * sig(lb + s) * sig(sa + s) * sig(sb + s)))
    resp = (a['response_rate'] * b['response_rate']) ** 2 if use_resp else 1.0
    return resp * e


def p_date_in_window(variant):
    """P(date within 30 days of assignment): response delays 1-7 each, then 1-14 days, plus 5-12 if delayed."""
    if variant != 'delayed':
        return 1.0
    ok = tot = 0
    for d1 in range(1, 8):
        for d2 in range(1, 8):
            for x in range(1, 15):
                for y in range(5, 13):
                    tot += 1; ok += max(d1, d2) + x + y <= 30
    return ok / tot


def expected_msmi(variant, day, a, b):
    """Full expected P(qualifying outcome) for one introduction (analysis-only measurement)."""
    return chain(variant, day, a, b) * 0.78 * (3 / 5) ** 2 * p_date_in_window(variant)


def foresight_success(sim, ia, ib):
    """Replays the simulator's own draws for this pair today (exactly as kit.Simulator.advance does)."""
    ia, ib = sorted([ia, ib]); ma, mb = sim.members[ia], sim.members[ib]
    r = rand_for(sim.world['seed'], ia, ib, sim.day)
    shared = r.gauss(0, .45); responded, accept, days = [], [], []
    for actor, other in ((ma, mb), (mb, ma)):
        responded.append(r.random() < actor['response_rate'])
        accept.append(r.random() < sim._prob(actor, other, shared))
        days.append(sim.day + r.randint(1, 7))
    if not (all(responded) and all(accept)):
        return 0
    date_day = max(days) + r.randint(1, 14)
    if sim.world['variant'] == 'delayed':
        date_day += r.randint(5, 12)
    if not r.random() < .78:
        return 0
    ok = date_day - sim.day <= 30
    for actor, other in ((ma, mb), (mb, ma)):
        answer = r.random() < actor['response_rate']; delay = r.randint(1, 5)
        p = 1 / (1 + math.exp(-(.15 + actor['second_bias'] + shared + .4 * (actor['truth']['relationship_goal'] == other['truth']['relationship_goal']))))
        yes = r.random() < p
        ok = ok and answer and yes and delay <= 3
    return int(ok)


def greedy_on(scores):
    used, out = set(), []
    for s, key in sorted(scores, reverse=True):
        if not used.intersection(key):
            out.append(list(key)); used.update(key)
    return out


FLAGS = {'O_resp': None, 'O_people': (True, True, False), 'O_profile': (False, False, True), 'O_full': (True, True, True)}


def make_oracle(kind, holder):
    def match(state):
        sim = holder['sim']; v = sim.world['variant']; d = sim.day
        scores = []
        for a, b, key in feasible_edges(state):
            ma, mb = sim.members[a['member_id']], sim.members[b['member_id']]
            if kind == 'O_resp':
                s = (ma['response_rate'] * mb['response_rate']) ** 2
            elif kind == 'O_foresight':
                s = foresight_success(sim, ma['member_id'], mb['member_id']) + 1e-3 * chain(v, d, ma, mb)
            else:
                use_resp, use_bias, use_fit = FLAGS[kind]
                s = chain(v, d, ma, mb, use_resp, use_bias, use_fit)
            scores.append((s, key))
        return greedy_on(scores)
    return match


ORACLES = ('O_resp', 'O_people', 'O_profile', 'O_full', 'O_foresight')
