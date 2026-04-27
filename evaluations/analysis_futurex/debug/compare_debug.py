#!/usr/bin/env python3
"""Compare L3+L4 debug experiment results and generate failure analysis report."""

import json
import re
import ast
import os
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR / ".." / ".." / ".."

EXPERIMENTS = {
    "D0_no_search": SCRIPT_DIR / "no_search_l3l4",
    "D1_baseline": SCRIPT_DIR / "baseline_l3l4",
    "D2_evo": SCRIPT_DIR / "evo_l3l4",
    "D3_no_hedge": SCRIPT_DIR / "no_hedge_l3l4",
}


def load_gt():
    """Load ground truth from the local parquet (updated from HuggingFace)."""
    import pandas as pd
    df = pd.read_parquet(REPO_ROOT / "data" / "futurex" / "futurex_past.parquet")
    gt = {}
    for _, row in df.iterrows():
        gt[row["id"]] = {
            "level": int(row["level"]),
            "title": row.get("title", ""),
            "ground_truth": row["ground_truth"],
        }
    return gt


def has_chinese(text):
    return bool(re.search(r"[\u4e00-\u9fff]", str(text)))


def parse_gt(gt_str):
    try:
        return ast.literal_eval(gt_str)
    except Exception:
        return gt_str


def extract_boxed(text):
    """Extract the last \\boxed{...} answer from text."""
    matches = re.findall(r"\\boxed\{([^}]*)\}", str(text))
    return matches[-1].strip() if matches else None


def is_hedged(pred):
    hedges = [
        "unable to", "insufficient data", "cannot predict", "cannot reliably",
        "it is unclear", "due to the dynamic nature", "based on available data, it is not",
        "without access to", "i cannot", "not possible to determine",
    ]
    return any(h in str(pred).lower() for h in hedges)


def classify_failure(gt_parsed, pred_str, title, prompt_has_chinese):
    """Classify a failed prediction into a failure mode."""
    if is_hedged(pred_str):
        return "hedged"

    is_numeric = (isinstance(gt_parsed, list) and len(gt_parsed) == 1
                  and isinstance(gt_parsed[0], (int, float)))
    if is_numeric:
        try:
            pred_num = float(str(pred_str).strip().replace(",", "").split("\n")[0])
            gt_num = float(gt_parsed[0])
            pct_err = abs(pred_num - gt_num) / max(abs(gt_num), 0.01) * 100
            if pct_err < 5:
                return "numeric_near_miss"
            return "numeric_wrong"
        except (ValueError, IndexError):
            return "numeric_wrong"

    if prompt_has_chinese or has_chinese(str(gt_parsed)):
        return "chinese_platform"

    return "wrong_data"


def score_prediction(gt_parsed, pred_str):
    """Simple scorer: check if prediction matches GT."""
    if gt_parsed is None or pred_str is None:
        return False

    pred_lower = str(pred_str).lower().strip()

    if isinstance(gt_parsed, list):
        if len(gt_parsed) == 1:
            gt_val = gt_parsed[0]
            # Numeric
            try:
                pred_num = float(pred_lower.replace(",", ""))
                gt_num = float(gt_val)
                return abs(pred_num - gt_num) < 0.02 * max(abs(gt_num), 0.01)
            except (ValueError, TypeError):
                pass
            # String match
            return str(gt_val).lower().strip() in pred_lower
        else:
            # All items must appear in prediction
            return all(str(g).lower().strip() in pred_lower for g in gt_parsed)

    return str(gt_parsed).lower().strip() in pred_lower


def load_experiment(exp_dir):
    """Load results.jsonl from an experiment directory."""
    results_file = exp_dir / "results.jsonl"
    if not results_file.exists():
        return []
    results = []
    with open(results_file) as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line))
    return results


def analyze_experiment(name, results, gt_map):
    """Analyze one experiment's results against ground truth."""
    stats = {
        "name": name,
        "total": 0,
        "correct": 0,
        "l3_total": 0, "l3_correct": 0,
        "l4_total": 0, "l4_correct": 0,
        "cn_total": 0, "cn_correct": 0,
        "ncn_total": 0, "ncn_correct": 0,
        "failure_modes": defaultdict(int),
        "details": [],
    }

    # Build instance_id -> platform_id mapping
    # instance_id format: futurex_past_NNNN_YYYYMMDD
    # We need to match against gt_map which uses platform IDs
    # The data loader creates instance_ids from the sorted dataset index

    import pandas as pd
    df = pd.read_parquet(REPO_ROOT / "data" / "futurex" / "futurex_past.parquet")
    df_sorted = df.sort_values("end_time").reset_index(drop=True)

    idx_to_platform_id = {}
    for i, row in df_sorted.iterrows():
        idx_to_platform_id[i] = row["id"]

    for r in results:
        iid = r.get("instance_id", "")
        m = re.match(r"futurex_past_(\d+)_", iid)
        if not m:
            continue
        idx = int(m.group(1))
        platform_id = idx_to_platform_id.get(idx)
        if not platform_id or platform_id not in gt_map:
            continue

        gt_info = gt_map[platform_id]
        level = gt_info["level"]
        if level not in (3, 4):
            continue

        gt_parsed = parse_gt(gt_info["ground_truth"])
        title = gt_info.get("title", "")
        is_cn = has_chinese(str(gt_parsed)) or has_chinese(title)

        # Get prediction from trajectory or detail
        pred = r.get("detail", "")
        if "prediction=" in str(pred):
            pred = str(pred).split("prediction=")[-1]

        correct = r.get("success", False) or r.get("score", 0) > 0

        stats["total"] += 1
        if correct:
            stats["correct"] += 1

        if level == 3:
            stats["l3_total"] += 1
            if correct:
                stats["l3_correct"] += 1
        else:
            stats["l4_total"] += 1
            if correct:
                stats["l4_correct"] += 1

        if is_cn:
            stats["cn_total"] += 1
            if correct:
                stats["cn_correct"] += 1
        else:
            stats["ncn_total"] += 1
            if correct:
                stats["ncn_correct"] += 1

        if not correct:
            mode = classify_failure(gt_parsed, pred, title, is_cn)
            stats["failure_modes"][mode] += 1

        stats["details"].append({
            "instance_id": iid,
            "level": level,
            "chinese": is_cn,
            "correct": correct,
            "gt": str(gt_parsed)[:60],
            "pred": str(pred)[:60],
        })

    return stats


