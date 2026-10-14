# Final Report: EmptyBrains

**Team EmptyBrains, IITM × Romeo & Juliet: Sequential Matching Problem, Round 2.**
Method, admission experiments and report: Vishnu P (LuisMckellen). Defensive policy adapter and fallback tests: emtypyie. Reporting pipeline: Taniya Jhabcah. Baselines B1–B3: Ameya (aetherx0).

## 1. Summary

We submit a policy that cannot make an episode invalid. It uses the supplied list-order clarification and greedy matching inside a validation and fallback layer, and it writes an explanation record for every decision.

We also tested two components on top of this core, each against a rule we pre-registered in Round 1 (Section 6 of our research note):

- whole-pool maximum-weight matching (L1, hypothesis H4)
- value-based clarification (L2, hypothesis H2)

Both were rejected. L1 showed a detected loss in the `delayed` family on fresh seeds. L2 lost MSMI in `sparse`.

This matches the central finding of our Round 1 note (H1): in these worlds, policy choices move expected MSMI by a few percent at most, while pair compatibility and chance dominate. We report what was tested and what failed, rather than a gain that would not replicate.

## 2. Submitted policy

| Stage | What it does |
|---|---|
| Ask | The supplied list-order asks, within the 12-unit daily budget |
| Match | The supplied greedy matching over pairs that pass `eligibility()` and were never proposed before |
| Validity layer | Every response is validated against the request before it is returned. If the candidate fails or runs out of time, the policy falls back to the supplied baseline, then to an empty list (always valid) |
| Explanations | One JSON record per decision on stderr (Section 6). It never changes the response |

- **Fixed limits:** a stage deadline using SIGALRM, with a clock check where SIGALRM does not exist; 1 MiB caps on the request, response, memory and diagnostics.
- **Runtime:** the slowest call measured was below 1 s, including Python startup. The limit is 10 s.
- **Dependencies:** the container image uses the standard library only.

## 3. Results on the declared evaluation seeds

The declared seeds are 1181–1200, 20 per family, across all six families (120 episodes per policy). We used the supplied `evaluate.py` in trusted-local mode. The baselines are B1 greedy, B2 no asks and B3 random. All episodes were valid.

See `results/final_tables.md` for MSMI, coverage, mutual acceptances, waiting times, clarification cost, missing feedback and runtime per family. The raw data is in `results/method.json` and `results/B1_greedy.json`, `results/B2_no_asks.json` and `results/B3_random.json`.

The submitted policy makes the same decisions as B1 greedy. Its outcome rows are identical to B1, episode for episode; only `inference_seconds` differs. Its value is validity and explanation, not a different score.

## 4. Admission experiments and ablations

**Rule (pre-registered).** A component enters only with:
- a replicated gain in mutual acceptances in at least one family, using realised MSMI and coverage as no-loss checks; and
- no detected loss in any family.

The test design:
- paired comparisons against greedy on 20 fresh seeds per family;
- 95% bootstrap intervals with 5,000 resamples;
- admission block on seeds 1201–1220, replication block on seeds 1221–1240.

The raw rows are in `lab_results/results.jsonl`. The summaries are in `lab_results/r2_admission_1201-1220.txt` and `lab_results/r2_replication_1221-1240.txt`.

| Component (hypothesis) | Admission block 1201–1220 | Replication block 1221–1240 | Decision |
|---|---|---|---|
| L1 maximum-weight matching (H4: no loss against greedy) | No detected loss. Point gains in development (+0.35) and drift (+0.50) mutual acceptances per 100; intervals include 0 | **Delayed: mutual acceptances −1.00 [−1.95, −0.05].** Development +0.15; all MSMI intervals include 0 | Cut |
| L2 value-based asks (H2: better-targeted asks beat list order) | **Sparse: MSMI −0.25 [−0.45, −0.05]**, 0 wins / 15 ties / 5 losses. Ask cost lower in every family | Not run: already failed admission | Cut |

Both cuts are hypothesis-driven ablations. Each switches off exactly one component, controlled by `USE_BLOSSOM` and `USE_VALUE_ASKS` in `policy.py`, and is kept in the code so it can be reproduced.

