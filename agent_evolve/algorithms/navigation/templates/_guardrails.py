"""Shared guardrails for V2 evolution templates.

Every V2 template calls these after the evolver finishes and before
committing.  They enforce the hard constraints that V1 experiments
showed are necessary to avoid regression:

  G2. strip_search_caps   — remove solver search-count limits
  G3. seed_news_hint      — return the Google News RSS seed text
  G4. verify_tools        — subprocess-test each tool, remove failures
  G5. cap_prompt_size     — truncate prompts/system.md to MAX chars
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MAX_PROMPT_CHARS = 10_000

SEARCH_CAP_PATTERNS = [
    r"(?i)limit\s+searches?\s+to\s+\d+",
    r"(?i)use\s+\d+-?\d*\s+searches?",
    r"(?i)submit\s+by\s+search\s+\d+",
    r"(?i)HARD\s+SEARCH\s+LIMIT",
    r"(?i)max(imum)?\s+\d+\s+searches?",
    r"(?i)no\s+more\s+than\s+\d+\s+searches?",
]

NEWS_SEARCH_HINT = (
    "Google News RSS at `https://news.google.com/rss/search?q=...` "
    "returns timestamped headlines without htmldate. Build a "
    "`news_search.py` tool using this source as your first priority."
)

NO_THROTTLE_RULE = (
    "Never limit the solver's search count. The solver has an 80-turn "
    "budget and manages it. Your job is better tools, not fewer turns."
)


def strip_search_caps(prompt: str) -> str:
    """Remove solver search-count limits from the system prompt (G2)."""
    for pattern in SEARCH_CAP_PATTERNS:
        prompt = re.sub(pattern, "", prompt)
    # Clean up resulting double-blank-lines.
    prompt = re.sub(r"\n{3,}", "\n\n", prompt)
    return prompt.strip()


def seed_news_hint() -> str:
    """Return the Google News RSS seed text for evolver prompts (G3)."""
    return NEWS_SEARCH_HINT


def no_throttle_rule() -> str:
    """Return the no-throttle instruction for evolver prompts (G2)."""
    return NO_THROTTLE_RULE


def verify_tools(
    workspace_root: Path,
    sample_query: str = "test query 2026",
    cutoff: str = "2026-01-15",
    timeout: int = 15,
) -> list[str]:
    """Test each registered tool and remove failures from registry (G4).

    Returns list of removed tool names.
    """
    import yaml

    tools_dir = workspace_root / "tools"
    reg_path = tools_dir / "registry.yaml"
    if not reg_path.exists():
        return []

    try:
        data = yaml.safe_load(reg_path.read_text()) or {}
    except Exception:
        return []

    tools = data.get("tools", [])
    if not tools:
        return []

    removed = []
    kept = []
    for t in tools:
        name = t.get("name", "")
        script = tools_dir / f"{name}.py"
        if not script.exists():
            removed.append(name)
            logger.info("G4: removed %s (script missing)", name)
            continue
        try:
            proc = subprocess.run(
                ["python3", str(script), sample_query, cutoff],
                capture_output=True, text=True, timeout=timeout,
                cwd=str(workspace_root),
            )
            if proc.returncode != 0:
                removed.append(name)
                logger.info("G4: removed %s (exit %d)", name, proc.returncode)
                continue
            if not proc.stdout.strip():
                removed.append(name)
                logger.info("G4: removed %s (empty output)", name)
                continue
        except subprocess.TimeoutExpired:
            removed.append(name)
            logger.info("G4: removed %s (timeout >%ds)", name, timeout)
            continue
        except Exception as e:
            removed.append(name)
            logger.info("G4: removed %s (%s)", name, e)
            continue
        kept.append(t)

    if removed:
        data["tools"] = kept
        reg_path.write_text(yaml.dump(data, default_flow_style=False))
        logger.info("G4: registry updated, kept %d, removed %d: %s",
                     len(kept), len(removed), removed)
    return removed


def cap_prompt_size(
    workspace_root: Path,
    max_chars: int = MAX_PROMPT_CHARS,
) -> bool:
    """Truncate prompts/system.md if it exceeds max_chars (G5).

    Returns True if truncation happened.
    """
    prompt_path = workspace_root / "prompts" / "system.md"
    if not prompt_path.exists():
        return False
    content = prompt_path.read_text()
    if len(content) <= max_chars:
        return False
    prompt_path.write_text(content[:max_chars])
    logger.info("G5: truncated prompt from %d to %d chars",
                len(content), max_chars)
    return True


def verify_pipeline(workspace_root: Path, timeout: int = 15) -> bool:
    """Test that infra/search_pipeline.py runs and returns valid JSON (G6).

    Returns True if pipeline is valid or absent. Returns False and removes
    the pipeline if it fails.
    """
    pipeline = workspace_root / "infra" / "search_pipeline.py"
    if not pipeline.exists():
        return True
    test_input = json.dumps({"query": "test query 2026", "cutoff_date": "2026-01-15"})
    try:
        proc = subprocess.run(
            [sys.executable, str(pipeline)],
            input=test_input, capture_output=True, text=True, timeout=timeout,
            cwd=str(workspace_root),
        )
        if proc.returncode != 0:
            logger.info("G6: removed search_pipeline.py (exit %d: %s)",
                        proc.returncode, proc.stderr[:200])
            pipeline.unlink()
            return False
        output = json.loads(proc.stdout.strip())
        if not isinstance(output, dict):
            logger.info("G6: removed search_pipeline.py (output not a dict)")
            pipeline.unlink()
            return False
        return True
    except subprocess.TimeoutExpired:
        logger.info("G6: removed search_pipeline.py (timeout %ds)", timeout)
        pipeline.unlink()
        return False
    except (json.JSONDecodeError, Exception) as e:
        logger.info("G6: removed search_pipeline.py (%s)", e)
        pipeline.unlink()
        return False


def apply_all_guardrails(
    workspace_root: Path,
    sample_query: str = "test query 2026",
    cutoff: str = "2026-01-15",
) -> dict[str, Any]:
    """Apply G2-G5 guardrails. Returns a summary dict."""
    results: dict[str, Any] = {}

    # G2: strip search caps from evolved prompt
    prompt_path = workspace_root / "prompts" / "system.md"
    if prompt_path.exists():
        original = prompt_path.read_text()
        cleaned = strip_search_caps(original)
        if cleaned != original:
            prompt_path.write_text(cleaned)
            results["search_caps_stripped"] = True
        else:
            results["search_caps_stripped"] = False

    # G4: verify tools
    removed = verify_tools(workspace_root, sample_query, cutoff)
    results["tools_removed"] = removed

    # G5: cap prompt size
    truncated = cap_prompt_size(workspace_root)
    results["prompt_truncated"] = truncated

    return results
