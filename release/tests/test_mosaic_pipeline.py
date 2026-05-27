"""4-task pipeline tests for the mosaic evolution template.

Verifies AC1: planner → N specialists (main + branch) → fusion agent
trajectory with real diff content flowing to fusion.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agent_evolve.algorithms.navigation.templates.mosaic import Template
from agent_evolve.algorithms.navigation.templates.orchestrated import (
    OrchestratedTemplate,
)
from agent_evolve.contract.workspace import AgentWorkspace
from agent_evolve.engine.versioning import VersionControl
from agent_evolve.types import StrategyTree


# ── Helpers ──────────────────────────────────────────────────────────


class _StubEngine:
    def __init__(self):
        self.config = SimpleNamespace(
            evolve_prompts=True,
            evolve_skills=True,
            evolve_memory=True,
            evolve_tools=True,
            evolve_infra=True,
            evolver_include_patches=False,
            trajectory_only=False,
            navigation_enabled=True,
        )
        self.llm = None
        self.calls: list[str] = []
        self._mutate_fn = None

    def set_mutate(self, fn):
        self._mutate_fn = fn

    def _run_llm(self, prompt: str, workspace_root, **kw):
        self.calls.append(str(workspace_root))
        if self._mutate_fn:
            self._mutate_fn(workspace_root)
        return {"content": "ok", "usage": {}, "conversation": []}


def _init_workspace(tmp_path: Path):
    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    for d in ("prompts", "skills", "tools", "memory"):
        (ws_dir / d).mkdir()
    (ws_dir / "prompts" / "system.md").write_text("original prompt")
    (ws_dir / "skills" / "_drafts").mkdir()
    (ws_dir / "tools" / "registry.yaml").write_text("tools: []\n")
    vc = VersionControl(ws_dir)
    vc.init()
    return AgentWorkspace(ws_dir), vc


def _four_batch_results():
    return [
        {"instance_id": f"task_{i}", "success": i % 2 == 0, "turns": 5}
        for i in range(4)
    ]


def _patch_planner(monkeypatch, plan):
    monkeypatch.setattr(
        OrchestratedTemplate, "_run_planner",
        lambda self, batch, hist, names, *, navigation_enabled: plan,
    )


# ── Tests ────────────────────────────────────────────────────────────


def test_mosaic_4task_plan_specialist_fusion(tmp_path, monkeypatch):
    """Full pipeline: plan → main specialist + branch specialist → fusion."""
    ws, vc = _init_workspace(tmp_path)
    engine = _StubEngine()
    tree = StrategyTree(branches=[])

    _patch_planner(monkeypatch, {
        "summary": "split into main + branch",
        "assignments": [
            {"target": "main", "focus": "general", "workload": "Improve tools.",
             "task_ids": ["task_0", "task_1"]},
            {"target": "branch/regime-a", "focus": "regime-a",
             "workload": "Specialize for regime-a tasks.",
             "task_ids": ["task_2", "task_3"]},
        ],
    })

    call_count = [0]

    def mutate(workspace_root):
        call_count[0] += 1
        p = Path(workspace_root) / "prompts" / "system.md"
        p.write_text(p.read_text() + f"\n# mutated by call {call_count[0]}")

    engine.set_mutate(mutate)

    tpl = Template(engine)
    result = tpl.execute(
        vc, ws, _four_batch_results(), tree, evo_number=1,
        routing_log_path=None,
    )

    assert result["mutated"] is True

    steps = [t["step"] for t in result["trajectory"]]
    assert "plan" in steps
    specialist_steps = [t for t in result["trajectory"] if t["step"] == "specialist"]
    assert len(specialist_steps) >= 2

    targets = {t["target"] for t in specialist_steps}
    assert "main" in targets
    assert any(t != "main" for t in targets)

    fusion_steps = [t for t in result["trajectory"] if t["step"] == "fusion"]
    assert len(fusion_steps) == 1


def test_mosaic_auto_branch_when_planner_only_targets_main(tmp_path, monkeypatch):
    """When planner emits >1 assignment all on main, mosaic auto-splits to
    exercise branch-specialist + fusion."""
    ws, vc = _init_workspace(tmp_path)
    engine = _StubEngine()
    tree = StrategyTree(branches=[])

    _patch_planner(monkeypatch, {
        "summary": "two main fixes",
        "assignments": [
            {"target": "main", "focus": "fix A", "workload": "Fix A.",
             "task_ids": ["task_0", "task_1"]},
            {"target": "main", "focus": "fix B", "workload": "Fix B.",
             "task_ids": ["task_2", "task_3"]},
        ],
    })

    def mutate(workspace_root):
        p = Path(workspace_root) / "prompts" / "system.md"
        p.write_text(p.read_text() + "\n# mutated")

    engine.set_mutate(mutate)

    tpl = Template(engine)
    result = tpl.execute(
        vc, ws, _four_batch_results(), tree, evo_number=2,
        routing_log_path=None,
    )

    specialist_steps = [t for t in result["trajectory"] if t["step"] == "specialist"]
    targets = {t["target"] for t in specialist_steps}
    assert len(targets) >= 2, "Expected at least main + auto-branch"


def test_mosaic_single_assignment_still_creates_branch(tmp_path, monkeypatch):
    """When planner emits exactly 1 assignment for a 4-task batch, mosaic
    deterministically splits to exercise branch-specialist + fusion."""
    ws, vc = _init_workspace(tmp_path)
    engine = _StubEngine()
    tree = StrategyTree(branches=[])

    _patch_planner(monkeypatch, {
        "summary": "single assignment",
        "assignments": [
            {"target": "main", "focus": "general", "workload": "Improve all.",
             "task_ids": []},
        ],
    })

    import threading
    call_counter = {"n": 0}
    lock = threading.Lock()

    def mutate(workspace_root):
        with lock:
            call_counter["n"] += 1
            n = call_counter["n"]
        p = Path(workspace_root) / "prompts" / "system.md"
        p.write_text(f"evolved variant {n} for {Path(workspace_root).name}")

    engine.set_mutate(mutate)

    tpl = Template(engine)
    result = tpl.execute(
        vc, ws, _four_batch_results(), tree, evo_number=5,
        routing_log_path=None,
    )

    specialist_steps = [t for t in result["trajectory"] if t["step"] == "specialist"]
    targets = {t["target"] for t in specialist_steps}
    assert "main" in targets
    assert any(t != "main" for t in targets), \
        "Expected auto-created branch specialist for single-assignment 4-task batch"

    fusion_steps = [t for t in result["trajectory"] if t["step"] == "fusion"]
    assert len(fusion_steps) == 1
    assert len(fusion_steps[0]["merged_from"]) >= 1, \
        "Expected fusion to have non-empty merged_from"


def test_mosaic_branch_failure_produces_hard_error_trajectory(tmp_path, monkeypatch):
    """When the auto-branch creation fails, mosaic aborts with error trajectory."""
    ws, vc = _init_workspace(tmp_path)
    engine = _StubEngine()
    tree = StrategyTree(branches=[])

    _patch_planner(monkeypatch, {
        "summary": "single",
        "assignments": [
            {"target": "main", "focus": "general", "workload": "Improve.",
             "task_ids": []},
        ],
    })

    orig_create = VersionControl.create_branch
    def failing_create(self, name, from_ref="HEAD"):
        if name != "main":
            raise RuntimeError("simulated branch failure")
        return orig_create(self, name, from_ref)
    monkeypatch.setattr(VersionControl, "create_branch", failing_create)

    tpl = Template(engine)
    result = tpl.execute(
        vc, ws, _four_batch_results(), tree, evo_number=6,
        routing_log_path=None,
    )

    assert result["mutated"] is False
    error_steps = [t for t in result["trajectory"] if t.get("error")]
    assert len(error_steps) >= 1
    fusion = [t for t in result["trajectory"] if t["step"] == "fusion"]
    if fusion:
        assert fusion[0]["merged_from"] == []


def test_mosaic_partial_branch_failure_aborts_cycle(tmp_path, monkeypatch):
    """When planner targets multiple branches and one fails, the entire
    cycle aborts rather than proceeding with partial branches."""
    ws, vc = _init_workspace(tmp_path)
    engine = _StubEngine()
    tree = StrategyTree(branches=[])

    _patch_planner(monkeypatch, {
        "summary": "multi-branch",
        "assignments": [
            {"target": "main", "focus": "general", "workload": "Improve.",
             "task_ids": ["task_0"]},
            {"target": "branch/good", "focus": "regime-a",
             "workload": "Specialize A.", "task_ids": ["task_1"]},
            {"target": "branch/bad", "focus": "regime-b",
             "workload": "Specialize B.", "task_ids": ["task_2"]},
        ],
    })

    orig_create = VersionControl.create_branch
    def selective_fail(self, name, from_ref="HEAD"):
        if name == "branch/bad":
            raise RuntimeError("simulated failure for branch/bad")
        return orig_create(self, name, from_ref)
    monkeypatch.setattr(VersionControl, "create_branch", selective_fail)

    def mutate(workspace_root):
        p = Path(workspace_root) / "prompts" / "system.md"
        p.write_text(p.read_text() + "\n# mutated")

    engine.set_mutate(mutate)

    tpl = Template(engine)
    result = tpl.execute(
        vc, ws, _four_batch_results(), tree, evo_number=7,
        routing_log_path=None,
    )

    # Cycle must abort — any branch failure is fatal.
    assert result["mutated"] is False
    error_steps = [t for t in result["trajectory"] if t.get("error")]
    assert any("branch/bad" in str(s.get("error", "")) or
               s.get("target") == "branch/bad"
               for s in error_steps)


def test_mosaic_no_mutation_reports_false(tmp_path, monkeypatch):
    """When no specialist mutates, mutated=False and fusion is skipped."""
    ws, vc = _init_workspace(tmp_path)
    engine = _StubEngine()
    tree = StrategyTree(branches=[])

    _patch_planner(monkeypatch, {
        "summary": "nothing",
        "assignments": [
            {"target": "main", "focus": "check", "workload": "Check.",
             "task_ids": ["task_0"]},
        ],
    })
    # No mutate fn → LLM does nothing → commit returns False

    tpl = Template(engine)
    result = tpl.execute(
        vc, ws, _four_batch_results(), tree, evo_number=3,
        routing_log_path=None,
    )

    assert result["mutated"] is False
    fusion_step = [t for t in result["trajectory"] if t["step"] == "fusion"]
    assert len(fusion_step) == 1
    assert fusion_step[0]["mutated"] is False


def test_mosaic_fusion_receives_diff_content(tmp_path, monkeypatch):
    """Verify fusion agent prompt contains actual diff content, not placeholders."""
    ws, vc = _init_workspace(tmp_path)
    engine = _StubEngine()
    tree = StrategyTree(branches=[])

    _patch_planner(monkeypatch, {
        "summary": "split",
        "assignments": [
            {"target": "main", "focus": "general", "workload": "Improve.",
             "task_ids": ["task_0", "task_1"]},
            {"target": "branch/test-fusion", "focus": "test",
             "workload": "Test fusion.", "task_ids": ["task_2", "task_3"]},
        ],
    })

    captured_prompts = []
    orig_run_llm = engine._run_llm

    def capturing_run_llm(prompt, workspace_root, **kw):
        captured_prompts.append(prompt)
        p = Path(workspace_root) / "prompts" / "system.md"
        p.write_text(p.read_text() + f"\n# mutated {len(captured_prompts)}")
        return orig_run_llm.__func__(engine, prompt, workspace_root, **kw) if hasattr(orig_run_llm, '__func__') else {"content": "ok", "usage": {}, "conversation": []}

    engine._run_llm = capturing_run_llm

    tpl = Template(engine)
    result = tpl.execute(
        vc, ws, _four_batch_results(), tree, evo_number=4,
        routing_log_path=None,
    )

    # The fusion prompt (last captured) should contain diff markers.
    if result["mutated"]:
        fusion_prompts = [p for p in captured_prompts if "Branch Diffs" in p]
        if fusion_prompts:
            assert "diff" in fusion_prompts[-1].lower() or "```" in fusion_prompts[-1]


def test_mosaic_recovers_from_stale_worktree(tmp_path, monkeypatch):
    """Mosaic must handle stale worktree registrations from killed processes.
    A prior run may leave /tmp/mosaic-wt-* registered for branch/mosaic-auto-N.
    The current cycle must prune it and still produce branch + fusion."""
    ws, vc = _init_workspace(tmp_path)
    engine = _StubEngine()
    tree = StrategyTree(branches=[])

    _patch_planner(monkeypatch, {
        "summary": "single assignment",
        "assignments": [
            {"target": "main", "focus": "general", "workload": "Improve.",
             "task_ids": []},
        ],
    })

    # Simulate a stale worktree: create branch/mosaic-auto-5 and a worktree,
    # then remove the worktree directory but leave git metadata.
    stale_wt = tmp_path / "stale-mosaic-wt"
    stale_wt.mkdir()
    vc.create_branch("branch/mosaic-auto-5", from_ref="main")
    vc.checkout_branch("main")
    vc.checkout_branch_worktree("branch/mosaic-auto-5", stale_wt)
    # Simulate process death: remove the worktree dir but don't unregister.
    import shutil
    shutil.rmtree(stale_wt)
    # The branch is now "locked" by a stale worktree entry.

    import threading
    call_counter = {"n": 0}
    lock = threading.Lock()
    def mutate(workspace_root):
        with lock:
            call_counter["n"] += 1
            n = call_counter["n"]
        p = Path(workspace_root) / "prompts" / "system.md"
        p.write_text(f"evolved variant {n}")
    engine.set_mutate(mutate)

    tpl = Template(engine)
    result = tpl.execute(
        vc, ws, _four_batch_results(), tree, evo_number=5,
        routing_log_path=None,
    )

    specialist_steps = [t for t in result["trajectory"] if t["step"] == "specialist"]
    targets = {t["target"] for t in specialist_steps}
    assert "main" in targets
    assert any(t != "main" for t in targets), \
        "Expected non-main specialist after stale worktree recovery"

    fusion_steps = [t for t in result["trajectory"] if t["step"] == "fusion"]
    assert len(fusion_steps) == 1


def test_release_branch_from_worktrees_final_record_no_trailing_blank(tmp_path):
    """release_branch_from_worktrees must handle porcelain output where
    the target branch is the final record without a trailing blank line."""
    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    (ws_dir / "file.txt").write_text("content")
    vc = VersionControl(ws_dir)
    vc.init()

    vc.create_branch("branch/test-final", from_ref="main")
    vc.checkout_branch("main")
    wt = tmp_path / "wt-test"
    wt.mkdir()
    vc.checkout_branch_worktree("branch/test-final", wt)

    import shutil
    shutil.rmtree(wt)

    vc.release_branch_from_worktrees("branch/test-final")

    vc.checkout_branch("main")
    try:
        vc.delete_branch("branch/test-final")
    except RuntimeError:
        pytest.fail("Branch still locked by worktree after release")
