"""Phase 2 tests — validator, runtime, exporters, builder.

Scenarios:
  1. Validator catches mismatched types, cycles, unwired required pins,
     missing sub-Activities, bad endpoints, Void violations on ControlFlow.
  2. Runtime executes a simple source → map → sink Activity.
  3. ExpansionRegion iterates (and parallels) a sub-Activity.
  4. CallActivity passes inputs to a sub-Activity and returns outputs.
  5. Mermaid and PlantUML exporters produce non-empty text.
"""

from __future__ import annotations

import pytest

from agent_evolve.algorithms.navigation.activity import (
    Activity,
    ActivityBuilder,
    ActivityRuntime,
    ActivityValidationError,
    FlowSpec,
    InputPin,
    NodeSpec,
    OutputPin,
    ParameterSpec,
    Type,
    default_registry,
    to_mermaid,
    to_plantuml,
    validate,
)
from agent_evolve.algorithms.navigation.activity.action import Action
from agent_evolve.algorithms.navigation.activity.registry import ActionRegistry


# ── Test actions ─────────────────────────────────────────────────────


class Source(Action):
    action_kind = "test.source"

    @classmethod
    def input_pins(cls, config=None):
        return []

    @classmethod
    def output_pins(cls, config=None):
        return [OutputPin(name="out", type=Type.STRING)]

    def execute(self, inputs, ctx):
        return {"out": self.config.get("value", "hello")}


class Upper(Action):
    action_kind = "test.upper"

    @classmethod
    def input_pins(cls, config=None):
        return [InputPin(name="text", type=Type.STRING)]

    @classmethod
    def output_pins(cls, config=None):
        return [OutputPin(name="out", type=Type.STRING)]

    def execute(self, inputs, ctx):
        return {"out": inputs["text"].upper()}


class Sink(Action):
    action_kind = "test.sink"

    @classmethod
    def input_pins(cls, config=None):
        return [InputPin(name="text", type=Type.STRING)]

    @classmethod
    def output_pins(cls, config=None):
        return [OutputPin(name="out", type=Type.STRING)]

    def execute(self, inputs, ctx):
        # Just echo so the caller can inspect.
        return {"out": inputs["text"]}


class Repeat(Action):
    action_kind = "test.repeat"

    @classmethod
    def input_pins(cls, config=None):
        return [InputPin(name="text", type=Type.STRING)]

    @classmethod
    def output_pins(cls, config=None):
        return [OutputPin(name="out", type=Type.STRING)]

    def execute(self, inputs, ctx):
        return {"out": inputs["text"] * int(self.config.get("times", 2))}


@pytest.fixture
def registry() -> ActionRegistry:
    r = ActionRegistry()
    for cls in (Source, Upper, Sink, Repeat):
        r.register(cls)
    return r


# ── Validator ────────────────────────────────────────────────────────


def test_validator_accepts_simple_pipeline(registry):
    act = (
        ActivityBuilder("ok")
        .action("s", "test.source", value="hi")
        .action("u", "test.upper")
        .object_flow("s.out", "u.text")
        .build(registry)
    )
    assert act.name == "ok"


def test_validator_rejects_type_mismatch(registry):
    # Wire a STRING output into a WORKSPACE parameter (no such node
    # exists, so simulate by wiring a STRING output into a wrong-typed
    # input on Upper via parameter).
    act = (
        ActivityBuilder("bad_types")
        .parameter("wksp", Type.WORKSPACE)
        .action("u", "test.upper")
        .object_flow("wksp", "u.text")
        .build_unchecked()
    )
    with pytest.raises(ActivityValidationError, match="type mismatch"):
        validate(act, registry)


def test_validator_rejects_unwired_required_pin(registry):
    act = (
        ActivityBuilder("unwired")
        .action("u", "test.upper")
        .build_unchecked()
    )
    with pytest.raises(ActivityValidationError, match="required input pin"):
        validate(act, registry)


def test_validator_rejects_cycle(registry):
    act = (
        ActivityBuilder("cyclic")
        .parameter("p", Type.STRING)
        .action("u1", "test.upper")
        .action("u2", "test.upper")
        .object_flow("u2.out", "u1.text")
        .object_flow("u1.out", "u2.text")
        .build_unchecked()
    )
    with pytest.raises(ActivityValidationError, match="Cycle"):
        validate(act, registry)


def test_validator_rejects_unknown_sub_activity(registry):
    act = (
        ActivityBuilder("missing_sub")
        .node("c", "CallActivity", activity="ghost")
        .build_unchecked()
    )
    with pytest.raises(ActivityValidationError, match="ghost"):
        validate(act, registry)


