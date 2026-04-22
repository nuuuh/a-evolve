#!/usr/bin/env python3
"""Comprehensive analysis of A-Evolve-V2 PolyBench experiments.

Auto-discovers polybench experiments from the results directory. Outputs
Markdown and automatically writes to report.md alongside this script.

Usage:
    python evaluations/analysis_poly/analyze_all.py
    python evaluations/analysis_poly/analyze_all.py --path results
    python evaluations/analysis_poly/analyze_all.py --path results --baseline polybench_baseline
"""
from __future__ import annotations

import argparse
import json
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPORT_PATH = SCRIPT_DIR / "report.md"


# -- Discovery ----------------------------------------------------------------

def _load_experiment_config(name: str) -> dict:
    """Try to load the YAML config for an experiment from experiments/polybench/configs/."""
    import yaml
    for p in [
        Path("experiments/polybench/configs") / f"{name}.yaml",
        Path("experiments/polybench/configs") / f"{name.replace('polybench_', '')}.yaml",
    ]:
        if p.exists():
            with open(p) as f:
                return yaml.safe_load(f) or {}
    return {}


def discover_experiments(
    results_root: Path, baseline_name: str | None = None,
) -> dict[str, dict]:
    experiments = {}
    for d in sorted(results_root.iterdir()):
        if not d.is_dir() or not d.name.startswith("polybench_"):
            continue
        if not (d / "results.jsonl").exists():
            continue
        name = d.name
        hist = _load_history(results_root, name)
        has_evo = any(not h.get("skipped", True) for h in hist)
        batch_totals = [h.get("batch_total", 0) for h in hist if h.get("batch_total")]
        batch_size = max(set(batch_totals), key=batch_totals.count) if batch_totals else 10
        cfg = _load_experiment_config(name)
        has_evo_config = cfg.get("evo_start_after_pct", 0) > 0 or cfg.get("evo_freeze_after_pct", 0) > 0
        if baseline_name:
            is_baseline = name == baseline_name
        else:
            is_baseline = (bool(hist) and all(h.get("skipped", True) for h in hist)
                           and not has_evo_config)
        experiments[name] = {
            "label": name.replace("polybench_", ""),
            "has_evo": has_evo,
            "is_baseline": is_baseline,
            "batch_size": batch_size,
            "evo_start_after_pct": cfg.get("evo_start_after_pct", 0),
        }
    return experiments


def _get_baseline_name(experiments: dict[str, dict]) -> str | None:
    for name, meta in experiments.items():
        if meta["is_baseline"]:
            return name
    return None


# -- Helpers ------------------------------------------------------------------

def _load_history(results_root: Path, name: str) -> list[dict]:
    """Load history.jsonl, checking both new (out_dir/) and old (ws/evolution/) paths."""
    for p in [
        results_root / name / "history.jsonl",
        results_root / name / "polybench" / "evolution" / "history.jsonl",
    ]:
        rows = load_jsonl(p)
        if rows:
            return _dedup_history(rows)
    return []


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for line in path.read_text().splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def _dedup_history(hist: list[dict]) -> list[dict]:
    """Keep last history entry per cycle (handles resume duplicates)."""
    seen: dict[int, dict] = {}
    for h in hist:
        seen[h.get("cycle", 0)] = h
    return sorted(seen.values(), key=lambda h: h.get("cycle", 0))


def _dedup_results(results: list[dict]) -> list[dict]:
    """Keep last result per instance_id."""
    seen: dict[str, dict] = {}
    for r in results:
        seen[r["instance_id"]] = r
    return list(seen.values())


def _load_results(results_root: Path, name: str) -> list[dict]:
    return _dedup_results(load_jsonl(results_root / name / "results.jsonl"))


def _common_task_ids(results_root: Path, experiments: dict[str, dict]) -> set[str]:
    """Task IDs present in ALL experiments."""
    all_sets = []
    for name in experiments:
        results = _load_results(results_root, name)
        all_sets.append({r["instance_id"] for r in results})
    return set.intersection(*all_sets) if all_sets else set()


def count_workspace_artifacts(ws: Path) -> dict[str, Any]:
    skills = list((ws / "skills").iterdir()) if (ws / "skills").is_dir() else []
    skill_names = [s.name for s in skills if s.is_dir()]
    tools_dir = ws / "tools"
    tool_files = [f for f in tools_dir.iterdir() if f.suffix in (".py", ".sh")] if tools_dir.is_dir() else []
    mem_files = list((ws / "memory").glob("*.jsonl")) if (ws / "memory").is_dir() else []
    mem_count = sum(1 for f in mem_files for line in f.read_text().splitlines() if line.strip())
    prompt = ws / "prompts" / "system.md"
    prompt_chars = prompt.stat().st_size if prompt.exists() else 0
    return {
        "skills": len(skill_names), "skill_names": skill_names,
        "tools": len(tool_files), "tool_names": [f.stem for f in tool_files],
        "memories": mem_count, "prompt_chars": prompt_chars,
    }


def _count_artifacts_at_tag(ws: Path, tag: str) -> dict:
    def git(*args):
        r = subprocess.run(
            ["git", "-C", str(ws)] + list(args), capture_output=True, text=True,
        )
        return r.stdout.strip()

    tree = git("ls-tree", "-d", "--name-only", tag, "skills/")
    skills = len([l for l in tree.splitlines() if l.strip()]) if tree else 0
    tree = git("ls-tree", "--name-only", tag, "tools/")
    tools = len([l for l in tree.splitlines()
                 if l.strip() and (l.endswith(".py") or l.endswith(".sh"))]) if tree else 0
    memos = 0
    mem_tree = git("ls-tree", "--name-only", tag, "memory/")
    if mem_tree:
        for f in mem_tree.splitlines():
            if f.endswith(".jsonl"):
                content = git("show", f"{tag}:{f}")
                memos += len([l for l in content.splitlines() if l.strip()])
    prompt = git("show", f"{tag}:prompts/system.md")
    prompt_len = len(prompt) if prompt else 0
    return {"skills": skills, "tools": tools, "memos": memos, "prompt": prompt_len}


def _compute_official_metrics(results: list[dict]) -> dict[str, Any]:
    """Compute official PolyBench metrics from per-task result dicts.

    Returns dict with: accuracy, f1, ece, non_cwr_return, cwr_return,
    avg_apy, sharpe, avg_conf, n_traded.
    Matches evaluate_mimo.py methodology.
    """
    # Filter to traded (non-gated, non-skip) predictions
    traded = [r for r in results
              if not r.get("gated") and r.get("decision", "").upper() not in ("SKIP", "")]
    n = len(traded)
    if n == 0:
        return {k: 0.0 for k in (
            "accuracy", "f1", "ece", "non_cwr_return", "cwr_return",
            "avg_apy", "sharpe", "avg_conf", "n_traded",
        )}

    correct = [1 if r.get("is_correct") or r.get("success") else 0 for r in traded]
    confs = [r.get("confidence", 0.5) for r in traded]
    y_pred = [1 if r.get("decision", "").upper() == "BUY" else 0 for r in traded]

    accuracy = sum(correct) / n

    # F1
    tp = sum(1 for c, p in zip(correct, y_pred) if c == 1 and p == 1)
    fp = sum(1 for c, p in zip(correct, y_pred) if c == 0 and p == 1)
    fn = sum(1 for c, p in zip(correct, y_pred) if c == 1 and p == 0)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0

    # ECE (10-bin)
    bins = 10
    ece = 0.0
    for i in range(bins):
        lo, hi = i / bins, (i + 1) / bins
        in_bin = [j for j, c in enumerate(confs) if lo <= c <= hi]
        if not in_bin:
            continue
        bin_acc = sum(correct[j] for j in in_bin) / len(in_bin)
        bin_conf = sum(confs[j] for j in in_bin) / len(in_bin)
        ece += (len(in_bin) / n) * abs(bin_acc - bin_conf)

    # Returns
    raw_returns = [r["raw_return"] for r in traded if "raw_return" in r]
    non_cwr_ret = sum(raw_returns) / len(raw_returns) if raw_returns else 0.0
    cwr_inv = sum(r.get("cwr_investment", 0.0) for r in traded)
    cwr_profit = sum(r.get("cwr_profit", 0.0) for r in traded)
    cwr_ret = cwr_profit / cwr_inv if cwr_inv > 0 else 0.0

    # APY + Sharpe
    apys = [r["apy"] for r in traded if r.get("apy") is not None]
    avg_apy = sum(apys) / len(apys) if apys else 0.0
    if len(apys) >= 2:
        m = sum(apys) / len(apys)
        s = (sum((x - m) ** 2 for x in apys) / (len(apys) - 1)) ** 0.5
        sharpe = m / s if s > 0 else 0.0
    else:
        sharpe = 0.0

    return {
        "accuracy": accuracy, "f1": f1, "ece": ece,
        "non_cwr_return": non_cwr_ret, "cwr_return": cwr_ret,
        "avg_apy": avg_apy, "sharpe": sharpe,
        "avg_conf": sum(confs) / n, "n_traded": n,
    }


