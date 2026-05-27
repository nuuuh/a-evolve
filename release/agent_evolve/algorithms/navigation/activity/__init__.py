"""UML Activity Diagram framework for designing evolution systems.

This package provides a typed dataflow metamodel aligned with UML 2.5
Activity Diagrams.  Users compose evolution systems from typed
``ActivityNode`` instances wired together by ``ObjectFlow`` and
``ControlFlow``; the ``ActivityRuntime`` executes the resulting
``Activity`` (a UML-style blueprint).

Layered design (no layer imports from a layer above it):

    Layer 1   types.py, spec.py               (data only)
    Layer 2   pin.py, activity_node.py,
              action.py, call_activity.py,
              control.py, flow.py             (metamodel)
    Layer 3   registry.py, nodes/*.py         (concrete actions)
    Layer 4   validator.py, runtime.py,
              builder.py, exporters.py        (tooling)
    Layer 5   adapters.py                     (bridges to EvolutionTemplate)

Public API is re-exported here.  See ``README.md`` for the design
tutorial.
"""

from .builder import ActivityBuilder
from .exporters import to_json, to_mermaid, to_plantuml
from .pin import InputPin, OutputPin
from .registry import ActionRegistry, default_registry
from .runtime import ActivityRuntime, RunContext
from .spec import Activity, FlowSpec, NodeSpec, ParameterSpec
from .types import Type
from .validator import ActivityValidationError, validate

__all__ = [
    # Spec (Layer 1)
    "Activity",
    "FlowSpec",
    "NodeSpec",
    "ParameterSpec",
    "Type",
    # Metamodel (Layer 2)
    "InputPin",
    "OutputPin",
    # Registry (Layer 3)
    "ActionRegistry",
    "default_registry",
    # Tooling (Layer 4)
    "ActivityBuilder",
    "ActivityRuntime",
    "RunContext",
    "ActivityValidationError",
    "validate",
    "to_json",
    "to_mermaid",
    "to_plantuml",
    # Adapters (Layer 5)
    "ActivityTemplate",
]


# Lazy adapter imports to avoid pulling Layer 5 into every Layer-1 user.
def __getattr__(name: str):  # noqa: D401
    if name == "ActivityTemplate":
        from . import adapters

        return adapters.ActivityTemplate
    raise AttributeError(f"module 'activity' has no attribute {name!r}")
