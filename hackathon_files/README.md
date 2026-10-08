# Experiment scripts and lab results

This is the single guide to the team's experiments: the scripts in `hackathon_files/` and their outputs in `lab_results/`.
The repo-root `README.md` is the organisers' kit README and is left unchanged.

## How to run

Run every script from the repo root (next to `kit.py`):
`PYTHONHASHSEED=0 PYTHONPATH=. python hackathon_files/<script> ...` (PowerShell: set `$env:PYTHONHASHSEED="0"; $env:PYTHONPATH="."` first).
Install: `pip install networkx numpy scikit-learn`. Seeds accept `1101-1120` or `1101,1105`. Quote any comma-separated policy list in PowerShell.

## Scripts

| Script | Lab | What it does | Writes |
|---|---|---|---|
| `runner.py` | all | One definition of an episode, its metrics (incl. missing feedback, first-introduction waiting times, unserved count, funnel stage of every introduction), the funnel check and run metadata. Imported, never run | - |
| `diagnose_graph.py <family> <seeds>` | 3 | Feasible pairs per day, options per matchable person, zero-pair days; prints a per-family summary | `lab_results/graph.jsonl` |
| `h1.py [seeds]` | 7 | Trains the acceptance model (time-correct features). Default seeds 2001-2008 reproduce the note; for the build use the official training pools: `h1.py 20261000-20261005` | `lab_results/models/h1_model.pkl` |
| `h1eval.py <family> <seeds>` | 6 | Greedy vs learned score (greedy, blossom). Run `h1.py` first | `lab_results/results.jsonl` (h1_learned) |
| `h4.py <family> <seeds> [prior]` | 6, 10 | Adds per-person reply rate and Yes tendency; `resp_thompson` draws reply rates (Thompson). Rerun with prior 2, 4, 8 | `lab_results/results.jsonl` (h4_resp_prior<k>) |
| `exp.py <family> <seeds> [policies]` | 9 | Question order: greedy vs value-based asks, with greedy, blossom and max-cardinality matching | `lab_results/results.jsonl` (lab9_asking) |
| `summ.py <experiment> [baseline] [seeds]` | all | Per family (optionally only the given seeds): seed count, paired diffs with 95% intervals and W/T/L, decision diff, funnel violations | stdout |
| `h1_bootstrap.py [n_boot]` | 7b | Are the Lab 7 weights real? Bootstrap over introductions + split-half check on seeds 2001-2008. `collect_pairs(seeds, family)` is reused by 7c/7d | stdout |
| `per_person.py <experiment> <policy> <family> <seeds>` | C | Introductions per served member (upper bound on labels per person) | stdout |
| `h1_scale.py <seeds> [n_boot]` | 7c | Many random-feasible rollouts (use 3001-3130): episode-level bootstrap, split halves, learning curve at 8/16/32/64/all rollouts | `lab_results/cache/h1c_groups_<a>_<b>.pkl` |
| `h1_holdout.py <train seeds> <test seeds> [family]` | 7d | AUC for a directional Yes on held-out rollouts: greedy's equal-field count vs model on 8 rollouts vs on all. Run `h1_scale.py` first | `lab_results/cache/h1c_groups_<a>_<b>[_family].pkl` |
| `lab12_waiting.py <family> <seeds> ["policies"]` | 12 | H5 reserve (protected and pure) vs always match, plus the learned score vs greedy, using the Lab 7c model | `lab_results/results.jsonl` (lab12_waiting) |
| `lab12_resume.py [budget_seconds]` | 12 | Runs only the Lab 12 episodes not yet recorded, within a time budget (for shells that stop long jobs) | `lab_results/results.jsonl` (lab12_waiting) |
| `ceiling_policy_ANALYSIS_ONLY.py <family> <seeds>` | 11 | Workshop 2, slide 9: greedy with perfect clarification (hidden non-declined hard answers revealed free). Reads hidden truth: analysis only | `lab_results/results.jsonl` (ceiling_perfect_asks) |
| `gap_and_funnel.py <family> <seeds>` | 11 | Workshop 2, slides 9 and 15-16: headroom to the ceiling, % of the gap each lab9 policy closes, and where introductions leave the funnel | stdout |
| `verify_claims.py` | check | Re-checks numbers quoted in the note from observable data, the results files and the supplied baseline results | stdout |
| `world_ceiling_ANALYSIS_ONLY.py` | - | Reads hidden truth. Analysis only, never in a policy | stdout |

Every result line carries `experiment`, `policy`, `family`, `seed`, `funnel_ok`, the introductions made (`pairs`) and `env` (versions, git SHA, PYTHONHASHSEED).

## Results (`lab_results/`)

| Path | What it is | Committed |
|---|---|---|
| `results.jsonl` | One record per episode (experiment, policy, family, seed, metrics, funnel stages, introductions, environment) | yes |
| `graph.jsonl` | Daily feasible-graph diagnostics | yes |
| `models/h1_model.pkl` | Acceptance model from Lab 7 (seeds 2001-2008) | yes |
| `summaries/` | Text output of every lab (table below); save new summaries here with `Out-File` | yes |
| `LAB_REPORT.md` | The lab write-ups (Labs 0-9 and checks) | yes |
| `cache/` | Label caches for Labs 7c, 7d and 12 (regenerable) | no |
| `archive/` | Superseded files: pre-dedupe result copies and an earlier model run | no |

| Lab | Summary files in `summaries/` | Seeds |
|---|---|---|
| 3b | `lab3b_graph_1101-1120.txt` | 1101-1120 |
| 6 | `lab6_summ_1001-1015.txt`, `shift_summ_1001-1005.txt`, `shift_summ_1001-1015.txt` | 1001-1015 |
| 7 | `lab7_h1_weights.txt` | 2001-2008 |
| 7b | `lab7b_bootstrap.txt` | 2001-2008 |
| 7c | `lab7c_scale.txt` | 3001-3130 |
| 7d | `lab7d_holdout_dev.txt`, `lab7d_holdout_shift.txt` | 3131-3150 |
| 8 | `lab8_toy.txt` | toy example |
| 9 | `lab9_summ_1101-1120.txt` | 1101-1120 |
| 11, 11b | `lab11_<family>.txt`, `ceiling_ANALYSIS_ONLY.txt` | 1101-1120 |
| C | `per_person.txt` | 1101-1120 |
| 12 | `lab12_h1_<seeds>.txt` (learned score vs greedy), `lab12_h5_<seeds>.txt` (waiting) | 1121-1140, 1141-1160, pooled 1121-1160 |
| Claim check | `verify_claims.txt` | as listed in the file |

Files named `*ANALYSIS_ONLY*` come from runs that read hidden simulator data; they are for analysis only and never used by a policy.
Integrity check: every line of `results.jsonl` is valid JSON, no (experiment, policy, family, seed) key appears twice, and every record has `funnel_ok = true` (970 records as of commit 5fa3efd).

## Seeds

Preliminary training 2001-2008; preliminary test 1001-1015 (reproduce only, never tune); main experiments 1101-1120; acceptance model at scale: train 3001-3130, held-out test 3131-3150; Lab 12: 1121-1140 and replication 1141-1160. Seeds up to 1160 are spent; new experiments start at 1161.
Official pools (data_manifest.json, problem statement §4): train public_01-06 = seeds 20261000-20261005, validation public_07-08 = 20261006-20261007, development test public_09-10 = 20261008-20261009. `generate(seed, 200, pool_id, variant)` with these seeds reproduces the supplied pools.
In-process numbers are for exploring. Final reported numbers come from `evaluate.py` running `policy.py`. Approximate runtime: 3-6 s per episode on one core.
