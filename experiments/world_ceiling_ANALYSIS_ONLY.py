"""ANALYSIS ONLY - reads hidden 'truth' fields. NEVER import or copy this into the policy:
reading hidden simulator state inside a submitted policy is disqualifying.
Counts servable members and feasible pairs if every non-declined hard answer were known."""
import sys, itertools, copy
sys.path.insert(0,'.')
from kit import generate, eligibility, HARD
for v in ['development','sparse','cold_start']:
    out=[]
    for seed in [1001,1002,1003]:
        w=generate(seed,200,'evaluation',v); ms=[]
        for m in w['members']:
            if any(m['field_status'][k]=='declined' for k in HARD): continue
            x=copy.deepcopy(m); x['fields'].update({k:m['truth'][k] for k in HARD}); ms.append(x)
        out.append((len(ms),sum(eligibility(a,b)['status']=='feasible' for a,b in itertools.combinations(ms,2))))
    print(v,'(servable members, feasible pairs):',out)
