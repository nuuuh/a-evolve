#!/usr/bin/env python3
"""CTF-Dojo L_adapt evidence: per-branch lift of routed harness over baselines.

The navigation evolver spawned per-category skills. We use the task's
declared category as the routing key (CTF tasks come pre-labelled with a
category in the archive). Branches:

    crypto-workflow    : crypto challenges
    rev-workflow       : reversing challenges
    binary-quickstart  : pwn challenges
    forensics-workflow : forensics challenges
    misc-esoteric      : misc challenges
    web                : web challenges (handled by general agent + GitHub-first)
    other              : everything else (recon, rare categories)

For each task we compute:
    y_best_base = max score across {baseline, full_evo, gepa_lite, mh_lite,
                                     continual_harness, skillos}
    y_nav       = score from ctf_dojo_navigation
    lift        = y_nav - y_best_base

If lift is positive on every branch, the per-task optimum varies enough that
no single committed baseline harness matches it across the partition.

Output: analysis/L_adapt/output/ctf_per_branch_lift.{pdf,png}
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
OUTPUT.mkdir(exist_ok=True)
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

REPO_ROOT = Path("/home/ec2-user/A-EVOLVE-V2/a-evolve")
RESULTS_ROOT = REPO_ROOT / "results"
ARCHIVE_PATH = REPO_ROOT / "data" / "ctf_archive.json"

NAV_RUN = "ctf_dojo_navigation"
BASELINE_RUNS = [
    "ctf_dojo_baseline",
    "ctf_dojo_full_evo",
    "ctf_dojo_gepa_lite",
    "ctf_dojo_mh_lite",
    "ctf_dojo_continual_harness",
    "ctf_dojo_skillos",
]

BRANCHES = [
    ("crypto",    "crypto challenges\n(crypto-workflow skill)",          "#3a6ea5"),
    ("rev",       "reversing challenges\n(rev-workflow skill)",          "#1f4e79"),
    ("pwn",       "pwn challenges\n(binary-quickstart skill)",           "#7fa5cc"),
    ("forensics", "forensics challenges\n(forensics-workflow skill)",    "#a52a2a"),
    ("misc",      "misc / esoteric\n(misc-esoteric skill)",              "#cc9966"),
    ("web",       "web challenges\n(general agent)",                     "#888888"),
]


def load_archive_categories() -> dict[str, str]:
    """instance_id (e.g., 'csawctf2011/crypto1') -> category."""
    with open(ARCHIVE_PATH) as f:
        arr = json.load(f)
    out = {}
    for k, v in arr.items():
        if isinstance(v, dict) and "category" in v:
            out[k] = str(v["category"]).lower().strip()
    return out


def load_run_scores(run_name: str) -> dict[str, float]:
    rj = RESULTS_ROOT / run_name / "results.jsonl"
    out = {}
    for line in rj.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        tid = r.get("task_id") or r.get("instance_id")
        if not tid:
            continue
        out[tid] = float(r.get("score") or 0.0)
    return out


def main() -> None:
    cats = load_archive_categories()
    print(f"loaded {len(cats)} archive categories")

    scores = {r: load_run_scores(r) for r in BASELINE_RUNS + [NAV_RUN]}
    for r, s in scores.items():
        print(f"  {r:<32s}  n={len(s)}")

    overall_pass = {r: np.mean(list(scores[r].values())) for r in BASELINE_RUNS}
    best_run = max(overall_pass, key=overall_pass.get)
    print(f"\nOverall best single-committed baseline: {best_run} "
          f"(pass={overall_pass[best_run]*100:.1f}%)")

    # Per-task aggregation
    rows = []
    no_branch = 0
    for tid in scores[NAV_RUN].keys():
        cat = cats.get(tid)
        if cat is None:
            no_branch += 1
            continue
        if cat in {"crypto", "rev", "pwn", "forensics", "misc", "web"}:
            b = cat
        else:
            no_branch += 1
            continue
        baseline_scores = [scores[r][tid] for r in BASELINE_RUNS if tid in scores[r]]
        if not baseline_scores:
            continue
        rows.append({
            "task_id": tid,
            "branch": b,
            "best_overall_base": scores[best_run].get(tid, 0.0),
            "median_base": float(np.median(baseline_scores)),
            "nav": scores[NAV_RUN].get(tid, 0.0),
        })
    print(f"\nrows: {len(rows)}  excluded as ambiguous: {no_branch}")

    print(f"\n{'branch':<10s}  {'n':>4s}  {'best-overall':>13s}  {'mean-base':>10s}  {'nav':>9s}  "
          f"{'lift vs best-1':>14s}  {'lift vs mean':>13s}")
    summary = []
    for b_key, b_label, b_color in BRANCHES:
        sub = [r for r in rows if r["branch"] == b_key]
        n = len(sub)
        if n == 0:
            continue
        best_overall = np.mean([r["best_overall_base"] for r in sub])
        mean_b = np.mean([r["median_base"] for r in sub])
        nav = np.mean([r["nav"] for r in sub])
        diff_bo = np.array([r["nav"] - r["best_overall_base"] for r in sub])
        ci_bo = 1.96 * diff_bo.std(ddof=1) / np.sqrt(n) if n > 1 else 0.0
        diff_mn = np.array([r["nav"] - r["median_base"] for r in sub])
        ci_mn = 1.96 * diff_mn.std(ddof=1) / np.sqrt(n) if n > 1 else 0.0
        summary.append({
            "branch": b_key, "label": b_label, "color": b_color,
            "n": n, "best_overall_base": float(best_overall),
            "median_base": float(mean_b), "nav": float(nav),
            "lift_vs_best_overall": float(nav - best_overall),
            "lift_vs_median": float(nav - mean_b),
            "ci_best_overall": float(ci_bo),
            "ci_median": float(ci_mn),
        })
        print(f"{b_key:<10s}  {n:>4d}  {best_overall*100:>12.1f}%  {mean_b*100:>9.1f}%  "
              f"{nav*100:>8.1f}%  {(nav-best_overall)*100:>13.1f}pp  {(nav-mean_b)*100:>12.1f}pp")

    # Sort branches by lift_vs_best descending for visual scan
    # but keep original BRANCHES order for paper consistency

    # ---- Figure ----
    fig, ax = plt.subplots(figsize=(11.5, 4.0))
    y_pos = np.arange(len(summary))
    lift_mn = np.array([s["lift_vs_median"] * 100 for s in summary])

    ax.barh(y_pos, lift_mn, 0.55,
            color=[s["color"] for s in summary],
            edgecolor="#222", linewidth=0.5)

    for i, s in enumerate(summary):
        ax.text(lift_mn[i] + 0.5, i,
                f"{lift_mn[i]:+.1f}pp",
                va="center", fontsize=9.5, fontweight="bold", color="#222")

    ax.set_yticks(y_pos)
    ax.set_yticklabels([s["label"] for s in summary], fontsize=9.5)
    ax.set_xlabel("per-task pass-rate lift over the median single-committed baseline  (pp)",
                  fontsize=10.5)
    xlim_hi = lift_mn.max() + 8
    xlim_lo = min(0, lift_mn.min() - 3)
    ax.set_xlim(xlim_lo, xlim_hi)
    ax.axvline(0, color="#222", linewidth=0.8)
    ax.grid(axis="x", alpha=0.25, linestyle="--", color="#aaa")
    ax.set_axisbelow(True)
    ax.invert_yaxis()

    ax.set_title(
        "CTF-Dojo $L_{\\mathrm{adapt}}$ evidence: per-branch lift of the routed harness over the median single-committed baseline.",
        fontsize=11, fontweight="bold")

    fig.tight_layout()
    pdf = OUTPUT / "ctf_per_branch_lift.pdf"
    png = OUTPUT / "ctf_per_branch_lift.png"
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, bbox_inches="tight", dpi=170)
    print(f"\nwrote {pdf}\nwrote {png}")

    out = DATA / "ctf_per_branch_lift.json"
    out.write_text(json.dumps(summary, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
