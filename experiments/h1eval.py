import sys, json, pickle, time
sys.path.insert(0,'.')
import numpy as np, networkx as nx
from kit import generate, Simulator, baseline_asks, baseline_match
from exp import feasible_edges
from h1 import feats
M=pickle.load(open('h1_model.pkl','rb'))
def scored(state):
    E=feasible_edges(state)
    if not E: return []
    F=np.array([feats(a,b) for a,b,_ in E]+[feats(b,a) for a,b,_ in E])
    p=M.predict_proba(F)[:,1]; n=len(E)
    return [(p[i]*p[n+i],key) for i,(a,b,key) in enumerate(E)]
def learned_greedy(state):
    used=set();out=[]
    for s,key in sorted(scored(state),reverse=True):
        if not used.intersection(key): out.append(list(key)); used.update(key)
    return out
def learned_mwm(state):
    G=nx.Graph()
    for s,key in scored(state): G.add_edge(*key,weight=s)
    return [sorted(p) for p in nx.max_weight_matching(G)]
P={'greedy':baseline_match,'learned_greedy':learned_greedy,'learned_mwm':learned_mwm}
def run(pol,seed,variant):
    sim=Simulator(generate(seed,200,'evaluation',variant))
    for _ in range(60):
        sim.resolve_asks(baseline_asks(sim.observe())); sim.advance(P[pol](sim.observe()))
    arrived={m['member_id'] for m in sim.members.values() if m['arrived_day']<=59}
    served=set()
    for i in sim.introductions: served.update([i['user_a'],i['user_b']])
    for _ in range(40): sim.advance([])
    r=sim.metrics(); N=len(arrived)
    return dict(policy=pol,seed=seed,variant=variant,msmi=100*r['mutual_second_meeting_intention']/N,
        mutual=100*r['mutual_acceptances']/N,dates=r['dates'],coverage=len(served&arrived)/N,assign=r['assignments'])
if __name__=='__main__':
    variant=sys.argv[1]; seeds=[int(s) for s in sys.argv[2].split(',')]
    t=time.time()
    with open('results_h1.jsonl','a') as f:
        for s in seeds:
            for p in P: f.write(json.dumps(run(p,s,variant))+'\n'); f.flush()
    print('done',time.time()-t)
