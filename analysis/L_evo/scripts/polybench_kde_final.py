#!/usr/bin/env python3
"""PolyBench L_evo final figure: confidence-vs-consensus density per evolver class.

Story:
    Multi-agent's stated confidence tracks the task-intrinsic market-consensus
    statistic (max outcome price) monotonically; single-agent's confidence is
    decoupled from consensus and collapses to a tight peak at the
    "obviously decided" corner. The single-agent harness fails to *use* the
    task input, mirroring FutureX's search-tier stair-step where the
    benchmark bottleneck is a task-side statistic the agent must adapt to.

Figure layout:
    1 row, 3 columns (paper-column-width or full-width).
        (a) single-agent  : 2D KDE of (max_price, confidence) over traded rows
                            with liquidity >= $1K. Marginal hist on top.
        (b) multi-agent   : same, with shared color scale magnitude.
        (c) conditional    : mean confidence per max_price band, single vs
                             multi as two lines with 95% CI bands. The
                             "money chart": a 1D summary distilling the 2D story.

x-axis: market consensus (max outcome price). Task-intrinsic.
y-axis: stated confidence. Model output.

Filter: traded rows with liquidity >= $1K (drop illiquid markets where the
right answer is SKIP regardless of direction).

Output: output/polybench_kde_final.{pdf,png}
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
from scipy.stats import gaussian_kde

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
OUTPUT.mkdir(exist_ok=True)

REPO_ROOT = Path("/home/ec2-user/A-EVOLVE-V2/a-evolve")
RESULTS_ROOT = REPO_ROOT / "results"
DB_PATH = Path("/home/ec2-user/A-EVOLVE-V2/data/polymarket_analysis.db")

CLASSES = [
    ("Single-agent",
     ["polybench_full_evo", "polybench_gepa_lite", "polybench_continual_harness",
      "polybench_skillos", "polybench_mh_lite"], "#cc4444", "Reds"),
    ("Multi-agent",
     ["polybench_structured_evo", "polybench_navigation"], "#3a6ea5", "Blues"),
]


def load_features() -> dict[str, dict]:
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("""
        SELECT m.id, m.outcome_prices, m.liquidity, m.volume FROM markets m
        JOIN resolutions r ON r.market_id = m.id
        WHERE r.winning_outcome IS NOT NULL
    """)
    out = {}
    for mid, prices_json, liq, vol in cur.fetchall():
        try:
            prices = [float(p) for p in json.loads(prices_json or "[]")]
            mp = max(prices) if prices else 0.5
        except Exception:
            mp = 0.5
        out[str(mid)] = {"max_price": mp, "liquidity": float(liq or 0),
                          "volume": float(vol or 0)}
    conn.close()
    return out


def task_id_to_market_id(t: str) -> str | None:
    p = t.split("_")
    return p[1] if len(p) >= 2 else None


def collect(runs: list[str], features: dict, *, min_liq: float = 1000.0):
    """Return arrays of (max_price, confidence) over traded rows with liq>=$1K."""
    xs, ys = [], []
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
            xs.append(f["max_price"])
            ys.append(conf)
    return np.array(xs), np.array(ys)


def kde_grid(x, y, x_lo, x_hi, y_lo, y_hi, *, resolution=200, bw=0.18):
    grid_x = np.linspace(x_lo, x_hi, resolution)
    grid_y = np.linspace(y_lo, y_hi, resolution)
    X, Y = np.meshgrid(grid_x, grid_y)
    pts = np.vstack([X.ravel(), Y.ravel()])
    kde = gaussian_kde(np.vstack([x, y]), bw_method=bw)
    Z = kde(pts).reshape(X.shape) * len(x)  # n-weighted: density magnitude reflects count
    return X, Y, Z


def conditional_curve(x, y, edges):
    """Per-bin (center, mean confidence, 95% CI half-width)."""
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

    # Collect once per class
    data = {}
    for label, runs, color, cmap in CLASSES:
        x, y = collect(runs, features)
        data[label] = (x, y, color, cmap)
        print(f"  {label}: n={len(x):,} traded rows (liq >= $1K)")

    # Bounds
    x_lo, x_hi = 0.5, 1.0
    y_lo, y_hi = 0.5, 1.0

    # Compute KDE for both classes; share a max for direct comparison
    grids = {}
    z_max = 0.0
    for label, (x, y, color, cmap) in data.items():
        X, Y, Z = kde_grid(x, y, x_lo, x_hi, y_lo, y_hi, bw=0.18)
        z_max = max(z_max, Z.max())
        grids[label] = (X, Y, Z)

    # ---- Build figure ----
    fig = plt.figure(figsize=(13.6, 4.8))
    gs = gridspec.GridSpec(
        2, 3,
        height_ratios=[1, 5],
        width_ratios=[1, 1, 1.1],
        hspace=0.04, wspace=0.20,
    )

    # Marginal histogram axes (top of panels a,b)
    ax_top_a = fig.add_subplot(gs[0, 0])
    ax_top_b = fig.add_subplot(gs[0, 1])
    ax_a = fig.add_subplot(gs[1, 0], sharex=ax_top_a)
    ax_b = fig.add_subplot(gs[1, 1], sharex=ax_top_b)
    ax_c = fig.add_subplot(gs[:, 2])

    bins_x = np.linspace(x_lo, x_hi, 30)

    # ---- (a) single-agent ----
    label = "Single-agent"
    x, y, color, cmap = data[label]
    X, Y, Z = grids[label]
    levels = np.linspace(z_max * 0.02, z_max, 16)
    ax_a.contourf(X, Y, Z, levels=levels, cmap=cmap, alpha=0.92)
    ax_a.contour(X, Y, Z, levels=levels[2::3], colors="#222",
                 linewidths=0.4, alpha=0.5)

    ax_a.axhline(0.6, color="#666", linestyle=":", linewidth=0.9)
    ax_a.text(0.51, 0.605, "gate $c{=}0.6$", fontsize=8.5, color="#444",
              style="italic")
    ax_a.axvline(0.95, color="#666", linestyle=":", linewidth=0.9)
    ax_a.plot([x_lo, x_hi], [x_lo, x_hi], color="#222", linestyle="--",
              linewidth=0.9, alpha=0.55)
    ax_a.text(0.83, 0.86, r"$y{=}x$ (calibrated)", fontsize=7.8, color="#222",
              style="italic", rotation=44, alpha=0.65)

    ax_a.set_xlim(x_lo, x_hi)
    ax_a.set_ylim(y_lo, y_hi)
    ax_a.set_xlabel("market consensus  (max outcome price)", fontsize=10.5)
    ax_a.set_ylabel("stated confidence", fontsize=10.5)
    ax_a.set_title(f"(a) Single-agent  ($n={len(x):,}$ traded rows)",
                   fontsize=11, fontweight="bold", color=color)
    ax_a.grid(alpha=0.18, linestyle="--", color="#aaa")
    ax_a.set_axisbelow(True)

    ax_top_a.hist(x, bins=bins_x, color=color, alpha=0.65, edgecolor="none")
    ax_top_a.tick_params(labelbottom=False, labelsize=8)
    ax_top_a.set_ylabel("# traded", fontsize=8.5)
    ax_top_a.set_xlim(x_lo, x_hi)
    ax_top_a.grid(axis="y", alpha=0.2, linestyle="--")
    ax_top_a.set_axisbelow(True)

    # ---- (b) multi-agent ----
    label = "Multi-agent"
    x, y, color, cmap = data[label]
    X, Y, Z = grids[label]
    ax_b.contourf(X, Y, Z, levels=levels, cmap=cmap, alpha=0.92)
    ax_b.contour(X, Y, Z, levels=levels[2::3], colors="#222",
                 linewidths=0.4, alpha=0.5)

    ax_b.axhline(0.6, color="#666", linestyle=":", linewidth=0.9)
    ax_b.text(0.51, 0.605, "gate $c{=}0.6$", fontsize=8.5, color="#444",
              style="italic")
    ax_b.axvline(0.95, color="#666", linestyle=":", linewidth=0.9)
    ax_b.plot([x_lo, x_hi], [x_lo, x_hi], color="#222", linestyle="--",
              linewidth=0.9, alpha=0.55)
    ax_b.text(0.83, 0.86, r"$y{=}x$ (calibrated)", fontsize=7.8, color="#222",
              style="italic", rotation=44, alpha=0.65)

    ax_b.set_xlim(x_lo, x_hi)
    ax_b.set_ylim(y_lo, y_hi)
    ax_b.set_xlabel("market consensus  (max outcome price)", fontsize=10.5)
    ax_b.set_title(f"(b) Multi-agent  ($n={len(x):,}$ traded rows)",
                   fontsize=11, fontweight="bold", color=color)
    ax_b.grid(alpha=0.18, linestyle="--", color="#aaa")
    ax_b.set_axisbelow(True)
    ax_b.tick_params(labelleft=False)

    ax_top_b.hist(x, bins=bins_x, color=color, alpha=0.65, edgecolor="none")
    ax_top_b.tick_params(labelbottom=False, labelsize=8)
    ax_top_b.set_xlim(x_lo, x_hi)
    ax_top_b.grid(axis="y", alpha=0.2, linestyle="--")
    ax_top_b.set_axisbelow(True)

    # ---- (c) conditional mean confidence per consensus band ----
    edges = np.array([0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80,
                      0.85, 0.90, 0.95, 1.001])

    summary_lines = []
    for label, runs, color, cmap in CLASSES:
        x, y = data[label][:2]
        cx, cm, lo95, hi95, ns = conditional_curve(x, y, edges)
        ax_c.fill_between(cx, lo95, hi95, color=color, alpha=0.18,
                          edgecolor="none")
        ax_c.plot(cx, cm, color=color, linewidth=2.4,
                  marker="o", markersize=5.5, label=label, zorder=5)
        summary_lines.append(
            f"{label}: $\\bar{{c}}$ at $p{{<}}0.7$ = {cm[cx < 0.7].mean():.2f},  "
            f"at $p{{>}}0.95$ = {cm[cx > 0.95].mean():.2f}"
        )

    ax_c.plot([x_lo, x_hi], [x_lo, x_hi], color="#222", linestyle="--",
              linewidth=1.0, alpha=0.65, label=r"$y{=}x$ (calibrated)")
    ax_c.axhline(0.6, color="#888", linestyle=":", linewidth=0.9)
    ax_c.text(x_lo + 0.005, 0.605, "gate $c{=}0.6$", fontsize=8.5,
              color="#444", style="italic")

    ax_c.set_xlim(x_lo, x_hi)
    ax_c.set_ylim(0.55, 1.0)
    ax_c.set_xlabel("market consensus  (max outcome price)", fontsize=10.5)
    ax_c.set_ylabel("mean stated confidence  (95\\% CI)", fontsize=10.5)
    ax_c.set_title("(c) Conditional mean confidence vs.\\ consensus",
                   fontsize=11, fontweight="bold")
    ax_c.grid(alpha=0.22, linestyle="--", color="#aaa")
    ax_c.set_axisbelow(True)
    ax_c.legend(loc="lower right", fontsize=9, framealpha=0.96)

    # ---- Suptitle ----
    fig.suptitle(
        "PolyBench $L_{\\mathrm{evo}}$ bottleneck: stated confidence as a function of a task-intrinsic statistic.\n"
        "Multi-agent's confidence tracks market consensus monotonically; single-agent's collapses to "
        "the obviously-decided corner.",
        fontsize=11.5, y=1.04,
    )

    pdf = OUTPUT / "polybench_kde_final.pdf"
    png = OUTPUT / "polybench_kde_final.png"
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, bbox_inches="tight", dpi=170)
    print(f"\nwrote {pdf}")
    print(f"wrote {png}")

    # Print the summary numbers explicitly
    print("\nSummary numbers:")
    for line in summary_lines:
        print(" ", line.replace("$", "").replace("\\bar{c}", "mean conf"))


if __name__ == "__main__":
    main()
