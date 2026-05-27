"""Phase 3 tests — node catalog against real workspace + git repo.

Each built-in Action is exercised in isolation to make sure it wraps
the existing helper correctly.  No LLM calls.
"""

from __future__ import annotations

import pytest

from agent_evolve.algorithms.navigation.activity import default_registry
from agent_evolve.algorithms.navigation.activity.nodes.agents import (
    build_analyst_activity,
    build_evolver_activity,
    build_planner_activity,
)
from agent_evolve.algorithms.navigation.activity.nodes.git import (
    GitCommit,
    GitDiscoverNewBranches,
    GitListBranches,
    GitRealiseBranches,
)
from agent_evolve.algorithms.navigation.activity.nodes.navigation import (
    ExtractPlanBranches,
)
from agent_evolve.algorithms.navigation.activity.nodes.workspace import (
    ClearDrafts,
    DetectMutations,
    SnapshotWorkspace,
)
from agent_evolve.contract.workspace import AgentWorkspace
from agent_evolve.engine.versioning import VersionControl
from agent_evolve.types import BranchInfo, StrategyTree


class _FakeCtx:
    def __init__(self):
        self.trace = []
        self.extra = {}


def _workspace(tmp_path):
    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    (ws_dir / "prompts").mkdir()
    (ws_dir / "prompts" / "system.md").write_text("hello")
    (ws_dir / "skills").mkdir()
    (ws_dir / "skills" / "_drafts").mkdir()
    (ws_dir / "tools").mkdir()
    (ws_dir / "memory").mkdir()
    vc = VersionControl(ws_dir)
    vc.init()
    return AgentWorkspace(ws_dir), vc


# ── Workspace actions ────────────────────────────────────────────────


def test_snapshot_then_detect_no_mutation(tmp_path):
    ws, _ = _workspace(tmp_path)
    ctx = _FakeCtx()

    snapshot_out = SnapshotWorkspace().execute({"workspace": ws}, ctx)
    assert set(snapshot_out) == {"snapshot", "drafts"}

    diff_out = DetectMutations().execute(
        {"workspace": ws, "snapshot": snapshot_out["snapshot"]}, ctx,
    )
    report = diff_out["report"]
    assert report["mutated"] is False
    assert report["changed_layers"] == []


def test_snapshot_then_detect_prompt_change(tmp_path):
    ws, _ = _workspace(tmp_path)
    ctx = _FakeCtx()

    snapshot = SnapshotWorkspace().execute({"workspace": ws}, ctx)["snapshot"]
    ws.write_prompt("new prompt")

    report = DetectMutations().execute(
        {"workspace": ws, "snapshot": snapshot}, ctx,
    )["report"]
    assert report["mutated"] is True
    assert "prompt" in report["changed_layers"]


def test_clear_drafts_removes_draft(tmp_path):
    ws, _ = _workspace(tmp_path)
    (ws.root / "skills" / "_drafts" / "foo.md").write_text("draft")
    ctx = _FakeCtx()
    ClearDrafts().execute({"workspace": ws}, ctx)
    assert not (ws.root / "skills" / "_drafts" / "foo.md").exists()


# ── Git actions ──────────────────────────────────────────────────────


def test_git_list_branches_initially_empty_main(tmp_path):
    ws, vc = _workspace(tmp_path)
    tree = StrategyTree(branches=[])
    out = GitListBranches().execute({"git": (vc, tree)}, _FakeCtx())
    # Only main, list_branches excludes main by convention.
    assert out["branches"] == []


def test_git_discover_new_branches(tmp_path):
    ws, vc = _workspace(tmp_path)
    tree = StrategyTree(branches=[])
    before = []  # no branches before
    vc.create_branch("branch/new-one", "main")
    vc.checkout_branch("main")
    out = GitDiscoverNewBranches().execute(
        {"git": (vc, tree), "before": before}, _FakeCtx(),
    )
    assert "branch/new-one" in out["new_branches"]


