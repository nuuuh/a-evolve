"""Tests for V2 evolution templates and guardrails."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml


def _init_git(root: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
    for d in ("prompts", "skills", "memory", "tools", "infra"):
        (root / d).mkdir(exist_ok=True)
    (root / "prompts" / "system.md").write_text("seed prompt")
    (root / "tools" / "registry.yaml").write_text("tools: []\n")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=root, check=True)


def _make_batch(n: int = 4) -> list[dict]:
    return [
        {"instance_id": f"task_{i}", "success": i % 2 == 0,
         "score": float(i % 2 == 0), "turns": 5,
         "task_input": f"Will event {i} happen by date X?",
         "batch_num": 1, "evo_cycle": 1}
        for i in range(n)
    ]


class _StubTree:
    branches = []
    def branch_names(self): return ["main"]
    def to_dict(self): return {}


class _FakeEngine:
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
    llm = None

    def __init__(self):
        self._call_count = 0

    def _run_llm(self, prompt, workspace_root, **kwargs):
        self._call_count += 1
        ws = Path(workspace_root)
        if self._call_count == 1:
            # First call: scout writes discoveries (or single evolver writes tools)
            (ws / "infra").mkdir(exist_ok=True)
            (ws / "infra" / "discoveries.jsonl").write_text(
                json.dumps({"source": "google_news_rss", "works": True, "latency_s": 0.3}) + "\n"
                + json.dumps({"source": "duckduckgo_html", "works": False, "error": "timeout"}) + "\n"
            )
        # Every call: write tools + prompt (ensures commit has changes)
        (ws / "tools" / "news_search.py").write_text(
            f'#!/usr/bin/env python3\nimport sys\nprint("results for:", sys.argv[1], "call {self._call_count}")\n'
        )
        (ws / "tools" / "broken.py").write_text(
            '#!/usr/bin/env python3\nimport sys; sys.exit(1)\n'
        )
        (ws / "tools" / "registry.yaml").write_text(yaml.dump({
            "tools": [
                {"name": "news_search", "description": "Google News RSS"},
                {"name": "broken", "description": "fails"},
            ]
        }))
        (ws / "prompts" / "system.md").write_text(
            f"You are a prediction agent (v{self._call_count}).\n\n"
            "Use 2-4 searches then submit.\n\n"
            "HARD SEARCH LIMITS: maximum 5 searches per task.\n"
        )
        return {"content": "done", "conversation": []}


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    _init_git(ws)
    return ws


@pytest.fixture
def engine():
    e = _FakeEngine()
    e.config = _FakeEngine.config
    return e


@pytest.fixture
def vc(workspace):
    from agent_evolve.engine.versioning import VersionControl
    return VersionControl(workspace)


@pytest.fixture
def agent_workspace(workspace):
    from agent_evolve.contract.workspace import AgentWorkspace
    return AgentWorkspace(workspace)


# ── Guardrails tests ──


def test_strip_search_caps():
    from agent_evolve.algorithms.navigation.templates._guardrails import strip_search_caps
    prompt = "Use 2-4 searches then submit.\nHARD SEARCH LIMITS: max 5.\nOther text."
    cleaned = strip_search_caps(prompt)
    assert "2-4 searches" not in cleaned
    assert "HARD SEARCH LIMIT" not in cleaned
    assert "Other text" in cleaned


def test_verify_tools_removes_broken(workspace):
    from agent_evolve.algorithms.navigation.templates._guardrails import verify_tools
    (workspace / "tools" / "good.py").write_text(
        '#!/usr/bin/env python3\nimport sys\nprint("ok", sys.argv[1])\n'
    )
    (workspace / "tools" / "bad.py").write_text(
        '#!/usr/bin/env python3\nimport sys; sys.exit(1)\n'
    )
    (workspace / "tools" / "registry.yaml").write_text(yaml.dump({
        "tools": [
            {"name": "good", "description": "works"},
            {"name": "bad", "description": "fails"},
        ]
    }))
    removed = verify_tools(workspace)
    assert "bad" in removed
    assert "good" not in removed
    reg = yaml.safe_load((workspace / "tools" / "registry.yaml").read_text())
    assert len(reg["tools"]) == 1
    assert reg["tools"][0]["name"] == "good"


def test_cap_prompt_size(workspace):
    from agent_evolve.algorithms.navigation.templates._guardrails import cap_prompt_size
    (workspace / "prompts" / "system.md").write_text("x" * 15000)
    truncated = cap_prompt_size(workspace, max_chars=10000)
    assert truncated is True
    assert len((workspace / "prompts" / "system.md").read_text()) == 10000


def test_apply_all_guardrails(workspace):
    from agent_evolve.algorithms.navigation.templates._guardrails import apply_all_guardrails
    (workspace / "tools" / "good.py").write_text(
        '#!/usr/bin/env python3\nimport sys\nprint("ok")\n'
    )
    (workspace / "tools" / "bad.py").write_text(
        '#!/usr/bin/env python3\nimport sys; sys.exit(1)\n'
    )
    (workspace / "tools" / "registry.yaml").write_text(yaml.dump({
        "tools": [
            {"name": "good", "description": "works"},
            {"name": "bad", "description": "fails"},
        ]
    }))
    (workspace / "prompts" / "system.md").write_text(
        "Limit searches to 3.\n" + "x" * 12000
    )
    results = apply_all_guardrails(workspace)
    assert results["search_caps_stripped"] is True
    assert "bad" in results["tools_removed"]
    assert results["prompt_truncated"] is True


# ── Deep single template ──


def test_deep_single_trajectory(workspace, engine, vc, agent_workspace):
    from agent_evolve.algorithms.navigation.templates.deep_single import Template
    template = Template(engine)
    result = template.execute(
        vc, agent_workspace, _make_batch(4),
        _StubTree(), evo_number=1, routing_log_path=None,
    )
    steps = [s["step"] for s in result["trajectory"]]
    assert "evolve" in steps
    assert "guardrails" in steps
    assert result["mutated"] is True

    # G2: search caps stripped from evolved prompt.
    reg = yaml.safe_load((workspace / "tools" / "registry.yaml").read_text())
    tool_names = [t["name"] for t in reg.get("tools", [])]
    assert "broken" not in tool_names  # G4: broken tool removed
    assert "news_search" in tool_names  # G4: working tool kept

    prompt = (workspace / "prompts" / "system.md").read_text()
    assert "2-4 searches" not in prompt  # G2
    assert "HARD SEARCH" not in prompt  # G2
    assert len(prompt) <= 10000  # G5: prompt capped


# ── Scout evolver template ──


def test_scout_evolver_trajectory(workspace, engine, vc, agent_workspace):
    from agent_evolve.algorithms.navigation.templates.scout_evolver import Template
    template = Template(engine)
    result = template.execute(
        vc, agent_workspace, _make_batch(4),
        _StubTree(), evo_number=1, routing_log_path=None,
    )
    steps = [s["step"] for s in result["trajectory"]]
    assert "scout" in steps
    assert "evolve" in steps
    assert "guardrails" in steps
    assert result["mutated"] is True

    # Verify discoveries were written and consumed.
    disc = workspace / "infra" / "discoveries.jsonl"
    assert disc.exists()
    lines = [json.loads(l) for l in disc.read_text().splitlines() if l.strip()]
    assert any(d.get("source") == "google_news_rss" for d in lines)

    # G2: search caps stripped.
    prompt = (workspace / "prompts" / "system.md").read_text()
    assert "2-4 searches" not in prompt
    assert "HARD SEARCH" not in prompt

    # G4: broken tool removed, working tool kept.
    reg = yaml.safe_load((workspace / "tools" / "registry.yaml").read_text())
    tool_names = [t["name"] for t in reg.get("tools", [])]
    assert "broken" not in tool_names
    assert "news_search" in tool_names

    # G5: prompt capped.
    assert len(prompt) <= 10000


# ── Orthogonal pair template ──


def test_orthogonal_pair_general_only(workspace, engine, vc, agent_workspace):
    """No hard tasks → only general_tool_agent runs."""
    from agent_evolve.algorithms.navigation.templates.orthogonal_pair import Template
    template = Template(engine)
    batch = _make_batch(4)  # no difficulty_level or domain fields
    result = template.execute(
        vc, agent_workspace, batch,
        _StubTree(), evo_number=1, routing_log_path=None,
    )
    steps = [s["step"] for s in result["trajectory"]]
    assert "dispatch" in steps
    assert "general_tool_agent" in steps
    assert "domain_expert" not in steps
    assert "guardrails" in steps
    assert result["mutated"] is True

    # G2-G5 compliance.
    prompt = (workspace / "prompts" / "system.md").read_text()
    assert "2-4 searches" not in prompt
    assert len(prompt) <= 10000
    reg = yaml.safe_load((workspace / "tools" / "registry.yaml").read_text())
    assert all(t["name"] != "broken" for t in reg.get("tools", []))


def test_orthogonal_pair_with_hard_tasks(workspace, engine, vc, agent_workspace):
    """Hard tasks → both general + domain expert run."""
    from agent_evolve.algorithms.navigation.templates.orthogonal_pair import Template
    template = Template(engine)
    batch = _make_batch(4)
    batch[0]["difficulty_level"] = 3
    batch[1]["domain"] = "chinese"
    result = template.execute(
        vc, agent_workspace, batch,
        _StubTree(), evo_number=1, routing_log_path=None,
    )
    steps = [s["step"] for s in result["trajectory"]]
    assert "general_tool_agent" in steps
    assert "domain_expert" in steps
    assert "guardrails" in steps

    dispatch = next(s for s in result["trajectory"] if s["step"] == "dispatch")
    assert dispatch["n_hard_tasks"] == 2
    assert dispatch["run_domain_expert"] is True


def test_orthogonal_pair_nested_metadata(workspace, engine, vc, agent_workspace):
    """Hard tasks detected via nested task_metadata (production shape)."""
    from agent_evolve.algorithms.navigation.templates.orthogonal_pair import Template
    template = Template(engine)
    batch = _make_batch(4)
    # Only nested metadata — no top-level difficulty_level/domain.
    batch[0]["task_metadata"] = {"difficulty_level": 4, "domain": "sports"}
    batch[2]["task_metadata"] = {"difficulty_level": 2, "domain": "chinese"}
    result = template.execute(
        vc, agent_workspace, batch,
        _StubTree(), evo_number=1, routing_log_path=None,
    )
    dispatch = next(s for s in result["trajectory"] if s["step"] == "dispatch")
    assert dispatch["n_hard_tasks"] == 2
    assert dispatch["run_domain_expert"] is True


# ── Planner task_preview ──


def test_planner_prompt_includes_task_preview():
    from agent_evolve.algorithms.navigation.templates.orchestrated import build_planner_prompt
    batch = [
        {"instance_id": "futurex_past_0057", "turns": 5,
         "task_input": "Will the US Storm Prediction Center issue a Tornado Watch?"},
    ]
    prompt = build_planner_prompt(
        batch, evolution_history=[], branches=["main"],
        navigation_enabled=False,
    )
    assert "Tornado Watch" in prompt
    assert "task_preview" in prompt or "Storm Prediction" in prompt


# ── Discovery cache template ──


def test_discovery_cache_trajectory(workspace, engine, vc, agent_workspace):
    from agent_evolve.algorithms.navigation.templates.discovery_cache import Template
    template = Template(engine)
    result = template.execute(
        vc, agent_workspace, _make_batch(4),
        _StubTree(), evo_number=1, routing_log_path=None,
    )
    steps = [s["step"] for s in result["trajectory"]]
    assert "cache_state" in steps
    assert "tool_builder" in steps
    assert "strategy_writer" in steps
    assert "cache_growth" in steps
    assert "guardrails" in steps
    assert result["mutated"] is True

    # Cache file created with valid records.
    cache = workspace / "infra" / "discovery_cache.jsonl"
    assert cache.exists()
    records = [json.loads(l) for l in cache.read_text().splitlines() if l.strip()]
    assert len(records) >= 2  # at least cycle_start + tool_test records
    # Validate schema.
    for r in records:
        assert "cycle" in r
        assert "type" in r

    # Cache growth reported in trajectory.
    growth = next(s for s in result["trajectory"] if s["step"] == "cache_growth")
    assert growth["new_records"] >= 2

    # G2-G5 compliance.
    prompt = (workspace / "prompts" / "system.md").read_text()
    assert "2-4 searches" not in prompt
    assert len(prompt) <= 10000
    reg = yaml.safe_load((workspace / "tools" / "registry.yaml").read_text())
    assert all(t["name"] != "broken" for t in reg.get("tools", []))


# ── Population template ──


def test_population_trajectory(workspace, engine, vc, agent_workspace):
    from agent_evolve.algorithms.navigation.templates.population import Template
    template = Template(engine)
    result = template.execute(
        vc, agent_workspace, _make_batch(4),
        _StubTree(), evo_number=1, routing_log_path=None,
    )
    steps = [s["step"] for s in result["trajectory"]]

    # Must have candidate steps + tournament + fusion + guardrails.
    assert sum(1 for s in steps if s == "candidate") >= 2
    assert "tournament" in steps
    assert "fusion" in steps
    assert "guardrails" in steps

    # Tournament selected a winner.
    tournament = next(s for s in result["trajectory"] if s["step"] == "tournament")
    assert tournament["winner_index"] is not None

    # G2-G5.
    prompt = (workspace / "prompts" / "system.md").read_text()
    assert "2-4 searches" not in prompt
    assert len(prompt) <= 10000
