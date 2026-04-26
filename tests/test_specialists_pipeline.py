"""Pipeline tests for the parallel_specialists evolution template.

Verifies two specialists (tool_builder + strategy_writer) run on separate
branches, then merge at a barrier.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agent_evolve.algorithms.navigation.templates.parallel_specialists import Template
from agent_evolve.algorithms.navigation.templates.orchestrated import (
    OrchestratedTemplate,
)
from agent_evolve.contract.workspace import AgentWorkspace
from agent_evolve.engine.versioning import VersionControl
from agent_evolve.types import StrategyTree


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
            navigation_enabled=False,
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


def _four_batch():
    return [
        {"instance_id": f"task_{i}", "success": i % 2 == 0, "turns": 5,
         "task_input": f"predict event {i}"}
        for i in range(4)
    ]


def _patch_planner(monkeypatch, plan):
    monkeypatch.setattr(
        OrchestratedTemplate, "_run_planner",
        lambda self, batch, hist, names, *, navigation_enabled: plan,
    )


def test_specialists_trajectory_has_plan_specialist_merge(tmp_path, monkeypatch):
    """Trajectory shows plan → specialist (x2) → merge steps."""
    ws, vc = _init_workspace(tmp_path)
    engine = _StubEngine()
    tree = StrategyTree(branches=[])

    _patch_planner(monkeypatch, {
        "summary": "improve tools and strategy",
        "assignments": [{"target": "main", "focus": "all",
                         "workload": "Improve.", "task_ids": []}],
    })

    call_count = [0]
    def mutate(workspace_root):
        call_count[0] += 1
        p = Path(workspace_root) / "prompts" / "system.md"
        p.write_text(f"evolved by specialist {call_count[0]}")

    engine.set_mutate(mutate)

    tpl = Template(engine)
    result = tpl.execute(vc, ws, _four_batch(), tree, evo_number=1,
                         routing_log_path=None)

    steps = [t["step"] for t in result["trajectory"]]
    assert "plan" in steps
    assert "specialist" in steps
    assert "merge" in steps

    specialist_steps = [t for t in result["trajectory"] if t["step"] == "specialist"]
    assert len(specialist_steps) == 2
    names = {t["name"] for t in specialist_steps}
    assert "tool_builder" in names
    assert "strategy_writer" in names


def test_specialists_creates_and_merges_branches(tmp_path, monkeypatch):
    """Specialists run on separate branches that get merged into main."""
    ws, vc = _init_workspace(tmp_path)
    engine = _StubEngine()
    tree = StrategyTree(branches=[])

    _patch_planner(monkeypatch, {
        "summary": "test",
        "assignments": [{"target": "main", "focus": "test",
                         "workload": "Test.", "task_ids": []}],
    })

    def mutate(workspace_root):
        p = Path(workspace_root) / "prompts" / "system.md"
        p.write_text(p.read_text() + "\n# specialist change")

    engine.set_mutate(mutate)

    tpl = Template(engine)
    result = tpl.execute(vc, ws, _four_batch(), tree, evo_number=1,
                         routing_log_path=None)

    assert result["mutated"] is True
    assert vc.get_current_branch() == "main"


def test_specialists_noop_mutation(tmp_path, monkeypatch):
    """When specialists don't modify files, mutated=False."""
    ws, vc = _init_workspace(tmp_path)
    engine = _StubEngine()
    tree = StrategyTree(branches=[])

    _patch_planner(monkeypatch, {
        "summary": "noop",
        "assignments": [{"target": "main", "focus": "check",
                         "workload": "Check.", "task_ids": []}],
    })

    tpl = Template(engine)
    result = tpl.execute(vc, ws, _four_batch(), tree, evo_number=1,
                         routing_log_path=None)

    assert result["mutated"] is False
    merge_step = [t for t in result["trajectory"] if t["step"] == "merge"]
    assert len(merge_step) == 1
    assert merge_step[0]["mutated"] is False
