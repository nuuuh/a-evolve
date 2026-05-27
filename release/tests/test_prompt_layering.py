"""Tests that the full-system prompts directory layering works correctly.

Layer 1: framework template at agent_evolve/algorithms/navigation/templates/prompts/<name>
Layer 2 (full system override): experiments/<bench>/evolver_prompts_nav/<name>
Layer 3 (shared per-benchmark fallback): experiments/<bench>/evolver_prompts/<name>

The full system's prompts_dir points at evolver_prompts_nav/. When a file
is missing from there, _load_prompt should fall back to the sibling
evolver_prompts/ directory so shared per-benchmark guidance is preserved.

Multi-only's prompts_dir points at evolver_prompts/ — it should NOT see
any of the nav-specific content.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_evolve.algorithms.navigation.templates.structured_evolution import _load_prompt


# ── Helper to construct a minimal benchmark-prompts layout ──

def _make_layout(tmp: Path, nav_files: dict[str, str], shared_files: dict[str, str]):
    bench = tmp / "experiments" / "fakebench"
    nav_dir = bench / "evolver_prompts_nav"
    shared_dir = bench / "evolver_prompts"
    nav_dir.mkdir(parents=True, exist_ok=True)
    shared_dir.mkdir(parents=True, exist_ok=True)
    for name, content in nav_files.items():
        (nav_dir / name).write_text(content)
    for name, content in shared_files.items():
        (shared_dir / name).write_text(content)
    return nav_dir, shared_dir


# ── Tests ──


def test_nav_dir_used_when_file_present(tmp_path: Path):
    """When the nav file exists, it is used as benchmark_context."""
    nav_dir, _ = _make_layout(tmp_path,
        nav_files={"verifier_system.md": "NAV-SPECIFIC verifier content"},
        shared_files={"verifier_system.md": "SHARED verifier content"},
    )
    text = _load_prompt(nav_dir, "verifier_system.md")
    assert "NAV-SPECIFIC verifier content" in text
    assert "SHARED verifier content" not in text


def test_nav_dir_falls_back_to_shared_when_file_missing(tmp_path: Path):
    """When the nav file is missing, the shared file is used."""
    nav_dir, _ = _make_layout(tmp_path,
        nav_files={},  # no nav-specific override
        shared_files={"builder_system.md": "SHARED builder content"},
    )
    text = _load_prompt(nav_dir, "builder_system.md")
    assert "SHARED builder content" in text


def test_shared_dir_does_not_see_nav_files(tmp_path: Path):
    """Multi-only's prompts_dir (evolver_prompts) must NOT load nav files."""
    nav_dir, shared_dir = _make_layout(tmp_path,
        nav_files={"analyst_nav_system.md": "NAV-only content"},
        shared_files={"analyst_system.md": "SHARED analyst content"},
    )
    # When multi-only loads analyst_nav_system.md (which exists in nav only),
    # using shared_dir, it should NOT find it (no fallback in this direction).
    text = _load_prompt(shared_dir, "analyst_nav_system.md")
    assert "NAV-only content" not in text


def test_no_files_returns_empty_context(tmp_path: Path):
    """If neither dir has the file, benchmark_context is empty."""
    nav_dir, _ = _make_layout(tmp_path,
        nav_files={},
        shared_files={},
    )
    # Use a name that exists in the framework templates so we get the
    # general template; benchmark_context substitution should be empty.
    text = _load_prompt(nav_dir, "analyst_nav_system.md")
    # The general template exists and contains the placeholder marker;
    # after substitution, the placeholder text should be replaced with empty
    assert "{benchmark_context}" not in text  # placeholder substituted


def test_real_layout_full_system_loads_both(tmp_path: Path):
    """Smoke test against the actual repo layout: nav dir present, shared dir present."""
    repo = Path(__file__).resolve().parent.parent
    ctf_nav = repo / "experiments" / "ctf_dojo" / "evolver_prompts_nav"
    if not ctf_nav.exists():
        # If repo isn't laid out as expected, skip
        return

    # analyst_nav_system.md should come from evolver_prompts_nav/
    text = _load_prompt(ctf_nav, "analyst_nav_system.md")
    assert "non-transferable artifacts" in text or "transferability audit" in text.lower(), \
        f"Expected nav-specific transferability content in CTF analyst_nav_system, got: {text[:300]}"

    # builder_system.md is NOT in nav/, should fall back to shared evolver_prompts/
    text = _load_prompt(ctf_nav, "builder_system.md")
    # The shared CTF builder_system mentions tools like xor_decrypt or sandbox
    assert "sandbox" in text.lower() or "tools" in text.lower(), \
        f"Expected shared CTF builder content (mentions sandbox/tools); got: {text[:300]}"


