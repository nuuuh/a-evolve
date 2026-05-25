#!/usr/bin/env python3
"""FutureX L_adapt evidence: per-branch lift of routed harness over baselines.

The navigation evolver spawned per-task-type skills:
    sports_prediction              : sports match outcomes
    sports_stats_multiselect       : sports stats multi-select
    chinese_financial_prediction   : Chinese financial exact-value (early exit)
    financial_instruments          : financial instrument disambiguation
    future_value_estimation        : value-estimation tasks
    daily_ranking_prediction       : ranking-volatility tasks
    multi_select_strategy          : general multi-select
    prediction_market_resolution   : prediction-market-style questions
    search_workflow                : default search-grounded prediction

We bin tasks by question content (regex over the prompt) onto these branches.

For each task we compute:
    y_best_base = max score across {baseline, full_evo, gepa_lite, mh_lite,
                                     continual_harness, skillos}
    y_nav       = score from futurex_navigation
    lift        = y_nav - y_best_base

Output: analysis/L_adapt/output/futurex_per_branch_lift.{pdf,png}
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
CATALOG_PATH = REPO_ROOT / "data" / "futurex" / "futurex_past.json"

NAV_RUN = "futurex_navigation"
BASELINE_RUNS = [
    "futurex_baseline",
    "futurex_full_evo",
    "futurex_gepa_lite",
    "futurex_mh_lite",
    "futurex_continual_harness",
    "futurex_skillos",
]

# Branch order matches the system prompt's routing rules: more-specific first
BRANCHES = [
    ("sports_multiselect",
     "sports stats multi-select\n(super bowl / nfl / nba props)",
     "#1f4e79"),
    ("sports",
     "sports match outcomes\n(soccer / nhl / nba / etc.)",
     "#3a6ea5"),
    ("chinese_finance",
     "Chinese financial exact-value\n(market cap / index / commodity)",
     "#7fa5cc"),
    ("ranking",
     "daily ranking / chart prediction\n(Maoyan / Douban / TV / etc.)",
     "#cc9966"),
    ("multi_select",
     "general multi-select\n(non-sports)",
     "#a52a2a"),
    ("financial_value",
     "future value estimation\n(currency / commodity / index)",
     "#cc4444"),
    ("default",
     "default search-grounded\n(general events)",
     "#888888"),
]


def load_catalog() -> dict[str, dict]:
    """instance_id -> question metadata."""
    out = {}
    with open(CATALOG_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            qid = r.get("id")
            if qid:
                out[qid] = r
    return out


def assign_branch(meta: dict) -> str | None:
    """Use the question prompt + title to route to a branch via keyword match.
    Order matters: more-specific keywords first."""
    txt = ((meta.get("prompt") or "") + " " + (meta.get("title") or "")).lower()
    if not txt.strip():
        return None

    # 1. Sports multi-select (Super Bowl / NFL props / etc.)
    if (("super bowl" in txt or "nfl" in txt or "nba" in txt
         or "premier league" in txt or "world cup" in txt)
        and ("\\boxed{" in txt and ("a." in txt or "all correct" in txt))):
        # multi-select format detected via boxed prompt
        if re.search(r"(team\s+stat|score|points|yards|touchdown|goal|assist|rebound)", txt):
            return "sports_multiselect"

    # 2. Sports match outcomes (single-team/winner predictions)
    if re.search(r"(match|game)\b.*\b(win|loss|outcome|defeat|victory|score)", txt):
        return "sports"
    if re.search(r"\b(beat|defeat|vs\.?|against)\b", txt) and ("\\boxed{" in txt):
        # decide single-select sports
        if re.search(r"(soccer|football|hockey|nhl|nba|baseball|mlb|tennis|"
                     r"premier league|champions league|cricket)", txt):
            return "sports"

    # 3. Chinese financial / commodity
    if re.search(r"(china|chinese|hsi|csi|hong kong|shanghai|shenzhen|yuan|"
                 r"rmb|cny|hkd|hkex|sse|szse|沪深|上证|深证|港股)", txt):
        if re.search(r"(close|open|high|low|price|index|market cap|stock)", txt):
            return "chinese_finance"

    # 4. Ranking / chart prediction (volatile daily/weekly rankings)
    if re.search(r"(rank|ranking|top\s*\d+|chart|leaderboard|atp|wta)", txt):
        return "ranking"

    # 5. Financial value estimation (currency / commodity / index)
    if re.search(r"(usd|eur|jpy|gbp|gold|oil|brent|wti|copper|silver|bitcoin|"
                 r"ethereum|crude|s&p|nasdaq|dow|stock|currency|exchange rate)", txt):
        if re.search(r"(price|value|close|high|low|exchange rate)", txt):
            return "financial_value"

    # 6. Multi-select non-sports
    if "\\boxed{" in txt and re.search(r"(\bA\.\s|\boption|listing all correct)", txt):
        return "multi_select"

    # 7. Default
    return "default"


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
    catalog = load_catalog()
    print(f"loaded {len(catalog)} catalog entries")

    scores = {r: load_run_scores(r) for r in BASELINE_RUNS + [NAV_RUN]}
    for r, s in scores.items():
        print(f"  {r:<32s}  n={len(s)}")

    overall_pass = {r: np.mean(list(scores[r].values())) for r in BASELINE_RUNS}
    best_run = max(overall_pass, key=overall_pass.get)
    print(f"\nOverall best single-committed baseline: {best_run} "
          f"(pass={overall_pass[best_run]*100:.1f}%)")

    # FutureX instance_id format: "futurex_past_NNNN_YYYYMMDD"  -> need to map to
    # catalog id. The benchmark loader truncates to NNNN, so let's match by index.
    # Easier: re-load the JSONL in order, since catalog is ordered.
    catalog_list = list(catalog.values())

    # Build instance_id -> meta map
    iid_to_meta = {}
    for line in (RESULTS_ROOT / "futurex_baseline" / "results.jsonl").read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        iid = r.get("instance_id")
        if not iid:
            continue
        # iid like "futurex_past_0474_20260108"
        m = re.match(r"futurex_past_(\d+)_", iid)
        if m:
            idx = int(m.group(1))
            if 0 <= idx < len(catalog_list):
                iid_to_meta[iid] = catalog_list[idx]
    print(f"mapped {len(iid_to_meta)} instance_ids to catalog entries")

    # Per-task aggregation
    rows = []
    for tid in scores[NAV_RUN].keys():
        meta = iid_to_meta.get(tid)
        if meta is None:
            continue
        b = assign_branch(meta)
        if b is None:
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

    print(f"\nrows: {len(rows)}")
    branch_counts = defaultdict(int)
    for r in rows:
        branch_counts[r["branch"]] += 1
    print("branch counts:", dict(branch_counts))

    print(f"\n{'branch':<22s}  {'n':>4s}  {'best-overall':>13s}  {'mean-base':>10s}  "
          f"{'nav':>9s}  {'lift vs best-1':>14s}  {'lift vs mean':>13s}")
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
        print(f"{b_key:<22s}  {n:>4d}  {best_overall*100:>12.1f}%  {mean_b*100:>9.1f}%  "
              f"{nav*100:>8.1f}%  {(nav-best_overall)*100:>13.1f}pp  {(nav-mean_b)*100:>12.1f}pp")

    if not summary:
        print("no branches with tasks; aborting figure")
        return

    # ---- Figure ----
    fig, ax = plt.subplots(figsize=(11.5, 4.4))
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
    xlim_hi = lift_mn.max() + 12
    xlim_lo = min(0, lift_mn.min() - 3)
    ax.set_xlim(xlim_lo, xlim_hi)
    ax.axvline(0, color="#222", linewidth=0.8)
    ax.grid(axis="x", alpha=0.25, linestyle="--", color="#aaa")
    ax.set_axisbelow(True)
    ax.invert_yaxis()

    ax.set_title(
        "FutureX $L_{\\mathrm{adapt}}$ evidence: per-branch lift of the routed harness over the median single-committed baseline.\n"
        "Each row = task type the navigation evolver spawned a dedicated skill for.",
        fontsize=11, fontweight="bold")

    fig.tight_layout()
    pdf = OUTPUT / "futurex_per_branch_lift.pdf"
    png = OUTPUT / "futurex_per_branch_lift.png"
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, bbox_inches="tight", dpi=170)
    print(f"\nwrote {pdf}\nwrote {png}")

    out = DATA / "futurex_per_branch_lift.json"
    out.write_text(json.dumps(summary, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
