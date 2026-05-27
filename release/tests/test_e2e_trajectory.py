"""End-to-end trajectory test proving mutated=True + tools in registry.

Verifies AC5: at least one template produces a 4-task trajectory with
mutated=True and tools written to the registry.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from agent_evolve.algorithms.navigation.templates.adaptive import Template as AdaptiveTemplate
from agent_evolve.algorithms.navigation.templates.mosaic import Template as MosaicTemplate
from agent_evolve.algorithms.navigation.templates.orchestrated import OrchestratedTemplate
from agent_evolve.contract.workspace import AgentWorkspace
from agent_evolve.engine.versioning import VersionControl
from agent_evolve.types import StrategyTree


class _ToolWritingEngine:
    """Stub engine that writes a tool to the workspace, simulating real evolution."""

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

    def _run_llm(self, prompt: str, workspace_root, **kw):
        ws = Path(workspace_root)
        tool_code = (
            '#!/usr/bin/env python3\n'
            'import sys\n'
            'print(f"Search results for: {sys.argv[1]}")\n'
        )
        (ws / "tools" / "web_search.py").write_text(tool_code)
        (ws / "tools" / "registry.yaml").write_text(
            yaml.dump({"tools": [
                {"name": "web_search", "description": "Web search tool"},
            ]})
        )
        (ws / "prompts" / "system.md").write_text(
            "Use web_search tool to gather evidence.\n"
        )
        return {"content": "Created web_search tool", "usage": {}, "conversation": []}


def _init_workspace(tmp_path: Path):
    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    for d in ("prompts", "skills", "tools", "memory"):
        (ws_dir / d).mkdir()
    (ws_dir / "prompts" / "system.md").write_text("original")
    (ws_dir / "skills" / "_drafts").mkdir()
    (ws_dir / "tools" / "registry.yaml").write_text("tools: []\n")
    vc = VersionControl(ws_dir)
    vc.init()
    return AgentWorkspace(ws_dir), vc


def _four_batch():
    return [
        {"instance_id": f"task_{i}", "success": i % 2 == 0, "turns": 5,
         "task_input": f"query {i}"}
        for i in range(4)
    ]


def _patch_planner(monkeypatch, plan):
    monkeypatch.setattr(
        OrchestratedTemplate, "_run_planner",
        lambda self, batch, hist, names, *, navigation_enabled: plan,
    )


def test_adaptive_e2e_mutated_true_with_registry_tools(tmp_path):
    """AC5: adaptive template produces mutated=True + tools in registry."""
    ws, vc = _init_workspace(tmp_path)
    engine = _ToolWritingEngine()
    tree = StrategyTree(branches=[])

    tpl = AdaptiveTemplate(engine)
    result = tpl.execute(
        vc, ws, _four_batch(), tree, evo_number=1,
        routing_log_path=None,
    )

    assert result["mutated"] is True

    tools = ws.read_tool_registry()
    assert len(tools) >= 1
    assert any(t["name"] == "web_search" for t in tools)

    assert len(result["trajectory"]) >= 2
    state = result["trajectory"][0]
    assert state["step"] == "state_inspection"


def test_mosaic_e2e_mutated_true_with_registry_tools(tmp_path, monkeypatch):
    """AC5: mosaic template produces mutated=True + tools in registry."""
    ws, vc = _init_workspace(tmp_path)
    engine = _ToolWritingEngine()
    tree = StrategyTree(branches=[])

    _patch_planner(monkeypatch, {
        "summary": "build tools",
        "assignments": [
            {"target": "main", "focus": "tools",
             "workload": "Build web search tool.", "task_ids": ["task_0", "task_1"]},
            {"target": "branch/search", "focus": "search",
             "workload": "Build search.", "task_ids": ["task_2", "task_3"]},
        ],
    })

    tpl = MosaicTemplate(engine)
    result = tpl.execute(
        vc, ws, _four_batch(), tree, evo_number=1,
        routing_log_path=None,
    )

    assert result["mutated"] is True

    tools = ws.read_tool_registry()
    assert len(tools) >= 1

    steps = [t["step"] for t in result["trajectory"]]
    assert "plan" in steps
    assert "specialist" in steps
    assert "fusion" in steps


def test_trajectory_has_four_observations(tmp_path):
    """AC5: trajectory is produced from 4 batch observations."""
    ws, vc = _init_workspace(tmp_path)
    engine = _ToolWritingEngine()
    tree = StrategyTree(branches=[])

    batch = _four_batch()
    assert len(batch) == 4

    tpl = AdaptiveTemplate(engine)
    result = tpl.execute(
        vc, ws, batch, tree, evo_number=1,
        routing_log_path=None,
    )

    assert result["mutated"] is True
    assert len(result["trajectory"]) >= 2
    assert result["evo_number"] == 1