def _md_table(
    headers: list[str], rows: list[list[str]], align: list[str] | None = None,
) -> list[str]:
    if not align:
        align = ["l"] * len(headers)
    sep = []
    for a in align:
        if a == "r":
            sep.append("---:")
        elif a == "c":
            sep.append(":---:")
        else:
            sep.append("---")
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(sep) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return lines


# -- Analysis sections --------------------------------------------------------

def section_summary(results_root: Path, experiments: dict[str, dict]) -> list[str]:
    """Transposed summary: metrics as rows, experiments as columns."""
    # Collect stats per experiment
    cols: list[tuple[str, dict[str, str]]] = []
    for name, meta in experiments.items():
        results = _load_results(results_root, name)
        traded = [r for r in results
                  if not r.get("gated") and r.get("decision", "").upper() not in ("SKIP", "")]
        correct = [r for r in traded if r.get("success") or r.get("is_correct")]
        gated = sum(1 for r in results if r.get("gated"))
        skips = sum(1 for r in results
                    if r.get("decision", "").upper() == "SKIP" and not r.get("gated"))

        # Financial
        cwr_inv = sum(r.get("cwr_investment", 0) for r in traded)
        cwr_prof = sum(r.get("cwr_profit", 0) for r in traded)
        raw_rets = [r["raw_return"] for r in traded if "raw_return" in r]
        apys = [r["apy"] for r in traded if r.get("apy") is not None]

        # Agent behaviour
        turns = [r.get("turns", 0) for r in results if r.get("turns")]
        elapsed = [r.get("elapsed", 0) for r in results if r.get("elapsed")]
        in_tok = [r.get("input_tokens", 0) for r in results if r.get("input_tokens")]
        out_tok = [r.get("output_tokens", 0) for r in results if r.get("output_tokens")]
        confs = [r.get("confidence", 0) for r in traded]

        # Evolution
        hist = _load_history(results_root, name)
        evo_cycles = sum(1 for h in hist if not h.get("skipped", True))
        mutated = sum(1 for h in hist if h.get("mutated"))
        evo_time = sum(h.get("evo_elapsed", 0) for h in hist
                       if not h.get("skipped", True))

        # Workspace artifacts
        ws = results_root / name / "polybench"
        art = count_workspace_artifacts(ws) if ws.is_dir() else {}

        def _mean(xs):
            return sum(xs) / len(xs) if xs else 0.0

        s: dict[str, str] = {}
        # -- Tasks --
        s["Total tasks"] = str(len(results))
        s["Gated (conf < 0.6)"] = str(gated)
        s["Agent SKIPs"] = str(skips)
        s["Traded"] = str(len(traded))
        s["Correct"] = str(len(correct))
        s["Accuracy"] = f"{100*len(correct)/len(traded):.1f}%" if traded else "-"
        # -- Financial --
        s["Avg confidence"] = f"{_mean(confs):.3f}" if confs else "-"
        s["CWR Return"] = f"{100*cwr_prof/cwr_inv:+.1f}%" if cwr_inv > 0 else "-"
        s["CWR invested"] = f"${cwr_inv:.2f}"
        s["CWR profit"] = f"${cwr_prof:+.2f}"
        s["Non-CWR Return"] = f"{100*_mean(raw_rets):+.1f}%" if raw_rets else "-"
        s["Avg APY"] = f"{_mean(apys):+.0f}%" if apys else "-"
        # -- Agent stats --
        s["Avg turns"] = f"{_mean(turns):.1f}"
        s["Avg elapsed (s)"] = f"{_mean(elapsed):.1f}"
        s["Avg input tokens"] = f"{_mean(in_tok)/1000:.1f}K"
        s["Avg output tokens"] = f"{_mean(out_tok)/1000:.1f}K"
        # -- Evolution --
        s["Evo cycles"] = str(evo_cycles)
        s["Mutated"] = str(mutated)
        s["Evo time (s)"] = f"{evo_time:.0f}" if evo_time else "-"
        s["Skills"] = str(art.get("skills", 0))
        s["Tools"] = str(art.get("tools", 0))
        s["Memories"] = str(art.get("memories", 0))
        s["Prompt (chars)"] = str(art.get("prompt_chars", 0))

        cols.append((meta["label"], s))

    if not cols:
        return []

    # Build transposed markdown table
    metric_keys = list(cols[0][1].keys())
    headers = ["Metric"] + [label for label, _ in cols]
    align = ["l"] + ["r"] * len(cols)
    rows = []
    for k in metric_keys:
        rows.append([k] + [s.get(k, "-") for _, s in cols])

    return (
        ["## Experiment Summary", ""]
        + _md_table(headers, rows, align)
        + [""]
    )


def section_overview(results_root: Path, experiments: dict[str, dict]) -> list[str]:
    out = ["## Table 1: Experiment Overview", ""]
    headers = [
        "Experiment", "Tasks", "Traded", "Acc", "F1",
        "CWR%", "Sharpe", "Gated",
        "Skills", "Tools", "Memos",
        "EvoCyc", "Mutated",
    ]
    align = ["l"] + ["r"] * 12
    rows = []
    for name, meta in experiments.items():
        d = results_root / name
        results = _load_results(results_root, name)
        total = len(results)
        m = _compute_official_metrics(results)
        gated = sum(1 for r in results if r.get("gated"))

        ws = d / "polybench"
        art = count_workspace_artifacts(ws) if ws.is_dir() else {}

        hist = _load_history(results_root, name)
        cycles = sum(1 for h in hist if not h.get("skipped", True))
        mutated = sum(1 for h in hist if h.get("mutated"))

        rows.append([
            meta["label"], str(total), str(m["n_traded"]),
            f"{m['accuracy']:.1%}", f"{m['f1']:.3f}",
            f"{m['cwr_return']:+.1%}", f"{m['sharpe']:.2f}", str(gated),
            str(art.get("skills", 0)), str(art.get("tools", 0)),
            str(art.get("memories", 0)),
            str(cycles), str(mutated),
        ])
    out += _md_table(headers, rows, align)
    out.append("")
    return out


