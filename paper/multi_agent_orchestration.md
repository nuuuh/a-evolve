# Multi-Agent Orchestration for Evolution

Design document for the multi-agent orchestration framework under
`agent_evolve/algorithms/navigation/`. This framework makes the evolution
process itself multi-agent, addressing C3 (evolver capability bottleneck)
from `challenges.md`.

---

## System Flow Map

Four LLM-powered agents across two phases. **Phase 1 (inference)** is
shared with the inline navigation pipeline — the same navigator routes
each task to a branch, and the same solver runs on the selected branch.
**Phase 2 (evolution)** is where multi-agent differs: an Analyst LLM
classifies batch failures into a structured plan, then the Evolver LLM
executes that plan — first on main, then on each branch the plan
nominates — via per-branch `ExpansionRegion` calls into the shared
`evolve_one_branch` sub-Activity.

```
===================================================================
  PHASE 1: INFERENCE                 PHASE 2: EVOLUTION (orchestrated)
===================================================================

 Batch of tasks                     Batch results
      |                             (trajectories)
      v                                  |
+-----------+                             v
| NAVIGATOR | -- routes each -->  +------------------+
|   (LLM)   |    task to best      |     ANALYST      |
|           |    branch            |      (LLM)       |
| Reads each|                      |                  |
| branch's  |                      | Pure analysis:   |
| workspace |                      | - read batch     |
| (prompt,  |                      | - classify fail- |
| skills,   |                      |   ures as        |
| tools,    |                      |   stationary or  |
| README)   |                      |   non-stationary |
| via git   |                      | - emit JSON plan |
| show      |                      |   {main_evo,     |
+-----------+                      |    branches: []} |
      |                            +------------------+
      v                                   |
+-----------+                         (Plan)
|  SOLVER   |                              |
|   (LLM)   |                              v
|           |                     +------------------+
| Runs on   |                     |     EVOLVER      |
| the branch|                     |      (LLM)       |
| workspace |                     |                  |
| assigned  |                     | Runs branch_cycle|
| by the    |                     | sub-Activity on  |
| navigator |                     | main with plan   |
|           |                     | context, then    |
|           |                     | ONCE PER planned |
|           |                     | branch via       |
|           |                     | ExpansionRegion. |
|           |                     |                  |
|           |                     | Each run: snap → |
|           |                     |   build_prompt → |
|           |                     |   prepend_plan → |
|           |                     |   call_llm →     |
|           |                     |   diff → clear   |
|           |                     |   (in sandbox)   |
+-----------+                     +------------------+
      |                                   |
      v                             pipeline applies:
 task results                       - commit main + tag
                                    - rebase branches
                                    - realise planned
                                      branches in git
                                    - commit each branch
                                      (evo-{N}-{slug})
                                    - register in
                                      StrategyTree
                                          |
                                          v
                            +-------------------+
                            |   STRATEGY TREE    |
                            |                    |
                            |  main o--o--o--*   |
                            |            \       |
                            |  branch/A   o--o   |
                            |               \    |
                            |  branch/B      o   |
                            +--------+-----------+
                                     |
                                next cycle
```

**Agent roles (orchestrated mode):**

| Agent | Phase | Role | Has tools? |
|-------|-------|------|:----------:|
| **Navigator** | Inference | Routes each task to the best-fit branch by reading workspace content from all branches (same as inline mode) | No |
| **Solver** | Inference | Solves tasks on the branch assigned by the navigator (same as inline mode) | Yes (benchmark tools) |
| **Analyst** | Evolution | Single LLM call — no sandbox, no tools. Classifies patterns as stationary (main) vs non-stationary (branch), emits a JSON plan | No |
| **Evolver** | Evolution | One LLM call per branch in the plan (main plus each specialized branch). Sandboxed with bash + git. Driven by the `evolve_one_branch` Activity | Yes (bash + git in sandbox) |

**Relationship to inline navigation:**

The inference phase (Navigator + Solver) is shared with the inline flow
in `navigation_implementation.md`. The evolution phase is where the two
templates diverge:

