"""Lab 13 summary (ANALYSIS ONLY: the expected-outcome measure reads hidden simulator data).

For every recorded episode it computes the EXPECTED number of qualifying outcomes given the introductions the
policy actually made: the sum over its introductions of the true P(qualifying outcome), with chemistry and
all later random draws integrated out. This removes the outcome luck that makes actual MSMI so noisy, so
paired differences between policies on the same worlds become far more precise. It is a measurement tool
only. Actual MSMI is reported beside it, and the two should agree on average (sanity check printed).

Usage (repo root, PYTHONHASHSEED=0, PYTHONPATH=.):
  python hackathon_files/lab13_expected_ANALYSIS_ONLY.py   -> prints and writes lab_results/summaries/lab13_ceilings_1161-1180.txt
"""
import sys, json, random, statistics as st, collections
sys.path.insert(0, '.')
sys.path.insert(0, 'hackathon_files')
from kit import generate
from lab13_ceiling_ANALYSIS_ONLY import expected_msmi

EXP = 'lab13_ceilings'
OUT_TXT = 'lab_results/summaries/lab13_ceilings_1161-1180.txt'
ORDER = ['O_foresight', 'O_full', 'O_people', 'O_resp', 'O_profile', 'L_people', 'L_resp', 'L_resp_ts']


def boot(d, n=4000):
    m = sorted(st.mean(random.Random(i).choices(d, k=len(d))) for i in range(n))
    return m[int(.025 * n)], m[int(.975 * n) - 1]


def main():
    rows = [json.loads(l.lstrip('﻿')) for l in open('lab_results/results.jsonl', encoding='utf-8') if l.strip()]
    rows = [r for r in rows if r['experiment'] == EXP]
    worlds = {}
    for r in rows:
        key = (r['family'], r['seed'])
        if key not in worlds:
            worlds[key] = {m['member_id']: m for m in generate(r['seed'], 200, 'evaluation', r['family'])['members']}
        mem = worlds[key]
        r['exp_msmi_per_100'] = 100 * sum(expected_msmi(r['family'], d, mem[a], mem[b]) for a, b, d in r['pairs']) / r['n_arrived']
        r['no_response_share'] = r['stages']['no_response'] / max(r['assignments'], 1)
    by = collections.defaultdict(dict)
    for r in rows:
        by[(r['family'], r['seed'])][r['policy']] = r
    out = []
    p = out.append
    p(f'Lab 13 ceilings | experiment {EXP} | records {len(rows)} | funnel violations {sum(not r["funnel_ok"] for r in rows)}')
    p('Expected MSMI = sum over the introductions made of the true P(qualifying outcome) (analysis only).')
    p('\nSanity check, mean over all episodes: expected vs actual MSMI per 100')
    for pol in ['greedy'] + ORDER:
        rs = [r for r in rows if r['policy'] == pol]
        if rs:
            p('  %-12s expected %.3f | actual %.3f | n=%d' % (pol, st.mean(r['exp_msmi_per_100'] for r in rs), st.mean(r['msmi_per_100'] for r in rs), len(rs)))
    for fam in sorted({k[0] for k in by}):
        keys = sorted(k for k in by if k[0] == fam and 'greedy' in by[k])
        g = [by[k]['greedy'] for k in keys]
        p(f'\n== {fam}: {len(keys)} seeds; greedy expected MSMI {st.mean(x["exp_msmi_per_100"] for x in g):.3f}, '
          f'actual {st.mean(x["msmi_per_100"] for x in g):.3f}, no-response share {st.mean(x["no_response_share"] for x in g):.3f}')
        p('  %-12s %-24s %-24s %-22s %-22s %-20s %s' % ('policy', 'expected MSMI diff', 'actual MSMI diff', 'mutual/100 diff', 'no-response diff', 'coverage diff', 'differ'))
        full = None
        for pol in ORDER:
            ks = [k for k in keys if pol in by[k]]
            if len(ks) < 2:
                continue
            cells = []
            for m in ('exp_msmi_per_100', 'msmi_per_100', 'mutual_per_100', 'no_response_share', 'coverage'):
                d = [by[k][pol][m] - by[k]['greedy'][m] for k in ks]
                lo, hi = boot(d)
                cells.append('%+.3f [%+.3f, %+.3f]' % (st.mean(d), lo, hi))
                if m == 'exp_msmi_per_100' and pol == 'O_full':
                    full = st.mean(d)
            diff = st.mean(len({tuple(sorted(x[:2])) for x in by[k][pol]['pairs']} - {tuple(sorted(x[:2])) for x in by[k]['greedy']['pairs']}) / max(len(by[k][pol]['pairs']), 1) for k in ks)
            p('  %-12s %-24s %-24s %-22s %-22s %-20s %.0f%%' % (pol, *cells, 100 * diff))
        if full:
            p('  share of the O_full headroom (expected MSMI) captured by each learner:')
            for pol in ('L_resp', 'L_resp_ts', 'L_people'):
                ks = [k for k in keys if pol in by[k]]
                if ks:
                    gain = st.mean(by[k][pol]['exp_msmi_per_100'] - by[k]['greedy']['exp_msmi_per_100'] for k in ks)
                    p('    %-10s %+.0f%%' % (pol, 100 * gain / full))
    text = '\n'.join(out)
    print(text)
    with open(OUT_TXT, 'w', encoding='utf-8') as f:
        f.write(text + '\n')


if __name__ == '__main__':
    main()
