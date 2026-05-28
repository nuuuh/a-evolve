#!/usr/bin/env python3
"""Emit Table H1: per-branch routing volume and pass rate for the Adaptive
(navigation-only) and Full System (structured_nav) variants on each benchmark."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

VARIANTS = [
    ("Adaptive", "navigation"),
    ("Full System", "structured_nav"),
]
BENCHES = [("PolyBench", "polybench"), ("CTF-Dojo", "ctf_dojo"), ("FutureX", "futurex")]


def load_routing(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def main():
    rows_out = []
    for bench_label, bench in BENCHES:
        for variant_label, suffix in VARIANTS:
            log = load_routing(REPO_ROOT / "results" / f"{bench}_{suffix}" / "routing_log.jsonl")
            if not log:
                continue
            counts = Counter()
            succ = Counter()
            for r in log:
                b = r.get("branch", "?")
                counts[b] += 1
                if r.get("success"):
                    succ[b] += 1
            for branch, n in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
                pass_rate = 100 * succ[branch] / n if n else 0
                rows_out.append((bench_label, variant_label, branch, n, pass_rate))

    out = []
    out.append(r"\begin{table}[t]")
    out.append(r"\centering\footnotesize")
    out.append(r"\setlength{\tabcolsep}{4pt}")
    out.append(r"\caption{Per-branch routing volume and pass rate from \texttt{routing\_log.jsonl}. \emph{Adaptive} runs the solve-time router over a navigation-only evolved tree; \emph{Full System} pairs the router with the multi-agent evolver. The pass column reports Pass@1 on tasks routed to that branch (CTF-Dojo, FutureX) or accuracy among traded markets (PolyBench).}")
    out.append(r"\label{tab:branch_perf}")
    out.append(r"\begin{tabular}{@{}lllrr@{}}")
    out.append(r"\toprule")
    out.append(r"Benchmark & Variant & Branch & N routed & Pass / Acc \\")
    out.append(r"\midrule")

    last_bench = None
    last_variant = None
    for bench_label, variant_label, branch, n, pass_rate in rows_out:
        bcell = bench_label if bench_label != last_bench else ""
        vcell = variant_label if (bench_label != last_bench or variant_label != last_variant) else ""
        out.append(f"{bcell} & {vcell} & \\texttt{{{branch}}} & {n} & {pass_rate:.1f} \\\\")
        last_bench, last_variant = bench_label, variant_label

    out.append(r"\bottomrule")
    out.append(r"\end{tabular}")
    out.append(r"\end{table}")

    target = Path(__file__).resolve().parent.parent / "tables" / "H1_branch_perf.tex"
    target.write_text("\n".join(out) + "\n")
    print(f"Wrote {target}", file=sys.stderr)


if __name__ == "__main__":
    main()
