# Lab report: Sequential Matching Problem (7–8 Oct 2026)

Author: Vishnu. Every number below comes from runs I did myself, recorded in committed files in this repo.
Environment for every result: Python 3.14.7, networkx 3.7, numpy 2.5.3, scikit-learn 1.9.1, kit git 23f53f3, `PYTHONHASHSEED=0`, run on Windows from the repo root as `python hackathon_files\<script>`.
Evidence files: `results.jsonl` (370 records, 0 duplicate keys, 0 funnel violations), `graph.jsonl` (60 records), `h1_model.pkl`, plus the text summaries named in each log.
Seen seeds (reproduce only): 1001–1015, plus training seeds 2001–2008. Fresh seeds: 1101–1120. Nothing was tuned on any seed reported here.

---

## 1. Concepts learned
- **Observable state:** a policy may use only `sim.observe()`. `generate()` also holds hidden truth, bias and reply rates, which must never reach a policy.
- **Field status:** `observed`, `not_asked` (you can ask) or `declined` (unknown forever; asking can't reveal it).
- **None is not "no" and not "yes":** treating `None` as a failure loses candidates. Treating it as a pass gives an unverified introduction, which is an invalid action and disqualifies the entry.
- **Two-type population:** members are either complete (11/11 hard fields known) or mostly blank (~1 known). Report the groups, not the average.
- **Test a rule on the group it acts on:** declines only affect incomplete members, so check the rate there (50% observed vs 51% predicted).
- **Single-seed noise:** one world of ~137 people moves about ±10 in a count by chance alone.
- **Independent checks (rule 30):** a calculation and a measurement from the same generator agreeing only shows the code is right.
- **`eligibility()`:** infeasible / needs_clarification / feasible. A known failure wins over missing data. Age, gender and zone are always public.
- **Value of an ask:** asks unlock very different numbers of pairs (someone who wants only `non_binary` has ~8% of the pool to choose from).
- **Paired comparison:** both policies play the same seed, and the per-seed difference cancels the world's luck.
- **Bootstrap 95% interval:** resample the per-seed differences 4,000 times. If the interval includes 0, the data fits "no effect".
- **W/T/L:** wins/ties/losses per seed. Many ties on MSMI shows how rare the event is.
- **Decision diff (rule 7):** the share of introductions that changed. Check it before reading a tie.
- **Sizing the effect (rule 21):** compare the most a change could move the metric with the interval width. If it's smaller, a tie says nothing.
- **Square-root law:** interval width shrinks with √(seeds). Shrinking it 3.4× needs ~11.6× the seeds.
- **Determinism:** a rerun must give identical output. An identical accidental duplicate is free proof of that.
- **Trickle graph:** an introduction makes both people busy for 8 days (+6 after a date), a pair can never repeat, and people pause and exit. Feasible pairs get used almost the day they appear.
- **Small samples flip signs (rule 6):** shift MSMI was −0.30 on 5 seeds and +0.23 on 15 seeds.
- **Reproducibility hygiene:** set `PYTHONHASHSEED`/`PYTHONPATH` in every new terminal; run each command once; dedupe by key; add files to git by name.
- **Pickle safety:** a `.pkl` can run code when loaded. Load only your own files.
- **Label every claim (rule 22):** separate what I measured, what someone else claimed, and what is only a plan.

---

## 2. Experiment logs

### Lab 0: observable state on day 0
- **HYPOTHESIS:** member 0 has 11 or ~1 hard fields known (most likely ~1). Fully known ≈ 0.35 × arrived. At least one hard field declined ≈ 0.65 × 0.511 ≈ 33% of the pool, and ≈ 51% of incomplete members.
- **SETUP:** observe only; development; seed 1101; day 0; n = 1 seed (137 arrived).
- **RESULTS:** member 0 has 1/11 known. Fully known 55 vs 48 predicted. Declined 41 vs 45 predicted; 41/82 = 50.0% of incomplete members vs 51.1% predicted. No comparison, so no paired diff, CI, W/T/L or decision diff.
- **FUNNEL CHECK:** n/a (no episode).
- **VERDICT:** supported (all three within single-seed noise).
- **WHY:** the counts follow `generate()` lines 52–57 (35% complete, 10% per-field visibility, 7% decline).
- **CONCERNS:** one seed, day 0 only. Prediction and measurement share a generator, so this is not independent evidence.
- **NEXT STEP:** done at scale in the claim check (C1).

### Lab 1: pair feasibility on day 0
- **HYPOTHESIS:** 10–100 feasible pairs out of ~9,300; infeasible > needs_clarification.
- **SETUP:** `eligibility()` over all available pairs; development; seed 1101; day 0.
- **RESULTS:** not run.
- **FUNNEL CHECK:** n/a. **VERDICT:** inconclusive (not run). **WHY:** time. **CONCERNS:** none. **NEXT STEP:** optional; Lab 3b covers scarcity.

### Lab 6a: learned soft-field weights vs greedy (H1, H2)
- **HYPOTHESIS:** MSMI interval includes 0; decision diff under 5% (graph too sparse to matter).
- **SETUP:** `greedy`, `learned_greedy`, `learned_mwm`; development; seeds 1001–1015; n = 15. Model trained on seeds 2001–2008 (`h1.py`). Files: `results.jsonl` (`h1_learned`), `lab6_summ_1001-1015.txt`.
- **RESULTS:**
  - learned_greedy vs greedy: MSMI/100 0.567 vs 0.433, diff +0.133 [−0.033, +0.300], W/T/L 4/10/1. Mutual/100 6.600 vs 6.933, −0.333 [−0.967, +0.233], W/T/L 6/1/8. Decision diff 12% (2–22%).
  - learned_mwm vs greedy: MSMI 0.500 vs 0.433, +0.067 [−0.100, +0.233], W/T/L 4/9/2. Mutual +0.000 [−0.533, +0.600]. Decision diff 12% (2–23%).
- **FUNNEL CHECK:** pass (0 violations, 45 records, n_seeds = 15).
- **VERDICT:** MSMI interval includes 0, supported. Decision diff < 5%, not supported (12%). H1/H2 effect on MSMI: inconclusive.
- **WHY:** about 14 introductions differ per episode, and MSMI is ~0.0073 per introduction. Even doubling success on those gives about +0.05 per 100, against an interval half-width of ±0.17. The test cannot see an effect of the size this change could make (~173 seeds per family would be needed even in the best case).
- **CONCERNS:** MSMI is underpowered at 15–20 seeds. Determinism: `h1_model.pkl` MD5 `34c28546fca89074c3d177091920155b` on two separate trainings. Matches the v11 note exactly.
- **NEXT STEP:** develop on higher-event metrics; don't claim H1/H2 effects on MSMI.

### Lab 6b: per-person responsiveness vs greedy (H4)
- **HYPOTHESIS:** same as 6a.
- **SETUP:** `greedy`, `resp_greedy`, `resp_mwm`, `resp_thompson` (prior 4); development; seeds 1001–1015; n = 15. Files: `results.jsonl` (`h4_resp_prior4`), `lab6_summ_1001-1015.txt`.
- **RESULTS:**
  - resp_greedy: MSMI 0.433 vs 0.433, +0.000 [−0.200, +0.200], W/T/L 5/5/5. Mutual 6.633 vs 6.933, −0.300 [−0.933, +0.300]. Decision diff 12%.
  - resp_mwm: MSMI 0.500, +0.067 [−0.100, +0.233], W/T/L 5/7/3. Mutual 6.633, −0.300 [−0.867, +0.267]. Decision diff 11%.
  - resp_thompson: MSMI 0.433, +0.000 [−0.200, +0.200], W/T/L 5/5/5. Mutual 6.767, −0.167 [−0.667, +0.300]. Decision diff 11%.
- **FUNNEL CHECK:** pass (0 violations, 60 records).
- **VERDICT:** inconclusive (all intervals include 0).
- **WHY:** same sizing argument as 6a.
- **CONCERNS:** mutual acceptances differ from the v11 note by 1–2 events (note: 6.67 and 6.77), probably from an earlier `h4.py` version, so my numbers replace the note's. An accidental double run gave 60 identical records, including `resp_thompson`, so h4 is deterministic. Exploratory lead only: missing_feedback is lower than greedy for every variant (W/T/L ~3/0/12).
- **NEXT STEP:** report as a tie with sizing.

### Lab 3b: how scarce is the feasible graph?
- **HYPOTHESIS:** ranking development > cold_start > sparse. Share of available people with ≥1 option ≈ 10% (above the claimed 2–4%).
- **SETUP:** supplied greedy, daily graph logging after asks; development, sparse, cold_start; seeds 1101–1120; n = 20 per family. Files: `graph.jsonl`, `lab3b_graph_1101-1120.txt`.
- **RESULTS:**
  - development: 2.88 feasible pairs/day (seed means 1.58–4.32), 34% zero-pair days, 1.29 options per matchable person, 3% of available matchable (2–4%).
  - cold_start: 2.21 (1.07–4.27), 41% zero days, 1.28 options, 2% (1–3%).
  - sparse: 0.43 (0.22–0.77), 76% zero days, 1.07 options, ~0% (0–1%).
  - No paired comparison.
- **FUNNEL CHECK:** n/a (diagnostic); 60 records, one environment.
- **VERDICT:** ranking supported. 10% share not supported (3%; the earlier 2–4% claim holds).
- **WHY:** my prediction counted only forces that add options. Introductions remove both people for 8+ days, pairs never repeat, and people pause and exit. The graph is a trickle.
- **CONCERNS:** measured under the supplied asking rule; better asking could change it (that's H3).
- **NEXT STEP:** Lab 9.

### Claim check: numbers in the v11 note (`verify_claims.py`)
- **HYPOTHESIS:** the note's stated numbers are correct.
- **SETUP:** observable state and committed files only. C1 on seeds 1101–1120 (n = 20 per family); C2 on results 1001–1015; C3 on `graph.jsonl`; C4 on the organisers' baseline files (seed 101). File: `verify_claims.txt`.
- **RESULTS:**
  - **C1** declined hard field: development 33% (28–40%), cold_start 41% (34–49%), sparse 32% (25–37%).
  - **C2** greedy, development: 92.6 introductions per episode (60–129), coverage 0.378, mutual = 16× MSMI events, 0.87 MSMI per episode.
  - **C3** graph, development: available median 160 (112–177); all hard known 35–120; feasible pairs 0–36 per day (mean 2.88); options 1.00–2.60.
  - **C4** organisers' baselines: greedy 0.50, no_asks 0.33, random 0.25 MSMI/100; coverage 0.408 vs 0.174.
  - **C5** runtime: 3.0 s per in-process episode.
- **FUNNEL CHECK:** n/a.
- **VERDICT:** supported for C1, C2, C4. C3 ranges and C5 runtime need updating.
- **WHY:** the note's ranges came from two episodes; mine come from 20 seeds.
- **CONCERNS:** C4 is a single organiser episode per family (seed 101).
- **NEXT STEP:** update the note.

### Lab 7: what the model learned
- **HYPOTHESIS:** the note's claims hold: 1,049 labels, 14 features, relationship goal +0.53/−0.51 is the largest weight.
- **SETUP:** `h1.py` on seeds 2001–2008. File: `lab7_h1_weights.txt`.
- **RESULTS:** 1,049 labels, base rate 0.461, 14 features. Relationship goal +0.53/−0.51. **Largest weight: emotional_availability_agree −0.58.**
- **FUNNEL CHECK:** n/a.
- **VERDICT:** counts and the relationship-goal weights are supported. "Largest weight" is not supported.
- **WHY:** a single logistic fit; the note ranked the weights by "stability", which wasn't measured.
- **CONCERNS:** no uncertainty on the weights (one fit, no bootstrap). A negative weight for agreement on emotional availability is unexplained.
- **NEXT STEP:** fix the note's wording. Bootstrap the weights in Round 2.

### Analysis-only ceiling (`world_ceiling_ANALYSIS_ONLY.py`)
- **HYPOTHESIS:** 100–162 / 80–114 / 14–22 feasible pairs per world if all non-declined answers were known.
- **SETUP:** reads hidden truth (analysis only, never in a policy); development, cold_start, sparse; seeds 1001–1003; n = 3 worlds each. File: `ceiling_ANALYSIS_ONLY.txt`.
- **RESULTS:** development 162 / 100 / 114; cold_start 114 / 89 / 80; sparse 22 / 21 / 14.
- **FUNNEL CHECK:** n/a.
- **VERDICT:** supported (exact).
- **WHY:** greedy makes ~93 introductions per development episode against 100–162 possible pairs, so most possible pairs get used.
- **CONCERNS:** only 3 worlds; ignores timing (busy periods, exits). The script reads hidden data, so its numbers must never inform the policy directly.
- **NEXT STEP:** say "3 worlds, analysis-only" in the note.

### Shift reproduction (H1, H2, H4 on shift)
- **HYPOTHESIS:** the note's shift (5) rows reproduce: greedy 0.70/7.10, learned blossom 0.60/6.70, responsiveness blossom 0.60/6.50.
- **SETUP:** same policies as Lab 6; shift; seeds 1001–1015; n = 15, with the first 5 checked separately. Files: `shift_summ_1001-1005.txt`, `shift_summ_1001-1015.txt`.
- **RESULTS:**
  - **5 seeds (1001–1005):** greedy 0.700/7.100; learned_mwm 0.600/6.700; resp_mwm 0.600/**6.600**. learned_greedy MSMI −0.300 [−0.500, −0.100], W/T/L 0/2/3, decision diff 13%.
  - **15 seeds:** greedy MSMI 0.433, mutual 6.467. learned_greedy MSMI 0.667, **+0.233 [−0.033, +0.500]**, W/T/L 7/5/3, mutual −0.333 [−1.067, +0.300], decision diff 12%. learned_mwm +0.200 [−0.067, +0.467], decision diff 11%. resp_greedy +0.033 [−0.133, +0.233]. resp_mwm +0.033 [−0.200, +0.267]. resp_thompson +0.100 [−0.133, +0.333]. All decision diffs 11–12%.
- **FUNNEL CHECK:** pass (0 violations). Duplicates from repeated runs were all identical and were removed.
- **VERDICT:** h1 rows supported (exact, and the note's seeds are identified as 1001–1005). The h4 row is not supported (mutual 6.60 vs 6.50). On 15 seeds all effects are inconclusive.
- **WHY:** on 5 seeds MSMI looked significantly worse for learned_greedy; on 15 the sign flipped. Five seeds of a rare event aren't evidence.
- **CONCERNS:** the note's shift rows rest on 5 seeds.
- **NEXT STEP:** replace them with the 15-seed rows, or drop them.

### Lab 8: greedy vs blossom on the toy example
- **HYPOTHESIS:** blossom picks A–C + B–D (1.30); greedy picks A–D + B–C (0.95).
- **SETUP:** networkx `max_weight_matching` on 4 nodes. File: `lab8_toy.txt`.
- **RESULTS:** `{A–C, B–D}`, total 1.3.
- **FUNNEL CHECK:** n/a.
- **VERDICT:** supported.
- **WHY:** blossom optimises the whole pool; greedy takes the best edge first.
- **CONCERNS:** in the real graph each person has ~1.3 options, so situations like this are rare. That's why blossom ties with greedy in Lab 6.
- **NEXT STEP:** none.

### Lab 9: value-based asking (H3, primary hypothesis)
- **HYPOTHESIS:** `voi_greedy` unlocks more feasible pairs per day (days 0–20) than greedy's list-order asking; the interval excludes 0 and is positive; the gain is bigger in cold_start than in development. (My sparse prediction wasn't tested: sparse wasn't run.)
- **SETUP:** `greedy`, `voi_greedy`, `voi_mwm`, `voi_maxcard`; development and cold_start; seeds 1101–1120; n = 20 per family. Files: `results.jsonl` (`lab9_asking`), `lab9_summ_1101-1120.txt`.
- **RESULTS (voi_greedy vs greedy):**
  - development: feasible/day 5.183 vs 4.736, **+0.448 [+0.298, +0.598]**, W/T/L 19/0/1. Mutual 7.375 vs 6.900, +0.475 [−0.225, +1.200]. MSMI 0.575 vs 0.700, −0.125 [−0.325, +0.075]. Coverage +0.001. Decision diff 7% (0–16%).
  - cold_start: feasible/day 3.748 vs 3.255, **+0.493 [+0.310, +0.676]**, W/T/L 17/2/1. Mutual 5.300 vs 5.800, −0.500 [−1.175, +0.175], W/T/L 5/5/10. MSMI 0.325 vs 0.400, −0.075 [−0.250, +0.125]. Coverage +0.002. Decision diff 11% (0–18%).
  - voi_mwm: development +0.262 [+0.026, +0.488], cold_start +0.348 [+0.219, +0.481].
  - voi_maxcard: development +0.255 [−0.012, +0.488], cold_start +0.340 [+0.207, +0.476].
  - Downstream metrics flat for all variants.
- **FUNNEL CHECK:** pass (0 violations, 160 records, n_seeds = 20).
- **VERDICT:** "reveals feasible pairs sooner": supported in both families. "Bigger in cold_start": consistent (+15% vs +9% relative) but not tested head to head. "Turns them into more outcomes": not supported (mutual, MSMI and coverage flat; cold_start mutual leans negative).
- **WHY:** open question, under investigation. `feasible_per_day_d0_20` counts the pairs available each day, which may include pairs left unused, not only newly unlocked ones. More options for people who already had one wouldn't serve anyone new.
- **CONCERNS:** the metric definition (stock vs flow). Seeds 1101–1120 are now "seen" for H3, so Round 2 needs fresh seeds (1121+). No tuning was done.
- **NEXT STEP:** check whether value-based asks add new matchable people or only extra options for people who are already matchable. Then decide whether H3's primary metric should be newly matchable members per day.

---

## 3. Status
- Reproduced: all h1 numbers in the v11 note (development and shift). The h4 mutual numbers differ by 1–2 events and are replaced by mine.
- Not reproducible: the note's "28-episode pilot" (seeds unknown), replaced by Lab 9.
- Not run: Labs 1, 2, 4, 5, 10 (learning exercises; not needed as evidence).
