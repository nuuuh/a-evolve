"""Tests for the temporal ground-truth reveal feature.

The observer now has two orthogonal flags:

  - ``trajectory_only``: legacy blanket strip (unchanged contract).
  - ``temporal_reveal``:  new per-task gate — include feedback only
    if the task's ``resolution_date`` / ``resolved_at`` is on or
    before the batch timestamp.

``temporal_reveal=True`` overrides ``trajectory_only`` per-task.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from agent_evolve.engine.observer import (
    Observer,
    _label_revealed,
    _parse_iso_tolerant,
    render_reveal_update,
)
from agent_evolve.types import Feedback, Observation, Task, Trajectory


def _make_obs(
    task_id: str,
    resolution_date: str | None = None,
    creation_date: str | None = None,
    success: bool = True,
    score: float = 1.0,
) -> Observation:
    meta: dict = {}
    if resolution_date is not None:
        meta["resolution_date"] = resolution_date
    if creation_date is not None:
        meta["creation_date"] = creation_date
    return Observation(
        task=Task(id=task_id, input="x", metadata=meta),
        trajectory=Trajectory(
            task_id=task_id, output="done",
            steps=[{"tool_call_count": 1}],
            conversation=[{"role": "assistant"}],
        ),
        feedback=Feedback(
            success=success, score=score, detail="ok",
            raw={"success": success, "score": score},
        ),
    )


def _parse(s: str) -> datetime:
    """ISO string → aware datetime."""
    return _parse_iso_tolerant(s)  # type: ignore[return-value]


# ── _label_revealed / _parse_iso_tolerant ─────────────────────────────


def test_parse_iso_tolerant_accepts_common_forms():
    assert _parse_iso_tolerant(None) is None
    assert _parse_iso_tolerant("") is None
    assert _parse_iso_tolerant("2026-01-10") == datetime(
        2026, 1, 10, tzinfo=timezone.utc)
    assert _parse_iso_tolerant("2026-01-10T12:00:00Z") == datetime(
        2026, 1, 10, 12, 0, tzinfo=timezone.utc)
    # already-a-datetime passes through (naive → UTC).
    naive = datetime(2026, 1, 10)
    out = _parse_iso_tolerant(naive)
    assert out == naive.replace(tzinfo=timezone.utc)


def test_reveal_when_resolved_before_batch_ts():
    obs = _make_obs("a", resolution_date="2026-01-10")
    assert _label_revealed(obs, _parse("2026-02-01")) is True


def test_hide_when_resolved_after_batch_ts():
    obs = _make_obs("b", resolution_date="2026-05-01")
    assert _label_revealed(obs, _parse("2026-02-01")) is False


def test_hide_when_no_resolution_date():
    obs = _make_obs("ctf", resolution_date=None)
    assert _label_revealed(obs, _parse("2026-02-01")) is False


def test_batch_ts_none_hides_all():
    obs = _make_obs("x", resolution_date="2020-01-01")  # long resolved
    assert _label_revealed(obs, None) is False


# ── Observer integration: the gate actually changes the JSONL ─────────


def test_observer_temporal_reveal_includes_only_resolved_tasks(tmp_path):
    evo_dir = tmp_path / "evolution"
    obs = Observer(evo_dir, trajectory_only=True, temporal_reveal=True)
    obs.set_batch_timestamp(_parse("2026-04-01"))

    revealed = _make_obs("past_task", resolution_date="2026-02-10")
    pending = _make_obs("future_task", resolution_date="2026-05-15")
    ctf = _make_obs("ctf_task", resolution_date=None)

    batch_file = obs.collect([revealed, pending, ctf])
    records = [json.loads(l) for l in batch_file.read_text().splitlines() if l]
    by_id = {r["task_id"]: r for r in records}

    # Revealed task carries success/score; others do not.
    assert "success" in by_id["past_task"]
    assert "score" in by_id["past_task"]
    assert by_id["past_task"]["success"] is True

    assert "success" not in by_id["future_task"]
    assert "feedback" not in by_id["future_task"]
    assert "success" not in by_id["ctf_task"]


def test_legacy_trajectory_only_unchanged_when_reveal_off(tmp_path):
    """With temporal_reveal=False, Observer behaves identically to today:
    trajectory_only strips all labels, no per-task gate applies."""
    evo_dir = tmp_path / "evolution"
    obs = Observer(evo_dir, trajectory_only=True, temporal_reveal=False)
    obs.set_batch_timestamp(_parse("2026-04-01"))  # should be ignored

    revealed_by_temporal = _make_obs("past_task", resolution_date="2020-01-01")
    rec = json.loads(obs.collect([revealed_by_temporal]).read_text())
    assert "success" not in rec
    assert "feedback" not in rec


def test_legacy_full_info_unchanged_when_reveal_off(tmp_path):
    """With both flags off, labels are always included (legacy default)."""
    evo_dir = tmp_path / "evolution"
    obs = Observer(evo_dir, trajectory_only=False, temporal_reveal=False)
    future = _make_obs("future", resolution_date="2099-01-01")
    rec = json.loads(obs.collect([future]).read_text())
    # Legacy mode: labels always included even for unresolved tasks.
    assert rec["success"] is True


def test_temporal_reveal_overrides_trajectory_only_per_task(tmp_path):
    """When both flags are on, the per-task gate wins: resolved tasks
    get labels even though trajectory_only is True."""
    evo_dir = tmp_path / "evolution"
    obs = Observer(evo_dir, trajectory_only=True, temporal_reveal=True)
    obs.set_batch_timestamp(_parse("2026-04-01"))
    past = _make_obs("past", resolution_date="2026-01-15")
    rec = json.loads(obs.collect([past]).read_text())
    assert rec["success"] is True


# ── Cumulative reveal renderer ────────────────────────────────────────


def test_render_reveal_update_with_both_buckets():
    block = render_reveal_update(
        cycle=3,
        watermark=_parse("2026-02-15"),
        in_batch_revealed=[
            {"task_id": "t_cur",
             "creation_date": _parse("2026-02-08"),
             "resolution_date": _parse("2026-02-10")},
        ],
        newly_revealed_past=[
            {"task_id": "t_past_a",
             "creation_date": _parse("2026-02-06"),
             "resolution_date": _parse("2026-02-12")},
            {"task_id": "t_past_b",
             "creation_date": _parse("2026-02-09"),
             "resolution_date": _parse("2026-02-13")},
        ],
        total_revealed=22,
        total_past=30,
    )
    assert "cycle 3" in block
    assert "2026-02-15" in block
    assert "In-batch reveals (1)" in block
    assert "t_cur" in block
    assert "Newly revealed past tasks (2)" in block
    assert "t_past_a" in block and "t_past_b" in block
    assert "22 / 30 past tasks" in block
    assert "8 still pending" in block


def test_render_reveal_update_no_reveals_either_bucket():
    block = render_reveal_update(
        cycle=4, watermark=_parse("2026-02-20"),
        in_batch_revealed=[], newly_revealed_past=[],
        total_revealed=22, total_past=30,
    )
    assert "In-batch reveals (0)" in block
    assert "Newly revealed past tasks (0)" in block
    assert "22 / 30 past tasks" in block


# ── Cumulative reveal across cycles ────────────────────────────────────


def test_cumulative_reveal_surfaces_task_in_later_cycle(tmp_path):
    """A task resolved AFTER its batch watermark should not appear in
    the batch JSONL, but should appear via the supplement once a later
    cycle's watermark crosses its resolution date."""
    evo_dir = tmp_path / "evolution"
    obs = Observer(evo_dir, temporal_reveal=True)

    # Batch 1: one task creates Jan 06, resolves Jan 20.  Watermark = Jan 10.
    b1_task = _make_obs("t_late", resolution_date="2026-01-20",
                        creation_date="2026-01-06")
    obs.set_batch_timestamp(_parse("2026-01-10"))
    b1_file = obs.collect([b1_task])
    recs1 = [json.loads(l) for l in b1_file.read_text().splitlines() if l]
    # Task is pending at batch 1 write-time.
    assert "success" not in recs1[0]

    # Before batch 2, evolution cycle 1 runs with watermark Jan 25
    # (upcoming batch's max creation date). t_late resolved Jan 20 ≤
    # Jan 25 → should be newly revealed.
    newly = obs.update_reveal_state(cycle=1, watermark=_parse("2026-01-25"))
    assert len(newly) == 1
    assert newly[0]["task_id"] == "t_late"

    # Supplement file must now contain a line for t_late.
    sup_path = evo_dir / "observations" / "revealed_supplement.jsonl"
    assert sup_path.exists()
    sup_entries = [json.loads(l) for l in sup_path.read_text().splitlines() if l]
    assert any(e["task_id"] == "t_late" for e in sup_entries)

    # get_recent_logs should overlay the supplement onto the batch record.
    recs = obs.get_recent_logs(n_batches=1)
    t_late = next(r for r in recs if r["task_id"] == "t_late")
    assert t_late.get("success") is True


