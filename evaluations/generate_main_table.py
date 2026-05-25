#!/usr/bin/env python3
"""Generate the paper main table directly from ``results/``.

The script emits two artifacts:
  1. a Markdown preview on stdout, and
  2. a wide CSV table under ``evaluations/main_table.csv`` by default.

The CSV is intentionally shaped like the LaTeX table: rows are metrics and
columns are systems. Missing result folders are emitted as ``--``.
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


POLYBENCH_TOTAL = 5075


@dataclass(frozen=True)
class Method:
    key: str
    label: str
    pb_dir: str | None
    ctf_dir: str | None
    fx_dir: str | None
    repair_polybench_return: bool = False


METHODS = [
    Method("sonnet", "Sonnet", "polybench_baseline", "ctf_dojo_baseline", "futurex_baseline"),
    Method("deepseek", "DeepSeek", None, None, None),
    Method("kimi", "Kimi", None, None, None),
    Method("a_evolve", "A-Evolve", "polybench_full_evo", "ctf_dojo_full_evo", "futurex_full_evo"),
    Method("gepa", "GEPA", "polybench_gepa_lite", "ctf_dojo_gepa_lite", "futurex_gepa_lite"),
    Method("meta_harness", "Meta Harness", "polybench_mh_lite", "ctf_dojo_mh_lite", "futurex_mh_lite"),
    Method(
        "continual_harness",
        "Continual Harness",
        "polybench_continual_harness",
        "ctf_dojo_continual_harness",
        "futurex_continual_harness",
    ),
    Method("skillos", "SkillOS", "polybench_skillos", "ctf_dojo_skillos", "futurex_skillos", True),
    Method("octotools", "OctoTools", "polybench_octo_expert", "ctf_dojo_octo_expert", "futurex_octo_expert"),
    Method(
        "multi_agent",
        "Multi-agent",
        "polybench_structured_evo",
        "ctf_dojo_structured_evo",
        "futurex_structured_evo",
    ),
    Method("nav", "Navigation", "polybench_navigation", "ctf_dojo_navigation", "futurex_navigation"),
    Method(
        "full_system",
        "Full System",
        "polybench_structured_nav",
        "ctf_dojo_structured_nav",
        "futurex_structured_nav",
    ),
]


def load_results(path: Path) -> list[dict]:
    """Load JSONL results and keep the first row per instance_id."""
    if not path.exists():
        return []

    results = []
    seen = set()
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue

        instance_id = row.get("instance_id", "")
        if instance_id in seen:
            continue
        seen.add(instance_id)
        results.append(row)
    return results


# -- PolyBench ---------------------------------------------------------------

_PRICE_CACHE: dict[Path, dict[str, float]] = {}


def _norm_label(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().upper())


def _polybench_side_prices(run_dir: Path, instance_id: str) -> dict[str, float]:
    """Extract outcome -> price from the saved PolyBench task prompt.

    Result rows do not store ``outcomes``/``outcome_prices``. The trajectory
    prompt does, and it is enough to repair the known fallback-price artifact
    where non-YES labels were indexed as the second binary outcome.
    """
    traj_path = run_dir / f"trajectory_{instance_id}.json"
    if traj_path in _PRICE_CACHE:
        return _PRICE_CACHE[traj_path]

    prices: dict[str, float] = {}
    try:
        trajectory = json.loads(traj_path.read_text())
    except (OSError, json.JSONDecodeError):
        _PRICE_CACHE[traj_path] = prices
        return prices

    content = ""
    if isinstance(trajectory, list) and trajectory:
        content = str(trajectory[0].get("content", ""))

    match = re.search(r"Last Known Prices:\s*(\[[^\n\r]+?\])", content)
    if not match:
        _PRICE_CACHE[traj_path] = prices
        return prices

    try:
        price_values = [float(x) for x in ast.literal_eval(match.group(1))]
    except (SyntaxError, ValueError, TypeError):
        _PRICE_CACHE[traj_path] = prices
        return prices

    outcome_labels = [
        _norm_label(m.group(1))
        for m in re.finditer(r"^Outcome:\s*(.+?)\s*$", content, flags=re.MULTILINE)
    ]
    for label, price in zip(outcome_labels, price_values):
        if 0.0 < price < 1.0:
            prices[label] = price

    _PRICE_CACHE[traj_path] = prices
    return prices


def _corrected_polybench_profit(row: dict, run_dir: Path | None) -> tuple[float, float, bool]:
    """Return ``(investment, profit, repaired)`` for one PolyBench trade.

    Some stored runs used a fallback-price helper that mapped every non-YES
    side to ``outcome_prices[1]``. For markets whose first outcome was a
    non-YES label such as ``OVER`` and priced near 1.0, this created impossible
    1999x returns. When the saved prompt provides the correct side price, we
    repair only those clearly inconsistent BUY-success fallback artifacts.
    """
    inv = float(row.get("cwr_investment") or 0.0)
    profit = float(row.get("cwr_profit") or 0.0)
    if not run_dir or inv <= 0:
        return inv, profit, False

    decision = _norm_label(row.get("decision"))
    side = _norm_label(row.get("side"))
    if decision != "BUY" or side in {"YES", "NO"} or not row.get("success"):
        return inv, profit, False

    try:
        raw_return = float(row.get("raw_return") or 0.0)
    except (TypeError, ValueError):
        return inv, profit, False
    if raw_return <= 1.0:
        return inv, profit, False

    price = _polybench_side_prices(run_dir, str(row.get("instance_id", ""))).get(side)
    if not price:
        return inv, profit, False

    expected_return = (1.0 / price) - 1.0
    # Only repair large disagreements; ordinary order-book VWAP variation stays
    # untouched. This preserves genuine long-shot wins when the side price is low.
    if expected_return < raw_return / 10.0:
        return inv, inv * expected_return, True
    return inv, profit, False


def polybench_metrics(results: list[dict], run_dir: Path | None = None) -> dict:
    if not results:
        return {}

    traded = [
        row for row in results
        if not row.get("gated") and _norm_label(row.get("decision")) != "SKIP"
    ]
    correct = [row for row in traded if row.get("success")]

    cwr_inv = 0.0
    cwr_profit = 0.0
    repaired = 0
    for row in traded:
        inv, profit, did_repair = _corrected_polybench_profit(row, run_dir)
        cwr_inv += inv
        cwr_profit += profit
        repaired += int(did_repair)

    coverage = len(traded) / POLYBENCH_TOTAL
    cwr_pct = (cwr_profit / cwr_inv * 100.0) if cwr_inv > 0 else 0.0

    return {
        "coverage": coverage * 100.0,
        "acc": len(correct) / POLYBENCH_TOTAL * 100.0,
        "port_ret": cwr_pct * coverage,
        "cwr": cwr_pct,
        "n_total": len(results),
        "n_traded": len(traded),
        "n_correct": len(correct),
        "n_repaired": repaired,
    }


# -- Stream Metrics -----------------------------------------------------------

def _success_sequence(results: list[dict]) -> list[float]:
    ordered = sorted(enumerate(results), key=lambda item: (item[1].get("batch_num", 1), item[0]))
    return [1.0 if row.get("success") else 0.0 for _, row in ordered]


def _relative_success_sequence(results: list[dict], baseline_results: list[dict]) -> list[float]:
    baseline_success = {
        row.get("instance_id", ""): 1.0 if row.get("success") else 0.0
        for row in baseline_results
    }
    ordered = sorted(enumerate(results), key=lambda item: (item[1].get("batch_num", 1), item[0]))
    return [
        (1.0 if row.get("success") else 0.0) - baseline_success[row.get("instance_id", "")]
        for _, row in ordered
        if row.get("instance_id", "") in baseline_success
    ]


def _ols_delta(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    n = len(values)
    xs = [i / (n - 1) for i in range(n)]
    x_bar = sum(xs) / n
    y_bar = sum(values) / n
    denom = sum((x - x_bar) ** 2 for x in xs)
    if denom <= 0:
        return 0.0
    return sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, values)) / denom


def _sliding_rates(values: list[float], window: int, step: int) -> list[float]:
    if not values:
        return []
    if len(values) <= window:
        return [sum(values) / len(values)]

    rates = []
    for start in range(0, len(values) - window + 1, step):
        rates.append(sum(values[start:start + window]) / window)
    if (len(values) - window) % step != 0:
        rates.append(sum(values[-window:]) / window)
    return rates


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    pos = q * (len(ordered) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] * (hi - pos) + ordered[hi] * (pos - lo)


def stream_metrics(
    results: list[dict],
    baseline_results: list[dict],
    q25_window: int,
    q25_step: int,
) -> dict:
    """Pass, Sonnet-adjusted OLS trend, and lower-tail sliding-window pass."""
    if not results:
        return {}

    success = _success_sequence(results)
    relative_success = _relative_success_sequence(results, baseline_results)
    pass_rate = sum(success) / len(success)
    trend = _ols_delta(relative_success) if relative_success else 0.0
    q25 = _quantile(_sliding_rates(success, q25_window, q25_step), 0.25)

    return {
        "pass": pass_rate * 100.0,
        "trend": trend * 100.0,
        "q25": q25 * 100.0,
        "n_passed": int(sum(success)),
        "n_total": len(success),
    }


# -- Table assembly -----------------------------------------------------------

def _fmt(value: float | None, digits: int = 1, signed: bool = False) -> str:
    if value is None:
        return "--"
    prefix = "+" if signed else ""
    return f"{value:{prefix}.{digits}f}"


def _method_metrics(
    results_dir: Path,
    method: Method,
    ctf_baseline: list[dict],
    fx_baseline: list[dict],
) -> dict[str, dict]:
    out: dict[str, dict] = {}

    if method.pb_dir:
        run_dir = results_dir / method.pb_dir
        repair_dir = run_dir if method.repair_polybench_return else None
        out["polybench"] = polybench_metrics(load_results(run_dir / "results.jsonl"), repair_dir)
    else:
        out["polybench"] = {}

    if method.ctf_dir:
        run_dir = results_dir / method.ctf_dir
        out["ctf"] = stream_metrics(
            load_results(run_dir / "results.jsonl"),
            ctf_baseline,
            q25_window=60,
            q25_step=20,
        )
    else:
        out["ctf"] = {}

    if method.fx_dir:
        run_dir = results_dir / method.fx_dir
        out["futurex"] = stream_metrics(
            load_results(run_dir / "results.jsonl"),
            fx_baseline,
            q25_window=60,
            q25_step=20,
        )
    else:
        out["futurex"] = {}

    return out


def build_table(results_dir: Path) -> tuple[list[dict[str, str]], dict[str, dict[str, dict]]]:
    ctf_baseline = load_results(results_dir / "ctf_dojo_baseline" / "results.jsonl")
    fx_baseline = load_results(results_dir / "futurex_baseline" / "results.jsonl")
    metrics_by_method = {
        method.key: _method_metrics(results_dir, method, ctf_baseline, fx_baseline)
        for method in METHODS
    }

    row_specs = [
        ("PolyBench", "Coverage", "up", "polybench", "coverage", 1, False),
        ("PolyBench", "Accuracy", "up", "polybench", "acc", 1, False),
        ("PolyBench", "Return", "up", "polybench", "port_ret", 1, True),
        ("CTF-Dojo", "Pass", "up", "ctf", "pass", 1, False),
        ("CTF-Dojo", "Trend", "up", "ctf", "trend", 1, True),
        ("CTF-Dojo", "Q25@60", "up", "ctf", "q25", 1, False),
        ("FutureX", "Pass", "up", "futurex", "pass", 1, False),
        ("FutureX", "Trend", "up", "futurex", "trend", 1, True),
        ("FutureX", "Q25@60", "up", "futurex", "q25", 1, False),
    ]

    rows: list[dict[str, str]] = []
    for benchmark, metric, direction, domain, key, digits, signed in row_specs:
        row: dict[str, str] = {
            "benchmark": benchmark,
            "metric": metric,
            "direction": direction,
        }
        for method in METHODS:
            value = metrics_by_method[method.key].get(domain, {}).get(key)
            row[method.key] = _fmt(value, digits=digits, signed=signed)
        rows.append(row)
    return rows, metrics_by_method


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["benchmark", "metric", "direction"] + [method.key for method in METHODS]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_markdown(rows: list[dict[str, str]]) -> None:
    headers = ["Benchmark", "Metric"] + [method.label for method in METHODS]
    print("| " + " | ".join(headers) + " |")
    print("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        cells = [row["benchmark"], row["metric"]] + [row[method.key] for method in METHODS]
        print("| " + " | ".join(cells) + " |")


def print_diagnostics(metrics_by_method: dict[str, dict[str, dict]]) -> None:
    repaired = {
        method.label: metrics_by_method[method.key].get("polybench", {}).get("n_repaired", 0)
        for method in METHODS
    }
    repaired = {label: count for label, count in repaired.items() if count}
    if repaired:
        joined = ", ".join(f"{label}={count}" for label, count in repaired.items())
        print(f"\nPolyBench repaired fallback-price rows: {joined}", file=sys.stderr)


def _row_count_warnings(results_dir: Path) -> list[str]:
    """Warn when one of our system columns is sourced from a partial run."""
    expected = {
        "PolyBench": (POLYBENCH_TOTAL, ["polybench_structured_evo", "polybench_navigation", "polybench_structured_nav"]),
        "CTF-Dojo": (261, ["ctf_dojo_structured_evo", "ctf_dojo_navigation", "ctf_dojo_structured_nav"]),
        "FutureX": (503, ["futurex_structured_evo", "futurex_navigation", "futurex_structured_nav"]),
    }
    warnings: list[str] = []
    for bench, (total, dirs) in expected.items():
        for sub in dirs:
            jsonl = results_dir / sub / "results.jsonl"
            n = len(load_results(jsonl)) if jsonl.exists() else 0
            if 0 < n < total:
                warnings.append(f"{bench}/{sub}: {n}/{total} rows (partial)")
    return warnings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument("--csv-out", type=Path, default=Path("evaluations/main_table.csv"))
    args = parser.parse_args()

    rows, metrics_by_method = build_table(args.results_dir)
    write_csv(args.csv_out, rows)
    print_markdown(rows)
    print(f"\nWrote {args.csv_out}")
    print_diagnostics(metrics_by_method)

    warnings = _row_count_warnings(args.results_dir)
    if warnings:
        print("\nPartial-run warnings:", file=sys.stderr)
        for w in warnings:
            print(f"  {w}", file=sys.stderr)


if __name__ == "__main__":
    main()
