
"""Read-only reporting pipeline for Lab 12.

Reads existing JSONL results and creates separate reports.
Does not run simulations or modify the source results.
"""

import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

SOURCE = Path("lab_results/results.jsonl")
OUT = Path("lab_results/reporting")
EXPERIMENT = "lab12_waiting"

BOOTSTRAPS = 5000
RNG = random.Random(20261014)

METRICS = [
    "n_arrived",
    "assignments",
    "mutual_acceptances",
    "dates",
    "msmi",
    "msmi_per_100",
    "mutual_per_100",
    "coverage",
    "unserved",
    "ask_cost",
    "missing_feedback",
    "wait_median_days",
    "wait_mean_days",
    "feasible_per_day_d0_20",
]

BLOCKS = {
    "block1": set(range(1121, 1141)),
    "block2": set(range(1141, 1161)),
}
def get_seed_block(seed):
    if seed in BLOCKS["block1"]:
        return "block1"
    if seed in BLOCKS["block2"]:
        return "block2"
    return "outside_assigned_blocks"




def mean(values):
    return sum(values) / len(values) if values else None


def bootstrap_ci(values):
    """95% percentile interval, resampling independent seeds."""
    if not values:
        return None, None

    if len(values) == 1:
        return values[0], values[0]

    estimates = []

    for _ in range(BOOTSTRAPS):
        sample = [RNG.choice(values) for _ in values]
        estimates.append(mean(sample))

    estimates.sort()

    low = estimates[int(0.025 * BOOTSTRAPS)]
    high = estimates[min(BOOTSTRAPS - 1, int(0.975 * BOOTSTRAPS))]

    return low, high


def write_csv(path, rows):
    rows = list(rows)

    if not rows:
        path.write_text("No eligible rows\n", encoding="utf-8")
        return

    fields = list(dict.fromkeys(
        key for row in rows for key in row
    ))

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def pair_key(pair):
    """Represent an unordered pair consistently."""
    if not isinstance(pair, (list, tuple)) or len(pair) < 2:
        return None

    return tuple(sorted((str(pair[0]), str(pair[1]))))

def load_results():
    if not SOURCE.exists():
        raise FileNotFoundError(f"Results file not found: {SOURCE}")

    all_rows = []

    with SOURCE.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                all_rows.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSON on line {line_number}: {error}"
                ) from error

    rows = [
        row for row in all_rows
        if row.get("experiment") == EXPERIMENT
    ]

    if not rows:
        raise ValueError(
            f"No records found for experiment {EXPERIMENT!r}"
        )

    return all_rows, rows


def check_integrity(all_rows, rows):
    report = [
        f"Source file: {SOURCE}",
        f"Experiment filter: {EXPERIMENT}",
        f"All source records: {len(all_rows)}",
        f"Filtered records: {len(rows)}",
        "",
    ]

    # Check uniqueness using the full experiment key.
    keys = [
        (
            row.get("experiment"),
            row.get("seed"),
            row.get("family"),
            row.get("policy"),
        )
        for row in rows
    ]

    counts = Counter(keys)
    duplicates = [
        (key, count)
        for key, count in counts.items()
        if count > 1
    ]

    report.append(
        f"Duplicate full keys: {len(duplicates)}"
    )

    for key, count in duplicates:
        report.append(f"  DUPLICATE {key}: {count} records")

    # Check whether core metrics exist.
    report.extend(["", "Metric availability:"])

    for metric in METRICS:
        present = sum(
            row.get(metric) is not None
            for row in rows
        )
        report.append(
            f"  {metric}: {present}/{len(rows)}"
        )

    # Check the outcome funnel.
    violations = []

    for row in rows:
        a = row.get("assignments")
        m = row.get("mutual_acceptances")
        d = row.get("dates")
        s = row.get("msmi")

        values = (a, m, d, s)

        if not all(
            isinstance(value, (int, float))
            for value in values
        ):
            violations.append(
                (row.get("seed"), row.get("family"),
                 row.get("policy"), "missing/non-numeric metric")
            )
        elif not (a >= m >= d >= s >= 0):
            violations.append(
                (row.get("seed"), row.get("family"),
                 row.get("policy"), a, m, d, s)
            )

    report.extend([
        "",
        f"Funnel violations: {len(violations)}",
    ])

    for violation in violations:
        report.append(f"  FUNNEL ISSUE: {violation}")

    # Summarize which policies are available in each assigned block.
    report.extend(["", "Seed-block coverage:"])

    for block_name, seeds in BLOCKS.items():
        block_rows = [
            row for row in rows
            if row.get("seed") in seeds
        ]

        block_policies = sorted({
            row.get("policy") for row in block_rows
        })

        block_families = sorted({
            row.get("family") for row in block_rows
        })

        report.append(
            f"{block_name}: {len(block_rows)} rows; "
            f"{len({row.get('seed') for row in block_rows})} seeds"
        )
        report.append(f"  Policies: {block_policies}")
        report.append(f"  Families: {block_families}")

    OUT.mkdir(parents=True, exist_ok=True)

    (OUT / "integrity_report.txt").write_text(
        "\n".join(report) + "\n",
        encoding="utf-8",
    )

