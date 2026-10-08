# Learning Labs (v2) — rebuild the proposal yourself

Goal: by Lab 10 you can explain every part of the v11 proposal from things you ran.
**Predict first, then run, then compare.** Write the prediction and what each outcome would mean.
Run from the repo root: `PYTHONHASHSEED=0 PYTHONPATH=. python3 <script> ...`
Follow METHOD.md on every run: paired seeds, intervals, W/T/L, funnel check, seed count.

Labs 0, 1, 2, 4, 5 and 8 start with:
```python
from kit import generate, Simulator, eligibility, baseline_asks, baseline_match, HARD, SOFT
```

---

## Day 1 (7 Oct): what the world looks like

### Lab 0 — Look at one person (15 min) → "observable state"
```python
sim = Simulator(generate(1101, 200, 'evaluation', 'development'))
s = sim.observe()
m = s['members'][0]
for k in HARD: print(k, m['fields'][k], m['field_status'][k])
```
- Predict: how many hard fields will be known?
- Notice: `None` + `not_asked` (askable) vs `None` + `declined` (never available).
- Check: why must the policy never treat `None` as "no"?

### Lab 1 — Can these two meet? (15 min) → Phase 1 feasibility
```python
a, b = s['members'][0], s['members'][1]
print(eligibility(a, b))
```
- Try 10 pairs; count `infeasible` / `needs_clarification` / `feasible`.
- Look at `who_to_meet` for both people: any gender can meet any gender if both accept.
- Check: why is a known failure stronger than missing data?

### Lab 2 — Ask a question (15 min) → clarification budget
```python
t = next(x for x in s['members'] if x['available'] and any(x['fields'][k] is None for k in HARD))
print(s['ask_budget_remaining'], [k for k in HARD if t['fields'][k] is None])
sim.resolve_asks([{'member_id': t['member_id'], 'field': 'constraints'}])
s = sim.observe(); t = next(x for x in s['members'] if x['member_id'] == t['member_id'])
print(s['ask_budget_remaining'], [k for k in HARD if t['fields'][k] is None])
```
- Check: with 12 units/day, how many people can you fully clarify per day?

### Lab 3 — How many choices exist? → the scarcity claim (the reviewers' top request)
**3a (explore, 2 min):** `python3 diagnose_graph.py development 1001-1002`
- Predict first: feasible pairs per day among ~150 available people? Share of days with none?

**3b (confirm, ~6 min):** 20 seeds each of development, sparse, cold_start:
```
python3 diagnose_graph.py development 1101-1120
python3 diagnose_graph.py sparse 1101-1120
python3 diagnose_graph.py cold_start 1101-1120
```
- Record the SUMMARY lines (mean and range across seeds) for the note.
- Check: does scarcity hold in all three families, or only in some?

### Lab 4 — The funnel (20 min) → Phase 2 funnel scorer
```python
sim = Simulator(generate(1101, 200, 'evaluation', 'development'))
for d in range(60):
    sim.resolve_asks(baseline_asks(sim.observe()))
    sim.advance(baseline_match(sim.observe()))
for d in range(40): sim.advance([])
print(sim.metrics())
```
- Expect roughly ~90 introductions → ~15 mutual Yes → ~11 dates → ~1 success.
- Funnel check (METHOD 15): assignments ≥ mutual ≥ dates ≥ MSMI. Must hold.

---

## Day 2 (7–8 Oct): luck, fairness, learning

### Lab 5 — Seeds and luck (20 min) → "20+ seeds"
Run Lab 4 for seeds 1101–1105, then seed 1101 twice.
- Same seed = identical result; different seeds = very different MSMI.

### Lab 6 — Reproduce the "tie" (~10 min compute) → paired comparisons
```
python3 h1.py                                   # run twice; outputs must match
python3 h1eval.py development 1001-1015
python3 h4.py development 1001-1015
python3 summ.py h1_learned greedy 1001-1015
python3 summ.py h4_resp_prior4 greedy 1001-1015
```
- Your numbers must match the research note exactly (same seeds, deterministic).
- Read the **decision diff** line: what share of introductions actually changed?
  Few changes = the new score barely reached a decision (METHOD 7).
