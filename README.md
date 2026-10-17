# Sequential Matching

### EmptyBrains | IITM

**Romeo & Juliet Hackathon — Sequential Matching Problem, Round 2**

A deterministic, defensive policy for sequential reciprocal introductions under incomplete information, delayed feedback, and daily clarification constraints.

The central result is deliberately modest: our submitted policy matches the supplied greedy baseline's outcome exactly on the declared evaluation seeds. Its contribution is a stronger execution contract—validated responses, bounded execution, fallback behavior, per-decision explanations, and reproducible experiments—rather than a claimed improvement in matching quality.

## The problem

The simulator introduces members over time. Information may be missing or declined, feasible supply can be sparse, and feedback from introductions arrives later. The policy must choose clarification requests and introductions without violating eligibility or protocol constraints.

The primary outcome is **Mutual Second-Meeting Intention (MSMI) per 100 arrived members**: realised mutual matches per 100 members who have arrived in the simulation.

The environment and member data are synthetic. Results should not be interpreted as evidence about real-world relationships.

## Submitted policy

The default `policy.py` mode (`method`) uses the supplied list-order clarification strategy and greedy matching over feasible, previously unproposed pairs. It wraps these decisions in a defensive validation and fallback layer.

1. **Ask:** request missing information in supplied list order within the remaining daily ask budget (12 units at the start of a day).
2. **Match:** select eligible, never-before-proposed pairs with the supplied greedy matcher.
3. **Validate:** validate the complete response against the request, including eligibility, availability, pair history, ask budget, JSON shape, and size limits.
4. **Fallback:** if candidate generation, validation, or timing fails, try the supplied baseline; if that also fails, return a protocol-shaped empty response.
5. **Explain:** emit one JSON diagnostic record per decision to stderr. Explanations distinguish missing data, heuristic-score uncertainty, and outcomes that have not yet been observed. Diagnostics do not alter the response.

The policy uses only observable request state and does not read hidden simulator values. It is deterministic in method mode and uses no trained assets.

### Runtime safeguards

- Standard-library-only submitted container.
- Stage deadlines with a total internal decision budget.
- Request, response, memory, and diagnostic size limits.
- Strict JSON serialization, including rejection of non-finite numeric values.
- A safe empty response as the final fallback.

The slowest individual call measured in the report was **0.27 seconds including Python startup**, against the evaluator's 10-second per-call limit. This is a local measurement, not a claim about the organisers' isolated execution environment.

## Evaluation results

The declared evaluation uses seeds **1181–1200**, 20 seeds per family, across six scenario families: `cold_start`, `delayed`, `development`, `drift`, `shift`, and `sparse`. Each policy was evaluated on 120 episodes.

### Overall MSMI

| Policy | Episodes | All episodes valid | MSMI per 100 |
|---|---:|---|---:|
| Submitted method | 120 | Yes | **0.375** |
| B1 — Greedy | 120 | Yes | **0.375** |
| B2 — No clarification | 120 | Yes | **0.104** |
| B3 — Random feasible | 120 | Yes | **0.325** |

The submitted method and B1 greedy produced identical decisions and outcome rows, episode by episode. Their only differences were in inference time. The matching score is therefore **not an improvement over greedy**; the added value is defensive behavior, validity, explanations, and auditability.

See [`results/final_tables.md`](results/final_tables.md) for per-family results and additional metrics, and [`REPORT.md`](REPORT.md) for the experimental design and failure analysis.

## Ablations: what we tested and cut

We pre-registered an admission rule: a component needed a replicated gain in mutual acceptances in at least one family, no detected loss in any family, and MSMI and coverage as no-loss checks. Comparisons used paired evaluations and 95% bootstrap intervals with 5,000 resamples.

| Component | Evidence | Decision |
|---|---|---|
| L1 — Maximum-weight (blossom) matching | On replication seeds 1221–1240, delayed-family mutual acceptances fell by 1.00 per 100; 95% bootstrap interval [−1.95, −0.05]. | **Cut** |
| L2 — Value-based clarification asks | In the sparse-family admission block, MSMI fell by 0.25 per 100; 95% bootstrap interval [−0.45, −0.05]. | **Cut** |

Both experiments remain behind `USE_BLOSSOM` and `USE_VALUE_ASKS` in `policy.py`, so the decisions can be reproduced. The submitted configuration keeps both disabled and uses list-order asks with greedy matching.

## Reproducibility and auditability

The Round 2 report records the following checks:

- **54 tests passed**.
- The data verification script reported the dataset as verified.
- Linux (Python 3.12) and Windows (Python 3.11) replication runs produced identical **240 outcome rows**.
- Docker was built and run locally by the team.
- The report records the public repository at commit `e1b88622318e20c110a37a34614d299308ca3aa4` for the audit snapshot.

The locally performed Docker check does not establish that the image was tested in the organisers' isolated environment.

## Reproduce

Use Python and Docker as available in your environment. From the repository root:

```bash
pip install -r requirements.txt

# Policy and fallback tests
python -m unittest test_method test_fallback

# Declared baseline/method evaluation
python evaluate.py --policy policy_default.py --seeds 1181,...,1200 --variants all --output results/method.json

# Admission experiment and summaries
python hackathon_files/round2_admission.py 1201-1220 2
python hackathon_files/round2_summary.py 1201-1220
python hackathon_files/final_tables.py > results/final_tables.md

# Container smoke test
docker build -t sequential-policy:submission .
python evaluate.py --image sequential-policy:submission --seeds 101
```

For the replication block, use seeds 1221–1240 as described in `REPORT.md` and the experiment scripts.

`policy_default.py` is a local wrapper that calls `policy.main([])`. The evaluator passes `--baseline` to policy scripts, whereas the submitted container launches `policy.py` in its default method mode.

## Repository structure

```text
.
├── kit.py, evaluate.py       # supplied simulator and evaluator
├── policy.py                 # policy, validation, fallbacks, explanations
├── policy_default.py         # local evaluator wrapper
├── test_method.py            # method tests
├── test_fallback.py          # fallback and runtime regression tests
├── REPORT.md                 # full Round 2 technical report
├── hackathon_files/          # admission experiments and report tables
├── lab_results/              # raw experiment rows
├── results/                  # evaluation outputs and final tables
├── data/, docs/, examples/   # supporting project materials
├── Dockerfile
└── requirements.txt
```

## Limitations

- Realised outcomes are strongly affected by pair compatibility and stochasticity. Twenty seeds per family cannot reliably detect effects of only a few percent.
- Reporting point estimates and bootstrap intervals does not mean every smaller loss would be detected.
- The supplied simulator and its members are synthetic; these results do not validate real-world relationship prediction.
- The submitted policy follows the greedy baseline's choices and does not learn from delayed outcomes.
- The Docker image was tested locally by the team, not in the organisers' isolated environment.

## Team

**EmptyBrains | IITM**

- **Vishnu P (LuisMckellen):** method, admission experiments, and report.
- **Subhadeep Das (emtypyie):** defensive policy adapter and fallback tests.
- **Taniya Jhabcah:** reporting pipeline.
- **Ameya (aetherx0):** baselines B1–B3.

## Provenance and licences

The simulator, evaluator, and data originate from the organisers' starter kit and are subject to the repository's `LICENSE` and `DATA_LICENSE.md`. The rejected maximum-weight matching experiment used NetworkX 3.6.1 (BSD-3-Clause); NetworkX is not part of the submitted container. No external pretrained models or datasets were used.
