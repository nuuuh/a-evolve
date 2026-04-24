"""JSON-serialisable spec for an UML Activity.

These dataclasses are the on-disk representation of an ``Activity`` — the
artifact a designer produces (by hand, via the builder, or from a future
GUI).  The runtime consumes these specs and dispatches to registered
``ActivityNode`` classes.

No imports from Layer 2+ — spec is pure data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .types import Type


FlowKind = Literal["ObjectFlow", "ControlFlow"]
ParameterDirection = Literal["in", "out"]


@dataclass(frozen=True)
class ParameterSpec:
    """UML ActivityParameterNode — a typed input/output of an Activity."""

    id: str
    type: Type
    direction: ParameterDirection = "in"

    def to_json(self) -> dict[str, Any]:
        return {"id": self.id, "type": self.type.value, "direction": self.direction}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> ParameterSpec:
        return cls(
            id=data["id"],
            type=Type(data["type"]),
            direction=data.get("direction", "in"),
        )


@dataclass(frozen=True)
class NodeSpec:
    """A node inside an Activity.  ``kind`` selects the class in the registry."""

    id: str
    kind: str
    config: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {"id": self.id, "kind": self.kind}
        if self.config:
            out["config"] = dict(self.config)
        return out

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> NodeSpec:
        return cls(id=data["id"], kind=data["kind"], config=dict(data.get("config", {})))


@dataclass(frozen=True)
class FlowSpec:
    """An UML ObjectFlow or ControlFlow between two node pins."""

    kind: FlowKind
    source: str
    target: str

    def to_json(self) -> dict[str, Any]:
        return {"kind": self.kind, "source": self.source, "target": self.target}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> FlowSpec:
        return cls(kind=data["kind"], source=data["source"], target=data["target"])


@dataclass
class Activity:
    """An UML Activity: the blueprint a designer produces.

    An Activity owns its parameters, nodes, flows, and any nested
    sub-Activities (referenced by ``CallActivity`` and ``ExpansionRegion``
    nodes by name).
    """

    name: str
    description: str = ""
    parameters: list[ParameterSpec] = field(default_factory=list)
    nodes: list[NodeSpec] = field(default_factory=list)
    flows: list[FlowSpec] = field(default_factory=list)
    sub_activities: dict[str, Activity] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [p.to_json() for p in self.parameters],
            "nodes": [n.to_json() for n in self.nodes],
            "flows": [f.to_json() for f in self.flows],
            "sub_activities": {
                name: sub.to_json() for name, sub in self.sub_activities.items()
            },
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Activity:
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            parameters=[ParameterSpec.from_json(p) for p in data.get("parameters", [])],
            nodes=[NodeSpec.from_json(n) for n in data.get("nodes", [])],
            flows=[FlowSpec.from_json(f) for f in data.get("flows", [])],
            sub_activities={
                name: Activity.from_json(sub)
                for name, sub in data.get("sub_activities", {}).items()
            },
        )
