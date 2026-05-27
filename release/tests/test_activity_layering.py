"""Phase 6 — decoupling invariants.

Walks every file in ``agent_evolve/algorithms/navigation/activity/`` and
asserts that no file imports from a layer above its own.  Violations
fail CI.

Layer map (files at depth 1 relative to ``activity/``):

    Layer 1   types.py, spec.py
    Layer 2   pin.py, activity_node.py, action.py, call_activity.py,
              control.py, flow.py
    Layer 3   registry.py, nodes/*.py  (any depth)
    Layer 4   validator.py, runtime.py, builder.py, exporters.py
    Layer 5   adapters.py

Spec bundles (``specs/*.py``) are Layer 5 because they compose
everything.  ``__init__.py`` files are Layer 5 — they re-export and may
reference any layer for the public API.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


ACTIVITY_ROOT = (
    Path(__file__).resolve().parent.parent
    / "agent_evolve"
    / "algorithms"
    / "navigation"
    / "activity"
)


FILE_LAYER: dict[str, int] = {
    # Layer 1 — pure data
    "types.py": 1,
    "spec.py": 1,
    # Layer 2 — metamodel
    "pin.py": 2,
    "activity_node.py": 2,
    "action.py": 2,
    "call_activity.py": 2,
    "control.py": 2,
    "flow.py": 2,
    # Layer 3 — registry + node catalog
    "registry.py": 3,
    # Layer 4 — tooling
    "validator.py": 4,
    "runtime.py": 4,
    "builder.py": 4,
    "exporters.py": 4,
    # Layer 5 — adapters, specs, public init
    "adapters.py": 5,
    "__init__.py": 5,
}


def _relpath(path: Path) -> str:
    return str(path.relative_to(ACTIVITY_ROOT))


def _file_layer(rel: str) -> int:
    """Layer of a file (by path relative to activity/)."""
    parts = rel.split("/")
    basename = parts[-1]
    # nodes/ is Layer 3 for leaf Action modules, Layer 5 for the
    # agents/ sub-package (those are compositions that use the builder).
    if parts[0] == "nodes":
        if len(parts) >= 2 and parts[1] == "agents":
            return 5
        return 3
    # specs/ is Layer 5 (composes everything)
    if parts[0] == "specs":
        return 5
    return FILE_LAYER.get(basename, 5)


def _imported_siblings(source: str) -> set[str]:
    """Return the set of *relative* module names imported from within
    this package (any level of ``.``-prefix)."""
    out: set[str] = set()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level and node.module:
                # Normalise to a sibling file name when possible.  For
                # "from ..nodes.git import X" -> "nodes.git"; for
                # "from .spec import ..." -> "spec".
                out.add(node.module)
            elif node.level and not node.module:
                # from . import foo
                for alias in node.names:
                    out.add(alias.name)
    return out


def _importee_layer(relative_module: str) -> int | None:
    """Resolve a relative import (``foo.bar``) to a layer number.

    Returns None if the import is not inside the ``activity/`` package
    (e.g. ``....contract.workspace`` — those go outside and are allowed).
    """
    segments = relative_module.split(".")
    first = segments[0]
    if first == "nodes":
        return 3
    if first == "specs":
        return 5
    if f"{first}.py" in FILE_LAYER:
        return FILE_LAYER[f"{first}.py"]
    return None  # External import


def test_every_file_has_a_layer():
    for path in ACTIVITY_ROOT.rglob("*.py"):
        rel = _relpath(path)
        layer = _file_layer(rel)
        assert layer in {1, 2, 3, 4, 5}, f"{rel}: no layer assigned"


def test_no_layer_imports_from_higher_layer():
    violations: list[str] = []
    for path in ACTIVITY_ROOT.rglob("*.py"):
        rel = _relpath(path)
        own_layer = _file_layer(rel)
        source = path.read_text()
        for imp in _imported_siblings(source):
            target_layer = _importee_layer(imp)
            if target_layer is None:
                continue
            if target_layer > own_layer:
                violations.append(
                    f"{rel} (layer {own_layer}) imports from "
                    f"{imp} (layer {target_layer})"
                )
    assert not violations, "Layering violations:\n  " + "\n  ".join(violations)


def test_layer1_imports_nothing_from_activity():
    """Layer 1 (types.py, spec.py) must be self-contained — no relative
    imports from any other activity/ module."""
    for name in ("types.py", "spec.py"):
        source = (ACTIVITY_ROOT / name).read_text()
        sibs = _imported_siblings(source)
        in_package = {
            s for s in sibs
            if _importee_layer(s) is not None and _importee_layer(s) > 1
        }
        assert not in_package, f"{name} imports {in_package}"


def test_layer2_only_imports_layer1():
    """Metamodel files must not reach into registry or node catalog."""
    layer2_files = [f for f, l in FILE_LAYER.items() if l == 2]
    for name in layer2_files:
        path = ACTIVITY_ROOT / name
        source = path.read_text()
        sibs = _imported_siblings(source)
        bad = {
            s for s in sibs
            if (tl := _importee_layer(s)) is not None and tl > 2
        }
        assert not bad, f"{name} imports from layer >2: {bad}"