| Template | Evolution calls per cycle | Planning stage | Per-branch stage |
|---|---|---|---|
| `InlineTemplate` (H5)       | 1 LLM call                | Folded into the single evolver call (branching section in prompt) | Evolver creates branches directly via git in sandbox |
| `OrchestratedTemplate` (H5_multi) | 1 analyst + 1 main + N branches | Dedicated Analyst LLM call emits a structured plan | Dedicated Evolver call per planned branch, guided by plan context |

Both modes reuse the same `branch_cycle` Activity
(`activity/specs/plan_driven.py::_build_branch_cycle_activity`) for the
snapshot → prompt → LLM → diff → clear pipeline. Multi-agent orchestration
is the only thing that changes — the activity framework, navigation core,
and solver path are all shared.

---

## 1. Motivation

### The Single-Evolver Bottleneck (C3)

Standard A-Evolve uses a single LLM call for evolution: one prompt that
must simultaneously analyze batch failures, decide what to change, and
execute mutations in a sandboxed workspace. This conflates three distinct
cognitive functions:

```
Single Evolver (current)
+------------------------------------------------------------+
|                                                            |
|  1. Analyze failures  (what went wrong?)                   |
|  2. Classify patterns (stationary vs non-stationary?)      |
|  3. Plan mutations    (what to change on which branch?)    |
|  4. Execute mutations (edit files in sandbox)              |
|                                                            |
|  All in ONE LLM call with ONE system prompt                |
+------------------------------------------------------------+
```

Problems with this approach:

1. **Cognitive overload**: A single prompt asking the LLM to analyze, classify,
   plan, and execute produces shallow analysis because most token budget goes
   to tool-use for file editing.

2. **No specialization**: Analysis (pure reasoning, no tools needed) and mutation
   (tool-heavy, sandbox access) have different optimal configurations (temperature,
   max tokens, system prompt, tool access).

3. **No feedback loops**: The evolver cannot review its own mutations or iterate
   based on critique.

4. **Rigid pipeline**: Adding new cognitive functions (critique, verification,
   meta-analysis) requires rewriting the evolution prompt rather than composing
   independent agents.

### Multi-Agent as Decomposition

The orchestration framework decomposes evolution into **roles** -- specialist
agents with distinct cognitive functions -- coordinated by an **orchestrator**
that decides the collaboration strategy:

```
Multi-Agent Evolution
+------------------------------------------------------------+
|                                                            |
|  Analyst  ->  Evolver  ->  (Critic)  ->  (Verifier)       |
|  (analyze)    (mutate)     (review)      (test)            |
|                                                            |
|  Each role: own system prompt, own tools, own config       |
|  Orchestrator: decides sequence, routing, iteration        |
+------------------------------------------------------------+
```

This is orthogonal to navigation (branching + task routing). Navigation solves
C1+C2 (distribution shift + coupled experience). Multi-agent solves C3 (evolver
capability). They compose independently:

| Experiment | Navigation | Multi-Agent | What it tests |
|---|:---:|:---:|---|
| H1 | No | No | Single-path evolution |
| H5 | Yes | No | Value of branching |
| H5_multi | Yes | Yes | Value of multi-agent orchestration |

---

## 2. Theoretical Framework

### Inspiration: Puppeteer Paradigm

The framework draws from the Puppeteer paradigm for multi-agent systems
(Dang et al., 2025), which formalizes multi-agent collaboration as:

- **Agent-as-tuple**: Each agent = (model, reasoning_pattern, tools)
- **Shared state S_t**: Mutable context accumulated across agent invocations
- **Orchestration policy**: Selects next agent and routing based on S_t
- **Emergent topologies**: Sequential, cyclic, branching, or dynamic routing

Applied to evolution:

| Puppeteer Concept | Evolution Mapping |
|---|---|
| Agent | `EvolutionRole` (analyst, evolver, critic, ...) |
| Model | LLM provider (shared via engine, or role-specific) |
| Reasoning pattern | Role's system prompt and cognitive function |
| Tools | Sandbox bash (evolver), none (analyst), test runner (verifier) |
| Shared state S_t | `EvolutionState` (workspace, tree, batch results, role outputs) |
| Orchestration policy | `Orchestrator.run()` (sequential, plan-driven, cyclic, ...) |
| Emergent topology | Determined by orchestrator implementation |