def test_multi_only_does_not_get_nav_content(tmp_path: Path):
    """Multi-only's prompts_dir is evolver_prompts/. It should NOT inherit nav content."""
    repo = Path(__file__).resolve().parent.parent
    ctf_shared = repo / "experiments" / "ctf_dojo" / "evolver_prompts"
    if not ctf_shared.exists():
        return

    # Multi-only loads analyst_nav_system.md? It doesn't, but if it did,
    # the shared dir should not have any nav-only content.
    # The structured_evolution template loads analyst_system.md (multi),
    # not analyst_nav_system.md. Verify analyst_system.md does NOT contain
    # the nav-specific phrases that I added (transferability audit, etc.).
    text = _load_prompt(ctf_shared, "analyst_system.md")
    bad_phrases = [
        "transferability audit",
        "non-transferable artifacts",
        "TRANSFERABILITY ANALYSIS",
    ]
    for phrase in bad_phrases:
        assert phrase.lower() not in text.lower(), \
            f"Multi-only analyst_system.md should not contain nav phrase '{phrase}'"


def test_nav_verifier_has_partial_verdict_semantics():
    """Each benchmark's evolver_prompts_nav/verifier_system.md must define
    PASS/PARTIAL/FAIL so the structured_navigation _verify() parser sees them."""
    repo = Path(__file__).resolve().parent.parent
    for bench in ("ctf_dojo", "futurex", "polybench"):
        p = repo / "experiments" / bench / "evolver_prompts_nav" / "verifier_system.md"
        if not p.exists():
            continue
        text = p.read_text()
        for verdict in ("VERDICT: PASS", "VERDICT: PARTIAL", "VERDICT: FAIL"):
            assert verdict in text, f"{bench}: missing '{verdict}' in nav verifier"
        # Non-regression / cross-category guidance
        assert ("regression" in text.lower()
                or "transferab" in text.lower()), \
            f"{bench}: nav verifier should mention regression/transferability"


def test_nav_research_has_transferability_fields():
    """Each benchmark's evolver_prompts_nav/research_system.md must instruct
    the researcher to fill transferability fields."""
    repo = Path(__file__).resolve().parent.parent
    for bench in ("ctf_dojo", "futurex", "polybench"):
        p = repo / "experiments" / bench / "evolver_prompts_nav" / "research_system.md"
        if not p.exists():
            continue
        text = p.read_text()
        assert "transferable" in text.lower(), \
            f"{bench}: nav research should mention transferable"
        assert ("recommended_target" in text or "branch/" in text), \
            f"{bench}: nav research should mention recommended_target / branch routing"


def test_general_research_template_clean():
    """Framework's research_system.md must NOT contain nav-only transferability
    instructions — those would leak into multi-only."""
    repo = Path(__file__).resolve().parent.parent
    p = repo / "agent_evolve" / "algorithms" / "navigation" / "templates" / "prompts" / "research_system.md"
    text = p.read_text()
    assert "TRANSFERABILITY" not in text, \
        "Framework research_system.md should not have nav-only TRANSFERABILITY block"
    assert "recommended_target" not in text, \
        "Framework research_system.md should not require recommended_target field"


def test_general_verifier_template_clean():
    """Framework's verifier_system.md must NOT mention PARTIAL — that's
    a full-system-only concept, not multi-only's verdict space."""
    repo = Path(__file__).resolve().parent.parent
    p = repo / "agent_evolve" / "algorithms" / "navigation" / "templates" / "prompts" / "verifier_system.md"
    text = p.read_text()
    assert "PARTIAL" not in text, \
        "Framework verifier_system.md should not mention PARTIAL (multi-only path)"
    assert "VERIFY TWO THINGS" not in text, \
        "Framework verifier_system.md should not contain regression-check block"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
