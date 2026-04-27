"""Orthogonal pair template — general tool builder + domain expert.

Splits by problem difficulty instead of workspace layer. The general
agent builds/maintains search tools (stationary work). The domain
expert writes skills for hard tasks that tools can't solve (non-
stationary work: Chinese content, niche platforms, unsearchable data).

Dispatch is deterministic (no LLM planner): count tasks with
difficulty_level >= 3 or domain == "chinese". If count > 0, run
domain expert after general agent.

Addresses R2 (no planner = no hallucination) and R3 (general agent
has explicit no-throttle rule).

Activated via config: ``orchestrator: orthogonal_pair``
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .base import EvolutionTemplate
from ._guardrails import apply_all_guardrails, seed_news_hint, no_throttle_rule

logger = logging.getLogger(__name__)

GENERAL_TOOL_SYSTEM = f"""\
You are a GENERAL TOOL BUILDER. Build and maintain web search tools
so the solver can gather evidence for temporal prediction tasks.

Rules:
1. {no_throttle_rule()}
2. {seed_news_hint()}
3. Test every tool: `python3 tools/<name>.py "query" "2026-01-15"`
4. Register working tools in tools/registry.yaml.
5. Update prompts/system.md to teach the solver how to use each tool.
6. Keep prompts/system.md under 10,000 characters.

Commit: `git add -A && git commit -m "tools: <summary>"`
"""

DOMAIN_EXPERT_SYSTEM = """\
You are a DOMAIN EXPERT for hard prediction tasks. The solver already
has general web search tools (see tools/registry.yaml). Your job is
to write SKILLS and MEMORY for task types where search alone isn't
enough.

Focus areas:
- Chinese-language tasks (Weibo rankings, Maoyan box office, QQ Music)
- Tasks with unsearchable platform data
- Level 3-4 difficulty tasks that need domain reasoning heuristics

Write skills under skills/<name>/SKILL.md with YAML frontmatter.
Add lessons to memory/lessons.jsonl.
Do NOT modify tools/ — the general agent handles that.

Commit: `git add skills/ memory/ && git commit -m "skills: <summary>"`
"""


class Template(EvolutionTemplate):
    """General tool builder + optional domain expert."""

    def __init__(self, engine):
        self.engine = engine

    @property
    def name(self) -> str:
        return "orthogonal_pair"

    def execute(
        self,
        vc, solver_workspace, batch_results,
        tree, evo_number, routing_log_path,
    ) -> dict[str, Any]:
        trajectory: list[dict] = []

        # Deterministic dispatch: check if batch has hard tasks.
        n_hard = sum(
            1 for r in batch_results
            if (r.get("difficulty_level", 0) or 0) >= 3
            or str(r.get("domain", "")).lower() == "chinese"
        )
        run_domain = n_hard > 0

        trajectory.append({
            "step": "dispatch",
            "n_hard_tasks": n_hard,
            "run_domain_expert": run_domain,
        })
        logger.info(
            "Orthogonal dispatch: %d hard tasks → domain_expert=%s",
            n_hard, run_domain,
        )

        # ── General tool agent (always runs) ──
        from ....algorithms.aevolve.prompts import build_evolution_prompt
        cfg = self.engine.config
        base_prompt = build_evolution_prompt(
            solver_workspace, batch_results, drafts=[],
            evo_number=evo_number,
            evolve_prompts=cfg.evolve_prompts,
            evolve_skills=cfg.evolve_skills,
            evolve_memory=cfg.evolve_memory,
            evolve_tools=cfg.evolve_tools,
            evolve_infra=cfg.evolve_infra,
        )

        mutated = False
        try:
            self.engine._run_llm(
                base_prompt, solver_workspace.root,
                system_prompt=GENERAL_TOOL_SYSTEM,
            )
            committed = vc.commit(
                message=f"evo-{evo_number}-general: tool building",
                tag=f"evo-{evo_number}-general",
            )
            trajectory.append({"step": "general_tool_agent", "mutated": committed})
            if committed:
                mutated = True
        except Exception as e:
            logger.warning("General tool agent failed: %s", e)
            trajectory.append({"step": "general_tool_agent", "mutated": False, "error": str(e)})

        # ── Domain expert (only if hard tasks exist) ──
        if run_domain:
            try:
                self.engine._run_llm(
                    base_prompt, solver_workspace.root,
                    system_prompt=DOMAIN_EXPERT_SYSTEM,
                )
                committed = vc.commit(
                    message=f"evo-{evo_number}-domain: skills + memory",
                    tag=f"evo-{evo_number}-domain",
                )
                trajectory.append({"step": "domain_expert", "mutated": committed})
                if committed:
                    mutated = True
            except Exception as e:
                logger.warning("Domain expert failed: %s", e)
                trajectory.append({"step": "domain_expert", "mutated": False, "error": str(e)})

        # ── Guardrails G2-G5 ──
        if mutated:
            sample_query = "Bitcoin price January 2026"
            for r in batch_results[:3]:
                inp = r.get("task_input") or r.get("input") or ""
                if isinstance(inp, dict):
                    inp = inp.get("input", "")
                if inp:
                    sample_query = str(inp)[:100]
                    break

            guardrail_results = apply_all_guardrails(
                solver_workspace.root, sample_query=sample_query,
            )
            trajectory.append({"step": "guardrails", **guardrail_results})
            vc.commit(
                message=f"evo-{evo_number}-guardrails: cleanup",
                tag=f"evo-{evo_number}-guardrails",
            )

        return {
            "evo_number": evo_number,
            "mutated": mutated,
            "plan": {},
            "branches": tree.branch_names(),
            "trajectory": trajectory,
        }
