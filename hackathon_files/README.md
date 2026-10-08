# Experiment scripts (v2)

Put every file in the repo root next to `kit.py`. Install: `pip install networkx numpy scikit-learn`.
Always run as `PYTHONHASHSEED=0 PYTHONPATH=. python <script> ...`. Seeds accept `1101-1120` or `1101,1105`.

| Script | Lab | What it does | Writes |
|---|---|---|---|
| `runner.py` | all | One definition of an episode, its metrics (incl. missing feedback, first-introduction waiting times, unserved count, funnel stage of every introduction), the funnel check and run metadata. Imported, never run | — |
| `diagnose_graph.py <family> <seeds>` | 3 | Feasible pairs per day, options per matchable person, zero-pair days; prints a per-family summary | `graph.jsonl` |
| `h1.py [seeds]` | 7 | Trains the acceptance model (time-correct features). Default seeds 2001-2008 reproduce the note; for the build use the official training pools: `h1.py 20261000-20261005` | `h1_model.pkl` |
| `h1eval.py <family> <seeds>` | 6 | greedy vs learned score (greedy, blossom). Run `h1.py` first | `results.jsonl` (h1_learned) |
| `h4.py <family> <seeds> [prior]` | 6, 10 | Adds per-person reply rate and Yes-tendency; `resp_thompson` draws reply rates (Thompson). Rerun with prior 2, 4, 8 | `results.jsonl` (h4_resp_prior<k>) |
| `exp.py <family> <seeds> [policies]` | 9 | Question order: greedy vs value-based asks, with greedy, blossom and max-cardinality matching | `results.jsonl` (lab9_asking) |
| `summ.py <experiment> [baseline] [seeds]` | all | Per family (optionally only the given seeds): seed count, paired diffs with 95% intervals and W/T/L, decision diff, funnel violations | stdout |
| `h1_bootstrap.py [n_boot]` | 7b | Are the Lab 7 weights real? Bootstrap over introductions + split-half check on seeds 2001-2008. `collect_pairs(seeds, family)` is reused by 7c/7d | stdout |
| `per_person.py <experiment> <policy> <family> <seeds>` | C | Introductions per served member (upper bound on labels per person) | stdout |
| `h1_scale.py <seeds> [n_boot]` | 7c | Many random-feasible rollouts (use 3001-3130): episode-level bootstrap, split halves, learning curve at 8/16/32/64/all rollouts | `h1c_groups_<a>_<b>.pkl` (cache, not committed) |
| `h1_holdout.py <train seeds> <test seeds> [family]` | 7d | AUC for a directional Yes on held-out rollouts: greedy's equal-field count vs model on 8 rollouts vs on all. Run `h1_scale.py` first | `h1c_groups_<a>_<b>[_family].pkl` |
| `lab12_waiting.py <family> <seeds> ["policies"]` | 12 | H5 reserve (protected and pure) vs always match, plus the learned score vs greedy, using the Lab 7c model | `results.jsonl` (lab12_waiting) |
| `ceiling_policy_ANALYSIS_ONLY.py <family> <seeds>` | 11 | Workshop 2, slide 9: greedy with perfect clarification (hidden non-declined hard answers revealed free). Reads hidden truth: analysis only | `results.jsonl` (ceiling_perfect_asks) |
| `gap_and_funnel.py <family> <seeds>` | 11 | Workshop 2, slides 9 and 15-16: headroom to the ceiling, % of the gap each lab9 policy closes, and where introductions leave the funnel | stdout |
| `world_ceiling_ANALYSIS_ONLY.py` | — | Reads hidden truth. Analysis only, never in a policy | stdout |

Every result line carries `experiment`, `policy`, `family`, `seed`, `funnel_ok`, the introductions made (`pairs`) and `env` (versions, git SHA, PYTHONHASHSEED).

Seeds: preliminary training 2001-2008; preliminary test 1001-1015 (reproduce only, never tune); new experiments 1101-1120 (now seen for H3; new policy experiments start at 1121); acceptance model at scale: train 3001-3130, held-out test 3131-3150; Lab 12: 1121-1140 and replication 1141-1160.
Official pools (data_manifest.json, problem statement §4): train public_01-06 = seeds 20261000-20261005, validation public_07-08 = 20261006-20261007, development test public_09-10 = 20261008-20261009. `generate(seed, 200, pool_id, variant)` with these seeds reproduces the supplied pools.
In-process numbers are for exploring. Final reported numbers come from `evaluate.py` running `policy.py`.
Approximate runtime: 5 s per episode on one core.