- Check the record count, n_seeds = 15, and funnel violations = 0 before reading anything else.
- Optional (rule 20): `python3 h4.py development 1001-1015 2` and `... 8`. Does the conclusion change?

### Lab 7 — What did the model learn? (30 min) → learned weights
Open `h1.py`: features (`feats`), saved on the assignment day (`snap[...]`), labels from revealed responses.
- Which soft field matters most? Why save features on the assignment day? (leakage)

### Lab 8 — Greedy vs whole-pool matching (15 min) → blossom
```python
import networkx as nx
G = nx.Graph()
G.add_weighted_edges_from([('A','D',.90),('B','C',.05),('A','C',.65),('B','D',.65)])
print(nx.max_weight_matching(G))
```
- Greedy total by hand vs blossom total. Then: why might it barely help here? (Lab 3, Lab 6 decision diff)

---

## Day 3 (8 Oct): your own experiments

### Lab 9 — Does question order matter? (~15 min compute) → H3, the primary hypothesis
```
python3 exp.py development 1101-1120
python3 exp.py cold_start 1101-1120
python3 summ.py lab9_asking greedy 1101-1120
```
Policies: `greedy` (list-order asks), `voi_greedy` (value-based asks), `voi_mwm` (+ blossom),
`voi_maxcard` (+ max-cardinality matching).
- Primary metric: `feasible_per_day_d0_20` (pairs unlocked in the first 21 days), then mutual acceptances, coverage.
- Write your prediction and what would prove you wrong before running.

