"""SkillOS-lite — hierarchical skill curation via LLM curator.

Fair-comparison port of SkillOS (Ouyang et al., 2025). Preserves the
hierarchical skill registry (domain/skill structure) and the curator's
create/refine/retire operations with effectiveness tracking. Substitutes
the RL-trained curator with an LLM-based curator (same model as all
other baselines) for fair comparison.

Single-phase cycle: one bash-enabled LLM call that curates the skill
registry based on batch outcomes. Skills are markdown files organized
in domain subdirectories under skills/.

Activated via config: ``orchestrator: skillos_lite``
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
    """Render per-task summary (same as gepa_lite/continual_harness_lite)."""
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


def _load_effectiveness(evo_ws: Path) -> dict[str, dict[str, int]]:
    """Load persisted skill effectiveness data."""
    path = evo_ws / "skill_effectiveness.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


def _save_effectiveness(evo_ws: Path, data: dict[str, dict[str, int]]) -> None:
    """Persist skill effectiveness data."""
    path = evo_ws / "skill_effectiveness.json"
    path.write_text(json.dumps(data, indent=2))


CURATOR_SYSTEM = """You are a SkillOS curator managing a hierarchical skill library for an AI agent.
You have bash access to the solver workspace at /solver_workspace/.
Your job: maintain a skill registry under /solver_workspace/skills/ organized by domain.

IMPORTANT: All file operations MUST target /solver_workspace/ (the solver's workspace).
Do NOT write to /evolver_workspace/ — that is for internal tracking only.

Each skill file at /solver_workspace/skills/<domain>/<skill_name>.md should contain:
- Title, domain, description of when to use it
- Step-by-step instructions the solver should follow
- Effectiveness notes (what worked, what didn't)

Your curation operations:
1. CREATE: Write new skills (mkdir -p /solver_workspace/skills/<domain> && write file)
2. REFINE: Rewrite underperforming skills with improved instructions
3. RETIRE: Remove skills that consistently fail (rm the file)

Also update /solver_workspace/prompts/system.md to reference new/updated skills when relevant.
Focus on high-impact skills that would help across multiple similar tasks."""


CURATOR_PROMPT = """## Skill Curation Cycle {evo_number}

## Current Skill Registry
{registry}

## Skill Effectiveness (from prior cycles)
{effectiveness}

## Recent Batch Outcomes
{batch_summary}

## Instructions
Based on the batch outcomes:
1. Create skills from successful patterns (especially PASS tasks with reusable strategies)
2. Refine skills that were relevant but didn't help enough
3. Retire skills that tasks clearly didn't benefit from
4. Update prompts/system.md if the skill landscape changed significantly

Organize skills hierarchically: skills/<domain>/<name>.md"""


class Template(EvolutionTemplate):
    """SkillOS-lite: LLM-based curator with hierarchical skill registry."""

    def __init__(self, engine):
        self.engine = engine

    @property
    def name(self) -> str:
        return "skillos_lite"

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

        # Load persisted effectiveness data
        effectiveness = _load_effectiveness(evo_ws)

        # Build registry overview
        skills_dir = ws_root / "skills"
        registry = self._build_registry(skills_dir)
        effectiveness_text = self._format_effectiveness(effectiveness)

        # Pre-mutation checkpoint
        pre_tag = f"evo-{evo_number}-pre-skillos"
        vc.commit(message=f"evo-{evo_number} pre-skillos checkpoint", tag=pre_tag)

        curator_prompt = CURATOR_PROMPT.format(
            evo_number=evo_number,
            registry=registry,
            effectiveness=effectiveness_text,
            batch_summary=batch_summary[:14000],
        )

        logger.info("SkillOS-lite: running curator (cycle %d)", evo_number)
        try:
            result = self.engine._run_llm(
                curator_prompt, ws_root,
                system_prompt=CURATOR_SYSTEM,
                evolver_workspace=evo_ws,
            )
            content = (result.get("content") or "").strip()
            trajectory.append({"step": "curate", "success": True, "chars": len(content)})
        except Exception as e:
            logger.warning("SkillOS-lite curation failed: %s", e)
            vc.rollback_to_tag(pre_tag)
            trajectory.append({"step": "curate", "success": False, "error": str(e)})
            return {
                "evo_number": evo_number, "mutated": False, "plan": {},
                "branches": tree.branch_names(), "trajectory": trajectory,
            }

        # Check mutations and commit (uncommitted diffs in workspace)
        mutated = bool(vc.diff_from_head().strip())
        if mutated:
            vc.commit(
                message=f"evo-{evo_number}-skillos: skill curation",
                tag=f"evo-{evo_number}-skillos-curate",
            )

            # Update effectiveness tracking based on what skills exist now
            self._update_effectiveness(ws_root, batch_results, effectiveness)
            _save_effectiveness(evo_ws, effectiveness)

        # Log
        log_entry = {"cycle": evo_number, "mutated": mutated, "trajectory": trajectory}
        log_path = evo_ws / "skillos_log.jsonl"
        with open(log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

        return {
            "evo_number": evo_number,
            "mutated": mutated,
            "plan": {},
            "branches": tree.branch_names(),
            "trajectory": trajectory,
        }

    def _build_registry(self, skills_dir: Path) -> str:
        """Build a summary of the current skill registry."""
        if not skills_dir.exists():
            return "(empty — no skills created yet)"
        files = sorted(skills_dir.rglob("*.md"))
        if not files:
            return "(empty — no skills created yet)"
        lines = []
        for f in files[:30]:
            rel = f.relative_to(skills_dir)
            first_line = ""
            try:
                first_line = f.read_text().split("\n")[0][:80]
            except Exception:
                pass
            lines.append(f"- {rel}: {first_line}")
        if len(files) > 30:
            lines.append(f"  ...and {len(files) - 30} more")
        return "\n".join(lines)

    def _format_effectiveness(self, data: dict[str, dict[str, int]]) -> str:
        """Format effectiveness tracking data."""
        if not data:
            return "(no effectiveness data yet — first cycle)"
        lines = []
        for name, stats in sorted(data.items()):
            u, s = stats.get("uses", 0), stats.get("successes", 0)
            rate = f"{s}/{u} ({100*s//u if u > 0 else 0}%)" if u > 0 else "unused"
            lines.append(f"- {name}: {rate}")
        return "\n".join(lines)

    def _update_effectiveness(
        self, ws_root: Path, batch_results: list[dict],
        effectiveness: dict[str, dict[str, int]],
    ) -> None:
        """Update effectiveness based on which skills exist and batch outcomes."""
        skills_dir = ws_root / "skills"
        if not skills_dir.exists():
            return
        current_skills = {f.stem for f in skills_dir.rglob("*.md")}
        for skill in current_skills:
            if skill not in effectiveness:
                effectiveness[skill] = {"uses": 0, "successes": 0}
            effectiveness[skill]["uses"] += 1
        pass_count = sum(1 for r in batch_results if r.get("success"))
        if pass_count > 0:
            for skill in current_skills:
                effectiveness[skill]["successes"] += 1
