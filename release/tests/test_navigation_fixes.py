"""Tests for the two navigation fixes:

Fix #1: branch_confidence_threshold is enforced — low-confidence routing
        falls back to "main"; negative threshold disables branching.
Fix #3: navigator prompt + builder_branch.md require structured READMEs
        with a "When to route here" section so routing is reliable.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure the repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_evolve.algorithms.navigation.engine import NavigationEngine
from agent_evolve.algorithms.navigation.prompts import (
    NAVIGATE_SYSTEM_PROMPT,
    build_navigate_prompt,
)
from agent_evolve.types import StrategyTree, BranchInfo


def _fake_response(branch: str, confidence: float):
    """Build a fake Bedrock response object for navigate()."""
    resp = MagicMock()
    resp.content = json.dumps(
        {"branch": branch, "confidence": confidence, "reason": "test"}
    )
    return resp


def _make_engine(threshold: float = 0.7):
    """Create a NavigationEngine with a controllable confidence threshold."""
    cfg = MagicMock()
    cfg.branch_confidence_threshold = threshold
    cfg.extra = {}
    eng = NavigationEngine.__new__(NavigationEngine)
    eng.config = cfg
    eng.observer = None

    # Mock LLM so we control what the navigator returns.
    from agent_evolve.llm.bedrock import BedrockProvider
    llm = MagicMock(spec=BedrockProvider)
    eng._llm = llm
    return eng, llm


def _make_tree_with_branch(name: str = "branch/pwn"):
    tree = StrategyTree()
    tree.branches.append(BranchInfo(
        name=name, created_at_cycle=1, description="pwn-specialized",
    ))
    return tree


# ── Fix #1: confidence threshold ────────────────────────────────────


def test_high_confidence_routes_to_branch(tmp_path: Path):
    """Confidence >= threshold → route to the chosen branch."""
    eng, llm = _make_engine(threshold=0.7)
    tree = _make_tree_with_branch("branch/pwn")

    llm.converse_loop.return_value = _fake_response("branch/pwn", 0.85)

    # Mock _viable_branches and _read_branch_leaves to bypass git access
    with patch.object(NavigationEngine, "_viable_branches",
                       return_value=["branch/pwn"]), \
         patch.object(NavigationEngine, "_read_branch_leaves",
                       return_value=[
                           {"name": "main", "description": "general", "readme": ""},
                           {"name": "branch/pwn", "description": "pwn", "readme": "# branch/pwn"},
                       ]), \
         patch.object(NavigationEngine, "_resolve_branch_name",
                       side_effect=lambda raw, t, vc: raw):
        result = eng.navigate("Solve a pwn challenge", tree, workspace_root=tmp_path)
    assert result == "branch/pwn", f"expected routing to branch/pwn, got {result}"


def test_low_confidence_falls_back_to_main(tmp_path: Path):
    """Confidence < threshold → fall back to main."""
    eng, llm = _make_engine(threshold=0.7)
    tree = _make_tree_with_branch("branch/pwn")

    llm.converse_loop.return_value = _fake_response("branch/pwn", 0.4)

    with patch.object(NavigationEngine, "_viable_branches",
                       return_value=["branch/pwn"]), \
         patch.object(NavigationEngine, "_read_branch_leaves",
                       return_value=[
                           {"name": "main", "description": "general", "readme": ""},
                           {"name": "branch/pwn", "description": "pwn", "readme": "# branch/pwn"},
                       ]), \
         patch.object(NavigationEngine, "_resolve_branch_name",
                       side_effect=lambda raw, t, vc: raw):
        result = eng.navigate("Solve an ambiguous task", tree, workspace_root=tmp_path)
    assert result == "main", \
        f"expected fallback to main due to low confidence, got {result}"


def test_main_chosen_with_low_confidence_stays_main(tmp_path: Path):
    """If router chooses main, low confidence still returns main (no harm)."""
    eng, llm = _make_engine(threshold=0.7)
    tree = _make_tree_with_branch("branch/pwn")

    llm.converse_loop.return_value = _fake_response("main", 0.3)

    with patch.object(NavigationEngine, "_viable_branches",
                       return_value=["branch/pwn"]), \
         patch.object(NavigationEngine, "_read_branch_leaves",
                       return_value=[
                           {"name": "main", "description": "general", "readme": ""},
                           {"name": "branch/pwn", "description": "pwn", "readme": ""},
                       ]), \
         patch.object(NavigationEngine, "_resolve_branch_name",
                       side_effect=lambda raw, t, vc: raw):
        result = eng.navigate("Some task", tree, workspace_root=tmp_path)
    assert result == "main"


def test_negative_threshold_disables_branching(tmp_path: Path):
    """Negative threshold (-1) means 'never branch' regardless of confidence."""
    eng, llm = _make_engine(threshold=-1.0)
    tree = _make_tree_with_branch("branch/pwn")

    # Even if LLM would return high confidence, threshold short-circuits.
    llm.converse_loop.return_value = _fake_response("branch/pwn", 0.99)

    with patch.object(NavigationEngine, "_viable_branches",
                       return_value=["branch/pwn"]):
        result = eng.navigate("pwn task", tree, workspace_root=tmp_path)
    assert result == "main"
    # LLM should NOT have been called when threshold is negative.
    llm.converse_loop.assert_not_called()


def test_zero_threshold_allows_any_confidence(tmp_path: Path):
    """Threshold = 0 → any positive confidence routes to branch."""
    eng, llm = _make_engine(threshold=0.0)
    tree = _make_tree_with_branch("branch/pwn")

    llm.converse_loop.return_value = _fake_response("branch/pwn", 0.05)

    with patch.object(NavigationEngine, "_viable_branches",
                       return_value=["branch/pwn"]), \
         patch.object(NavigationEngine, "_read_branch_leaves",
                       return_value=[
                           {"name": "main", "description": "general", "readme": ""},
                           {"name": "branch/pwn", "description": "pwn", "readme": ""},
                       ]), \
         patch.object(NavigationEngine, "_resolve_branch_name",
                       side_effect=lambda raw, t, vc: raw):
        result = eng.navigate("any task", tree, workspace_root=tmp_path)
    assert result == "branch/pwn"


def test_no_branches_always_returns_main(tmp_path: Path):
    """Empty strategy tree → always main, regardless of threshold."""
    eng, llm = _make_engine(threshold=0.7)
    tree = StrategyTree()  # no branches

    result = eng.navigate("any task", tree, workspace_root=tmp_path)
    assert result == "main"
    llm.converse_loop.assert_not_called()


# ── Fix #3: README quality enforced via prompts ─────────────────────


def test_navigate_system_prompt_mentions_when_to_route():
    """The router's system prompt must instruct it to read 'When to route here'."""
    assert "When to route here" in NAVIGATE_SYSTEM_PROMPT
    # Also check it has the decision procedure structure
    assert "Decision procedure" in NAVIGATE_SYSTEM_PROMPT
    # And the JSON output format
    assert '"branch"' in NAVIGATE_SYSTEM_PROMPT
    assert '"confidence"' in NAVIGATE_SYSTEM_PROMPT


