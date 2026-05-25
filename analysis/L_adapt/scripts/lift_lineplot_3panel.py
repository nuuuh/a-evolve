#!/usr/bin/env python3
"""L_adapt evidence figure: per-cycle mean lift over the median single-committed
baseline, across the three benchmarks.

For each benchmark x cycle, every task contributes one lift value:
    lift_i = score_nav(x_i) - median_b score_b(x_i)
where the median is taken over the single-committed baselines.

Per cycle, we plot:
    - the mean lift (thick line)
    - +/- 1 sigma band (lift std around the mean within the cycle)

A horizontal reference at lift=0. If mean lift stays above 0 throughout the
stream and the band is wide, that is the L_adapt signature: structural
heterogeneity sustained over time.

Output: analysis/L_adapt/output/lift_lineplot_3panel.{pdf,png}
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
OUTPUT.mkdir(exist_ok=True)

REPO_ROOT = Path("/home/ec2-user/A-EVOLVE-V2/a-evolve")
RESULTS_ROOT = REPO_ROOT / "results"

BENCHES = [
    ("PolyBench", "polybench_navigation",
     ["polybench_baseline", "polybench_full_evo", "polybench_gepa_lite",
      "polybench_mh_lite", "polybench_continual_harness", "polybench_skillos"],
     "#3a6ea5", (-0.05, 1.0)),
    ("CTF-Dojo", "ctf_dojo_navigation",
     ["ctf_dojo_baseline", "ctf_dojo_full_evo", "ctf_dojo_gepa_lite",
      "ctf_dojo_mh_lite", "ctf_dojo_continual_harness", "ctf_dojo_skillos"],
     "#a52a2a", (-0.05, 0.30)),
    ("FutureX", "futurex_navigation",
     ["futurex_baseline", "futurex_full_evo", "futurex_gepa_lite",
      "futurex_mh_lite", "futurex_continual_harness", "futurex_skillos"],
     "#cc9966", (-0.05, 0.35)),
]


def load_run(run: str) -> dict[str, dict]:
    out = {}
    for line in (RESULTS_ROOT / run / "results.jsonl").read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        tid = r.get("task_id") or r.get("instance_id")
        if not tid:
            continue
        out[tid] = {
            "score": float(r.get("score") or 0.0),
            "cycle": r.get("evo_cycle"),
        }
    return out


def per_cycle_lifts(nav: dict, baselines: list[dict]) -> dict[int, list[float]]:
    out = defaultdict(list)
    for tid, nav_row in nav.items():
        if nav_row["cycle"] is None:
            continue
        b_scores = []
        for b in baselines:
            if tid not in b:
                continue
            b_scores.append(b[tid]["score"])
        if len(b_scores) < 3:
            continue
        med = float(np.median(b_scores))
        out[int(nav_row["cycle"])].append(nav_row["score"] - med)
    return out


def main() -> None:
    fig, axes = plt.subplots(3, 1, figsize=(11.5, 8.0), sharey=False)

    legend_handles = None

    for j, (name, nav_run, baseline_runs, color, ylim) in enumerate(BENCHES):
        ax = axes[j]
        nav = load_run(nav_run)
        bs = [load_run(b) for b in baseline_runs]
        per_cyc = per_cycle_lifts(nav, bs)
        cycles = sorted(c for c in per_cyc if len(per_cyc[c]) >= 5)
        means = np.array([np.mean(per_cyc[c]) for c in cycles])

        running = []
        cum_mean, cum_ci = [], []
        for c in cycles:
            running.extend(per_cyc[c])
            arr = np.array(running)
            n = len(arr)
            m = float(np.mean(arr))
            sd = float(np.std(arr, ddof=1)) if n > 1 else 0.0
            cum_mean.append(m)
            cum_ci.append(1.96 * sd / np.sqrt(n))
        cum_mean = np.array(cum_mean)
        cum_ci = np.array(cum_ci)

        h_band = ax.fill_between(cycles, cum_mean - cum_ci, cum_mean + cum_ci,
                                  color=color, alpha=0.18,
                                  label="95\\% CI on cumulative mean")
        h_dots, = ax.plot(cycles, means, color=color, linewidth=0.0, marker="o",
                          markersize=5.5, markerfacecolor=color, alpha=0.35,
                          label="per-cycle mean")
        h_line, = ax.plot(cycles, cum_mean, color=color, linewidth=3.0,
                          label="cumulative mean lift", zorder=4)
        ax.axhline(0, color="#222", linewidth=1.0, linestyle="-", zorder=1)

        ax.set_xlim(min(cycles) - 0.6, max(cycles) + 0.6)
        ax.set_ylim(*ylim)
        ax.tick_params(axis="both", labelsize=16)
        ax.grid(axis="y", alpha=0.25, linestyle="--", color="#aaa")
        ax.set_axisbelow(True)
        ax.set_title(name, fontsize=20, fontweight="bold", color=color)
        if j == 0:
            legend_handles = [h_line, h_dots, h_band]
        if j == len(BENCHES) - 1:
            ax.set_xlabel("evolver cycle", fontsize=18)

    # Single legend above the three panels, 1x3 layout
    fig.legend(handles=legend_handles,
               loc="upper center", bbox_to_anchor=(0.5, 1.0),
               ncol=3, fontsize=18, framealpha=0.95, frameon=False,
               columnspacing=1.0, handletextpad=0.4, handlelength=2.0)
    fig.tight_layout(rect=[0.05, 0, 1, 0.95])
    # Single shared y-label, placed close to the plots
    fig.supylabel("per-task lift", fontsize=20, x=0.04)

    pdf = OUTPUT / "lift_lineplot_3panel.pdf"
    png = OUTPUT / "lift_lineplot_3panel.png"
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, bbox_inches="tight", dpi=150)
    print(f"wrote {pdf}\nwrote {png}")


if __name__ == "__main__":
    main()
