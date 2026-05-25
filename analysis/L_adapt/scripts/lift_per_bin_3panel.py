#!/usr/bin/env python3
"""L_adapt evidence figure: per-task-type cumulative lift over the median
single-committed baseline, across the three benchmarks.

Each panel: one cumulative-mean line per task-type bin (the partition the
navigation evolver itself spawned branches over). All lines should sit above
zero (conditioning helps everywhere) AND occupy different heights
(per-task optimum varies -> L_adapt > 0).

Layout: 3 rows, 1 column. Single shared y-label. Single legend block above
the figure for the line styles; a per-panel inline legend names the bins.

Output: analysis/L_adapt/output/lift_per_bin_3panel.{pdf,png}
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
OUTPUT.mkdir(exist_ok=True)

REPO_ROOT = Path("/home/ec2-user/A-EVOLVE-V2/a-evolve")
RESULTS_ROOT = REPO_ROOT / "results"
DB_PATH = Path("/home/ec2-user/A-EVOLVE-V2/data/polymarket_analysis.db")
ARCHIVE_PATH = REPO_ROOT / "data" / "ctf_archive.json"
FUTUREX_CATALOG = REPO_ROOT / "data" / "futurex" / "futurex_past.json"


# --- PolyBench: bin by (T1, p_max) ----------------------------------------
def load_polybench_bins() -> dict[str, str]:
    """task_id -> bin label."""
    db = sqlite3.connect(str(DB_PATH))
    cur = db.cursor()
    cur.execute("""SELECT s.id, s.timestamp, m.end_date, m.outcome_prices
                   FROM market_snapshots s
                   JOIN markets m ON m.id = s.market_id
                   JOIN resolutions r ON r.market_id = m.id
                   WHERE r.winning_outcome IS NOT NULL""")
    sid_meta = {}
    for sid, ts, end, op_json in cur.fetchall():
        try:
            t = datetime.fromisoformat(ts.replace("Z", ""))
            e = datetime.fromisoformat(end.replace("Z", "").replace("T", " "))
            ttr = (e - t).total_seconds() / 3600.0
        except Exception:
            continue
        p = None
        try:
            ops = json.loads(op_json or "[]")
            if ops:
                p = max(float(x) for x in ops)
        except Exception:
            pass
        sid_meta[int(sid)] = (ttr, p)
    db.close()

    out = {}
    for line in (RESULTS_ROOT / "polybench_navigation" / "results.jsonl").read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        tid = r.get("task_id") or r.get("instance_id")
        parts = (tid or "").split("_")
        if len(parts) < 3:
            continue
        try:
            sid = int(parts[2])
        except Exception:
            continue
        if sid not in sid_meta:
            continue
        t, p = sid_meta[sid]
        if p is None:
            continue
        if t < -2:
            if p >= 0.99:
                b = "post: decided"
            elif p >= 0.85:
                b = "post: LKP lags OB"
            elif p <= 0.7:
                b = "post: stale wide-spread"
            else:
                continue
        elif t > 2:
            if p >= 0.85:
                b = "pre: decisive OB"
            elif 0.40 <= p <= 0.60:
                b = "pre: near-50/50"
            elif 0.6 < p < 0.85:
                b = "pre: mid"
            else:
                continue
        else:
            continue
        out[tid] = b
    return out


# --- CTF: bin by category from archive -------------------------------------
def load_ctf_bins() -> dict[str, str]:
    cats = json.load(open(ARCHIVE_PATH))
    LABELS = {"crypto": "crypto", "rev": "reversing", "pwn": "pwn",
              "forensics": "forensics", "misc": "misc", "web": "web"}
    out = {}
    for k, v in cats.items():
        if not isinstance(v, dict):
            continue
        c = str(v.get("category", "")).lower().strip()
        if c in LABELS:
            out[k] = LABELS[c]
    return out


# --- FutureX: bin by question type from prompt -----------------------------
def load_futurex_bins() -> dict[str, str]:
    catalog = []
    for line in FUTUREX_CATALOG.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        catalog.append(json.loads(line))

    def assign(meta: dict) -> str | None:
        txt = ((meta.get("prompt") or "") + " " + (meta.get("title") or "")).lower()
        if not txt.strip():
            return None
        if (("super bowl" in txt or "nfl" in txt or "nba" in txt
             or "premier league" in txt or "world cup" in txt)
            and ("\\boxed{" in txt and ("a." in txt or "all correct" in txt))):
            if re.search(r"(team\s+stat|score|points|yards|touchdown|goal|assist|rebound)", txt):
                return "sports multi-select"
        if re.search(r"(match|game)\b.*\b(win|loss|outcome|defeat|victory|score)", txt):
            return "sports outcome"
        if re.search(r"\b(beat|defeat|vs\.?|against)\b", txt) and ("\\boxed{" in txt):
            if re.search(r"(soccer|football|hockey|nhl|nba|baseball|mlb|tennis|"
                         r"premier league|champions league|cricket)", txt):
                return "sports outcome"
        if re.search(r"(china|chinese|hsi|csi|hong kong|shanghai|shenzhen|yuan|"
                     r"rmb|cny|hkd|hkex|sse|szse|沪深|上证|深证|港股)", txt):
            if re.search(r"(close|open|high|low|price|index|market cap|stock)", txt):
                return "Chinese finance"
        if re.search(r"(rank|ranking|top\s*\d+|chart|leaderboard|atp|wta)", txt):
            return "ranking"
        if re.search(r"(usd|eur|jpy|gbp|gold|oil|brent|wti|copper|silver|bitcoin|"
                     r"ethereum|crude|s&p|nasdaq|dow|stock|currency|exchange rate)", txt):
            if re.search(r"(price|value|close|high|low|exchange rate)", txt):
                return "value estimation"
        if "\\boxed{" in txt and re.search(r"(\bA\.\s|\boption|listing all correct)", txt):
            return "general multi-select"
        return "default"

    out = {}
    for line in (RESULTS_ROOT / "futurex_navigation" / "results.jsonl").read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        tid = r.get("instance_id") or r.get("task_id")
        m = re.match(r"futurex_past_(\d+)_", tid or "")
        if not m:
            continue
        idx = int(m.group(1))
        if idx >= len(catalog):
            continue
        b = assign(catalog[idx])
        if b is not None:
            out[tid] = b
    return out


# --- Per-cycle per-bin lift -------------------------------------------------
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


def per_bin_per_cycle_lifts(nav: dict, baselines: list[dict],
                             bins: dict[str, str]):
    """Returns {bin_label: {cycle: [lifts]}}."""
    out = defaultdict(lambda: defaultdict(list))
    for tid, nav_row in nav.items():
        if nav_row["cycle"] is None:
            continue
        b = bins.get(tid)
        if b is None:
            continue
        b_scores = [bs[tid]["score"] for bs in baselines if tid in bs]
        if len(b_scores) < 3:
            continue
        med = float(np.median(b_scores))
        out[b][int(nav_row["cycle"])].append(nav_row["score"] - med)
    return out


def cumulative_curve(per_cyc: dict[int, list[float]], cycles: list[int],
                     min_pooled: int = 5):
    """Return (cycle list, cumulative-mean array). Cumulative includes all
    bin-tasks from cycles 1..t, regardless of which cycle they fell in.
    Lines start at the first cycle reaching min_pooled and continue forward
    so all bins share the same final cycle."""
    running = []
    out_x, out_y = [], []
    started = False
    for c in cycles:
        running.extend(per_cyc.get(c, []))
        if not started and len(running) < min_pooled:
            continue
        started = True
        out_x.append(c)
        out_y.append(float(np.mean(running)) if running else 0.0)
    return np.array(out_x), np.array(out_y)


# ---------------------------------------------------------------------------
BENCHES = [
    ("PolyBench", "polybench_navigation",
     ["polybench_baseline", "polybench_full_evo", "polybench_gepa_lite",
      "polybench_mh_lite", "polybench_continual_harness", "polybench_skillos"],
     load_polybench_bins,
     [("post: decided",            "#08306b"),
      ("post: LKP lags OB",        "#2171b5"),
      ("post: stale wide-spread",  "#6baed6"),
      ("pre: decisive OB",         "#cc4444"),
      ("pre: near-50/50",          "#a52a2a"),
      ("pre: mid",                 "#cc9966")],
     (-0.05, 1.0)),
    ("CTF-Dojo", "ctf_dojo_navigation",
     ["ctf_dojo_baseline", "ctf_dojo_full_evo", "ctf_dojo_gepa_lite",
      "ctf_dojo_mh_lite", "ctf_dojo_continual_harness", "ctf_dojo_skillos"],
     load_ctf_bins,
     [("crypto",     "#3a6ea5"),
      ("reversing",  "#1f4e79"),
      ("pwn",        "#7fa5cc"),
      ("forensics",  "#a52a2a"),
      ("misc",       "#cc9966"),
      ("web",        "#666666")],
     (-0.05, 0.40)),
    ("FutureX", "futurex_navigation",
     ["futurex_baseline", "futurex_full_evo", "futurex_gepa_lite",
      "futurex_mh_lite", "futurex_continual_harness", "futurex_skillos"],
     load_futurex_bins,
     [("sports multi-select", "#08306b"),
      ("sports outcome",      "#2171b5"),
      ("Chinese finance",     "#6baed6"),
      ("ranking",             "#cc9966"),
      ("general multi-select","#a52a2a"),
      ("value estimation",    "#cc4444"),
      ("default",             "#666666")],
     (-0.05, 0.45)),
]


def main() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(7.5, 3.2), sharey=False,
                              gridspec_kw={"wspace": 0.16})

    for j, (name, nav_run, baseline_runs, bin_loader,
            bin_palette, ylim) in enumerate(BENCHES):
        ax = axes[j]
        nav = load_run(nav_run)
        bs = [load_run(b) for b in baseline_runs]
        bins = bin_loader()
        per_bin_cyc = per_bin_per_cycle_lifts(nav, bs, bins)

        # Determine the cycle range from the union
        all_cycles = sorted({c for d in per_bin_cyc.values() for c in d})

        bin_color = "#3a6ea5" if j == 0 else ("#a52a2a" if j == 1 else "#cc9966")

        # Pooled (all bins together) cumulative lift -> bold line
        all_per_cyc = defaultdict(list)
        for label, _ in bin_palette:
            for c, v in per_bin_cyc.get(label, {}).items():
                all_per_cyc[c].extend(v)

        # Per-bin cumulative lifts as a (bin x cycle) matrix.
        # At each cycle t we compute quantiles across bins of their cumulative
        # lifts up to t (the heterogeneity across task types at stream-position t).
        bin_cum: dict[str, dict[int, float]] = {}
        for label, _ in bin_palette:
            if label not in per_bin_cyc:
                continue
            x_b, y_b = cumulative_curve(per_bin_cyc[label], all_cycles,
                                        min_pooled=5)
            bin_cum[label] = dict(zip(x_b.tolist(), y_b.tolist()))

        q25, q50, q75, q10, q90 = [], [], [], [], []
        x_q = []
        for c in all_cycles:
            vals = [bin_cum[lbl][c] for lbl in bin_cum if c in bin_cum[lbl]]
            if len(vals) < 3:
                continue
            x_q.append(c)
            q10.append(float(np.percentile(vals, 10)))
            q25.append(float(np.percentile(vals, 25)))
            q50.append(float(np.percentile(vals, 50)))
            q75.append(float(np.percentile(vals, 75)))
            q90.append(float(np.percentile(vals, 90)))

        x_q = np.array(x_q)
        q10, q25, q50, q75, q90 = map(np.array, (q10, q25, q50, q75, q90))

        # Outer band: Q10-Q90 (full heterogeneity range across task types)
        ax.fill_between(x_q, q10, q90, color=bin_color, alpha=0.13,
                        zorder=2)
        # Inner band: Q25-Q75 (interquartile range)
        ax.fill_between(x_q, q25, q75, color=bin_color, alpha=0.30,
                        zorder=3)

        # Bold pooled overall line
        x_p, y_p = cumulative_curve(all_per_cyc, all_cycles, min_pooled=5)
        ax.plot(x_p, y_p, color=bin_color, linewidth=3.2, zorder=4)

        ax.axhline(0, color="#222", linewidth=1.0, linestyle="-", zorder=1)
        ax.set_xlim(min(all_cycles) - 0.6, max(all_cycles) + 0.6)
        ax.set_ylim(*ylim)
        ax.tick_params(axis="both", labelsize=9, pad=2)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.1f}"))
        ax.grid(axis="y", alpha=0.25, linestyle="--", color="#aaa")
        ax.set_axisbelow(True)
        ax.set_title(name, fontsize=12, fontweight="bold", color=bin_color)

        ax.set_xlabel("")

    # Shared legend above the three panels
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    line_handle = [Line2D([0], [0], color="#444", linewidth=3.2,
                           label="task-weighted cumulative lift")]
    band_handles = [
        Patch(facecolor="#444", alpha=0.30,
              label="branch-type Q25--Q75"),
        Patch(facecolor="#444", alpha=0.13,
              label="branch-type Q10--Q90"),
    ]
    leg1 = fig.legend(handles=line_handle,
                      loc="upper center", bbox_to_anchor=(0.5, 1.13),
                      ncol=1, fontsize=14, framealpha=0.95, frameon=False,
                      handletextpad=0.4, handlelength=2.0)
    fig.add_artist(leg1)
    fig.legend(handles=band_handles,
               loc="upper center", bbox_to_anchor=(0.5, 1.06),
               ncol=2, fontsize=14, framealpha=0.95, frameon=False,
               columnspacing=1.2, handletextpad=0.4, handlelength=2.0)

    fig.tight_layout(rect=[0.0, 0.06, 1, 0.93], w_pad=0.2)
    fig.supylabel("cumulative per-task lift",
                  fontsize=16, x=0.012, y=0.55)
    fig.supxlabel("evolver cycle", fontsize=16, y=-0.01)
    fig.subplots_adjust(left=0.08, wspace=0.16, bottom=0.12)

    pdf = OUTPUT / "l_adapt_evidence.pdf"
    png = OUTPUT / "l_adapt_evidence.png"
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, bbox_inches="tight", dpi=150)
    print(f"wrote {pdf}\nwrote {png}")


if __name__ == "__main__":
    main()
