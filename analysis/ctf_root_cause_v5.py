"""CTF Dojo root-cause analysis: full-system v4 (107/261=41.0%) vs multi-only (136/261=52.1%).

Read-only. Reads:
  - data/ctf_archive.json
  - results/ctf_dojo_structured_evo/results.jsonl   (multi-only)
  - results/ctf_dojo_structured_nav/results.jsonl   (full system)
  - results/ctf_dojo_structured_nav/routing_log.jsonl
  - trajectory_*.json (raw text, capped read)
  - flag_*.txt (sidecar submitted flag)

Writes:
  - analysis/ctf_root_cause_summary.json
  - analysis/ctf_root_cause.md

Usage:  python analysis/ctf_root_cause.py
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MULTI_DIR = ROOT / "results" / "ctf_dojo_structured_evo"
FULL_DIR = ROOT / "results" / "ctf_dojo_structured_nav"
ARCHIVE = ROOT / "data" / "ctf_archive.json"
OUT_JSON = ROOT / "analysis" / "ctf_root_cause_v5_summary.json"
OUT_MD = ROOT / "analysis" / "ctf_root_cause_v5.md"

TRAJ_MAX_CHARS = 200_000

PATTERNS = {
    "pwntools":         re.compile(r"\bpwntools\b|from pwn import"),
    "RsaCtfTool":       re.compile(r"RsaCtfTool"),
    "checksec":         re.compile(r"\bchecksec\b"),
    "binwalk":          re.compile(r"\bbinwalk\b"),
    "rsa_solver":       re.compile(r"rsa_solver\.py"),
    "precompute_cands": re.compile(r"precompute_candidates"),
    "flagcheck_oracle": re.compile(r"flagcheck_oracle"),
    "bls_forgery":      re.compile(r"bls[_-]forgery", re.I),
    "docker_error":     re.compile(r"DOCKER ERROR", re.I),
    "broken_rehost":    re.compile(r"broken rehost|MAY BE UNSOLVABLE", re.I),
    "submit_call":      re.compile(r"\[tool_use:\s*submit\b"),
    "bash_call":        re.compile(r"\[tool_use:\s*bash\b"),
    "stego_zsteg":      re.compile(r"\bzsteg\b|\bsteghide\b"),
    "github_fetch":     re.compile(r"github_fetch"),
}


# ── Loaders ─────────────────────────────────────────────────────────────

def load_archive(path: Path) -> dict[str, dict]:
    with open(path) as f:
        return json.load(f)


def load_results(path: Path) -> dict[str, dict]:
    out = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            tid = r.get("instance_id") or r.get("task_id")
            if tid:
                out[tid] = r
    return out


def load_routing(path: Path) -> dict[str, dict]:
    out = {}
    if not path.exists():
        return out
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            tid = r.get("task_id")
            if tid:
                out[tid] = r
    return out


def to_traj_id(slash_id: str) -> str:
    """Convert event/challenge → event_challenge for trajectory filename."""
    return slash_id.replace("/", "_", 1)


def traj_path(run_dir: Path, slash_id: str) -> Path:
    return run_dir / f"trajectory_{to_traj_id(slash_id)}.json"


def flag_sidecar_path(run_dir: Path, slash_id: str) -> Path:
    return run_dir / f"flag_{to_traj_id(slash_id)}.txt"


def read_traj_text(path: Path, max_chars: int = TRAJ_MAX_CHARS) -> str:
    if not path.exists():
        return ""
    try:
        with open(path, "r", errors="replace") as f:
            return f.read(max_chars)
    except Exception:
        return ""


def read_submitted_flag(run_dir: Path, slash_id: str) -> str | None:
    sidecar = flag_sidecar_path(run_dir, slash_id)
    if sidecar.exists():
        try:
            return sidecar.read_text(errors="replace").strip()
        except Exception:
            pass
    text = read_traj_text(traj_path(run_dir, slash_id))
    if not text:
        return None
    matches = re.findall(r"\[tool_use:\s*submit\][^\[]*?(\{.*?\})", text, re.DOTALL)
    if not matches:
        return None
    last = matches[-1]
    m = re.search(r'"flag"\s*:\s*"([^"]*)"', last)
    return m.group(1) if m else None


# ── Feature extraction ───────────────────────────────────────────────────

def task_features(slash_id: str, archive: dict) -> dict:
    meta = archive.get(slash_id, {})
    return {
        "category": meta.get("category", "unknown") or "unknown",
        "year": meta.get("year", 0),
        "files_count": len(meta.get("files", []) or []),
        "desc_len": len(meta.get("description", "") or ""),
        "event": meta.get("event", ""),
    }


def make_quartile_fn(values: list[int]):
    if not values:
        return lambda v: 0
    qs = statistics.quantiles(values, n=4, method="inclusive")
    def assign(v: int) -> int:
        for i, q in enumerate(qs):
            if v <= q:
                return i
        return len(qs)
    return assign


# ── Outcome classification ───────────────────────────────────────────────

def classify_outcome(row: dict) -> str:
    if not row:
        return "missing"
    if row.get("error"):
        return "errored"
    if row.get("success"):
        return "success"
    submitted = bool(row.get("submitted"))
    max_hit = bool(row.get("max_turns_hit"))
    timed_out = bool(row.get("timed_out"))
    turns = int(row.get("turns") or 0)
    if not submitted:
        if max_hit:
            return "max_turns_no_submit"
        if timed_out:
            return "timed_out_no_submit"
        return "no_submit_other"
    # submitted == True but failed
    if max_hit:
        return "max_turns_wrong_submit"
    if turns <= 5:
        return "wrong_submit_quick"
    return "wrong_submit_normal"


# ── Comparison computations ──────────────────────────────────────────────

def overlap_matrix(multi: dict, full: dict) -> dict:
    keys = set(multi.keys()) | set(full.keys())
    cells = {"both_pass": [], "multi_only": [], "full_only": [], "both_fail": []}
    for k in sorted(keys):
        m = bool(multi.get(k, {}).get("success"))
        f = bool(full.get(k, {}).get("success"))
        if m and f:
            cells["both_pass"].append(k)
        elif m and not f:
            cells["multi_only"].append(k)
        elif f and not m:
            cells["full_only"].append(k)
        else:
            cells["both_fail"].append(k)
    return cells


def stratified_pass_rate(rows: dict, archive: dict, key_fn) -> dict:
    bucket = defaultdict(lambda: [0, 0])  # bucket -> [pass, total]
    for tid, r in rows.items():
        feats = task_features(tid, archive)
        b = key_fn(tid, r, feats)
        bucket[b][1] += 1
        if r.get("success"):
            bucket[b][0] += 1
    return {str(k): {"pass": v[0], "total": v[1],
                     "rate": (v[0] / v[1] if v[1] else 0.0)}
            for k, v in bucket.items()}


def per_batch_passrate(rows: dict) -> list[dict]:
    by_batch: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    for r in rows.values():
        b = int(r.get("batch_num") or 0)
        by_batch[b][1] += 1
        if r.get("success"):
            by_batch[b][0] += 1
    out = []
    for b in sorted(by_batch.keys()):
        p, t = by_batch[b]
        out.append({"batch": b, "pass": p, "total": t,
                    "rate": (p / t if t else 0.0)})
    return out


def branch_analysis(routing: dict, multi: dict, full: dict) -> dict:
    by_branch: dict[str, list[str]] = defaultdict(list)
    for tid, r in routing.items():
        b = r.get("branch") or "main"
        by_branch[b].append(tid)
    summary = {}
    for branch, ids in by_branch.items():
        full_pass = sum(1 for k in ids if full.get(k, {}).get("success"))
        multi_pass = sum(1 for k in ids if multi.get(k, {}).get("success"))
        summary[branch] = {
            "n": len(ids),
            "full_pass": full_pass,
            "full_rate": (full_pass / len(ids) if ids else 0.0),
            "multi_pass_on_same": multi_pass,
            "multi_rate_on_same": (multi_pass / len(ids) if ids else 0.0),
            "task_ids": ids,
        }
    return summary


def failure_mode_distribution(rows: dict, ids: list[str]) -> Counter:
    return Counter(classify_outcome(rows.get(tid, {})) for tid in ids)


def lost_tasks_table(multi: dict, full: dict, archive: dict,
                     routing: dict) -> list[dict]:
    out = []
    for tid in sorted(set(multi) & set(full)):
        m = multi[tid]
        f = full[tid]
        if not (m.get("success") and not f.get("success")):
            continue
        feats = task_features(tid, archive)
        out.append({
            "id": tid,
            "category": feats["category"],
            "files_count": feats["files_count"],
            "desc_len": feats["desc_len"],
            "branch": (routing.get(tid, {}) or {}).get("branch", "main"),
            "full_outcome": classify_outcome(f),
            "full_turns": int(f.get("turns") or 0),
            "full_max_hit": bool(f.get("max_turns_hit")),
            "full_submitted": bool(f.get("submitted")),
            "multi_turns": int(m.get("turns") or 0),
            "multi_outcome": classify_outcome(m),
            "full_submitted_flag": read_submitted_flag(FULL_DIR, tid),
            "multi_submitted_flag": read_submitted_flag(MULTI_DIR, tid),
        })
    return out


# ── Trajectory mining ────────────────────────────────────────────────────

def mine_trajectory(text: str) -> dict[str, int]:
    return {name: len(p.findall(text)) for name, p in PATTERNS.items()}


def mine_run(run_dir: Path, ids: list[str]) -> dict[str, dict[str, int]]:
    out = {}
    for tid in ids:
        text = read_traj_text(traj_path(run_dir, tid))
        out[tid] = mine_trajectory(text) if text else {}
    return out


def aggregate_pattern_counts(mined: dict[str, dict[str, int]]) -> dict[str, int]:
    agg = Counter()
    for v in mined.values():
        for k, c in v.items():
            agg[k] += 1 if c > 0 else 0
    return dict(agg)


# ── Main orchestration ─────────────────────────────────────────────────

def main() -> int:
    print("Loading data...", file=sys.stderr)
    archive = load_archive(ARCHIVE)
    multi = load_results(MULTI_DIR / "results.jsonl")
    full = load_results(FULL_DIR / "results.jsonl")
    routing = load_routing(FULL_DIR / "routing_log.jsonl")

    multi_pass = sum(1 for r in multi.values() if r.get("success"))
    full_pass = sum(1 for r in full.values() if r.get("success"))
    print(f"  multi: {multi_pass}/{len(multi)}, full: {full_pass}/{len(full)}",
          file=sys.stderr)

    # ── 1. Overlap matrix ──
    matrix = overlap_matrix(multi, full)
    matrix_counts = {k: len(v) for k, v in matrix.items()}

    # ── 2. Stratified pass rates ──
    cats = lambda tid, r, f: f["category"]
    years = lambda tid, r, f: f["year"]
    fcount = lambda tid, r, f: f["files_count"]

    desc_lens = [task_features(t, archive)["desc_len"] for t in archive]
    desc_q = make_quartile_fn(desc_lens)
    descq = lambda tid, r, f: f"q{desc_q(f['desc_len'])}"
    branchk = lambda tid, r, f: (routing.get(tid, {}) or {}).get("branch", "main")

    strata = {
        "multi_by_category": stratified_pass_rate(multi, archive, cats),
        "full_by_category":  stratified_pass_rate(full, archive, cats),
        "multi_by_year":     stratified_pass_rate(multi, archive, years),
        "full_by_year":      stratified_pass_rate(full, archive, years),
        "multi_by_files":    stratified_pass_rate(multi, archive, fcount),
        "full_by_files":     stratified_pass_rate(full, archive, fcount),
        "multi_by_descq":    stratified_pass_rate(multi, archive, descq),
        "full_by_descq":     stratified_pass_rate(full, archive, descq),
        "full_by_branch":    stratified_pass_rate(full, archive, branchk),
    }

    # ── 3. Failure mode for the 46 lost tasks ──
    lost_ids = matrix["multi_only"]
    full_only_ids = matrix["full_only"]
    fm_lost = failure_mode_distribution(full, lost_ids)
    fm_full_only_in_multi = failure_mode_distribution(multi, full_only_ids)

    # ── 4. Branch analysis ──
    branches = branch_analysis(routing, multi, full)

    # ── 5. Lost tasks detail ──
    lost_table = lost_tasks_table(multi, full, archive, routing)

    # ── 6. Trajectory mining (cap to ~150 union) ──
    interesting_ids = set(lost_ids) | set(full_only_ids) | set(branches.get("branch/pwn-hard", {}).get("task_ids", []))
    interesting_ids = list(interesting_ids)[:150]
    mined_full = mine_run(FULL_DIR, interesting_ids)
    mined_multi = mine_run(MULTI_DIR, interesting_ids)

    # Pattern counts (number of trajectories where pattern appears ≥ 1×)
    full_pattern_presence = aggregate_pattern_counts(mined_full)
    multi_pattern_presence = aggregate_pattern_counts(mined_multi)

    # Specific: lost-only mining (the 46 tasks under full vs same 46 tasks under multi)
    lost_pattern_full = aggregate_pattern_counts({k: v for k, v in mined_full.items() if k in lost_ids})
    lost_pattern_multi = aggregate_pattern_counts({k: v for k, v in mined_multi.items() if k in lost_ids})

    # Quick-wrong-submit mining: tasks where full submitted ≤5 turns and failed
    quick_wrong = [tid for tid in lost_ids
                   if classify_outcome(full.get(tid, {})) == "wrong_submit_quick"]
    quick_wrong_with_broken_rehost = sum(
        1 for tid in quick_wrong
        if mined_full.get(tid, {}).get("broken_rehost", 0) > 0
    )

    # No-submit detail
    fno_submit = [tid for tid in full
                  if classify_outcome(full.get(tid, {})) in
                  ("max_turns_no_submit", "no_submit_other", "timed_out_no_submit")]
    mno_submit = [tid for tid in multi
                  if classify_outcome(multi.get(tid, {})) in
                  ("max_turns_no_submit", "no_submit_other", "timed_out_no_submit")]

    # ── 7. Per-batch trajectory ──
    multi_batch = per_batch_passrate(multi)
    full_batch = per_batch_passrate(full)

    # ── 8. Solver behavioral diff on shared-success ──
    both_pass_ids = matrix["both_pass"]
    multi_turns_shared = [int(multi[t].get("turns") or 0) for t in both_pass_ids]
    full_turns_shared = [int(full[t].get("turns") or 0) for t in both_pass_ids]

    def stats(xs: list[int]) -> dict:
        if not xs:
            return {"mean": 0, "p50": 0, "p90": 0, "n": 0}
        xs2 = sorted(xs)
        return {
            "mean": round(statistics.mean(xs2), 1),
            "p50": xs2[len(xs2) // 2],
            "p90": xs2[max(0, int(len(xs2) * 0.9) - 1)] if len(xs2) > 1 else xs2[0],
            "n": len(xs2),
        }

    # ── Compose summary ──
    summary = {
        "headline": {
            "multi_pass": multi_pass,
            "multi_total": len(multi),
            "multi_rate": round(multi_pass / len(multi), 4) if multi else 0,
            "full_pass": full_pass,
            "full_total": len(full),
            "full_rate": round(full_pass / len(full), 4) if full else 0,
            "delta_pp": round(100 * (full_pass / len(full) - multi_pass / len(multi)), 2),
        },
        "overlap_matrix": matrix,
        "overlap_counts": matrix_counts,
        "strata": strata,
        "failure_mode_lost46": dict(fm_lost),
        "failure_mode_fullonly17_in_multi": dict(fm_full_only_in_multi),
        "branch_summary": branches,
        "lost_tasks_count": len(lost_table),
        "lost_tasks": lost_table,
        "trajectory_pattern_presence": {
            "all_interesting_full": full_pattern_presence,
            "all_interesting_multi": multi_pattern_presence,
            "lost46_full": lost_pattern_full,
            "lost46_multi": lost_pattern_multi,
        },
        "quick_wrong_submit": {
            "count": len(quick_wrong),
            "with_broken_rehost_mention": quick_wrong_with_broken_rehost,
            "ids": quick_wrong,
        },
        "no_submit_breakdown": {
            "full_total": len(fno_submit),
            "full_max_turns": sum(1 for t in fno_submit
                                  if classify_outcome(full[t]) == "max_turns_no_submit"),
            "full_other": sum(1 for t in fno_submit
                              if classify_outcome(full[t]) == "no_submit_other"),
            "full_timed_out": sum(1 for t in fno_submit
                                  if classify_outcome(full[t]) == "timed_out_no_submit"),
            "full_ids": fno_submit,
            "multi_total": len(mno_submit),
            "multi_max_turns": sum(1 for t in mno_submit
                                   if classify_outcome(multi[t]) == "max_turns_no_submit"),
            "multi_other": sum(1 for t in mno_submit
                               if classify_outcome(multi[t]) == "no_submit_other"),
            "multi_timed_out": sum(1 for t in mno_submit
                                   if classify_outcome(multi[t]) == "timed_out_no_submit"),
        },
        "per_batch_multi": multi_batch,
        "per_batch_full": full_batch,
        "shared_success_turns": {
            "n": len(both_pass_ids),
            "multi": stats(multi_turns_shared),
            "full": stats(full_turns_shared),
        },
    }

    print("Writing JSON summary...", file=sys.stderr)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(summary, indent=2, default=str))

    print("Writing markdown report...", file=sys.stderr)
    write_report(summary, OUT_MD)
    print(f"Done. JSON={OUT_JSON} MD={OUT_MD}", file=sys.stderr)
    return 0


# ── Markdown writer ──────────────────────────────────────────────────────

def md_table(headers: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def write_report(s: dict, path: Path) -> None:
    h = s["headline"]
    sections = []
    sections.append("# CTF Dojo root-cause analysis: full-system v4 vs multi-only")
    sections.append("")
    sections.append("**Read-only investigation.** Source data: `results/ctf_dojo_structured_evo/` (multi), `results/ctf_dojo_structured_nav/` (full v4).")
    sections.append("")

    sections.append("## 1. Headline numbers")
    sections.append("")
    sections.append(md_table(["Run", "Pass", "Total", "Rate", "Δ vs multi"],
        [["multi-only", h["multi_pass"], h["multi_total"], f"{h['multi_rate']*100:.1f}%", "—"],
         ["full v4",    h["full_pass"],  h["full_total"],  f"{h['full_rate']*100:.1f}%",  f"{h['delta_pp']:+.2f}pp"]]))
    sections.append("")
    counts = s["overlap_counts"]
    sections.append(md_table(["Cell", "Count"],
        [[k, v] for k, v in counts.items()]))
    sections.append("")
    sections.append(f"Net for full = full_only − multi_only = {counts['full_only']} − {counts['multi_only']} = **{counts['full_only'] - counts['multi_only']:+d}**.")
    sections.append("")

    # 2. Stratified
    sections.append("## 2. Where the regression concentrates")
    sections.append("")
    sections.append("### By category")
    sections.append("")
    cm = s["strata"]["multi_by_category"]
    cf = s["strata"]["full_by_category"]
    cats_all = sorted(set(cm) | set(cf), key=lambda c: -((cm.get(c, {}).get("total") or 0) + (cf.get(c, {}).get("total") or 0)))
    rows = []
    for c in cats_all:
        m = cm.get(c, {"pass": 0, "total": 0, "rate": 0})
        f = cf.get(c, {"pass": 0, "total": 0, "rate": 0})
        n = m.get("total") or f.get("total") or 0
        d = (f["rate"] - m["rate"]) * 100
        rows.append([c, n,
                     f"{m['pass']}/{m['total']} ({m['rate']*100:.0f}%)",
                     f"{f['pass']}/{f['total']} ({f['rate']*100:.0f}%)",
                     f"{d:+.1f}pp"])
    sections.append(md_table(["Category", "N", "Multi", "Full", "Δpp"], rows))
    sections.append("")

    sections.append("### By files_count")
    sections.append("")
    fm = s["strata"]["multi_by_files"]
    ff = s["strata"]["full_by_files"]
    keys = sorted(set(fm) | set(ff))
    rows = []
    for k in keys:
        m = fm.get(k, {"pass": 0, "total": 0, "rate": 0})
        f = ff.get(k, {"pass": 0, "total": 0, "rate": 0})
        d = (f["rate"] - m["rate"]) * 100
        rows.append([k,
                     f"{m['pass']}/{m['total']} ({m['rate']*100:.0f}%)",
                     f"{f['pass']}/{f['total']} ({f['rate']*100:.0f}%)",
                     f"{d:+.1f}pp"])
    sections.append(md_table(["files_count", "Multi", "Full", "Δpp"], rows))
    sections.append("")

    sections.append("### By description-length quartile")
    sections.append("")
    dm = s["strata"]["multi_by_descq"]
    df = s["strata"]["full_by_descq"]
    keys = sorted(set(dm) | set(df))
    rows = []
    for k in keys:
        m = dm.get(k, {"pass": 0, "total": 0, "rate": 0})
        f = df.get(k, {"pass": 0, "total": 0, "rate": 0})
        d = (f["rate"] - m["rate"]) * 100
        rows.append([k,
                     f"{m['pass']}/{m['total']} ({m['rate']*100:.0f}%)",
                     f"{f['pass']}/{f['total']} ({f['rate']*100:.0f}%)",
                     f"{d:+.1f}pp"])
    sections.append(md_table(["desc-len q", "Multi", "Full", "Δpp"], rows))
    sections.append("")

    # 3. Confusion + lost-task failure modes
    sections.append("## 3. Failure-mode distribution on the 46 lost tasks (full's outcome)")
    sections.append("")
    fm_lost = s["failure_mode_lost46"]
    rows = sorted(fm_lost.items(), key=lambda x: -x[1])
    rows = [[k, v, f"{100*v/sum(fm_lost.values()):.1f}%"] for k, v in rows]
    sections.append(md_table(["Mode", "Count", "%"], rows))
    sections.append("")

    sections.append("## 4. Failure-mode on the 17 full-only-wins (multi's outcome)")
    sections.append("")
    fm_other = s["failure_mode_fullonly17_in_multi"]
    if fm_other:
        rows = sorted(fm_other.items(), key=lambda x: -x[1])
        rows = [[k, v, f"{100*v/sum(fm_other.values()):.1f}%"] for k, v in rows]
        sections.append(md_table(["Mode", "Count", "%"], rows))
        sections.append("")

    # 5. Branch isolation
    sections.append("## 5. Branch routing (full system only)")
    sections.append("")
    branches = s["branch_summary"]
    rows = []
    for b, st in sorted(branches.items()):
        rows.append([b, st["n"],
                     f"{st['full_pass']}/{st['n']} ({st['full_rate']*100:.0f}%)",
                     f"{st['multi_pass_on_same']}/{st['n']} ({st['multi_rate_on_same']*100:.0f}%)",
                     f"{(st['full_rate'] - st['multi_rate_on_same'])*100:+.1f}pp"])
    sections.append(md_table(["Branch", "N", "Full", "Multi (same tasks)", "Δpp"], rows))
    sections.append("")
    pwn_hard = branches.get("branch/pwn-hard")
    if pwn_hard:
        sections.append("### branch/pwn-hard tasks (the 20 isolated)")
        sections.append("")
        ids = pwn_hard["task_ids"]
        # Build a lookup of multi/full per task
        rows = []
        for tid in sorted(ids):
            rows.append([tid,
                         "P" if (s["overlap_matrix"].get("both_pass") and tid in s["overlap_matrix"]["both_pass"]) else
                         "P" if tid in s["overlap_matrix"]["multi_only"] else "F",
                         "P" if tid in s["overlap_matrix"]["both_pass"] or tid in s["overlap_matrix"]["full_only"] else "F"])
        sections.append(md_table(["task_id", "Multi", "Full"], rows))
        sections.append("")
        sections.append(f"**Headline for branching:** multi-only would have solved "
                        f"{pwn_hard['multi_pass_on_same']}/{pwn_hard['n']} of these "
                        f"if not isolated; the full system's branch got "
                        f"{pwn_hard['full_pass']}/{pwn_hard['n']}. "
                        f"Branching cost = "
                        f"{pwn_hard['multi_pass_on_same'] - pwn_hard['full_pass']} tasks.")
        sections.append("")

    # 6. Trajectory pattern presence (lost46)
    sections.append("## 6. Trajectory pattern presence (the 46 lost tasks)")
    sections.append("")
    sections.append("Counts = #trajectories (out of 46) where the pattern appears at least once.")
    sections.append("")
    pat_full = s["trajectory_pattern_presence"]["lost46_full"]
    pat_multi = s["trajectory_pattern_presence"]["lost46_multi"]
    rows = []
    for k in sorted(set(pat_full) | set(pat_multi)):
        rows.append([k, pat_multi.get(k, 0), pat_full.get(k, 0),
                     pat_full.get(k, 0) - pat_multi.get(k, 0)])
    sections.append(md_table(["Pattern", "multi (lost46)", "full (lost46)", "Δ"], rows))
    sections.append("")

    # 7. Quick-wrong-submit early-exit hypothesis
    qw = s["quick_wrong_submit"]
    sections.append("## 7. Early-exit-on-broken-rehost hypothesis")
    sections.append("")
    sections.append(f"- Tasks classified `wrong_submit_quick` (full submitted ≤5 turns, wrong): **{qw['count']}**")
    sections.append(f"- Of those, # with `'broken rehost' | 'MAY BE UNSOLVABLE'` in trajectory: **{qw['with_broken_rehost_mention']}**")
    sections.append("")

    # 8. No-submit breakdown
    nsb = s["no_submit_breakdown"]
    sections.append("## 8. No-submit cases")
    sections.append("")
    rows = [
        ["full", nsb["full_total"], nsb["full_max_turns"], nsb["full_other"], nsb["full_timed_out"]],
        ["multi", nsb["multi_total"], nsb["multi_max_turns"], nsb["multi_other"], nsb["multi_timed_out"]],
    ]
    sections.append(md_table(["Run", "Total no-submit", "max_turns", "other", "timed_out"], rows))
    sections.append("")

    # 9. Shared-success turns
    sst = s["shared_success_turns"]
    sections.append("## 9. Solver behavioral diff on shared-success tasks")
    sections.append("")
    rows = [
        ["multi", sst["multi"]["n"], sst["multi"]["mean"], sst["multi"]["p50"], sst["multi"]["p90"]],
        ["full",  sst["full"]["n"],  sst["full"]["mean"],  sst["full"]["p50"],  sst["full"]["p90"]],
    ]
    sections.append(md_table(["Run", "n", "mean turns", "p50", "p90"], rows))
    sections.append("")

    # 10. Per-batch
    sections.append("## 10. Per-batch pass rate")
    sections.append("")
    multi_batch = {b["batch"]: b for b in s["per_batch_multi"]}
    full_batch = {b["batch"]: b for b in s["per_batch_full"]}
    keys = sorted(set(multi_batch) | set(full_batch))
    rows = []
    for k in keys:
        m = multi_batch.get(k)
        f = full_batch.get(k)
        rows.append([k,
                     f"{m['pass']}/{m['total']} ({m['rate']*100:.0f}%)" if m else "—",
                     f"{f['pass']}/{f['total']} ({f['rate']*100:.0f}%)" if f else "—"])
    sections.append(md_table(["batch", "Multi", "Full"], rows))
    sections.append("")

    # 11. Hypotheses
    sections.append("## 11. Top hypotheses (ranked by evidence weight)")
    sections.append("")
    sections.append("See accompanying chat summary or `ctf_root_cause_summary.json` "
                    "for full numeric backing. Hypotheses are ordered by the magnitude "
                    "of evidence. The recommended action will depend on user judgment.")
    sections.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(sections))


if __name__ == "__main__":
    sys.exit(main())