def section_official_metrics(
    results_root: Path, experiments: dict[str, dict],
) -> list[str]:
    """Official PolyBench metrics (evaluate_mimo.py methodology)."""
    out = [
        "## Table 2: Official PolyBench Metrics",
        "",
        "Matches `evaluate_mimo.py`: Accuracy, F1, ECE, Non-CWR Return, "
        "CWR Return, Avg APY, Sharpe Ratio.",
        "",
    ]
    headers = [
        "Experiment", "N", "Accuracy", "F1", "ECE", "AvgConf",
        "NonCWR%", "CWR%", "AvgAPY", "Sharpe",
    ]
    align = ["l"] + ["r"] * 9
    rows = []
    for name, meta in experiments.items():
        results = _load_results(results_root, name)
        m = _compute_official_metrics(results)
        rows.append([
            meta["label"], str(m["n_traded"]),
            f"{m['accuracy']:.1%}", f"{m['f1']:.3f}", f"{m['ece']:.3f}",
            f"{m['avg_conf']:.3f}",
            f"{m['non_cwr_return']:+.1%}", f"{m['cwr_return']:+.1%}",
            f"{m['avg_apy']:+.1%}", f"{m['sharpe']:.2f}",
        ])
    out += _md_table(headers, rows, align)
    out.append("")
    return out


def section_common_tasks(
    results_root: Path, experiments: dict[str, dict],
) -> list[str]:
    """Fair comparison on common task set only."""
    common = _common_task_ids(results_root, experiments)
    out = [
        f"## Table 3: Fair Comparison (common {len(common)} tasks)",
        "",
    ]
    headers = ["Experiment", "Acc", "F1", "CWR%", "Sharpe", "Δ Acc", "Δ CWR%"]
    align = ["l"] + ["r"] * 6
    rows = []

    baseline_name = _get_baseline_name(experiments)
    bl_m: dict[str, float] = {}
    if baseline_name:
        bl_all = {r["instance_id"]: r for r in _load_results(results_root, baseline_name)}
        bl_filtered = [v for k, v in bl_all.items() if k in common]
        bl_m = _compute_official_metrics(bl_filtered)

    for name, meta in experiments.items():
        all_r = {r["instance_id"]: r for r in _load_results(results_root, name)}
        filtered = [v for k, v in all_r.items() if k in common]
        m = _compute_official_metrics(filtered)

        da = f"{m['accuracy'] - bl_m['accuracy']:+.1%}" if bl_m and not meta["is_baseline"] else "-"
        dc = f"{m['cwr_return'] - bl_m['cwr_return']:+.1%}" if bl_m and not meta["is_baseline"] else "-"

        rows.append([
            meta["label"], f"{m['accuracy']:.1%}", f"{m['f1']:.3f}",
            f"{m['cwr_return']:+.1%}", f"{m['sharpe']:.2f}", da, dc,
        ])
    out += _md_table(headers, rows, align)
    out.append("")
    return out


def section_task_agreement(
    results_root: Path, experiments: dict[str, dict],
) -> list[str]:
    baseline_name = _get_baseline_name(experiments)
    if not baseline_name:
        return ["*(Skipping task agreement — no baseline detected)*", ""]

    common = _common_task_ids(results_root, experiments)
    out = [f"## Table 4: Task-Level Agreement vs `{baseline_name}` ({len(common)} common)", ""]
    base = {r["instance_id"]: r.get("success", False)
            for r in _load_results(results_root, baseline_name) if r["instance_id"] in common}

    headers = ["Experiment", "Agree", "Improve", "Regress", "Net"]
    align = ["l", "r", "r", "r", "r"]
    rows = []
    for name, meta in experiments.items():
        if meta["is_baseline"]:
            continue
        results = {r["instance_id"]: r.get("success", False)
                   for r in _load_results(results_root, name) if r["instance_id"] in common}
        agree = sum(1 for i in common if base.get(i) == results.get(i))
        improve = sum(1 for i in common if not base.get(i) and results.get(i))
        regress = sum(1 for i in common if base.get(i) and not results.get(i))
        net = improve - regress
        rows.append([meta["label"], str(agree), str(improve), str(regress), f"{net:+d}"])
    out += _md_table(headers, rows, align)
    out.append("")
    return out


def section_cycle1_consistency(
    results_root: Path, experiments: dict[str, dict],
) -> list[str]:
    """Check that cycle-1 (pre-evolution) results agree across experiments."""
    # Find the 10-task experiments that share the same cycle-1 task set
    cycle1: dict[str, dict[str, dict]] = {}
    for name, meta in experiments.items():
        results = _load_results(results_root, name)
        c1 = {r["instance_id"]: r for r in results if r.get("evo_cycle") == 1}
        cycle1[name] = c1

    # Common cycle-1 tasks across ALL experiments
    all_c1_ids = [set(v.keys()) for v in cycle1.values()]
    common = sorted(set.intersection(*all_c1_ids)) if all_c1_ids else []

    out = [
        f"## Table 5: Cycle-1 Consistency Check (pre-evolution, {len(common)} common tasks)",
        "",
        "Before any evolution, all experiments using the same solver model should "
        "produce similar results. Differences come from LLM non-determinism and "
        "seed workspace config (baseline skips skills).",
        "",
    ]

    if not common:
        out.append("*(No common cycle-1 tasks found)*")
        out.append("")
        return out

    # Summary table
    headers = ["Experiment", "C1 Tasks", "C1 Pass", "C1 Rate",
               "Common Pass", "Common Rate", "BatchSize"]
    align = ["l"] + ["r"] * 6
    rows = []
    for name, meta in experiments.items():
        c1 = cycle1[name]
        c1_pass = sum(1 for r in c1.values() if r.get("success"))
        c1_total = len(c1)
        common_pass = sum(1 for tid in common if c1.get(tid, {}).get("success"))
        rows.append([
            meta["label"], str(c1_total), str(c1_pass),
            f"{c1_pass/c1_total:.0%}" if c1_total else "-",
            str(common_pass), f"{common_pass/len(common):.0%}" if common else "-",
            str(meta["batch_size"]),
        ])
    out += _md_table(headers, rows, align)
    out.append("")

    # Task-level detail on common tasks
    out.append("### Task-level detail (common cycle-1 tasks)")
    out.append("")
    exp_names = list(experiments.keys())
    short_labels = [experiments[n]["label"][:10] for n in exp_names]
    headers2 = ["Task"] + short_labels
    align2 = ["l"] + ["r"] * len(exp_names)
    rows2 = []
    for tid in common:
        row = [f"`{tid[:25]}`"]
        for name in exp_names:
            s = cycle1[name].get(tid, {}).get("score", 0)
            row.append(f"{s:.2f}")
        rows2.append(row)
    out += _md_table(headers2, rows2, align2)

    # Agreement summary
    diverge = 0
    for tid in common:
        outcomes = [cycle1[n].get(tid, {}).get("success", False) for n in exp_names]
        if len(set(outcomes)) > 1:
            diverge += 1
    out.append("")
    out.append(
        f"**Agreement**: {len(common) - diverge}/{len(common)} tasks have identical "
        f"pass/fail across all experiments. {diverge} task(s) diverge due to LLM "
        f"non-determinism (borderline confidence near 0.6 gate)."
    )
    out.append("")
    return out


def section_batch_progression(
    results_root: Path, experiments: dict[str, dict],
) -> list[str]:
    out = ["## Table 6: Batch-Level Score Progression", ""]
    for name, meta in experiments.items():
        results = _load_results(results_root, name)
        if not results:
            continue
        batches: dict[int, list[dict]] = defaultdict(list)
        for r in results:
            batches[r.get("batch_num", 0)].append(r)

        hist = _load_history(results_root, name)
        hist_by_cycle = {h.get("cycle", 0): h for h in hist}

        out.append(f"### {meta['label']}")
        headers = ["Batch", "Tasks", "Acc", "CWR%", "NonCWR%", "Mutated"]
        align = ["r"] * 6
        rows = []
        for bn in sorted(batches):
            br = batches[bn]
            m = _compute_official_metrics(br)
            h = hist_by_cycle.get(bn, {})
            mut = "Y" if h.get("mutated") else ("skip" if h.get("skipped") else "N")
            rows.append([
                str(bn), str(len(br)), f"{m['accuracy']:.0%}",
                f"{m['cwr_return']:+.1%}", f"{m['non_cwr_return']:+.1%}", mut,
            ])
        out += _md_table(headers, rows, align)
        out.append("")
    return out


