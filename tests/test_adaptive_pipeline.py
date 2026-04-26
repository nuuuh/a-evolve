"""4-task pipeline tests for the adaptive evolution template.

Verifies AC2: deterministic state-based dispatch (no LLM planner) with
role-specific trajectory steps and real tool health inspection.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from agent_evolve.algorithms.navigation.templates.adaptive import Template
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


def _init_workspace(tmp_path: Path, *, with_tools=False):
    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    for d in ("prompts", "skills", "tools", "memory"):
        (ws_dir / d).mkdir()
    (ws_dir / "prompts" / "system.md").write_text("original prompt")
    (ws_dir / "skills" / "_drafts").mkdir()

    if with_tools:
        (ws_dir / "tools" / "registry.yaml").write_text(
            "tools:\n- name: web_search\n  description: search\n"
        )
        (ws_dir / "tools" / "web_search.py").write_text(
            '#!/usr/bin/env python3\nimport sys\nprint("result for", sys.argv[1])\n'
        )
    else:
        (ws_dir / "tools" / "registry.yaml").write_text("tools: []\n")

    vc = VersionControl(ws_dir)
    vc.init()
    return AgentWorkspace(ws_dir), vc


def _four_batch_results(*, all_pass=False):
    return [
        {"instance_id": f"task_{i}", "success": all_pass or (i % 2 == 0),
         "turns": 5, "input": f"test query {i}"}
        for i in range(4)
    ]


# ── Tests ────────────────────────────────────────────────────────────


def test_adaptive_dispatches_tool_builder_when_no_tools(tmp_path):
    """With no tools in registry, adaptive must dispatch tool_builder."""
    ws, vc = _init_workspace(tmp_path, with_tools=False)
    engine = _StubEngine()
    tree = StrategyTree(branches=[])

    def mutate(workspace_root):
        p = Path(workspace_root) / "prompts" / "system.md"
        p.write_text(p.read_text() + "\n# tools added")

    engine.set_mutate(mutate)

    tpl = Template(engine)
    result = tpl.execute(
        vc, ws, _four_batch_results(), tree, evo_number=1,
        routing_log_path=None,
    )

    state_step = result["trajectory"][0]
    assert state_step["step"] == "state_inspection"
    assert state_step["n_tools"] == 0
    assert "tool_builder" in state_step["dispatches"]

    dispatch_steps = [t for t in result["trajectory"] if t["step"] == "tool_builder"]
    assert len(dispatch_steps) == 1


def test_adaptive_dispatches_debugger_when_tools_fail(tmp_path):
    """With tools that have >30% error rate, adaptive must dispatch debugger."""
    ws, vc = _init_workspace(tmp_path, with_tools=True)
    engine = _StubEngine()
    tree = StrategyTree(branches=[])

    # Make the tool script fail.
    (ws.root / "tools" / "web_search.py").write_text(
        "#!/usr/bin/env python3\nimport sys; sys.exit(1)\n"
    )
    vc.commit("break tool")

    def mutate(workspace_root):
        p = Path(workspace_root) / "prompts" / "system.md"
        p.write_text(p.read_text() + "\n# debugged")

    engine.set_mutate(mutate)

    tpl = Template(engine)
    result = tpl.execute(
        vc, ws, _four_batch_results(), tree, evo_number=1,
        routing_log_path=None,
    )

    state_step = result["trajectory"][0]
    assert state_step["step"] == "state_inspection"
    assert state_step["tool_health"]["error_rate"] > 0.3
    assert "debugger" in state_step["dispatches"]


def test_adaptive_dispatches_refiner_when_tools_pass_and_improving(tmp_path):
    """With working tools and improving scores, dispatch refiner."""
    ws, vc = _init_workspace(tmp_path, with_tools=True)
    engine = _StubEngine()
    tree = StrategyTree(branches=[])

    tpl = Template(engine)
    # First cycle: establishes baseline.
    tpl.execute(
        vc, ws, _four_batch_results(all_pass=False), tree,
        evo_number=1, routing_log_path=None,
    )
    # Second cycle: score improved (all pass).
    result = tpl.execute(
        vc, ws, _four_batch_results(all_pass=True), tree,
        evo_number=2, routing_log_path=None,
    )

    state_step = result["trajectory"][0]
    assert state_step["step"] == "state_inspection"
    assert "refiner" in state_step["dispatches"]


def test_adaptive_dispatches_strategist_when_stagnant(tmp_path):
    """With working tools but stagnant scores, dispatch strategist."""
    ws, vc = _init_workspace(tmp_path, with_tools=True)
    engine = _StubEngine()
    tree = StrategyTree(branches=[])

    tpl = Template(engine)
    batch = _four_batch_results(all_pass=False)
    # First cycle: establishes baseline.
    tpl.execute(vc, ws, batch, tree, evo_number=1, routing_log_path=None)
    # Second cycle: same score → patience=1.
    result = tpl.execute(
        vc, ws, batch, tree, evo_number=2, routing_log_path=None,
    )

    state_step = result["trajectory"][0]
    dispatches = state_step["dispatches"]
    assert any("strategist" in d for d in dispatches)


def test_adaptive_escalation_tiers(tmp_path):
    """Patience counter should escalate: tweak → restructure → paradigm."""
    ws, vc = _init_workspace(tmp_path, with_tools=True)
    engine = _StubEngine()
    tree = StrategyTree(branches=[])

    tpl = Template(engine)
    batch = _four_batch_results(all_pass=False)

    tiers_seen = []
    for cycle in range(1, 5):
        result = tpl.execute(
            vc, ws, batch, tree, evo_number=cycle, routing_log_path=None,
        )
        state = result["trajectory"][0]
        for d in state["dispatches"]:
            if "strategist" in d:
                tiers_seen.append(d)

    assert len(tiers_seen) >= 2
    assert "strategist_tweak" in tiers_seen
    if len(tiers_seen) >= 3:
        assert "strategist_restructure" in tiers_seen


def test_adaptive_mutation_reflects_commit(tmp_path):
    """mutated=True only when a commit actually occurred."""
    ws, vc = _init_workspace(tmp_path, with_tools=False)
    engine = _StubEngine()
    tree = StrategyTree(branches=[])
    # No mutate fn → LLM does nothing → commit returns False.

    tpl = Template(engine)
    result = tpl.execute(
        vc, ws, _four_batch_results(), tree, evo_number=1,
        routing_log_path=None,
    )

    dispatch_steps = [t for t in result["trajectory"] if t["step"] != "state_inspection"]
    for step in dispatch_steps:
        assert step["mutated"] is False
    assert result["mutated"] is False


def test_adaptive_tool_health_records_details(tmp_path):
    """Tool health inspection records n_tested, n_pass, failed_tools."""
    ws, vc = _init_workspace(tmp_path, with_tools=True)
    engine = _StubEngine()
    tree = StrategyTree(branches=[])

    tpl = Template(engine)
    result = tpl.execute(
        vc, ws, _four_batch_results(), tree, evo_number=1,
        routing_log_path=None,
    )

    health = result["trajectory"][0]["tool_health"]
    assert health["n_tested"] >= 1
    assert "n_pass" in health
    assert "n_fail" in health
    assert "error_rate" in health
    assert isinstance(health["failed_tools"], list)


def test_adaptive_tool_health_honors_registry_command(tmp_path):
    """Tool health checker uses registry `command` field with template substitution."""
    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    for d in ("prompts", "skills", "tools", "memory"):
        (ws_dir / d).mkdir()
    (ws_dir / "prompts" / "system.md").write_text("prompt")
    (ws_dir / "skills" / "_drafts").mkdir()
    (ws_dir / "tools" / "cli_tool.py").write_text(
        '#!/usr/bin/env python3\n'
        'import argparse\n'
        'p = argparse.ArgumentParser()\n'
        'p.add_argument("--query", required=True)\n'
        'p.add_argument("--cutoff_date", required=True)\n'
        'args = p.parse_args()\n'
        'print(f"result for {args.query}")\n'
    )
    import yaml
    (ws_dir / "tools" / "registry.yaml").write_text(yaml.dump({"tools": [
        {"name": "cli_tool", "description": "test",
         "command": "python tools/cli_tool.py --query '{query}' --cutoff_date '{cutoff_date}'"},
    ]}))
    vc = VersionControl(ws_dir)
    vc.init()
    ws = AgentWorkspace(ws_dir)

    engine = _StubEngine()
    tree = StrategyTree(branches=[])
    tpl = Template(engine)
    result = tpl.execute(
        vc, ws, _four_batch_results(), tree, evo_number=1,
        routing_log_path=None,
    )

    health = result["trajectory"][0]["tool_health"]
    assert health["n_tested"] == 1
    assert health["n_pass"] == 1
    assert health["error_rate"] == 0.0


def test_adaptive_tool_health_honors_registry_path(tmp_path):
    """Tool health checker falls back to registry `path` field."""
    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    for d in ("prompts", "skills", "tools", "memory"):
        (ws_dir / d).mkdir()
    (ws_dir / "prompts" / "system.md").write_text("prompt")
    (ws_dir / "skills" / "_drafts").mkdir()
    (ws_dir / "tools" / "my_search.py").write_text(
        '#!/usr/bin/env python3\nimport sys\nprint(f"result for {sys.argv[1]}")\n'
    )
    import yaml
    (ws_dir / "tools" / "registry.yaml").write_text(yaml.dump({"tools": [
        {"name": "my_search", "description": "test",
         "path": "tools/my_search.py"},
    ]}))
    vc = VersionControl(ws_dir)
    vc.init()
    ws = AgentWorkspace(ws_dir)

    engine = _StubEngine()
    tree = StrategyTree(branches=[])
    tpl = Template(engine)
    result = tpl.execute(
        vc, ws, _four_batch_results(), tree, evo_number=1,
        routing_log_path=None,
    )

    health = result["trajectory"][0]["tool_health"]
    assert health["n_tested"] == 1
    assert health["n_pass"] == 1
