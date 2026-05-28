#!/usr/bin/env python3
"""Emit the hyperparameter table (Table B1) by reading per-benchmark configs."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG = {
    "polybench": REPO_ROOT / "experiments/polybench/configs/structured_navigation_evo.yaml",
    "ctf_dojo": REPO_ROOT / "experiments/ctf_dojo/configs/structured_navigation_evo.yaml",
    "futurex": REPO_ROOT / "experiments/futurex/configs/structured_navigation_evo.yaml",
}

PAPER_BATCH = {"polybench": 100, "ctf_dojo": 20, "futurex": 20}
PAPER_CYCLES = {"polybench": 51, "ctf_dojo": 14, "futurex": 26}
PAPER_TASKS = {"polybench": 5075, "ctf_dojo": 261, "futurex": 503}
SOLVER_MAX_TURNS = {"polybench": 80, "ctf_dojo": 80, "futurex": 80}
SOLVER_TEMP = 0.0
EVOLVER_TEMP = 0.0
ROUTING_CONFIDENCE = 0.7
ROUTER_MODEL = "Sonnet 4.6"


def fmt(value):
    return value if value not in (None, "") else "--"


def main():
    cfg = {b: yaml.safe_load(p.read_text()) for b, p in CONFIG.items()}

    rows = [
        ("Solver model", "Sonnet 4.6", "Sonnet 4.6", "Sonnet 4.6"),
        ("Evolver model", "Opus 4.6", "Opus 4.6", "Opus 4.6"),
        ("Router model", ROUTER_MODEL, ROUTER_MODEL, ROUTER_MODEL),
        ("Solver temperature", SOLVER_TEMP, SOLVER_TEMP, SOLVER_TEMP),
        ("Evolver temperature", EVOLVER_TEMP, EVOLVER_TEMP, EVOLVER_TEMP),
        ("Solver max turns", *(SOLVER_MAX_TURNS[b] for b in CONFIG)),
        ("Evolver max tokens", *(cfg[b].get("evolver_max_tokens", "--") for b in CONFIG)),
        ("Batch size", *(PAPER_BATCH[b] for b in CONFIG)),
        ("Total tasks", *(PAPER_TASKS[b] for b in CONFIG)),
        ("Evolution cycles", *(PAPER_CYCLES[b] for b in CONFIG)),
        ("EGL trigger threshold", *(cfg[b].get("egl_threshold", "--") for b in CONFIG)),
        ("EGL window", *(cfg[b].get("egl_window", "--") for b in CONFIG)),
        ("Solve workers", *(cfg[b].get("solve_workers", "--") for b in CONFIG)),
        ("Routing confidence threshold",
         *(cfg[b].get("branch_confidence", ROUTING_CONFIDENCE) for b in CONFIG)),
        ("Research parallel agents",
         *(cfg[b].get("structured_evolution", {}).get("research_parallel", "--") for b in CONFIG)),
        ("Build/verify retries",
         *(cfg[b].get("structured_evolution", {}).get("build_verify_retries", "--") for b in CONFIG)),
        ("Solver sandbox network",
         *(cfg[b].get("sandbox_network", "--") for b in CONFIG)),
        ("Evolver sandbox network",
         *(cfg[b].get("evolver_sandbox_network", "--") for b in CONFIG)),
    ]

    out = []
    out.append(r"\begin{table}[t]")
    out.append(r"\centering\footnotesize")
    out.append(r"\setlength{\tabcolsep}{4pt}")
    out.append(r"\caption{Adaptive Auto-Harness hyperparameters across the three benchmarks.}")
    out.append(r"\label{tab:hyperparams}")
    out.append(r"\begin{tabular}{@{}lccc@{}}")
    out.append(r"\toprule")
    out.append(r"Hyperparameter & PolyBench & CTF-Dojo & FutureX \\")
    out.append(r"\midrule")
    for r in rows:
        out.append(" & ".join(str(fmt(c)) for c in r) + r" \\")
    out.append(r"\bottomrule")
    out.append(r"\end{tabular}")
    out.append(r"\end{table}")

    target = Path(__file__).resolve().parent.parent / "tables" / "B1_hyperparameters.tex"
    target.write_text("\n".join(out) + "\n")
    print(f"Wrote {target}", file=sys.stderr)


if __name__ == "__main__":
    main()
