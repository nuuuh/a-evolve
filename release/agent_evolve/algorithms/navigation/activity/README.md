# Activity — design evolution systems as UML Activity Diagrams

This package provides a small framework for **designing** evolution
systems — picking inputs, dropping nodes, wiring them together — and
plugging the resulting design into the existing navigation engine.

It is a peer of `templates/`, `roles.py`, `orchestration.py` inside
`agent_evolve/algorithms/navigation/`. It does not change any existing
code path; it exposes a new, optional design surface.

## The three-step design process

1. **Declare parameters.** Pick what flows into the design: a workspace,
   a git tree, a batch of results, a config.
2. **Drop nodes.** Instantiate Actions (atomic ops) and control-flow
   nodes (Decision, Fork, ExpansionRegion, …) for every step.
3. **Wire outputs to inputs.** Every wire is typechecked.

## UML alignment

| UML 2.5 concept | This framework | Role |
|---|---|---|
| Activity | `Activity` | The blueprint (also the JSON spec) |
| ActivityParameterNode | `ParameterSpec` | Typed input/output of an Activity |
| ActivityNode | `ActivityNode` (ABC) | Any node kind |
| OpaqueAction | `Action` | A unit of work (single typed function) |
| CallBehaviorAction | `CallActivity` | Invokes a sub-Activity |
| InputPin / OutputPin | `InputPin`, `OutputPin` | Typed ports on a node |
| ObjectFlow | `FlowSpec(kind="ObjectFlow")` | Typed wire |
| ControlFlow | `FlowSpec(kind="ControlFlow")` | Void ordering wire |
| DecisionNode + MergeNode | `DecisionNode` | `if` branching |
| ForkNode, JoinNode | `ForkNode`, `JoinNode` | Parallel fan-out / fan-in |
| ExpansionRegion | `ExpansionRegion` | `for each` over a collection |
| InitialNode / ActivityFinalNode | `InitialNode`, `FinalNode` | Entry / exit markers |
| Classifier (type) | `Type` enum | The port type |

Every spec file round-trips to UML Activity Diagram notation via
`to_plantuml(activity)` — open the output in any UML editor (draw.io,
Enterprise Architect, the PlantUML server) for visual inspection.

## Types on wires

The enum `Type` enumerates every kind of data that can flow between
nodes:

```
TrajectoriesFolder  GitTree        Workspace          BatchResults
Config              PromptText     LLMResponse        Plan
BranchSpec          BranchSpecList WorkspaceSnapshot  MutationReport
Boolean  String  StringList  Integer  Void
```

## Node catalog

Auto-discoverable via `default_registry().list_actions()`. Current
built-ins (grouped by module):

### `nodes/workspace.py`
- `op.snapshot_workspace`     — capture pre-mutation state
- `op.detect_mutations`       — compare to a snapshot
- `op.clear_drafts`           — drop `_drafts/`

### `nodes/prompt.py`
- `op.build_evolution_prompt`   — the standard A-Evolve prompt
- `op.append_branching_section` — add the branching stanza
- `op.prepend_plan_context`     — prepend a plan context block
- `op.build_analyze_plan_prompt` — the analyst's batch-analysis prompt

### `nodes/llm.py`
- `op.call_llm`        — sandboxed evolver call (bash tool access)
- `op.call_llm_simple` — single-turn completion (no tools)
- `op.parse_plan`      — extract a Plan from an LLMResponse

### `nodes/git.py`
- `op.git_commit`                — commit + tag (templated messages)
- `op.git_checkout`              — checkout a branch
- `op.git_list_branches`         — list non-main branches
- `op.git_discover_new_branches` — branches added since a snapshot
- `op.git_register_branches`     — attach discovered branches to the tree
- `op.git_tag_branch_heads`      — tag each branch head per evo cycle
- `op.git_realise_branches`      — sanitise + create from a BranchSpecList
- `op.git_rebase_branches`       — rebase each non-main branch onto main

### `nodes/navigation.py`
- `op.read_branch_leaves`    — summarise every branch's workspace
- `op.extract_plan_branches` — pull the `branches` list out of a Plan
- `op.load_routing_history`  — read the routing log JSONL

### `nodes/agents/*.py` — pre-built sub-Activities
- `build_analyst_activity()`  — build prompt → call LLM → parse plan
- `build_evolver_activity()`  — snapshot → prompt → call LLM → diff
- `build_planner_activity()`  — analyst + extract branches for fan-out
- `build_critic_activity()`   — placeholder for a future critic role

## Two ways to design

### 1. Fluent Python builder

```python
from agent_evolve.algorithms.navigation.activity import (
    ActivityBuilder, Type,
)

activity = (
    ActivityBuilder("my_evolution")
    .parameter("workspace", Type.WORKSPACE)
    .parameter("cfg",       Type.CONFIG)
    .parameter("batch",     Type.BATCH_RESULTS)
    .parameter("evo_number", Type.INTEGER)
    .action("snap",   "op.snapshot_workspace")
    .action("prompt", "op.build_evolution_prompt")
    .action("call",   "op.call_llm")
    .action("diff",   "op.detect_mutations")
    .object_flow("workspace", "snap.workspace")
    .object_flow("workspace", "prompt.workspace")
    .object_flow("batch",     "prompt.batch_results")
    .object_flow("cfg",       "prompt.config")
    .object_flow("evo_number", "prompt.evo_number")
    .object_flow("prompt.text", "call.prompt")
    .object_flow("workspace",   "call.workspace")
    .object_flow("cfg",         "call.config")
    .object_flow("workspace",   "diff.workspace")
    .object_flow("snap.snapshot", "diff.snapshot")
    .build()   # runs validator
)
```

