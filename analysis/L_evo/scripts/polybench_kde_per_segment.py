#!/usr/bin/env python3
"""PolyBench L_evo evidence (per-segment): how does the (consensus -> confidence)
function evolve over the stream within each class?

Same axes as polybench_kde_final.py:
    x = market consensus (max outcome price), task-intrinsic.
    y = stated confidence, model outcome.

Split: stream segment (early cycles 1-17 / mid cycles 18-34 / late cycles
35-51). Within each class, plot E[c | p_max] once per segment with 95% CI bands.

This figure complements the headline L_evo figure (polybench_kde_final): it
shows that the multi-agent class's calibrated y(x) function emerges and
sharpens over the stream, while the single-agent class's flat-confidence
function does not develop into a calibrated mapping at any stream position.

Output: analysis/L_evo/output/polybench_kde_per_segment.{pdf,png}
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
OUTPUT.mkdir(exist_ok=True)

REPO_ROOT = Path("/home/ec2-user/A-EVOLVE-V2/a-evolve")
RESULTS_ROOT = REPO_ROOT / "results"
DB_PATH = Path("/home/ec2-user/A-EVOLVE-V2/data/polymarket_analysis.db")

CLASSES = [
    ("Single-agent",
     ["polybench_full_evo", "polybench_gepa_lite", "polybench_continual_harness",
      "polybench_skillos", "polybench_mh_lite"], "#cc4444"),
    ("Multi-agent",
     ["polybench_structured_evo", "polybench_navigation"], "#3a6ea5"),
]

# Stream segments (51 cycles total, ~100 tasks each)
SEGMENTS = [
    ("early (cycles 1-17)",  1, 17,  "#fdd0a2"),
    ("mid (cycles 18-34)",  18, 34,  "#fdae6b"),
    ("late (cycles 35-51)", 35, 51,  "#a63603"),
]
# Same shape: light -> dark
SEGMENT_BLUES = ["#9ecae1", "#4292c6", "#08519c"]
SEGMENT_REDS  = ["#fcae91", "#de2d26", "#67000d"]


def load_features() -> dict[str, dict]:
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("""
        SELECT m.id, m.outcome_prices, m.liquidity FROM markets m
        JOIN resolutions r ON r.market_id = m.id
        WHERE r.winning_outcome IS NOT NULL
    """)
    out = {}
    for mid, prices_json, liq in cur.fetchall():
        try:
            prices = [float(p) for p in json.loads(prices_json or "[]")]
            mp = max(prices) if prices else 0.5
        except Exception:
            mp = 0.5
        out[str(mid)] = {"max_price": mp, "liquidity": float(liq or 0)}
    conn.close()
    return out


def task_id_to_market_id(t: str) -> str | None:
    p = t.split("_")
    return p[1] if len(p) >= 2 else None


def collect_with_cycle(runs: list[str], features: dict, *, min_liq: float = 1000.0):
    """Return arrays of (max_price, confidence, evo_cycle) over traded rows
    with liquidity >= $1K."""
    xs, ys, cs = [], [], []
    for run_name in runs:
        rj = RESULTS_ROOT / run_name / "results.jsonl"
        if not rj.exists():
            continue
        for line in rj.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            mid = task_id_to_market_id(r.get("task_id", "") or r.get("instance_id", ""))
            if mid is None or mid not in features:
                continue
            f = features[mid]
            if f["liquidity"] < min_liq:
                continue
            decision = (r.get("decision") or "").strip().upper()
            gated = bool(r.get("gated"))
            traded = (not gated) and decision in ("BUY", "SELL")
            if not traded:
                continue
            conf = float(r.get("confidence") or 0)
            if conf <= 0:
                continue
            cyc = r.get("evo_cycle")
            if cyc is None:
                continue
            xs.append(f["max_price"])
            ys.append(conf)
            cs.append(int(cyc))
    return np.array(xs), np.array(ys), np.array(cs)


def conditional_curve(x, y, edges):
    centers, means, hi95, lo95, ns = [], [], [], [], []
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        if i == len(edges) - 2:
            mask = (x >= lo) & (x <= hi + 1e-9)
        else:
            mask = (x >= lo) & (x < hi)
        n = mask.sum()
        if n < 30:
            continue
        vals = y[mask]
        m = vals.mean()
        sd = vals.std(ddof=1)
        ci = 1.96 * sd / np.sqrt(n)
        centers.append((lo + hi) / 2)
        means.append(m)
        hi95.append(m + ci)
        lo95.append(m - ci)
        ns.append(n)
    return (np.array(centers), np.array(means),
            np.array(lo95), np.array(hi95), np.array(ns))


def main() -> None:
    print("Loading features...")
    features = load_features()
    print(f"  {len(features)} markets")

    edges = np.array([0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80,
                      0.85, 0.90, 0.95, 1.001])

    fig, ax = plt.subplots(figsize=(4.8, 4.4))

    palettes = {"Single-agent": SEGMENT_REDS, "Multi-agent": SEGMENT_BLUES}
    drift_summary = []
    SEG_SHORT = {"early (cycles 1-17)": "early",
                 "mid (cycles 18-34)": "mid",
                 "late (cycles 35-51)": "late"}
    CLS_SHORT = {"Single-agent": "single", "Multi-agent": "multi"}

    for cls_label, runs, base_color in CLASSES:
        x_all, y_all, c_all = collect_with_cycle(runs, features)
        n_total = len(x_all)
        print(f"\n{cls_label}: n={n_total:,} traded rows total")

        for s_idx, (seg_label, lo_c, hi_c, _) in enumerate(SEGMENTS):
            mask = (c_all >= lo_c) & (c_all <= hi_c)
            x_seg, y_seg = x_all[mask], y_all[mask]
            n_seg = len(x_seg)
            print(f"  {seg_label}: n={n_seg}")
            if n_seg < 100:
                continue
            cx, cm, lo95, hi95, _ = conditional_curve(x_seg, y_seg, edges)
            color = palettes[cls_label][s_idx]
            ax.plot(cx, cm, color=color, linewidth=2.6,
                    marker="o", markersize=6,
                    label=f"{CLS_SHORT[cls_label]}-{SEG_SHORT[seg_label]}",
                    zorder=3 + s_idx)
            if (cx < 0.7).any():
                drift_summary.append((cls_label, seg_label,
                                      float(cm[cx < 0.7].mean())))

    # Shared reference lines
    ax.plot([0.5, 1.0], [0.5, 1.0], color="#222", linestyle="--",
            linewidth=1.2, alpha=0.65, label=r"$y{=}x$")
    ax.axhline(0.6, color="#888", linestyle=":", linewidth=1.0)

    ax.set_xlim(0.5, 1.0)
    ax.set_ylim(0.55, 1.0)
    ax.set_xlabel("market consensus  (max outcome price)", fontsize=15)
    ax.set_ylabel("mean stated confidence", fontsize=15)
    ax.tick_params(axis="both", labelsize=13)
    ax.grid(alpha=0.22, linestyle="--", color="#aaa")
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", fontsize=12, framealpha=0.96, ncol=2,
              columnspacing=0.8, handletextpad=0.4, handlelength=1.6)

    fig.tight_layout()

    pdf = OUTPUT / "polybench_kde_per_segment.pdf"
    png = OUTPUT / "polybench_kde_per_segment.png"
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, bbox_inches="tight", dpi=170)
    print(f"\nwrote {pdf}")
    print(f"wrote {png}")

    print("\nDrift on uncertain markets (p_max < 0.7):")
    for cls_label, seg_label, m in drift_summary:
        print(f"  {cls_label:<13s}  {seg_label:<22s}  mean conf = {m:.3f}")


if __name__ == "__main__":
    main()
