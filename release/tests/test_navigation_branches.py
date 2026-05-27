"""Bug 2 tests: navigation branch validation, sanitisation, and realisation.

Covers:
- VersionControl.is_valid_ref_name and create_branch rejection paths.
- NavigationEngine._sanitize_branch_name for LLM-shaped inputs.
- NavigationEngine._realise_branches invariant: every name in the
  returned list exists in git AND in tree.branches; invalid names are
  dropped without throwing.
- _resolve_branch_name's git-aware fallback when a tree-known name is
  missing from git.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from agent_evolve.algorithms.navigation.engine import NavigationEngine
from agent_evolve.engine.versioning import VersionControl
from agent_evolve.types import BranchInfo, StrategyTree


def _git_repo(tmp_path: Path) -> VersionControl:
    root = tmp_path / "ws"
    root.mkdir()
    (root / "hello.txt").write_text("hi\n")
    vc = VersionControl(root)
    vc.init()
    vc.commit("seed")
    return vc


# ──────────────────────────────────────────── is_valid_ref_name


@pytest.mark.parametrize(
    "name,expected",
    [
        ("branch/foo", True),
        ("multi-outcome-markets", True),
        ("branch/topic/sub", True),
        # Git itself considers these names illegal.
        ("with space", False),
        ("..bad", False),
        ("-leading-dash", False),
        ("trailing.", False),
        ("has\\backslash", False),
        ("colon:in-name", False),
        ("", False),
        (None, False),
    ],
)
def test_is_valid_ref_name(name, expected):
    assert VersionControl.is_valid_ref_name(name) == expected


def test_create_branch_rejects_illegal_name(tmp_path):
    vc = _git_repo(tmp_path)
    # Space and double-dot are ref-format violations at the git level.
    with pytest.raises(ValueError):
        vc.create_branch("multi outcome markets")
    with pytest.raises(ValueError):
        vc.create_branch("..bad")


def test_create_branch_succeeds_and_is_visible(tmp_path):
    vc = _git_repo(tmp_path)
    vc.create_branch("branch/clean-name")
    assert vc.branch_exists("branch/clean-name")


# ──────────────────────────────────────────── _sanitize_branch_name


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Multi-Outcome Markets", "branch/multi-outcome-markets"),
        ("low information markets", "branch/low-information-markets"),
        ("branch/foo", "branch/foo"),
        ("FOO/BAR", "branch/foo/bar"),
        ("foo|bar", "branch/foobar"),
        ("...", None),
        ("", None),
        (None, None),
        ("main", "main"),
        ("  spaced  ", "branch/spaced"),
    ],
)
def test_sanitize_branch_name(raw, expected):
    assert NavigationEngine._sanitize_branch_name(raw) == expected


# ──────────────────────────────────────────── _realise_branches


class _StubEngine:
    """Minimal stand-in that exposes the realise_branches helper without
    instantiating the full NavigationEngine (which pulls in LLM providers
    and configs).

    ``_realise_branches`` now lives on ``OrchestratedTemplate`` since
    only the orchestrated template needs to turn an LLM-proposed plan
    into real git branches (inline mode lets the evolver create them
    directly via ``workspace_bash``).
    """

    _sanitize_branch_name = staticmethod(NavigationEngine._sanitize_branch_name)

    @staticmethod
    def _realise_branches(vc, tree, recs, evo_number):
        from agent_evolve.algorithms.navigation.templates.orchestrated import (
            OrchestratedTemplate,
        )

        class _FakeEngine:
            class _Cfg:
                trajectory_only = False
            config = _Cfg()
            llm = None
        tpl = OrchestratedTemplate(_FakeEngine())
        return tpl._realise_branches(vc, tree, recs, evo_number)


def test_realise_branches_creates_git_branches_and_updates_tree(tmp_path):
    vc = _git_repo(tmp_path)
    tree = StrategyTree()

    recs = [
        {"name": "Multi-Outcome Markets", "description": "mom"},
        {"name": "low information markets", "description": "lim"},
        {"name": "foo|bar", "description": "bad name, still usable after sanitising"},
        {"name": "...", "description": "unusable"},
        {"name": "main", "description": "cannot use main"},
    ]
    engine = _StubEngine()
    realised = engine._realise_branches(vc, tree, recs, evo_number=1)

    names = [r["name"] for r in realised]
    assert "branch/multi-outcome-markets" in names
    assert "branch/low-information-markets" in names
    assert "branch/foobar" in names
    # Unusable / main entries are dropped.
    assert "main" not in names
    assert None not in names

    # Every returned name exists in git AND in the tree.
    for name in names:
        assert vc.branch_exists(name)
        assert any(b.name == name for b in tree.branches)

    # After realisation we should be back on main.
    assert vc.get_current_branch() == "main"


def test_realise_branches_deduplicates_on_sanitised_name(tmp_path):
    vc = _git_repo(tmp_path)
    tree = StrategyTree()

    recs = [
        {"name": "Alpha Branch"},
        {"name": "alpha-branch"},  # sanitises to same slug
    ]
    realised = _StubEngine()._realise_branches(vc, tree, recs, evo_number=1)
    assert len(realised) == 1
    assert realised[0]["name"] == "branch/alpha-branch"


def test_realise_branches_idempotent_on_existing_branch(tmp_path):
    vc = _git_repo(tmp_path)
    tree = StrategyTree()
    # Pre-create the branch; _realise_branches should not blow up.
    vc.create_branch("branch/already-there")
    vc.checkout_branch("main")

    recs = [{"name": "already there"}]
    realised = _StubEngine()._realise_branches(vc, tree, recs, evo_number=1)
    assert realised[0]["name"] == "branch/already-there"
    assert vc.branch_exists("branch/already-there")


# ──────────────────────────────────────────── _resolve_branch_name


def test_resolve_branch_name_git_aware_falls_back_to_main(tmp_path):
    vc = _git_repo(tmp_path)
    tree = StrategyTree(branches=[
        BranchInfo(name="branch/ghost"),
        BranchInfo(name="branch/real"),
    ])
    vc.create_branch("branch/real")
    vc.checkout_branch("main")

    # Resolver should return real as-is…
    assert NavigationEngine._resolve_branch_name("branch/real", tree, vc=vc) == "branch/real"
    # …but ghost should fall back to main since the git branch is absent.
    assert NavigationEngine._resolve_branch_name("branch/ghost", tree, vc=vc) == "main"


def test_resolve_branch_name_without_vc_still_works():
    tree = StrategyTree(branches=[BranchInfo(name="branch/foo")])
    assert NavigationEngine._resolve_branch_name("foo", tree) == "branch/foo"
    assert NavigationEngine._resolve_branch_name("branch/foo", tree) == "branch/foo"
    assert NavigationEngine._resolve_branch_name("nonexistent", tree) == "main"


# ──────────────────────────────────────────── _viable_branches


def test_viable_branches_filters_failed_checkouts(tmp_path):
    vc = _git_repo(tmp_path)
    vc.create_branch("branch/good")
    vc.create_branch("branch/bad")
    vc.checkout_branch("main")

    tree = StrategyTree(branches=[
        BranchInfo(name="branch/good", failed_checkouts=0),
        BranchInfo(name="branch/bad", failed_checkouts=5),
    ])
    assert NavigationEngine._viable_branches(tree, vc) == ["branch/good"]


def test_viable_branches_filters_missing_git_branches(tmp_path):
    vc = _git_repo(tmp_path)
    vc.create_branch("branch/real")
    vc.checkout_branch("main")

    tree = StrategyTree(branches=[
        BranchInfo(name="branch/real"),
        BranchInfo(name="branch/ghost"),
    ])
    assert NavigationEngine._viable_branches(tree, vc) == ["branch/real"]
