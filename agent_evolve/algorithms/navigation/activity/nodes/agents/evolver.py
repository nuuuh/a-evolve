"""Evolver agent — snapshot → build prompt → call LLM → detect mutations → clear drafts.

Reusable sub-Activity invoked by ``CallActivity`` or ``ExpansionRegion``.
Replaces the 3x-duplicated snapshot-execute-diff pattern in
``engine.py`` / ``inline.py`` / ``orchestrated.py``.

Ordering note (important for exact parity):
  - ``_execute_plan_step`` computes mutations *before* clearing drafts
    (lines 265-274 of ``templates/orchestrated.py``).
  - ``InlineTemplate.execute`` clears drafts *before* computing
    mutations (lines 87 vs 108-113 of ``templates/inline.py``).

The default ordering here matches ``_execute_plan_step`` (diff → clear);
``InlineTemplate`` uses a custom layout (see ``specs/inline.py``).
"""

from __future__ import annotations

from ...builder import ActivityBuilder
from ...spec import Activity
from ...types import Type


def build_evolver_activity() -> Activity:
    """Return the per-branch evolver sub-Activity.

    Matches ``OrchestratedTemplate._execute_plan_step`` exactly:
      snap → build_prompt → [optional plan_context] → call_llm →
      diff → clear_drafts

    Parameters:
        workspace    (in)  Workspace
        batch        (in)  BatchResults
        cfg          (in)  Config
        evo_number   (in)  Integer
        plan_context (in, optional) PromptText — prepended to the prompt
                                     if non-empty
        target       (in, optional) String — branch name for
                                     plan_context formatting
        report       (out) MutationReport
        response     (out) LLMResponse
    """
    return (
        ActivityBuilder(
            "evolver",
            description="Snapshot → prompt → (prepend plan ctx) → call LLM → diff → clear.",
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
        .object_flow("workspace", "snap.workspace")
        .object_flow("workspace", "build_prompt.workspace")
        .object_flow("batch", "build_prompt.batch_results")
        .object_flow("cfg", "build_prompt.config")
        .object_flow("snap.drafts", "build_prompt.drafts")
        .object_flow("evo_number", "build_prompt.evo_number")
        .object_flow("build_prompt.text", "plan_ctx.prompt")
        .object_flow("plan", "plan_ctx.plan")
        .object_flow("target", "plan_ctx.target")
        .object_flow("plan_ctx.text", "call.prompt")
        .object_flow("workspace", "call.workspace")
        .object_flow("cfg", "call.config")
        .object_flow("workspace", "diff.workspace")
        .object_flow("snap.snapshot", "diff.snapshot")
        .object_flow("workspace", "clear.workspace")
        .object_flow("diff.report", "report")
        .object_flow("call.response", "response")

        # ── ControlFlows (enforce ordering; LLM mutates workspace
        # in-place, so downstream observers must run after the LLM) ──
        .control_flow("snap", "build_prompt")
        .control_flow("build_prompt", "plan_ctx")
        .control_flow("plan_ctx", "call")
        .control_flow("call", "diff")
        .control_flow("diff", "clear")

        .build_unchecked()
    )
