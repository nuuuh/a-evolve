#!/usr/bin/env python3
"""Emit Table F1: per-CTF-Dojo-category pass rates across systems.

Categories are parsed from the `detail` field. Pass rate uses the first
record per `instance_id` to match the rest of the paper.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

SYSTEMS = [
    ("Sonnet", "ctf_dojo_baseline"),
    ("A-Evolve", "ctf_dojo_full_evo"),
    ("Meta-Harness", "ctf_dojo_mh_lite"),
    ("Multi-agent", "ctf_dojo_structured_evo"),
    ("Adaptive", "ctf_dojo_navigation"),
    ("Full System", "ctf_dojo_structured_nav"),
]

# Conventional CTF category set + a misc bucket for everything else.
CANONICAL = ("crypto", "binary", "pwn", "web", "reverse", "rev", "forensics", "misc")
DISPLAY_ORDER = ["crypto", "binary/pwn", "web", "reverse", "forensics", "misc"]


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


def categorise(row: dict) -> str:
    detail = row.get("detail") or ""
    m = re.search(r"\((\w+)\)\s*$", detail)
    raw = (m.group(1).lower() if m else "")
    if raw in {"binary", "pwn"}:
        return "binary/pwn"
    if raw in {"reverse", "rev"}:
        return "reverse"
    if raw in {"crypto", "web", "forensics", "misc"}:
        return raw
    return "misc"


def main():
    # Canonical N per category is taken from the Sonnet baseline (every task ran).
    cat_n = defaultdict(int)
    sys_pass = {label: defaultdict(lambda: [0, 0]) for label, _ in SYSTEMS}

    for label, dirname in SYSTEMS:
        rows = load_results(REPO_ROOT / "results" / dirname / "results.jsonl")
        for r in rows:
            cat = categorise(r)
            sys_pass[label][cat][1] += 1
            if r.get("success"):
                sys_pass[label][cat][0] += 1
            if label == "Sonnet":
                cat_n[cat] += 1

    out = []
    out.append(r"\begin{table}[t]")
    out.append(r"\centering\footnotesize")
    out.append(r"\setlength{\tabcolsep}{4pt}")
    out.append(r"\caption{Per-category Pass@1 on CTF-Dojo. Categories are parsed from the \texttt{detail} field of each result row; \emph{binary/pwn} merges the conventionally-equivalent CTF tags.}")
    out.append(r"\label{tab:per_domain_ctf}")
    cols = "l" + "r" + "r" * len(SYSTEMS)
    out.append(r"\begin{tabular}{@{}" + cols + r"@{}}")
    out.append(r"\toprule")
    header = ["Category", "N"] + [s for s, _ in SYSTEMS]
    out.append(" & ".join(header) + r" \\")
    out.append(r"\midrule")
    for cat in DISPLAY_ORDER:
        n = cat_n.get(cat, 0)
        if n == 0:
            continue
        cells = [cat, str(n)]
        for label, _ in SYSTEMS:
            ok, total = sys_pass[label].get(cat, [0, 0])
            cells.append(f"{100 * ok / total:.1f}" if total else "--")
        out.append(" & ".join(cells) + r" \\")

    # Overall row
    out.append(r"\midrule")
    overall = ["Overall", str(sum(cat_n.values()))]
    for label, dirname in SYSTEMS:
        rows = load_results(REPO_ROOT / "results" / dirname / "results.jsonl")
        if rows:
            overall.append(f"{100 * sum(1 for r in rows if r.get('success')) / len(rows):.1f}")
        else:
            overall.append("--")
    out.append(" & ".join(overall) + r" \\")

    out.append(r"\bottomrule")
    out.append(r"\end{tabular}")
    out.append(r"\end{table}")

    target = Path(__file__).resolve().parent.parent / "tables" / "F1_per_domain_ctf.tex"
    target.write_text("\n".join(out) + "\n")
    print(f"Wrote {target}", file=sys.stderr)


if __name__ == "__main__":
    main()