**Reproducibility check.** We ran the replication block twice: on Linux with Python 3.12 and on Windows with Python 3.11. The 240 outcome rows were identical.

## 5. Failure analysis

**Sparse supply.**
- About 1.3 feasible options exist per matchable member.
- On 34–76% of days there is no feasible pair at all (Round 1 note, Section 2.1).
- A large group of members can never be served.
- The `sparse` family is where value-based asks failed. With almost no feasible partners, asks ranked by expected unlocks were spent on members whose answers then had no partner to unlock.

**Withheld answers.**
- A declined answer stays unavailable, and `eligibility()` keeps such a pair at `needs_clarification`.
- The policy never treats an unknown field as a match, and never asks a member again for a field they declined.
- In the Round 1 ceilings, perfect hard-constraint answers added only 3–4% to expected MSMI. That is the clearest measured lever, and its interval excludes 0.

**Delayed feedback.**
- Responses, dates and second-meeting answers arrive days later.
- The submitted policy does not learn from outcomes, so delay cannot bias it.
- The learner on probation (H3) handles delay by treating a pending window as no label, and a passed deadline as a missed response rather than a No (Round 1 note, Section 3.5).
- The `delayed` family is where maximum-weight matching lost.

**Competition for the same candidate.**
- When two pairs share a member, greedy takes the higher-scoring pair first. Maximum-weight matching instead resolves such conflicts across the whole pool.
- In Round 1 this changed 8% of introductions with no measurable gain.
- In Round 2 it produced a detected loss in `delayed`, which is why it was cut.

## 6. Explanations and uncertainty (PS §9)

For every introduction or ask, `policy.py` writes a record to stderr. It is written only after the response has been emitted. Each record keeps three sources of uncertainty separate:

- **Missing data:** for each side, the hard fields still unknown, the fields declined, and the number of soft fields known.
- **Model uncertainty:** the score is a count of equal known soft fields, not a probability, and the record says so.
- **Stochastic outcomes:** both responses are still unobserved until their deadlines.

Each record also lists the checks passed (always `feasible`, since hard constraints are never overridden) and the observed evidence (the number of equal soft fields). It never contains a latent simulator value; a test checks this.

## 7. Cold starts, uneven history, unknown preferences and delayed observations

- **Cold starts:** the submitted policy uses no per-member history, so a newcomer is treated exactly like everyone else, with feasibility decided only from observed fields.
- **Uneven history and delayed observations:** these cannot bias decisions, because no outcome model is used. The design for the learner on probation is given in Round 1, Section 3.5: pooled estimates, shrinkage and time-correct training.
- **Unknown preferences:** these are handled by `eligibility()` and clarification, not by guessing.
- **Exploration:** none.

## 8. Seeds and reproducibility

| Purpose | Seeds |
|---|---|
| Evaluation (declared) | 1181–1200, all six families |
| Admission | 1201–1220 |
| Replication | 1221–1240 |
| Inference random seed | Random baseline only: 17 + day. The submitted policy is deterministic |
| Training | None: no trained assets |

The README lists the exact commands under "Our Method".

## 9. Limitations

- **Statistical power:** realised MSMI is dominated by compatibility and chance, so 20 seeds per family cannot detect effects of a few percent (Round 1 note, Section 2.6). An admitted gain would have needed a larger effect than any component showed.
- **Loss-detection threshold:** we report point estimates and intervals, not significance tests. Some losses smaller than our intervals may go undetected.
- **Container check:** the Docker image was built and run locally by the team, not in the organisers' isolated environment.
- **Synthetic data:** the simulator and its members are synthetic. Nothing here is evidence about real relationships.

## 10. Provenance and licences

- `kit.py`, `evaluate.py` and the data are from the organisers' starter kit, under its licences (`LICENSE`, `DATA_LICENSE.md`).
- The rejected L1 experiment used `networkx` 3.6.1 (BSD-3-Clause). It is not part of the submitted image.
- No other external assets, models or data were used.