def test_git_commit_with_templated_message(tmp_path):
    ws, vc = _workspace(tmp_path)
    tree = StrategyTree(branches=[])
    (ws.root / "prompts" / "system.md").write_text("changed")
    action = GitCommit(config={"message": "evo-{evo_number}: {summary}",
                               "tag": "evo-{evo_number}"})
    action.execute(
        {
            "git": (vc, tree),
            "evo_number": 1,
            "report": {"summary": "prompt", "mutated": True, "changed_layers": ["prompt"]},
        },
        _FakeCtx(),
    )
    tags = vc.list_tags()
    assert "evo-1" in tags


def test_git_realise_branches_creates_branch(tmp_path):
    ws, vc = _workspace(tmp_path)
    tree = StrategyTree(branches=[])
    branches = [{"name": "New Specialist", "description": "does stuff"}]
    out = GitRealiseBranches().execute(
        {"git": (vc, tree), "branches": branches, "evo_number": 0},
        _FakeCtx(),
    )
    assert any(b["name"].startswith("branch/") for b in out["branches"])
    assert len(tree.branches) == 1


# ── Navigation actions ───────────────────────────────────────────────


def test_extract_plan_branches():
    out = ExtractPlanBranches().execute(
        {"plan": {"branches": [{"name": "a"}, {"name": "b"}]}},
        _FakeCtx(),
    )
    assert out["branches"] == [{"name": "a"}, {"name": "b"}]


def test_extract_plan_branches_empty():
    out = ExtractPlanBranches().execute({"plan": {}}, _FakeCtx())
    assert out["branches"] == []


# ── Agent sub-activities ─────────────────────────────────────────────


def test_analyst_activity_structure():
    act = build_analyst_activity()
    assert act.name == "analyst"
    param_ids = {p.id for p in act.parameters}
    assert {"batch", "git", "cfg", "plan"} <= param_ids
    action_kinds = {
        n.config.get("action_kind") for n in act.nodes if n.kind == "Action"
    }
    assert action_kinds == {
        "op.build_analyze_plan_prompt", "op.call_llm_simple", "op.parse_plan",
    }


def test_evolver_activity_structure():
    act = build_evolver_activity()
    assert act.name == "evolver"
    param_ids = {p.id for p in act.parameters}
    assert {"workspace", "batch", "cfg", "evo_number", "report"} <= param_ids
    action_kinds = {
        n.config.get("action_kind") for n in act.nodes if n.kind == "Action"
    }
    # Key actions — the snapshot / build / call / clear / diff sequence.
    assert "op.snapshot_workspace" in action_kinds
    assert "op.build_evolution_prompt" in action_kinds
    assert "op.call_llm" in action_kinds
    assert "op.detect_mutations" in action_kinds


def test_planner_emits_branches():
    act = build_planner_activity()
    out_params = {p.id for p in act.parameters if p.direction == "out"}
    assert {"plan", "branches"} <= out_params


# ── Registry exposes every builtin ───────────────────────────────────


def test_registry_contains_every_builtin():
    r = default_registry()
    expected = {
        # workspace
        "op.snapshot_workspace",
        "op.detect_mutations",
        "op.clear_drafts",
        # prompt
        "op.build_evolution_prompt",
        "op.append_branching_section",
        "op.prepend_plan_context",
        "op.build_analyze_plan_prompt",
        # llm
        "op.call_llm",
        "op.call_llm_simple",
        "op.parse_plan",
        # git
        "op.git_commit",
        "op.git_checkout",
        "op.git_list_branches",
        "op.git_discover_new_branches",
        "op.git_register_branches",
        "op.git_tag_branch_heads",
        "op.git_realise_branches",
        "op.git_rebase_branches",
        # navigation
        "op.read_branch_leaves",
        "op.extract_plan_branches",
        "op.load_routing_history",
    }
    assert expected <= set(r.list_actions())
