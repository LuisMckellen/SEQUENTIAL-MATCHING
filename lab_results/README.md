# lab_results

Raw experiment output for the technical report (`../REPORT.md`).

- `results.jsonl`: one JSON record per episode (`experiment`, `policy`, `family`, `seed`, outcomes, `env`). One record per key.
- `r2_admission_1201-1220.txt` and `r2_replication_1221-1240.txt`: Round 2 admission and replication summaries (paired differences against greedy).
- `summaries/`: Round 1 text summaries, one file per experiment.
- `reporting/`: the reporting pipeline's tables (`metric_summary.csv`, `paired_comparisons.csv` and so on).
- `graph.jsonl`: feasible-pair graph diagnostics.

Scripts that produce these files are in `../hackathon_files/`, and its `README.md` lists the commands, seeds and what each script writes.
