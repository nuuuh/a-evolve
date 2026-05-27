"""Tests for the partial-trajectory preservation pipeline.

Covers:
  1. ``install_partial_writer`` writes after each tool call
  2. ``read_partial_trajectory`` returns None when absent
  3. Harness helper ``_enrich_from_partial`` merges partial into the
     synthetic cancelled record
  4. ``build_evolution_prompt`` surfaces ``status: cut_off`` text
  5. ``Observer.collect(trajectory_only=True)`` still strips ground-truth
     fields even with the new cut-off metadata
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from agent_evolve.agents._partial_trajectory import (
    clear_partial_trajectory,
    install_partial_writer,
    read_partial_trajectory,
)


# ── Shared helper tests ──────────────────────────────────────────────


class _FakeAgent:
    """Minimal Strands-agent stand-in that mimics the hooks API."""

    def __init__(self):
        self._cb = None
        self.messages = []
        self.hooks = SimpleNamespace(
            add_callback=lambda _evt_cls, cb: setattr(self, "_cb", cb)
        )

    def fire(self):
        """Simulate one tool-call hook firing."""
        if self._cb is None:
            return
        event = SimpleNamespace(
            agent=self,
            tool_use={"name": "bash"},
            result={"status": "success"},
            exception=None,
        )
        self._cb(event)


def test_partial_writer_writes_after_each_tool_call(tmp_path):
    agent = _FakeAgent()
    turn_counter = [0]
    t0 = time.time()

    path = install_partial_writer(
        agent,
        task_id="task_x",
        out_dir=tmp_path,
        turn_counter=turn_counter,
        start_time=t0,
    )

    # Fire three tool-call hooks with increasing turn counts.
    turn_counter[0] = 1
    agent.messages.append({"role": "assistant", "content": "turn 1"})
    agent.fire()
    assert path.exists()
    snap1 = json.loads(path.read_text())
    assert snap1["turns"] == 1
    assert snap1["status"] == "in_progress"
    assert len(snap1["conversation"]) == 1

    turn_counter[0] = 2
    agent.messages.append({"role": "user", "content": "tool result"})
    agent.fire()
    snap2 = json.loads(path.read_text())
    assert snap2["turns"] == 2
    assert len(snap2["conversation"]) == 2

    turn_counter[0] = 3
    agent.fire()
    snap3 = json.loads(path.read_text())
    assert snap3["turns"] == 3


def test_read_partial_returns_none_if_missing(tmp_path):
    assert read_partial_trajectory(tmp_path, "never-ran") is None


def test_clear_partial_trajectory_removes_file(tmp_path):
    path = tmp_path / "partial_foo.json"
    path.write_text("{}")
    clear_partial_trajectory(tmp_path, "foo")
    assert not path.exists()
    # Idempotent
    clear_partial_trajectory(tmp_path, "foo")


# ── Harness enrichment ───────────────────────────────────────────────


def test_enrich_from_partial_merges_turns_and_conversation(tmp_path):
    """The harness enrichment helper should pull real turn count + conv
    from the solver's partial snapshot when the Future was cancelled."""
    from solve_all_with_evolution import _enrich_from_partial

    sid = "task_y"
    (tmp_path / f"partial_{sid}.json").write_text(json.dumps({
        "instance_id": sid,
        "turns": 7,
        "elapsed": 83.4,
        "status": "in_progress",
        "conversation": [{"role": "user", "content": "..."}] * 14,
    }))

    r = {
        "instance_id": sid, "success": False, "score": 0.0,
        "detail": "Hung past batch deadline",
        "elapsed": 300, "error": "hung",
    }
    _enrich_from_partial(r, tmp_path, sid, cut_off_reason="batch_deadline")

    assert r["status"] == "cut_off"
    assert r["cut_off_reason"] == "batch_deadline"
    assert r["turns"] == 7
    assert len(r["conversation"]) == 14
    assert r["partial_elapsed"] == pytest.approx(83.4, abs=0.1)
    assert "Cut off mid-run" in r["detail"]
    assert "7 turn" in r["detail"]


def test_enrich_from_partial_no_snapshot_leaves_turns_unset(tmp_path):
    """When there's no partial (genuine 'never started' case), the
    cancelled record still gets status/cut_off_reason tags but no
    fabricated turns/conversation."""
    from solve_all_with_evolution import _enrich_from_partial

    r = {
        "instance_id": "task_z", "success": False, "score": 0.0,
        "detail": "Timed out (>300s)",
        "elapsed": 300, "error": "timeout",
    }
    _enrich_from_partial(r, tmp_path, "task_z", cut_off_reason="per_task_timeout")

    assert r["status"] == "cut_off"
    assert r["cut_off_reason"] == "per_task_timeout"
    assert "turns" not in r
    assert "conversation" not in r


# ── Evolver prompt flag ──────────────────────────────────────────────


def test_summarise_tool_latency_groups_by_tool():
    from agent_evolve.agents._partial_trajectory import summarise_tool_latency

    timings = [
        {"tool": "web_search", "duration_s": 12.0},
        {"tool": "web_search", "duration_s": 24.0},
        {"tool": "bash", "duration_s": 0.1},
        {"tool": "web_search", "duration_s": 30.0},
        {"tool": "bash", "duration_s": 0.2},
    ]
    s = summarise_tool_latency(timings)
    # Most-costly tool (web_search) appears first.
    assert s.startswith("web_search: ")
    assert "3× mean 22.0s max 30s" in s
    assert "bash: 2× mean 0.2s max 0s" in s


