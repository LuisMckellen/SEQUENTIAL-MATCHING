"""Paired comparison against a baseline policy, per family (METHOD 1-4, 7, 15, 18-19).
Usage: python summ.py <experiment> [baseline=greedy] [seeds, e.g. 1101-1120]"""
import sys, json, random, collections, statistics as st
from runner import parse_seeds


def boot(d, n=4000):
    means = sorted(st.mean(random.Random(i).choices(d, k=len(d))) for i in range(n))
    return means[int(.025 * n)], means[int(.975 * n) - 1]


if __name__ == '__main__':
    exp_name = sys.argv[1]; base = sys.argv[2] if len(sys.argv) > 2 else 'greedy'
    rows = [json.loads(l) for l in open('lab_results/results.jsonl')]
    rows = [r for r in rows if r['experiment'] == exp_name]          # rule 25: filter, never assume
    if len(sys.argv) > 3:                                             # keep seen and fresh seeds apart
        keep = set(parse_seeds(sys.argv[3])); rows = [r for r in rows if r['seed'] in keep]
    by = collections.defaultdict(dict)
    for r in rows:
        by[(r['family'], r['seed'])][r['policy']] = r                 # rule 18: pair by key
    bad = [r for r in rows if not r['funnel_ok']]
    print('experiment', exp_name, '| records', len(rows), '| funnel violations', len(bad))
    for fam in sorted({k[0] for k in by}):
        keys = sorted(k for k in by if k[0] == fam)
        pols = sorted({p for k in keys for p in by[k]} - {base})
        print('\n== family', fam)
        for p in pols:
            seeds = [k for k in keys if p in by[k] and base in by[k]]
            print(' %s vs %s: n_seeds = %d' % (p, base, len(seeds)))     # rule 19: check the count
            if len(seeds) < 2:
                continue
            for metric in ['mutual_per_100', 'msmi_per_100', 'coverage', 'feasible_per_day_d0_20', 'unserved', 'missing_feedback']:
                d = [by[k][p][metric] - by[k][base][metric] for k in seeds]
                lo, hi = boot(d)
                w = sum(x > 0 for x in d); t = sum(x == 0 for x in d)
                print('   %-24s mean %.3f vs %.3f | diff %+.3f [%+.3f, %+.3f] | W/T/L %d/%d/%d' % (
                    metric, st.mean(by[k][p][metric] for k in seeds), st.mean(by[k][base][metric] for k in seeds),
                    st.mean(d), lo, hi, w, t, len(d) - w - t))
            # rule 7: did the change reach a decision? share of p's introductions not made by the baseline
            diff = []
            for k in seeds:
                a = {tuple(sorted(x[:2])) for x in by[k][p]['pairs']}
                b = {tuple(sorted(x[:2])) for x in by[k][base]['pairs']}
                diff.append(len(a - b) / max(len(a), 1))
            print('   decision diff: %.0f%% of introductions differ from %s (range %.0f-%.0f%%)' % (
                100 * st.mean(diff), base, 100 * min(diff), 100 * max(diff)))