def pct(num, denom):
    return f"{100 * num / max(denom, 1):.1f}%"


def generate_report(all_stats):
    """Generate markdown comparison report."""
    lines = ["# L3+L4 Debug Experiment Report\n"]

    # Summary table
    lines.append("## Summary\n")
    lines.append("| Experiment | Total | Correct | Rate | L3 | L4 | Chinese | Non-CN |")
    lines.append("|------------|------:|--------:|-----:|---:|---:|--------:|-------:|")
    for s in all_stats:
        lines.append(
            f"| {s['name']} | {s['total']} | {s['correct']} | "
            f"{pct(s['correct'], s['total'])} | "
            f"{s['l3_correct']}/{s['l3_total']} ({pct(s['l3_correct'], s['l3_total'])}) | "
            f"{s['l4_correct']}/{s['l4_total']} ({pct(s['l4_correct'], s['l4_total'])}) | "
            f"{s['cn_correct']}/{s['cn_total']} ({pct(s['cn_correct'], s['cn_total'])}) | "
            f"{s['ncn_correct']}/{s['ncn_total']} ({pct(s['ncn_correct'], s['ncn_total'])}) |"
        )

    # Failure mode breakdown
    lines.append("\n## Failure Mode Breakdown\n")
    all_modes = set()
    for s in all_stats:
        all_modes |= set(s["failure_modes"].keys())

    lines.append("| Mode | " + " | ".join(s["name"] for s in all_stats) + " |")
    lines.append("|------|" + "|".join("------:" for _ in all_stats) + "|")
    for mode in sorted(all_modes):
        row = f"| {mode} |"
        for s in all_stats:
            count = s["failure_modes"].get(mode, 0)
            total_fail = s["total"] - s["correct"]
            row += f" {count} ({pct(count, max(total_fail, 1))}) |"
        lines.append(row)

    # Key findings
    lines.append("\n## Key Findings\n")
    if len(all_stats) >= 2:
        d0 = all_stats[0] if all_stats[0]["name"].startswith("D0") else None
        d1 = next((s for s in all_stats if s["name"].startswith("D1")), None)
        d3 = next((s for s in all_stats if s["name"].startswith("D3")), None)

        if d0 and d1:
            d0_rate = d0["correct"] / max(d0["total"], 1) * 100
            d1_rate = d1["correct"] / max(d1["total"], 1) * 100
            lines.append(f"- **Search impact**: D0 (no search) = {d0_rate:.1f}% vs D1 (strict) = {d1_rate:.1f}% "
                         f"(delta = {d1_rate - d0_rate:+.1f}%)")

        if d1 and d3:
            d1_hedge = d1["failure_modes"].get("hedged", 0)
            d3_hedge = d3["failure_modes"].get("hedged", 0)
            lines.append(f"- **Hedge reduction**: D1 hedged {d1_hedge} tasks vs D3 hedged {d3_hedge} tasks")
            d3_rate = d3["correct"] / max(d3["total"], 1) * 100
            d1_rate = d1["correct"] / max(d1["total"], 1) * 100
            lines.append(f"- **No-hedge impact**: D1 = {d1_rate:.1f}% vs D3 = {d3_rate:.1f}% "
                         f"(delta = {d3_rate - d1_rate:+.1f}%)")

    return "\n".join(lines)


def main():
    gt_map = load_gt()
    print(f"Loaded {len(gt_map)} tasks with ground truth")

    all_stats = []
    for name, exp_dir in sorted(EXPERIMENTS.items()):
        results = load_experiment(Path(exp_dir))
        if not results:
            print(f"  {name}: no results found at {exp_dir}")
            continue
        stats = analyze_experiment(name, results, gt_map)
        all_stats.append(stats)
        print(f"  {name}: {stats['correct']}/{stats['total']} = {pct(stats['correct'], stats['total'])}")

    if not all_stats:
        print("No experiments found. Run the experiments first.")
        sys.exit(1)

    report = generate_report(all_stats)
    report_path = SCRIPT_DIR / "debug_report.md"
    report_path.write_text(report)
    print(f"\nReport written to {report_path}")


if __name__ == "__main__":
    main()
