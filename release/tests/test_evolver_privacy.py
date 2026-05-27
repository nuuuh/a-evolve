"""Privacy tests: the evolver prompt reflects the upstream reveal gate.

The prompt builder is a passthrough: it includes ground-truth labels
(success/score) when they survive the upstream gate (observer or
filter_batch_for_evolver), and omits them when they don't.  The
sandbox mount (evolution/trajectories/) is always ground-truth-free.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_evolve.algorithms.aevolve.prompts import build_evolution_prompt
from agent_evolve.contract.workspace import AgentWorkspace
from agent_evolve.engine.observer import Observer
from agent_evolve.types import Feedback, Observation, Task, Trajectory


def _mk_workspace(tmp_path: Path) -> AgentWorkspace:
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "system.md").write_text("# solver\n")
    (tmp_path / "skills").mkdir()
    (tmp_path / "memory").mkdir()
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "registry.yaml").write_text("tools: []\n")
    return AgentWorkspace(tmp_path)


def _mk_log(
    *,
    task_id: str = "task-42",
    batch: int = 7,
    success: bool = True,
    score: float = 1.0,
    detail: str = "judge says: passed",
) -> dict:
    return {
        "task_id": task_id,
        "batch": batch,
        "success": success,
        "score": score,
        "feedback_detail": detail,
        "feedback": {
            "success": success,
            "score": score,
            "detail": detail,
            "claims": [{"claim": "answer correct", "outcome": "fulfilled", "score": 1.0}],
            "raw": {"judge_score": 1.0, "sentinel_LEAK_ME": True},
        },
        "task_input": "What is 2+2?",
        "conversation": [
            {"role": "assistant", "content": "4"},
        ],
    }


def test_prompt_surfaces_revealed_labels(tmp_path):
    """When logs carry success/score (upstream gate allowed them),
    those fields appear in the prompt so the evolver can learn."""
    ws = _mk_workspace(tmp_path)
    logs = [_mk_log()]  # has success=True, score=1.0
    prompt = build_evolution_prompt(ws, logs, drafts=[], evo_number=1)

    assert '"success": true' in prompt
    assert '"score": 1.0' in prompt
    assert "Ground-truth labels" in prompt
    # Raw feedback internals should NOT be inlined — only success/score.
    for leak in ('"feedback":', '"feedback_detail":', '"claims":', '"raw":'):
        assert leak not in prompt, (
            f"Prompt should not include raw feedback field {leak!r}"
        )


def test_prompt_omits_labels_when_upstream_strips_them(tmp_path):
    """When logs have no success/score (upstream gate stripped them),
    the prompt contains no ground-truth and says so."""
    ws = _mk_workspace(tmp_path)
    log = _mk_log()
    del log["success"]
    del log["score"]
    del log["feedback"]
    del log["feedback_detail"]
    prompt = build_evolution_prompt(ws, [log], drafts=[], evo_number=1)

    assert '"success":' not in prompt
    assert '"score":' not in prompt
    assert "No ground-truth labels available" in prompt


def test_prompt_includes_safe_index_fields(tmp_path):
    ws = _mk_workspace(tmp_path)
    logs = [_mk_log(task_id="abc/123", batch=3)]
    prompt = build_evolution_prompt(ws, logs, drafts=[], evo_number=1)

    assert "Trajectory Memory Index" in prompt
    assert '"task_id": "abc/123"' in prompt
    assert '"batch": 3' in prompt
    assert '"turns": 1' in prompt
    assert "/trajectories/batch_0003/trajectory_abc_123.json" in prompt
    assert "/trajectories/batch_0003/patch_abc_123.diff" in prompt


def test_prompt_stays_compact_under_heavy_conversation(tmp_path):
    ws = _mk_workspace(tmp_path)
    big_turn = {"role": "assistant", "content": "X" * 4096}
    heavy_conv = [big_turn] * 100  # ~400KB if inlined
    logs = [
        {
            "task_id": f"task-{i}",
            "batch": 1,
            "task_input": "heavy",
            "conversation": heavy_conv,
            "success": True,
            "score": 1.0,
            "feedback_detail": "x",
        }
        for i in range(20)
    ]
    prompt = build_evolution_prompt(ws, logs, drafts=[], evo_number=1)
    # With 20 tasks of 100 huge turns, the old inline mode would emit
    # >8MB. The new index mode must stay under 20KB.
    assert len(prompt) < 20_000, f"Index-mode prompt is too large: {len(prompt)} bytes"


def test_prompt_orders_by_batch_descending(tmp_path):
    ws = _mk_workspace(tmp_path)
    logs = [
        _mk_log(task_id="old", batch=1),
        _mk_log(task_id="new", batch=9),
        _mk_log(task_id="mid", batch=5),
    ]
    prompt = build_evolution_prompt(ws, logs, drafts=[], evo_number=1)
    # Assert 'new' appears before 'mid' appears before 'old' in the prompt body.
    p_new = prompt.index('"task_id": "new"')
    p_mid = prompt.index('"task_id": "mid"')
    p_old = prompt.index('"task_id": "old"')
    assert p_new < p_mid < p_old


def test_observer_separates_trajectories_from_observations(tmp_path):
    evolution_dir = tmp_path / "evolution"
    observer = Observer(evolution_dir)
    obs = [
        Observation(
            task=Task(id="t-1", input="q", metadata={}),
            trajectory=Trajectory(task_id="t-1", output="patchy", steps=[], conversation=[{"role": "assistant", "content": "a"}]),
            feedback=Feedback(success=True, score=1.0, detail="passed", raw={"judge_score": 1.0}),
        )
    ]
    observer.collect(obs)

    # Ground-truth JSONL in observations/
    observations = list((evolution_dir / "observations").glob("batch_*.jsonl"))
    assert len(observations) == 1, "Batch JSONL missing from observations/"
    content = observations[0].read_text()
    assert '"success": true' in content
    assert '"score": 1.0' in content

    # Safe per-task artifacts in trajectories/ (sibling tree)
    traj_dir = evolution_dir / "trajectories"
    assert traj_dir.exists()
    batch_dirs = list(traj_dir.glob("batch_*"))
    assert len(batch_dirs) == 1
    traj_files = list(batch_dirs[0].glob("trajectory_*.json"))
    patch_files = list(batch_dirs[0].glob("patch_*.diff"))
    assert len(traj_files) == 1
    assert len(patch_files) == 1
    # Trajectory file MUST NOT contain ground-truth signals.
    traj_content = traj_files[0].read_text()
    parsed = json.loads(traj_content)
    assert isinstance(parsed, list)
    for turn in parsed:
        assert "success" not in turn
        assert "score" not in turn
        assert "feedback" not in turn


def test_observer_trajectories_dir_contains_no_jsonl(tmp_path):
    """The mountable trajectories/ tree must never carry ground-truth JSONL."""
    evolution_dir = tmp_path / "evolution"
    observer = Observer(evolution_dir)
    observer.collect(
        [
            Observation(
                task=Task(id="t-1", input="q", metadata={}),
                trajectory=Trajectory(task_id="t-1", output="patch", steps=[], conversation=[]),
                feedback=Feedback(success=False, score=0.0, detail="no", raw={}),
            )
        ]
    )
    for f in (evolution_dir / "trajectories").rglob("*.jsonl"):
        pytest.fail(f"trajectories/ must not contain .jsonl files (found {f})")
