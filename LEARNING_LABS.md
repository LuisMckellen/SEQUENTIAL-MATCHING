# Learning Labs — rebuild the proposal yourself

Goal: by Lab 9 you can explain every part of the v11 proposal from things you ran.
Rules for every lab: **predict first, then run, then compare.** Write your prediction down.
Run everything from the repo root with: `PYTHONHASHSEED=0 PYTHONPATH=. python3 <file>.py`

Each lab starts with this line:
```python
from kit import generate, Simulator, eligibility, baseline_asks, baseline_match, HARD, SOFT
```

---

## Day 1 (6–7 Oct): what the world looks like

### Lab 0 — Look at one person  (15 min) → proposal: "observable state"
```python
sim = Simulator(generate(1101, 200, 'evaluation', 'development'))
s = sim.observe()
m = s['members'][0]
for k in HARD: print(k, m['fields'][k], m['field_status'][k])
```
- Predict: how many hard fields will be known?
- Notice: `None` + `not_asked` (you could ask) vs `None` + `declined` (never available).
- Check yourself: why must the policy never treat `None` as "no"?

### Lab 1 — Can these two meet?  (15 min) → proposal: Phase 1 feasibility
```python
a, b = s['members'][0], s['members'][1]
print(eligibility(a, b))
```
- Try 10 random pairs. Count `infeasible`, `needs_clarification`, `feasible`.
- Check yourself: why is a known failure stronger than missing data?

### Lab 2 — Ask a question  (15 min) → proposal: clarification budget
```python
t = next(x for x in s['members'] if x['available'] and any(x['fields'][k] is None for k in HARD))
print(s['ask_budget_remaining'], [k for k in HARD if t['fields'][k] is None])
sim.resolve_asks([{'member_id': t['member_id'], 'field': 'constraints'}])
s = sim.observe(); t = next(x for x in s['members'] if x['member_id'] == t['member_id'])
print(s['ask_budget_remaining'], [k for k in HARD if t['fields'][k] is None])
```
- Notice: 12 → 9 units, missing fields filled (unless declined).
- Check yourself: with 12 units/day, how many people can you fully clarify per day?

### Lab 3 — How many choices exist?  (15 min) → proposal: the scarcity finding
Run `experiments/diagnose_graph.py development`, then `sparse`.
- Predict first: how many feasible pairs per day among ~150 available people?
- Check yourself: if each person has 1–2 options, why can't clever ranking help much?

### Lab 4 — The funnel  (20 min) → proposal: Phase 2 funnel scorer
```python
sim = Simulator(generate(1101, 200, 'evaluation', 'development'))
for d in range(60):
    sim.resolve_asks(baseline_asks(sim.observe()))
    sim.advance(baseline_match(sim.observe()))
for d in range(40): sim.advance([])
print(sim.metrics())
```
- Expect roughly: ~90 introductions → ~15 mutual Yes → ~11 dates → ~1 success.
- Check yourself: which stage loses the most? Why is MSMI hard to compare between policies?

---

## Day 2 (7 Oct): luck, fairness and learning

### Lab 5 — Seeds and luck  (20 min) → proposal: "20+ seeds"
Run Lab 4 for seeds 1101–1105. Then run seed 1101 twice.
- Notice: same seed = identical result; different seeds = very different MSMI.
- Check yourself: why does one run prove nothing?

### Lab 6 — A fair comparison  (30 min) → proposal: paired comparisons + intervals
Reproduce: `h1.py`, then `h1eval.py development 1001,...,1015`, then `summ.py`.
- Learn: paired difference = same world, two policies; bootstrap interval = range the true difference probably sits in.
- Check yourself: the interval for learned-vs-greedy includes 0. What does that mean?

### Lab 7 — What did the model learn?  (30 min) → proposal: learned weights (your v10.1 idea)
Open `h1.py`. Find: features (line 11), when they're saved (line 29), labels (line 32).
- Look at the printed weights. Which soft field matters most?
- Check yourself: why save features on the assignment day, not at the end? (data leakage)

### Lab 8 — Greedy vs whole-pool matching  (15 min) → proposal: Phase 3 blossom matching
```python
import networkx as nx
G = nx.Graph()
G.add_weighted_edges_from([('A','D',.90),('B','C',.05),('A','C',.65),('B','D',.65)])
print(nx.max_weight_matching(G))
```
- Do greedy by hand: take the best edge, then the best remaining one. Total?
- Compare with blossom's total. Then: why didn't this help in Lab 6? (hint: Lab 3)

---

## Day 3 (8 Oct): your own experiment

### Lab 9 — Does question order matter?  → proposal: H3, the main open question
Compare `greedy` vs `voi_greedy` in `experiments/exp.py`, seeds 1101–1120, development + cold_start.
Before running, write: hypothesis, metric, what result would prove you wrong.
Report with `summ.py`-style paired intervals. Either answer is a real result.

---

## After Lab 9 you should be able to explain
1. Why hard constraints are checked, never scored (Labs 0–1)
2. Why asking questions is a decision with a cost (Lab 2)
3. Why scarcity makes ranking tie (Labs 3, 8)
4. Why the score is a funnel and is rare (Lab 4)
5. Why we need seeds, pairs and intervals (Labs 5–6)
6. What learning weights does, and its limits (Lab 7)
7. Whether question order helps — your own finding (Lab 9)
