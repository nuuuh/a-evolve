#!/usr/bin/env python3
"""Emit Table I1: solver and evolver token cost + wall-clock per system.

Per-task tokens come from results.jsonl rows. Evolver tokens are summed
from the evolver workspace's evolution/observations/* batch records when
present, otherwise reported as ``--``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

# (label, results-dir-prefix). dirs = {pb, ctf, fx}
SYSTEMS = [
    ("Sonnet (no-evo)", "polybench_baseline", "ctf_dojo_baseline", "futurex_baseline"),
    ("A-Evolve", "polybench_full_evo", "ctf_dojo_full_evo", "futurex_full_evo"),
    ("Meta-Harness", "polybench_mh_lite", "ctf_dojo_mh_lite", "futurex_mh_lite"),
    ("Multi-agent", "polybench_structured_evo", "ctf_dojo_structured_evo", "futurex_structured_evo"),
    ("Full System", "polybench_structured_nav", "ctf_dojo_structured_nav", "futurex_structured_nav"),
]
BENCH_LABELS = ["PolyBench", "CTF-Dojo", "FutureX"]
N_TASKS = {"PolyBench": 5075, "CTF-Dojo": 261, "FutureX": 503}


def load_results(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows, seen = [], set()
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        iid = row.get("instance_id", "")
        if iid in seen:
            continue
        seen.add(iid)
        rows.append(row)
    return rows


def solver_totals(results_dir: Path) -> tuple[float, float, float, int]:
    rows = load_results(results_dir / "results.jsonl")
    if not rows:
        return 0.0, 0.0, 0.0, 0
    in_tok = sum(r.get("input_tokens") or 0 for r in rows)
    out_tok = sum(r.get("output_tokens") or 0 for r in rows)
    elapsed = sum(r.get("elapsed") or 0 for r in rows)
    return in_tok / 1e6, out_tok / 1e6, elapsed / 3600.0, len(rows)


def evolver_totals(results_dir: Path) -> tuple[float, float]:
    """Sum evolver-side tokens from evolution/observations/*.jsonl if present.

    Each batch record may contain a top-level ``evolver_tokens`` summary
    written by the orchestrator. If absent we return zeros.
    """
    obs_dir = results_dir / "evolver_workspace" / "evolution" / "observations"
    if not obs_dir.exists():
        return 0.0, 0.0
    in_tot, out_tot = 0, 0
    for batch_file in sorted(obs_dir.glob("batch_*.jsonl")):
        for line in batch_file.read_text().splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            tok = row.get("evolver_tokens") or row.get("tokens") or {}
            if isinstance(tok, dict):
                in_tot += tok.get("input", 0) or 0
                out_tot += tok.get("output", 0) or 0
    return in_tot / 1e6, out_tot / 1e6


def fmt(x, dp=1):
    if x is None:
        return "--"
    if x == 0:
        return "0"
    return f"{x:.{dp}f}"


def main():
    out = []
    out.append(r"\begin{table*}[t]")
    out.append(r"\centering\footnotesize")
    out.append(r"\setlength{\tabcolsep}{4pt}")
    out.append(r"\caption{Solver and evolver token cost and wall-clock per system. Solver tokens are summed across the per-task \texttt{input\_tokens} / \texttt{output\_tokens} fields in \texttt{results.jsonl}; evolver tokens are summed from the cycle-level evolution observations when recorded by the orchestrator (\texttt{--} otherwise). Wall-clock is the sum of per-task \texttt{elapsed} seconds and excludes orchestration overhead.}")
    out.append(r"\label{tab:cost}")
    out.append(r"\begin{tabular}{@{}llrrrrrr@{}}")
    out.append(r"\toprule")
    out.append(r"System & Bench & \makecell{Solver in\\(M-tok)} & \makecell{Solver out\\(M-tok)} & \makecell{Evolver in\\(M-tok)} & \makecell{Evolver out\\(M-tok)} & \makecell{Solver\\hours} & \makecell{Tasks/\\hour} \\")
    out.append(r"\midrule")

    for sys_label, pb_dir, ctf_dir, fx_dir in SYSTEMS:
        for bench_label, dirname in zip(BENCH_LABELS, [pb_dir, ctf_dir, fx_dir]):
            run_dir = REPO_ROOT / "results" / dirname
            sin, sout, hours, n = solver_totals(run_dir)
            ein, eout = evolver_totals(run_dir)
            tasks_per_hr = (n / hours) if hours > 0 else None
            cells = [
                sys_label,
                bench_label,
                fmt(sin),
                fmt(sout, 2),
                fmt(ein) if ein > 0 else "--",
                fmt(eout, 2) if eout > 0 else "--",
                fmt(hours),
                fmt(tasks_per_hr) if tasks_per_hr else "--",
            ]
            out.append(" & ".join(cells) + r" \\")
        out.append(r"\midrule")
    # remove trailing midrule
    out = [l for i, l in enumerate(out) if not (i == len(out) - 1 and l == r"\midrule")]
    out.append(r"\bottomrule")
    out.append(r"\end{tabular}")
    out.append(r"\end{table*}")

    target = Path(__file__).resolve().parent.parent / "tables" / "I1_cost.tex"
    target.write_text("\n".join(out) + "\n")
    print(f"Wrote {target}", file=sys.stderr)


if __name__ == "__main__":
    main()
