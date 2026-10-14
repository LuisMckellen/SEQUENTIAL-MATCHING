# Sequential Matching and Information Acquisition for Reciprocal Introductions Under Incomplete Information and Dynamic Constraints

### EmptyBrains | IITM
## The Sequential Matching Problem

This project addresses **The One Introduction Problem**, where a system must decide who should be introduced to whom in a changing population with incomplete information.

The challenge is not simply to find the best pair. The system must make sequential decisions while considering:

- Reciprocal preferences
- Missing information
- Clarification costs
- Changing availability
- Previous introductions and feedback
- Constraints on concurrent introductions

## What We Build

Our system implements a decision policy that can:

1. Read the current population and available information.
2. Identify feasible reciprocal matches.
3. Decide when additional information is worth requesting.
4. Select introductions while respecting constraints.
5. Process feedback from previous introductions.
6. Update future decisions as the population changes.

The goal is to maximize the number of successful reciprocal introductions over time.

## Dataset

The provided dataset contains synthetic people and simulated interaction histories.

It includes:

- `members.jsonl` — member information
- `questionnaires.jsonl` — questionnaire responses
- `conversations.jsonl` — synthetic conversation records
- `introductions.jsonl` — previous introductions
- `feedback.jsonl` — introduction outcomes
- `state.json` — simulator state
- `members_flat.csv` — flattened member data

The dataset contains **2,000 synthetic adults** divided into independent pools.

## Matching Process

For each decision cycle, the system considers:

**Available members → Information → Feasible matches → Clarifications → Introductions → Feedback → Updated decisions**

A potential match must satisfy the relevant constraints for both people.

The system also has to ensure that a person is not assigned to multiple concurrent introductions and that previously attempted pairs are not repeated.

## Clarification

Additional information can be requested when the available information is insufficient to make a good decision.

However, clarification has a limited daily budget, so the system must decide whether obtaining additional information is worth its cost.

## Evaluation

The primary outcome is **Mutual Second-Meeting Intention (MSMI)**.

A successful outcome requires:

- The introduction is mutually accepted.
- The meeting occurs within the simulation period.
- Both participants indicate that they would like a second meeting.

The main metric is:

**MSMI per 100 arrived members**

The policy is evaluated against multiple simulated scenarios and compared with baseline strategies.

## Baselines

We consider simple baseline strategies such as:

- Greedy matching
- No-clarification matching
- Random feasible matching

Our policy is intended to improve upon these by combining reciprocal feasibility, information acquisition, and sequential allocation.

## Our Method (Round 2 submission)

`policy.py` with no arguments runs **method** mode:

- **Asks:** the supplied list-order asks within the daily 12-unit budget.
- **Matching:** maximum-weight matching (Edmonds' blossom, `networkx`) over feasible, never-before-proposed pairs, weight `1 + soft score`. This replaces the greedy pass, which can block two good pairs with one mediocre one.
- **Safety:** every proposal is validated before it is returned. If validation, the time limit or the `networkx` import fails, the policy falls back to the supplied greedy baseline, then to an empty list.

**Admission rule.** A component was kept only if it showed a gain on mutual acceptances in at least one family and no detected loss in any family on 20 fresh seeds per family, with paired bootstrap intervals against greedy.

| Component | Seeds 1201–1220 | Decision |
|---|---|---|
| L1 blossom matching | no loss in any family; coverage gain in cold_start | **kept** |
| L2 value-of-information asks | sparse MSMI −0.25 per 100 [−0.45, −0.05] | **cut** (ablation) |

L1 was replicated on seeds 1221–1240: RESULT_REPLICATION.

**Evaluation.** Declared seeds 1181–1200, all six variants (120 episodes per policy). RESULT_TABLE

### Reproduce

```bash
pip install -r requirements.txt
python -m unittest test_method test_fallback
python evaluate.py --policy policy_default.py --seeds 1181,...,1200 --variants all --output results/method.json
python hackathon_files/round2_admission.py 1201-1220 2           # admission
python hackathon_files/round2_summary.py 1201-1220
python hackathon_files/final_tables.py > results/final_tables.md
docker build -t sequential-policy:submission .
python evaluate.py --image sequential-policy:submission --seeds 101
```

`policy_default.py` only calls `policy.main([])`. It exists because `evaluate.py` always passes `--baseline`, while the container runs the default method mode.

## Repository Structure

```text
.
├── kit.py, evaluate.py      # supplied simulator and evaluator
├── policy.py                # submission policy (method mode + baselines + fallback)
├── policy_default.py        # local stand-in for the container entrypoint
├── test_method.py, test_fallback.py
├── hackathon_files/         # experiments: admission, summaries, tables
├── lab_results/             # raw experiment rows (results.jsonl)
├── results/                 # B1–B3 baselines, method.json, final_tables.md
├── data/, docs/, examples/
├── Dockerfile, requirements.txt
└── README.md
```

## Goal

The objective is to develop a reproducible sequential decision system that balances:

**Matching quality + Information value + Availability + Constraints**

rather than optimizing pair compatibility in isolation.

## Disclaimer

The simulator and dataset use synthetic people and synthetic interaction data. Results from the simulator should not be interpreted as evidence about real-world relationship prediction.
