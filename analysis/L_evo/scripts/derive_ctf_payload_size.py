#!/usr/bin/env python3
"""Derive largest-payload-byte-size bin for each CTF-Dojo challenge.

Bins (5 monotone categories):
    no-payload   : challenge ships only metadata (description / sha)
    <1KB         : largest payload file is under 1 KB
    1-10KB       : 1 KB <= largest < 10 KB
    10KB-1MB     : 10 KB <= largest < 1 MB
    >1MB         : largest payload >= 1 MB

Output: analysis/L_evo/data/ctf_payload_size.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = Path("/home/ec2-user/A-EVOLVE-V2/a-evolve")
ARCHIVE_JSON = REPO_ROOT / "data" / "ctf_archive.json"
META_NAMES = {"DESCRIPTION.md", "REHOST.md", ".flag.sha256", "flagCheck"}


def bin_size(b: int) -> str:
    if b == 0: return "no-payload"
    if b < 1_000: return "<1KB"
    if b < 10_000: return "1-10KB"
    if b < 1_000_000: return "10KB-1MB"
    return ">1MB"


def main() -> None:
    archive = json.load(open(ARCHIVE_JSON))
    out = {}
    for i, (cid, meta) in enumerate(archive.items()):
        if i % 50 == 0:
            print(f"  {i}/{len(archive)}", file=sys.stderr)
        chal = REPO_ROOT / meta.get("path", "")
        if not chal.exists() or not chal.is_dir():
            out[cid] = {"largest_bytes": 0, "size_bin": "missing", "n_payload_files": 0}
            continue
        payloads = [f for f in chal.iterdir()
                    if f.is_file() and f.name not in META_NAMES]
        largest = max((f.stat().st_size for f in payloads), default=0)
        out[cid] = {
            "largest_bytes": int(largest),
            "size_bin": bin_size(largest),
            "n_payload_files": len(payloads),
        }

    target = ROOT / "data" / "ctf_payload_size.json"
    target.write_text(json.dumps(out, indent=2))
    print(f"wrote {target}", file=sys.stderr)
    from collections import Counter
    dist = Counter(v["size_bin"] for v in out.values())
    for k in ["no-payload", "<1KB", "1-10KB", "10KB-1MB", ">1MB", "missing"]:
        if k in dist:
            print(f"  {k:<12s}  {dist[k]:4d}")


if __name__ == "__main__":
    main()