def test_validator_rejects_control_flow_on_typed_pin(registry):
    # ControlFlow is only legal between Void pins.
    act = (
        ActivityBuilder("bad_control")
        .action("s", "test.source")
        .action("u", "test.upper")
        .control_flow("s.out", "u.text")
        .build_unchecked()
    )
    with pytest.raises(ActivityValidationError, match="ControlFlow"):
        validate(act, registry)


# ── Runtime: simple linear flow ──────────────────────────────────────


def test_runtime_linear_pipeline(registry):
    act = (
        ActivityBuilder("pipe")
        .action("s", "test.source", value="abc")
        .action("u", "test.upper")
        .action("r", "test.repeat", times=3)
        .object_flow("s.out", "u.text")
        .object_flow("u.out", "r.text")
        .build(registry)
    )
    runtime = ActivityRuntime(registry)
    outputs = runtime.run(act, bindings={})
    assert outputs["s.out"] == "abc"
    assert outputs["u.out"] == "ABC"
    assert outputs["r.out"] == "ABCABCABC"


def test_runtime_uses_activity_parameter(registry):
    act = (
        ActivityBuilder("echo")
        .parameter("msg", Type.STRING)
        .action("u", "test.upper")
        .object_flow("msg", "u.text")
        .build(registry)
    )
    runtime = ActivityRuntime(registry)
    outputs = runtime.run(act, bindings={"msg": "hello"})
    assert outputs["u.out"] == "HELLO"


# ── Runtime: CallActivity ────────────────────────────────────────────


def test_runtime_call_activity_returns_outputs(registry):
    inner = (
        ActivityBuilder("inner")
        .parameter("txt", Type.STRING, direction="in")
        .parameter("upped", Type.STRING, direction="out")
        .action("u", "test.upper")
        .object_flow("txt", "u.text")
        .object_flow("u.out", "upped")
        .build(registry)
    )

    outer = (
        ActivityBuilder("outer")
        .parameter("payload", Type.STRING)
        .node("c", "CallActivity", activity="inner")
        .object_flow("payload", "c.txt")
        .sub_activity("inner", inner)
        .build(registry)
    )

    runtime = ActivityRuntime(registry)
    outputs = runtime.run(outer, bindings={"payload": "loud"})
    assert outputs["c.upped"] == "LOUD"


# ── Runtime: ExpansionRegion iteration ───────────────────────────────


def test_runtime_expansion_region_iterates(registry):
    inner = (
        ActivityBuilder("one")
        .parameter("item", Type.STRING, direction="in")
        .parameter("upper", Type.STRING, direction="out")
        .action("u", "test.upper")
        .object_flow("item", "u.text")
        .object_flow("u.out", "upper")
        .build(registry)
    )

    outer = (
        ActivityBuilder("loop")
        .parameter("words", Type.STRING_LIST)
        .node("expand", "ExpansionRegion",
              activity="one", item_param="item", result_param="upper")
        .object_flow("words", "expand.items")
        .sub_activity("one", inner)
        .build(registry)
    )

    runtime = ActivityRuntime(registry)
    outputs = runtime.run(outer, bindings={"words": ["a", "bc", "def"]})
    assert outputs["expand.results"] == ["A", "BC", "DEF"]


def test_runtime_expansion_region_parallel_mode(registry):
    inner = (
        ActivityBuilder("one")
        .parameter("item", Type.STRING, direction="in")
        .parameter("upper", Type.STRING, direction="out")
        .action("u", "test.upper")
        .object_flow("item", "u.text")
        .object_flow("u.out", "upper")
        .build(registry)
    )

    outer = (
        ActivityBuilder("loop_par")
        .parameter("words", Type.STRING_LIST)
        .node("expand", "ExpansionRegion",
              activity="one", item_param="item", result_param="upper",
              mode="parallel")
        .object_flow("words", "expand.items")
        .sub_activity("one", inner)
        .build(registry)
    )

    runtime = ActivityRuntime(registry)
    outputs = runtime.run(outer, bindings={"words": ["x", "yy", "zzz", "q"]})
    assert outputs["expand.results"] == ["X", "YY", "ZZZ", "Q"]


# ── Exporters ────────────────────────────────────────────────────────


def test_mermaid_contains_nodes(registry):
    act = (
        ActivityBuilder("demo")
        .action("s", "test.source")
        .action("u", "test.upper")
        .object_flow("s.out", "u.text")
        .build(registry)
    )
    out = to_mermaid(act)
    assert "flowchart TD" in out
    assert "test.source" in out
    assert "test.upper" in out


def test_plantuml_contains_start_stop(registry):
    act = (
        ActivityBuilder("demo")
        .action("s", "test.source")
        .build(registry)
    )
    out = to_plantuml(act)
    assert "@startuml" in out
    assert "@enduml" in out
    assert "start" in out
    assert "stop" in out