def test_navigate_system_prompt_says_main_for_uncertainty():
    """Router should be told to default to main when uncertain."""
    txt = NAVIGATE_SYSTEM_PROMPT.lower()
    assert "main" in txt
    # Either "uncertainty", "uncertain", or fallback wording should appear
    assert any(kw in txt for kw in ["uncertainty", "uncertain", "no specialized", "no clear", "no branches"]) \
        or "if multiple branches" in txt


def test_builder_branch_prompt_requires_routing_section():
    """builder_branch.md must require the 'When to route here' README section."""
    p = Path("agent_evolve/algorithms/navigation/templates/prompts/builder_branch.md")
    text = p.read_text()
    # Routing-critical format block exists
    assert "ROUTING-CRITICAL" in text
    # The required README sections are spelled out
    assert "When to route here" in text
    assert "Strategy" in text
    assert "Known limitations" in text


def test_build_navigate_prompt_includes_branch_readmes():
    """build_navigate_prompt should include each branch's README content."""
    branches = [
        {"name": "main", "description": "general", "readme": "# main\nGeneral solver."},
        {
            "name": "branch/pwn",
            "description": "pwn",
            "readme": (
                "# branch/pwn\n\n"
                "## When to route here\n"
                "- Task category contains: pwn, exploitation\n"
                "- Task title mentions: buffer overflow, ROP\n"
            ),
        },
    ]
    prompt = build_navigate_prompt("Solve a buffer overflow", branches)
    # Both branches present with their readmes
    assert "branch/pwn" in prompt
    assert "When to route here" in prompt
    assert "buffer overflow" in prompt
    # JSON output schema is in the instructions
    assert '"branch"' in prompt and '"confidence"' in prompt


# ── Smoke: fixes wired together ─────────────────────────────────────


def test_fix1_uses_config_branch_confidence_threshold(tmp_path: Path):
    """Fix #1 reads config.branch_confidence_threshold; verify both extreme values."""
    # Below-threshold confidence should fall back at threshold=0.7 ...
    eng, llm = _make_engine(threshold=0.7)
    tree = _make_tree_with_branch("branch/pwn")
    llm.converse_loop.return_value = _fake_response("branch/pwn", 0.6)
    with patch.object(NavigationEngine, "_viable_branches",
                       return_value=["branch/pwn"]), \
         patch.object(NavigationEngine, "_read_branch_leaves",
                       return_value=[{"name": "main", "description": "", "readme": ""},
                                      {"name": "branch/pwn", "description": "", "readme": ""}]), \
         patch.object(NavigationEngine, "_resolve_branch_name",
                       side_effect=lambda raw, t, vc: raw):
        assert eng.navigate("t", tree, workspace_root=tmp_path) == "main"

    # ... but should route at threshold=0.5 (lower threshold)
    eng.config.branch_confidence_threshold = 0.5
    llm.converse_loop.return_value = _fake_response("branch/pwn", 0.6)
    with patch.object(NavigationEngine, "_viable_branches",
                       return_value=["branch/pwn"]), \
         patch.object(NavigationEngine, "_read_branch_leaves",
                       return_value=[{"name": "main", "description": "", "readme": ""},
                                      {"name": "branch/pwn", "description": "", "readme": ""}]), \
         patch.object(NavigationEngine, "_resolve_branch_name",
                       side_effect=lambda raw, t, vc: raw):
        assert eng.navigate("t", tree, workspace_root=tmp_path) == "branch/pwn"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