def section_artifact_growth(
    results_root: Path, experiments: dict[str, dict],
) -> list[str]:
    out = ["## Table 7: Artifact Growth Over Evolution (C1: Context Saturation)", ""]
    for name, meta in experiments.items():
        if not meta["has_evo"]:
            continue
        d = results_root / name
        ws = d / "polybench"
        if not (ws / ".git").is_dir():
            continue
        hist = _load_history(results_root, name)
        if not hist:
            continue

        r = subprocess.run(
            ["git", "-C", str(ws), "tag", "-l", "evo-*"],
            capture_output=True, text=True,
        )
        tags = {}
        for t in r.stdout.strip().splitlines():
            if t and "-" in t:
                try:
                    tags[int(t.split("-")[1])] = t
                except (IndexError, ValueError):
                    pass

        out.append(f"### {meta['label']}")
        headers = ["Cycle", "Score", "Skills", "Tools", "Memos", "Prompt", "Mutated"]
        align = ["r"] * 7
        rows = []
        for h in hist:
            cyc = h.get("cycle", 0)
            tag = tags.get(cyc)
            if tag:
                art = _count_artifacts_at_tag(ws, tag)
            else:
                art = {"skills": 0, "tools": 0, "memos": 0, "prompt": 0}
            rows.append([
                str(cyc), f"{h.get('batch_score', 0):.2f}",
                str(art["skills"]), str(art["tools"]),
                str(art["memos"]), f"{art['prompt']}c",
                str(h.get("mutated", False)),
            ])
        out += _md_table(headers, rows, align)
        out.append("")
    return out


def section_confidence_calibration(
    results_root: Path, experiments: dict[str, dict],
) -> list[str]:
    """How well-calibrated are confidence predictions?"""
    out = ["## Table 8: Confidence Calibration", ""]
    headers = [
        "Experiment",
        "Avg Conf (correct)", "Avg Conf (wrong)",
        "High Conf (≥0.8) Acc", "Low Conf (<0.7) Acc",
        "Overconfident%",
    ]
    align = ["l"] + ["r"] * 5
    rows = []
    for name, meta in experiments.items():
        results = _load_results(results_root, name)
        correct = [r for r in results if r.get("success") and "confidence" in r]
        wrong = [r for r in results if not r.get("success") and "confidence" in r
                 and not r.get("gated")]
        avg_c = sum(r["confidence"] for r in correct) / len(correct) if correct else 0
        avg_w = sum(r["confidence"] for r in wrong) / len(wrong) if wrong else 0

        high = [r for r in results if r.get("confidence", 0) >= 0.8 and not r.get("gated")]
        high_acc = sum(1 for r in high if r.get("success")) / len(high) if high else 0
        low = [r for r in results if 0.6 <= r.get("confidence", 0) < 0.7 and not r.get("gated")]
        low_acc = sum(1 for r in low if r.get("success")) / len(low) if low else 0

        overconf = sum(1 for r in results
                       if r.get("confidence", 0) >= 0.8 and not r.get("success")
                       and not r.get("gated"))
        total_active = sum(1 for r in results if not r.get("gated")
                           and r.get("decision", "").upper() != "SKIP")
        oc_pct = f"{100 * overconf / total_active:.1f}%" if total_active else "-"

        rows.append([
            meta["label"],
            f"{avg_c:.3f}", f"{avg_w:.3f}",
            f"{high_acc:.1%}", f"{low_acc:.1%}",
            oc_pct,
        ])
    out += _md_table(headers, rows, align)
    out.append("")
    return out


def section_regression_analysis(
    results_root: Path, experiments: dict[str, dict],
) -> list[str]:
    baseline_name = _get_baseline_name(experiments)
    if not baseline_name:
        return ["*(Skipping regression analysis — no baseline detected)*", ""]

    common = _common_task_ids(results_root, experiments)
    out = [f"## Table 9: Task-Level Changes vs `{baseline_name}`", ""]
    base = {r["instance_id"]: r for r in _load_results(results_root, baseline_name)
            if r["instance_id"] in common}

    headers = ["Instance", "Dir", "BL Side", "BL Conf", "Evo Side", "Evo Conf",
               "Winning", "BL Score", "Evo Score"]
    align = ["l", "l"] + ["r"] * 7

    for name, meta in experiments.items():
        if meta["is_baseline"]:
            continue
        results = {r["instance_id"]: r for r in _load_results(results_root, name)
                   if r["instance_id"] in common}
        regressions = [(i, base[i], results[i]) for i in sorted(common)
                       if base[i].get("success") and not results[i].get("success")
                       and i in results]
        improvements = [(i, base[i], results[i]) for i in sorted(common)
                        if not base[i].get("success") and results[i].get("success")
                        and i in results]
        if not regressions and not improvements:
            continue
        out.append(
            f"### {meta['label']}: {len(regressions)} regressions, "
            f"{len(improvements)} improvements"
        )
        out.append("")
        rows = []
        for iid, b, r in regressions:
            rows.append([
                f"`{iid[:30]}`", "REGRESS",
                b.get("side", ""), f"{b.get('confidence', 0):.2f}",
                r.get("side", ""), f"{r.get('confidence', 0):.2f}",
                b.get("winning_outcome", ""),
                f"{b.get('score', 0):.2f}", f"{r.get('score', 0):.2f}",
            ])
        for iid, b, r in improvements:
            rows.append([
                f"`{iid[:30]}`", "IMPROVE",
                b.get("side", ""), f"{b.get('confidence', 0):.2f}",
                r.get("side", ""), f"{r.get('confidence', 0):.2f}",
                b.get("winning_outcome", ""),
                f"{b.get('score', 0):.2f}", f"{r.get('score', 0):.2f}",
            ])
        out += _md_table(headers, rows, align)
        out.append("")
    return out


def section_evolution_cost(
    results_root: Path, experiments: dict[str, dict],
) -> list[str]:
    out = ["## Table 10: Evolution Cost (C4: Wasteful Triggering)", ""]
    headers = [
        "Experiment", "EvoCycles", "Mutated", "NoMutation",
        "EvoTime", "Wasted", "Wasted%",
    ]
    align = ["l"] + ["r"] * 6
    rows = []
    for name, meta in experiments.items():
        hist = _load_history(results_root, name)
        if not hist:
            continue
        total_cyc = sum(1 for h in hist if not h.get("skipped", True))
        mutated = sum(1 for h in hist if h.get("mutated"))
        no_mut = total_cyc - mutated
        evo_time = sum(h.get("evo_elapsed", 0) for h in hist if not h.get("skipped", True))
        wasted = sum(h.get("evo_elapsed", 0) for h in hist
                     if not h.get("skipped", True) and not h.get("mutated"))
        pct = f"{100 * wasted / evo_time:.0f}%" if evo_time > 1 else "-"
        rows.append([
            meta["label"], str(total_cyc), str(mutated), str(no_mut),
            f"{evo_time:.0f}s", f"{wasted:.0f}s", pct,
        ])
    out += _md_table(headers, rows, align)
    out.append("")
    return out


