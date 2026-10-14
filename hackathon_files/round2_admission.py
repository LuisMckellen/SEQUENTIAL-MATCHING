"""Round 2 admission runs (Section 6 rule): L1 blossom matching and L2 value-based asks vs greedy.
Usage: PYTHONHASHSEED=0 PYTHONPATH=. python hackathon_files/round2_admission.py <seeds> [workers] [policies]
Runs every family; writes lab_results/results.jsonl (experiment 'r2_admission'); observable state only."""
import sys
from multiprocessing import Pool
sys.path.insert(0, 'hackathon_files')
sys.path.insert(0, '.')
from kit import baseline_asks, baseline_match
from runner import run_episode, write, parse_seeds
from exp import blossom, voi_asks

FAMILIES = ['development', 'sparse', 'cold_start', 'delayed', 'shift', 'drift']
POLICIES = {
    'greedy': (baseline_asks, baseline_match),
    'L1_blossom': (baseline_asks, blossom),          # same asks and scores as greedy, whole-pool blossom
    'L2_voi_asks': (voi_asks, baseline_match),       # value-based hard asks, greedy matching
}


def job(args):
    name, family, seed = args
    ask, match = POLICIES[name]
    r = run_episode(ask, match, seed, family)
    r.pop('pairs', None); r.pop('stages', None)
    return name, r


if __name__ == '__main__':
    seeds = parse_seeds(sys.argv[1])
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    names = sys.argv[3].split(',') if len(sys.argv) > 3 else list(POLICIES)
    jobs = [(p, f, s) for f in FAMILIES for s in seeds for p in names]
    with Pool(workers) as pool:
        for name, r in pool.imap_unordered(job, jobs):
            write('lab_results/results.jsonl', 'r2_admission', name, r)
            print(name, r['family'], r['seed'], r['mutual_acceptances'], r['msmi'], flush=True)
