#!/usr/bin/env python3
"""Comprehensive analysis of A-Evolve-V2 FutureX experiments.

Auto-discovers futurex experiments from the results directory. Outputs
Markdown report and two figures (accuracy over batches, artifact growth).

Usage:
    python evaluations/analysis_futurex/analyze_all.py
    python evaluations/analysis_futurex/analyze_all.py --path results
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPORT_PATH = SCRIPT_DIR / "report.md"


# -- Helpers ------------------------------------------------------------------

def load_jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text().splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def _dedup_results(results: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for r in results:
        seen[r["instance_id"]] = r
    return list(seen.values())


def _load_results(results_root: Path, name: str) -> list[dict]:
    return _dedup_results(load_jsonl(results_root / name / "results.jsonl"))


def _load_history(results_root: Path, name: str) -> list[dict]:
    for p in [
        results_root / name / "history.jsonl",
        results_root / name / "futurex" / "evolution" / "history.jsonl",
    ]:
        rows = load_jsonl(p)
        if rows:
            seen: dict[int, dict] = {}
            for h in rows:
                seen[h.get("cycle", 0)] = h
            return sorted(seen.values(), key=lambda h: h.get("cycle", 0))
    return []


def _load_experiment_config(name: str) -> dict:
    import yaml
    # Try multiple naming conventions
    candidates = [
        f"{name}.yaml",
        f"{name.replace('futurex_', '')}.yaml",
        f"futurex_{name.replace('futurex_', '')}.yaml",
    ]
    # Also handle _live suffix: futurex_full_evo_live → futurex_live.yaml
    if name.endswith("_live"):
        base = name.rsplit("_live", 1)[0]
        candidates.append(f"{base.replace('futurex_', 'futurex_')}_live.yaml")
        candidates.append(f"futurex_live.yaml")
        candidates.append(f"futurex_{base.replace('futurex_', '')}_live.yaml")
    for fname in candidates:
        p = Path("experiments/futurex/configs") / fname
        if p.exists():
            with open(p) as f:
                return yaml.safe_load(f) or {}
    return {}


def _load_tasks():
    """Load FutureX tasks for metadata (domain, level, resolve date)."""
    import sys
    sys.path.insert(0, ".")
    import logging
    logging.disable(logging.WARNING)
    from agent_evolve.benchmarks.futurex.futurex import FutureXBenchmark
    from agent_evolve.config import EvolveConfig
    config = EvolveConfig.from_yaml("experiments/futurex/configs/baseline.yaml")
    bm = FutureXBenchmark(config)
    return {t.id: t for t in bm.get_tasks(split="test", limit=0)}


def _extract_resolve_date(task_input: str) -> str:
    m = re.search(r'resolved around (\S+)', task_input)
    return m.group(1)[:10] if m else ""


def _md_table(headers, rows, align=None):
    if not align:
        align = ["l"] * len(headers)
    sep = ["---:" if a == "r" else ":---:" if a == "c" else "---" for a in align]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(sep) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return lines


def count_workspace_artifacts(ws: Path) -> dict:
    skills = [s.name for s in (ws / "skills").iterdir() if s.is_dir()] if (ws / "skills").is_dir() else []
    tools_dir = ws / "tools"
    tool_files = [f for f in tools_dir.iterdir() if f.suffix in (".py", ".sh")] if tools_dir.is_dir() else []
    mem_files = list((ws / "memory").glob("*.jsonl")) if (ws / "memory").is_dir() else []
    mem_count = sum(1 for f in mem_files for line in f.read_text().splitlines() if line.strip())
    prompt = ws / "prompts" / "system.md"
    prompt_chars = prompt.stat().st_size if prompt.exists() else 0
    return {
        "skills": len(skills), "skill_names": skills,
        "tools": len(tool_files), "tool_names": [f.stem for f in tool_files],
        "memories": mem_count, "prompt_chars": prompt_chars,
    }


# -- Discovery ----------------------------------------------------------------

def discover_experiments(results_root: Path, baseline_name=None) -> dict[str, dict]:
    experiments = {}
    for d in sorted(results_root.iterdir()):
        if not d.is_dir() or not d.name.startswith("futurex_"):
            continue
        if not (d / "results.jsonl").exists():
            continue
        name = d.name
        hist = _load_history(results_root, name)
        has_evo = any(not h.get("skipped", True) for h in hist)
        cfg = _load_experiment_config(name)

        # Determine search mode
        no_web_search = cfg.get("no_web_search", False)
        search_mode = cfg.get("search_mode", "?")
        if no_web_search:
            search_mode = "none"

        # Baseline detection: no evolution + no_web_search is the primary baseline
        if baseline_name:
            is_baseline = name == baseline_name
        else:
            is_baseline = name == "futurex_baseline_no_search"

        experiments[name] = {
            "label": name.replace("futurex_", ""),
            "has_evo": has_evo,
            "is_baseline": is_baseline,
            "search_mode": search_mode,
            "no_web_search": no_web_search,
            "evo_start_after_pct": cfg.get("evo_start_after_pct", 0),
            "evo_freeze_after_pct": cfg.get("evo_freeze_after_pct", 0),
        }
    return experiments


# -- Sections -----------------------------------------------------------------

def section_summary(results_root, experiments, task_map) -> list[str]:
    out = ["## Experiment Summary", ""]
    headers = ["Metric"] + [meta["label"] for meta in experiments.values()]
    align = ["l"] + ["r"] * len(experiments)

    metric_rows = defaultdict(list)
    for name, meta in experiments.items():
        results = _load_results(results_root, name)
        passed = sum(1 for r in results if r.get("success"))
        n = len(results)
        turns = [r.get("turns", 0) for r in results]
        elapsed = [r.get("elapsed", 0) for r in results]
        hist = _load_history(results_root, name)
        evo_cycles = sum(1 for h in hist if not h.get("skipped", True))
        mutated = sum(1 for h in hist if h.get("mutated"))
        ws = results_root / name / "futurex"
        art = count_workspace_artifacts(ws) if ws.is_dir() else {}

        metric_rows["Tasks"].append(str(n))
        metric_rows["Passed"].append(f"{passed}/{n}")
        metric_rows["**Accuracy**"].append(f"**{100*passed/n:.1f}%**" if n else "-")
        metric_rows["Search mode"].append(meta["search_mode"])
        metric_rows["Avg turns"].append(f"{sum(turns)/n:.1f}" if n else "-")
        metric_rows["Avg elapsed"].append(f"{sum(elapsed)/n:.0f}s" if n else "-")
        metric_rows["Evo cycles"].append(str(evo_cycles))
        metric_rows["Mutated"].append(str(mutated))
        metric_rows["Skills"].append(str(art.get("skills", 0)))
        metric_rows["Tools"].append(str(art.get("tools", 0)))
        metric_rows["Memories"].append(str(art.get("memories", 0)))
        metric_rows["Prompt (chars)"].append(str(art.get("prompt_chars", 0)))

    rows = [[k] + v for k, v in metric_rows.items()]
    out += _md_table(headers, rows, align)
    out.append("")
    return out


def section_by_domain(results_root, experiments, task_map) -> list[str]:
    out = ["## Accuracy by Domain", ""]
    domains = sorted(set(t.metadata.get("domain", "?") for t in task_map.values()))
    headers = ["Domain", "Tasks"] + [meta["label"] for meta in experiments.values()]
    align = ["l", "r"] + ["r"] * len(experiments)
    rows = []
    for domain in domains:
        domain_tasks = [t for t in task_map.values() if t.metadata.get("domain") == domain]
        row = [domain, str(len(domain_tasks))]
        for name in experiments:
            rmap = {r["instance_id"]: r for r in _load_results(results_root, name)}
            p = sum(1 for t in domain_tasks if rmap.get(t.id, {}).get("success"))
            row.append(f"{p}/{len(domain_tasks)} ({100*p/len(domain_tasks):.0f}%)" if domain_tasks else "-")
        rows.append(row)
    out += _md_table(headers, rows, align)
    out.append("")
    return out


def section_by_level(results_root, experiments, task_map) -> list[str]:
    out = ["## Accuracy by Difficulty Level", ""]
    levels = sorted(set(t.metadata.get("difficulty_level", 0) for t in task_map.values()))
    headers = ["Level", "Tasks"] + [meta["label"] for meta in experiments.values()]
    align = ["l", "r"] + ["r"] * len(experiments)
    rows = []
    for lvl in levels:
        lvl_tasks = [t for t in task_map.values() if t.metadata.get("difficulty_level") == lvl]
        row = [str(lvl), str(len(lvl_tasks))]
        for name in experiments:
            rmap = {r["instance_id"]: r for r in _load_results(results_root, name)}
            p = sum(1 for t in lvl_tasks if rmap.get(t.id, {}).get("success"))
            row.append(f"{p}/{len(lvl_tasks)} ({100*p/len(lvl_tasks):.0f}%)" if lvl_tasks else "-")
        rows.append(row)
    out += _md_table(headers, rows, align)
    out.append("")
    return out


def _get_week_label(date_str: str) -> str:
    """Map a date string (YYYY-MM-DD) to a week label like 'Mar W2'."""
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(date_str)
    except Exception:
        return "?"
    week_num = (dt.day - 1) // 7 + 1
    return f"{dt.strftime('%b')} W{week_num}"


def _acc_str(passed, total):
    """Format accuracy as 'P/T (X%)'."""
    if not total:
        return "-"
    return f"{passed}/{total} ({100*passed/total:.0f}%)"


def _get_leaderboard_shared_task_ids(task_map: dict) -> tuple[set, dict]:
    """Find tasks shared between our Past dataset and the FutureX leaderboard
    March Week 2 Online snapshot. Returns (shared_task_ids, level_dist).

    Matching criteria (strict):
      1. Same `id` field in both datasets
      2. Same title
      3. Same end_time
    """
    try:
        import pandas as pd
        from datasets import load_dataset

        ds_online = load_dataset("futurex-ai/Futurex-Online", split="train",
                                 revision="a696ecd3")
        past = pd.read_parquet("data/futurex/futurex_past.parquet")
        online_by_id = {r["id"]: r for r in ds_online}
        past_by_id = {row["id"]: row for _, row in past.iterrows()}

        strict_ids = set()
        for tid in set(online_by_id) & set(past_by_id):
            if (str(online_by_id[tid].get("en_title", "")) ==
                    str(past_by_id[tid].get("title", "")) and
                    str(online_by_id[tid].get("end_time", ""))[:10] ==
                    str(past_by_id[tid].get("end_time", ""))[:10]):
                strict_ids.add(tid)

        # Map raw Past IDs → our experiment task IDs
        prompt_to_raw = {}
        for _, row in past.iterrows():
            prompt_to_raw[str(row["prompt"])[:200]] = row["id"]

        shared_task_ids = set()
        level_dist = defaultdict(int)
        for t in task_map.values():
            raw_id = prompt_to_raw.get(t.input[:200])
            if raw_id and raw_id in strict_ids:
                shared_task_ids.add(t.id)
                level_dist[t.metadata.get("difficulty_level", 0)] += 1

        return shared_task_ids, dict(level_dist)
    except Exception:
        return set(), {}


def section_by_month(results_root, experiments, task_map) -> list[str]:
    out = ["## Accuracy by Resolution Month", ""]
    months = defaultdict(list)
    for t in task_map.values():
        rd = _extract_resolve_date(t.input)
        if rd:
            months[rd[:7]].append(t)
    headers = ["Month", "Tasks"] + [meta["label"] for meta in experiments.values()]
    align = ["l", "r"] + ["r"] * len(experiments)
    rows = []
    for month in sorted(months):
        mtasks = months[month]
        row = [month, str(len(mtasks))]
        for name in experiments:
            rmap = {r["instance_id"]: r for r in _load_results(results_root, name)}
            p = sum(1 for t in mtasks if rmap.get(t.id, {}).get("success"))
            row.append(_acc_str(p, len(mtasks)))
        rows.append(row)
    out += _md_table(headers, rows, align)
    out.append("")
    return out


def section_leaderboard_comparison(results_root, experiments, task_map) -> list[str]:
    """Fair comparison with FutureX leaderboard on strictly matched shared tasks."""
    shared_ids, level_dist = _get_leaderboard_shared_task_ids(task_map)
    if not shared_ids:
        return ["*(Skipping leaderboard comparison — could not load Online dataset)*", ""]

    n_shared = len(shared_ids)
    out = [
        "## FutureX Leaderboard Comparison (March Week 2)",
        "",
        f"**{n_shared} verified shared tasks** between our Futurex-Past and the leaderboard's "
        f"Futurex-Online snapshot (`a696ecd3`, 77 tasks, Mar 12-17).",
        "",
        "Matching criteria (all three must hold):",
        "1. Same `id` field in both datasets",
        "2. Same `title` / `en_title`",
        "3. Same `end_time` (resolution date)",
        "",
        f"Level distribution: " + ", ".join(
            f"L{k}={v}" for k, v in sorted(level_dist.items())) + f" (total {n_shared})",
        "",
    ]

    # Build unified table
    headers = ["Agent", "Model", "Search"]
    for lvl in sorted(level_dist):
        headers.append(f"L{lvl} ({level_dist[lvl]})")
    headers.append(f"Overall ({n_shared})")
    align = ["l", "l", "l"] + ["r"] * (len(level_dist) + 1)

    rows = []

    # Leaderboard entries (per-level scores from their published results)
    leaderboard = [
        ("H2O Super Agent v1.82", "Sonnet 4.6", "Google Serper + Jina", {1: 83.3, 2: 65.3, 3: 72.2, 4: 53.8}),
        ("MiroFlow", "GPT-5", "Google Serper + Jina", {1: 83.3, 2: 65.3, 3: 66.8, 4: 54.8}),
        ("TongAgents beta", "GPT-5", "Google Serper", {1: 83.3, 2: 69.4, 3: 74.2, 4: 44.3}),
    ]
    for agent, model, search, level_scores in leaderboard:
        row = [agent, model, search]
        total_est = 0
        for lvl in sorted(level_dist):
            pct = level_scores.get(lvl)
            if pct is not None:
                row.append(f"{pct:.1f}%")
                total_est += pct / 100 * level_dist[lvl]
            else:
                row.append("-")
        row.append(f"~{100 * total_est / n_shared:.0f}%*")
        rows.append(row)

    # Separator
    rows.append(["---"] * len(headers))

    # Our experiments
    for name, meta in experiments.items():
        results = {r["instance_id"]: r for r in _load_results(results_root, name)}
        row = [f"**{meta['label']}**", "Sonnet 4.6", meta["search_mode"]]
        total_pass = 0
        for lvl in sorted(level_dist):
            lvl_tasks = [t for t in task_map.values()
                         if t.id in shared_ids and t.metadata.get("difficulty_level") == lvl]
            p = sum(1 for t in lvl_tasks if results.get(t.id, {}).get("success"))
            total_pass += p
            row.append(f"{100*p/len(lvl_tasks):.1f}%" if lvl_tasks else "-")
        row.append(f"**{100*total_pass/n_shared:.1f}%**")
        rows.append(row)

    out += _md_table(headers, rows, align)
    out.append("")
    out.append("*\\*Leaderboard L1+L2 overall estimated as weighted average. "
               "Their published overall (62-65%) includes L3+L4 tasks not in our shared set.*")
    out.append("")
    return out


def section_head_to_head(results_root, experiments, task_map) -> list[str]:
    baseline_name = next((n for n, m in experiments.items() if m["is_baseline"]), None)
    if not baseline_name:
        return []
    out = [f"## Head-to-Head vs `{baseline_name}`", ""]
    base = {r["instance_id"]: r.get("success", False) for r in _load_results(results_root, baseline_name)}
    headers = ["Experiment", "Both pass", "Improved", "Regressed", "Net"]
    align = ["l", "r", "r", "r", "r"]
    rows = []
    for name, meta in experiments.items():
        if meta["is_baseline"]:
            continue
        rmap = {r["instance_id"]: r.get("success", False) for r in _load_results(results_root, name)}
        common = set(base) & set(rmap)
        both = sum(1 for i in common if base[i] and rmap[i])
        imp = sum(1 for i in common if not base[i] and rmap[i])
        reg = sum(1 for i in common if base[i] and not rmap[i])
        rows.append([meta["label"], str(both), str(imp), str(reg), f"{imp-reg:+d}"])
    out += _md_table(headers, rows, align)
    out.append("")
    return out


def section_batch_progression(results_root, experiments) -> list[str]:
    out = ["## Batch-Level Score Progression", ""]
    for name, meta in experiments.items():
        results = _load_results(results_root, name)
        if not results:
            continue
        batches = defaultdict(list)
        for r in results:
            batches[r.get("batch_num", 0)].append(r)
        hist = _load_history(results_root, name)
        hist_by_cycle = {h.get("cycle", 0): h for h in hist}
        out.append(f"### {meta['label']}")
        headers = ["Batch", "Tasks", "Passed", "Acc", "Mutated"]
        align = ["r"] * 5
        rows = []
        for bn in sorted(batches):
            br = batches[bn]
            p = sum(1 for r in br if r.get("success"))
            h = hist_by_cycle.get(bn, {})
            mut = "Y" if h.get("mutated") else ("skip" if h.get("skipped") else "N")
            rows.append([str(bn), str(len(br)), str(p), f"{100*p/len(br):.0f}%", mut])
        out += _md_table(headers, rows, align)
        out.append("")
    return out


def section_artifact_growth(results_root, experiments) -> list[str]:
    out = ["## Artifact Growth Over Evolution", ""]
    for name, meta in experiments.items():
        if not meta["has_evo"]:
            continue
        ws = results_root / name / "futurex"
        if not (ws / ".git").is_dir():
            continue
        hist = _load_history(results_root, name)
        if not hist:
            continue
        r = subprocess.run(["git", "-C", str(ws), "tag", "-l", "evo-*"],
                           capture_output=True, text=True)
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
                def git(*args):
                    return subprocess.run(
                        ["git", "-C", str(ws)] + list(args),
                        capture_output=True, text=True).stdout.strip()
                tree = git("ls-tree", "-d", "--name-only", tag, "skills/")
                skills = len([l for l in tree.splitlines() if l.strip()]) if tree else 0
                tree = git("ls-tree", "--name-only", tag, "tools/")
                tools = len([l for l in tree.splitlines() if l.endswith(".py")]) if tree else 0
                prompt = git("show", f"{tag}:prompts/system.md")
                prompt_len = len(prompt)
                art = {"skills": skills, "tools": tools, "prompt": prompt_len}
            else:
                art = {"skills": 0, "tools": 0, "prompt": 0}
            rows.append([
                str(cyc), f"{h.get('batch_score', 0):.2f}",
                str(art["skills"]), str(art["tools"]),
                "-", f"{art['prompt']}c",
                str(h.get("mutated", False)),
            ])
        out += _md_table(headers, rows, align)
        out.append("")
    return out


def section_data_integrity(results_root, experiments) -> list[str]:
    out = ["## Data Integrity", ""]
    headers = ["Experiment", "Raw", "Dedup", "Dupes", "Errors", "Timeouts", "MaxTurns"]
    align = ["l"] + ["r"] * 6
    rows = []
    for name, meta in experiments.items():
        raw = load_jsonl(results_root / name / "results.jsonl")
        deduped = _dedup_results(raw)
        dupes = len(raw) - len(deduped)
        errors = sum(1 for r in deduped if r.get("error"))
        timeouts = sum(1 for r in deduped if r.get("timed_out"))
        max_turns = sum(1 for r in deduped if r.get("max_turns_hit"))
        rows.append([meta["label"], str(len(raw)), str(len(deduped)),
                     str(dupes), str(errors), str(timeouts), str(max_turns)])
    out += _md_table(headers, rows, align)
    out.append("")
    return out


# -- Plotting -----------------------------------------------------------------

def plot_accuracy_over_batches(results_root, experiments) -> Path | None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    COLORS = {
        "baseline_no_search": "#888888",
        "baseline": "#222222",
        "baseline_live_search": "#ff7f00",
        "full_evo": "#377eb8",
        "early_freeze": "#e41a1c",
        "late_start": "#984ea3",
    }

    fig, ax = plt.subplots(figsize=(12, 5))
    for name, meta in experiments.items():
        results = _load_results(results_root, name)
        if not results:
            continue
        batches = defaultdict(list)
        for r in results:
            batches[r.get("batch_num", 0)].append(r)
        xs, ys = [], []
        cum_pass, cum_total = 0, 0
        for bn in sorted(batches):
            br = batches[bn]
            cum_pass += sum(1 for r in br if r.get("success"))
            cum_total += len(br)
            xs.append(cum_total)
            ys.append(100 * cum_pass / cum_total)
        color = COLORS.get(meta["label"], "#4daf4a")
        lw = 2.5 if meta["is_baseline"] else 1.5
        ax.plot(xs, ys, label=meta["label"], color=color, lw=lw, marker="o", markersize=3)

    # Mark freeze / start points
    max_tasks = max((sum(len(v) for v in defaultdict(list, {r.get("batch_num", 0): [r] for r in _load_results(results_root, n)}).values()) for n in experiments), default=0)
    for name, meta in experiments.items():
        freeze_pct = meta.get("evo_freeze_after_pct", 0)
        start_pct = meta.get("evo_start_after_pct", 0)
        label = meta["label"]
        color = COLORS.get(label, "#4daf4a")
        n_tasks = len(_load_results(results_root, name))
        if freeze_pct > 0:
            freeze_idx = int(n_tasks * freeze_pct / 100)
            ax.axvline(x=freeze_idx, color=color, lw=1.5, ls="--", alpha=0.7, zorder=15)
            ax.text(freeze_idx + 2, ax.get_ylim()[1] * 0.95,
                    f"{label}\nfrozen", color=color, fontsize=8,
                    va="top", ha="left", fontweight="bold")
        if start_pct > 0:
            start_idx = int(n_tasks * start_pct / 100)
            ax.axvline(x=start_idx, color=color, lw=1.5, ls="--", alpha=0.7, zorder=15)
            ax.text(start_idx + 2, ax.get_ylim()[1] * 0.95,
                    f"{label}\nstart", color=color, fontsize=8,
                    va="top", ha="left", fontweight="bold")

    ax.set_xlabel("Tasks Completed", fontsize=12)
    ax.set_ylabel("Cumulative Accuracy (%)", fontsize=12)
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3, ls="--")
    ax.set_title("FutureX: Cumulative Accuracy Over Batches", fontsize=14, fontweight="bold")
    fig.tight_layout()
    out_path = SCRIPT_DIR / "accuracy_over_batches.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path


def plot_marginal_accuracy(results_root, experiments, task_map, window=40) -> Path | None:
    """Marginal accuracy over time, ordered by task resolution date.

    Plots a sliding-window accuracy (%) for each experiment, with the
    x-axis ordered by the event resolution date extracted from the prompt.
    Excludes live_search (H0c) to focus on comparable experiments.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return None

    # -- Build global task ordering by resolution date --
    task_dates = {}
    for tid, t in task_map.items():
        rd = _extract_resolve_date(t.input)
        if rd:
            task_dates[tid] = rd
    sorted_tasks = sorted(task_dates, key=lambda t: task_dates[t])
    task_to_idx = {tid: i for i, tid in enumerate(sorted_tasks)}
    n_total = len(sorted_tasks)

    if n_total < window:
        return None

    COLORS = {
        "baseline_no_search": "#888888",
        "baseline": "#222222",
        "full_evo": "#377eb8",
        "early_freeze": "#e41a1c",
        "late_start": "#984ea3",
    }

    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor("white")

    for name, meta in experiments.items():
        # Exclude live search (H0c)
        if "live" in meta["label"]:
            continue

        results = _load_results(results_root, name)
        # Build success array indexed by global position
        success = np.full(n_total, np.nan)
        for r in results:
            tid = r["instance_id"]
            if tid in task_to_idx:
                success[task_to_idx[tid]] = 1.0 if r.get("success") else 0.0

        # Sliding window accuracy
        xs, means = [], []
        half = window // 2
        for center in range(half, n_total - half):
            w = success[center - half: center + half]
            valid = ~np.isnan(w)
            if valid.sum() < window * 0.5:
                continue
            xs.append(center)
            means.append(100.0 * np.nanmean(w[valid]))

        if not xs:
            continue

        color = COLORS.get(meta["label"], "#4daf4a")
        is_bl = meta["is_baseline"] or meta["label"] == "baseline_no_search"
        lw = 2.5 if is_bl else 1.5
        ls = "--" if meta["label"] == "baseline_no_search" else "-"
        zorder = 10 if is_bl else 5
        ax.plot(xs, means, label=meta["label"], color=color, lw=lw,
                ls=ls, zorder=zorder, alpha=0.85)

    # Mark freeze / start points
    for name, meta in experiments.items():
        if "live" in meta["label"]:
            continue
        freeze_pct = meta.get("evo_freeze_after_pct", 0)
        start_pct = meta.get("evo_start_after_pct", 0)
        label = meta["label"]
        color = COLORS.get(label, "#4daf4a")
        if freeze_pct > 0:
            freeze_idx = int(n_total * freeze_pct / 100)
            ax.axvline(x=freeze_idx, color=color, lw=1.5, ls="--", alpha=0.7, zorder=15)
            ax.text(freeze_idx + 2, ax.get_ylim()[1] * 0.95,
                    f"{label}\nfrozen", color=color, fontsize=8,
                    va="top", ha="left", fontweight="bold")
        if start_pct > 0:
            start_idx = int(n_total * start_pct / 100)
            ax.axvline(x=start_idx, color=color, lw=1.5, ls="--", alpha=0.7, zorder=15)
            ax.text(start_idx + 2, ax.get_ylim()[1] * 0.95,
                    f"{label}\nstart", color=color, fontsize=8,
                    va="top", ha="left", fontweight="bold")

    ax.axhline(y=0, color="black", lw=0.5, zorder=1)
    ax.set_xlabel("Task Index (ordered by resolution date)", fontsize=12)
    ax.set_ylabel(f"Marginal Accuracy % ({window}-task window)", fontsize=12)
    ax.legend(loc="best", fontsize=9, framealpha=0.9)
    ax.grid(True, alpha=0.3, ls="--")

    # Date annotations on top axis
    ax2 = ax.twiny()
    n_labels = min(6, n_total)
    label_indices = [int(i * (n_total - 1) / (n_labels - 1)) for i in range(n_labels)]
    ax2.set_xlim(ax.get_xlim())
    ax2.set_xticks(label_indices)
    ax2.set_xticklabels(
        [task_dates[sorted_tasks[i]] for i in label_indices],
        fontsize=8, rotation=20, ha="left",
    )

    fig.suptitle(f"FutureX: Marginal Accuracy (sliding {window}-task window)",
                 fontsize=14, fontweight="bold", y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    out_path = SCRIPT_DIR / "marginal_accuracy.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path


# -- Main --------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Analyze FutureX experiments")
    parser.add_argument("--path", default="results")
    parser.add_argument("--baseline", default=None)
    parser.add_argument("--output", default=str(REPORT_PATH))
    args = parser.parse_args()
    results_root = Path(args.path)

    experiments = discover_experiments(results_root, baseline_name=args.baseline)
    if not experiments:
        print(f"No futurex experiments found in {results_root}")
        return

    task_map = _load_tasks()

    lines = [
        "# A-Evolve-V2 FutureX Experiment Report",
        "",
        f"Auto-generated from `{results_root}` ({len(experiments)} experiments).",
        "",
        "---", "",
    ]

    lines += section_summary(results_root, experiments, task_map)
    lines += section_by_domain(results_root, experiments, task_map)
    lines += section_by_level(results_root, experiments, task_map)
    lines += section_by_month(results_root, experiments, task_map)
    lines += section_leaderboard_comparison(results_root, experiments, task_map)
    lines += section_head_to_head(results_root, experiments, task_map)
    lines += section_batch_progression(results_root, experiments)
    lines += section_artifact_growth(results_root, experiments)
    lines += section_data_integrity(results_root, experiments)

    # Figures
    fig1 = plot_accuracy_over_batches(results_root, experiments)
    if fig1:
        lines += ["## Figure: Cumulative Accuracy Over Batches", "",
                   f"![Accuracy]({fig1.name})", ""]

    fig2 = plot_marginal_accuracy(results_root, experiments, task_map)
    if fig2:
        lines += ["## Figure: Marginal Accuracy Over Time", "",
                   f"![Marginal Accuracy]({fig2.name})", "",
                   "Sliding 40-task window accuracy (%) ordered by event resolution date. "
                   "Shows local performance trends. H0c (live search) excluded.",
                   ""]

    md = "\n".join(lines)
    print(md)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md)
    print(f"\n--- Report written to {out_path} ---")


if __name__ == "__main__":
    main()
