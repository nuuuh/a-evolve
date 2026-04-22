#!/usr/bin/env python3
"""Generate distribution shift figure for CTF-Dojo crypto challenges.

Shows three dimensions of how crypto challenges evolve across the catalog:
  (a) Cryptographic primitive (classical -> RSA/AES/ECC)
  (b) Input format (text file -> script+output, crypto artifacts, images)
  (c) Number of challenge files (single -> multi)

Usage:
    python evaluations/analysis_ctf_dojo/plot_distribution_shift.py
"""
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

ERAS = [
    ("2011-14", 2011, 2014),
    ("2017-18", 2017, 2018),
    ("2019-21", 2019, 2021),
    ("2022-24", 2022, 2024),
]


def classify_crypto(cid: str, info: dict) -> dict:
    files = info.get("files", [])
    desc_raw = info.get("description", "")
    desc = desc_raw.lower()
    fnames = " ".join(f.lower() for f in files)

    # --- Primitive ---
    if any(x in desc for x in ["rsa", "prime"]) or "N =" in desc_raw or "rsa" in fnames:
        prim = "RSA"
    elif any(x in desc for x in ["aes", "ecb", "cbc"]) or "aes" in fnames:
        prim = "AES / block cipher"
    elif any(x in desc for x in ["elliptic", "curve"]):
        prim = "ECC / DH"
    elif any(x in desc for x in ["diffie", "exchange"]):
        prim = "ECC / DH"
    elif "xor" in desc:
        prim = "XOR"
    else:
        prim = "Classical"

    # --- Format ---
    if any(f.endswith(".py") for f in files) or any("output" in f.lower() for f in files):
        fmt = "Script + output"
    elif any(f.endswith(x) for f in files for x in [".enc", ".pem", ".pub"]):
        fmt = "Crypto artifact"
    elif any(f.endswith(x) for f in files for x in [".png", ".jpg", ".jpeg"]):
        fmt = "Image / stego"
    elif len(files) == 0:
        fmt = "Description only"
    else:
        fmt = "Text file"

    return {"prim": prim, "fmt": fmt, "nfiles": len(files)}


def load_crypto_data(catalog_path: str = "data/ctf_archive.json"):
    with open(catalog_path) as f:
        catalog = json.load(f)
    rows = []
    for cid, info in catalog.items():
        if info.get("category") != "crypto":
            continue
        c = classify_crypto(cid, info)
        c["year"] = info.get("year", 0)
        c["cid"] = cid
        rows.append(c)
    return rows


