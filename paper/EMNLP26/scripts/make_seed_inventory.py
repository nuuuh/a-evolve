#!/usr/bin/env python3
"""Emit Table B2: seed harness inventory per benchmark."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
BENCHES = ("polybench", "ctf_dojo", "futurex")
LABELS = {"polybench": "PolyBench", "ctf_dojo": "CTF-Dojo", "futurex": "FutureX"}


def count_lines(p: Path) -> int:
    if not p.exists():
        return 0
    return sum(1 for _ in p.open())


def count_dir(p: Path) -> int:
    if not p.exists() or not p.is_dir():
        return 0
    return sum(1 for child in p.iterdir() if child.name not in {"__init__.py", ".gitkeep"})


def count_tools(p: Path) -> int:
    if not p.exists():
        return 0
    data = yaml.safe_load(p.read_text()) or {}
    tools = data.get("tools", []) or []
    return len(tools)


def main():
    rows = []
    for bench in BENCHES:
        root = REPO_ROOT / "seed_workspaces" / bench
        rows.append((
            LABELS[bench],
            count_lines(root / "prompts/system.md"),
            count_dir(root / "skills"),
            count_tools(root / "tools/registry.yaml"),
            count_lines(root / "memory/memories.jsonl"),
            "yes" if (root / "infra").exists() else "no",
        ))

    out = []
    out.append(r"\begin{table}[t]")
    out.append(r"\centering\footnotesize")
    out.append(r"\setlength{\tabcolsep}{6pt}")
    out.append(r"\caption{Seed harness shipped to the evolver before any cycle runs. \emph{Skills} counts top-level skill directories. \emph{Memory} counts JSONL entries in the seed memory.}")
    out.append(r"\label{tab:seed_inventory}")
    out.append(r"\begin{tabular}{@{}lrrrrl@{}}")
    out.append(r"\toprule")
    out.append(r"Benchmark & Prompt LOC & Skills & Tools & Memory entries & Infra dir \\")
    out.append(r"\midrule")
    for r in rows:
        out.append(" & ".join(str(c) for c in r) + r" \\")
    out.append(r"\bottomrule")
    out.append(r"\end{tabular}")
    out.append(r"\end{table}")

    target = Path(__file__).resolve().parent.parent / "tables" / "B2_seed_inventory.tex"
    target.write_text("\n".join(out) + "\n")
    print(f"Wrote {target}", file=sys.stderr)


if __name__ == "__main__":
    main()
