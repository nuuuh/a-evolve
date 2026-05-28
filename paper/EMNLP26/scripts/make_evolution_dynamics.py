#!/usr/bin/env python3
"""Emit Table G1: numeric companion to Figure rq2 (multi-agent dynamics).

Reports the headline metric for the no-evolution baseline, the single-agent
evolver (A-Evolve), and the multi-agent evolver, plus the cycle count and
the cycle index where the running mean peaked.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "evaluations"))
import generate_main_table as gmt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]

CONFIGS = [
    ("PolyBench", "polybench_baseline", "polybench_full_evo", "polybench_structured_evo", "Acc"),
    ("CTF-Dojo",  "ctf_dojo_baseline",  "ctf_dojo_full_evo",  "ctf_dojo_structured_evo",  "Pass@1"),
    ("FutureX",   "futurex_baseline",   "futurex_full_evo",   "futurex_structured_evo",   "Pass@1"),
]


def acc(rows):
    if not rows:
        return None
    return 100.0 * sum(1 for r in rows if r.get("success")) / len(rows)


def per_cycle_mean(rows):
    """Return list of cumulative pass-rate by cycle index."""
    by_cycle = {}
    for r in rows:
        c = r.get("evo_cycle", 0)
        by_cycle.setdefault(c, []).append(r)
    out = []
    cumulative_total, cumulative_succ = 0, 0
    for c in sorted(by_cycle.keys()):
        for r in by_cycle[c]:
            cumulative_total += 1
            cumulative_succ += int(bool(r.get("success")))
        out.append((c, 100.0 * cumulative_succ / cumulative_total if cumulative_total else 0.0))
    return out


def peak_cycle(rows):
    pc = per_cycle_mean(rows)
    if not pc:
        return None, None
    best_cycle, best_val = max(pc, key=lambda x: x[1])
    return best_cycle, best_val


def cycles_run(rows):
    if not rows:
        return None
    return max(r.get("evo_cycle", 0) for r in rows)


def main():
    out = []
    out.append(r"\begin{table}[t]")
    out.append(r"\centering\footnotesize")
    out.append(r"\setlength{\tabcolsep}{4pt}")
    out.append(r"\caption{Numeric companion to Figure~\ref{fig:rq2_stats}. \emph{No-evo} is the no-evolution Sonnet baseline; \emph{Single-agent} is A-Evolve; \emph{Multi-agent} is the four-phase evolver. \emph{Peak} is the cycle index at which the cumulative mean of the multi-agent run was highest, and \emph{Final} is the cumulative mean at the last cycle. The PolyBench cells use Accuracy (\%); CTF-Dojo and FutureX use Pass@1 (\%).}")
    out.append(r"\label{tab:evolution_dynamics}")
    out.append(r"\begin{tabular}{@{}lrrrrrr@{}}")
    out.append(r"\toprule")
    out.append(r"Benchmark & Metric & No-evo & Single-agent & Multi-agent & Peak cycle & Cycles run \\")
    out.append(r"\midrule")

    for bench, base, single, multi, metric in CONFIGS:
        base_rows = gmt.load_results(REPO_ROOT / "results" / base / "results.jsonl")
        single_rows = gmt.load_results(REPO_ROOT / "results" / single / "results.jsonl")
        multi_rows = gmt.load_results(REPO_ROOT / "results" / multi / "results.jsonl")
        base_v = acc(base_rows)
        single_v = acc(single_rows)
        multi_v = acc(multi_rows)
        pc_idx, _ = peak_cycle(multi_rows)
        ncycles = cycles_run(multi_rows)
        cells = [
            bench, metric,
            f"{base_v:.1f}" if base_v is not None else "--",
            f"{single_v:.1f}" if single_v is not None else "--",
            f"{multi_v:.1f}" if multi_v is not None else "--",
            str(pc_idx) if pc_idx is not None else "--",
            str(ncycles) if ncycles is not None else "--",
        ]
        out.append(" & ".join(cells) + r" \\")

    out.append(r"\bottomrule")
    out.append(r"\end{tabular}")
    out.append(r"\end{table}")

    target = Path(__file__).resolve().parent.parent / "tables" / "G1_evolution_dynamics.tex"
    target.write_text("\n".join(out) + "\n")
    print(f"Wrote {target}", file=sys.stderr)


if __name__ == "__main__":
    main()
