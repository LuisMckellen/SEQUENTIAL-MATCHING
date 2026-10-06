import sys, time, json, itertools
sys.path.insert(0,'.')
from kit import generate, Simulator, eligibility, baseline_asks, baseline_match, HARD, SOFT
import networkx as nx

def soft_score(a,b):
    return sum(a['fields'].get(k) is not None and a['fields'].get(k)==b['fields'].get(k) for k in SOFT)

def feasible_edges(state):
    members=[m for m in state['members'] if m['available']]
    past={tuple(sorted((i['user_a'],i['user_b']))) for i in state['introductions']}
    out=[]
    for a,b in itertools.combinations(members,2):
        key=tuple(sorted((a['member_id'],b['member_id'])))
        if key in past: continue
        if eligibility(a,b)['status']!='feasible': continue
        out.append((a,b,key))
    return out

def mwm_match(state):
    G=nx.Graph()
    for a,b,key in feasible_edges(state):
        G.add_edge(key[0],key[1],weight=1.0+soft_score(a,b))
    M=nx.max_weight_matching(G,maxcardinality=False)
    return [sorted(p) for p in M]

def voi_asks(state):
    mem=state['members']
    budget=state['ask_budget_remaining']
    cands=[m for m in mem if m['available'] and any(m['fields'][k] is None for k in HARD)
           and not any(m['field_status'][k]=='declined' for k in HARD)]
    complete=[m for m in mem if all(m['fields'][k] is not None for k in HARD)]
    unknown=[m for m in mem if any(m['fields'][k] is None for k in HARD) and not any(m['field_status'][k]=='declined' for k in HARD)]
    scored=[]
    for m in cands:
        known=sum(1 for j in complete if j['member_id']!=m['member_id'] and eligibility(m,j)['status']!='infeasible')
        avail_known=sum(1 for j in complete if j['available'] and j['member_id']!=m['member_id'] and eligibility(m,j)['status']!='infeasible')
        unk=sum(1 for j in unknown if j['member_id']!=m['member_id'] and eligibility(m,j)['status']!='infeasible')
        scored.append((avail_known+0.5*known+0.2*unk, m['member_id']))
    scored.sort(reverse=True)
    return [{'member_id':i,'field':'constraints'} for s,i in scored[:budget//3] if s>0]

POL={
 'greedy':(baseline_asks,baseline_match),
 'mwm':(baseline_asks,mwm_match),
 'voi_greedy':(voi_asks,baseline_match),
 'voi_mwm':(voi_asks,mwm_match),
}

def run(policy,seed,variant):
    ask,match=POL[policy]
    sim=Simulator(generate(seed,200,'evaluation',variant))
    t=time.time()
    for _ in range(60):
        sim.resolve_asks(ask(sim.observe()))
        sim.advance(match(sim.observe()))
    arrived={m['member_id'] for m in sim.members.values() if m['arrived_day']<=59}
    served=set()
    for i in sim.introductions: served.update([i['user_a'],i['user_b']])
    for _ in range(40): sim.advance([])
    r=sim.metrics()
    N=len(arrived)
    return dict(policy=policy,seed=seed,variant=variant,msmi=100*r['mutual_second_meeting_intention']/N,
                mutual=100*r['mutual_acceptances']/N,coverage=len(served&arrived)/N,assign=r['assignments'],
                dates=r['dates'],ask=r['ask_cost'],secs=time.time()-t)

if __name__=='__main__':
    print(run(sys.argv[1],int(sys.argv[2]),sys.argv[3]))
