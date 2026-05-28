#!/usr/bin/env python3
"""Emit Table F2: per-domain Pass@1 on FutureX.

FutureX trajectories store the question text but not the official domain
tags. We infer language (en/zh based on Chinese characters in the question)
and a coarse domain bucket from keyword matches. Domain inference is therefore
approximate and is reported alongside the unknown bucket so the row totals
sum to N.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

SYSTEMS = [
    ("Sonnet", "futurex_baseline"),
    ("A-Evolve", "futurex_full_evo"),
    ("Meta-Harness", "futurex_mh_lite"),
    ("Multi-agent", "futurex_structured_evo"),
    ("Adaptive", "futurex_navigation"),
    ("Full System", "futurex_structured_nav"),
]

# Display rows in this order; "other" catches unmatched.
DOMAINS = ["finance", "tech", "geopolitics", "sports", "entertainment", "other"]
DOMAIN_KEYWORDS = {
    "finance": [r"\bstock", r"\bmarket", r"\binflation", r"\binterest rate", r"\bGDP",
                r"\bbond", r"\bUSD", r"\bcurrency", r"\bnasdaq", r"\bdow", r"\bS\&P",
                r"\bcrypto", r"\bbitcoin", r"\bethereum", r"\bprice", r"\brate",
                r"\bfed\b", r"\bbank", r"\beconom"],
    "tech": [r"\bAI\b", r"\bGPU", r"\bchip", r"\bsemiconductor", r"\bsoftware",
             r"\bchatGPT", r"\bopenAI", r"\bgoogle", r"\bapple", r"\bmicrosoft",
             r"\bmodel", r"\btoken", r"\btech stock", r"\biPhone"],
    "geopolitics": [r"\belection", r"\bpresident", r"\bUkraine", r"\bRussia",
                    r"\bIsrael", r"\bGaza", r"\bcongress", r"\bsenate",
                    r"\bdiplom", r"\btreaty", r"\bsanction", r"\bwar"],
    "sports": [r"\bfootball", r"\bsoccer", r"\bbasketball", r"\bNBA", r"\bNFL",
               r"\btennis", r"\bgoal", r"\bmatch", r"\bplayer", r"\bgame",
               r"\bchampion", r"\btournament"],
    "entertainment": [r"\bmovie", r"\bfilm", r"\bbox office", r"\bgrammys?",
                      r"\boscar", r"\bmusic", r"\bchart", r"\balbum",
                      r"\bbroadway", r"\bnetflix"],
}
DOMAIN_REGEX = {d: re.compile("|".join(kws), re.IGNORECASE) for d, kws in DOMAIN_KEYWORDS.items()}


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


def task_text(run_dir: Path, instance_id: str) -> str:
    p = run_dir / f"trajectory_{instance_id}.json"
    if not p.exists():
        return ""
    try:
        d = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return ""
    if isinstance(d, list) and d:
        return str(d[0].get("content", ""))[:2000]
    return ""


def detect_language(text: str) -> str:
    cn_chars = sum(1 for ch in text[:1500] if "一" <= ch <= "鿿")
    return "zh" if cn_chars >= 5 else "en"


def detect_domain(text: str) -> str:
    for domain, regex in DOMAIN_REGEX.items():
        if regex.search(text):
            return domain
    return "other"


def main():
    # Cache classifications using the baseline run's trajectories so that all
    # systems use the same domain assignment.
    baseline = REPO_ROOT / "results" / "futurex_baseline"
    classification: dict[str, tuple[str, str]] = {}
    for r in load_results(baseline / "results.jsonl"):
        text = task_text(baseline, r["instance_id"])
        classification[r["instance_id"]] = (detect_language(text), detect_domain(text))

    # Aggregate.
    n_per_slice = defaultdict(int)
    sys_pass = {label: defaultdict(lambda: [0, 0]) for label, _ in SYSTEMS}

    for label, dirname in SYSTEMS:
        rows = load_results(REPO_ROOT / "results" / dirname / "results.jsonl")
        for r in rows:
            iid = r["instance_id"]
            lang, dom = classification.get(iid, ("en", "other"))
            slice_key = (lang, dom)
            sys_pass[label][slice_key][1] += 1
            if r.get("success"):
                sys_pass[label][slice_key][0] += 1
            if label == "Sonnet":
                n_per_slice[slice_key] += 1

    out = []
    out.append(r"\begin{table}[t]")
    out.append(r"\centering\footnotesize")
    out.append(r"\setlength{\tabcolsep}{4pt}")
    out.append(r"\caption{Per-slice Pass@1 on FutureX. Language is detected from the presence of Chinese characters in the question; domain is inferred by keyword match (\textit{other} catches unmatched questions). N is computed from the Sonnet-baseline run so columns reflect the same task set.}")
    out.append(r"\label{tab:per_domain_futurex}")
    cols = "ll" + "r" + "r" * len(SYSTEMS)
    out.append(r"\begin{tabular}{@{}" + cols + r"@{}}")
    out.append(r"\toprule")
    header = ["Lang", "Domain", "N"] + [s for s, _ in SYSTEMS]
    out.append(" & ".join(header) + r" \\")
    out.append(r"\midrule")

    for lang in ("en", "zh"):
        for dom in DOMAINS:
            key = (lang, dom)
            n = n_per_slice.get(key, 0)
            if n == 0:
                continue
            cells = [lang, dom, str(n)]
            for label, _ in SYSTEMS:
                ok, total = sys_pass[label].get(key, [0, 0])
                cells.append(f"{100 * ok / total:.1f}" if total else "--")
            out.append(" & ".join(cells) + r" \\")
        out.append(r"\midrule")
    # remove trailing midrule before bottomrule
    out = [l for i, l in enumerate(out) if not (i == len(out) - 1 and l == r"\midrule")]

    overall = ["", "Overall", str(sum(n_per_slice.values()))]
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

    target = Path(__file__).resolve().parent.parent / "tables" / "F2_per_domain_futurex.tex"
    target.write_text("\n".join(out) + "\n")
    print(f"Wrote {target}", file=sys.stderr)


if __name__ == "__main__":
    main()
