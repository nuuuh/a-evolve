"""Reference Activity: ``OrchestratedTemplate`` + ``PlanDrivenOrchestrator``.

The top-level Activity coordinates three phases:

  1. Analyst sub-Activity emits a Plan (main_evolution + branches).
  2. Commit any main mutations (evolver sub-Activity invoked on main).
  3. Realise the plan's branch specs in git; per-branch ExpansionRegion
     runs the evolver sub-Activity once per branch.

Sub-Activities:
    analyst           — see nodes/agents/analyst.py
    evolve_one_branch — see nodes/agents/evolver.py

Also exported:
    ``_build_branch_cycle_activity()`` — the per-branch snapshot →
    prompt → plan-context → call_llm → diff → clear sequence used by
    ``templates/orchestrated.py::_execute_plan_step``.  Kept here so
    the Activity and the template stay in lockstep.
"""

from __future__ import annotations

from ..builder import ActivityBuilder
from ..nodes.agents import build_analyst_activity, build_evolver_activity
from ..spec import Activity
from ..types import Type


def _build_branch_cycle_activity() -> Activity:
    """Per-branch evolution cycle for ``OrchestratedTemplate._execute_plan_step``.

    Ordering (exact match to original orchestrated.py lines 235-274):
      snap → build_prompt → prepend_plan_context → call_llm → diff → clear_drafts

    The commit step is NOT included — the template performs the commit
    itself so the ``evo-{N}-{tag_suffix}`` tag formula is applied
    precisely.  This sub-Activity emits the ``report`` (for mutation /
    summary detection) and ``response`` (for conversation capture).

    Parameters:
        workspace (in)  Workspace
        batch     (in)  BatchResults
        cfg       (in)  Config
        evo_number(in)  Integer
        plan      (in)  Plan             — empty dict disables plan ctx
        target    (in)  String           — branch name for plan ctx
        report    (out) MutationReport
        response  (out) LLMResponse
    """
    return (
        ActivityBuilder(
            "branch_cycle",
            description="Per-branch evolver cycle used by OrchestratedTemplate "
                        "and PlanDriven mode.",
        )
        .parameter("workspace", Type.WORKSPACE, direction="in")
        .parameter("batch", Type.BATCH_RESULTS, direction="in")
        .parameter("cfg", Type.CONFIG, direction="in")
        .parameter("evo_number", Type.INTEGER, direction="in")
        .parameter("plan", Type.PLAN, direction="in")
        .parameter("target", Type.STRING, direction="in")
        .parameter("report", Type.MUTATION_REPORT, direction="out")
        .parameter("response", Type.LLM_RESPONSE, direction="out")
        .action("snap", "op.snapshot_workspace")
        .action("build_prompt", "op.build_evolution_prompt")
        .action("plan_ctx", "op.prepend_plan_context")
        .action("call", "op.call_llm")
        .action("diff", "op.detect_mutations")
        .action("clear", "op.clear_drafts")

        # Snapshot state
        .object_flow("workspace", "snap.workspace")

        # Build prompt
        .object_flow("workspace", "build_prompt.workspace")
        .object_flow("batch", "build_prompt.batch_results")
        .object_flow("cfg", "build_prompt.config")
        .object_flow("snap.drafts", "build_prompt.drafts")
        .object_flow("evo_number", "build_prompt.evo_number")

        # Optional plan context
        .object_flow("build_prompt.text", "plan_ctx.prompt")
        .object_flow("plan", "plan_ctx.plan")
        .object_flow("target", "plan_ctx.target")

        # LLM call
        .object_flow("plan_ctx.text", "call.prompt")
        .object_flow("workspace", "call.workspace")
        .object_flow("cfg", "call.config")

        # Diff (before clear!)
        .object_flow("workspace", "diff.workspace")
        .object_flow("snap.snapshot", "diff.snapshot")

        # Clear drafts (after diff)
        .object_flow("workspace", "clear.workspace")

        # Out-parameters
        .object_flow("diff.report", "report")
        .object_flow("call.response", "response")

        # ── ControlFlows (enforce execution ordering) ──
        .control_flow("snap", "build_prompt")
        .control_flow("build_prompt", "plan_ctx")
        .control_flow("plan_ctx", "call")
        .control_flow("call", "diff")
        .control_flow("diff", "clear")

        .build_unchecked()
    )


def build_plan_driven_activity() -> Activity:
    analyst = build_analyst_activity()
    evolve = build_evolver_activity()

    return (
        ActivityBuilder(
            "plan_driven",
            description="Plan-driven multi-agent evolution: analyst then "
                        "per-branch evolver via ExpansionRegion.",
        )
        .parameter("workspace", Type.WORKSPACE, direction="in")
        .parameter("git", Type.GIT_TREE, direction="in")
        .parameter("batch", Type.BATCH_RESULTS, direction="in")
        .parameter("cfg", Type.CONFIG, direction="in")
        .parameter("evo_number", Type.INTEGER, direction="in")
        .parameter("plan", Type.PLAN, direction="out")
        .parameter("mutated", Type.MUTATION_REPORT, direction="out")

        # Step 1: Analyst produces a plan.
        .node("analyst", "CallActivity", activity="analyst")

        # Step 2: Evolve main using the plan context.
        .node("evolve_main", "CallActivity", activity="evolve_one_branch")

        # Step 3: Extract + realise branches.
        .action("extract", "op.extract_plan_branches")
        .action("realise", "op.git_realise_branches")

        # Per-branch fan-out.
        .node(
            "expand",
            "ExpansionRegion",
            activity="evolve_one_branch",
            mode="iterative",
            item_param="item",
            result_param="report",
        )

        # Commit aggregation (post-expand).
        .action(
            "commit_main",
            "op.git_commit",
            message="evo-{evo_number}-main: plan-driven",
            tag="evo-{evo_number}-main",
        )

        # ── Wires ──

        # analyst inputs
        .object_flow("batch", "analyst.batch")
        .object_flow("git", "analyst.git")
        .object_flow("cfg", "analyst.cfg")

        # evolve_main inputs
        .object_flow("workspace", "evolve_main.workspace")
        .object_flow("batch", "evolve_main.batch")
        .object_flow("cfg", "evolve_main.cfg")
        .object_flow("evo_number", "evolve_main.evo_number")

        # extract branches from plan
        .object_flow("analyst.plan", "extract.plan")

        # realise branches
        .object_flow("git", "realise.git")
        .object_flow("extract.branches", "realise.branches")
        .object_flow("evo_number", "realise.evo_number")

        # expansion region inputs
        .object_flow("realise.branches", "expand.items")
        .object_flow("workspace", "expand.workspace")
        .object_flow("batch", "expand.batch")
        .object_flow("cfg", "expand.cfg")
        .object_flow("evo_number", "expand.evo_number")

        # commit
        .object_flow("git", "commit_main.git")
        .object_flow("evo_number", "commit_main.evo_number")
        .object_flow("evolve_main.report", "commit_main.report")

        # out-parameters
        .object_flow("analyst.plan", "plan")
        .object_flow("evolve_main.report", "mutated")

        # Sub-Activities
        .sub_activity("analyst", analyst)
        .sub_activity("evolve_one_branch", evolve)

        .build_unchecked()
    )
