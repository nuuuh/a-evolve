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
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

WORKSPACE_DIR = "evolver_workspace"
TASK_BOARD = "task_board.md"
RESEARCH_LOG = "research_log.jsonl"
ARCHITECTURE = "architecture.md"
INSIGHTS = "insights.jsonl"

REQUIRED_RESEARCH_FIELDS = {"cycle", "regime", "approach", "tested", "works"}


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
    """Check required fields: cycle, regime, approach, tested, works."""
    return REQUIRED_RESEARCH_FIELDS.issubset(record.keys())


def get_verified_approaches(ws_root: Path) -> list[dict[str, Any]]:
    """Return only records with works=True."""
    return [r for r in load_research_log(ws_root) if r.get("works") is True]


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