### Lab 10 — Thompson sampling on reply rates (if time; already in Lab 6 output)
`resp_thompson` in `h4.py` draws each person's reply rate once per day instead of using the average.
- For a fresh test: `python3 h4.py development 1101-1120`, then
  `python3 summ.py h4_resp_prior4 greedy 1101-1120` (the seed filter keeps fresh seeds apart from Lab 6's).
- Check: does it spread introductions more evenly, or change nothing (Lab 3 again)?


### Lab 11 — How much could asking ever add? (~12 min compute) → workshop 2, slides 9 and 15–16
The ceiling: what greedy would get if every non-declined hard answer were known (perfect clarification).
It reads hidden truth, so it is analysis only and never goes near the policy.
```
python3 exp.py development 1101-1120          # rerun: the new runner records funnel stages
python3 exp.py cold_start 1101-1120
python3 ceiling_policy_ANALYSIS_ONLY.py development 1101-1120
python3 ceiling_policy_ANALYSIS_ONLY.py cold_start 1101-1120
python3 gap_and_funnel.py development 1101-1120
python3 gap_and_funnel.py cold_start 1101-1120
```
- Predict first: does perfect clarification raise coverage and mutual acceptances, or only feasible pairs?
- (1) **Headroom:** ceiling minus greedy. If coverage and MSMI headroom are ~0, no asking strategy can move them.
- (2) **Gap closed:** what share of the headroom `voi_*` covers. Printed only where headroom is real.
- (3) **Funnel stages:** where introductions are lost (no response, declined, no date, date too late,
  no second meeting, success). The biggest leak is where the next lever is.
- The rerun duplicates your lab9 records with identical numbers plus a `stages` field; dedupe by key as before.


### Lab 11b — The ceiling in all six families (~12 min) → does the headline hold everywhere?
PowerShell: quote the policy list, or PowerShell splits it into two arguments and only greedy runs.
```powershell
foreach ($f in "sparse","shift","delayed","drift") {
  & $py hackathon_files\exp.py $f 1101-1120 "greedy,voi_greedy"
  & $py hackathon_files\ceiling_policy_ANALYSIS_ONLY.py $f 1101-1120
  & $py hackathon_files\gap_and_funnel.py $f 1101-1120 | Out-File -Encoding utf8 "lab11_$f.txt"
}
```
Expect 410 + 4 × 60 = 650 lines in results.jsonl. Watch `date_too_late` in delayed.

### Lab 7b — Are the learned weights real? (~1–2 min)
`python hackathon_files\h1_bootstrap.py 200`
- "distinguishable" needs BOTH an interval excluding 0 AND the same sign in both halves of the training seeds.
- The bootstrap resamples introductions, not single labels: both answers to one introduction share chemistry.

### Lab 7c — With enough rollouts, are the weights real? (~10 min compute) → the "too few labels" fix
`python hackathon_files\h1_scale.py 3001-3130 200`
- Seeds 3001–3130 are a NEW block. Random-feasible rollouts, time-correct features, revealed responses only (same rules as Lab 7).
- The bootstrap now resamples whole EPISODES. People never cross episodes, so this also handles one person appearing in many labels (7b could not).
- Learning curve at 8 / 16 / 32 / 64 / 130 rollouts: interval width and which weights pass.
- **Predict first:** which fields will pass at 130 rollouts? Does any unused field pass at 16 or 32?
- Labels are cached in `h1c_groups_3001_3130.pkl` (regenerable; don't commit it).

### Lab 7d — Does the learned model rank Yes better than greedy, on held-out worlds? (~2 min each)
`python hackathon_files\h1_holdout.py 3001-3130 3131-3150`
`python hackathon_files\h1_holdout.py 3001-3130 3131-3150 shift`
- AUC for "this person says Yes" on 20 held-out rollouts: greedy's count of equal fields vs a model trained on 8 rollouts vs on 130.
- Paired bootstrap over held-out episodes. Seeds must not overlap training (the script asserts this).
- This is a PROXY (workshop 2): better ranking reaches MSMI only through the ~12% of introductions a policy changes.

### Lab 12 — Does waiting help, and does the learned score reach outcomes? (~30 min compute) → H5 and H1
Script: `hackathon_files\lab12_waiting.py` (needs `h1c_groups_3001_3130.pkl` from Lab 7c in the repo root).
- Same asks (supplied list order), same learned score (the Lab 7c model), same seeds; only the reserve changes.
- `learned_tau0` = always match. `learned_tau0.10` / `learned_tau0.12` = the note's reserve WITH its two protections
  (no reserve for people never introduced; a person's only option is never postponed).
  `learned_tau0.12_pure` = the same reserve with NO protections (pure waiting). `greedy` = supplied baseline.
- Step 1: both families, seeds 1121–1140, all five policies. Step 2 (replication): seeds 1141–1160, three policies.
- **Predict first:** (1) How often will the protected reserve change a decision, given ~1.3 options per person?
  (2) Does pure waiting raise or lower MSMI, mutual acceptances and coverage? (3) Does the learned score beat greedy on MSMI?
- **Read it with METHOD.md:** check `n_seeds` and the decision-diff line first. A 0.2 MSMI difference is about four
  qualifying pairs over 20 episodes; a result counts only if it holds on BOTH seed blocks (1121–1140 and 1141–1160).

### Check C — How much history per person? (seconds, no new runs)
`python hackathon_files\per_person.py lab9_asking greedy development 1101-1120`
- If most served members get 1–2 introductions, per-person reply and Yes rates rest on 1–2 labels: that bounds H4.

---

## After the labs you should be able to explain
1. Why hard constraints are checked, never scored (Labs 0–1)
2. Why asking is a decision with a cost (Lab 2)
3. Whether scarcity is real and where (Lab 3b) and whether changes reach decisions (Lab 6)
4. Why the score is a funnel and is rare (Lab 4)
5. Why we need seeds, pairs and intervals (Labs 5–6)
6. What learning weights does, its limits, and how many rollouts make weights trustworthy (Labs 7–7d)
7. Whether question order helps — your own finding (Lab 9)
8. How much asking could ever add, and where introductions are lost (Lab 11)
9. Whether waiting helps when options are this scarce, and why a replication block matters (Lab 12)
