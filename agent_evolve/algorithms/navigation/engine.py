"""NavigationEngine -- decoupled evolution with agentic navigation.

Extends AEvolveEngine with holistic experience analysis, plan-driven
evolution, and per-task routing (F_Navigate).

Enforced pipeline (evolve_with_navigation):
  Step 1: Analyze ALL experience → produce evolution plan
  Step 2: Deepen main with stationary improvements, rebase branches
  Step 3: Execute branch evolution for non-stationary patterns

Inherits from AEvolveEngine:
  - evolve()    -- standard workspace mutation (standalone mode)
  - _run_llm()  -- sandboxed LLM execution
  - step()      -- EvolutionEngine interface
  - config, llm -- shared state
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ...contract.workspace import AgentWorkspace
from ...engine.versioning import VersionControl
from ...types import BranchInfo, StrategyTree
from ..aevolve.engine import AEvolveEngine
from ..aevolve.prompts import build_evolution_prompt
from .prompts import (
    ANALYZE_PLAN_SYSTEM_PROMPT, NAVIGATE_SYSTEM_PROMPT,
    build_analyze_plan_prompt, build_navigate_prompt,
)

logger = logging.getLogger(__name__)


class NavigationEngine(AEvolveEngine):
    """Decoupled evolution with agentic navigation.

    Adds to AEvolveEngine:
      - navigate()                -- F_Navigate: route task to branch (LLM)
      - evolve_with_navigation()  -- holistic 3-step pipeline
      - _analyze_and_plan()       -- Step 1: experience analysis → plan
      - _execute_plan_step()      -- Steps 2-3: plan-guided evolution
    """

    # ── Visualization ───────────────────────────────────────────

    @staticmethod
    def _format_tree(tree: StrategyTree, vc: VersionControl, evo_number: int) -> str:
        """Render the strategy tree as ASCII art for logging."""
        try:
            tags = vc.list_tags()
            n_evo = len([t for t in tags if t.startswith("evo-")])
        except Exception:
            n_evo = evo_number + 1

        n_show = min(n_evo, 10)
        if n_show == 0:
            main_dots = "●"
        else:
            main_dots = "──".join(["○"] * n_show) + "──●"
        if n_evo > 10:
            main_dots = "○──…" + main_dots

        lines = [
            "",
            f"  main:  {main_dots}  (evo-{evo_number})",
        ]

        if not tree.branches:
            lines.append("         (no branches)")
        else:
            fork_col = len("  main:  ") + n_show * 3
            for b in tree.branches:
                try:
                    br_log = vc._git("log", "--oneline", f"main..{b.name}")
                    br_n = len(br_log.strip().splitlines()) if br_log.strip() else 0
                except Exception:
                    br_n = 1
                br_n = max(br_n, 1)
                br_dots = "──".join(["○"] * min(br_n, 6))

                stats = ""
                if b.total_tasks > 0:
                    pct = b.total_passed / b.total_tasks * 100
                    stats = f"  ({b.total_passed}/{b.total_tasks}, {pct:.0f}%)"

                pad = " " * fork_col
                lines.append(f"{pad}╲")
                lines.append(f"  {b.name}:  {br_dots}{stats}")

        lines.append("")
        return "\n".join(lines)

    # ── F_Navigate ──────────────────────────────────────────────

    def navigate(
        self,
        task_description: str,
        tree: StrategyTree,
        workspace_root: Path | None = None,
    ) -> str:
        """F_Navigate: examine git tree leaves and pick the best branch.

        Reads actual workspace content (system prompt, skills, tools) from
        each branch so the LLM can make an informed routing decision.
        Returns branch name (e.g., "main" or "branch/algebraic-reasoning").
        """
        if not tree.branches:
            return "main"

        branch_summaries = self._read_branch_leaves(tree, workspace_root)
        prompt = build_navigate_prompt(task_description, branch_summaries)
        try:
            from ...llm.bedrock import BedrockProvider
            if isinstance(self.llm, BedrockProvider):
                response = self.llm.converse_loop(
                    system_prompt=NAVIGATE_SYSTEM_PROMPT,
                    user_message=prompt,
                    tools=[],
                    tool_executor={},
                    max_tokens=256,
                    temperature=0.0,
                )
                result = json.loads(response.content)
                raw = result.get("branch", "main")
                return self._resolve_branch_name(raw, tree)
        except Exception:
            pass
        return "main"

    @staticmethod
    def _resolve_branch_name(raw: str, tree: StrategyTree) -> str:
        """Normalize LLM-returned branch name to match actual git branch.

        The navigator LLM may return bare names like "turn-budget-convergence"
        instead of the full git name "branch/turn-budget-convergence".
        Match against known branch names in the strategy tree.
        """
        if raw == "main":
            return "main"
        known = {b.name for b in tree.branches}
        # Exact match
        if raw in known:
            return raw
        # Try adding branch/ prefix
        prefixed = f"branch/{raw}"
        if prefixed in known:
            return prefixed
        # Try stripping branch/ prefix
        if raw.startswith("branch/"):
            stripped = raw[len("branch/"):]
            for name in known:
                if name.endswith(stripped):
                    return name
        # Fuzzy: check if raw is a suffix of any known branch
        for name in known:
            if name.endswith(f"/{raw}") or name == raw:
                return name
        # No match — fall back to main
        logger.warning("Navigator returned unknown branch %r, falling back to main", raw)
        return "main"

    def _read_branch_leaves(
        self,
        tree: StrategyTree,
        workspace_root: Path | None,
    ) -> list[dict[str, Any]]:
        """Read workspace content from each branch (git tree leaves).

        For each branch (including main), reads the system prompt, skill
        names, and tool registry so the navigator can compare strategies.
        """
        branch_names = ["main"] + [b.name for b in tree.branches]
        descriptions = {"main": "general-purpose root strategy"}
        for b in tree.branches:
            descriptions[b.name] = b.description

        if not workspace_root:
            return [
                {"name": n, "description": descriptions.get(n, "")}
                for n in branch_names
            ]

        vc = VersionControl(workspace_root)
        summaries = []
        for name in branch_names:
            summary: dict[str, Any] = {
                "name": name,
                "description": descriptions.get(name, ""),
            }
            try:
                summary["system_prompt"] = vc.show_file_at(name, "prompts/system.md")
            except Exception:
                summary["system_prompt"] = ""
            try:
                ls_out = vc._git("ls-tree", "--name-only", f"{name}:skills/")
                summary["skills"] = [
                    s for s in ls_out.strip().splitlines()
                    if s and s != "_drafts"
                ]
            except Exception:
                summary["skills"] = []
            try:
                summary["tools_registry"] = vc.show_file_at(
                    name, "tools/registry.yaml")
            except Exception:
                summary["tools_registry"] = ""
            summaries.append(summary)
        return summaries

    # ── Holistic Evolution Pipeline ─────────────────────────────

    def evolve_with_navigation(
        self,
        solver_workspace: AgentWorkspace,
        batch_results: list[dict[str, Any]],
        tree: StrategyTree,
        evo_number: int = 0,
        routing_log_path: Path | None = None,
    ) -> dict[str, Any]:
        """Holistic evolution: analyze → plan → execute.

        Enforced pipeline:
          Step 1: Analyze ALL experience, produce evolution plan
          Step 2: Deepen main with stationary improvements, rebase branches
          Step 3: Create/evolve branches for non-stationary patterns
        """
        vc = VersionControl(solver_workspace.root)
        vc.init()

        # Pre-evolution snapshot
        vc.commit(
            message=f"pre-nav-evo-{evo_number}: snapshot before navigation evolution",
            tag=f"pre-nav-evo-{evo_number}",
        )

        # Step 1: Analyze & Plan
        evolution_history = []
        if routing_log_path and routing_log_path.exists():
            for line in routing_log_path.read_text().splitlines():
                if line.strip():
                    evolution_history.append(json.loads(line))

        plan = self._analyze_and_plan(
            batch_results, evolution_history, tree.branch_names(),
        )

        logger.info("Evolution plan: %s", plan.get("summary", ""))

        mutated = False
        trajectory: list[dict[str, Any]] = []

        # Record Step 1 trajectory
        step1_traj = plan.pop("_trajectory", None)
        if step1_traj:
            trajectory.append({
                "step": "analyze_and_plan",
                "plan_summary": plan.get("summary", ""),
                **step1_traj,
            })

        # Step 2: Deepen main (stationary improvements)
        main_evo = plan.get("main_evolution", {})
        if main_evo.get("description"):
            current = vc.get_current_branch()
            if current != "main":
                vc.checkout_branch("main")

            main_task_ids = set(main_evo.get("task_ids", []))
            main_logs = ([r for r in batch_results
                          if r.get("instance_id") in main_task_ids]
                         if main_task_ids else batch_results)

            result = self._execute_plan_step(
                solver_workspace, main_logs, evo_number,
                plan_context=self._format_plan_context(plan, "main"),
                tag_suffix="main",
            )
            trajectory.append({
                "step": "deepen_main",
                "mutated": result.get("mutated", False),
                "summary": result.get("summary", ""),
                "conversation": result.get("conversation", []),
            })
            if result.get("mutated"):
                mutated = True
                logger.info("Main deepened: %s", result.get("summary", ""))

                # Rebase all branches onto updated main
                for br_name in vc.list_branches():
                    try:
                        vc.rebase_branch(br_name, "main")
                    except Exception as e:
                        logger.warning("Rebase %s failed: %s", br_name, e)

        # Step 3: Branch (non-stationary patterns)
        for branch_plan in plan.get("branches", []):
            branch_name = branch_plan.get("name", "")
            if not branch_name:
                continue

            if not vc.branch_exists(branch_name):
                vc.create_branch(branch_name, "main")
                tree.branches.append(BranchInfo(
                    name=branch_name,
                    created_at_cycle=evo_number,
                    description=branch_plan.get("description", ""),
                ))
                logger.info("Created branch: %s (%s)",
                            branch_name, branch_plan.get("description", ""))
            else:
                vc.checkout_branch(branch_name)

            branch_task_ids = set(branch_plan.get("task_ids", []))
            branch_logs = ([r for r in batch_results
                            if r.get("instance_id") in branch_task_ids]
                           if branch_task_ids else [])

            result = self._execute_plan_step(
                solver_workspace, branch_logs, evo_number,
                plan_context=self._format_plan_context(plan, branch_name),
                tag_suffix=branch_name.replace("/", "-"),
            )
            trajectory.append({
                "step": "branch_evolution",
                "branch": branch_name,
                "mutated": result.get("mutated", False),
                "summary": result.get("summary", ""),
                "conversation": result.get("conversation", []),
            })
            if result.get("mutated"):
                mutated = True

        # Return to main
        try:
            vc.checkout_branch("main")
        except Exception:
            pass

        tree_viz = self._format_tree(tree, vc, evo_number)
        logger.info("Strategy tree after cycle %d:\n%s", evo_number, tree_viz)

        return {
            "evo_number": evo_number,
            "mutated": mutated,
            "plan": plan,
            "branches": tree.branch_names(),
            "trajectory": trajectory,
        }

    # ── Step 1: Analyze & Plan ─────────────────────────────────

    def _analyze_and_plan(
        self,
        batch_results: list[dict],
        evolution_history: list[dict],
        branches: list[str],
    ) -> dict[str, Any]:
        """Step 1: Analyze all experience and produce evolution plan.

        Pure analysis — no workspace mutation. Uses LLM prompt only.
        Returns structured plan dict.
        """
        prompt = build_analyze_plan_prompt(
            batch_results, evolution_history, branches,
            trajectory_only=self.config.trajectory_only,
        )
        try:
            from ...llm.bedrock import BedrockProvider
            if isinstance(self.llm, BedrockProvider):
                response = self.llm.converse_loop(
                    system_prompt=ANALYZE_PLAN_SYSTEM_PROMPT,
                    user_message=prompt,
                    tools=[],
                    tool_executor={},
                    max_tokens=4096,
                    temperature=0.0,
                )
                plan = self._parse_plan(response.content)
                plan["_trajectory"] = {
                    "prompt": prompt,
                    "response": response.content,
                }
                return plan
        except Exception as e:
            logger.warning("Analysis LLM failed: %s", e)

        # Fallback: everything goes to main
        all_ids = [r.get("instance_id", "") for r in batch_results]
        return {
            "summary": "default plan (LLM unavailable)",
            "main_evolution": {
                "description": "evolve main with all tasks",
                "insights": [],
                "task_ids": all_ids,
            },
            "branches": [],
        }

    @staticmethod
    def _parse_plan(text: str) -> dict[str, Any]:
        """Extract evolution plan dict from LLM response text."""
        import re

        for m in re.finditer(r'\{.*\}', text, re.DOTALL):
            try:
                plan = json.loads(m.group(0))
                if "main_evolution" in plan or "branches" in plan:
                    plan.setdefault("summary", "")
                    plan.setdefault("main_evolution", {})
                    plan.setdefault("branches", [])
                    return plan
            except (json.JSONDecodeError, ValueError):
                continue
        return {"summary": "", "main_evolution": {}, "branches": []}

    # ── Steps 2-3: Plan Execution ──────────────────────────────

    def _execute_plan_step(
        self,
        workspace: AgentWorkspace,
        observation_logs: list[dict[str, Any]],
        evo_number: int,
        plan_context: str = "",
        tag_suffix: str = "",
    ) -> dict[str, Any]:
        """Execute one step of the evolution plan with sandbox access.

        Builds the standard evolution prompt, prepends plan context,
        then runs the evolver LLM with bash tool access.
        """
        vc = VersionControl(workspace.root)

        skills_before = set(s.name for s in workspace.list_skills())
        prompt_before = workspace.read_prompt()
        memory_before = workspace.read_all_memories(limit=9999)
        tools_before = workspace.read_tool_registry()
        drafts = workspace.list_drafts()

        prompt = build_evolution_prompt(
            workspace, observation_logs, drafts, evo_number,
            evolve_prompts=self.config.evolve_prompts,
            evolve_skills=self.config.evolve_skills,
            evolve_memory=self.config.evolve_memory,
            evolve_tools=self.config.evolve_tools,
            evolve_infra=self.config.evolve_infra,
            include_patches=self.config.evolver_include_patches,
            trajectory_only=self.config.trajectory_only,
        )

        if plan_context:
            prompt = f"{plan_context}\n\n{prompt}"

        disabled = [name for name, on in [
            ("prompts", self.config.evolve_prompts),
            ("skills",  self.config.evolve_skills),
            ("memory",  self.config.evolve_memory),
            ("tools",   self.config.evolve_tools),
            ("infra",   self.config.evolve_infra),
        ] if not on]
        with workspace.protect(disabled):
            llm_result = self._run_llm(prompt, workspace.root)

        skills_after = set(s.name for s in workspace.list_skills())
        prompt_changed = workspace.read_prompt() != prompt_before
        memory_changed = (len(workspace.read_all_memories(limit=9999))
                          != len(memory_before))
        skills_changed = skills_after != skills_before
        tools_changed = workspace.read_tool_registry() != tools_before
        mutated = (prompt_changed or memory_changed
                   or skills_changed or tools_changed)

        workspace.clear_drafts()

        changes = []
        if prompt_changed:
            changes.append("prompt")
        if skills_changed:
            changes.append("skills")
        if memory_changed:
            changes.append("memory")
        if tools_changed:
            changes.append("tools")
        summary = ", ".join(changes) if changes else "no mutation"

        tag = f"evo-{evo_number}"
        if tag_suffix and tag_suffix != "main":
            tag = f"evo-{evo_number}-{tag_suffix}"

        vc.commit(message=f"{tag}: {summary}", tag=tag)

        return {
            "mutated": mutated,
            "summary": summary,
            "conversation": llm_result.get("conversation", []),
        }

    @staticmethod
    def _format_plan_context(plan: dict[str, Any], target: str) -> str:
        """Format plan context to prepend to the evolution prompt."""
        lines = ["## Evolution Plan Context\n"]
        lines.append(f"**Overall analysis:** {plan.get('summary', '')}\n")

        if target == "main":
            main_evo = plan.get("main_evolution", {})
            lines.append("**Your role:** Evolve the main (general-purpose) branch.")
            lines.append(f"**Focus:** {main_evo.get('description', '')}")
            insights = main_evo.get("insights", [])
            if insights:
                lines.append("**Key insights:**")
                for i in insights:
                    lines.append(f"- {i}")
        else:
            for bp in plan.get("branches", []):
                if bp.get("name") == target:
                    lines.append(
                        f"**Your role:** Evolve the specialized branch `{target}`.")
                    lines.append(
                        f"**Branch purpose:** {bp.get('description', '')}")
                    lines.append(
                        f"**Guidance:** {bp.get('evolution_guidance', '')}")
                    break

        return "\n".join(lines)
