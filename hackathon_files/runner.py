"""One definition of an episode run, its metrics and its metadata.
METHOD rules 15-19 and 24-25: every script imports this; nothing runs at import."""
import sys, json, itertools, platform, subprocess, os
sys.path.insert(0, '.')
from kit import generate, Simulator, eligibility


def parse_seeds(text):
    """'1101-1120' or '1101,1102' -> list of ints."""
    out = []
    for part in text.split(','):
        if '-' in part:
            a, b = part.split('-'); out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def feasible_edges(state):
    """Allowed, never-introduced pairs among available members (observable state only)."""
    members = [m for m in state['members'] if m['available']]
    past = {tuple(sorted((i['user_a'], i['user_b']))) for i in state['introductions']}
    out = []
    for a, b in itertools.combinations(members, 2):
        key = tuple(sorted((a['member_id'], b['member_id'])))
        if key in past or eligibility(a, b)['status'] != 'feasible':
            continue
        out.append((a, b, key))
    return out


def env_meta():
    def ver(mod):
        try:
            return __import__(mod).__version__
        except Exception:
            return None
    try:
        sha = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip() or None
    except Exception:
        sha = None
    return {'python': platform.python_version(), 'networkx': ver('networkx'), 'numpy': ver('numpy'),
            'sklearn': ver('sklearn'), 'git_sha': sha, 'pythonhashseed': os.environ.get('PYTHONHASHSEED')}


def funnel_ok(r):
    """Free identity (METHOD 15): assignments >= mutual acceptances >= dates >= MSMI."""
    return r['assignments'] >= r['mutual_acceptances'] >= r['dates'] >= r['mutual_second_meeting_intention']


def run_episode(ask_fn, match_fn, seed, family, trace_days=21):
    sim = Simulator(generate(seed, 200, 'evaluation', family))
    unlocked = []
    for day in range(60):
        sim.resolve_asks(ask_fn(sim.observe()))
        state = sim.observe()
        if day < trace_days:
            unlocked.append(len(feasible_edges(state)))
        sim.advance(match_fn(state))
    end = sim.observe()
    arrival = {m['member_id']: m['arrived_day'] for m in end['members'] if m['arrived_day'] <= 59}
    arrived = set(arrival)
    pairs = [[i['user_a'], i['user_b'], i['assigned_day']] for i in end['introductions']]
    served = {p for i in pairs for p in i[:2]}
    first = {}
    for a, b, day in pairs:
        for p in (a, b):
            first[p] = min(first.get(p, day), day)
    waits = sorted(first[p] - arrival[p] for p in arrived if p in first)   # PS 10: first-introduction waiting time
    for _ in range(40):
        sim.advance([])
    r = sim.metrics()
    n = r['arrived_members']
    return {'seed': seed, 'family': family, 'n_arrived': n,
            'msmi_per_100': r['msmi_per_100_arrived_members'],
            'mutual_per_100': 100 * r['mutual_acceptances'] / n,
            'assignments': r['assignments'], 'mutual_acceptances': r['mutual_acceptances'],
            'dates': r['dates'], 'msmi': r['mutual_second_meeting_intention'],
            'coverage': len(served & arrived) / n, 'ask_cost': r['ask_cost'],
            'feasible_per_day_d0_20': sum(unlocked) / len(unlocked),
            'missing_feedback': r['missing_feedback'],
            'wait_median_days': waits[len(waits) // 2] if waits else None,
            'wait_mean_days': sum(waits) / len(waits) if waits else None,
            'unserved': len(arrived - served),
            'funnel_ok': funnel_ok(r), 'pairs': pairs}


def write(path, experiment, policy, result):
    rec = {'experiment': experiment, 'policy': policy, **result, 'env': env_meta()}
    with open(path, 'a') as f:
        f.write(json.dumps(rec) + '\n')
