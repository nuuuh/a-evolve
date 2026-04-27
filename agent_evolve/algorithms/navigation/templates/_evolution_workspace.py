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

WORKSPACE_DIR = "evolver_workspace"
TASK_BOARD = "task_board.md"
RESEARCH_LOG = "research_log.jsonl"
ARCHITECTURE = "architecture.md"
INSIGHTS = "insights.jsonl"

REQUIRED_RESEARCH_FIELDS = {
    "cycle", "regime", "approach", "endpoint", "tested", "works",
    "latency_ms", "coverage", "does_not_cover", "complementary_to",
    "sample_output", "credential_needed", "credential_env", "error", "notes",
}
REQUIRED_TOOL_TEST_FIELDS = {
    "cycle", "regime", "approach", "tested", "works", "type",
}
MINIMAL_RESEARCH_FIELDS = {"cycle", "regime", "approach", "tested", "works"}


def _ws_path(ws_root: Path) -> Path:
    return ws_root / WORKSPACE_DIR


def init_evolution_workspace(ws_root: Path) -> None:
    """Create evolver workspace structure if missing."""
    ws = _ws_path(ws_root)
    ws.mkdir(parents=True, exist_ok=True)
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
    r"[-*]\s*\w[\w_]*:\s*\d+.*PRIORITY:\s*(HIGH|MEDIUM|LOW)", re.IGNORECASE,
)
_MALFORMED_PRIORITY_RE = re.compile(
    r"[-*]\s*\w[\w_]*:.*PRIORITY:\s*(HIGH|MEDIUM|LOW)", re.IGNORECASE,
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
        stripped = line.strip()
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
