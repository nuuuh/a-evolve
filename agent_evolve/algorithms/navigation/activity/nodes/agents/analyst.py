"""Analyst agent — classifies batch failures into a plan.

Equivalent to ``AnalystRole.execute``: build an analyze prompt → call LLM
simple → parse plan.
"""

from __future__ import annotations

from ...builder import ActivityBuilder
from ...spec import Activity
from ...types import Type


def build_analyst_activity() -> Activity:
    """Return the analyst sub-Activity.

    Parameters:
        batch (in)  BatchResults
        git   (in)  GitTree
        cfg   (in)  Config
        plan  (out) Plan
    """
    return (
        ActivityBuilder("analyst", description="Classify failures; produce a plan.")
        .parameter("batch", Type.BATCH_RESULTS, direction="in")
        .parameter("git", Type.GIT_TREE, direction="in")
        .parameter("cfg", Type.CONFIG, direction="in")
        .parameter("plan", Type.PLAN, direction="out")
        .action("build_prompt", "op.build_analyze_plan_prompt")
        .action("call", "op.call_llm_simple")
        .action("parse", "op.parse_plan")
        .object_flow("batch", "build_prompt.batch_results")
        .object_flow("cfg", "build_prompt.config")
        .object_flow("git", "build_prompt.git")
        .object_flow("build_prompt.text", "call.prompt")
        .object_flow("cfg", "call.config")
        .object_flow("call.response", "parse.response")
        .object_flow("parse.plan", "plan")

        # Ordering (ObjectFlows already enforce it but explicit is clearer).
        .control_flow("build_prompt", "call")
        .control_flow("call", "parse")

        .build_unchecked()
    )