### 2. JSON spec

```python
import json
from agent_evolve.algorithms.navigation.activity import Activity

activity = Activity.from_json(json.load(open("my_spec.json")))
```

The two are equivalent — `activity.to_json()` round-trips.

## Running a design

```python
from agent_evolve.algorithms.navigation.activity import (
    ActivityRuntime, default_registry,
)

runtime = ActivityRuntime(default_registry())
outputs = runtime.run(activity, bindings={
    "workspace": my_workspace,
    "cfg":       my_config,
    "batch":     my_batch_results,
    "evo_number": 3,
})
```

## Plugging into `NavigationEngine`

```python
from agent_evolve.algorithms.navigation.activity import ActivityTemplate
from agent_evolve.algorithms.navigation.engine import NavigationEngine

template = ActivityTemplate(activity, engine=...)
engine = NavigationEngine(config, template=template)
```

The engine calls `template.execute(...)` during `evolve_with_navigation`
and the Activity is executed. No edit to the engine itself.

## Planner → spawns → N sub-agents

The "planner spawns any number of sub-agents" pattern is a single
`ExpansionRegion` pointing at a sub-Activity:

```python
(ActivityBuilder("planner_spawns")
    .parameter("workspace", Type.WORKSPACE)
    .parameter("batch",     Type.BATCH_RESULTS)
    .parameter("git",       Type.GIT_TREE)
    .parameter("cfg",       Type.CONFIG)
    .parameter("evo_number", Type.INTEGER)

    # Planner produces a Plan + a BranchSpecList.
    .node("plan", "CallActivity", activity="planner")

    # One evolver per branch, in parallel.
    .node("evolve_each",
          "ExpansionRegion",
          activity="evolve_one_branch",
          mode="parallel",
          item_param="item",
          result_param="report")

    .object_flow("batch",            "plan.batch")
    .object_flow("git",              "plan.git")
    .object_flow("cfg",              "plan.cfg")
    .object_flow("plan.branches",    "evolve_each.items")
    .object_flow("workspace",        "evolve_each.workspace")
    .object_flow("batch",            "evolve_each.batch")
    .object_flow("cfg",              "evolve_each.cfg")
    .object_flow("evo_number",       "evolve_each.evo_number")

    .sub_activity("planner",          build_planner_activity())
    .sub_activity("evolve_one_branch", build_evolver_activity())
    .build()
)
```

If the planner emits 5 branches, the runtime invokes
`evolve_one_branch` five times (in parallel), collecting each
`MutationReport` into `evolve_each.results`.

## Visualising

```python
from agent_evolve.algorithms.navigation.activity import to_mermaid, to_plantuml

print(to_mermaid(activity))    # renders in GitHub READMEs
print(to_plantuml(activity))   # open in any UML editor
```

## Layered architecture

The framework enforces a strict import layering (checked by
`tests/test_activity_layering.py`):

```
Layer 5  adapters.py, __init__.py, specs/*.py, nodes/agents/*.py
Layer 4  validator.py, runtime.py, builder.py, exporters.py
Layer 3  registry.py, nodes/{workspace,prompt,llm,git,navigation}.py
Layer 2  pin.py, activity_node.py, action.py, call_activity.py, control.py, flow.py
Layer 1  types.py, spec.py
```

Every file may only import from its own layer or below. A CI test
fails on violations. This keeps the metamodel free of adapter and
tooling dependencies, and keeps Actions self-contained (no Action
imports another Action).

## Reference specs — 1:1 with current templates

Two shipped activities in `specs/` reproduce the current templates:

- `specs/inline.py` + `specs/inline.json` ≡ `InlineTemplate.execute()`
- `specs/plan_driven.py` + `specs/plan_driven.json` ≡
  `OrchestratedTemplate` + `PlanDrivenOrchestrator`

The plan-driven spec illustrates the payoff: the snapshot → call-LLM →
diff → commit pattern, previously duplicated in three files, appears
exactly **once** as the `evolve_one_branch` sub-Activity and is
referenced by both the main-branch `CallActivity` and the per-branch
`ExpansionRegion`.

## Future GUI

The node registry exposes enough schema (`registry.list_actions()`
plus each class's `input_pins()` / `output_pins()`) to drive a visual
canvas. A future GUI would:

- Use `registry.list_kinds()` + per-class pin declarations to build a
  palette.
- Use the JSON spec as canvas state (load/save).
- Run `validator.validate()` on every wire edit to give live red-line
  feedback.

No changes to this package are needed when/if a GUI is added —
everything it needs already exists as inspectable Python API.