### Design Principles

The framework follows `agent_evolve`'s established patterns:

1. **ABCs for extension points** -- `EvolutionRole` and `Orchestrator` are abstract,
   like `EvolutionEngine` in `engine/base.py`. New roles and orchestration strategies
   are added by subclassing.

2. **Shared state via dataclass** -- `EvolutionState` bundles all context, like
   `Observation` and `StepResult` in the engine layer. Roles read from and write
   to this shared state.

3. **Composition over inheritance** -- `NavigationEngine` *has-an* optional
   `Orchestrator`, not *is-an* orchestrator. This keeps navigation and
   multi-agent independently toggleable.

4. **Concrete implementations import from abstract files** -- `plan_driven.py`
   imports from `roles.py` + `orchestration.py`. Adding a new orchestrator means
   adding one file, not modifying existing ones.

---

## 3. Abstract Types

### EvolutionRole

```python
# roles.py

class EvolutionRole(ABC):
    """A specialist agent in multi-agent evolution.

    Each role represents a cognitive function: analysis, mutation,
    critique, planning, etc. Roles are composable -- an orchestrator
    decides which to invoke and in what order.
    """
    name: str = ""

    @abstractmethod
    def execute(self, state: EvolutionState) -> RoleOutput:
        """Execute this role given the current shared evolution state."""

    @property
    def description(self) -> str:
        """Human-readable description of what this role does."""
        return ""
```

Each role receives the full `EvolutionState` and can read prior roles' outputs
from `state.role_outputs`. This enables data flow between roles without
hard-coding dependencies.

`RoleOutput` is a lightweight container:

```python
@dataclass
class RoleOutput:
    content: Any              # role-specific (plan dict, mutation summary, ...)
    metadata: dict = field()  # token usage, timing, trajectory data
```

### EvolutionState

```python
# orchestration.py

@dataclass
class EvolutionState:
    """Shared mutable context for all roles in one evolution cycle.

    Analogous to the Puppeteer's global state S_t.
    """
    workspace: AgentWorkspace          # mutable file-system workspace
    tree: StrategyTree                 # branch structure + routing history
    batch_results: list[dict]          # task results from latest batch
    routing_history: list[dict]        # historical routing decisions
    cycle_number: int                  # current evolution cycle index
    role_outputs: dict[str, RoleOutput] = field(default_factory=dict)
```

The `role_outputs` dict accumulates outputs as the orchestrator invokes roles.
Each role can read prior outputs to inform its execution -- this is the
inter-role communication channel.

### Orchestrator

```python
# orchestration.py

class Orchestrator(ABC):
    """Decides how evolution roles collaborate during a cycle.

    Possible strategies:
    - Sequential: fixed pipeline (analyze -> evolve -> critique)
    - Plan-driven: analyst produces plan, evolver executes per-branch
    - Dynamic: learned policy selects next role
    - Cyclic: roles iterate until convergence
    """
    @abstractmethod
    def run(self, roles: dict[str, EvolutionRole],
            state: EvolutionState) -> OrchestrationResult:
        """Orchestrate one evolution cycle across roles."""

    @property
    def name(self) -> str:
        return self.__class__.__name__
```

### OrchestrationResult

```python
# orchestration.py

@dataclass
class OrchestrationResult:
    """Result of one orchestrated evolution cycle."""
    mutated: bool                              # did workspace change?
    summary: str                               # human-readable summary
    plan: dict = field(default_factory=dict)    # structured plan (if any)
    branches: list[dict] = field()             # branch decisions for engine
    trajectory: list[dict] = field()           # step-by-step log
    metadata: dict = field(default_factory=dict)
```

The `branches` field carries branch creation/update decisions back to the engine.
The engine (not the orchestrator) handles git operations -- this separation keeps
orchestration logic git-agnostic.

