"""Integration tests for per-branch README.md in the navigation engine.

Tests the README code paths deterministically using real git repos
(no LLM calls): branch leaf reading, post-hoc description extraction,
and prompt rendering.
"""
from __future__ import annotations

import pytest

from agent_evolve.engine.versioning import VersionControl
from agent_evolve.types import BranchInfo, StrategyTree
from agent_evolve.algorithms.navigation.engine import NavigationEngine
from agent_evolve.algorithms.navigation.prompts import build_navigate_prompt


def _setup_workspace(tmp_path):
    """Create a minimal git workspace on main."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "prompts").mkdir()
    (ws / "prompts" / "system.md").write_text("main prompt")
    (ws / "skills").mkdir()
    (ws / "tools").mkdir()
    vc = VersionControl(ws)
    vc.init()
    return ws, vc


def _make_engine():
    """Create a NavigationEngine without calling __init__ (no LLM needed)."""
    return NavigationEngine.__new__(NavigationEngine)


# ── Test A: _read_branch_leaves includes README ──────────────────────


def test_read_branch_leaves_includes_readme(tmp_path):
    ws, vc = _setup_workspace(tmp_path)

    # Create branch with README and custom prompt
    vc.create_branch("branch/sports-specialist")
    (ws / "prompts" / "system.md").write_text("Sports specialist prompt")
    (ws / "README.md").write_text(
        "# Branch: branch/sports-specialist\n\n"
        "Specializes in sports game predictions.\n\n"
        "## Strategy\n- Head-to-head analysis\n"
    )
    vc.commit("branch: sports specialist")
    vc.checkout_branch("main")

    tree = StrategyTree(branches=[
        BranchInfo(name="branch/sports-specialist", description="sports"),
    ])
    engine = _make_engine()
    summaries = engine._read_branch_leaves(
        tree, ws, viable=["branch/sports-specialist"],
    )

    branch = next(s for s in summaries if s["name"] == "branch/sports-specialist")
    assert "sports game predictions" in branch["readme"]
    assert "Sports specialist prompt" in branch["system_prompt"]

    main = next(s for s in summaries if s["name"] == "main")
    assert main["readme"] == ""


# ── Test B: Post-hoc README description extraction ───────────────────


def test_readme_description_extraction(tmp_path):
    ws, vc = _setup_workspace(tmp_path)

    # Branch with a proper README
    vc.create_branch("branch/test-regime")
    (ws / "README.md").write_text(
        "# Branch: branch/test-regime\n\n"
        "Handles tasks requiring specialized analysis.\n\n"
        "## Strategy\n- Technique A\n"
    )
    vc.commit("branch: test regime")
    vc.checkout_branch("main")

    # Replicate _evolve_inline extraction logic (engine.py:532-550)
    readme = vc.show_file_at("branch/test-regime", "README.md")
    description = ""
    for line in readme.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            description = stripped[:200]
            break
    assert description == "Handles tasks requiring specialized analysis."


def test_readme_description_fallback_to_commit_msg(tmp_path):
    ws, vc = _setup_workspace(tmp_path)

    # Branch without README
    vc.create_branch("branch/no-readme")
    (ws / "dummy.txt").write_text("x")
    vc.commit("branch/no-readme: fallback test")
    vc.checkout_branch("main")

    description = ""
    try:
        vc.show_file_at("branch/no-readme", "README.md")
    except Exception:
        pass
    if not description:
        try:
            log_msg = vc._git("log", "--format=%s", "main..branch/no-readme", "-1")
            description = log_msg.strip()
        except Exception:
            pass
    assert "fallback" in description


def test_readme_description_only_headings(tmp_path):
    ws, vc = _setup_workspace(tmp_path)

    # Branch with README containing only headings
    vc.create_branch("branch/headings-only")
    (ws / "README.md").write_text("# Title\n## Subtitle\n### Section\n")
    vc.commit("branch: headings only")
    vc.checkout_branch("main")

    readme = vc.show_file_at("branch/headings-only", "README.md")
    description = ""
    for line in readme.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            description = stripped[:200]
            break
    # All lines are headings → description stays empty, falls back to commit msg
    assert description == ""


# ── Test C: build_navigate_prompt renders README ─────────────────────


def test_navigate_prompt_renders_readme():
    branches = [
        {"name": "main", "description": "root", "system_prompt": "main prompt",
         "skills": [], "tools_registry": "", "readme": ""},
        {"name": "branch/sports", "description": "sports",
         "system_prompt": "sports prompt", "skills": ["predict_match"],
         "tools_registry": "", "readme": "# Sports\n\nSports specialist branch."},
    ]
    prompt = build_navigate_prompt("Predict the match outcome", branches)

    assert "**README:**" in prompt
    assert "Sports specialist branch." in prompt
    # Main has no README → only one README block
    assert prompt.count("**README:**") == 1


# ── Test D: Graceful handling of missing README ──────────────────────


def test_read_branch_leaves_no_readme_graceful(tmp_path):
    ws, vc = _setup_workspace(tmp_path)

    vc.create_branch("branch/bare")
    (ws / "dummy.txt").write_text("x")
    vc.commit("bare branch")
    vc.checkout_branch("main")

    tree = StrategyTree(branches=[
        BranchInfo(name="branch/bare", description="bare"),
    ])
    engine = _make_engine()
    summaries = engine._read_branch_leaves(tree, ws, viable=["branch/bare"])

    branch = next(s for s in summaries if s["name"] == "branch/bare")
    assert branch["readme"] == ""
