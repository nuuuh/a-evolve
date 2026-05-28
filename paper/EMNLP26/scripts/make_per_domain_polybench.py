#!/usr/bin/env python3
"""Emit Table F3: per-category Coverage / Acc / CWR / Return on PolyBench.

PolyBench `results.jsonl` does not store the market category; we infer it
from the trajectory prompt's Event/Description text using keyword matches.
Categories are computed once on the Sonnet baseline run and shared across
systems so the same task always lands in the same row.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "evaluations"))
import generate_main_table as gmt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]

SYSTEMS = [
    ("Sonnet", "polybench_baseline"),
    ("A-Evolve", "polybench_full_evo"),
    ("Meta-Harness", "polybench_mh_lite"),
    ("Multi-agent", "polybench_structured_evo"),
    ("Adaptive", "polybench_navigation"),
    ("Full System", "polybench_structured_nav"),
]

DOMAINS = ["politics", "sports", "finance", "crypto", "entertainment", "other"]
DOMAIN_KEYWORDS = {
    "politics": [r"\belection", r"\bpresident", r"\bcongress", r"\bsenate",
                 r"\bgovernor", r"\bsupreme court", r"\bUkraine", r"\bRussia",
                 r"\bGaza", r"\bpoll", r"\bparliament", r"\bbiden", r"\btrump"],
    "sports": [r"\bsuper bowl", r"\bNFL", r"\bNBA", r"\bMLB", r"\bUEFA",
               r"\bchampions league", r"\bworld cup", r"\bolympics?", r"\btennis",
               r"\bgolf", r"\bsoccer", r"\bhockey", r"\bbasketball", r"\bbaseball",
               r"\btournament", r"\bpremier league", r"\bUFC"],
    "finance": [r"\bstock", r"\binflation", r"\bfed\b", r"\bgdp", r"\bjobs report",
                r"\binterest rate", r"\bcpi\b", r"\bdow", r"\bnasdaq",
                r"\bs\&p", r"\beconom", r"\bbank", r"\bcurrency"],
    "crypto": [r"\bbitcoin", r"\bethereum", r"\bcrypto", r"\bsolana",
               r"\bdoge", r"\bBTC\b", r"\bETH\b", r"\bcoinbase",
               r"\bbinance", r"\baltcoin"],
    "entertainment": [r"\bmovie", r"\bbox office", r"\bgrammys?", r"\boscar",
                      r"\bemmy", r"\bbillboard", r"\bsong of the year",
                      r"\btaylor swift", r"\bmusic", r"\bnetflix",
                      r"\bbroadway", r"\btv\b"],
}
DOMAIN_REGEX = {d: re.compile("|".join(kws), re.IGNORECASE) for d, kws in DOMAIN_KEYWORDS.items()}


def trajectory_text(run_dir: Path, instance_id: str) -> str:
    p = run_dir / f"trajectory_{instance_id}.json"
    if not p.exists():
        return ""
    try:
        d = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return ""
    if isinstance(d, list) and d:
        return str(d[0].get("content", ""))[:1500]
    return ""


def detect_domain(text: str) -> str:
    for domain, regex in DOMAIN_REGEX.items():
        if regex.search(text):
            return domain
    return "other"


def main():
    baseline = REPO_ROOT / "results" / "polybench_baseline"
    classification = {}
    print("Building category index from baseline trajectories...", file=sys.stderr)
    for r in gmt.load_results(baseline / "results.jsonl"):
        text = trajectory_text(baseline, r["instance_id"])
        classification[r["instance_id"]] = detect_domain(text)

    n_per_domain = defaultdict(int)
    for cat in classification.values():
        n_per_domain[cat] += 1

    # Compute polybench metrics per slice for each system.
    print("Computing per-slice metrics...", file=sys.stderr)
    sys_metrics = {}  # label -> {domain -> dict of metrics}
    for label, dirname in SYSTEMS:
        run_dir = REPO_ROOT / "results" / dirname
        rows = gmt.load_results(run_dir / "results.jsonl")
        per_dom = defaultdict(list)
        for r in rows:
            cat = classification.get(r["instance_id"], "other")
            per_dom[cat].append(r)
        slice_metrics = {}
        for dom in DOMAINS + ["all"]:
            if dom == "all":
                slice_rows = rows
            else:
                slice_rows = per_dom.get(dom, [])
            if not slice_rows:
                slice_metrics[dom] = None
                continue
            # Mimic gmt.polybench_metrics but on a sliced row set with
            # the local total for accuracy/coverage.
            traded = [
                row for row in slice_rows
                if not row.get("gated")
                and gmt._norm_label(row.get("decision")) not in {"SKIP", ""}
            ]
            correct = [row for row in traded if row.get("success")]
            cwr_inv = sum(float(row.get("cwr_investment") or 0.0) for row in traded)
            cwr_profit = sum(float(row.get("cwr_profit") or 0.0) for row in traded)
            n_total = len(slice_rows)
            coverage = 100.0 * len(traded) / n_total if n_total else 0.0
            acc = 100.0 * len(correct) / n_total if n_total else 0.0
            cwr_pct = 100.0 * cwr_profit / cwr_inv if cwr_inv else 0.0
            slice_metrics[dom] = {
                "coverage": coverage,
                "acc": acc,
                "cwr": cwr_pct,
                "return": coverage * cwr_pct / 100.0,
                "n": n_total,
            }
        sys_metrics[label] = slice_metrics

    # Emit a tall format: rows are (domain) and columns group by system.
    out = []
    out.append(r"\begin{table*}[t]")
    out.append(r"\centering\footnotesize")
    out.append(r"\setlength{\tabcolsep}{3pt}")
    out.append(r"\caption{Per-category PolyBench metrics. Categories are inferred by keyword match on the trajectory prompt's Event description; \textit{other} catches unmatched markets. Each cell reports Accuracy / Return; full Coverage and CWR are available in the released artifacts.}")
    out.append(r"\label{tab:per_domain_polybench}")
    cols = "lr" + "c" * len(SYSTEMS)
    out.append(r"\begin{tabular}{@{}" + cols + r"@{}}")
    out.append(r"\toprule")
    out.append(" & ".join(["Domain", "N"] + [s for s, _ in SYSTEMS]) + r" \\")
    out.append(r"\midrule")
    for dom in DOMAINS:
        n = n_per_domain.get(dom, 0)
        if n == 0:
            continue
        cells = [dom, str(n)]
        for label, _ in SYSTEMS:
            m = sys_metrics[label].get(dom)
            if m is None:
                cells.append("--")
            else:
                cells.append(f"{m['acc']:.1f}/{m['return']:+.0f}")
        out.append(" & ".join(cells) + r" \\")
    out.append(r"\midrule")
    overall = ["Overall", str(sum(n_per_domain.values()))]
    for label, _ in SYSTEMS:
        m = sys_metrics[label].get("all")
        overall.append(f"{m['acc']:.1f}/{m['return']:+.0f}" if m else "--")
    out.append(" & ".join(overall) + r" \\")
    out.append(r"\bottomrule")
    out.append(r"\end{tabular}")
    out.append(r"\end{table*}")

    target = Path(__file__).resolve().parent.parent / "tables" / "F3_per_domain_polybench.tex"
    target.write_text("\n".join(out) + "\n")
    print(f"Wrote {target}", file=sys.stderr)


if __name__ == "__main__":
    main()
