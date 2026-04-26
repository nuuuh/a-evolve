"""Behavioural parity tests for InlineTemplate and OrchestratedTemplate.

Both templates are implemented over the activity runtime and own their
template-specific prompts.  These tests run the rewritten templates
end-to-end against a stub engine and assert the exact side effects
(git commits, tags, StrategyTree state, return-dict shape) that the
original implementation produced.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from agent_evolve.algorithms.navigation.templates.inline import InlineTemplate
from agent_evolve.algorithms.navigation.templates.orchestrated import (
    OrchestratedTemplate,
)
from agent_evolve.contract.workspace import AgentWorkspace
from agent_evolve.engine.versioning import VersionControl
from agent_evolve.types import StrategyTree


# ── Test doubles ─────────────────────────────────────────────────────


class _StubEngine:
    """Minimal engine stand-in: captures prompts and supports a
    workspace-mutating side effect to model the LLM's behaviour.

    ``next_plan`` drives the analyst step when ``OrchestratedTemplate``
    is under test — the stub returns a canned JSON plan so no real LLM
    is needed.
    """

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
        self.calls: list[tuple[str, str]] = []
        self._mutate = None
        self.next_plan: dict[str, Any] | None = None

    def set_mutate(self, fn):
        self._mutate = fn

    def _run_llm(self, prompt: str, workspace_root):
        self.calls.append(("_run_llm", prompt))
        if self._mutate is not None:
            self._mutate()
        return {
            "content": "no mutation",
            "usage": {},
            "conversation": [{"role": "assistant", "content": "ok"}],
        }


def _init_workspace(tmp_path):
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


# ── InlineTemplate ───────────────────────────────────────────────────


def test_inline_noop_returns_unmutated(tmp_path):
    ws, vc = _init_workspace(tmp_path)
    engine = _StubEngine()
    tree = StrategyTree(branches=[])
    tpl = InlineTemplate(engine)

    vc.commit(
        message="pre-nav-evo-0: snapshot before navigation evolution",
        tag="pre-nav-evo-0",
    )

    result = tpl.execute(vc, ws, batch_results=[], tree=tree,
                         evo_number=0, routing_log_path=None)

    assert result["evo_number"] == 0
    assert result["mutated"] is False
    assert result["plan"] == {}
    assert result["branches"] == []
    assert len(result["trajectory"]) == 1
    step = result["trajectory"][0]
    assert step["step"] == "evolve_inline"
    assert step["mutated"] is False
    assert step["new_branches"] == []
    assert "evo-0-main" in vc.list_tags()


def test_inline_detects_prompt_mutation(tmp_path):
    ws, vc = _init_workspace(tmp_path)
    engine = _StubEngine()
    tree = StrategyTree(branches=[])
    tpl = InlineTemplate(engine)
    vc.commit(message="pre-nav-evo-0: snapshot", tag="pre-nav-evo-0")

    def mutate():
        ws.write_prompt("NEW prompt produced by LLM")

    engine.set_mutate(mutate)
    result = tpl.execute(vc, ws, batch_results=[], tree=tree,
                         evo_number=1, routing_log_path=None)

    assert result["mutated"] is True
    assert result["trajectory"][0]["mutated"] is True
    assert "evo-1-main" in vc.list_tags()


def test_inline_registers_branches_created_by_llm(tmp_path):
    ws, vc = _init_workspace(tmp_path)
    engine = _StubEngine()
    tree = StrategyTree(branches=[])
    tpl = InlineTemplate(engine)
    vc.commit(message="pre-nav-evo-0: snapshot", tag="pre-nav-evo-0")

    def mutate():
        vc.create_branch("branch/new-skill", "main")
        vc.checkout_branch("branch/new-skill")
        (ws.root / "README.md").write_text(
            "# Branch: branch/new-skill\n\nSpecialist for widgets.\n"
        )
        vc.commit(message="branch: widget specialist")

    engine.set_mutate(mutate)
    result = tpl.execute(vc, ws, batch_results=[], tree=tree,
                         evo_number=2, routing_log_path=None)

    assert result["mutated"] is True
    assert "branch/new-skill" in [b.name for b in tree.branches]
    assert result["trajectory"][0]["new_branches"] == ["branch/new-skill"]


# ── OrchestratedTemplate ─────────────────────────────────────────────


def _nav_engine():
    """Stub engine with navigation_enabled=True."""
    eng = _StubEngine()
    eng.config.navigation_enabled = True
    return eng


def _flat_engine():
    """Stub engine with navigation_enabled=False (flat multi-agent)."""
    eng = _StubEngine()
    eng.config.navigation_enabled = False
    return eng


def _patch_planner(monkeypatch, plan):
    """Force _run_planner to return a canned plan."""
    monkeypatch.setattr(
        OrchestratedTemplate, "_run_planner",
        lambda self, batch, hist, names, *, navigation_enabled: plan,
    )


def test_orchestrated_noop_when_plan_has_no_assignments(tmp_path, monkeypatch):
    ws, vc = _init_workspace(tmp_path)
    engine = _nav_engine()
    tree = StrategyTree(branches=[])

    _patch_planner(monkeypatch, {
        "summary": "nothing to do",
        "assignments": [],
    })

    tpl = OrchestratedTemplate(engine)
    vc.commit(message="pre-nav-evo-0: snapshot", tag="pre-nav-evo-0")

    result = tpl.execute(vc, ws, batch_results=[], tree=tree,
                         evo_number=0, routing_log_path=None)

    assert result["mutated"] is False
    assert result["plan"]["summary"] == "nothing to do"
    assert result["trajectory"][0]["step"] == "plan"
    # No assignments → no evolver calls → no evo-0-main tag.
    assert "evo-0-main" not in vc.list_tags()


def test_orchestrated_runs_main_assignment(tmp_path, monkeypatch):
    ws, vc = _init_workspace(tmp_path)
    engine = _nav_engine()
    tree = StrategyTree(branches=[])

    _patch_planner(monkeypatch, {
        "summary": "fix search api",
        "assignments": [
            {
                "target": "main",
                "focus": "search API skill",
                "workload": "Update skills/search/SKILL.md with a freshness check.",
                "task_ids": [],
            },
        ],
    })

    def mutate():
        ws.write_prompt(ws.read_prompt() + "\n# evolved")
    engine.set_mutate(mutate)

    tpl = OrchestratedTemplate(engine)
    vc.commit(message="pre-nav-evo-0: snapshot", tag="pre-nav-evo-0")
    result = tpl.execute(vc, ws, batch_results=[], tree=tree,
                         evo_number=1, routing_log_path=None)

    assert result["mutated"] is True
    assert "evo-1-main" in vc.list_tags()
    steps = [t["step"] for t in result["trajectory"]]
    assert "plan" in steps
    assert "deepen_main" in steps


def test_orchestrated_runs_branch_assignment(tmp_path, monkeypatch):
    ws, vc = _init_workspace(tmp_path)
    engine = _nav_engine()
    tree = StrategyTree(branches=[])

    _patch_planner(monkeypatch, {
        "summary": "widget specialist",
        "assignments": [
            {
                "target": "branch/widget-specialist",
                "focus": "widget skills",
                "workload": "Add widget-specific tool handlers.",
                "task_ids": [],
            },
        ],
    })

    def mutate():
        ws.write_prompt(ws.read_prompt() + "\n# widget evolved")
    engine.set_mutate(mutate)

    tpl = OrchestratedTemplate(engine)
    vc.commit(message="pre-nav-evo-0: snapshot", tag="pre-nav-evo-0")
    result = tpl.execute(vc, ws, batch_results=[], tree=tree,
                         evo_number=1, routing_log_path=None)

    assert "branch/widget-specialist" in [b.name for b in tree.branches]
    branch_entries = [t for t in result["trajectory"]
                      if t.get("step") == "branch_evolution"]
    assert len(branch_entries) == 1
    assert branch_entries[0]["target"] == "branch/widget-specialist"
    assert "evo-1-branch-widget-specialist" in vc.list_tags()
    assert vc.get_current_branch() == "main"


def test_orchestrated_runs_multiple_assignments_on_main(tmp_path, monkeypatch):
    """In flat mode (no navigation) the planner may still decompose the
    work into multiple focused passes on main."""
    ws, vc = _init_workspace(tmp_path)
    engine = _flat_engine()
    tree = StrategyTree(branches=[])

    _patch_planner(monkeypatch, {
        "summary": "two focused fixes on main",
        "assignments": [
            {"target": "main", "focus": "parser fix",
             "workload": "Fix the output parser.", "task_ids": []},
            {"target": "main", "focus": "memory cleanup",
             "workload": "Drop stale memory entries.", "task_ids": []},
        ],
    })

    def mutate():
        ws.write_prompt(ws.read_prompt() + "\n# flat-evolved")
    engine.set_mutate(mutate)

    tpl = OrchestratedTemplate(engine)
    vc.commit(message="pre-nav-evo-0: snapshot", tag="pre-nav-evo-0")
    result = tpl.execute(vc, ws, batch_results=[], tree=tree,
                         evo_number=2, routing_log_path=None)

    # Two main assignments → two LLM calls → the stub engine recorded both.
    llm_calls = [c for c in engine.calls if c[0] == "_run_llm"]
    assert len(llm_calls) == 2
    # Both trajectory entries are "deepen_main" with distinct focuses.
    focuses = [t["focus"] for t in result["trajectory"]
               if t.get("step") == "deepen_main"]
    assert focuses == ["parser fix", "memory cleanup"]


def test_orchestrated_flat_mode_drops_branch_assignments(tmp_path, monkeypatch):
    """In flat mode, branch-targeting assignments are dropped with a warning
    rather than silently creating a branch."""
    ws, vc = _init_workspace(tmp_path)
    engine = _flat_engine()
    tree = StrategyTree(branches=[])

    _patch_planner(monkeypatch, {
        "summary": "mixed",
        "assignments": [
            {"target": "main", "focus": "main tweak",
             "workload": "Update main.", "task_ids": []},
            {"target": "branch/illegal", "focus": "illegal",
             "workload": "Should be dropped.", "task_ids": []},
        ],
    })

    tpl = OrchestratedTemplate(engine)
    vc.commit(message="pre-nav-evo-0: snapshot", tag="pre-nav-evo-0")
    tpl.execute(vc, ws, batch_results=[], tree=tree,
                evo_number=3, routing_log_path=None)

    # No branch created.
    assert tree.branches == []
    # Only the main assignment ran the LLM.
    llm_calls = [c for c in engine.calls if c[0] == "_run_llm"]
    assert len(llm_calls) == 1


def test_orchestrated_flat_planner_prompt_differs_from_nav(monkeypatch):
    """The planner system prompt is different between nav and flat modes."""
    from agent_evolve.algorithms.navigation.templates.orchestrated import (
        PLANNER_SYSTEM_PROMPT_FLAT, PLANNER_SYSTEM_PROMPT_NAV,
    )
    assert PLANNER_SYSTEM_PROMPT_FLAT != PLANNER_SYSTEM_PROMPT_NAV
    assert "branch" not in PLANNER_SYSTEM_PROMPT_FLAT.lower() or \
        "no branching" in PLANNER_SYSTEM_PROMPT_FLAT.lower()
    # Sanity: both prompts mention "assignments" (the new schema).
    assert "assignments" in PLANNER_SYSTEM_PROMPT_NAV.lower()
    assert "assignments" in PLANNER_SYSTEM_PROMPT_FLAT.lower()


def test_legacy_plan_shape_still_parses(tmp_path, monkeypatch):
    """Old {main_evolution, branches} plan shape is translated to the new
    assignment schema by _parse_plan."""
    from agent_evolve.algorithms.navigation.templates.orchestrated import (
        _parse_plan,
    )
    legacy = """
    {"summary": "legacy",
     "main_evolution": {"description": "do main stuff", "insights": [],
                        "task_ids": ["t1"]},
     "branches": [{"name": "branch/x", "description": "x regime",
                   "evolution_guidance": "tweak x", "task_ids": ["t2"]}]}
    """
    plan = _parse_plan(legacy, navigation_enabled=True)
    assert "assignments" in plan
    targets = [a["target"] for a in plan["assignments"]]
    assert "main" in targets
    assert "branch/x" in targets