def plot_shift(data, out_path: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    era_labels = [e[0] for e in ERAS]
    era_ranges = [(e[1], e[2]) for e in ERAS]

    # Bucket data by era
    era_data = []
    era_n = []
    for y1, y2 in era_ranges:
        items = [d for d in data if y1 <= d["year"] <= y2]
        era_data.append(items)
        era_n.append(len(items))

    # --- Shared style ---
    bar_kw = dict(edgecolor="white", linewidth=0.8)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=False)
    fig.patch.set_facecolor("white")

    # ========== Panel (a): Cryptographic primitive ==========
    ax = axes[0]
    prim_order = ["Classical", "XOR", "RSA", "AES / block cipher", "ECC / DH"]
    prim_colors = {
        "Classical": "#66c2a5",
        "XOR": "#fc8d62",
        "RSA": "#8da0cb",
        "AES / block cipher": "#e78ac3",
        "ECC / DH": "#a6d854",
    }
    x = np.arange(len(era_labels))
    bottom = np.zeros(len(era_labels))
    for prim in prim_order:
        vals = []
        for items in era_data:
            n = len(items)
            count = sum(1 for d in items if d["prim"] == prim)
            vals.append(100 * count / n if n else 0)
        vals = np.array(vals)
        if vals.sum() > 0:
            ax.bar(x, vals, bottom=bottom, label=prim,
                   color=prim_colors[prim], width=0.65, **bar_kw)
            bottom += vals

    ax.set_xticks(x)
    ax.set_xticklabels([f"{l}\n(n={n})" for l, n in zip(era_labels, era_n)], fontsize=9)
    ax.set_ylabel("% of crypto tasks", fontsize=10)
    ax.set_ylim(0, 108)
    ax.set_title("(a) Cryptographic primitive", fontsize=11, fontweight="bold")
    ax.legend(fontsize=7.5, loc="upper right", framealpha=0.9)
    ax.grid(axis="y", alpha=0.25, ls="--")

    # ========== Panel (b): Input format ==========
    ax = axes[1]
    fmt_order = ["Text file", "Description only", "Script + output",
                 "Crypto artifact", "Image / stego"]
    fmt_colors = {
        "Text file": "#66c2a5",
        "Description only": "#b3b3b3",
        "Script + output": "#8da0cb",
        "Crypto artifact": "#e78ac3",
        "Image / stego": "#fc8d62",
    }
    bottom = np.zeros(len(era_labels))
    for fmt in fmt_order:
        vals = []
        for items in era_data:
            n = len(items)
            count = sum(1 for d in items if d["fmt"] == fmt)
            vals.append(100 * count / n if n else 0)
        vals = np.array(vals)
        if vals.sum() > 0:
            ax.bar(x, vals, bottom=bottom, label=fmt,
                   color=fmt_colors[fmt], width=0.65, **bar_kw)
            bottom += vals

    ax.set_xticks(x)
    ax.set_xticklabels([f"{l}\n(n={n})" for l, n in zip(era_labels, era_n)], fontsize=9)
    ax.set_ylabel("% of crypto tasks", fontsize=10)
    ax.set_ylim(0, 108)
    ax.set_title("(b) Challenge input format", fontsize=11, fontweight="bold")
    ax.legend(fontsize=7.5, loc="upper right", framealpha=0.9)
    ax.grid(axis="y", alpha=0.25, ls="--")

    # ========== Panel (c): File count (tasks with files only) ==========
    ax = axes[2]
    # Only count tasks that ship at least 1 file (description-only excluded)
    fc_order = ["1 file", "2 files", "3+ files"]
    fc_colors = {"1 file": "#66c2a5", "2 files": "#8da0cb", "3+ files": "#e78ac3"}
    era_data_with_files = [[d for d in items if d["nfiles"] > 0] for items in era_data]
    era_n_wf = [len(items) for items in era_data_with_files]
    bottom = np.zeros(len(era_labels))
    for fc_label in fc_order:
        vals = []
        for items in era_data_with_files:
            n = len(items)
            if fc_label == "1 file":
                count = sum(1 for d in items if d["nfiles"] == 1)
            elif fc_label == "2 files":
                count = sum(1 for d in items if d["nfiles"] == 2)
            else:
                count = sum(1 for d in items if d["nfiles"] >= 3)
            vals.append(100 * count / n if n else 0)
        vals = np.array(vals)
        if vals.sum() > 0:
            ax.bar(x, vals, bottom=bottom, label=fc_label,
                   color=fc_colors[fc_label], width=0.65, **bar_kw)
            bottom += vals

    ax.set_xticks(x)
    ax.set_xticklabels([f"{l}\n(n={n})" for l, n in zip(era_labels, era_n_wf)], fontsize=9)
    ax.set_ylabel("% of crypto tasks (with files)", fontsize=10)
    ax.set_ylim(0, 108)
    ax.set_title("(c) Files per challenge", fontsize=11, fontweight="bold")
    ax.legend(fontsize=7.5, loc="upper right", framealpha=0.9)
    ax.grid(axis="y", alpha=0.25, ls="--")

    # --- Suptitle and timestamp ---
    fig.suptitle("Distribution shift in crypto challenges (80 tasks, 2011-2024)",
                 fontsize=13, fontweight="bold", y=1.02)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    fig.text(0.99, -0.02, ts, ha="right", va="top", fontsize=7, color="#999")

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {out_path}")


def classify_binary(catalog_path: str = "data/ctf_archive.json"):
    """Classify every ELF binary in the catalog by arch, linking, kernel target, stripped."""
    import os
    import re
    import subprocess

    with open(catalog_path) as f:
        catalog = json.load(f)

    rows = []
    for cid, info in catalog.items():
        year = info.get("year", 0)
        cat = info.get("category", "")
        path = info.get("path", "")
        files = info.get("files", [])

        for f in files:
            if "libc" in f.lower() or "ld-" in f.lower():
                continue  # skip shipped libc
            fpath = os.path.join(path, f)
            if not os.path.exists(fpath):
                continue
            try:
                with open(fpath, "rb") as fh:
                    if fh.read(4) != b"\x7fELF":
                        continue
            except Exception:
                continue

            r = subprocess.run(["file", fpath], capture_output=True, text=True, timeout=5)
            out = r.stdout

            arch = "i386" if ("Intel 80386" in out or "32-bit" in out) else "x86_64"
            linking = "static" if "statically linked" in out else "dynamic"
            stripped = "stripped" if ", stripped" in out else "not stripped"
            m = re.search(r"for GNU/Linux (\d+\.\d+)", out)
            kernel = m.group(1) if m else ""

            rows.append({"year": year, "cid": cid, "cat": cat,
                         "arch": arch, "linking": linking, "stripped": stripped,
                         "kernel": kernel})
            break  # one binary per task
    return rows


