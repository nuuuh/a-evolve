#!/usr/bin/env python3
"""Emit Tables R1 (turns + wall-clock), R2 (per-task tokens), R3 (turn-budget hits).

All stats come from per-task fields in `results.jsonl`. Means are rounded to
sensible precision; medians are reported alongside means because turn/elapsed
distributions are right-skewed on the security and forecasting benchmarks.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

SYSTEMS = [
    ("Sonnet", "baseline"),
    ("A-Evolve", "full_evo"),
    ("GEPA", "gepa_lite"),
    ("Meta-Harness", "mh_lite"),
    ("Continual H.", "continual_harness"),
    ("SkillOS", "skillos"),
    ("OctoTools", "octo_expert"),
    ("Multi-agent", "structured_evo"),
    ("Adaptive", "navigation"),
    ("Full System", "structured_nav"),
]
BENCHES = [("PolyBench", "polybench"), ("CTF-Dojo", "ctf_dojo"), ("FutureX", "futurex")]


def load(bench, suffix):
    p = REPO_ROOT / "results" / f"{bench}_{suffix}" / "results.jsonl"
    if not p.exists():
        return []
    seen, rows = set(), []
    for line in p.read_text().splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("instance_id") in seen:
            continue
        seen.add(r["instance_id"])
        rows.append(r)
    return rows


def stats_turns_time(rows):
    if not rows:
        return None
    # Turns counts non-submit tool calls; we add the submit call when the task
    # completed so that a successful direct-submit task is reported as 1 turn
    # rather than 0.
    turns = [
        (r.get("turns") or 0) + (1 if r.get("submitted") else 0)
        for r in rows
    ]
    elapsed = [r.get("elapsed") or 0 for r in rows]
    return {
        "n": len(rows),
        "avg_turn": statistics.mean(turns),
        "med_turn": statistics.median(turns),
        "avg_sec": statistics.mean(elapsed),
        "med_sec": statistics.median(elapsed),
    }


def stats_tokens(rows):
    if not rows:
        return None
    intok = [r.get("input_tokens") or 0 for r in rows]
    outtok = [r.get("output_tokens") or 0 for r in rows]
    return {
        "n": len(rows),
        "avg_in": statistics.mean(intok),
        "avg_out": statistics.mean(outtok),
        "med_in": statistics.median(intok),
    }


def fmt_int(x):
    return f"{round(x):,}"


def fmt1(x):
    if x is None:
        return "--"
    return f"{x:.1f}"


def fmt_k(x):
    if x is None:
        return "--"
    return f"{x/1000:.1f}k"


def main():
    out_dir = Path(__file__).resolve().parent.parent / "tables"

    # ---- R1: turns + wall-clock ----
    lines = [
        r"\begin{table*}[t]",
        r"\centering\footnotesize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\caption{Per-task solver turns and wall-clock seconds across systems and benchmarks. A \emph{turn} is one tool call, including the final \texttt{submit}; a task that submits directly without other tool use therefore counts as 1. \emph{$\overline{\mathrm{turns}}$} and \emph{$\overline{\mathrm{sec}}$} are arithmetic means; \emph{median} columns are added because both distributions are right-skewed on CTF-Dojo and FutureX. Wall-clock excludes orchestration overhead.}",
        r"\label{tab:run_turns_time}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{@{}l rrrr rrrr rrrr@{}}",
        r"\toprule",
        r"& \multicolumn{4}{c}{PolyBench} & \multicolumn{4}{c}{CTF-Dojo} & \multicolumn{4}{c}{FutureX} \\",
        r"\cmidrule(lr){2-5} \cmidrule(lr){6-9} \cmidrule(lr){10-13}",
        r"System & $\overline{\mathrm{turns}}$ & med & $\overline{\mathrm{sec}}$ & med & $\overline{\mathrm{turns}}$ & med & $\overline{\mathrm{sec}}$ & med & $\overline{\mathrm{turns}}$ & med & $\overline{\mathrm{sec}}$ & med \\",
        r"\midrule",
    ]
    for label, suffix in SYSTEMS:
        cells = [label]
        for _, bench in BENCHES:
            s = stats_turns_time(load(bench, suffix))
            if s is None:
                cells += ["--"] * 4
            else:
                cells += [fmt1(s["avg_turn"]), fmt1(s["med_turn"]),
                          fmt1(s["avg_sec"]), fmt1(s["med_sec"])]
        lines.append(" & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}}", r"\end{table*}"]
    (out_dir / "R1_run_turns_time.tex").write_text("\n".join(lines) + "\n")

    print("Wrote R1", file=sys.stderr)


if __name__ == "__main__":
    main()
