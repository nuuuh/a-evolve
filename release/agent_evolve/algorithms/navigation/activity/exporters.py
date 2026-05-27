"""Exporters: Activity → JSON / Mermaid / PlantUML.

Mermaid renders in GitHub READMEs directly.  PlantUML renders in any
UML editor (draw.io, Enterprise Architect, the online PlantUML server)
so a designer can inspect or edit the diagram with tooling they
already have.
"""

from __future__ import annotations

from .flow import Endpoint
from .spec import Activity


# ── Mermaid ──────────────────────────────────────────────────────────


def to_mermaid(activity: Activity) -> str:
    """Render an Activity as a Mermaid flowchart (top-down)."""
    lines: list[str] = [f"flowchart TD", f"    %% {activity.name}"]

    # Parameters as stadium-shaped entry points
    for p in activity.parameters:
        if p.direction == "in":
            lines.append(f"    {p.id}([{p.id}: {p.type.value}])")
        else:
            lines.append(f"    {p.id}[/{p.id}: {p.type.value}/]")

    # Nodes as rectangles; decision/fork/join with dedicated shapes
    for n in activity.nodes:
        label = _mermaid_label(n)
        shape_open, shape_close = _mermaid_shape(n.kind)
        lines.append(f"    {n.id}{shape_open}{label}{shape_close}")

    # Flows
    for f in activity.flows:
        arrow = "-->" if f.kind == "ObjectFlow" else "-.->"
        lines.append(f"    {f.source.replace('.', '_')} {arrow} "
                     f"{f.target.replace('.', '_')}")

    # (Mermaid IDs can't contain dots — emit pin-carrying edges as
    # labeled arrows between the plain node IDs.)
    return "\n".join(lines)


def _mermaid_label(node) -> str:
    kind = node.kind
    if kind == "Action":
        return f"\"{node.id}<br/>{node.config.get('action_kind', '')}\""
    return f"\"{node.id}<br/>{kind}\""


def _mermaid_shape(kind: str) -> tuple[str, str]:
    return {
        "InitialNode": ("((", "))"),
        "FinalNode": ("(((", ")))"),
        "DecisionNode": ("{", "}"),
        "ForkNode": ("[/", "/]"),
        "JoinNode": ("[\\", "\\]"),
        "ExpansionRegion": ("[[", "]]"),
        "CallActivity": ("[(", ")]"),
    }.get(kind, ("[", "]"))


# ── PlantUML ─────────────────────────────────────────────────────────


def to_plantuml(activity: Activity) -> str:
    """Render an Activity as a PlantUML Activity Diagram.

    Emits the ``activity beta`` syntax (supported by plantuml.com since
    2014).  For deeply nested activities only the top-level is
    rendered; referenced sub-Activities are expanded inline as
    partitions.
    """
    lines: list[str] = ["@startuml", f"title {activity.name}", "start"]

    # Linear topology rendering: walk nodes in declaration order,
    # emitting each as a PlantUML activity.  This gives a readable
    # diagram even for complex graphs; for strict topological order
    # the Mermaid output is preferable.
    for n in activity.nodes:
        if n.kind == "InitialNode":
            continue
        if n.kind == "FinalNode":
            lines.append("stop")
            continue
        if n.kind == "DecisionNode":
            lines.append(f"if ({n.id}?) then (yes)")
            lines.append("else (no)")
            lines.append("endif")
            continue
        if n.kind == "ExpansionRegion":
            sub = n.config.get("activity", "")
            lines.append(f"partition \"ExpansionRegion: {n.id} -> {sub}\" {{")
            if sub in activity.sub_activities:
                for sn in activity.sub_activities[sub].nodes:
                    if sn.kind == "Action":
                        lines.append(f"    :{sn.config.get('action_kind', sn.id)};")
            lines.append("}")
            continue
        if n.kind == "CallActivity":
            sub = n.config.get("activity", "")
            lines.append(f":{n.id} <<CallActivity -> {sub}>>;")
            continue
        if n.kind == "Action":
            lines.append(f":{n.config.get('action_kind', n.id)};")
            continue
        lines.append(f":{n.id} <<{n.kind}>>;")

    if not any(n.kind == "FinalNode" for n in activity.nodes):
        lines.append("stop")
    lines.append("@enduml")
    return "\n".join(lines)


# ── JSON (pass-through) ──────────────────────────────────────────────


def to_json(activity: Activity) -> dict:
    """Return the canonical JSON form of an Activity."""
    return activity.to_json()
