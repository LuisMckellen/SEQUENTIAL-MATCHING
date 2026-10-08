# Lab results

Everything the experiments produced, in one place. Scripts in `hackathon_files/` read and write these paths;
run them from the repo root with `PYTHONHASHSEED=0` and `PYTHONPATH=.`.

| Path | What it is | Written by |
|---|---|---|
| `results.jsonl` | One record per episode (experiment, policy, family, seed, metrics, funnel stages, introductions made, environment) | `exp.py`, `h1eval.py`, `h4.py`, `ceiling_policy_ANALYSIS_ONLY.py`, `lab12_waiting.py`, `lab12_resume.py` |
| `graph.jsonl` | Daily feasible-graph diagnostics | `diagnose_graph.py` |
| `models/h1_model.pkl` | Acceptance model from Lab 7 (seeds 2001-2008) | `h1.py` |
| `summaries/` | Text outputs of every lab, named by lab and seed block (see below) | `summ.py`, `gap_and_funnel.py`, `per_person.py`, `h1_bootstrap.py`, `h1_scale.py`, `h1_holdout.py`, `verify_claims.py` |
| `LAB_REPORT.md` | The lab write-ups (Labs 0-9 and checks) | the team |
| `cache/` | Label caches for Labs 7c, 7d and 12 (regenerable; not committed) | `h1_scale.py`, `h1_holdout.py` |
| `archive/` | Superseded files: pre-dedupe result copies and an earlier model run (not committed) | - |

## Summaries by lab

| Lab | Files | Seeds |
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
| 12 | `lab12_h1_<seeds>.txt` (learned score vs greedy), `lab12_h5_<seeds>.txt` (waiting) | 1121-1140, 1141-1160, pooled |
| Claim check | `verify_claims.txt` | as listed in the file |

Files named `*ANALYSIS_ONLY*` come from runs that read hidden simulator data. They are for analysis only and are
never used by a policy.

Check the results file at any time: every line is valid JSON, there are no duplicate
(experiment, policy, family, seed) keys, and every record has `funnel_ok = true`.
