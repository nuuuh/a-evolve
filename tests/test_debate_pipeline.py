"""Pipeline tests for the debate evolution template.

Verifies propose → critique → revise trajectory with real diff
content reaching the critic.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agent_evolve.algorithms.navigation.templates.debate import Template
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


def test_debate_propose_critique_trajectory(tmp_path, monkeypatch):
    """Trajectory shows propose + critique steps."""
    ws, vc = _init_workspace(tmp_path)
    engine = _StubEngine()
    tree = StrategyTree(branches=[])

    _patch_planner(monkeypatch, {
        "summary": "improve",
        "assignments": [{"target": "main", "focus": "tools",
                         "workload": "Build tools.", "task_ids": []}],
    })

    def mutate(workspace_root):
        p = Path(workspace_root) / "prompts" / "system.md"
        p.write_text(p.read_text() + "\n# proposed change")

    engine.set_mutate(mutate)

    tpl = Template(engine)
    result = tpl.execute(vc, ws, _four_batch(), tree, evo_number=1,
                         routing_log_path=None)

    steps = [t["step"] for t in result["trajectory"]]
    assert "plan" in steps
    assert "propose" in steps
    assert "critique" in steps
    assert result["mutated"] is True


def test_debate_diff_reaches_critic(tmp_path, monkeypatch):
    """The critic receives actual diff content from the proposer's changes."""
    ws, vc = _init_workspace(tmp_path)
    engine = _StubEngine()
    tree = StrategyTree(branches=[])

    _patch_planner(monkeypatch, {
        "summary": "test diff",
        "assignments": [{"target": "main", "focus": "tools",
                         "workload": "Improve.", "task_ids": []}],
    })

    def mutate(workspace_root):
        p = Path(workspace_root) / "prompts" / "system.md"
        p.write_text("UNIQUE_MARKER_FOR_DIFF_TEST")

    engine.set_mutate(mutate)

    critic_inputs = []
    orig_run_critic = Template._run_critic

    def capturing_critic(self, diff_text, workspace):
        critic_inputs.append(diff_text)
        return {"verdict": "accept", "issues": [], "summary": "ok"}

    monkeypatch.setattr(Template, "_run_critic", capturing_critic)

    tpl = Template(engine)
    result = tpl.execute(vc, ws, _four_batch(), tree, evo_number=1,
                         routing_log_path=None)

    assert len(critic_inputs) >= 1
    assert "UNIQUE_MARKER_FOR_DIFF_TEST" in critic_inputs[0]


def test_debate_noop_when_propose_doesnt_mutate(tmp_path, monkeypatch):
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

    steps = [t["step"] for t in result["trajectory"]]
    assert "propose" in steps
    assert "critique" not in steps
    assert result["mutated"] is False
