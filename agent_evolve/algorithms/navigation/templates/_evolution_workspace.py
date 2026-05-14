"""Helpers for the structured-evolution evolver workspace.

The evolver workspace persists across evolution cycles and contains:
  task_board.md       — failure patterns + prioritized gaps
  research_log.jsonl  — one JSON record per tested approach
  architecture.md     — what was built and why
  insights.jsonl      — cross-cycle lessons
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

WORKSPACE_DIR = "evolver_workspace"  # sibling directory name
TASK_BOARD = "task_board.md"
RESEARCH_LOG = "research_log.jsonl"
ARCHITECTURE = "architecture.md"
INSIGHTS = "insights.jsonl"
STRATEGY_TREE = "strategy_tree.md"

REQUIRED_RESEARCH_FIELDS = {
    "cycle", "regime", "approach", "endpoint", "tested", "works",
    "latency_ms", "coverage", "does_not_cover", "complementary_to",
    "sample_output", "credential_needed", "credential_env", "error", "notes",
}
REQUIRED_TOOL_TEST_FIELDS = {
    "cycle", "regime", "approach", "tested", "works", "type",
}
MINIMAL_RESEARCH_FIELDS = {"cycle", "regime", "approach", "tested", "works"}


def get_evolver_workspace_path(solver_root: Path) -> Path:
    """Return the evolver workspace path as a sibling of the solver workspace."""
    return solver_root.parent / WORKSPACE_DIR


def _ws_path(evo_root: Path) -> Path:
    """Identity — evo_root IS the evolver workspace directory."""
    return evo_root


TESTS_DIR = "tests"


def init_evolution_workspace(evo_root: Path) -> None:
    """Create evolver workspace structure if missing.

    Layout:
      evolver_workspace/
        task_board.md          — failure patterns + prioritized gaps
        research_log.jsonl     — structured research records
        architecture.md        — what was built and why
        insights.jsonl         — cross-cycle lessons
        tests/                 — verification test scripts + logs
        evolution/             — observer data (created by harness)
    """
    ws = _ws_path(evo_root)
    ws.mkdir(parents=True, exist_ok=True)
    (ws / TESTS_DIR).mkdir(exist_ok=True)
    tb = ws / TASK_BOARD
    if not tb.exists():
        tb.write_text(
            "## Failure Patterns\n\n## Verified Capabilities\n\n"
            "## Unresolved\n\n## Human Requests\n"
        )
    arch = ws / ARCHITECTURE
    if not arch.exists():
        arch.write_text("# Architecture\n\nNo pipelines built yet.\n")
    for jsonl in (RESEARCH_LOG, INSIGHTS):
        p = ws / jsonl
        if not p.exists():
            p.touch()


TASK_BOARD_REQUIRED_SECTIONS = {
    "## Failure Patterns",
    "## Verified Capabilities",
    "## Unresolved",
    "## Human Requests",
}

IGNORED_GAP_LABELS = {
    "successes", "failures", "diagnosis", "summary", "analysis",
    "verified", "unresolved", "human", "failure", "none", "no",
    "the", "and", "for", "from", "patterns", "capabilities",
    "requests", "cycle",
}


_PRIORITY_BULLET_RE = re.compile(
    r"[-*]\s*\w[\w_]*:\s*\d+.*PRIORITY:\s*(HIGH|MEDIUM|LOW)"
    r"(\s*→\s*TARGET:\s*(main|branch/[\w-]+))?",
    re.IGNORECASE,
)
_MALFORMED_PRIORITY_RE = re.compile(
    r"[-*]\s*\w[\w_]*:.*PRIORITY:\s*(HIGH|MEDIUM|LOW)"
    r"(\s*→\s*TARGET:\s*(main|branch/[\w-]+))?",
    re.IGNORECASE,
)


def validate_task_board(content: str) -> bool:
    """Check that task board has required sections, no preamble before
    ## Failure Patterns, and ALL priority bullets use numeric format.

    The first non-empty line must be the ## Failure Patterns heading.
    """
    content_lower = content.lower()
    for section in TASK_BOARD_REQUIRED_SECTIONS:
        if section.lower() not in content_lower:
            return False
    # First non-empty line must be ## Failure Patterns heading
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not re.match(r"^##\s+Failure Patterns(?:\s*\(.*\))?\s*$", stripped, re.IGNORECASE):
            return False
        break
    in_failure = False
    valid_count = 0
    for line in content.splitlines():
        stripped = line.strip().replace("`", "").replace("**", "")
        if re.match(r"^##\s+Failure Patterns(?:\s*\(.*\))?\s*$", stripped, re.IGNORECASE):
            in_failure = True
            continue
        if stripped.startswith("## "):
            in_failure = False
            continue
        if not in_failure:
            continue
        if _MALFORMED_PRIORITY_RE.match(stripped):
            if not _PRIORITY_BULLET_RE.match(stripped):
                return False
            valid_count += 1
    return valid_count > 0


def load_task_board(ws_root: Path) -> str:
    """Read task_board.md content."""
    p = _ws_path(ws_root) / TASK_BOARD
    if not p.exists():
        return ""
    return p.read_text()


def update_task_board(ws_root: Path, content: str) -> None:
    """Write updated task_board.md."""
    p = _ws_path(ws_root) / TASK_BOARD
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def load_research_log(ws_root: Path) -> list[dict[str, Any]]:
    """Load all research records."""
    p = _ws_path(ws_root) / RESEARCH_LOG
    if not p.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            logger.warning("Skipping malformed research record: %s", line[:80])
    return records


def append_research(ws_root: Path, record: dict[str, Any]) -> None:
    """Validate and append a research record."""
    if not validate_research_record(record):
        raise ValueError(
            f"Research record missing required fields "
            f"{REQUIRED_RESEARCH_FIELDS - set(record.keys())}"
        )
    p = _ws_path(ws_root) / RESEARCH_LOG
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def validate_research_record(record: dict[str, Any]) -> bool:
    """Validate a research or tool_test record.

    tool_test records (type="tool_test") require: cycle, regime, approach,
    tested, works, type.
    Source-test records require all 15 planned fields.
    """
    if record.get("type") == "tool_test":
        return REQUIRED_TOOL_TEST_FIELDS.issubset(record.keys())
    return REQUIRED_RESEARCH_FIELDS.issubset(record.keys())


def is_legacy_record(record: dict[str, Any]) -> bool:
    """Check if a record has only the minimal 5 fields (legacy format)."""
    return (
        MINIMAL_RESEARCH_FIELDS.issubset(record.keys())
        and not REQUIRED_RESEARCH_FIELDS.issubset(record.keys())
        and record.get("type") != "tool_test"
    )


def get_verified_approaches(ws_root: Path) -> list[dict[str, Any]]:
    """Return source records with works=True and the full 15-field schema.

    Excludes tool_test records and legacy/minimal records that lack the
    fields the builder needs for fallback-chain decisions.
    """
    results = []
    for r in load_research_log(ws_root):
        if r.get("works") is not True:
            continue
        if r.get("type") == "tool_test":
            continue
        if not REQUIRED_RESEARCH_FIELDS.issubset(r.keys()):
            logger.debug("Skipping record missing full schema: %s", r.get("approach"))
            continue
        results.append(r)
    return results


def get_failed_approaches(ws_root: Path) -> list[dict[str, Any]]:
    """Return records with works=False (avoid retesting)."""
    return [r for r in load_research_log(ws_root) if r.get("works") is False]


def load_architecture(ws_root: Path) -> str:
    """Read architecture.md."""
    p = _ws_path(ws_root) / ARCHITECTURE
    if not p.exists():
        return ""
    return p.read_text()


def update_architecture(ws_root: Path, content: str) -> None:
    """Write updated architecture.md."""
    p = _ws_path(ws_root) / ARCHITECTURE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def append_insight(ws_root: Path, record: dict[str, Any]) -> None:
    """Append cross-cycle insight."""
    p = _ws_path(ws_root) / INSIGHTS
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_insights(ws_root: Path) -> list[dict[str, Any]]:
    """Load all insight records."""
    p = _ws_path(ws_root) / INSIGHTS
    if not p.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            logger.warning("Skipping malformed insight record: %s", line[:80])
    return records


# ── Strategy Tree (for structured_navigation) ──────────────────────


def load_strategy_tree(ws_root: Path) -> str:
    """Read strategy_tree.md content."""
    p = _ws_path(ws_root) / STRATEGY_TREE
    if not p.exists():
        return ""
    return p.read_text()


def _format_branch_stats(stats: dict[str, int]) -> str:
    """Format per-branch stats truthfully (pending vs revealed)."""
    routed = stats.get("routed", 0)
    revealed = stats.get("revealed", 0)
    passed = stats.get("passed", 0)
    if routed == 0:
        return "- Routed: 0 tasks"
    if revealed == 0:
        return f"- Routed: {routed} tasks (labels pending reveal)"
    pending = routed - revealed
    pct = f"{100 * passed / revealed:.0f}%"
    if pending:
        return f"- Routed: {routed} tasks, {passed}/{revealed} passed ({pct}, {pending} pending)"
    return f"- Routed: {routed} tasks, {passed}/{revealed} passed ({pct})"


def update_strategy_tree(
    ws_root: Path,
    tree: Any,
    routing_stats: dict[str, dict[str, int]],
    evo_number: int,
) -> None:
    """Write strategy_tree.md from StrategyTree + routing performance data.

    Args:
        tree: StrategyTree with .branches list
        routing_stats: {"main": {"routed": N, "revealed": M, "passed": K}, ...}
        evo_number: current cycle number
    """
    lines = [f"## Strategy Tree (Cycle {evo_number})", ""]

    # Main
    lines.append("### main")
    lines.append("General-purpose root strategy. Handles all tasks by default.")
    lines.append(_format_branch_stats(routing_stats.get("main", {})))
    lines.append("")

    # Branches
    for b in getattr(tree, "branches", []):
        lines.append(f"### {b.name}")
        lines.append(b.description or "(no description)")
        lines.append(f"- Created: cycle {b.created_at_cycle}")
        lines.append(_format_branch_stats(routing_stats.get(b.name, {})))
        lines.append("")

    p = _ws_path(ws_root) / STRATEGY_TREE
    p.write_text("\n".join(lines))


def parse_routing_stats(routing_log_path: Path | None) -> dict[str, dict[str, int]]:
    """Parse routing_log.jsonl into per-branch stats.

    Returns: {"main": {"routed": N, "revealed": M, "passed": K}, ...}
    Entries without 'success' field are pending (label not yet revealed).
    """
    stats: dict[str, dict[str, int]] = {}
    if not routing_log_path or not routing_log_path.exists():
        return stats
    for line in routing_log_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        branch = rec.get("branch", "main") or "main"
        if branch not in stats:
            stats[branch] = {"routed": 0, "revealed": 0, "passed": 0}
        stats[branch]["routed"] += 1
        if "success" in rec:
            stats[branch]["revealed"] += 1
            if rec["success"]:
                stats[branch]["passed"] += 1
    return stats


# ── TARGET parsing for structured_navigation ────────────────────────

_TARGET_RE = re.compile(r"→\s*TARGET:\s*(main|branch/[\w-]+)", re.IGNORECASE)


def extract_targets_from_task_board(content: str) -> dict[str, list[str]]:
    """Parse task board bullets for TARGET annotations.

    Returns: {"main": ["regime_a", ...], "branch/X": ["regime_b", ...]}
    Regimes without explicit TARGET default to "main".
    """
    targets: dict[str, list[str]] = {}
    in_failure = False
    for line in content.splitlines():
        stripped = line.strip()
        if re.match(r"^##\s+Failure Patterns", stripped, re.IGNORECASE):
            in_failure = True
            continue
        if stripped.startswith("## "):
            in_failure = False
            continue
        if not in_failure:
            continue
        if not _PRIORITY_BULLET_RE.match(stripped.replace("`", "")):
            continue
        # Extract regime name
        regime_match = re.match(r"[-*]\s*(\w[\w_]*):", stripped)
        if not regime_match:
            continue
        regime = regime_match.group(1)
        # Extract target
        target_match = _TARGET_RE.search(stripped)
        target = target_match.group(1) if target_match else "main"
        targets.setdefault(target, []).append(regime)
    return targets
