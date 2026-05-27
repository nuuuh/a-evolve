"""Phase 5 tests — parity of the reference Activity specs with their templates.

Structural parity: the reference Activities expose the right parameters,
reference the right Actions, and the JSON files round-trip.

  1. ``inline.json`` round-trips through ``Activity.from_json``.
  2. ``plan_driven.json`` round-trips.
  3. The inline spec covers every operation in ``InlineTemplate.execute``.
  4. The plan_driven spec covers every phase of
     ``OrchestratedTemplate``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_evolve.algorithms.navigation.activity import Activity
from agent_evolve.algorithms.navigation.activity.specs import (
    build_inline_activity,
    build_plan_driven_activity,
)


SPECS_DIR = (
    Path(__file__).resolve().parent.parent
    / "agent_evolve"
    / "algorithms"
    / "navigation"
    / "activity"
    / "specs"
)


# ── inline ──────────────────────────────────────────────────────────


def test_inline_spec_round_trip():
    programmatic = build_inline_activity()
    data = programmatic.to_json()
    restored = Activity.from_json(data)
    assert restored.name == programmatic.name
    assert [p.id for p in restored.parameters] == [
        p.id for p in programmatic.parameters
    ]
    assert len(restored.nodes) == len(programmatic.nodes)
    assert len(restored.flows) == len(programmatic.flows)


def test_inline_json_file_matches_programmatic():
    on_disk = json.loads((SPECS_DIR / "inline.json").read_text())
    programmatic = build_inline_activity().to_json()
    assert on_disk == programmatic


def test_inline_covers_every_inline_template_step():
    act = build_inline_activity()
    kinds = {n.config.get("action_kind") for n in act.nodes if n.kind == "Action"}
    # Each non-trivial step in InlineTemplate.execute has a dedicated
    # action in the spec.
    required = {
        "op.git_list_branches",        # line 52
        "op.snapshot_workspace",        # lines 58-62
        "op.build_evolution_prompt",    # lines 65-75
        "op.append_branching_section",  # line 75
        "op.call_llm",                  # lines 77-85
        "op.clear_drafts",              # line 87
        "op.detect_mutations",          # lines 108-113
        "op.git_commit",                # lines 118-121
        "op.git_discover_new_branches", # lines 124-155
        "op.git_register_branches",     # lines 124-155
        "op.git_tag_branch_heads",      # lines 157-170
    }
    missing = required - kinds
    assert not missing, f"inline.json missing actions: {sorted(missing)}"


def test_inline_parameters_match_binding_contract():
    """ActivityTemplate binds these parameters by name; the spec must
    declare them so the runtime passes values into the right ports."""
    act = build_inline_activity()
    param_ids = {p.id for p in act.parameters}
    assert {"workspace", "git", "batch", "cfg", "evo_number"} <= param_ids


# ── plan_driven ─────────────────────────────────────────────────────


def test_plan_driven_spec_round_trip():
    programmatic = build_plan_driven_activity()
    data = programmatic.to_json()
    restored = Activity.from_json(data)
    assert restored.name == programmatic.name
    assert set(restored.sub_activities) == set(programmatic.sub_activities)


def test_plan_driven_json_file_matches_programmatic():
    on_disk = json.loads((SPECS_DIR / "plan_driven.json").read_text())
    programmatic = build_plan_driven_activity().to_json()
    assert on_disk == programmatic


def test_plan_driven_has_expected_phases():
    act = build_plan_driven_activity()
    kinds = {n.kind for n in act.nodes}
    assert "CallActivity" in kinds      # analyst + evolve_main
    assert "ExpansionRegion" in kinds   # per-branch fan-out
    assert "Action" in kinds

    # Sub-Activities declared
    assert "analyst" in act.sub_activities
    assert "evolve_one_branch" in act.sub_activities

    # ExpansionRegion references the evolver sub-activity
    expand_nodes = [n for n in act.nodes if n.kind == "ExpansionRegion"]
    assert len(expand_nodes) == 1
    assert expand_nodes[0].config.get("activity") == "evolve_one_branch"


def test_plan_driven_emits_plan_and_mutated_out_params():
    act = build_plan_driven_activity()
    out_params = {p.id for p in act.parameters if p.direction == "out"}
    assert {"plan", "mutated"} <= out_params


def test_plan_driven_evolver_sub_activity_is_the_shared_pattern():
    """The evolver sub-activity is the snapshot-execute-diff pattern that
    used to be duplicated.  It should appear exactly once in the spec,
    referenced by CallActivity (main) and ExpansionRegion (per branch)."""
    act = build_plan_driven_activity()
    evolver = act.sub_activities["evolve_one_branch"]
    inner_kinds = {
        n.config.get("action_kind") for n in evolver.nodes if n.kind == "Action"
    }
    assert {
        "op.snapshot_workspace",
        "op.build_evolution_prompt",
        "op.call_llm",
        "op.detect_mutations",
    } <= inner_kinds

    # Referenced from both CallActivity (main) and ExpansionRegion (fan-out)
    refs = [
        n.config.get("activity")
        for n in act.nodes
        if n.kind in {"CallActivity", "ExpansionRegion"}
    ]
    assert refs.count("evolve_one_branch") == 2


# ── JSON-on-disk sanity ─────────────────────────────────────────────


def test_both_spec_json_files_exist_and_parse():
    for filename in ("inline.json", "plan_driven.json"):
        path = SPECS_DIR / filename
        assert path.exists(), f"missing reference spec: {filename}"
        data = json.loads(path.read_text())
        restored = Activity.from_json(data)
        assert restored.name in {"inline", "plan_driven"}
