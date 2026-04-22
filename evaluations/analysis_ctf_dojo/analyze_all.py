#!/usr/bin/env python3
"""Comprehensive analysis of A-Evolve-V2 CTF-Dojo experiments.

Auto-discovers ctf_dojo experiments from the results directory. Outputs
Markdown report and two figures (cumulative accuracy over batches,
marginal accuracy by category).

Usage:
    python evaluations/analysis_ctf_dojo/analyze_all.py
    python evaluations/analysis_ctf_dojo/analyze_all.py --path results
    python evaluations/analysis_ctf_dojo/analyze_all.py --catalog data/ctf_archive.json
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
REPORT_PATH = SCRIPT_DIR / "auto_report.md"


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
        results_root / name / "ctf_dojo" / "evolution" / "history.jsonl",
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
    candidates = [
        f"{name}.yaml",
        f"{name.replace('ctf_dojo_', '')}.yaml",
        f"ctf_dojo_{name.replace('ctf_dojo_', '')}.yaml",
    ]
    for fname in candidates:
        p = Path("experiments/ctf_dojo/configs") / fname
        if p.exists():
            with open(p) as f:
                return yaml.safe_load(f) or {}
    return {}


def _load_catalog(catalog_path: str) -> dict:
    """Load CTF catalog and return dict keyed by challenge id."""
    p = Path(catalog_path)
    if not p.exists():
        return {}
    with open(p) as f:
        return json.load(f)


def _get_category(result: dict, catalog: dict) -> str:
    """Extract category from result detail or catalog."""
    iid = result["instance_id"]
    # Try catalog first
    if iid in catalog:
        cat = catalog[iid].get("category", "")
        if cat:
            return cat
    # Fallback: parse from detail string "CORRECT flag for X (category)"
    detail = result.get("detail", "")
    m = re.search(r'\((\w+)\)\s*$', detail)
    if m:
        return m.group(1)
    return "unknown"


def _get_year(result: dict, catalog: dict) -> int:
    """Extract year from catalog or instance_id."""
    iid = result["instance_id"]
    if iid in catalog:
        return catalog[iid].get("year", 0)
    m = re.search(r'(20\d{2})', iid)
    return int(m.group(1)) if m else 0


def _get_event(result: dict, catalog: dict) -> str:
    iid = result["instance_id"]
    if iid in catalog:
        return catalog[iid].get("event", iid.split("/")[0])
    return iid.split("/")[0]


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


def _acc_str(passed, total):
    if not total:
        return "-"
    return f"{passed}/{total} ({100*passed/total:.0f}%)"


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
        if not d.is_dir() or not d.name.startswith("ctf_dojo_"):
            continue
        if not (d / "results.jsonl").exists():
            continue
        name = d.name
        hist = _load_history(results_root, name)
        has_evo = any(not h.get("skipped", True) for h in hist)
        cfg = _load_experiment_config(name)

        if baseline_name:
            is_baseline = name == baseline_name
        else:
            is_baseline = name == "ctf_dojo_baseline"

        experiments[name] = {
            "label": name.replace("ctf_dojo_", ""),
            "has_evo": has_evo,
            "is_baseline": is_baseline,
            "evo_start_after_pct": cfg.get("evo_start_after_pct", 0),
            "evo_freeze_after_pct": cfg.get("evo_freeze_after_pct", 0),
        }
    return experiments


# -- Sections -----------------------------------------------------------------

def section_intro() -> list[str]:
    """Static introduction describing the benchmark and solving process."""
    return [
        "## What is CTF-Dojo?",
        "",
        "**CTF-Dojo** is a cybersecurity Capture-The-Flag benchmark built from the",
        "[ctf-archive](https://github.com/pwncollege/ctf-archive) maintained by",
        "pwn.college. It evaluates an AI agent's ability to solve real CTF challenges",
        "spanning crypto, pwn, rev, forensics, web, and misc categories.",
        "",
        "| Property | Value |",
        "|---|---|",
        "| Evaluation method | SHA-256 hash comparison of submitted flag |",
        "| Agent sandbox | Docker (Alpine Linux) with host networking |",
        "| Tools available to agent | `bash` (execute commands), `submit` (submit flag) |",
        "| Max turns per challenge | 80 tool calls |",
        "| Task timeout | 900 s (15 min) |",
        "| Solver model | Claude Sonnet 4.6 on Amazon Bedrock |",
        "",
        "Challenges are sorted chronologically by year, then event, then challenge name.",
        "The agent receives each challenge's description, category, event, year, and",
        "file list. Challenge files are mounted read-only at `/challenge/` inside the",
        "sandbox container. There is no partial credit -- binary pass/fail.",
        "",
        "### Example: `csawctf2011/crypto2` (39 turns, 157s, PASS)",
        "",
        "**Input** to the agent:",
        "```",
        "## CTF Challenge",
        "**Event**: csawctf2011  |  **Category**: crypto  |  **Year**: 2011",
        "",
        "## Description",
        "Use flagCheck to input the flag you get from the challenge",
        "",
        "## Available Files: chall.txt",
        "```",
        "",
        "**Solving process** (abbreviated):",
        "1. Agent reads `chall.txt` -- finds colon-separated hex bytes",
        "2. Decodes hex to plaintext: *\"...this week's key will be **overthrow**\"*",
        "3. Identifies `flagCheck` as a PyInstaller-packed ELF (Alpine musl can't run it)",
        "4. Extracts `flagCheck.pyc` with pyinstxtractor, finds hardcoded SHA-256 hash",
        "5. Verifies `SHA256(\"overthrow\")` matches the hash",
        "6. Calls `submit(flag=\"overthrow\")`",
        "",
        "**Evaluation**: `SHA256(\"overthrow\") == catalog_hash` --> `score=1.0`",
        "",
        "---", "",
    ]


def section_overview(catalog: dict) -> list[str]:
    out = ["## Benchmark Overview", ""]
    total = len(catalog)
    cats = defaultdict(int)
    years = defaultdict(int)
    events = set()
    for cid, info in catalog.items():
        cats[info.get("category", "unknown")] += 1
        years[info.get("year", 0)] += 1
        events.add(info.get("event", ""))

    out.append(f"**{total} challenges** from **{len(events)} CTF events** "
               f"({min(years)}--{max(years)}).")
    out.append("")
    out.append("### Category Distribution (full catalog)")
    headers = ["Category", "Count", "Share"]
    align = ["l", "r", "r"]
    rows = []
    for cat in sorted(cats, key=lambda c: -cats[c]):
        rows.append([cat or "(empty)", str(cats[cat]),
                     f"{100*cats[cat]/total:.0f}%"])
    out += _md_table(headers, rows, align)
    out.append("")

    out.append("### Year Distribution (full catalog)")
    headers = ["Year", "Count"]
    align = ["l", "r"]
    rows = [[str(y), str(years[y])] for y in sorted(years)]
    out += _md_table(headers, rows, align)
    out.append("")
    return out


def section_summary(results_root, experiments, catalog) -> list[str]:
    out = ["## Experiment Summary", ""]
    headers = ["Metric"] + [meta["label"] for meta in experiments.values()]
    align = ["l"] + ["r"] * len(experiments)

    metric_rows = defaultdict(list)
    for name, meta in experiments.items():
        results = _load_results(results_root, name)
        passed = sum(1 for r in results if r.get("success"))
        n = len(results)
        # Exclude hung/error entries from turn/elapsed/token averages
        valid = [r for r in results if not r.get("error")]
        nv = len(valid)
        turns = [r.get("turns", 0) for r in valid]
        elapsed = [r.get("elapsed", 0) for r in valid]
        in_tok = [r.get("input_tokens", 0) for r in valid]
        out_tok = [r.get("output_tokens", 0) for r in valid]
        submitted = sum(1 for r in results if r.get("submitted"))
        timed_out = sum(1 for r in results if r.get("timed_out"))
        max_turns_hit = sum(1 for r in results if r.get("max_turns_hit"))
        hung = sum(1 for r in results if r.get("error"))
        hist = _load_history(results_root, name)
        evo_cycles = sum(1 for h in hist if not h.get("skipped", True))
        mutated = sum(1 for h in hist if h.get("mutated"))
        ws = results_root / name / "ctf_dojo"
        art = count_workspace_artifacts(ws) if ws.is_dir() else {}

        metric_rows["Tasks"].append(str(n))
        metric_rows["Passed"].append(f"{passed}/{n}")
        metric_rows["**Accuracy**"].append(f"**{100*passed/n:.1f}%**" if n else "-")
        metric_rows["Submitted"].append(f"{submitted}/{n}")
        metric_rows["Timed out"].append(str(timed_out))
        metric_rows["Max turns hit"].append(str(max_turns_hit))
        metric_rows["Hung / errors"].append(str(hung))
        metric_rows["Avg turns*"].append(f"{sum(turns)/nv:.1f}" if nv else "-")
        metric_rows["Avg elapsed (s)*"].append(f"{sum(elapsed)/nv:.0f}" if nv else "-")
        metric_rows["Avg tokens (in/out)*"].append(
            f"{sum(in_tok)/nv/1000:.0f}K / {sum(out_tok)/nv/1000:.0f}K" if nv else "-")
        metric_rows["Evo cycles"].append(str(evo_cycles))
        metric_rows["Mutated"].append(str(mutated))
        metric_rows["Skills"].append(str(art.get("skills", 0)))
        metric_rows["Tools"].append(str(art.get("tools", 0)))
        metric_rows["Prompt (chars)"].append(str(art.get("prompt_chars", 0)))

    rows = [[k] + v for k, v in metric_rows.items()]
    out += _md_table(headers, rows, align)
    out.append("")
    out.append("*\\*Averages exclude hung/error entries (tasks killed at batch deadline "
               "before the agent could act).*")
    out.append("")
    return out


def section_by_category(results_root, experiments, catalog) -> list[str]:
    out = ["## Accuracy by Category", ""]

    # Collect all categories present in evaluated results
    all_cats = set()
    all_results = {}
    for name in experiments:
        results = _load_results(results_root, name)
        all_results[name] = results
        for r in results:
            all_cats.add(_get_category(r, catalog))

    headers = ["Category", "Tasks"] + [meta["label"] for meta in experiments.values()]
    align = ["l", "r"] + ["r"] * len(experiments)
    rows = []
    for cat in sorted(all_cats):
        # Count tasks per category from union of all experiments
        cat_ids = set()
        for name in experiments:
            for r in all_results[name]:
                if _get_category(r, catalog) == cat:
                    cat_ids.add(r["instance_id"])
        row = [cat, str(len(cat_ids))]
        for name in experiments:
            rmap = {r["instance_id"]: r for r in all_results[name]}
            cat_results = [r for r in all_results[name]
                           if _get_category(r, catalog) == cat]
            p = sum(1 for r in cat_results if r.get("success"))
            t = len(cat_results)
            row.append(_acc_str(p, t))
        rows.append(row)
    out += _md_table(headers, rows, align)
    out.append("")
    return out


def section_by_year(results_root, experiments, catalog) -> list[str]:
    out = ["## Accuracy by Year", ""]

    all_years = set()
    all_results = {}
    for name in experiments:
        results = _load_results(results_root, name)
        all_results[name] = results
        for r in results:
            all_years.add(_get_year(r, catalog))

    headers = ["Year", "Tasks"] + [meta["label"] for meta in experiments.values()]
    align = ["l", "r"] + ["r"] * len(experiments)
    rows = []
    for year in sorted(all_years):
        year_ids = set()
        for name in experiments:
            for r in all_results[name]:
                if _get_year(r, catalog) == year:
                    year_ids.add(r["instance_id"])
        row = [str(year), str(len(year_ids))]
        for name in experiments:
            year_results = [r for r in all_results[name]
                            if _get_year(r, catalog) == year]
            p = sum(1 for r in year_results if r.get("success"))
            t = len(year_results)
            row.append(_acc_str(p, t))
        rows.append(row)
    out += _md_table(headers, rows, align)
    out.append("")
    return out


def section_by_event(results_root, experiments, catalog) -> list[str]:
    out = ["## Accuracy by CTF Event", ""]

    all_events = set()
    all_results = {}
    for name in experiments:
        results = _load_results(results_root, name)
        all_results[name] = results
        for r in results:
            all_events.add(_get_event(r, catalog))

    headers = ["Event", "Tasks"] + [meta["label"] for meta in experiments.values()]
    align = ["l", "r"] + ["r"] * len(experiments)
    rows = []
    for event in sorted(all_events):
        event_ids = set()
        for name in experiments:
            for r in all_results[name]:
                if _get_event(r, catalog) == event:
                    event_ids.add(r["instance_id"])
        row = [event, str(len(event_ids))]
        for name in experiments:
            event_results = [r for r in all_results[name]
                             if _get_event(r, catalog) == event]
            p = sum(1 for r in event_results if r.get("success"))
            t = len(event_results)
            row.append(_acc_str(p, t))
        rows.append(row)
    out += _md_table(headers, rows, align)
    out.append("")
    return out


def section_head_to_head(results_root, experiments, catalog) -> list[str]:
    baseline_name = next((n for n, m in experiments.items() if m["is_baseline"]), None)
    if not baseline_name:
        return []
    out = [f"## Head-to-Head vs `{experiments[baseline_name]['label']}`", ""]
    base = {r["instance_id"]: r.get("success", False)
            for r in _load_results(results_root, baseline_name)}
    headers = ["Experiment", "Shared", "Both pass", "Improved", "Regressed", "Net"]
    align = ["l", "r", "r", "r", "r", "r"]
    rows = []
    for name, meta in experiments.items():
        if meta["is_baseline"]:
            continue
        rmap = {r["instance_id"]: r.get("success", False)
                for r in _load_results(results_root, name)}
        common = set(base) & set(rmap)
        both = sum(1 for i in common if base[i] and rmap[i])
        imp_ids = [i for i in common if not base[i] and rmap[i]]
        reg_ids = [i for i in common if base[i] and not rmap[i]]
        rows.append([meta["label"], str(len(common)),
                     str(both), str(len(imp_ids)), str(len(reg_ids)),
                     f"{len(imp_ids)-len(reg_ids):+d}"])
        if imp_ids or reg_ids:
            out += _md_table(headers, rows, align)
            rows = []
            out.append("")
            if imp_ids:
                out.append(f"**Improved** ({meta['label']} passes, baseline fails):")
                for iid in sorted(imp_ids):
                    cat = catalog.get(iid, {}).get("category", "?")
                    out.append(f"- `{iid}` ({cat})")
                out.append("")
            if reg_ids:
                out.append(f"**Regressed** ({meta['label']} fails, baseline passes):")
                for iid in sorted(reg_ids):
                    cat = catalog.get(iid, {}).get("category", "?")
                    out.append(f"- `{iid}` ({cat})")
                out.append("")
    if rows:
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
            rows.append([str(bn), str(len(br)), str(p),
                         f"{100*p/len(br):.0f}%", mut])
        out += _md_table(headers, rows, align)
        out.append("")
    return out


def section_artifact_growth(results_root, experiments) -> list[str]:
    out = ["## Artifact Growth Over Evolution", ""]
    found = False
    for name, meta in experiments.items():
        if not meta["has_evo"]:
            continue
        ws = results_root / name / "ctf_dojo"
        if not (ws / ".git").is_dir():
            continue
        hist = _load_history(results_root, name)
        if not hist:
            continue
        found = True
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
        headers = ["Cycle", "Score", "Skills", "Tools", "Prompt", "Mutated"]
        align = ["r"] * 6
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
                tools = len([l for l in tree.splitlines()
                             if l.endswith(".py")]) if tree else 0
                prompt = git("show", f"{tag}:prompts/system.md")
                prompt_len = len(prompt)
                art = {"skills": skills, "tools": tools, "prompt": prompt_len}
            else:
                art = {"skills": 0, "tools": 0, "prompt": 0}
            rows.append([
                str(cyc), f"{h.get('batch_score', 0):.2f}",
                str(art["skills"]), str(art["tools"]),
                f"{art['prompt']}c", str(h.get("mutated", False)),
            ])
        out += _md_table(headers, rows, align)
        out.append("")
    if not found:
        out.append("*(No experiments with evolution history found.)*")
        out.append("")
    return out


def section_data_integrity(results_root, experiments) -> list[str]:
    out = ["## Data Integrity", ""]
    headers = ["Experiment", "Raw", "Dedup", "Dupes", "Errors",
               "Timeouts", "MaxTurns", "No submit"]
    align = ["l"] + ["r"] * 7
    rows = []
    for name, meta in experiments.items():
        raw = load_jsonl(results_root / name / "results.jsonl")
        deduped = _dedup_results(raw)
        dupes = len(raw) - len(deduped)
        errors = sum(1 for r in deduped if r.get("error"))
        timeouts = sum(1 for r in deduped if r.get("timed_out"))
        max_turns = sum(1 for r in deduped if r.get("max_turns_hit"))
        no_submit = sum(1 for r in deduped if not r.get("submitted"))
        rows.append([meta["label"], str(len(raw)), str(len(deduped)),
                     str(dupes), str(errors), str(timeouts),
                     str(max_turns), str(no_submit)])
    out += _md_table(headers, rows, align)
    out.append("")
    return out


# -- Plotting -----------------------------------------------------------------

def plot_accuracy_over_batches(results_root, experiments) -> Path | None:
    """Cumulative accuracy rolling over individual tasks — step plot matching
    the polybench performance_over_time style."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    LABEL_COLORS = {
        "baseline": "#222222",
        "full_evo": "#377eb8",
        "early_freeze": "#e41a1c",
        "late_start": "#984ea3",
    }

    # Build global task ordering (union of all experiments, sorted by batch+id)
    all_ids: set[str] = set()
    task_order: dict[str, int] = {}
    for name in experiments:
        for r in _load_results(results_root, name):
            all_ids.add(r["instance_id"])
    # Assign index by sorting on (batch_num, instance_id)
    all_results_union: list[dict] = []
    for name in experiments:
        for r in _load_results(results_root, name):
            all_results_union.append(r)
    seen_ids: set[str] = set()
    for r in sorted(all_results_union,
                    key=lambda x: (x.get("batch_num", 0), x["instance_id"])):
        if r["instance_id"] not in seen_ids:
            task_order[r["instance_id"]] = len(seen_ids)
            seen_ids.add(r["instance_id"])

    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor("white")

    for name, meta in experiments.items():
        results = _load_results(results_root, name)
        if not results:
            continue

        # Sort by global task order
        data = [(task_order.get(r["instance_id"], 0), r) for r in results
                if r["instance_id"] in task_order]
        data.sort(key=lambda x: x[0])

        # Rolling cumulative accuracy per task
        xs, ys = [], []
        cum_pass, cum_total = 0, 0
        for idx, r in data:
            cum_total += 1
            if r.get("success"):
                cum_pass += 1
            xs.append(idx)
            ys.append(100.0 * cum_pass / cum_total)

        label = meta["label"]
        is_bl = meta["is_baseline"]
        color = LABEL_COLORS.get(label, "#4daf4a")
        lw = 2.4 if is_bl else 1.5
        zorder = 10 if is_bl else 5

        ax.step(xs, ys, where="post",
                label=f"{label} ({len(data)} tasks)",
                color=color, lw=lw, zorder=zorder, alpha=0.85)

        # Endpoint marker
        if xs:
            ax.plot(xs[-1], ys[-1], "o", color=color, markersize=5,
                    zorder=zorder + 1)

    # Mark freeze / start points
    n_tasks_total = len(task_order)
    for name, meta in experiments.items():
        freeze_pct = meta.get("evo_freeze_after_pct", 0)
        start_pct = meta.get("evo_start_after_pct", 0)
        label = meta["label"]
        color = LABEL_COLORS.get(label, "#4daf4a")
        if freeze_pct > 0:
            freeze_idx = int(n_tasks_total * freeze_pct / 100)
            ax.axvline(x=freeze_idx, color=color, lw=1.5, ls="--", alpha=0.7, zorder=15)
            ax.text(freeze_idx + 2, ax.get_ylim()[1] * 0.95,
                    f"{label}\nfrozen", color=color, fontsize=8,
                    va="top", ha="left", fontweight="bold")
        if start_pct > 0:
            start_idx = int(n_tasks_total * start_pct / 100)
            ax.axvline(x=start_idx, color=color, lw=1.5, ls="--", alpha=0.7, zorder=15)
            ax.text(start_idx + 2, ax.get_ylim()[1] * 0.95,
                    f"{label}\nstart", color=color, fontsize=8,
                    va="top", ha="left", fontweight="bold")

    ax.axhline(y=50, color="grey", lw=0.8, ls=":", alpha=0.5, zorder=1)
    ax.set_xlabel("Task Index (ordered by batch)", fontsize=12)
    ax.set_ylabel("Cumulative Accuracy (%)", fontsize=12)
    ax.legend(loc="best", fontsize=9, framealpha=0.9)
    ax.grid(True, alpha=0.3, ls="--")
    fig.suptitle("CTF-Dojo: Cumulative Accuracy Over Tasks",
                 fontsize=14, fontweight="bold", y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    out_path = SCRIPT_DIR / "accuracy_over_batches.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path


def plot_marginal_accuracy(results_root, experiments, catalog,
                           window=40, n_boot=500) -> Path | None:
    """Marginal accuracy with sliding window and bootstrap CIs — matching
    the polybench marginal_cwr style (lines + fill_between bands)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return None

    LABEL_COLORS = {
        "baseline": "#222222",
        "full_evo": "#377eb8",
        "early_freeze": "#e41a1c",
        "late_start": "#984ea3",
    }

    # Build global task ordering
    all_results_union: list[dict] = []
    for name in experiments:
        all_results_union.extend(_load_results(results_root, name))
    seen_ids: set[str] = set()
    task_order: dict[str, int] = {}
    for r in sorted(all_results_union,
                    key=lambda x: (x.get("batch_num", 0), x["instance_id"])):
        if r["instance_id"] not in seen_ids:
            task_order[r["instance_id"]] = len(seen_ids)
            seen_ids.add(r["instance_id"])
    n_tasks_total = len(task_order)

    if n_tasks_total < window:
        return None

    series: list[dict] = []
    for name, meta in experiments.items():
        results = _load_results(results_root, name)

        # Build pass/fail array indexed by global task position
        scores = np.full(n_tasks_total, np.nan)
        for r in results:
            if r["instance_id"] in task_order:
                idx = task_order[r["instance_id"]]
                scores[idx] = 1.0 if r.get("success") else 0.0

        # Sliding window accuracy with bootstrap CIs
        xs, means, lo, hi = [], [], [], []
        half = window // 2
        for center in range(half, n_tasks_total - half):
            w = scores[center - half : center + half]
            valid = ~np.isnan(w)
            if valid.sum() < window * 0.3:
                continue
            s = w[valid]
            acc = 100.0 * s.mean()

            # Bootstrap CI (90%)
            rng = np.random.default_rng(center)
            n_valid = len(s)
            boot_accs = []
            for _ in range(n_boot):
                sample = s[rng.integers(0, n_valid, size=n_valid)]
                boot_accs.append(100.0 * sample.mean())
            boot_arr = np.array(boot_accs)
            ci_lo = float(np.percentile(boot_arr, 5))
            ci_hi = float(np.percentile(boot_arr, 95))

            xs.append(center)
            means.append(acc)
            lo.append(ci_lo)
            hi.append(ci_hi)

        if not xs:
            continue

        label = meta["label"]
        is_bl = meta["is_baseline"]
        color = LABEL_COLORS.get(label, "#4daf4a")
        series.append({
            "label": label, "is_bl": is_bl,
            "xs": xs, "means": means, "lo": lo, "hi": hi,
            "color": color,
        })

    if not series:
        return None

    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor("white")

    for s in series:
        lw = 2.4 if s["is_bl"] else 1.5
        zorder = 10 if s["is_bl"] else 5
        ax.plot(s["xs"], s["means"], label=s["label"],
                color=s["color"], lw=lw, zorder=zorder, alpha=0.85)
        ax.fill_between(s["xs"], s["lo"], s["hi"],
                        color=s["color"], alpha=0.15, zorder=zorder - 1)

    # Mark freeze points for early_freeze / late_start experiments
    for name, meta in experiments.items():
        freeze_pct = meta.get("evo_freeze_after_pct", 0)
        start_pct = meta.get("evo_start_after_pct", 0)
        label = meta["label"]
        color = LABEL_COLORS.get(label, "#4daf4a")
        if freeze_pct > 0:
            freeze_idx = int(n_tasks_total * freeze_pct / 100)
            ax.axvline(x=freeze_idx, color=color, lw=1.5, ls="--", alpha=0.7, zorder=15)
            ax.text(freeze_idx + 2, ax.get_ylim()[1] * 0.95,
                    f"{label}\nfrozen", color=color, fontsize=8,
                    va="top", ha="left", fontweight="bold")
        if start_pct > 0:
            start_idx = int(n_tasks_total * start_pct / 100)
            ax.axvline(x=start_idx, color=color, lw=1.5, ls="--", alpha=0.7, zorder=15)
            ax.text(start_idx + 2, ax.get_ylim()[1] * 0.95,
                    f"{label}\nstart", color=color, fontsize=8,
                    va="top", ha="left", fontweight="bold")

    ax.axhline(y=50, color="grey", lw=0.8, ls=":", alpha=0.5, zorder=1)
    ax.set_xlabel("Task Index (ordered by batch)", fontsize=12)
    ax.set_ylabel(f"Marginal Accuracy % (sliding {window}-task window)", fontsize=12)
    ax.legend(loc="best", fontsize=9, framealpha=0.9)
    ax.grid(True, alpha=0.3, ls="--")
    fig.suptitle(f"Marginal Accuracy (sliding {window}-task window)",
                 fontsize=14, fontweight="bold", y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    out_path = SCRIPT_DIR / "marginal_accuracy.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path


# -- Main --------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Analyze CTF-Dojo experiments")
    parser.add_argument("--path", default="results",
                        help="Results directory (default: results)")
    parser.add_argument("--catalog", default="data/ctf_archive.json",
                        help="CTF catalog JSON path")
    parser.add_argument("--baseline", default=None,
                        help="Name of baseline experiment directory")
    parser.add_argument("--output", default=str(REPORT_PATH),
                        help="Output report path")
    args = parser.parse_args()
    results_root = Path(args.path)

    experiments = discover_experiments(results_root, baseline_name=args.baseline)
    if not experiments:
        print(f"No ctf_dojo experiments found in {results_root}")
        return

    catalog = _load_catalog(args.catalog)
    print(f"Loaded catalog: {len(catalog)} challenges")
    print(f"Found experiments: {list(experiments.keys())}")

    lines = [
        "# A-Evolve-V2 CTF-Dojo Experiment Report",
        "",
        f"Auto-generated from `{results_root}` ({len(experiments)} experiments, "
        f"{len(catalog)} challenges in catalog).",
        "",
        "---", "",
    ]

    lines += section_intro()
    lines += section_overview(catalog)
    lines += section_summary(results_root, experiments, catalog)
    lines += section_by_category(results_root, experiments, catalog)
    lines += section_by_year(results_root, experiments, catalog)
    lines += section_by_event(results_root, experiments, catalog)
    lines += section_head_to_head(results_root, experiments, catalog)
    lines += section_batch_progression(results_root, experiments)
    lines += section_artifact_growth(results_root, experiments)
    lines += section_data_integrity(results_root, experiments)

    # Figures
    fig1 = plot_accuracy_over_batches(results_root, experiments)
    if fig1:
        lines += ["## Figure: Cumulative Accuracy Over Batches", "",
                   f"![Accuracy]({fig1.name})", ""]

    fig2 = plot_marginal_accuracy(results_root, experiments, catalog)
    if fig2:
        lines += ["## Figure: Accuracy by Category", "",
                   f"![Category Accuracy]({fig2.name})", "",
                   "Per-category solve rate comparison across experiments.",
                   ""]

    md = "\n".join(lines)
    print(md)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md)
    print(f"\n--- Report written to {out_path} ---")


if __name__ == "__main__":
    main()
