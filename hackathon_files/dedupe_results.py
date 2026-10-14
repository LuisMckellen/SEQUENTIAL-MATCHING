"""Keep one row per (experiment, policy, family, seed) in a results.jsonl (last wins; rows are deterministic).
Usage: python hackathon_files/dedupe_results.py lab_results/results.jsonl"""
import json, sys
path = sys.argv[1]
seen, order = {}, []
for line in open(path, encoding='utf-8'):
    if not line.strip():
        continue
    r = json.loads(line)
    k = (r.get('experiment'), r.get('policy'), r.get('family'), r.get('seed'))
    if k not in seen:
        order.append(k)
    seen[k] = line if line.endswith('\n') else line + '\n'
open(path, 'w', encoding='utf-8', newline='\n').writelines(seen[k] for k in order)
print(f'{len(order)} unique rows kept')
