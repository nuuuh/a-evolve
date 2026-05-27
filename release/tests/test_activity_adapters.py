"""Phase 4 tests — adapters.

Verifies that ``ActivityTemplate`` satisfies the ``EvolutionTemplate``
interface and plugs into ``NavigationEngine`` via the ``template=``
kwarg.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from agent_evolve.algorithms.navigation.activity import (
    ActivityBuilder,
    Type,
)
from agent_evolve.algorithms.navigation.activity.adapters import ActivityTemplate
from agent_evolve.algorithms.navigation.templates.base import EvolutionTemplate


class _FakeEngine:
    """Minimal engine stub — enough for adapter construction tests."""

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


def _trivial_activity():
    """Minimal Activity declaring the standard binding parameters."""
    return (
        ActivityBuilder("trivial")
        .parameter("workspace", Type.WORKSPACE)
        .parameter("git", Type.GIT_TREE)
        .parameter("batch", Type.BATCH_RESULTS)
        .parameter("cfg", Type.CONFIG)
        .parameter("evo_number", Type.INTEGER)
        .build_unchecked()
    )


def test_activity_template_satisfies_protocol():
    tpl = ActivityTemplate(_trivial_activity(), _FakeEngine())
    assert isinstance(tpl, EvolutionTemplate)
    assert tpl.name.startswith("activity:")


def test_activity_template_plugs_into_navigation_engine_template_slot():
    """NavigationEngine exposes a ``template=`` kwarg that accepts any
    EvolutionTemplate.  ActivityTemplate should be assignable there."""
    from agent_evolve.algorithms.navigation.engine import NavigationEngine

    tpl = ActivityTemplate(_trivial_activity(), _FakeEngine())
    assert isinstance(tpl, EvolutionTemplate)
    import inspect
    sig = inspect.signature(NavigationEngine.__init__)
    assert "template" in sig.parameters


def test_activity_template_runs_against_real_workspace(tmp_path):
    """Running the trivial Activity against a real workspace produces a
    well-formed return dict — shape is independent of Activity body."""
    from agent_evolve.contract.workspace import AgentWorkspace
    from agent_evolve.engine.versioning import VersionControl
    from agent_evolve.types import StrategyTree

    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    for d in ("prompts", "skills", "tools", "memory"):
        (ws_dir / d).mkdir()
    (ws_dir / "prompts" / "system.md").write_text("x")
    (ws_dir / "skills" / "_drafts").mkdir()
    (ws_dir / "tools" / "registry.yaml").write_text("tools: []\n")
    vc = VersionControl(ws_dir)
    vc.init()

    tpl = ActivityTemplate(_trivial_activity(), _FakeEngine())
    result = tpl.execute(
        vc=vc,
        solver_workspace=AgentWorkspace(ws_dir),
        batch_results=[],
        tree=StrategyTree(branches=[]),
        evo_number=0,
        routing_log_path=None,
    )
    assert set(result) >= {"evo_number", "mutated", "plan", "branches", "trajectory"}
    assert result["evo_number"] == 0
    assert result["mutated"] is False  # trivial activity does nothing