def test_cumulative_reveal_idempotent(tmp_path):
    """Calling update_reveal_state twice with the same watermark should
    not double-append to the supplement."""
    evo_dir = tmp_path / "evolution"
    obs = Observer(evo_dir, temporal_reveal=True)

    task = _make_obs("t", resolution_date="2026-01-10",
                     creation_date="2026-01-05")
    obs.set_batch_timestamp(_parse("2026-01-06"))  # pending at batch 1
    obs.collect([task])

    newly_first = obs.update_reveal_state(cycle=1, watermark=_parse("2026-01-12"))
    assert len(newly_first) == 1
    newly_second = obs.update_reveal_state(cycle=2, watermark=_parse("2026-01-20"))
    assert len(newly_second) == 0  # already revealed

    sup_path = evo_dir / "observations" / "revealed_supplement.jsonl"
    sup_entries = [json.loads(l) for l in sup_path.read_text().splitlines() if l]
    assert len(sup_entries) == 1


def test_ctf_task_with_no_resolution_never_revealed(tmp_path):
    """Tasks without a resolution_date (e.g. CTF) stay pending forever
    even when the watermark advances."""
    evo_dir = tmp_path / "evolution"
    obs = Observer(evo_dir, temporal_reveal=True)

    task = _make_obs("ctf", resolution_date=None)
    obs.set_batch_timestamp(None)
    obs.collect([task])

    newly = obs.update_reveal_state(cycle=1, watermark=_parse("2099-01-01"))
    assert newly == []


