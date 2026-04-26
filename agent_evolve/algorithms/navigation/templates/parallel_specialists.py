"""Parallel specialists template — role-based concurrent agents.

Decomposes each evolution cycle into 2-3 specialist roles that work
on different workspace layers in parallel. Each specialist runs in
its own git branch; results are merged afterward.

Specialists:
  - Tool builder: creates/fixes tools/*.py + registry.yaml
  - Strategy writer: refines prompts/system.md + skills/
  - (Optional) Memory curator: prunes/adds memory/*.jsonl

All specialists receive the same batch diagnosis from a shared
planner, but each gets a role-specific prompt focused on its layer.

Activated via config: ``orchestrator: parallel_specialists``
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .base import EvolutionTemplate
from .orchestrated import (
    OrchestratedTemplate,
    build_planner_prompt,
    PLANNER_SYSTEM_PROMPT_FLAT,
    _load_routing_history,
)

logger = logging.getLogger(__name__)

TOOL_BUILDER_PROMPT = """\
You are a TOOL BUILDER specialist. Your ONLY job is to create and fix
tools under tools/*.py and tools/registry.yaml.

You must NOT modify prompts/, skills/, or memory/. Focus entirely on:
1. Reading the diagnosis below to understand what data the solver needs.
2. Building tools that fetch that data (web search, APIs, scrapers).
3. Testing each tool with a real query via workspace_bash.
4. Registering working tools in tools/registry.yaml.

Every tool must:
- Accept (query, cutoff_date) as CLI args
- Use htmldate for date filtering on web content
- Handle timeouts and network errors gracefully
- Print results to stdout

Commit your changes with: git add tools/ && git commit -m "tools: <summary>"
"""

STRATEGY_WRITER_PROMPT = """\
You are a STRATEGY WRITER specialist. Your ONLY job is to refine
prompts/system.md and create/update skills under skills/.

You must NOT modify tools/ or memory/. Focus entirely on:
1. Reading the diagnosis below to understand failure patterns.
2. Reading the current tool registry (tools/registry.yaml) to know
   what tools are available — write the system prompt to USE them.
3. Writing clear, actionable instructions in prompts/system.md.
4. Creating skills (skills/<name>/SKILL.md) for recurring patterns.

The solver has these tools: submit + any tools in the registry.
Your system prompt must teach the solver HOW to use each tool
effectively (query strategies, when to stop searching, etc.).

Commit your changes with: git add prompts/ skills/ && git commit -m "strategy: <summary>"
"""


class Template(EvolutionTemplate):
    """Parallel specialist evolution: tool builder + strategy writer."""

    def __init__(self, engine):
        self.engine = engine
        self._inner = OrchestratedTemplate(engine)

    @property
    def name(self) -> str:
        return "parallel_specialists"

    def execute(
        self,
        vc, solver_workspace, batch_results,
        tree, evo_number, routing_log_path,
    ) -> dict[str, Any]:
        from ....engine.versioning import VersionControl

        cfg = self.engine.config
        nav_enabled = bool(getattr(cfg, "navigation_enabled", False))
        trajectory: list[dict] = []

        # Step 1: Planner — shared diagnosis for all specialists
        routing_history = _load_routing_history(routing_log_path)
        plan = self._inner._run_planner(
            batch_results, routing_history, tree.branch_names(),
            navigation_enabled=nav_enabled,
        )
        diagnosis = plan.get("summary", "Improve based on batch results.")
        assignments = list(plan.get("assignments", []) or [])
        workloads = "\n".join(
            f"- {a.get('focus', '')}: {a.get('workload', '')}"
            for a in assignments
        ) or diagnosis

        logger.info("Planner diagnosis: %s", diagnosis)
        trajectory.append({
            "step": "plan", "diagnosis": diagnosis,
            "n_assignments": len(assignments),
        })

        # Step 2-3: Run specialists sequentially (each on its own branch).
        # Git operations must be serialized (one workspace), but the LLM
        # calls inside _run_llm are the real bottleneck — each specialist
        # gets a full sandbox session.
        from ....algorithms.aevolve.prompts import build_evolution_prompt

        base_prompt = build_evolution_prompt(
            solver_workspace, batch_results, drafts=[],
            evo_number=evo_number,
            evolve_prompts=cfg.evolve_prompts,
            evolve_skills=cfg.evolve_skills,
            evolve_memory=cfg.evolve_memory,
            evolve_tools=cfg.evolve_tools,
            evolve_infra=cfg.evolve_infra,
        )
        context_block = f"## Planner Diagnosis\n{workloads}\n\n"

        specialists = [
            ("tool_builder", f"specialist/tools-{evo_number}",
             TOOL_BUILDER_PROMPT + "\n\n" + context_block + base_prompt),
            ("strategy_writer", f"specialist/strategy-{evo_number}",
             STRATEGY_WRITER_PROMPT + "\n\n" + context_block + base_prompt),
        ]

        results = {}
        for name, branch, prompt in specialists:
            try:
                vc.checkout_branch("main")
                vc.create_branch(branch, from_ref="main")
                result = self.engine._run_llm(prompt, solver_workspace.root)
                vc.commit(
                    message=f"evo-{evo_number}-{name}: specialist evolution",
                    tag=f"evo-{evo_number}-{name}",
                )
                r = {"name": name, "branch": branch, "mutated": True}
            except Exception as e:
                logger.warning("Specialist %s failed: %s", name, e)
                r = {"name": name, "branch": branch, "mutated": False}
            results[name] = r
            trajectory.append({
                "step": "specialist", "name": name,
                "branch": branch, "mutated": r["mutated"],
            })
            logger.info("Specialist %s: mutated=%s", name, r["mutated"])

        # Step 4: Merge specialist branches into main
        vc.checkout_branch("main")
        mutated = False

        for name, branch, _ in specialists:
            r = results.get(name, {})
            if not r.get("mutated"):
                continue
            try:
                vc.merge_branch(branch)
                mutated = True
                logger.info("Merged %s into main", branch)
            except Exception as e:
                logger.warning("Merge %s failed (conflict?): %s", branch, e)
                # On conflict, try cherry-picking the commit
                try:
                    import subprocess
                    subprocess.run(
                        ["git", "merge", "--abort"],
                        cwd=solver_workspace.root,
                        capture_output=True,
                    )
                except Exception:
                    pass

        # Commit merged result
        if mutated:
            vc.commit(
                message=f"evo-{evo_number}-main: merged specialists",
                tag=f"evo-{evo_number}-main",
            )

        # Cleanup branches
        for _, branch, _ in specialists:
            try:
                vc.delete_branch(branch)
            except Exception:
                pass

        trajectory.append({"step": "merge", "mutated": mutated})

        return {
            "evo_number": evo_number,
            "mutated": mutated,
            "plan": plan,
            "branches": tree.branch_names(),
            "trajectory": trajectory,
        }
