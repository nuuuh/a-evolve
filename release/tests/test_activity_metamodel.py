"""Phase 1 tests — Activity metamodel (Layer 1-2 classes).

Covers:
  - JSON ↔ Activity round-trip
  - Type enum coverage (every enum value parses from its string)
  - ActionRegistry register/lookup/list
  - ActivityNode pin declarations (control nodes)
"""

from __future__ import annotations

import json

import pytest

from agent_evolve.algorithms.navigation.activity import (
    Activity,
    FlowSpec,
    NodeSpec,
    ParameterSpec,
    Type,
)
from agent_evolve.algorithms.navigation.activity.action import Action
from agent_evolve.algorithms.navigation.activity.call_activity import CallActivity
from agent_evolve.algorithms.navigation.activity.control import (
    DecisionNode,
    ExpansionRegion,
    FinalNode,
    ForkNode,
    InitialNode,
    JoinNode,
)
from agent_evolve.algorithms.navigation.activity.pin import InputPin, OutputPin
from agent_evolve.algorithms.navigation.activity.registry import ActionRegistry


# ── Type enum ────────────────────────────────────────────────────────


def test_type_enum_round_trip():
    # Every enum value round-trips through its string form.
    for t in Type:
        assert Type(t.value) is t


# ── Spec dataclasses ─────────────────────────────────────────────────


def test_parameter_spec_round_trip():
    p = ParameterSpec(id="ws", type=Type.WORKSPACE, direction="in")
    assert ParameterSpec.from_json(p.to_json()) == p


def test_node_spec_round_trip_with_config():
    n = NodeSpec(id="snap", kind="Action", config={"action_kind": "op.snapshot_workspace"})
    assert NodeSpec.from_json(n.to_json()) == n


def test_node_spec_round_trip_without_config():
    n = NodeSpec(id="start", kind="InitialNode")
    round_tripped = NodeSpec.from_json(n.to_json())
    assert round_tripped.id == n.id
    assert round_tripped.kind == n.kind
    assert round_tripped.config == {}


def test_flow_spec_round_trip():
    f = FlowSpec(kind="ObjectFlow", source="a.out", target="b.in")
    assert FlowSpec.from_json(f.to_json()) == f


def test_activity_round_trip_flat():
    act = Activity(
        name="demo",
        description="flat activity",
        parameters=[ParameterSpec(id="ws", type=Type.WORKSPACE)],
        nodes=[
            NodeSpec(id="start", kind="InitialNode"),
            NodeSpec(id="end", kind="FinalNode"),
        ],
        flows=[FlowSpec(kind="ControlFlow", source="start", target="end")],
    )
    data = json.loads(json.dumps(act.to_json()))
    restored = Activity.from_json(data)
    assert restored.name == act.name
    assert restored.description == act.description
    assert restored.parameters == act.parameters
    assert restored.nodes == act.nodes
    assert restored.flows == act.flows


def test_activity_round_trip_nested_sub_activities():
    sub = Activity(
        name="child",
        parameters=[ParameterSpec(id="x", type=Type.STRING)],
    )
    top = Activity(
        name="parent",
        sub_activities={"child": sub},
    )
    restored = Activity.from_json(json.loads(json.dumps(top.to_json())))
    assert "child" in restored.sub_activities
    assert restored.sub_activities["child"].name == "child"
    assert restored.sub_activities["child"].parameters[0].id == "x"
    assert restored.sub_activities["child"].parameters[0].type is Type.STRING


# ── Control nodes: pin declarations ──────────────────────────────────


def test_initial_node_pins():
    assert InitialNode.input_pins() == []
    out = InitialNode.output_pins()
    assert out == [OutputPin(name="out", type=Type.VOID)]


def test_final_node_pins():
    assert FinalNode.output_pins() == []
    inputs = FinalNode.input_pins()
    assert len(inputs) == 1
    assert inputs[0].type is Type.VOID
    assert inputs[0].required is False


def test_decision_node_value_type_propagates():
    cfg = {"value_type": Type.PLAN.value}
    inputs = DecisionNode.input_pins(cfg)
    outputs = DecisionNode.output_pins(cfg)
    # guard + datum
    assert {p.name for p in inputs} == {"guard", "in"}
    assert next(p for p in inputs if p.name == "guard").type is Type.BOOLEAN
    assert next(p for p in inputs if p.name == "in").type is Type.PLAN
    # two outputs of the propagated type
    assert {p.name for p in outputs} == {"true", "false"}
    assert all(p.type is Type.PLAN for p in outputs)


