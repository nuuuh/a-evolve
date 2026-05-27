"""Serialise the Activity registry + Type enum into JSON for the frontend.

The frontend needs to know:
  - which concrete node kinds exist (Actions, Control nodes, CallActivity,
    ExpansionRegion) and their typed pin shapes, so it can render a
    palette + handles
  - the complete ``Type`` enum so wire colour-coding and type-match
    rules are identical on both sides

Everything is derived at runtime from ``default_registry()`` — there is
no hand-maintained schema here.
"""

from __future__ import annotations

from typing import Any

from ..activity.call_activity import CallActivity
from ..activity.control import ExpansionRegion
from ..activity.registry import default_registry
from ..activity.types import Type


def _pins_to_json(pins, direction: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in pins:
        entry: dict[str, Any] = {
            "name": p.name,
            "type": p.type.value,
            "direction": direction,
        }
        if direction == "in":
            entry["required"] = bool(getattr(p, "required", True))
        out.append(entry)
    return out


def _node_entry(cls, *, kind_override: str | None = None) -> dict[str, Any]:
    """Serialise one node class into a palette entry."""
    kind = kind_override or cls.kind
    entry: dict[str, Any] = {
        "kind": kind,
        "label": cls.__name__,
        "doc": (cls.__doc__ or "").strip().split("\n\n")[0].strip(),
    }
    # Dynamic-pin nodes (CallActivity, ExpansionRegion) have empty class-level
    # pins — pins are resolved at validation time from a referenced sub-Activity.
    # Expose an empty shape with a hint so the frontend shows the config field.
    if cls is CallActivity:
        entry["dynamic_pins"] = True
        entry["config_schema"] = {
            "activity": {"type": "string", "required": True,
                         "hint": "Name of a sibling Activity to invoke"},
        }
    elif cls is ExpansionRegion:
        entry["dynamic_pins"] = True
        entry["config_schema"] = {
            "activity": {"type": "string", "required": True,
                         "hint": "Name of a sibling Activity to invoke per item"},
            "mode": {"type": "string", "required": False,
                     "enum": ["iterative", "parallel"], "default": "iterative"},
            "item_param": {"type": "string", "required": False,
                           "default": "item",
                           "hint": "Name of the sub-Activity parameter that receives each element"},
            "result_param": {"type": "string", "required": False,
                             "default": "",
                             "hint": "Optional: name of the sub-Activity's output to collect into a list"},
        }
    else:
        try:
            entry["input_pins"] = _pins_to_json(cls.input_pins(None), "in")
            entry["output_pins"] = _pins_to_json(cls.output_pins(None), "out")
        except Exception:
            entry["input_pins"] = []
            entry["output_pins"] = []

    return entry


def _action_entry(cls) -> dict[str, Any]:
    entry = _node_entry(cls, kind_override="Action")
    entry["action_kind"] = cls.action_kind
    return entry


def build_schema() -> dict[str, Any]:
    """Return the full palette + type catalogue the frontend consumes."""
    reg = default_registry()

    # Control-flow + call nodes (excluding Action, which is the wrapper kind).
    control: list[dict[str, Any]] = []
    for kind in reg.list_kinds():
        if kind == "Action":
            continue
        cls = reg._by_kind[kind]  # internal but stable; used only for introspection
        control.append(_node_entry(cls))

    # Concrete actions, grouped by module for palette organisation.
    actions: list[dict[str, Any]] = []
    for action_kind in reg.list_actions():
        cls = reg._actions[action_kind]
        entry = _action_entry(cls)
        entry["group"] = (cls.__module__ or "").rsplit(".", 1)[-1]
        actions.append(entry)

    types = [{"name": t.name, "value": t.value} for t in Type]

    return {
        "types": types,
        "control_nodes": control,
        "actions": actions,
    }
