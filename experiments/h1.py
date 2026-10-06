import sys, json, itertools, random, pickle
sys.path.insert(0,'.')
import numpy as np
from kit import generate, Simulator, eligibility, baseline_asks, baseline_match, SOFT
from exp import feasible_edges
import networkx as nx

def feats(a,b):
    v=[]
    for k in SOFT:
        fa,fb=a['fields'].get(k),b['fields'].get(k)
        both=fa is not None and fb is not None
        v += [1.0 if both and fa==fb else 0.0, 1.0 if both and fa!=fb else 0.0]
    return v

def collect(seeds,variant='development'):
    X=[];y=[]
    for s in seeds:
        sim=Simulator(generate(s,200,'evaluation',variant))
        snap={}
        for d in range(60):
            sim.resolve_asks(baseline_asks(sim.observe()))
            st=sim.observe(); mem={m['member_id']:m for m in st['members']}
            edges=[e for e in feasible_edges(st)]
            random.Random(s*100+d).shuffle(edges)
            used=set();pairs=[]
            for a,b,key in edges:
                if not used.intersection(key): pairs.append(list(key)); used.update(key)
            for a,b in pairs: snap[(a,b,d)]=(feats(mem[a],mem[b]),feats(mem[b],mem[a]))
            sim.advance(pairs)
        for _ in range(40): sim.advance([])
        ev={(e['introduction_id'],e['member_id']):e for e in sim.receive_feedback() if e['event']=='introduction_response'}
        for i in sim.introductions:
            fab,fba=snap[(i['user_a'],i['user_b'],i['assigned_day'])]
            for actor,f in ((i['user_a'],fab),(i['user_b'],fba)):
                e=ev.get((i['introduction_id'],actor))
                if e and e['value'] is not None: X.append(f); y.append(1 if e['value']=='yes' else 0)
    return np.array(X),np.array(y)

if __name__=='__main__':
    from sklearn.linear_model import LogisticRegression
    X,y=collect(range(2001,2009))
    m=LogisticRegression(C=1.0).fit(X,y)
    names=[f'{k}_{t}' for k in SOFT for t in ('agree','disagree')]
    print(len(y),'labels, base rate %.3f'%y.mean())
    for n,c in sorted(zip(names,m.coef_[0]),key=lambda t:-abs(t[1])): print('%-32s %+.2f'%(n,c))
    pickle.dump(m,open('h1_model.pkl','wb'))
