"""Mosaic evolution template — per-branch specialists with fusion.

Navigation creates branches for non-stationary regimes (C1). This
template gives each branch its own specialist evolver, then a fusion
agent cross-pollinates successful techniques back into main.

Flow per cycle:
  1. Planner analyses batch → allocates tasks to branches
  2. N evolvers run (one per active branch + main), each seeing only
     its branch's tasks and workspace state
  3. Fusion agent reads all diffs, identifies transferable techniques,
     and selectively merges generalizable improvements into main

Activated via config: ``orchestrator: mosaic``
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .base import EvolutionTemplate
from .orchestrated import (
    OrchestratedTemplate,
    build_planner_prompt,
    PLANNER_SYSTEM_PROMPT_NAV,
    PLANNER_SYSTEM_PROMPT_FLAT,
    _load_routing_history,
)

logger = logging.getLogger(__name__)

FUSION_SYSTEM = """\
You are a fusion agent. You receive diffs from multiple specialist
evolvers that independently evolved different branches of a workspace.

Your job: identify techniques that are **generalizable** (would help
ALL tasks, not just one branch's specialty) and merge them into main.

For each branch diff:
1. Understand what changed and why.
2. Classify each change as:
   - GENERAL: useful for all tasks (e.g., better error handling,
     new API wrapper, improved search strategy) → merge into main
   - SPECIFIC: only helps this branch's regime (e.g., domain-specific
     heuristic, niche prompt tweak) → leave on the branch
3. For GENERAL changes, apply them to the main workspace using
   workspace_bash (edit files, copy tools, update registry).

Rules:
- Do NOT blindly copy branch files — understand WHY each change helps.
- Do NOT merge conflicting strategies (e.g., two different system prompts).
- Prefer merging TOOLS (reusable) over PROMPTS (regime-specific).
- Always verify merged tools work: test them with workspace_bash.
- Commit your changes: git add -A && git commit -m "fusion: <summary>"
"""

BRANCH_EVOLVER_PREFIX = """\
You are a SPECIALIST EVOLVER for branch `{branch}`.

You are evolving a workspace that handles a specific subset of tasks.
Focus your improvements on the patterns you see in YOUR branch's
task results — do not try to generalize to all tasks.

Your branch's task IDs: {task_ids}

