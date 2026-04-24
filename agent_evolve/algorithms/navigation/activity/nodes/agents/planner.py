"""Planner agent — runs the analyst and extracts branch specs.

Emits both a full ``Plan`` (downstream consumers may want it) and a
``BranchSpecList`` ready to feed an ``ExpansionRegion`` that spawns one
evolver sub-activity per branch.
"""

from __future__ import annotations

from ...builder import ActivityBuilder
from ...spec import Activity
from ...types import Type


def build_planner_activity() -> Activity:
    """Return the planner sub-Activity.

    Parameters:
        batch    (in)  BatchResults
        git      (in)  GitTree
        cfg      (in)  Config
        plan     (out) Plan
        branches (out) BranchSpecList
    """
    return (
        ActivityBuilder(
            "planner",
            description="Analyse batch; emit plan + branch specs for fan-out.",
        )
        .parameter("batch", Type.BATCH_RESULTS, direction="in")
        .parameter("git", Type.GIT_TREE, direction="in")
        .parameter("cfg", Type.CONFIG, direction="in")
        .parameter("plan", Type.PLAN, direction="out")
        .parameter("branches", Type.BRANCH_SPEC_LIST, direction="out")
        .action("build_prompt", "op.build_analyze_plan_prompt")
        .action("call", "op.call_llm_simple")
        .action("parse", "op.parse_plan")
        .action("extract", "op.extract_plan_branches")
        .object_flow("batch", "build_prompt.batch_results")
        .object_flow("cfg", "build_prompt.config")
        .object_flow("git", "build_prompt.git")
        .object_flow("build_prompt.text", "call.prompt")
        .object_flow("cfg", "call.config")
        .object_flow("call.response", "parse.response")
        .object_flow("parse.plan", "extract.plan")
        .object_flow("parse.plan", "plan")
        .object_flow("extract.branches", "branches")
        .build_unchecked()
    )
