#!/usr/bin/env python3
"""Generate the L_evo capability-bottleneck figure.

Produces a single 1x3 panel figure showing, per benchmark, how end-of-stream
performance climbs as the harness gains the capability that benchmark cares
about. PolyBench: confidence calibration. FutureX: search-API tier. CTF-Dojo:
per-category specialised toolkits.

Output: ../output/stairstep_figure.pdf and .png
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUTPUT = ROOT / "output"
OUTPUT.mkdir(exist_ok=True)

REPO_ROOT = Path("/home/ec2-user/A-EVOLVE-V2/a-evolve")
RESULTS_ROOT = REPO_ROOT / "results"
DB_PATH = Path("/home/ec2-user/A-EVOLVE-V2/data/polymarket_analysis.db")


def load(name: str) -> dict:
    with (DATA / name).open() as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# PolyBench panel: confidence vs. market consensus, per class x stream segment
# ---------------------------------------------------------------------------

CLASSES_POLY = [
    ("Single-agent",
     ["polybench_full_evo", "polybench_gepa_lite", "polybench_continual_harness",
      "polybench_skillos", "polybench_mh_lite"]),
    ("Multi-agent",
     ["polybench_structured_evo", "polybench_navigation"]),
]
SEGMENTS_POLY = [
    ("early", 1, 17),
    ("mid",  18, 34),
    ("late", 35, 51),
]
SEGMENT_REDS  = ["#fcae91", "#de2d26", "#67000d"]
SEGMENT_BLUES = ["#9ecae1", "#4292c6", "#08519c"]


def _poly_features() -> dict[str, dict]:
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


def _poly_collect(runs, features, *, min_liq=1000.0):
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
            tid = r.get("task_id", "") or r.get("instance_id", "")
            parts = tid.split("_")
            if len(parts) < 2:
                continue
            mid = parts[1]
            if mid not in features:
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


def _conditional_curve(x, y, edges, *, min_n=30):
    centers, means = [], []
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        if i == len(edges) - 2:
            mask = (x >= lo) & (x <= hi + 1e-9)
        else:
            mask = (x >= lo) & (x < hi)
        if mask.sum() < min_n:
            continue
        centers.append((lo + hi) / 2)
        means.append(float(y[mask].mean()))
    return np.array(centers), np.array(means)


def panel_polybench(ax, payload: dict) -> None:
    """payload kept for interface compatibility but unused; this panel uses
    the per-segment KDE conditional-mean curves."""
    features = _poly_features()
    edges = np.array([0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80,
                      0.85, 0.90, 0.95, 1.001])
    palettes = {"Single-agent": SEGMENT_REDS, "Multi-agent": SEGMENT_BLUES}
    cls_short = {"Single-agent": "single", "Multi-agent": "multi"}

    handles_by_cls: dict[str, list] = {"Single-agent": [], "Multi-agent": []}
    for cls_label, runs in CLASSES_POLY:
        x_all, y_all, c_all = _poly_collect(runs, features)
        for s_idx, (seg_label, lo_c, hi_c) in enumerate(SEGMENTS_POLY):
            mask = (c_all >= lo_c) & (c_all <= hi_c)
            x_seg, y_seg = x_all[mask], y_all[mask]
            if len(x_seg) < 100:
                continue
            cx, cm = _conditional_curve(x_seg, y_seg, edges)
            color = palettes[cls_label][s_idx]
            line, = ax.plot(cx, cm, color=color, linewidth=1.4,
                            marker="o", markersize=2.8,
                            label=f"{cls_short[cls_label]}-{seg_label}",
                            zorder=3 + s_idx)
            handles_by_cls[cls_label].append(line)

    ax.plot([0.5, 1.0], [0.5, 1.0], color="#222", linestyle="--",
            linewidth=0.9, alpha=0.65)
    ax.axhline(0.6, color="#888", linestyle=":", linewidth=0.7)

    ax.set_xlim(0.5, 1.0)
    ax.set_ylim(0.55, 1.05)
    ax.set_xlabel("market consensus", fontsize=9, labelpad=1)
    ax.set_ylabel("mean stated confidence", fontsize=9, labelpad=1)
    ax.set_title("PolyBench", fontsize=10, fontweight="bold")
    ax.tick_params(axis="both", labelsize=7, pad=1)

    s_handles = handles_by_cls["Single-agent"]
    m_handles = handles_by_cls["Multi-agent"]
    ordered = []
    for i in range(min(len(s_handles), len(m_handles))):
        ordered.append(s_handles[i])
        ordered.append(m_handles[i])
    ax.legend(handles=ordered, loc="upper left", fontsize=8,
              framealpha=0.95, ncol=2,
              columnspacing=0.6, handletextpad=0.3, handlelength=1.4,
              borderpad=0.3, labelspacing=0.3)
    ax.grid(alpha=0.22, linestyle="--", color="#aaa")
    ax.set_axisbelow(True)


def panel_futurex(ax, payload: dict) -> None:
    rows = payload["rows"]
    labels = [r["short_label"] for r in rows]
    acc = [r["headline_value"] for r in rows]
    y = np.arange(len(rows))

    cmap = plt.cm.viridis(np.linspace(0.2, 0.75, len(rows)))
    bars = ax.barh(y, acc, color=cmap, edgecolor="#333", linewidth=0.4)
    ax.plot(acc, y, color="#cc3333", marker="o", linewidth=1.6,
            markersize=5, zorder=3)

    for b, v in zip(bars, acc):
        ax.text(v + 1.0, b.get_y() + b.get_height() / 2, f"{v:.1f}",
                ha="left", va="center", fontsize=7.5, fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0, 70)
    ax.set_xlabel("Accuracy (\\%)", fontsize=9, labelpad=1)
    ax.tick_params(axis="both", labelsize=7, pad=1)
    ax.set_title("FutureX", fontsize=10, fontweight="bold")
    ax.grid(axis="x", alpha=0.25, linestyle="--")
    ax.set_axisbelow(True)


def panel_ctf(ax, payload: dict) -> None:
    rows = payload["rows"]
    tiers = [r["tier"] for r in rows]
    single = [r["single_pct"] for r in rows]
    multi = [r["multi_pct"] for r in rows]
    y = np.arange(len(rows))
    width = 0.38

    ax.barh(y - width / 2, single, width, color="#c0c0c0", edgecolor="#888",
            linewidth=0.5, label="Best single-agent")
    ax.barh(y + width / 2, multi, width, color="#3a6ea5", label="Multi-agent")

    for i in range(len(rows)):
        ax.text(single[i] + 1.0, y[i] - width / 2, f"{single[i]:.0f}",
                ha="left", va="center", fontsize=6.5, color="#555")
        ax.text(multi[i] + 1.0, y[i] + width / 2, f"{multi[i]:.0f}",
                ha="left", va="center", fontsize=6.5, color="#3a6ea5",
                fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels(tiers, fontsize=7.5)
    ax.invert_yaxis()
    ax.set_ylabel("largest file size", fontsize=9, labelpad=1)
    ax.set_xlabel("Pass rate (\\%)", fontsize=9, labelpad=1)
    ax.tick_params(axis="x", labelsize=7, pad=1)
    ax.tick_params(axis="y", labelsize=7, pad=0)
    ax.set_title("CTF-Dojo", fontsize=10, fontweight="bold")
    ax.set_xlim(0, 115)
    ax.legend(loc="lower right", fontsize=8, framealpha=0.95,
              borderpad=0.3, labelspacing=0.3, handletextpad=0.3,
              handlelength=1.4, ncol=1)
    ax.grid(axis="x", alpha=0.25, linestyle="--")
    ax.set_axisbelow(True)


def main() -> None:
    futurex = load("futurex_stairstep.json")
    ctf = load("ctf_dojo_stairstep.json")

    fig, axes = plt.subplots(3, 1, figsize=(3.4, 4.8),
                              gridspec_kw={"hspace": 0.45,
                                            "height_ratios": [1.6, 1.0, 1.0]})
    panel_polybench(axes[0], {})
    panel_futurex(axes[1], futurex)
    panel_ctf(axes[2], ctf)
    # Pin a common right edge across all panels; align y-label text positions
    # vertically. CTF's plot frame naturally starts further right than the
    # other two because its y-tick labels are wider.
    fig.subplots_adjust(right=0.97, top=0.96, bottom=0.07, hspace=0.45)
    fig.align_ylabels(axes)

    pdf_path = OUTPUT / "l_evo_evidence.pdf"
    png_path = OUTPUT / "l_evo_evidence.png"
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, bbox_inches="tight", dpi=180)
    print(f"wrote {pdf_path}")
    print(f"wrote {png_path}")


if __name__ == "__main__":
    main()