"""


class Template(EvolutionTemplate):
    """Per-branch specialist evolvers + fusion agent."""

    def __init__(self, engine):
        self.engine = engine
        self._inner = OrchestratedTemplate(engine)

    @property
    def name(self) -> str:
        return "mosaic"

    def execute(
        self,
        vc, solver_workspace, batch_results,
        tree, evo_number, routing_log_path,
    ) -> dict[str, Any]:
        cfg = self.engine.config
        nav_enabled = bool(getattr(cfg, "navigation_enabled", False))
        trajectory: list[dict] = []
        mutated = False

        # ── Step 1: Planner ──
        routing_history = _load_routing_history(routing_log_path)
        plan = self._inner._run_planner(
            batch_results, routing_history, tree.branch_names(),
            navigation_enabled=nav_enabled,
        )
        assignments = list(plan.get("assignments", []) or [])
        if not assignments:
            assignments = [{"target": "main", "focus": "general",
                            "workload": plan.get("summary", "")}]
        logger.info("Planner emitted %d assignment(s): %s",
                     len(assignments), plan.get("summary", ""))
        trajectory.append({
            "step": "plan", "n_assignments": len(assignments),
        })

        # ── Step 2: Per-branch specialist evolvers ──
        # Group assignments by target branch.  Sanitize branch names
        # through the engine's normalizer.
        by_target: dict[str, list[dict]] = {}
        from ..engine import NavigationEngine
        for a in assignments:
            raw_target = a.get("target", "main")
            if raw_target != "main":
                raw_target = NavigationEngine._sanitize_branch_name(raw_target)
            by_target.setdefault(raw_target, []).append(a)

        # Always include main.
        if "main" not in by_target:
            by_target["main"] = [{"target": "main", "focus": "general",
                                  "workload": "Improve stationary artifacts."}]

        # If the planner only produced main-targeting assignments but
        # we have >1, split half to an auto-created branch so we always
        # exercise branch-specialist + fusion.
        if len(by_target) == 1 and "main" in by_target and len(assignments) > 1:
            half = len(assignments) // 2
            branch_name = f"branch/mosaic-auto-{evo_number}"
            by_target[branch_name] = assignments[half:]
            by_target["main"] = assignments[:half]

        # ── Run specialists (main first, then branches) ──
        ordered_targets = sorted(
            by_target, key=lambda t: 0 if t == "main" else 1,
        )

        branch_diffs: dict[str, str] = {}
        for target in ordered_targets:
            target_assignments = by_target[target]

            # Ensure we're on the right branch.
            if target == "main":
                vc.checkout_branch("main")
            else:
                try:
                    vc.checkout_branch("main")
                    vc.create_branch(target, from_ref="main")
                except Exception:
                    try:
                        vc.checkout_branch(target)
                    except Exception as e:
                        logger.warning("Cannot reach branch %s: %s", target, e)
                        continue

            # Build focused prompt for this branch.
            task_ids = []
            workloads = []
            for a in target_assignments:
                task_ids.extend(a.get("task_ids", []))
                workloads.append(a.get("workload", ""))

            if task_ids:
                filtered = [r for r in batch_results
                            if r.get("instance_id") in set(task_ids)]
            else:
                filtered = batch_results

            combined_workload = "\n".join(workloads)
            assignment = {
                "target": target,
                "focus": ", ".join(a.get("focus", "") for a in target_assignments),
                "workload": combined_workload,
                "task_ids": task_ids,
            }
            if target != "main":
                assignment["workload"] = (
                    BRANCH_EVOLVER_PREFIX.format(
                        branch=target, task_ids=task_ids)
                    + combined_workload
                )

            result = self._inner._execute_plan_step(
                solver_workspace, filtered, evo_number,
                assignment=assignment, target=target,
                tag_suffix=f"{target.replace('/', '-')}-specialist",
            )
            step_mutated = result.get("mutated", False)
            trajectory.append({
                "step": "specialist",
                "target": target,
                "mutated": step_mutated,
                "n_tasks": len(filtered),
            })
            if step_mutated:
                mutated = True

            # Capture diff for fusion: use diff_from_head for main,
            # diff_branch_from_main for branches.
            if target != "main" and step_mutated:
                diff = vc.diff_branch_from_main(target)
                if diff:
                    branch_diffs[target] = diff[:4000]
            elif target == "main" and step_mutated:
                diff = vc.diff_from_head()
                if diff:
                    branch_diffs["main"] = diff[:4000]

            logger.info("Specialist %s: mutated=%s (%d tasks)",
                        target, step_mutated, len(filtered))

        # ── Step 3: Fusion agent ──
        non_main_diffs = {k: v for k, v in branch_diffs.items() if k != "main"}
        if non_main_diffs:
            vc.checkout_branch("main")
            fusion_result = self._run_fusion(
                solver_workspace, branch_diffs, evo_number,
            )
            fusion_mutated = fusion_result.get("mutated", False)
            trajectory.append({
                "step": "fusion",
                "mutated": fusion_mutated,
                "merged_from": list(non_main_diffs.keys()),
            })
            if fusion_mutated:
                mutated = True
            logger.info("Fusion: mutated=%s, merged from %s",
                        fusion_mutated, list(non_main_diffs.keys()))
        else:
            vc.checkout_branch("main")
            trajectory.append({"step": "fusion", "mutated": False, "merged_from": []})

        return {
            "evo_number": evo_number,
            "mutated": mutated,
            "plan": plan,
            "branches": tree.branch_names(),
            "trajectory": trajectory,
        }

    def _run_fusion(
        self,
        workspace,
        branch_diffs: dict[str, str],
        evo_number: int,
    ) -> dict:
        """Run the fusion agent to merge generalizable techniques into main."""
        diff_sections = []
        for branch, diff in branch_diffs.items():
            diff_sections.append(
                f"## Branch: {branch}\n```diff\n{diff}\n```"
            )

        # Read current main state for context.
        tools = workspace.read_tool_registry()
        tool_names = [t.get("name", "") for t in tools]

        prompt = (
            f"## Branch Diffs from Cycle {evo_number}\n\n"
            + "\n\n".join(diff_sections)
            + f"\n\n## Current main tools\n{json.dumps(tool_names)}\n\n"
            + "Identify GENERAL improvements from the branch diffs and "
            + "merge them into the main workspace. Leave branch-specific "
            + "changes on their branches."
        )

        try:
            result = self.engine._run_llm(
                prompt, workspace.root,
                system_prompt=FUSION_SYSTEM,
            )
            # Check if fusion made changes.
            from ....engine.versioning import VersionControl
            vc = VersionControl(workspace.root)
            vc.commit(
                message=f"evo-{evo_number}-fusion: merged generalizable techniques",
                tag=f"evo-{evo_number}-fusion",
            )
            return {"mutated": True, "content": result.get("content", "")}
        except Exception as e:
            logger.warning("Fusion agent failed: %s", e)
            return {"mutated": False}
