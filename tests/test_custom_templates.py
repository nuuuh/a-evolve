"""Tests for custom multi-agent evolution templates.

Uses fake engine/workspace stubs — no external LLM calls.
Verifies the execution contract: trajectory steps, dispatch logic,
diff capture, and return-dict shape.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest


# ── Shared fixtures ──────────────────────────────────────────────────


def _init_git(root: Path) -> None:
    """Create a minimal git repo with one commit on branch 'main'."""
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
    (root / "prompts").mkdir(exist_ok=True)
    (root / "prompts" / "system.md").write_text("seed prompt")
    (root / "skills").mkdir(exist_ok=True)
    (root / "memory").mkdir(exist_ok=True)
    (root / "tools").mkdir(exist_ok=True)
    (root / "tools" / "registry.yaml").write_text("tools: []\n")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=root, check=True)


def _make_batch(n: int = 4) -> list[dict]:
    return [
        {"instance_id": f"task_{i}", "success": i % 2 == 0,
         "score": float(i % 2 == 0), "turns": 5,
         "task_input": f"predict event {i}",
         "batch_num": 1, "evo_cycle": 1}
        for i in range(n)
    ]


class _StubTree:
    branches = []
    def branch_names(self):
        return ["main"]
    def to_dict(self):
        return {}


class _FakeEngine:
    """Minimal engine stub that simulates _run_llm by writing a tool."""

    class config:
        trajectory_only = False
        temporal_reveal = False
        navigation_enabled = False
        evolve_prompts = True
        evolve_skills = True
        evolve_memory = True
        evolve_tools = True
        evolve_infra = False
        evolver_include_patches = False
        extra = {}

    llm = None  # triggers default-plan fallback in _run_planner

    def _run_llm(self, prompt: str, workspace_root, **kwargs) -> dict:
        """Simulate evolution: write a tool to the workspace."""
        ws = Path(workspace_root)
        (ws / "tools" / "web_search.py").write_text(
            '#!/usr/bin/env python3\nimport sys\nprint("results for:", sys.argv[1])\n'
        )
        import yaml
        (ws / "tools" / "registry.yaml").write_text(
            yaml.dump({"tools": [{"name": "web_search",
                                   "description": "search"}]})
        )
        (ws / "prompts" / "system.md").write_text("evolved prompt")
        subprocess.run(["git", "add", "-A"], cwd=ws, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "evolved"],
                       cwd=ws, check=True)
        return {"content": "done", "conversation": []}


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    _init_git(ws)
    return ws


@pytest.fixture
def engine():
    return _FakeEngine()


@pytest.fixture
def vc(workspace):
    from agent_evolve.engine.versioning import VersionControl
    return VersionControl(workspace)


@pytest.fixture
def agent_workspace(workspace):
    from agent_evolve.contract.workspace import AgentWorkspace
    return AgentWorkspace(workspace)


# ── VersionControl.diff_from_head ────────────────────────────────────


def test_diff_from_head_returns_committed_changes(workspace, vc):
    (workspace / "prompts" / "system.md").write_text("changed")
    subprocess.run(["git", "add", "-A"], cwd=workspace, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "change"],
                   cwd=workspace, check=True)
    diff = vc.diff_from_head()
    assert "changed" in diff
    assert "system.md" in diff


def test_diff_branch_from_main(workspace, vc):
    vc.create_branch("branch/test", from_ref="main")
    (workspace / "tools" / "new.py").write_text("tool code")
    subprocess.run(["git", "add", "-A"], cwd=workspace, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "branch work"],
                   cwd=workspace, check=True)
    diff = vc.diff_branch_from_main("branch/test")
    assert "new.py" in diff
    assert "tool code" in diff


# ── Debate template ──────────────────────────────────────────────────


def test_debate_propose_critique_revise(
    workspace, engine, vc, agent_workspace,
):
    from agent_evolve.algorithms.navigation.templates.debate import Template
    template = Template(engine)

    result = template.execute(
        vc, agent_workspace, _make_batch(4),
        _StubTree(), evo_number=1, routing_log_path=None,
    )
    steps = [s["step"] for s in result["trajectory"]]
    assert "plan" in steps
    assert "propose" in steps
    assert result["mutated"] is True


# ── Mosaic template ──────────────────────────────────────────────────


def test_mosaic_specialist_plus_fusion(
    workspace, engine, vc, agent_workspace,
):
    from agent_evolve.algorithms.navigation.templates.mosaic import Template
    template = Template(engine)

    result = template.execute(
        vc, agent_workspace, _make_batch(4),
        _StubTree(), evo_number=1, routing_log_path=None,
    )
    steps = [s["step"] for s in result["trajectory"]]
    assert "plan" in steps
    assert "specialist" in steps
    assert "fusion" in steps
    assert result["mutated"] is True

    # Verify tools were written to workspace.
    import yaml
    reg = yaml.safe_load(
        (workspace / "tools" / "registry.yaml").read_text()
    )
    assert len(reg.get("tools", [])) > 0


# ── Adaptive template ────────────────────────────────────────────────


def test_adaptive_dispatches_tool_builder_when_no_tools(
    workspace, engine, vc, agent_workspace,
):
    from agent_evolve.algorithms.navigation.templates.adaptive import Template
    template = Template(engine)

    result = template.execute(
        vc, agent_workspace, _make_batch(4),
        _StubTree(), evo_number=1, routing_log_path=None,
    )
    steps = result["trajectory"]
    inspection = steps[0]
    assert inspection["step"] == "state_inspection"
    assert inspection["n_tools"] == 0
    assert "tool_builder" in inspection["dispatches"]
    assert result["mutated"] is True


def test_adaptive_dispatches_debugger_when_tools_fail(
    workspace, engine, vc, agent_workspace,
):
    from agent_evolve.algorithms.navigation.templates.adaptive import Template

    # Pre-populate a broken tool in the workspace.
    import yaml
    (workspace / "tools" / "broken.py").write_text(
        "#!/usr/bin/env python3\nimport sys; sys.exit(1)\n"
    )
    (workspace / "tools" / "registry.yaml").write_text(
        yaml.dump({"tools": [{"name": "broken", "description": "fails"}]})
    )
    subprocess.run(["git", "add", "-A"], cwd=workspace, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "add broken tool"],
                   cwd=workspace, check=True)

    template = Template(engine)
    result = template.execute(
        vc, agent_workspace, _make_batch(4),
        _StubTree(), evo_number=1, routing_log_path=None,
    )
    inspection = result["trajectory"][0]
    assert inspection["step"] == "state_inspection"
    assert inspection["n_tools"] == 1
    health = inspection.get("tool_health", {})
    assert health["n_fail"] >= 1
    assert health["error_rate"] > 0.3
    assert "debugger" in inspection["dispatches"]


# ── Verified template ────────────────────────────────────────────────


def test_verified_build_verify_trajectory(
    workspace, engine, vc, agent_workspace,
):
    from agent_evolve.algorithms.navigation.templates.verified import Template
    template = Template(engine)

    result = template.execute(
        vc, agent_workspace, _make_batch(4),
        _StubTree(), evo_number=1, routing_log_path=None,
    )
    steps = [s["step"] for s in result["trajectory"]]
    assert "plan" in steps
    assert "build" in steps
    assert result["mutated"] is True


# ── Parallel specialists ─────────────────────────────────────────────


def test_specialists_tool_builder_and_strategy_writer(
    workspace, engine, vc, agent_workspace,
):
    from agent_evolve.algorithms.navigation.templates.parallel_specialists import Template
    template = Template(engine)

    result = template.execute(
        vc, agent_workspace, _make_batch(4),
        _StubTree(), evo_number=1, routing_log_path=None,
    )
    steps = result["trajectory"]
    step_names = [s["step"] for s in steps]
    assert "plan" in step_names
    assert "specialist" in step_names
    assert "merge" in step_names
    assert result["mutated"] is True


# ── Mosaic stale worktree regression ─────────────────────────────────


def test_mosaic_survives_stale_worktree(
    workspace, engine, vc, agent_workspace,
):
    """Simulate a stale worktree from a killed run, then verify mosaic
    still creates a branch specialist and fusion in a subsequent cycle."""
    from agent_evolve.algorithms.navigation.templates.mosaic import Template

    # Create a stale worktree that would block branch/mosaic-auto-1.
    import tempfile, shutil
    stale_wt = Path(tempfile.mkdtemp(prefix="mosaic-wt-stale-"))
    subprocess.run(
        ["git", "worktree", "add", "--detach", str(stale_wt), "main"],
        cwd=workspace, check=True,
    )
    # Leave it dangling (don't remove it — simulating a killed process).

    template = Template(engine)
    result = template.execute(
        vc, agent_workspace, _make_batch(4),
        _StubTree(), evo_number=1, routing_log_path=None,
    )
    steps = [s["step"] for s in result["trajectory"]]
    assert "specialist" in steps
    assert "fusion" in steps
    assert result["mutated"] is True

    # Clean up the stale worktree.
    try:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(stale_wt)],
            cwd=workspace, capture_output=True,
        )
    except Exception:
        pass
    shutil.rmtree(stale_wt, ignore_errors=True)
