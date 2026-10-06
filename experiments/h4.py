import sys, json, math, time
sys.path.insert(0,'.')
import numpy as np, networkx as nx
from kit import generate, Simulator, baseline_asks
from exp import feasible_edges
from h1 import feats
import h1eval
M=h1eval.M
lg=lambda p: math.log(p/(1-p))
sg=lambda z: 1/(1+math.exp(-z))
def person_stats(state,k=4.0):
    # observable only: released feedback events
    resp={};yes={}
    for e in state['feedback']:
        if e['event'] not in ('introduction_response','second_meeting_intention'): continue
        i=e['member_id']; r=resp.setdefault(i,[0,0]); r[1]+=1
        if e['value'] is not None:
            r[0]+=1
            if e['event']=='introduction_response':
                y=yes.setdefault(i,[0,0]); y[1]+=1; y[0]+= e['value']=='yes'
    R=sum(v[0] for v in resp.values()); N=sum(v[1] for v in resp.values())
    Y=sum(v[0] for v in yes.values()); NY=sum(v[1] for v in yes.values())
    m_r=(R+8)/(N+10) if N else .8; m_y=min(max((Y+2)/(NY+4) if NY else .5,.05),.95)
    rho=lambda i:(resp.get(i,[0,0])[0]+k*m_r)/(resp.get(i,[0,0])[1]+k)
    off=lambda i:lg((yes.get(i,[0,0])[0]+k*m_y)/(yes.get(i,[0,0])[1]+k))-lg(m_y)
    return rho,off
def scored(state):
    E=feasible_edges(state)
    if not E: return []
    rho,off=person_stats(state)
    F=np.array([feats(a,b) for a,b,_ in E]+[feats(b,a) for a,b,_ in E])
    p=M.predict_proba(F)[:,1]; n=len(E); out=[]
    for i,(a,b,key) in enumerate(E):
        A,B=a['member_id'],b['member_id']
        pa=sg(lg(p[i])+off(A)); pb=sg(lg(p[n+i])+off(B))
        out.append(((rho(A)*rho(B))**2*pa*pb,key))
    return out
def resp_mwm(state):
    G=nx.Graph()
    for s,key in scored(state): G.add_edge(*key,weight=s)
    return [sorted(p) for p in nx.max_weight_matching(G)]
def resp_greedy(state):
    used=set();out=[]
    for s,key in sorted(scored(state),reverse=True):
        if not used.intersection(key): out.append(list(key)); used.update(key)
    return out
h1eval.P={'resp_mwm':resp_mwm,'resp_greedy':resp_greedy}
if __name__=='__main__':
    v=sys.argv[1]; seeds=[int(s) for s in sys.argv[2].split(',')]; t=time.time()
    with open('results_h1.jsonl','a') as f:
        for s in seeds:
            for p in h1eval.P: f.write(json.dumps(h1eval.run(p,s,v))+'\n'); f.flush()
    print('done',time.time()-t)