---

## 4. Concrete Roles

### AnalystRole

Classifies batch failures as stationary (domain-generalizable) or
non-stationary (distribution shift). Produces a structured evolution plan.

```
Input:  EvolutionState (batch_results, routing_history, branch names)
Output: RoleOutput(content=plan_dict)

plan_dict = {
    "summary": "high-level analysis",
    "main_evolution": {
        "description": "stationary improvements for main",
        "insights": ["..."],
        "task_ids": ["..."]
    },
    "branches": [
        {"name": "branch/...", "description": "...",
         "evolution_guidance": "...", "task_ids": ["..."]}
    ]
}
```

Properties:
- **No tools**: Pure reasoning -- no sandbox access needed.
- **Low temperature**: Analytical classification benefits from deterministic output.
- **System prompt**: `ANALYZE_PLAN_SYSTEM_PROMPT` -- meta-learning strategist framing.
- **Graceful fallback**: If LLM fails, returns default plan routing everything to main.

### EvolverRole

Mutates workspace artifacts (prompts, skills, memory, tools) via sandboxed
LLM execution. Can operate on main or a specific branch.

```
Input:  EvolutionState (workspace, batch_results, role_outputs["analyst"])
Output: RoleOutput(content={"mutated": bool}, metadata={"conversation": [...]})
```

Properties:
- **Has tools**: Docker sandbox with bash access to workspace filesystem.
- **Plan-aware**: Reads analyst output from `state.role_outputs["analyst"]` and
  prepends plan context to the standard evolution prompt.
- **Config-driven**: Respects `evolve_prompts`, `evolve_skills`, `evolve_memory`,
  `evolve_tools`, `evolve_infra` flags.

### Future Roles (Not Yet Implemented)

| Role | Cognitive Function | Tools | When to Add |
|---|---|---|---|
| **CriticRole** | Reviews evolver mutations for quality/safety | Diff viewer, test runner | When mutation quality variance is high |
| **VerifierRole** | Runs smoke tests on mutated workspace | Sandbox bash | When regressions from mutations are frequent |
| **MetaAnalystRole** | Analyzes evolution trajectory across cycles | Read-only workspace | When long-horizon evolution patterns matter |
| **NavigatorTunerRole** | Optimizes routing policy from outcomes | Routing log | When routing accuracy needs improvement |

Adding a new role requires:
1. Subclass `EvolutionRole` in `roles.py` (or a new file)
2. Implement `execute(state) -> RoleOutput`
3. Register in `_build_roles()` in `engine.py`
4. Reference in the orchestrator's `run()` method

---

## 5. Concrete Orchestrator: PlanDrivenOrchestrator

The first (and currently only) concrete orchestrator. Refactored from the
original `NavigationEngine.evolve_with_navigation()` 3-step pipeline.

### Pipeline

```
+------------------------------------------------------------------+
|  PlanDrivenOrchestrator.run(roles, state)                        |
|                                                                   |
|  Step 1: analyst.execute(state)                                   |
|           -> plan = {summary, main_evolution, branches}            |
|           -> state.role_outputs["analyst"] = analysis              |
|                                                                   |
|  Step 2: evolver.execute(state)                                   |
|           -> reads analyst plan from state.role_outputs            |
|           -> mutates workspace (main branch)                       |
|           -> state.role_outputs["evolver_main"] = result           |
|                                                                   |
|  Return: OrchestrationResult                                      |
|           mutated = main_result.mutated                            |
|           plan = analyst.plan                                      |
|           branches = plan["branches"]  (for engine to apply)       |
|           trajectory = [{analyze_and_plan}, {deepen_main}]         |
+------------------------------------------------------------------+
```

Note: Step 3 (branch evolution) is handled by the engine after
`Orchestrator.run()` returns, because it involves git operations
(checkout, create branch, commit) that the orchestrator doesn't manage.

### LLM Calls