def test_fork_node_produces_n_outputs():
    outs = ForkNode.output_pins({"outputs": 3, "value_type": Type.STRING.value})
    assert [p.name for p in outs] == ["out0", "out1", "out2"]
    assert all(p.type is Type.STRING for p in outs)


def test_join_node_accepts_n_inputs():
    ins = JoinNode.input_pins({"inputs": 4, "value_type": Type.STRING.value})
    assert [p.name for p in ins] == ["in0", "in1", "in2", "in3"]


def test_expansion_region_pins_from_sub_activity():
    sub = Activity(
        name="evolve_one",
        parameters=[
            ParameterSpec(id="item", type=Type.BRANCH_SPEC, direction="in"),
            ParameterSpec(id="workspace", type=Type.WORKSPACE, direction="in"),
            ParameterSpec(id="mutated", type=Type.MUTATION_REPORT, direction="out"),
        ],
    )
    cfg = {"activity": "evolve_one", "item_param": "item", "result_param": "mutated"}
    inputs, outputs = ExpansionRegion.pins_from_sub_activity(sub, cfg)

    input_names = [p.name for p in inputs]
    assert input_names[0] == "items"
    assert inputs[0].type is Type.BRANCH_SPEC_LIST
    assert "workspace" in input_names

    output_names = [p.name for p in outputs]
    assert output_names[0] == "results"
    # results list of MUTATION_REPORT falls back to STRING_LIST per the
    # framework's _list_type_for rule (no MUTATION_REPORT_LIST enum yet).
    assert outputs[0].type in (Type.STRING_LIST,)


def test_call_activity_pins_from_sub_activity():
    sub = Activity(
        name="analyst",
        parameters=[
            ParameterSpec(id="batch", type=Type.BATCH_RESULTS, direction="in"),
            ParameterSpec(id="plan", type=Type.PLAN, direction="out"),
        ],
    )
    inputs, outputs = CallActivity.pins_from_sub_activity(sub)
    assert inputs == [InputPin(name="batch", type=Type.BATCH_RESULTS)]
    assert outputs == [OutputPin(name="plan", type=Type.PLAN)]


# ── ActionRegistry ───────────────────────────────────────────────────


def test_registry_registers_action_by_action_kind():
    class Dummy(Action):
        action_kind = "op.dummy"

        @classmethod
        def input_pins(cls, config=None):
            return [InputPin(name="x", type=Type.STRING)]

        @classmethod
        def output_pins(cls, config=None):
            return [OutputPin(name="y", type=Type.STRING)]

        def execute(self, inputs, ctx):
            return {"y": inputs["x"].upper()}

    registry = ActionRegistry()
    registry.register(Dummy)

    node = NodeSpec(id="d", kind="Action", config={"action_kind": "op.dummy"})
    assert registry.lookup(node) is Dummy


def test_registry_rejects_action_without_kind():
    class NoKind(Action):
        @classmethod
        def input_pins(cls, config=None):
            return []

        @classmethod
        def output_pins(cls, config=None):
            return []

        def execute(self, inputs, ctx):
            return {}

    registry = ActionRegistry()
    with pytest.raises(ValueError, match="action_kind"):
        registry.register(NoKind)


def test_registry_lookup_control_nodes():
    registry = ActionRegistry()
    for kind, expected in [
        ("InitialNode", InitialNode),
        ("FinalNode", FinalNode),
        ("DecisionNode", DecisionNode),
        ("ForkNode", ForkNode),
        ("JoinNode", JoinNode),
        ("ExpansionRegion", ExpansionRegion),
        ("CallActivity", CallActivity),
    ]:
        assert registry.lookup(NodeSpec(id="n", kind=kind)) is expected


def test_registry_unknown_kind_raises():
    registry = ActionRegistry()
    with pytest.raises(KeyError):
        registry.lookup(NodeSpec(id="n", kind="UnknownKind"))


def test_registry_unknown_action_kind_raises():
    registry = ActionRegistry()
    with pytest.raises(KeyError):
        registry.lookup(NodeSpec(id="n", kind="Action",
                                 config={"action_kind": "op.nonexistent"}))
