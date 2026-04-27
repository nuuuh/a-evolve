"""Tests for _evolution_workspace helpers."""

import json
import pytest
from pathlib import Path

from agent_evolve.algorithms.navigation.templates._evolution_workspace import (
    init_evolution_workspace,
    load_task_board,
    update_task_board,
    validate_task_board,
    load_research_log,
    append_research,
    validate_research_record,
    get_verified_approaches,
    get_failed_approaches,
    load_architecture,
    update_architecture,
    append_insight,
    load_insights,
    WORKSPACE_DIR,
)


@pytest.fixture
def ws(tmp_path):
    init_evolution_workspace(tmp_path)
    return tmp_path


def _make_record(**overrides):
    """Full 15-field research record."""
    base = {
        "cycle": 1,
        "regime": "finance",
        "approach": "stooq",
        "endpoint": "https://stooq.com/q/d/l/",
        "tested": True,
        "works": True,
        "latency_ms": 300,
        "coverage": ["us_stocks", "us_indices"],
        "does_not_cover": ["cn_a_shares"],
        "complementary_to": ["sina_finance"],
        "sample_output": "Date,Open,High,Low,Close",
        "credential_needed": False,
        "credential_env": "",
        "error": "",
        "notes": "CSV OHLC data",
    }
    base.update(overrides)
    return base


def _make_tool_test(**overrides):
    """tool_test record."""
    base = {
        "cycle": 1,
        "regime": "finance",
        "approach": "finance_pipeline",
        "tested": True,
        "works": True,
        "type": "tool_test",
    }
    base.update(overrides)
    return base


class TestInit:
    def test_creates_directory_and_files(self, tmp_path):
        init_evolution_workspace(tmp_path)
        ws_dir = tmp_path / WORKSPACE_DIR
        assert ws_dir.is_dir()
        assert (ws_dir / "task_board.md").exists()
        assert (ws_dir / "architecture.md").exists()
        assert (ws_dir / "research_log.jsonl").exists()
        assert (ws_dir / "insights.jsonl").exists()

    def test_idempotent(self, ws):
        update_task_board(ws, "custom content")
        init_evolution_workspace(ws)
        assert load_task_board(ws) == "custom content"


class TestTaskBoard:
    def test_load_default(self, ws):
        content = load_task_board(ws)
        assert "Failure Patterns" in content

    def test_update_and_load(self, ws):
        update_task_board(ws, "## New Board\n- item 1\n")
        assert load_task_board(ws) == "## New Board\n- item 1\n"

    def test_load_missing_returns_empty(self, tmp_path):
        assert load_task_board(tmp_path) == ""


class TestResearchLog:
    def test_append_and_load(self, ws):
        r = _make_record()
        append_research(ws, r)
        records = load_research_log(ws)
        assert len(records) == 1
        assert records[0]["approach"] == "stooq"

    def test_append_multiple(self, ws):
        append_research(ws, _make_record(approach="a"))
        append_research(ws, _make_record(approach="b"))
        assert len(load_research_log(ws)) == 2

    def test_append_rejects_invalid(self, ws):
        with pytest.raises(ValueError, match="missing required"):
            append_research(ws, {"cycle": 1})

    def test_load_empty(self, ws):
        assert load_research_log(ws) == []

    def test_load_skips_malformed_lines(self, ws):
        p = ws / WORKSPACE_DIR / "research_log.jsonl"
        p.write_text('{"cycle":1,"regime":"x","approach":"y","tested":true,"works":true}\nnot json\n')
        records = load_research_log(ws)
        assert len(records) == 1


class TestValidation:
    def test_valid_full_record(self):
        assert validate_research_record(_make_record()) is True

    def test_missing_all_fields(self):
        assert validate_research_record({"cycle": 1, "regime": "x"}) is False

    def test_minimal_record_rejected(self):
        minimal = {"cycle": 1, "regime": "x", "approach": "y", "tested": True, "works": True}
        assert validate_research_record(minimal) is False

    def test_extra_fields_ok(self):
        r = _make_record(latency_ms=200, notes="fast")
        assert validate_research_record(r) is True

    def test_tool_test_record_valid(self):
        assert validate_research_record(_make_tool_test()) is True

    def test_tool_test_missing_type_rejected_as_source(self):
        r = _make_tool_test()
        del r["type"]
        # Without type, it's treated as a source record — missing full fields
        assert validate_research_record(r) is False

    def test_tool_test_with_extra(self):
        r = _make_tool_test(evidence="PASS on 3 queries", files=["finance_pipeline.py"])
        assert validate_research_record(r) is True


class TestFiltering:
    def test_get_verified_full_records(self, ws):
        append_research(ws, _make_record(works=True, approach="a"))
        append_research(ws, _make_record(works=False, approach="b"))
        append_research(ws, _make_record(works=True, approach="c"))
        verified = get_verified_approaches(ws)
        assert len(verified) == 2
        assert {r["approach"] for r in verified} == {"a", "c"}

    def test_get_verified_excludes_minimal(self, ws):
        """Minimal records (no coverage/endpoint) are not build inputs."""
        minimal = {"cycle": 1, "regime": "x", "approach": "y",
                    "tested": True, "works": True}
        # Write directly to bypass full validation
        import json
        p = ws / WORKSPACE_DIR / "research_log.jsonl"
        with p.open("a") as f:
            f.write(json.dumps(minimal) + "\n")
        assert get_verified_approaches(ws) == []

    def test_get_verified_excludes_tool_test(self, ws):
        append_research(ws, _make_tool_test(works=True))
        assert get_verified_approaches(ws) == []

    def test_get_failed(self, ws):
        append_research(ws, _make_record(works=True, approach="a"))
        append_research(ws, _make_record(works=False, approach="b"))
        failed = get_failed_approaches(ws)
        assert len(failed) == 1
        assert failed[0]["approach"] == "b"

    def test_blocked_excluded_from_both(self, ws):
        append_research(ws, _make_record(works="blocked", approach="x"))
        assert get_verified_approaches(ws) == []
        assert get_failed_approaches(ws) == []


class TestArchitecture:
    def test_load_default(self, ws):
        assert "Architecture" in load_architecture(ws)

    def test_update_and_load(self, ws):
        update_architecture(ws, "# New Arch\npipeline: finance\n")
        assert "pipeline: finance" in load_architecture(ws)

    def test_load_missing_returns_empty(self, tmp_path):
        assert load_architecture(tmp_path) == ""


class TestInsights:
    def test_append_and_load(self, ws):
        append_insight(ws, {"cycle": 1, "lesson": "DuckDuckGo times out"})
        insights = load_insights(ws)
        assert len(insights) == 1
        assert insights[0]["lesson"] == "DuckDuckGo times out"

    def test_load_empty(self, ws):
        assert load_insights(ws) == []
