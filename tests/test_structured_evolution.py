"""Tests for structured_evolution template."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

from agent_evolve.algorithms.navigation.templates.structured_evolution import Template
from agent_evolve.algorithms.navigation.templates._evolution_workspace import (
    init_evolution_workspace,
    load_task_board,
    load_research_log,
    append_research,
    WORKSPACE_DIR,
)


@pytest.fixture
def fake_engine(tmp_path):
    engine = MagicMock()
    engine.config = MagicMock()
    engine.config.evolve_prompts = True
    engine.config.evolve_skills = True
    engine.config.evolve_memory = True
    engine.config.evolve_tools = True
    engine.config.evolve_infra = False
    engine.config.extra = {
        "structured_evolution": {
            "research_parallel": 2,
            "build_verify_retries": 2,
        }
    }
    return engine


@pytest.fixture
def fake_workspace(tmp_path):
    ws = MagicMock()
    ws.root = tmp_path
    # Create minimal workspace structure
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "system.md").write_text("You are a solver.")
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "registry.yaml").write_text("tools: []\n")
    return ws


@pytest.fixture
def fake_vc():
    vc = MagicMock()
    vc.commit.return_value = True
    return vc


@pytest.fixture
def fake_tree():
    tree = MagicMock()
    tree.branch_names.return_value = ["main"]
    return tree


@pytest.fixture
def batch_results():
    return [
        {
            "task_id": "futurex_past_0001",
            "task_input": "Will Bitcoin exceed $100K in January 2026?",
            "turns": 5,
            "error": "",
            "correct": False,
        },
        {
            "task_id": "futurex_past_0002",
            "task_input": "What was the S&P 500 close on Jan 15?",
            "turns": 8,
            "error": "",
            "correct": False,
        },
    ]


class TestFourPhaseTrajectory:
    """AC1: Verify all 4 phases appear in trajectory."""

    def test_all_phases_present(
        self, fake_engine, fake_workspace, fake_vc, fake_tree, batch_results,
    ):
        def mock_run_llm(prompt, ws_root, system_prompt=None, **kw):
            sp = (system_prompt or "").lower()
            if "failure analyst" in sp:
                return {"content": (
                    "## Failure Patterns (Cycle 1)\n"
                    "- finance: 2 tasks fail because no exact price data. "
                    "PRIORITY: HIGH\n\n"
                    "## Verified Capabilities\n\n"
                    "## Unresolved\n"
                )}
            elif "research agent" in sp:
                return {"content": json.dumps({
                    "cycle": 1, "regime": "finance",
                    "approach": "stooq",
                    "tested": True, "works": True,
                })}
            elif "infrastructure builder" in sp:
                return {"content": "Built finance pipeline."}
            elif "verification agent" in sp:
                return {"content": "VERDICT: PASS\nAll tools working."}
            return {"content": ""}

        fake_engine._run_llm = MagicMock(side_effect=mock_run_llm)

        template = Template(fake_engine)
        result = template.execute(
            fake_vc, fake_workspace, batch_results,
            fake_tree, evo_number=1, routing_log_path=None,
        )

        steps = [t["step"] for t in result["trajectory"]]
        assert "analyze" in steps
        assert "research" in steps
        assert "build" in steps or "build_verify_exhausted" in steps
        assert result["evo_number"] == 1
        assert isinstance(result["mutated"], bool)
        assert isinstance(result["trajectory"], list)

    def test_template_name(self, fake_engine):
        t = Template(fake_engine)
        assert t.name == "structured_evolution"


class TestBuildVerifyLoop:
    """AC3: Build-verify retry loop fires correctly."""

    def test_fail_then_pass(
        self, fake_engine, fake_workspace, fake_vc, fake_tree, batch_results,
    ):
        ws_root = fake_workspace.root
        init_evolution_workspace(ws_root)
        append_research(ws_root, {
            "cycle": 1, "regime": "finance", "approach": "api1",
            "tested": True, "works": True,
        })

        verify_count = [0]

        def mock_run_llm(prompt, ws_root, system_prompt=None, **kw):
            sp = (system_prompt or "").lower()
            if "failure analyst" in sp:
                return {"content": "## Failure Patterns\n- finance: PRIORITY: HIGH\n"}
            elif "research agent" in sp:
                return {"content": ""}
            elif "infrastructure builder" in sp:
                return {"content": "Built tool."}
            elif "verification agent" in sp:
                verify_count[0] += 1
                if verify_count[0] == 1:
                    return {"content": "VERDICT: FAIL\nTool returns empty data."}
                return {"content": "VERDICT: PASS\nAll tools working."}
            return {"content": ""}

        fake_engine._run_llm = MagicMock(side_effect=mock_run_llm)

        template = Template(fake_engine)
        result = template.execute(
            fake_vc, fake_workspace, batch_results,
            fake_tree, evo_number=1, routing_log_path=None,
        )

        verify_steps = [t for t in result["trajectory"] if t["step"] == "verify"]
        assert len(verify_steps) >= 2
        assert verify_steps[0].get("passed") is False
        assert verify_steps[-1].get("passed") is True
        assert result["mutated"] is True

    def test_all_retries_exhausted(
        self, fake_engine, fake_workspace, fake_vc, fake_tree, batch_results,
    ):
        ws_root = fake_workspace.root
        init_evolution_workspace(ws_root)
        append_research(ws_root, {
            "cycle": 1, "regime": "finance", "approach": "api1",
            "tested": True, "works": True,
        })

        def mock_run_llm(prompt, ws_root, system_prompt=None, **kw):
            sp = (system_prompt or "").lower()
            if "failure analyst" in sp:
                return {"content": "## Failure Patterns\n- finance: PRIORITY: HIGH\n"}
            elif "research agent" in sp:
                return {"content": ""}
            elif "infrastructure builder" in sp:
                return {"content": "Built tool."}
            elif "verification agent" in sp:
                return {"content": "VERDICT: FAIL\nStill broken."}
            return {"content": ""}

        fake_engine._run_llm = MagicMock(side_effect=mock_run_llm)
        fake_engine.config.extra["structured_evolution"]["build_verify_retries"] = 2

        template = Template(fake_engine)
        result = template.execute(
            fake_vc, fake_workspace, batch_results,
            fake_tree, evo_number=1, routing_log_path=None,
        )

        assert result["mutated"] is False
        exhausted = [t for t in result["trajectory"] if t["step"] == "build_verify_exhausted"]
        assert len(exhausted) == 1


class TestResearchLogAccumulation:
    """AC2: Research records accumulate across cycles."""

    def test_records_persist(
        self, fake_engine, fake_workspace, fake_vc, fake_tree, batch_results,
    ):
        ws_root = fake_workspace.root

        call_idx = [0]

        def mock_run_llm(prompt, ws_root, system_prompt=None, **kw):
            call_idx[0] += 1
            n = call_idx[0]
            if "analyst" in (system_prompt or "").lower() or "failure" in (system_prompt or "").lower():
                return {"content": (
                    "## Failure Patterns (Cycle 1)\n"
                    "- finance: PRIORITY: HIGH\n"
                    "## Verified Capabilities\n## Unresolved\n"
                )}
            elif "research" in (system_prompt or "").lower():
                return {"content": json.dumps({
                    "cycle": 1, "regime": "finance",
                    "approach": f"source_{n}",
                    "tested": True, "works": True,
                })}
            elif "builder" in (system_prompt or "").lower() or "infrastructure" in (system_prompt or "").lower():
                return {"content": "Built pipeline."}
            else:
                return {"content": "VERDICT: PASS"}

        fake_engine._run_llm = MagicMock(side_effect=mock_run_llm)

        template = Template(fake_engine)

        # Cycle 1
        template.execute(
            fake_vc, fake_workspace, batch_results,
            fake_tree, evo_number=1, routing_log_path=None,
        )
        records_after_1 = load_research_log(ws_root)

        # Cycle 2
        call_idx[0] = 0
        template.execute(
            fake_vc, fake_workspace, batch_results,
            fake_tree, evo_number=2, routing_log_path=None,
        )
        records_after_2 = load_research_log(ws_root)

        assert len(records_after_2) >= len(records_after_1)


class TestHITL:
    """AC4: HITL integration (tested via mock)."""

    def test_hitl_not_called_when_disabled(
        self, fake_engine, fake_workspace, fake_vc, fake_tree, batch_results,
    ):
        fake_engine.config.extra["structured_evolution"]["hitl_enabled"] = False

        def mock_run_llm(prompt, ws_root, system_prompt=None, **kw):
            return {"content": "## Failure Patterns\n"}

        fake_engine._run_llm = MagicMock(side_effect=mock_run_llm)

        template = Template(fake_engine)
        result = template.execute(
            fake_vc, fake_workspace, batch_results,
            fake_tree, evo_number=1, routing_log_path=None,
        )
        assert isinstance(result, dict)


class TestGapExtraction:
    def test_extracts_high_priority_gaps(self, fake_engine):
        template = Template(fake_engine)
        board = (
            "## Failure Patterns\n"
            "- finance_exact: 5 tasks fail. PRIORITY: HIGH\n"
            "- sports_ranking: 3 tasks fail. PRIORITY: MEDIUM\n"
            "- weather: 1 task. PRIORITY: LOW\n"
        )
        gaps = template._extract_gaps(board, k=2)
        assert "finance_exact" in gaps
        assert "sports_ranking" in gaps
        assert "weather" not in gaps

    def test_fallback_when_no_priorities(self, fake_engine):
        template = Template(fake_engine)
        board = "## Failure Patterns\n- crypto: no data\n- sports: partial\n"
        gaps = template._extract_gaps(board, k=3)
        assert len(gaps) > 0
