"""Continual Harness-lite — four-pass CRUD harness refinement.

Fair-comparison port of Continual Harness (Karten et al., 2025). Preserves
the four independent refinement passes (prompt, skills, memory, tools) that
analyze trajectories and apply CRUD operations to the workspace. Drops the
game-specific emulator coupling and adapts to between-batch evolution.

Single-phase cycle: one bash-enabled LLM call that reads batch trajectories
and applies CRUD edits to prompts, skills, memory, and tools. Each pass is
requested in a single combined prompt to the evolver.

Activated via config: ``orchestrator: continual_harness_lite``
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .base import EvolutionTemplate
from ._evolution_workspace import (
    get_evolver_workspace_path,
    init_evolution_workspace,
)

logger = logging.getLogger(__name__)


def _summarize_batch(batch_results: list[dict], max_chars: int = 16000) -> str:
    """Render per-task summary (same pattern as gepa_lite)."""
    lines = []
    budget = max_chars
    for r in batch_results:
        tid = r.get("instance_id", "?")
        if "success" in r:
            status = "PASS" if r.get("success") else "FAIL"
        else:
            status = "PENDING"
        turns = r.get("turns", "?")
        task_in = str(r.get("task_input") or r.get("input") or "")[:400]
        conv = r.get("conversation") or []
        tail = ""
        if conv:
            try:
                last = conv[-1]
                tail = (json.dumps(last) if isinstance(last, dict) else str(last))[:600]
            except Exception:
                pass
        block = f"### task={tid} status={status} turns={turns}\ninput: {task_in}\nlast_turn: {tail}\n"
        if len(block) > budget:
            lines.append(f"### ...({len(batch_results) - len(lines)} more tasks truncated)")
            break
        lines.append(block)
        budget -= len(block)
    return "\n".join(lines)


EVOLVE_SYSTEM = """You are a Continual Harness evolver that refines an AI agent's workspace.
You have bash access to the solver workspace at /solver_workspace/.
Your job: analyze batch trajectories and apply CRUD operations to improve the harness.

IMPORTANT: All file operations MUST target /solver_workspace/ (the solver's workspace).
Do NOT write to /evolver_workspace/ — that is for internal tracking only.

You MUST perform four independent refinement passes:
1. PROMPT: Read /solver_workspace/prompts/system.md, analyze failures, rewrite to improve.
2. SKILLS: Create new /solver_workspace/skills/ files for successful patterns, update weak ones, rm bad ones.
3. MEMORY: Append lessons to /solver_workspace/memory/ as .jsonl entries.
4. TOOLS: Update /solver_workspace/tools/ if needed (rarely — only if tool failures observed).

Only edit files you have reason to change. If a pass has nothing to improve, skip it."""


EVOLVE_PROMPT = """## Evolution Cycle {evo_number}

## Current Workspace State
- Prompt: {prompt_preview}
- Skills: {skill_list}
- Memory entries: {memory_count}
- Tools: {tool_list}

## Recent Batch Trajectories
{batch_summary}

## Instructions
Perform the four CRUD passes (prompt, skills, memory, tools) based on the trajectories above.
For each pass where you make changes, explain what you changed and why in a brief comment.
Focus on the highest-impact improvements first."""


class Template(EvolutionTemplate):
    """Four-pass CRUD harness refinement adapted from Continual Harness."""

    def __init__(self, engine):
        self.engine = engine

    @property
    def name(self) -> str:
        return "continual_harness_lite"

    def execute(
        self,
        vc, solver_workspace, batch_results,
        tree, evo_number, routing_log_path,
    ) -> dict[str, Any]:
        cfg = self.engine.config
        ws_root = solver_workspace.root
        evo_ws = get_evolver_workspace_path(ws_root)
        init_evolution_workspace(evo_ws)

        trajectory: list[dict] = []
        batch_summary = _summarize_batch(batch_results)

        if not batch_summary.strip():
            return {
                "evo_number": evo_number, "mutated": False, "plan": {},
                "branches": tree.branch_names(), "trajectory": trajectory,
            }

        # Gather workspace state for the prompt
        system_md = ws_root / "prompts" / "system.md"
        prompt_preview = system_md.read_text()[:2000] if system_md.exists() else "(none)"

        skills_dir = ws_root / "skills"
        skill_list = ", ".join(f.stem for f in skills_dir.glob("*.md")) if skills_dir.exists() else "(none)"

        memory_dir = ws_root / "memory"
        memory_count = sum(1 for _ in memory_dir.glob("*.jsonl")) if memory_dir.exists() else 0

        tools_dir = ws_root / "tools"
        tool_list = ", ".join(f.stem for f in tools_dir.glob("*.py")) if tools_dir.exists() else "(none)"

        # Pre-mutation checkpoint
        pre_tag = f"evo-{evo_number}-pre-ch"
        vc.commit(message=f"evo-{evo_number} pre-continual-harness checkpoint", tag=pre_tag)

        # Single bash-enabled LLM call for all four passes
        evolve_prompt = EVOLVE_PROMPT.format(
            evo_number=evo_number,
            prompt_preview=prompt_preview,
            skill_list=skill_list,
            memory_count=memory_count,
            tool_list=tool_list,
            batch_summary=batch_summary[:14000],
        )

        logger.info("ContinualHarness-lite: running 4-pass CRUD evolution (cycle %d)", evo_number)
        try:
            result = self.engine._run_llm(
                evolve_prompt, ws_root,
                system_prompt=EVOLVE_SYSTEM,
                evolver_workspace=evo_ws,
            )
            content = (result.get("content") or "").strip()
            trajectory.append({"step": "crud_passes", "success": True, "chars": len(content)})
        except Exception as e:
            logger.warning("ContinualHarness-lite evolution failed: %s", e)
            vc.rollback_to_tag(pre_tag)
            trajectory.append({"step": "crud_passes", "success": False, "error": str(e)})
            return {
                "evo_number": evo_number, "mutated": False, "plan": {},
                "branches": tree.branch_names(), "trajectory": trajectory,
            }

        # Check if anything changed (uncommitted diffs in workspace)
        mutated = bool(vc.diff_from_head().strip())
        if mutated:
            vc.commit(
                message=f"evo-{evo_number}-continual-harness: 4-pass CRUD refinement",
                tag=f"evo-{evo_number}-ch-mutate",
            )

        # Log cycle result to evolver workspace
        log_entry = {"cycle": evo_number, "mutated": mutated, "trajectory": trajectory}
        log_path = evo_ws / "continual_harness_log.jsonl"
        with open(log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

        return {
            "evo_number": evo_number,
            "mutated": mutated,
            "plan": {},
            "branches": tree.branch_names(),
            "trajectory": trajectory,
        }
