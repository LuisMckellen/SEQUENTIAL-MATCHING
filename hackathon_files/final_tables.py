"""Tables for the report from the evaluator's JSON files (results/B1_greedy, B2_no_asks, B3_random, method).
Usage: python hackathon_files/final_tables.py > results/final_tables.md
Per family: means over seeds; method vs greedy: paired difference with a 95% bootstrap interval and W/T/L."""
import json, random, statistics as st

FILES = [('B1 greedy', 'results/B1_greedy.json'), ('B2 no-clarification', 'results/B2_no_asks.json'),
         ('B3 random-feasible', 'results/B3_random.json'), ('Method', 'results/method.json')]
COLS = [('msmi_per_100_arrived_members', 'MSMI/100'), ('mutual_acceptances_per_100', 'mutual/100'),
        ('coverage', 'coverage'), ('ask_cost', 'ask cost'), ('missing_feedback', 'missing feedback'),
        ('wait', 'median first wait (days)'), ('inference_seconds', 'inference s / episode')]
data = {}
for name, path in FILES:
    j = json.load(open(path))
    eps = j['episodes']
    for e in eps:
        w = sorted(e.get('first_introduction_wait_days') or [])
        e['wait'] = w[len(w) // 2] if w else None
    data[name] = {(e['variant'], e['seed']): e for e in eps}
    print(f"- {name}: {len(eps)} episodes, all valid: {all(e['valid'] for e in eps)}, mode {j.get('mode')}, "
          f"overall MSMI/100 {j['summary']['overall']['msmi_per_100_arrived_members']:.3f}")
fams = sorted({k[0] for k in data['Method']})
seeds = sorted({k[1] for k in data['Method']})
print(f"\nSeeds {seeds[0]}-{seeds[-1]} ({len(seeds)} per family), families: {', '.join(fams)}.\n")
for col, label in COLS:
    print(f"\n**{label}** (mean over seeds)\n\n| family | " + ' | '.join(n for n, _ in FILES) + ' |\n|---|' + '---|' * len(FILES))
    for f in fams + ['all']:
        cells = []
        for n, _ in FILES:
            v = [e[col] for (fam, s), e in data[n].items() if (f == 'all' or fam == f) and e.get(col) is not None]
            cells.append(f"{st.mean(v):.3f}" if v else '-')
        print(f"| {f} | " + ' | '.join(cells) + ' |')
rng = random.Random(20261014)
print('\n**Method minus B1 greedy, paired by seed** (mean [95% bootstrap interval], wins/ties/losses)\n')
print('| family | MSMI/100 | mutual/100 | coverage | ask cost |\n|---|---|---|---|---|')
for f in fams + ['all']:
    row = []
    for col in ['msmi_per_100_arrived_members', 'mutual_acceptances_per_100', 'coverage', 'ask_cost']:
        keys = [k for k in data['Method'] if (f == 'all' or k[0] == f) and k in data['B1 greedy']]
        d = [data['Method'][k][col] - data['B1 greedy'][k][col] for k in keys]
        b = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(5000))
        row.append(f"{st.mean(d):+.3f} [{b[124]:+.3f}, {b[4874]:+.3f}] {sum(x>0 for x in d)}/{sum(x==0 for x in d)}/{sum(x<0 for x in d)}")
    print(f"| {f} | " + ' | '.join(row) + ' |')
