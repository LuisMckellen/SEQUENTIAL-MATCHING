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

## Repository Structure

```text
.
├── data/
├── docs/
├── src/
├── tests/
├── README.md
└── requirements.txt
```

## Goal

The objective is to develop a reproducible sequential decision system that balances:

**Matching quality + Information value + Availability + Constraints**

rather than optimizing pair compatibility in isolation.

## Disclaimer

The simulator and dataset use synthetic people and synthetic interaction data. Results from the simulator should not be interpreted as evidence about real-world relationship prediction.
