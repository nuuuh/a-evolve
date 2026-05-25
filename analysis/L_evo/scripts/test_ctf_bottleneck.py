#!/usr/bin/env python3
"""Verification probe for the CTF-Dojo payload-size bottleneck.

Reads:
  analysis/L_evo/data/ctf_payload_size.json  (instance_id -> {size_bin, ...})
  results/ctf_dojo_<run>/results.jsonl       for each harness run

Prints per-size_bin x per-run pass rate. Expected:
    bin            n   baseline  full_evo  gepa_lite  mh_lite  continual  skillos  structured_evo
    no-payload    11    54.5%     81.8%     63.6%     63.6%     45.5%     54.5%     90.9%
    <1KB          45    53.3%     66.7%     55.6%     60.0%     22.2%     40.0%     77.8%
    1-10KB        74    39.2%     48.6%     48.6%     41.9%     32.4%     37.8%     50.0%
    10KB-1MB      85    34.1%     34.1%     35.3%     35.3%     23.5%     21.2%     42.4%
    >1MB          46    19.6%     30.4%     30.4%     26.1%     17.4%     15.2%     39.1%
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = Path("/home/ec2-user/A-EVOLVE-V2/a-evolve")
RESULTS = REPO_ROOT / "results"
SIZE_JSON = ROOT / "data" / "ctf_payload_size.json"

RUNS = [
    "ctf_dojo_baseline",
    "ctf_dojo_full_evo",
    "ctf_dojo_gepa_lite",
    "ctf_dojo_mh_lite",
    "ctf_dojo_continual_harness",
    "ctf_dojo_skillos",
    "ctf_dojo_structured_evo",
]
SHORT = {
    "ctf_dojo_baseline": "baseline",
    "ctf_dojo_full_evo": "full_evo",
    "ctf_dojo_gepa_lite": "gepa_lite",
    "ctf_dojo_mh_lite": "mh_lite",
    "ctf_dojo_continual_harness": "continual",
    "ctf_dojo_skillos": "skillos",
    "ctf_dojo_structured_evo": "structured_evo",
}

BIN_ORDER = ["no-payload", "<1KB", "1-10KB", "10KB-1MB", ">1MB"]


def load_run(name: str) -> dict[str, bool]:
    out = {}
    for line in (RESULTS / name / "results.jsonl").read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        tid = r.get("task_id") or r.get("instance_id")
        if tid:
            out[tid] = bool(r.get("success"))
    return out


def main() -> None:
    sizes = json.load(open(SIZE_JSON))
    runs = {r: load_run(r) for r in RUNS}

    bins = defaultdict(lambda: {"n": 0, **{r: 0 for r in RUNS}})
    for cid, info in sizes.items():
        b = info.get("size_bin", "?")
        if b == "missing":
            continue
        bins[b]["n"] += 1
        for r in RUNS:
            if runs[r].get(cid):
                bins[b][r] += 1

    header = ["bin", "n"] + [SHORT[r] for r in RUNS]
    widths = [12, 4] + [10] * len(RUNS)
    print("  ".join(f"{h:>{w}s}" for h, w in zip(header, widths)))
    for b in BIN_ORDER:
        info = bins[b]
        n = info["n"]
        if n == 0:
            continue
        cells = [b, str(n)]
        for r in RUNS:
            cells.append(f"{info[r] / n * 100:>9.1f}%")
        print("  ".join(f"{c:>{w}s}" for c, w in zip(cells, widths)))


if __name__ == "__main__":
    main()