def summarize_metrics(rows):
    summaries = []

    groups = defaultdict(list)

    for row in rows:
        seed = row.get("seed")

        if seed is None:
            continue

        groups[
            (row.get("family"), row.get("policy"))
        ].append(row)

    for (family, policy), group_rows in sorted(groups.items()):
        summary = {
            "family": family,
            "policy": policy,
            "seed_count": len({
                row.get("seed") for row in group_rows
            }),
        }

        for metric in METRICS:
            values = [
                row[metric]
                for row in group_rows
                if isinstance(row.get(metric), (int, float))
            ]

            low, high = bootstrap_ci(values)

            summary[f"{metric}_mean"] = mean(values)
            summary[f"{metric}_ci95_low"] = low
            summary[f"{metric}_ci95_high"] = high

        summaries.append(summary)

    return summaries


def summarize_pairwise(rows):
    """Compare policies with greedy on matching seed/family pairs."""
    grouped = defaultdict(dict)

    for row in rows:
        key = (row.get("family"), row.get("seed"))
        grouped[key][row.get("policy")] = row

    outcomes = [
        "mutual_acceptances",
        "msmi",
        "coverage",
    ]

    comparisons = []

    for (family, seed), policies in sorted(grouped.items()):
        baseline = policies.get("greedy")

        if baseline is None:
            continue

        for policy, candidate in sorted(policies.items()):
            if policy == "greedy":
                continue

            for metric in outcomes:
                base_value = baseline.get(metric)
                candidate_value = candidate.get(metric)

                if not isinstance(base_value, (int, float)):
                    continue

                if not isinstance(candidate_value, (int, float)):
                    continue

                if candidate_value > base_value:
                    result = "win"
                elif candidate_value < base_value:
                    result = "loss"
                else:
                    result = "tie"

                comparisons.append({
                    "family": family,
                    "seed": seed,
                    "seed_block": get_seed_block(seed),
                    "baseline": "greedy",
                    "policy": policy,
                    "metric": metric,
                    "greedy_value": base_value,
                    "policy_value": candidate_value,
                    "difference": candidate_value - base_value,
                    "result": result,
                })

    return comparisons


