# v11 experiment scripts

Copy these files into the root of the cloned kit repo (next to `kit.py`).
`pip install networkx numpy scikit-learn`. Everything runs in-process (~5 s per episode, one core).

| Script | What it does |
|---|---|
| `exp.py` | Pilot: greedy vs blossom vs value-based asks |
| `h1.py` | Collects time-correct training labels (seeds 2001-2008) and fits the acceptance model -> `h1_model.pkl`. Run first. |
| `h1eval.py` | Learned score vs greedy. `python h1eval.py development 1001,1002,1003` |
| `h4.py` | Adds per-person responsiveness. Same arguments as h1eval |
| `summ.py` | Paired differences with 95% bootstrap intervals over `results_h1.jsonl` |
| `diagnose_graph.py` | Feasible pairs per day and mean options per person |
| `world_ceiling_ANALYSIS_ONLY.py` | Reads hidden truth. Analysis only, never in the policy |

Training seeds 2001-2008 and test seeds 1001+ are disjoint. Keep it that way.
Final numbers must come from `evaluate.py` (subprocess/container), not these in-process scripts.