| Step | Role | System Prompt | Tools | Temperature |
|---|---|---|---|---|
| 1 | Analyst | `ANALYZE_PLAN_SYSTEM_PROMPT` | None | 0.0 |
| 2 | Evolver (main) | Standard evolution + plan context | Sandbox bash | config |
| 3+ | Evolver (per branch) | Branch evolution + plan context | Sandbox bash | config |

Total per cycle: **2 + N** (where N = number of branches recommended by analyst).

Compare to inline mode (H5): **1 + N** (evolver does analysis and mutation together).

### Separation of Concerns

```
PlanDrivenOrchestrator           NavigationEngine._evolve_orchestrated()
(orchestration logic)            (git + persistence logic)

analyst.execute()           -->
evolver.execute()           -->
return OrchestrationResult  -->  vc.commit(main)
                                 vc.rebase_branch() for each existing branch
                                 for each branch in result.branches:
                                     vc.create_branch() or checkout
                                     _execute_plan_step() with plan context
                                     vc.commit(branch)
                                 vc.checkout("main")
                                 return {evo_number, mutated, plan, branches, trajectory}
```

The orchestrator is git-agnostic. It coordinates roles and returns decisions.
The engine applies those decisions to the git tree.

---

## 6. Orchestration Topologies

The abstract framework supports multiple orchestration topologies. The
`Orchestrator.run()` method has full control over role invocation order,
iteration, and routing.

### Sequential (PlanDrivenOrchestrator)

```
analyst -> evolver -> done
```

Fixed pipeline. Each role runs once. Simple and predictable.

### Cyclic (future: CyclicOrchestrator)

```
analyst -> evolver -> critic -+
                              |
              +-- if rejected -+
              |
              v
          evolver (retry with critic feedback)
              |
              v
          critic -> ... (until approved or max iterations)
```

Roles iterate until a quality threshold is met. The critic reviews mutations
and can request re-execution with feedback.

Implementation sketch:
```python
class CyclicOrchestrator(Orchestrator):
    def __init__(self, config, max_iterations=3):
        self.max_iterations = max_iterations

    def run(self, roles, state):
        analysis = roles["analyst"].execute(state)
        state.role_outputs["analyst"] = analysis

        for i in range(self.max_iterations):
            evolution = roles["evolver"].execute(state)
            state.role_outputs[f"evolver_{i}"] = evolution

            critique = roles["critic"].execute(state)
            state.role_outputs[f"critic_{i}"] = critique

            if critique.content.get("approved"):
                break
            # Critic feedback feeds into next evolver iteration

        return OrchestrationResult(...)
```

### Dynamic (future: DynamicOrchestrator)

```
state -> policy(state) -> next_role -> execute -> update state -> repeat
```

A learned or rule-based policy selects the next role based on current state.
Closest to the Puppeteer's original formulation.

Implementation sketch:
```python
class DynamicOrchestrator(Orchestrator):
    def __init__(self, config, policy):
        self.policy = policy  # state -> role_name

    def run(self, roles, state):
        for step in range(self.max_steps):
            next_role = self.policy(state)
            if next_role == "done":
                break
            result = roles[next_role].execute(state)
            state.role_outputs[f"{next_role}_{step}"] = result

        return OrchestrationResult(...)
```

### Parallel (future: ParallelOrchestrator)

```
analyst -+-> evolver_main
         +-> evolver_branch_A  (concurrent)
         +-> evolver_branch_B
```

Multiple roles execute concurrently on independent branches. Requires
careful state isolation (each branch evolver gets its own workspace copy).

---

## 7. Integration with NavigationEngine

### Composition Pattern

```python
# engine.py

class NavigationEngine(AEvolveEngine):
    def __init__(self, config, llm=None, orchestrator=None):
        super().__init__(config, llm)
        self.orchestrator = orchestrator  # None = inline, else multi-agent

    def evolve_with_navigation(self, workspace, batch_results, tree, ...):
        if self.orchestrator:
            return self._evolve_orchestrated(...)
        else:
            return self._evolve_inline(...)
```

The orchestrator is injected at construction time. The engine dispatches
based on its presence. This keeps the two modes (inline vs orchestrated)
cleanly separated.

### Role Construction