def test_summarise_tool_latency_empty():
    from agent_evolve.agents._partial_trajectory import summarise_tool_latency
    assert summarise_tool_latency(None) == ""
    assert summarise_tool_latency([]) == ""
    assert summarise_tool_latency([{"tool": "x"}]) == ""  # no duration_s


def test_evolver_prompt_surfaces_tool_latency(tmp_path):
    from agent_evolve.algorithms.aevolve.prompts import build_evolution_prompt
    from agent_evolve.contract.workspace import AgentWorkspace

    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    (ws_dir / "prompts").mkdir()
    (ws_dir / "prompts" / "system.md").write_text("x")
    (ws_dir / "skills").mkdir()
    (ws_dir / "skills" / "_drafts").mkdir()
    (ws_dir / "tools").mkdir()
    (ws_dir / "tools" / "registry.yaml").write_text("tools: []")
    (ws_dir / "memory").mkdir()
    ws = AgentWorkspace(ws_dir)

    logs = [{
        "task_id": "beta",
        "task_input": "beta input",
        "batch_num": 1,
        "conversation": [{"role": "assistant"}] * 5,
        "steps": [{
            "tool_timings": [
                {"tool": "web_search", "duration_s": 22.0},
                {"tool": "web_search", "duration_s": 25.0},
                {"tool": "bash", "duration_s": 0.1},
            ],
        }],
    }]
    prompt = build_evolution_prompt(ws, logs=logs, drafts=[], evo_number=1)
    assert "tool_latency" in prompt
    assert "web_search" in prompt


def test_evolver_prompt_flags_cut_off_tasks(tmp_path):
    """The evolver prompt should surface status:cut_off for cancelled
    tasks so the planner doesn't mistake them for 'failed to start'."""
    from agent_evolve.algorithms.aevolve.prompts import build_evolution_prompt
    from agent_evolve.contract.workspace import AgentWorkspace

    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    (ws_dir / "prompts").mkdir()
    (ws_dir / "prompts" / "system.md").write_text("x")
    (ws_dir / "skills").mkdir()
    (ws_dir / "skills" / "_drafts").mkdir()
    (ws_dir / "tools").mkdir()
    (ws_dir / "tools" / "registry.yaml").write_text("tools: []")
    (ws_dir / "memory").mkdir()

    ws = AgentWorkspace(ws_dir)

    logs = [
        {
            "task_id": "alpha",
            "task_input": "alpha input",
            "batch_num": 1,
            "conversation": [{"role": "assistant"}] * 12,
            "steps": [{
                "status": "cut_off",
                "cut_off_reason": "batch_deadline",
                "partial_elapsed": 187.3,
            }],
        },
    ]

    prompt = build_evolution_prompt(
        ws,
        logs=logs,
        drafts=[],
        evo_number=1,
    )
    assert "cut_off" in prompt
    assert "batch_deadline" in prompt


# ── Privacy: trajectory_only still strips ground truth ──────────────


def test_trajectory_only_mode_strips_score_fields(tmp_path):
    """Observer.collect with trajectory_only=True must never leak
    success/score/feedback_detail/feedback, even when the new cut-off
    metadata is present on the observation."""
    from agent_evolve.engine.observer import Observer
    from agent_evolve.types import Feedback, Observation, Task, Trajectory

    evo_dir = tmp_path / "evolution"
    obs = Observer(evo_dir, trajectory_only=True)

    ok = Observation(
        task=Task(id="ok_task", input="x"),
        trajectory=Trajectory(
            task_id="ok_task", output="done",
            steps=[{"tool_call_count": 3}],
            conversation=[{"role": "assistant"}],
        ),
        feedback=Feedback(success=True, score=1.0, detail="ok",
                          raw={"success": True, "score": 1.0}),
    )
    cut = Observation(
        task=Task(id="cut_task", input="y"),
        trajectory=Trajectory(
            task_id="cut_task", output="",
            steps=[{
                "tool_call_count": 7,
                "status": "cut_off",
                "cut_off_reason": "batch_deadline",
                "partial_elapsed": 123.0,
            }],
            conversation=[{"role": "assistant"}] * 14,
        ),
        feedback=Feedback(success=False, score=0.0, detail="cut",
                          raw={"status": "cut_off",
                               "cut_off_reason": "batch_deadline"}),
    )

    batch_file = obs.collect([ok, cut])
    lines = [json.loads(l) for l in batch_file.read_text().splitlines() if l.strip()]
    assert len(lines) == 2

    for rec in lines:
        # Privacy: no ground truth leaked
        assert "success" not in rec
        assert "score" not in rec
        assert "feedback_detail" not in rec
        assert "feedback" not in rec

    # But liveness signal is available inside the trajectory steps
    # (solver/harness path) — validate by looking at the cut task.
    cut_rec = next(r for r in lines if r["task_id"] == "cut_task")
    step0 = cut_rec["trajectory"]["steps"][0]
    assert step0.get("status") == "cut_off"
    assert step0.get("cut_off_reason") == "batch_deadline"
