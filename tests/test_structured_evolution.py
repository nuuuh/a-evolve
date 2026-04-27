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
    """4-task batch per AC1 requirement."""
    return [
        {
            "task_id": "futurex_past_0001",
            "task_input": "Will Bitcoin exceed $100K in January 2026?",
            "turns": 5, "error": "", "correct": False,
        },
        {
            "task_id": "futurex_past_0002",
            "task_input": "What was the S&P 500 close on Jan 15?",
            "turns": 8, "error": "", "correct": False,
        },
        {
            "task_id": "futurex_past_0003",
            "task_input": "Who won the AFCON 2025 tournament?",
            "turns": 6, "error": "", "correct": False,
        },
        {
            "task_id": "futurex_past_0004",
            "task_input": "What was the Douban rating of Ne Zha 2?",
            "turns": 4, "error": "", "correct": False,
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
                    "approach": "stooq", "endpoint": "https://stooq.com/",
                    "tested": True, "works": True, "latency_ms": 300,
                    "coverage": ["us_stocks"], "does_not_cover": [],
                    "complementary_to": [], "sample_output": "Date,Close",
                    "credential_needed": False, "credential_env": "",
                    "error": "", "notes": "CSV data",
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
            "endpoint": "https://api1.example.com", "tested": True, "works": True,
            "coverage": ["us_stocks"], "sample_output": "data",
            "credential_needed": False, "error": "",
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
            "endpoint": "https://api1.example.com", "tested": True, "works": True,
            "coverage": ["us_stocks"], "sample_output": "data",
            "credential_needed": False, "error": "",
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

    def test_exhausted_rolls_back_and_logs_failure(
        self, fake_engine, fake_workspace, fake_vc, fake_tree, batch_results,
    ):
        ws_root = fake_workspace.root
        init_evolution_workspace(ws_root)
        append_research(ws_root, {
            "cycle": 1, "regime": "finance", "approach": "api1",
            "endpoint": "https://api1.example.com", "tested": True, "works": True,
            "coverage": ["us_stocks"], "sample_output": "data",
            "credential_needed": False, "error": "",
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
                return {"content": "VERDICT: FAIL\nBroken."}
            return {"content": ""}

        fake_engine._run_llm = MagicMock(side_effect=mock_run_llm)
        fake_engine.config.extra["structured_evolution"]["build_verify_retries"] = 1

        template = Template(fake_engine)
        result = template.execute(
            fake_vc, fake_workspace, batch_results,
            fake_tree, evo_number=1, routing_log_path=None,
        )

        assert result["mutated"] is False
        # rollback_to_tag was called to clean up
        fake_vc.rollback_to_tag.assert_called()
        # tool_test failure record was logged
        records = load_research_log(ws_root)
        tool_tests = [r for r in records if r.get("type") == "tool_test"]
        assert len(tool_tests) >= 1
        assert tool_tests[-1]["works"] is False

    def test_pass_logs_success_record(
        self, fake_engine, fake_workspace, fake_vc, fake_tree, batch_results,
    ):
        ws_root = fake_workspace.root
        init_evolution_workspace(ws_root)
        append_research(ws_root, {
            "cycle": 1, "regime": "finance", "approach": "api1",
            "endpoint": "https://api1.example.com", "tested": True, "works": True,
            "coverage": ["us_stocks"], "sample_output": "data",
            "credential_needed": False, "error": "",
        })

        def mock_run_llm(prompt, ws_root, system_prompt=None, **kw):
            sp = (system_prompt or "").lower()
            if "failure analyst" in sp:
                return {"content": "## Failure Patterns\n- finance: PRIORITY: HIGH\n"}
            elif "research agent" in sp:
                return {"content": ""}
            elif "infrastructure builder" in sp:
                return {"content": "Built pipeline."}
            elif "verification agent" in sp:
                return {"content": "VERDICT: PASS\nAll good."}
            return {"content": ""}

        fake_engine._run_llm = MagicMock(side_effect=mock_run_llm)

        template = Template(fake_engine)
        result = template.execute(
            fake_vc, fake_workspace, batch_results,
            fake_tree, evo_number=1, routing_log_path=None,
        )

        assert result["mutated"] is True
        records = load_research_log(ws_root)
        tool_tests = [r for r in records if r.get("type") == "tool_test"]
        assert len(tool_tests) >= 1
        assert tool_tests[-1]["works"] is True


class TestRollbackRemovesAddedFiles:
    """AC3: rollback_to_tag removes files added after the tag."""

    def test_rollback_removes_new_file(self, tmp_path):
        """Integration test with real git repo: file added after tag is gone."""
        import subprocess
        repo = tmp_path / "repo"
        repo.mkdir()

        def run(*args):
            subprocess.run(args, cwd=repo, capture_output=True, check=True)

        run("git", "init")
        run("git", "config", "user.email", "test@test.com")
        run("git", "config", "user.name", "test")

        # Initial commit + tag
        (repo / "good.txt").write_text("original")
        (repo / "tools").mkdir()
        (repo / "tools" / "registry.yaml").write_text("tools: []\n")
        run("git", "add", "-A")
        run("git", "commit", "-m", "initial")
        run("git", "tag", "pre-build")

        # Builder adds a bad pipeline + modifies registry
        (repo / "infra").mkdir()
        (repo / "infra" / "bad_pipeline.py").write_text("class Bad: pass")
        (repo / "tools" / "registry.yaml").write_text("tools:\n  - bad_pipeline\n")
        run("git", "add", "-A")
        run("git", "commit", "-m", "build: bad pipeline")

        # Rollback using VersionControl
        from agent_evolve.engine.versioning import VersionControl
        vc = VersionControl(repo)
        vc.rollback_to_tag("pre-build")

        # bad_pipeline.py must be gone
        assert not (repo / "infra" / "bad_pipeline.py").exists()
        # registry restored to original
        assert "bad_pipeline" not in (repo / "tools" / "registry.yaml").read_text()
        # original file preserved
        assert (repo / "good.txt").read_text() == "original"


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
                    "endpoint": f"https://source{n}.example.com",
                    "tested": True, "works": True, "latency_ms": 200,
                    "coverage": ["us_stocks"], "does_not_cover": [],
                    "complementary_to": [], "sample_output": "data",
                    "credential_needed": False, "credential_env": "",
                    "error": "", "notes": "",
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

    def test_hitl_credential_prompt_fires(
        self, fake_engine, fake_workspace, fake_vc, fake_tree, batch_results,
    ):
        ws_root = fake_workspace.root
        init_evolution_workspace(ws_root)
        # Seed a credential-needed record
        append_research(ws_root, {
            "cycle": 1, "regime": "chinese_search", "approach": "serper_api",
            "tested": False, "works": "unknown",
            "endpoint": "", "sample_output": "", "credential_needed": True,
            "credential_env": "SERPER_API_KEY", "error": "",
        })

        fake_engine.config.extra["structured_evolution"]["hitl_enabled"] = True
        fake_engine.config.extra["human_interface"] = "stdin"

        mock_hi = MagicMock()
        mock_hi.handle.return_value = "sk-test-key-123"

        def mock_run_llm(prompt, ws_root, system_prompt=None, **kw):
            sp = (system_prompt or "").lower()
            if "failure analyst" in sp:
                return {"content": "## Failure Patterns\n- chinese_search: PRIORITY: HIGH\n"}
            elif "retesting" in sp:
                # Retest call after credential supplied
                return {"content": json.dumps({
                    "cycle": 1, "regime": "chinese_search",
                    "approach": "serper_api", "endpoint": "https://serper.dev/",
                    "tested": True, "works": True, "latency_ms": 500,
                    "coverage": ["chinese_web"], "does_not_cover": [],
                    "complementary_to": [], "sample_output": "results...",
                    "credential_needed": True, "credential_env": "SERPER_API_KEY",
                    "error": "", "notes": "Needs API key",
                })}
            elif "research agent" in sp:
                return {"content": ""}
            elif "infrastructure builder" in sp:
                return {"content": "Built."}
            elif "verification agent" in sp:
                return {"content": "VERDICT: PASS"}
            return {"content": ""}

        fake_engine._run_llm = MagicMock(side_effect=mock_run_llm)

        with patch(
            "agent_evolve.algorithms.navigation.templates.structured_evolution.create_interface",
            return_value=mock_hi,
        ):
            template = Template(fake_engine)
            result = template.execute(
                fake_vc, fake_workspace, batch_results,
                fake_tree, evo_number=1, routing_log_path=None,
            )

        # Credential prompt was called
        mock_hi.handle.assert_called()
        cred_calls = [
            c for c in mock_hi.handle.call_args_list
            if "credential" in str(c).lower()
        ]
        assert len(cred_calls) >= 1

        # hitl_credentials step with retest
        hitl_steps = [t for t in result["trajectory"] if t["step"] == "hitl_credentials"]
        assert len(hitl_steps) == 1
        assert hitl_steps[0]["pending"] >= 1
        assert hitl_steps[0]["retested"] >= 1

        # A real source-test record was appended (not tool_test)
        records = load_research_log(ws_root)
        retest_records = [
            r for r in records
            if r.get("approach") == "serper_api" and r.get("tested") is True
            and r.get("type") != "tool_test"
        ]
        assert len(retest_records) >= 1
        assert retest_records[-1]["works"] is True

    def test_hitl_task_board_updated(
        self, fake_engine, fake_workspace, fake_vc, fake_tree, batch_results,
    ):
        ws_root = fake_workspace.root
        init_evolution_workspace(ws_root)

        fake_engine.config.extra["structured_evolution"]["hitl_enabled"] = True
        fake_engine.config.extra["human_interface"] = "stdin"

        mock_hi = MagicMock()
        # First call = credential check (none pending), second = task board
        mock_hi.handle.return_value = "Also build a GitHub trending tool"

        def mock_run_llm(prompt, ws_root, system_prompt=None, **kw):
            return {"content": "## Failure Patterns\n"}

        fake_engine._run_llm = MagicMock(side_effect=mock_run_llm)

        with patch(
            "agent_evolve.algorithms.navigation.templates.structured_evolution.create_interface",
            return_value=mock_hi,
        ):
            template = Template(fake_engine)
            result = template.execute(
                fake_vc, fake_workspace, batch_results,
                fake_tree, evo_number=1, routing_log_path=None,
            )

        # Task board was updated with human request
        board = load_task_board(ws_root)
        assert "GitHub trending" in board

        # hitl_task_board step in trajectory
        hitl_board = [t for t in result["trajectory"] if t["step"] == "hitl_task_board"]
        assert len(hitl_board) == 1
        assert hitl_board[0]["updated"] is True


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