```python
# engine.py

def _build_roles(self):
    from .roles import AnalystRole, EvolverRole
    return {
        "analyst": AnalystRole(self.llm, self.config),
        "evolver": EvolverRole(self),  # gets engine reference for _run_llm
    }
```

Roles are constructed lazily when orchestration runs. The analyst gets direct
LLM access; the evolver gets the full engine for sandboxed execution.

### Config-Driven Instantiation

```python
# solve_all_with_evolution.py

orchestrator = None
orchestrator_type = config.extra.get("orchestrator", "")
if orchestrator_type == "plan_driven":
    from agent_evolve.algorithms.navigation.plan_driven import PlanDrivenOrchestrator
    orchestrator = PlanDrivenOrchestrator(config)

evolver = NavigationEngine(config, orchestrator=orchestrator)
```

The YAML config controls the orchestration strategy:

```yaml
# navigation only (H5)
navigation_enabled: true

# navigation + multi-agent (H5_multi)
navigation_enabled: true
orchestrator: plan_driven
```

Unknown YAML keys land in `config.extra` via `EvolveConfig.from_yaml()`.

---

## 8. Extending the Framework

### Adding a New Role

1. Define the role class:

```python
# roles.py (or a new file)

class CriticRole(EvolutionRole):
    """Reviews evolver mutations and provides quality feedback."""
    name = "critic"

    def __init__(self, llm, config):
        self.llm = llm
        self.config = config

    def execute(self, state):
        evolver_output = state.role_outputs.get("evolver_main")
        # ... review mutations, produce critique ...
        return RoleOutput(content={"approved": True, "feedback": "..."})
```

2. Register in `_build_roles()`:

```python
def _build_roles(self):
    from .roles import AnalystRole, EvolverRole, CriticRole
    return {
        "analyst": AnalystRole(self.llm, self.config),
        "evolver": EvolverRole(self),
        "critic": CriticRole(self.llm, self.config),
    }
```

3. Use in an orchestrator that expects it (e.g., `CyclicOrchestrator`).

### Adding a New Orchestrator

1. Create a new file (e.g., `cyclic.py`):

```python
# cyclic.py

from .orchestration import Orchestrator, EvolutionState, OrchestrationResult
from .roles import EvolutionRole

class CyclicOrchestrator(Orchestrator):
    """Analyst -> evolver -> critic loop until approved."""

    def __init__(self, config, max_iterations=3):
        self.config = config
        self.max_iterations = max_iterations

    def run(self, roles, state):
        # ... orchestration logic ...
        return OrchestrationResult(...)
```

2. Register in `solve_all_with_evolution.py`:

```python
elif orchestrator_type == "cyclic":
    from agent_evolve.algorithms.navigation.cyclic import CyclicOrchestrator
    orchestrator = CyclicOrchestrator(config)
```

3. Add YAML config:

```yaml
navigation_enabled: true
orchestrator: cyclic
```

No changes to `NavigationEngine`, `EvolutionRole`, or `Orchestrator` ABCs needed.

---

## 9. File Reference

| File | Contents |
|------|----------|
| `navigation/orchestration.py` | `EvolutionState`, `OrchestrationResult`, `Orchestrator` ABC |
| `navigation/roles.py` | `RoleOutput`, `EvolutionRole` ABC, `AnalystRole`, `EvolverRole` |
| `navigation/plan_driven.py` | `PlanDrivenOrchestrator` -- concrete sequential orchestrator |
| `navigation/engine.py` | `NavigationEngine._evolve_orchestrated()`, `_build_roles()` -- integration layer |
| `navigation/__init__.py` | Re-exports all public types |

### Dependency Graph

```
orchestration.py  <--  roles.py
       ^                  ^
       |                  |
  plan_driven.py     engine.py
       ^                  ^
       |                  |
  solve_all_with_evolution.py
```

`orchestration.py` and `roles.py` are mutually aware via `TYPE_CHECKING` imports
(no runtime circular dependency). Concrete implementations (`plan_driven.py`)
import from both. The engine imports lazily to avoid circular references.