# ── Reveal-gate API used by navigation templates ─────────────────────


def test_filter_batch_strips_labels_for_unrevealed_tasks(tmp_path):
    """Observer.filter_batch_for_evolver must strip success/score/feedback
    from tasks that have not yet been revealed, while leaving behaviour
    signals (turns, status, tool_timings) intact."""
    obs = Observer(tmp_path / "evo1", trajectory_only=False,
                   temporal_reveal=True)
    obs._revealed_ids.add("resolved")

    batch = [
        {"instance_id": "resolved", "success": True, "score": 1.0,
         "detail": "ok", "turns": 5, "status": "ok"},
        {"instance_id": "pending", "success": False, "score": 0.0,
         "detail": "no", "turns": 7, "status": "cut_off"},
    ]
    out = obs.filter_batch_for_evolver(batch)

    assert out[0]["success"] is True
    assert out[0]["score"] == 1.0
    assert out[0]["turns"] == 5

    assert "success" not in out[1]
    assert "score" not in out[1]
    assert "detail" not in out[1]
    # Behaviour-level signals survive.
    assert out[1]["turns"] == 7
    assert out[1]["status"] == "cut_off"
    # Original batch untouched (shallow-copy semantics).
    assert batch[1]["success"] is False


def test_filter_batch_trajectory_only_strips_everything(tmp_path):
    """In trajectory_only mode nothing is ever revealed."""
    obs = Observer(tmp_path / "evo2", trajectory_only=True,
                   temporal_reveal=False)
    out = obs.filter_batch_for_evolver([
        {"instance_id": "a", "success": True, "score": 1.0, "detail": "ok"},
    ])
    assert "success" not in out[0]
    assert "score" not in out[0]


