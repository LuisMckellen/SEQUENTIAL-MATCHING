"""Diagnostic: feasible-graph density per day (observable state only)."""
import sys, collections, statistics as st
sys.path.insert(0,'.')
from kit import generate, Simulator, baseline_asks, baseline_match, HARD
from exp import feasible_edges
variant=sys.argv[1] if len(sys.argv)>1 else 'development'
for seed in [1001,1002]:
    sim=Simulator(generate(seed,200,'evaluation',variant))
    for d in range(60):
        sim.resolve_asks(baseline_asks(sim.observe())); s=sim.observe()
        E=feasible_edges(s); deg=collections.Counter()
        for a,b,k in E: deg[k[0]]+=1; deg[k[1]]+=1
        avail=[m for m in s['members'] if m['available']]
        known=[m for m in avail if all(m['fields'][k] is not None for k in HARD)]
        P=baseline_match(s)
        if d%6==0: print(variant,seed,'day %2d avail %3d hard-known %3d feasible %4d pairs %2d mean-degree %.1f'%(d,len(avail),len(known),len(E),len(P),st.mean(deg.values()) if deg else 0))
        sim.advance(P)