def plot_binary_shift(data, out_path: Path, catalog_path: str = "data/ctf_archive.json"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    era_labels = [e[0] for e in ERAS]
    era_ranges = [(e[1], e[2]) for e in ERAS]

    era_data = []
    era_n = []
    for y1, y2 in era_ranges:
        items = [d for d in data if y1 <= d["year"] <= y2]
        era_data.append(items)
        era_n.append(len(items))

    bar_kw = dict(edgecolor="white", linewidth=0.8)
    fig, ax = plt.subplots(1, 1, figsize=(8, 5))
    fig.patch.set_facecolor("white")
    x = np.arange(len(era_labels))
    # Re-classify ALL tasks by what runtime they assume
    import os as _os
    with open(catalog_path) as _f:
        _catalog = json.load(_f)
    dep_era_data = []
    dep_era_n = []
    for y1, y2 in era_ranges:
        items = [(c, i) for c, i in _catalog.items() if y1 <= i.get("year", 0) <= y2]
        dep_era_data.append(items)
        dep_era_n.append(len(items))

    dep_order = ["Text / description", "ELF binary (glibc)", "ELF + shipped libc",
                 "Python script", "Other"]
    dep_colors = {
        "Text / description": "#66c2a5",
        "ELF binary (glibc)": "#8da0cb",
        "ELF + shipped libc": "#e78ac3",
        "Python script": "#fc8d62",
        "Other": "#b3b3b3",
    }

    bottom = np.zeros(len(era_labels))
    for dep_label in dep_order:
        vals = []
        for items in dep_era_data:
            n = len(items)
            count = 0
            for cid, info in items:
                files = info.get("files", [])
                path = info.get("path", "")
                has_libc = any("libc" in f.lower() or "ld-" in f.lower() for f in files)
                has_py = any(f.endswith(".py") for f in files)
                has_elf = False
                for f in files:
                    fpath = _os.path.join(path, f)
                    if _os.path.exists(fpath):
                        try:
                            with open(fpath, "rb") as fh:
                                if fh.read(4) == b"\x7fELF":
                                    has_elf = True
                                    break
                        except Exception:
                            pass

                if dep_label == "ELF + shipped libc" and has_libc:
                    count += 1
                elif dep_label == "ELF binary (glibc)" and has_elf and not has_libc:
                    count += 1
                elif dep_label == "Python script" and has_py and not has_elf:
                    count += 1
                elif dep_label == "Text / description" and not has_elf and not has_py and not has_libc:
                    count += 1
                elif dep_label == "Other":
                    pass  # handled by exclusion
            vals.append(100 * count / n if n else 0)
        vals = np.array(vals)
        if vals.sum() > 0:
            ax.bar(x, vals, bottom=bottom, label=dep_label,
                   color=dep_colors[dep_label], width=0.65, **bar_kw)
            bottom += vals

    ax.set_xticks(x)
    ax.set_xticklabels([f"{l}\n(n={n})" for l, n in zip(era_labels, dep_era_n)], fontsize=9)
    ax.set_ylabel("% of all tasks", fontsize=10)
    ax.set_ylim(0, 108)
    ax.set_title("(b) Runtime dependency assumed", fontsize=11, fontweight="bold")
    ax.legend(fontsize=7.5, loc="upper right", framealpha=0.9)
    ax.grid(axis="y", alpha=0.25, ls="--")

    fig.suptitle("Distribution shift in runtime dependencies (261 tasks, 2011-2024)",
                 fontsize=13, fontweight="bold", y=1.02)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    fig.text(0.99, -0.02, ts, ha="right", va="top", fontsize=7, color="#999")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {out_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default="data/ctf_archive.json")
    args = parser.parse_args()

    data = load_crypto_data(args.catalog)
    print(f"Loaded {len(data)} crypto challenges")
    plot_shift(data, SCRIPT_DIR / "shift_crypto.png")

    bin_data = classify_binary(args.catalog)
    print(f"Loaded {len(bin_data)} challenge binaries")
    plot_binary_shift(bin_data, SCRIPT_DIR / "shift_binary.png", args.catalog)


if __name__ == "__main__":
    main()