def test_filter_batch_legacy_mode_reveals_everything(tmp_path):
    """When both flags are off, filter is an identity on label fields."""
    obs = Observer(tmp_path / "evo3", trajectory_only=False,
                   temporal_reveal=False)
    out = obs.filter_batch_for_evolver([
        {"instance_id": "a", "success": True, "score": 1.0, "detail": "ok"},
    ])
    assert out[0]["success"] is True
    assert out[0]["score"] == 1.0


def test_inline_branching_section_counts_pending_separately():
    """The batch summary line in inline.build_branching_section must
    distinguish pending-reveal tasks from failed ones."""
    from agent_evolve.algorithms.navigation.templates.inline import (
        build_branching_section,
    )

    class _Tree: branches = []

    # Mixed batch: 1 revealed-pass, 1 revealed-fail, 1 pending.
    out = build_branching_section(_Tree(), [
        {"instance_id": "a", "success": True},
        {"instance_id": "b", "success": False},
        {"instance_id": "c"},  # pending — no success field
    ])
    assert "1 passed, 1 failed, 1 pending reveal" in out

    # All pending → "labels withheld" phrasing.
    out_all_pending = build_branching_section(_Tree(), [
        {"instance_id": "a"}, {"instance_id": "b"},
    ])
    assert "labels withheld" in out_all_pending


def test_orchestrated_planner_prompt_counts_pending_separately():
    """build_planner_prompt surfaces 'pending reveal' in its header and
    omits success fields for unrevealed tasks."""
    from agent_evolve.algorithms.navigation.templates.orchestrated import (
        build_planner_prompt,
    )

    out = build_planner_prompt(
        [{"instance_id": "a", "turns": 5, "success": True},
         {"instance_id": "b", "turns": 3}],
        evolution_history=[], branches=["main"], navigation_enabled=False,
    )
    assert "1 passed" in out
    assert "pending reveal" in out

    out_all_pending = build_planner_prompt(
        [{"instance_id": "a", "turns": 5},
         {"instance_id": "b", "turns": 3}],
        evolution_history=[], branches=["main"], navigation_enabled=False,
    )
    assert "labels withheld" in out_all_pending


def test_navigation_engine_applies_reveal_gate(tmp_path):
    """NavigationEngine.evolve_with_navigation must pass a gated batch
    to the template when ``engine.observer`` is set."""
    from agent_evolve.algorithms.navigation.engine import NavigationEngine
    from agent_evolve.config import EvolveConfig

    # Substitute a recording template so we can inspect what it sees.
    captured = {}

    class _RecordingTemplate:
        name = "recording"
        def execute(self, vc, ws, batch, tree, evo_number, routing_log_path):
            captured["batch"] = batch
            return {"evo_number": evo_number, "mutated": False,
                    "plan": {}, "branches": [], "trajectory": []}

    config = EvolveConfig(trajectory_only=False, temporal_reveal=True)
    engine = NavigationEngine(config, mode="inline",
                              template=_RecordingTemplate())
    obs = Observer(tmp_path / "evo", trajectory_only=False,
                   temporal_reveal=True)
    obs._revealed_ids.add("resolved")
    engine.observer = obs

    # Stand in for a workspace path — VersionControl.init() needs a git
    # repo, so build one.
    import subprocess
    ws_root = tmp_path / "ws"
    ws_root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=ws_root, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"],
                   cwd=ws_root, check=True)
    subprocess.run(["git", "config", "user.name", "t"],
                   cwd=ws_root, check=True)
    (ws_root / "README").write_text("seed")
    subprocess.run(["git", "add", "-A"], cwd=ws_root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"],
                   cwd=ws_root, check=True)

    class _Ws:
        root = ws_root
    class _Tree:
        branches = []
        def branch_names(self):
            return ["main"]
        def to_dict(self):
            return {}
    batch = [
        {"instance_id": "resolved", "success": True, "score": 1.0},
        {"instance_id": "pending", "success": False, "score": 0.0},
    ]
    engine.evolve_with_navigation(_Ws(), batch, _Tree(), evo_number=1)

    seen = captured["batch"]
    assert seen[0]["success"] is True           # revealed
    assert "success" not in seen[1]             # pending, gated