def summarize_pair_differences(rows):
    """Compare unordered introduced pairs with greedy on matched runs."""
    grouped = defaultdict(dict)

    for row in rows:
        grouped[
            (row.get("family"), row.get("seed"))
        ][row.get("policy")] = row

    summaries = []

    for (family, seed), policies in sorted(grouped.items()):
        baseline = policies.get("greedy")

        if baseline is None:
            continue

        base_pairs = {
            pair_key(pair)
            for pair in baseline.get("pairs", [])
        }
        base_pairs.discard(None)

        for policy, candidate in sorted(policies.items()):
            if policy == "greedy":
                continue

            candidate_pairs = {
                pair_key(pair)
                for pair in candidate.get("pairs", [])
            }
            candidate_pairs.discard(None)

            union = base_pairs | candidate_pairs
            changed = base_pairs ^ candidate_pairs

            summaries.append({
                "family": family,
                "seed": seed,
                "baseline": "greedy",
                "policy": policy,
                "greedy_pair_count": len(base_pairs),
                "policy_pair_count": len(candidate_pairs),
                "different_pair_count": len(changed),
                "union_pair_count": len(union),
                "share_different_pairs": (
                    len(changed) / len(union) if union else 0.0
                ),
            })

    return summaries


def summarize_paired_effects(comparisons):
    """Summarize paired differences by seed block with 95% bootstrap CIs."""
    groups = defaultdict(list)

    for row in comparisons:
        key = (
            row["family"],
            row["seed_block"],
            row["policy"],
            row["metric"],
        )
        groups[key].append(row)

    summaries = []

    for (family, seed_block, policy, metric), group_rows in sorted(groups.items()):
        differences = [
            row["difference"] for row in group_rows
        ]

        low, high = bootstrap_ci(differences)

        counts = Counter(
            row["result"] for row in group_rows
        )

        summaries.append({
            "family": family,
            "seed_block": seed_block,
            "baseline": "greedy",
            "policy": policy,
            "metric": metric,
            "matched_seeds": len(differences),
            "mean_paired_difference": mean(differences),
            "ci95_low": low,
            "ci95_high": high,
            "wins": counts["win"],
            "ties": counts["tie"],
            "losses": counts["loss"],
        })

    return summaries




def main():
    all_rows, rows = load_results()

    # Save the integrity checks.
    check_integrity(all_rows, rows)

    # Create per-family and per-policy summaries.
    metric_summaries = summarize_metrics(rows)
    write_csv(
        OUT / "metric_summary.csv",
        metric_summaries,
    )

    # Compare each policy with greedy on matching seeds.
    comparisons = summarize_pairwise(rows)
    write_csv(
        OUT / "paired_comparisons.csv",
        comparisons,
    )

    paired_effects = summarize_paired_effects(comparisons)
    write_csv(
        OUT / "paired_effects.csv",
        paired_effects,
    )

    # Measure how often the introduced member pairs differ.
    pair_summaries = summarize_pair_differences(rows)
    write_csv(
        OUT / "pair_differences.csv",
        pair_summaries,
    )

    # Record the exact source and scope of this report.
    metadata = [
        "Lab 12 read-only reporting pipeline",
        f"Source: {SOURCE}",
        f"Experiment: {EXPERIMENT}",
        f"Records analyzed: {len(rows)}",
        f"Bootstrap resamples: {BOOTSTRAPS}",
        "Confidence intervals: 95% percentile bootstrap intervals",
        "Bootstrap sampling unit: recorded seed-level run within each family and policy",
        "Pair differences compare unordered member pairs; introduction day is ignored",
        "Expected MSMI, per-call runtime, and reliability curves are not "
        "calculated unless those data are available in the source",
        "Only families and policies present in the selected experiment are analyzed",
        "The source JSONL file is read only",
    ]

    (OUT / "report_metadata.txt").write_text(
        "\n".join(metadata) + "\n",
        encoding="utf-8",
    )

    print("Reporting complete.")
    print(f"Source records: {len(all_rows)}")
    print(f"Lab 12 records analyzed: {len(rows)}")
    print(f"Reports saved in: {OUT.resolve()}")
    print("Created:")
    print("  integrity_report.txt")
    print("  metric_summary.csv")
    print("  paired_comparisons.csv")
    print("  paired_effects.csv")
    print("  pair_differences.csv")
    print("  report_metadata.txt")


if __name__ == "__main__":
    main()
