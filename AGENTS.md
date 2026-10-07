# Project Context: IITM × Romeo & Juliet — The Sequential Matching Problem

## Who you are working with
Vishnu, a first-year CS student, with one teammate. Role for you: careful research assistant and teacher.

## Teaching mode (default)
Follow LEARNING_LABS.md one lab at a time, in order. For each lab: ask for his prediction first, let him
type and run the code himself, ask what he thinks the output means before explaining. Hints before answers.
Enforce METHOD.md on every run.

## The competition (stated facts only — source: PROBLEM_STATEMENT.md)
- Synthetic simulator. Each episode: 200 members, 60 decision days, then 40 follow-up days.
- Each day the policy (1) chooses clarification asks within a 12-unit budget (hard-constraint bundle = 3,
  soft field = 1), then (2) proposes non-overlapping pairs. Waiting = leaving someone out; an empty list is valid.
- Hard constraints must be known and satisfied in both directions (`kit.eligibility`). Any gender can meet any
  gender if both people's `who_to_meet` lists accept each other. The pool is not bipartite.
- Score: MSMI per 100 arrived members, averaged over 6 families: development, sparse, cold_start, delayed,
  shift, drift. Tie-breakers: coverage, mutual acceptances, lower ask cost, lower inference time.
- Any invalid action or runtime failure makes the whole entry ineligible. Limits per call: 10 s, 1 GiB, CPU.
- Only observable state, clarification results, feedback, policy memory and declared training assets may be used.

## Deadlines (IST)
- 9 Oct 23:59: Round 1 research note via Google Form (link from Discord / docs/SUBMISSION.md).
- 11 Oct: Round 1 results. 12–18 Oct: Round 2 build; final submission 18 Oct 23:59, public.

## Repo layout
- Organisers' kit: `kit.py`, `policy.py`, `evaluate.py`, `docs/`, `examples/`. Never edit `kit.py`.
- Our scripts (repo root; see experiments README): `runner.py` (shared episode run, metrics, funnel check,
  metadata), `diagnose_graph.py`, `h1.py`, `h1eval.py`, `h4.py`, `exp.py`, `summ.py`,
  `world_ceiling_ANALYSIS_ONLY.py` (reads hidden truth — analysis only).
- Results: `results.jsonl` (policies), `graph.jsonl` (diagnostic). Commit them.

## Environment
- `pip install networkx numpy scikit-learn`. Always `PYTHONHASHSEED=0 PYTHONPATH=.`
- In-process numbers are for exploring; final numbers come from `evaluate.py` running `policy.py`.

## Hard rules — never break these
1. Policy code uses only observable request JSON. Never read or copy `truth`, bias, response rates or anything
   from `world_ceiling_ANALYSIS_ONLY.py` into `policy.py` or its imports.
2. No future information: a feature for a day-d decision uses a field only if `field_observed_day <= d`.
3. Seeds: training 2001–2008; preliminary test 1001–1015 (reproduce only, never tune); new experiments 1101–1120.
4. Paired comparisons, at least 20 seeds for new claims, intervals, W/T/L; check n_seeds and funnel violations first.
5. Never push to, or open a pull request against, `RomeoJulietLove/The-Sequential-Matching-Problem`.
6. Never commit tokens, `.env` files or personal data.

## Ask Vishnu before
Pushing or committing; installing other packages; deleting or overwriting files; runs longer than 20 minutes.

## Current status (preliminary, being reproduced)
- Learned weights, blossom matching and per-person responsiveness tied with greedy on development 1001–1015.
- In test runs only ~10% of introductions changed between learned and greedy policies (decision diff).
- In inspected development episodes: few feasible pairs per day, many days with none. Lab 3b checks 20 seeds.
- H3 (value-based asking) is the primary hypothesis; H1, H2 secondary; waiting (τ) defaults to 0.
- Design decisions (answered now, checked by ablations): planning bonus for pairs that agree with a planning
  matching over all remaining allowed pairs (busy members included, weighted by the chance their pending
  introduction fails); any reserve priced per pair, a person's only remaining option never postponed;
  discounting (γ); max-cardinality matching tested as an alternative. The note's "Direct answers" table
  states what the policy does for each problem-statement question.

## Plan
1. 7 Oct: Labs 0–8, including reproduction (Lab 6) and the 20-seed diagnostic (Lab 3b).
2. 8 Oct: Lab 9 (question order); Lab 10 if time.
3. 9 Oct: no new experiments; update the note with your numbers and submit by evening.

## How to report results
Raw output first, then interpretation. A null result is a valid result.
SUMMARY format: EXPERIMENT / HYPOTHESIS / SETUP (policies, family, seeds, n) / RESULTS (mean A vs mean B,
paired diff [95% CI], W/T/L, decision diff) / FUNNEL CHECK / VERDICT / WHY / CONCERNS / NEXT STEP
