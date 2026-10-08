"""ANALYSIS ONLY - slide 9 "theoretical ceiling". Reads hidden truth. NEVER import into a policy.
Perfect clarification: every day, every arrived member's non-declined hard answers are revealed
for free (as if the ask budget were unlimited), then the supplied greedy matching runs.
Declined answers stay unknown, exactly as in the real simulator.
Usage: PYTHONHASHSEED=0 PYTHONPATH=. python ceiling_policy_ANALYSIS_ONLY.py <family> <seeds>
Writes results.jsonl, experiment='ceiling_perfect_asks', policy='perfect_asks_greedy'."""
import sys, copy
sys.path.insert(0, '.')
from kit import baseline_match, HARD
from runner import run_episode, write, parse_seeds


def reveal_all(sim):
    for m in sim.members.values():
        if m['arrived_day'] > sim.day:
            continue
        for k in HARD:
            if m['field_status'][k] != 'declined' and m['fields'][k] is None:
                m['fields'][k] = copy.deepcopy(m['truth'][k])
                m['field_status'][k] = 'observed'
                m['field_observed_day'][k] = sim.day


if __name__ == '__main__':
    family, seeds = sys.argv[1], parse_seeds(sys.argv[2])
    for seed in seeds:
        rec = run_episode(lambda s: [], baseline_match, seed, family, pre_day=reveal_all)
        write('lab_results/results.jsonl', 'ceiling_perfect_asks', 'perfect_asks_greedy', rec)
        print('done seed', seed, flush=True)
