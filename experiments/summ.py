import json,collections,statistics as st,random,sys
rows=[json.loads(l) for l in open('results_h1.jsonl')]
for v in sorted({r['variant'] for r in rows}):
    by=collections.defaultdict(dict)
    for r in rows:
        if r['variant']==v: by[r['seed']][r['policy']]=r
    pols=['greedy','learned_mwm','resp_greedy','resp_mwm']
    seeds=[s for s in by if all(p in by[s] for p in pols)]
    print(v,len(seeds),'seeds')
    for p in pols:
        rs=[by[s][p] for s in seeds]
        print(' %-12s msmi=%.2f mutual=%.2f dates=%.2f cov=%.3f assign=%.1f'%(p,*(st.mean(r[k] for r in rs) for k in ['msmi','mutual','dates','coverage','assign'])))
    for p in pols[1:]:
        for k in ['mutual','msmi']:
            d=[by[s][p][k]-by[s]['greedy'][k] for s in seeds]
            bs=sorted(st.mean(random.Random(i).choices(d,k=len(d))) for i in range(4000))
            print('  %-12s %-6s diff %+.2f [%+.2f, %+.2f] wins %d ties %d / %d'%(p,k,st.mean(d),bs[100],bs[3899],sum(x>0 for x in d),sum(x==0 for x in d),len(d)))
