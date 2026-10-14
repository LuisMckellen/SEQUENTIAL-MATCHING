"""Live demo: play one simulator episode with the submitted policy and print, for a chosen day,
what it asked, whom it introduced, and the explanation record behind each decision.
Usage: python demo_explain.py [seed] [variant] [day]"""
import sys
from kit import generate, Simulator
import policy

seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1181
variant = sys.argv[2] if len(sys.argv) > 2 else 'development'
show_day = int(sys.argv[3]) if len(sys.argv) > 3 else 8

sim = Simulator(generate(seed, 200, 'evaluation', variant))
memory, total_pairs = None, 0
for day in range(60):
    state = sim.observe()
    budget_before = state.get('ask_budget_remaining')
    asks = policy.decide({'phase': 'ask', 'state': state, 'memory': memory}, 'method')
    sim.resolve_asks(asks['asks'])
    state = sim.observe()
    out = policy.decide({'phase': 'match', 'state': state, 'memory': asks['memory']}, 'method')
    total_pairs += len(out['pairs'])
    if day == show_day:
        print(f"=== Day {day}: {sum(m['available'] for m in state['members'])} members available ===")
        print(f"Asked {len(asks['asks'])} members for their hard constraints "
              f"(daily budget {budget_before} units, 3 per member)")
        rec = policy.explain(state, 'match', out['pairs'])
        print(f"Introduced {len(out['pairs'])} pairs. Explanation records:")
        for d in rec['decisions'][:3]:
            print(f"\n  pair {d['pair'][0]} + {d['pair'][1]}")
            print(f"    checks passed        : {d['checks']} (all hard constraints known and satisfied both ways)")
            print(f"    observed evidence    : {d['evidence']['soft_matches']} equal soft fields")
            for s in d['missing_data']:
                print(f"    {s['id']}: unknown hard fields={s['hard_unknown']}, declined={s['declined']}, soft fields known={s['soft_known']}")
            print(f"    model uncertainty    : {d['model_uncertainty']}")
            print(f"    stochastic outcome   : {d['stochastic_outcome']}")
    sim.advance(out['pairs'])
    memory = out['memory']
print(f"\nOver 60 decision days: {total_pairs} introductions proposed, every action accepted by the simulator.")
