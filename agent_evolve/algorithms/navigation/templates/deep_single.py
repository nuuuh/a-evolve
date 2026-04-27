"""Deep single-agent template — extended single evolver with guardrails.

The V2 control experiment. Tests whether V1's performance gap was
caused by prompt quality (fixable with better guidance) or by
multi-agent architecture (requires structural change).

Design: one long evolver session with explicit guidance (seed Google
News RSS, never throttle solver) + programmatic post-LLM guardrails
(G2-G5: strip search caps, verify tools, cap prompt size).

If this template beats H1 (42.9%), the bottleneck was prompt quality.
If it matches H1, architecture matters and multi-agent templates
(F, H, I, J) are needed.

Activated via config: ``orchestrator: deep_single``
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .base import EvolutionTemplate
from ._guardrails import apply_all_guardrails, seed_news_hint, no_throttle_rule

logger = logging.getLogger(__name__)

DEEP_SINGLE_SYSTEM_SUFFIX = f"""

## Hard Rules (enforced by the framework — violations will be reverted)

1. {no_throttle_rule()}

2. {seed_news_hint()}

3. After building each tool, TEST it immediately:
   `python3 tools/<name>.py "sample query" "2026-01-15"`
   If it fails, fix it or delete it. Do not leave broken tools.

4. Keep prompts/system.md under 10,000 characters. Be concise.
"""


class Template(EvolutionTemplate):
    """Extended single-agent evolution with hard guardrails."""

    def __init__(self, engine):
        self.engine = engine

    @property
    def name(self) -> str:
        return "deep_single"

    def execute(
        self,
        vc, solver_workspace, batch_results,
        tree, evo_number, routing_log_path,
    ) -> dict[str, Any]:
        trajectory: list[dict] = []

        # Build the evolution prompt (same as H1 single-agent).
        from ....algorithms.aevolve.prompts import build_evolution_prompt
        cfg = self.engine.config
        prompt = build_evolution_prompt(
            solver_workspace, batch_results, drafts=[],
            evo_number=evo_number,
            evolve_prompts=cfg.evolve_prompts,
            evolve_skills=cfg.evolve_skills,
            evolve_memory=cfg.evolve_memory,
            evolve_tools=cfg.evolve_tools,
            evolve_infra=cfg.evolve_infra,
        )

        # Append the hard-rules suffix to the evolver's system prompt.
        evolver_system = None
        system_prompt_extra = cfg.extra.get("evolver_system_prompt", "")
        if system_prompt_extra:
            evolver_system = system_prompt_extra + DEEP_SINGLE_SYSTEM_SUFFIX
        else:
            evolver_system = DEEP_SINGLE_SYSTEM_SUFFIX.strip()

        # Run the evolver — one long session with full sandbox access.
        try:
            result = self.engine._run_llm(
                prompt, solver_workspace.root,
                system_prompt=evolver_system,
            )
            mutated = True
            trajectory.append({
                "step": "evolve",
                "mutated": True,
                "content_length": len(result.get("content", "")),
            })
        except Exception as e:
            logger.warning("Deep single evolver failed: %s", e)
            mutated = False
            trajectory.append({
                "step": "evolve", "mutated": False, "error": str(e),
            })

        # Commit whatever the evolver produced.
        committed = vc.commit(
            message=f"evo-{evo_number}-deep-single: evolution",
            tag=f"evo-{evo_number}-deep-single",
        )
        if not committed:
            mutated = False

        # Apply guardrails G2-G5 AFTER the evolver finishes.
        if mutated:
            # Extract a sample query from batch for tool testing.
            sample_query = "Bitcoin price January 2026"
            for r in batch_results[:3]:
                inp = r.get("task_input") or r.get("input") or ""
                if isinstance(inp, dict):
                    inp = inp.get("input", "")
                if inp:
                    sample_query = str(inp)[:100]
                    break

            guardrail_results = apply_all_guardrails(
                solver_workspace.root,
                sample_query=sample_query,
            )
            trajectory.append({
                "step": "guardrails",
                "search_caps_stripped": guardrail_results.get("search_caps_stripped", False),
                "tools_removed": guardrail_results.get("tools_removed", []),
                "prompt_truncated": guardrail_results.get("prompt_truncated", False),
            })

            # Commit guardrail changes.
            vc.commit(
                message=f"evo-{evo_number}-guardrails: post-evolution cleanup",
                tag=f"evo-{evo_number}-guardrails",
            )

        return {
            "evo_number": evo_number,
            "mutated": mutated,
            "plan": {},
            "branches": tree.branch_names(),
            "trajectory": trajectory,
        }