def section_data_integrity(
    results_root: Path, experiments: dict[str, dict],
) -> list[str]:
    """Flag data quality issues."""
    out = ["## Table 11: Data Integrity", ""]
    headers = ["Experiment", "Raw", "Dedup", "Dupes", "Errors", "Timeouts", "MaxTurns", "Issue"]
    align = ["l"] + ["r"] * 6 + ["l"]
    rows = []
    for name in experiments:
        raw = load_jsonl(results_root / name / "results.jsonl")
        deduped = _dedup_results(raw)
        dupes = len(raw) - len(deduped)
        errors = sum(1 for r in deduped if r.get("error"))
        timeouts = sum(1 for r in deduped if r.get("timed_out"))
        max_turns = sum(1 for r in deduped if r.get("max_turns_hit"))
        issues = []
        if dupes:
            issues.append(f"{dupes} dupes")
        if len(deduped) < 60:
            issues.append(f"only {len(deduped)} tasks")
        if errors:
            issues.append(f"{errors} errors")
        issue_str = "; ".join(issues) if issues else "OK"
        rows.append([
            experiments[name]["label"],
            str(len(raw)), str(len(deduped)), str(dupes),
            str(errors), str(timeouts), str(max_turns), issue_str,
        ])
    out += _md_table(headers, rows, align)
    out.append("")
    return out


def section_metrics_by_period(
    results_root: Path,
    experiments: dict[str, dict],
    db_path: Path | None = None,
) -> list[str]:
    """Break down key metrics by time period based on market resolution date."""
    from datetime import datetime

    if not db_path:
        return ["*(Skipping period metrics — no DB for timestamps)*", ""]

    ts_map = _load_timestamps(db_path)
    if not ts_map:
        return ["*(Skipping period metrics — no timestamps available)*", ""]

    # Define period boundaries (start of each period)
    boundaries = [
        datetime(2025, 1, 1),   # catch-all start
        datetime(2025, 2, 11),
        datetime(2025, 2, 13),
        datetime(2025, 2, 15),
        datetime(2025, 2, 17),
        datetime(2025, 2, 19),
        datetime(2025, 2, 21),
        datetime(2026, 2, 11),
        datetime(2026, 2, 13),
        datetime(2026, 2, 15),
        datetime(2026, 2, 17),
        datetime(2026, 2, 19),
        datetime(2026, 2, 22),  # end sentinel
    ]

    # Detect year from data
    all_dates = sorted(ts_map.values())
    if not all_dates:
        return []
    data_year = all_dates[len(all_dates) // 2].year
    boundaries = [
        datetime(data_year - 1, 1, 1),
        datetime(data_year, 2, 11),
        datetime(data_year, 2, 13),
        datetime(data_year, 2, 15),
        datetime(data_year, 2, 17),
        datetime(data_year, 2, 19),
        datetime(data_year, 2, 22),
    ]

    # Build period labels
    period_labels = []
    for i in range(len(boundaries) - 1):
        if i == 0:
            period_labels.append(f"< {boundaries[1].strftime('%b %d')}")
        else:
            period_labels.append(
                f"{boundaries[i].strftime('%b %d')}-{boundaries[i+1].strftime('%b %d')}"
            )

    def _period_idx(dt: "datetime") -> int:
        for i in range(len(boundaries) - 1, -1, -1):
            if dt >= boundaries[i]:
                return min(i, len(boundaries) - 2)
        return 0

    # Collect per-experiment, per-period results
    exp_period_results: dict[str, dict[int, list[dict]]] = {}
    for name in experiments:
        results = _load_results(results_root, name)
        per_period: dict[int, list[dict]] = {i: [] for i in range(len(boundaries) - 1)}
        for r in results:
            tid = r["instance_id"]
            if tid not in ts_map:
                continue
            pidx = _period_idx(ts_map[tid])
            if 0 <= pidx < len(boundaries) - 1:
                per_period[pidx].append(r)
        exp_period_results[name] = per_period

    exp_names = list(experiments.keys())
    exp_labels = [experiments[n]["label"] for n in exp_names]

    out = [
        "## Table 12: Metrics by Time Period",
        "",
        "Key metrics broken down by market resolution date windows.",
        "",
    ]

    headers = ["Period", "Experiment", "N Traded", "Accuracy", "CWR%", "Sharpe", "AvgConf"]
    align = ["l", "l"] + ["r"] * 5
    rows = []

    for pidx, plabel in enumerate(period_labels):
        first_in_period = True
        for name in exp_names:
            period_results = exp_period_results[name][pidx]
            label = plabel if first_in_period else ""
            first_in_period = False
            if period_results:
                m = _compute_official_metrics(period_results)
                rows.append([
                    label, experiments[name]["label"],
                    str(m["n_traded"]),
                    f"{m['accuracy']:.1%}",
                    f"{m['cwr_return']:+.1%}",
                    f"{m['sharpe']:.2f}",
                    f"{m['avg_conf']:.3f}",
                ])
            else:
                rows.append([label, experiments[name]["label"],
                             "-", "-", "-", "-", "-"])

    # Total row
    first_total = True
    for name in exp_names:
        all_results = _load_results(results_root, name)
        m = _compute_official_metrics(all_results)
        label = "**Total**" if first_total else ""
        first_total = False
        rows.append([
            label, f"**{experiments[name]['label']}**",
            f"**{m['n_traded']}**",
            f"**{m['accuracy']:.1%}**",
            f"**{m['cwr_return']:+.1%}**",
            f"**{m['sharpe']:.2f}**",
            f"**{m['avg_conf']:.3f}**",
        ])

    out += _md_table(headers, rows, align)
    out.append("")
    return out


# -- Plotting ----------------------------------------------------------------

_DEFAULT_DB_PATHS = [
    Path("data/polymarket_analysis.db"),
    Path("data/polybench_test.db"),
    Path("data/polybench.db"),
]


def _load_timestamps(db_path: Path) -> dict[str, "datetime"]:
    """Map task_id -> resolution datetime from PolyBench DB.

    Uses resolved_at (meaningful temporal ordering) rather than snapshot
    timestamp (which may be a batch-scrape date with no chronological value).
    """
    import sqlite3
    from datetime import datetime

    conn = sqlite3.connect(str(db_path))
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "market_snapshots" not in tables or "resolutions" not in tables:
        conn.close()
        return {}
    rows = conn.execute("""
        SELECT ms.id, ms.market_id, ms.event_id, r.resolved_at
        FROM market_snapshots ms
        JOIN resolutions r ON ms.market_id = r.market_id
    """).fetchall()
    conn.close()
    out = {}
    for snap_id, mkt_id, evt_id, ts_str in rows:
        if not ts_str:
            continue
        task_id = f"{evt_id}_{mkt_id}_{snap_id}"
        # Handle timezone suffix if present
        clean = ts_str[:19]
        try:
            out[task_id] = datetime.strptime(clean, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    return out


def _resolve_db(db_arg: str | None) -> Path | None:
    """Resolve DB path from explicit arg or default locations."""
    if db_arg:
        p = Path(db_arg)
        return p if p.exists() else None
    for p in _DEFAULT_DB_PATHS:
        if p.exists():
            return p
    return None


def _task_index(task_id: str) -> int:
    """Extract snapshot_id (last segment) as integer for fallback ordering."""
    parts = task_id.rsplit("_", 1)
    try:
        return int(parts[-1])
    except (ValueError, IndexError):
        return 0


def _load_naive_baseline(db_path: Path) -> dict[str, dict]:
    """Load market data for a naive 'always follow highest price' baseline.

    Returns {task_id: {"max_price": float, "correct": bool}}.
    """
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("""
        SELECT ms.id, ms.market_id, ms.event_id,
               m.outcomes, m.outcome_prices, r.winning_outcome
        FROM market_snapshots ms
        JOIN markets m ON ms.market_id = m.id
        JOIN resolutions r ON ms.market_id = r.market_id
        WHERE ms.ready_for_analysis = 1
    """).fetchall()
    conn.close()

    result = {}
    for snap_id, mkt_id, evt_id, outcomes_str, prices_str, winning in rows:
        task_id = f"{evt_id}_{mkt_id}_{snap_id}"
        try:
            outcomes = json.loads(outcomes_str)
            prices = [float(p) for p in json.loads(prices_str)]
            best_idx = max(range(len(prices)), key=lambda i: prices[i])
            result[task_id] = {
                "max_price": prices[best_idx],
                "correct": outcomes[best_idx] == winning,
            }
        except Exception:
            pass
    return result


def _load_random_baseline(db_path: Path, seed: int = 42) -> dict[str, dict]:
    """Load market data for a random decision baseline.

    Randomly picks YES or NO for each task, uses 0.65 fixed confidence.
    Returns {task_id: {"price": float, "correct": bool}}.
    """
    import random
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("""
        SELECT ms.id, ms.market_id, ms.event_id,
               m.outcomes, m.outcome_prices, r.winning_outcome
        FROM market_snapshots ms
        JOIN markets m ON ms.market_id = m.id
        JOIN resolutions r ON ms.market_id = r.market_id
        WHERE ms.ready_for_analysis = 1
    """).fetchall()
    conn.close()

    rng = random.Random(seed)
    result = {}
    for snap_id, mkt_id, evt_id, outcomes_str, prices_str, winning in rows:
        task_id = f"{evt_id}_{mkt_id}_{snap_id}"
        try:
            outcomes = json.loads(outcomes_str)
            prices = [float(p) for p in json.loads(prices_str)]
            chosen_idx = rng.randint(0, len(outcomes) - 1)
            result[task_id] = {
                "price": prices[chosen_idx],
                "correct": outcomes[chosen_idx] == winning,
            }
        except Exception:
            pass
    return result


def plot_performance_over_time(
    results_root: Path,
    experiments: dict[str, dict],
    db_path: Path | None = None,
) -> Path | None:
    """Generate CWR-over-time figure matching official PolyBench style.

    Plots running Confidence-Weighted Return (%) updated at each market
    resolution, mirroring PolyBench ``assets/returns_by_date.png``.

    CWR_t = sum(cwr_profits_1..t) / sum(cwr_investments_1..t) × 100
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError:
        print("WARNING: matplotlib not installed — skipping plot")
        return None

    from datetime import datetime

    # -- Timestamps (resolution dates) --
    ts_map = _load_timestamps(db_path) if db_path else {}
    use_dates = bool(ts_map)
    if not use_dates:
        for name in experiments:
            for r in _load_results(results_root, name):
                tid = r["instance_id"]
                if tid not in ts_map:
                    ts_map[tid] = _task_index(tid)

    # -- Build global task ordering by resolution time --
    # Collect all task IDs across experiments, sort by timestamp, assign index
    all_task_ids: set[str] = set()
    for name in experiments:
        for r in _load_results(results_root, name):
            if r["instance_id"] in ts_map:
                all_task_ids.add(r["instance_id"])
    sorted_tasks = sorted(all_task_ids, key=lambda tid: ts_map[tid])
    task_to_idx = {tid: i for i, tid in enumerate(sorted_tasks)}

    # -- Build per-experiment series --
    PALETTE = [
        "#e41a1c", "#377eb8", "#4daf4a", "#984ea3",
        "#ff7f00", "#a65628", "#f781bf", "#66c2a5",
    ]
    # Stable color mapping so each experiment always gets the same color
    LABEL_COLORS = {
        "baseline": "#222222",       # black
        "early_freeze": "#e41a1c",   # red
        "full_evo": "#377eb8",       # blue
        "late_start": "#984ea3",     # purple
        "navigation": "#4daf4a",     # green
    }
    series: list[dict] = []
    color_idx = 0
    for name, meta in experiments.items():
        results = _load_results(results_root, name)
        data = [(task_to_idx[r["instance_id"]], r)
                for r in results if r["instance_id"] in task_to_idx]
        data.sort(key=lambda x: x[0])
        if not data:
            continue

        # Respect evo_start_after_pct: only accumulate CWR from the
        # evolution start point onward (skip pre-evolution tasks).
        start_pct = meta.get("evo_start_after_pct", 0)
        if start_pct > 0:
            start_idx = int(len(sorted_tasks) * start_pct / 100)
            data = [(idx, r) for idx, r in data if idx >= start_idx]
        if not data:
            continue

        # Running CWR %: accumulate profit and investment, divide at each step
        xs, cwr_pcts = [], []
        cum_profit, cum_inv = 0.0, 0.0
        for idx, r in data:
            cum_profit += r.get("cwr_profit", 0.0)
            cum_inv += r.get("cwr_investment", 0.0)
            xs.append(idx)
            cwr_pcts.append(100.0 * cum_profit / cum_inv if cum_inv > 0 else 0.0)

        is_bl = meta["is_baseline"]
        if is_bl:
            color = LABEL_COLORS.get("baseline", "#222222")
        elif meta["label"] in LABEL_COLORS:
            color = LABEL_COLORS[meta["label"]]
        else:
            color = PALETTE[color_idx % len(PALETTE)]
            color_idx += 1

        series.append({
            "label": meta["label"], "is_bl": is_bl,
            "xs": xs, "cwr_pcts": cwr_pcts, "color": color,
            "n_tasks": len(data),
        })

    # -- Naive "follow market" baseline --
    if db_path:
        naive_data = _load_naive_baseline(db_path)
        xs_naive, cwr_pcts_naive = [], []
        cum_profit, cum_inv = 0.0, 0.0
        lot = 10.0
        for idx, tid in enumerate(sorted_tasks):
            if tid not in naive_data:
                continue
            nd = naive_data[tid]
            p = nd["max_price"]
            investment = p * lot  # confidence = market price
            profit = investment * (1 - p) / p if nd["correct"] else -investment
            cum_profit += profit
            cum_inv += investment
            xs_naive.append(idx)
            cwr_pcts_naive.append(
                100.0 * cum_profit / cum_inv if cum_inv > 0 else 0.0)
        if xs_naive:
            series.append({
                "label": "naive (follow market)", "is_bl": False,
                "xs": xs_naive, "cwr_pcts": cwr_pcts_naive,
                "color": "#888888", "n_tasks": len(xs_naive),
                "is_naive": True,
            })

    # -- Random decision baseline --
    if db_path:
        random_data = _load_random_baseline(db_path)
        xs_rand, cwr_pcts_rand = [], []
        cum_profit, cum_inv = 0.0, 0.0
        lot = 10.0
        fixed_conf = 0.65
        for idx, tid in enumerate(sorted_tasks):
            if tid not in random_data:
                continue
            rd = random_data[tid]
            p = rd["price"]
            if p <= 0 or p >= 1:
                continue
            investment = fixed_conf * lot
            profit = investment * (1 - p) / p if rd["correct"] else -investment
            cum_profit += profit
            cum_inv += investment
            xs_rand.append(idx)
            cwr_pcts_rand.append(
                100.0 * cum_profit / cum_inv if cum_inv > 0 else 0.0)
        if xs_rand:
            series.append({
                "label": "random (coin flip)", "is_bl": False,
                "xs": xs_rand, "cwr_pcts": cwr_pcts_rand,
                "color": "#cc79a7", "n_tasks": len(xs_rand),
                "is_naive": True,
            })

    if not series:
        return None

    # -- Draw --
    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor("white")

    max_x = len(sorted_tasks) - 1
    for s in series:
        is_naive = s.get("is_naive", False)
        lw = 2.4 if s["is_bl"] else (2.0 if is_naive else 1.5)
        zorder = 10 if s["is_bl"] else (8 if is_naive else 5)
        ls = "--" if is_naive else "-"
        complete = s["n_tasks"] >= max_x * 0.95
        suffix = "" if complete else " *"
        label = f"{s['label']} ({s['n_tasks']} tasks){suffix}"
        ax.step(s["xs"], s["cwr_pcts"], where="post", label=label,
                color=s["color"], lw=lw, zorder=zorder, alpha=0.85, ls=ls)

        # Endpoint marker with CWR annotation
        if s["xs"]:
            final_x, final_cwr = s["xs"][-1], s["cwr_pcts"][-1]
            ax.plot(final_x, final_cwr, "o", color=s["color"],
                    markersize=5, zorder=zorder + 1)
            # Extend incomplete experiments as dashed line to right edge
            if not complete and not is_naive:
                ax.plot([final_x, max_x], [final_cwr, final_cwr],
                        color=s["color"], lw=0.8, ls=":", alpha=0.4, zorder=2)

    ax.axhline(y=0, color="black", lw=1.2, zorder=1)
    ax.set_xlabel("Task Index (ordered by market resolution date)", fontsize=12)
    ax.set_ylabel("Confidence-Weighted Return (CWR) %", fontsize=12)
    ax.legend(loc="best", fontsize=9, ncol=2, framealpha=0.9)
    ax.grid(True, alpha=0.3, ls="--")

    # Add date annotations on top axis
    if use_dates:
        ax2 = ax.twiny()
        # Place date labels at evenly spaced task indices
        n_labels = min(6, len(sorted_tasks))
        label_indices = [int(i * (len(sorted_tasks) - 1) / (n_labels - 1))
                         for i in range(n_labels)]
        ax2.set_xlim(ax.get_xlim())
        ax2.set_xticks(label_indices)
        ax2.set_xticklabels(
            [ts_map[sorted_tasks[i]].strftime("%b %d %H:%M") for i in label_indices],
            fontsize=8, rotation=20, ha="left",
        )

    fig.suptitle("CWR Updated by Empirical Market Resolutions (Lot: $10)",
                 fontsize=14, fontweight="bold", y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.93])

    out_path = SCRIPT_DIR / "performance_over_time.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path


def plot_marginal_cwr(
    results_root: Path,
    experiments: dict[str, dict],
    db_path: Path | None = None,
    window: int = 200,
    n_boot: int = 500,
) -> Path | None:
    """Generate Marginal CWR plot with sliding window and bootstrap CIs.

    For each position, computes CWR % over a centered window of `window`
    tasks, with 90 % bootstrap confidence bands.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("WARNING: matplotlib/numpy not installed — skipping marginal CWR plot")
        return None

    # -- Timestamps and task ordering --
    ts_map = _load_timestamps(db_path) if db_path else {}
    use_dates = bool(ts_map)
    if not use_dates:
        for name in experiments:
            for r in _load_results(results_root, name):
                tid = r["instance_id"]
                if tid not in ts_map:
                    ts_map[tid] = _task_index(tid)

    all_task_ids: set[str] = set()
    for name in experiments:
        for r in _load_results(results_root, name):
            if r["instance_id"] in ts_map:
                all_task_ids.add(r["instance_id"])
    sorted_tasks = sorted(all_task_ids, key=lambda tid: ts_map[tid])
    task_to_idx = {tid: i for i, tid in enumerate(sorted_tasks)}
    n_tasks_total = len(sorted_tasks)

    if n_tasks_total < window:
        print(f"WARNING: fewer tasks ({n_tasks_total}) than window ({window}) — skipping marginal CWR")
        return None

    PALETTE = [
        "#e41a1c", "#377eb8", "#4daf4a", "#984ea3",
        "#ff7f00", "#a65628", "#f781bf", "#66c2a5",
    ]
    LABEL_COLORS = {
        "baseline": "#222222",       # black
        "early_freeze": "#e41a1c",   # red
        "full_evo": "#377eb8",       # blue
        "late_start": "#984ea3",     # purple
        "navigation": "#4daf4a",     # green
    }

    series: list[dict] = []
    color_idx = 0
    for name, meta in experiments.items():
        results = _load_results(results_root, name)
        # Respect evo_start_after_pct: mask pre-evolution tasks as NaN
        start_pct = meta.get("evo_start_after_pct", 0)
        start_idx = int(n_tasks_total * start_pct / 100) if start_pct > 0 else 0

        # Build arrays indexed by global task position
        profits = np.full(n_tasks_total, np.nan)
        investments = np.full(n_tasks_total, np.nan)
        for r in results:
            if r["instance_id"] not in task_to_idx:
                continue
            idx = task_to_idx[r["instance_id"]]
            if idx < start_idx:
                continue  # skip pre-evolution tasks
            profits[idx] = r.get("cwr_profit", 0.0)
            investments[idx] = r.get("cwr_investment", 0.0)

        # Sliding window marginal CWR with bootstrap CIs
        xs, cwr_means, cwr_lo, cwr_hi = [], [], [], []
        half = window // 2
        for center in range(max(half, start_idx), n_tasks_total - half):
            w_prof = profits[center - half : center + half]
            w_inv = investments[center - half : center + half]
            valid = ~np.isnan(w_prof)
            if valid.sum() < window * 0.3:
                continue
            p = w_prof[valid]
            inv = w_inv[valid]
            total_inv = inv.sum()
            if total_inv <= 0:
                continue
            cwr_point = 100.0 * p.sum() / total_inv

            # Bootstrap CI
            rng = np.random.default_rng(center)
            n_valid = len(p)
            boot_cwrs = []
            for _ in range(n_boot):
                idx_b = rng.integers(0, n_valid, size=n_valid)
                bi_sum = inv[idx_b].sum()
                if bi_sum > 0:
                    boot_cwrs.append(100.0 * p[idx_b].sum() / bi_sum)
            if boot_cwrs:
                boot_arr = np.array(boot_cwrs)
                ci_lo = float(np.percentile(boot_arr, 5))
                ci_hi = float(np.percentile(boot_arr, 95))
            else:
                ci_lo = ci_hi = cwr_point

            xs.append(center)
            cwr_means.append(cwr_point)
            cwr_lo.append(ci_lo)
            cwr_hi.append(ci_hi)

        if not xs:
            continue

        is_bl = meta["is_baseline"]
        if is_bl:
            color = LABEL_COLORS.get("baseline", "#222222")
        elif meta["label"] in LABEL_COLORS:
            color = LABEL_COLORS[meta["label"]]
        else:
            color = PALETTE[color_idx % len(PALETTE)]
            color_idx += 1

        series.append({
            "label": meta["label"], "is_bl": is_bl,
            "xs": xs, "means": cwr_means, "lo": cwr_lo, "hi": cwr_hi,
            "color": color,
        })

    # -- Naive "follow market" baseline --
    if db_path:
        naive_data = _load_naive_baseline(db_path)
        profits_naive = np.full(n_tasks_total, np.nan)
        investments_naive = np.full(n_tasks_total, np.nan)
        lot = 10.0
        for tid, nd in naive_data.items():
            if tid not in task_to_idx:
                continue
            idx = task_to_idx[tid]
            p = nd["max_price"]
            investment = p * lot
            profit = investment * (1 - p) / p if nd["correct"] else -investment
            profits_naive[idx] = profit
            investments_naive[idx] = investment

        xs_n, means_n, lo_n, hi_n = [], [], [], []
        half = window // 2
        for center in range(half, n_tasks_total - half):
            w_prof = profits_naive[center - half : center + half]
            w_inv = investments_naive[center - half : center + half]
            valid = ~np.isnan(w_prof)
            if valid.sum() < window * 0.3:
                continue
            p_v, inv_v = w_prof[valid], w_inv[valid]
            total_inv = inv_v.sum()
            if total_inv <= 0:
                continue
            cwr_pt = 100.0 * p_v.sum() / total_inv
            rng = np.random.default_rng(center)
            n_v = len(p_v)
            boot = []
            for _ in range(n_boot):
                ib = rng.integers(0, n_v, size=n_v)
                bi = inv_v[ib].sum()
                if bi > 0:
                    boot.append(100.0 * p_v[ib].sum() / bi)
            ba = np.array(boot) if boot else np.array([cwr_pt])
            xs_n.append(center)
            means_n.append(cwr_pt)
            lo_n.append(float(np.percentile(ba, 5)))
            hi_n.append(float(np.percentile(ba, 95)))
        if xs_n:
            series.append({
                "label": "naive (follow market)", "is_bl": False,
                "xs": xs_n, "means": means_n, "lo": lo_n, "hi": hi_n,
                "color": "#888888", "is_naive": True,
            })

    # -- Random decision baseline --
    if db_path:
        random_data = _load_random_baseline(db_path)
        profits_rand = np.full(n_tasks_total, np.nan)
        investments_rand = np.full(n_tasks_total, np.nan)
        lot = 10.0
        fixed_conf = 0.65
        for tid, rd in random_data.items():
            if tid not in task_to_idx:
                continue
            idx = task_to_idx[tid]
            p = rd["price"]
            if p <= 0 or p >= 1:
                continue
            investment = fixed_conf * lot
            profit = investment * (1 - p) / p if rd["correct"] else -investment
            profits_rand[idx] = profit
            investments_rand[idx] = investment

        xs_r, means_r, lo_r, hi_r = [], [], [], []
        half = window // 2
        for center in range(half, n_tasks_total - half):
            w_prof = profits_rand[center - half : center + half]
            w_inv = investments_rand[center - half : center + half]
            valid = ~np.isnan(w_prof)
            if valid.sum() < window * 0.3:
                continue
            p_v, inv_v = w_prof[valid], w_inv[valid]
            total_inv = inv_v.sum()
            if total_inv <= 0:
                continue
            cwr_pt = 100.0 * p_v.sum() / total_inv
            rng = np.random.default_rng(center)
            n_v = len(p_v)
            boot = []
            for _ in range(n_boot):
                ib = rng.integers(0, n_v, size=n_v)
                bi = inv_v[ib].sum()
                if bi > 0:
                    boot.append(100.0 * p_v[ib].sum() / bi)
            ba = np.array(boot) if boot else np.array([cwr_pt])
            xs_r.append(center)
            means_r.append(cwr_pt)
            lo_r.append(float(np.percentile(ba, 5)))
            hi_r.append(float(np.percentile(ba, 95)))
        if xs_r:
            series.append({
                "label": "random (coin flip)", "is_bl": False,
                "xs": xs_r, "means": means_r, "lo": lo_r, "hi": hi_r,
                "color": "#cc79a7", "is_naive": True,
            })

    if not series:
        return None

    # -- Draw --
    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor("white")

    for s in series:
        is_naive = s.get("is_naive", False)
        lw = 2.4 if s["is_bl"] else (2.0 if is_naive else 1.5)
        zorder = 10 if s["is_bl"] else (8 if is_naive else 5)
        ls = "--" if is_naive else "-"
        ax.plot(s["xs"], s["means"], label=s["label"],
                color=s["color"], lw=lw, zorder=zorder, alpha=0.85, ls=ls)
        ax.fill_between(s["xs"], s["lo"], s["hi"],
                        color=s["color"], alpha=0.15, zorder=zorder - 1)

    ax.axhline(y=0, color="black", lw=1.2, zorder=1)
    ax.set_xlabel("Task Index (ordered by market resolution date)", fontsize=12)
    ax.set_ylabel(f"Marginal CWR % (per {window}-task window)", fontsize=12)
    ax.legend(loc="best", fontsize=9, framealpha=0.9)
    ax.grid(True, alpha=0.3, ls="--")

    # Date annotations on top axis
    if use_dates:
        ax2 = ax.twiny()
        n_labels = min(6, n_tasks_total)
        label_indices = [int(i * (n_tasks_total - 1) / (n_labels - 1))
                         for i in range(n_labels)]
        ax2.set_xlim(ax.get_xlim())
        ax2.set_xticks(label_indices)
        ax2.set_xticklabels(
            [ts_map[sorted_tasks[i]].strftime("%b %d %H:%M") for i in label_indices],
            fontsize=8, rotation=20, ha="left",
        )

    fig.suptitle(f"Marginal CWR (sliding {window}-task window)",
                 fontsize=14, fontweight="bold", y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.93])

    out_path = SCRIPT_DIR / "marginal_cwr.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path


# -- Main --------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Analyze A-Evolve-V2 PolyBench experiments",
    )
    parser.add_argument(
        "--path", type=str, default="results",
        help="Path to the results directory (default: results)",
    )
    parser.add_argument(
        "--baseline", type=str, default=None,
        help="Baseline experiment name (auto-detected if not set)",
    )
    parser.add_argument(
        "--output", type=str, default=str(REPORT_PATH),
        help=f"Output Markdown file (default: {REPORT_PATH})",
    )
    parser.add_argument(
        "--db", type=str, default=None,
        help="PolyBench DB path for timestamps (auto-detected if not set)",
    )
    parser.add_argument(
        "--include", type=str, nargs="*", default=None,
        help="Only include these experiments (substring match on dir name)",
    )
    parser.add_argument(
        "--exclude", type=str, nargs="*", default=None,
        help="Exclude these experiments (substring match on dir name)",
    )
    args = parser.parse_args()
    results_root = Path(args.path)

    experiments = discover_experiments(results_root, baseline_name=args.baseline)

    if args.include:
        experiments = {k: v for k, v in experiments.items()
                       if any(pat in k for pat in args.include)}
    if args.exclude:
        experiments = {k: v for k, v in experiments.items()
                       if not any(pat in k for pat in args.exclude)}
    if not experiments:
        print(f"No polybench experiments found in {results_root}")
        return

    baseline = _get_baseline_name(experiments)

    lines = [
        "# A-Evolve-V2 PolyBench Experiment Report",
        "",
        f"Auto-generated from `{results_root}` ({len(experiments)} experiments).",
        "",
    ]
    if baseline:
        lines.append(f"Baseline: `{baseline}`")
    else:
        lines.append("**Warning**: no baseline detected (comparison tables skipped)")
    lines += ["", "---", ""]

    lines += section_summary(results_root, experiments)
    lines += section_overview(results_root, experiments)
    lines += section_official_metrics(results_root, experiments)
    lines += section_common_tasks(results_root, experiments)
    lines += section_task_agreement(results_root, experiments)
    lines += section_cycle1_consistency(results_root, experiments)
    lines += section_batch_progression(results_root, experiments)
    lines += section_artifact_growth(results_root, experiments)
    lines += section_confidence_calibration(results_root, experiments)
    lines += section_regression_analysis(results_root, experiments)
    lines += section_evolution_cost(results_root, experiments)
    lines += section_data_integrity(results_root, experiments)

    db_path = _resolve_db(args.db)
    lines += section_metrics_by_period(results_root, experiments, db_path)

    # -- Plot --
    fig_path = plot_performance_over_time(results_root, experiments, db_path)
    if fig_path:
        lines += [
            "## Figure: CWR Over Time", "",
            f"![CWR Over Time]({fig_path.name})", "",
            "Running Confidence-Weighted Return (%) updated at each market "
            "resolution. Matches official PolyBench methodology. "
            "Baseline shown in dark/bold.",
            "",
        ]

    marginal_path = plot_marginal_cwr(results_root, experiments, db_path)
    if marginal_path:
        lines += [
            "## Figure: Marginal CWR", "",
            f"![Marginal CWR]({marginal_path.name})", "",
            "Sliding 200-task window CWR (%) with 90% bootstrap confidence bands. "
            "Shows local performance trends over time rather than cumulative returns.",
            "",
        ]

    md = "\n".join(lines)
    print(md)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md)
    print(f"\n--- Report written to {out_path} ---")


if __name__ == "__main__":
    main()
