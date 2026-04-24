# Navigation Implementation: Decoupled Evolution with Agentic Navigation

Full implementation reference for Section 3 of `challenges.md`.

Navigation = branching. Git branches isolate strategies; the navigator routes
tasks to branches. Multi-agent orchestration is an optional composable layer.

**Architecture:**

| Experiment | Engine | Orchestrator | LLM calls/cycle |
|---|---|---|---|
| H0 | No evolution (baseline) | -- | 0 |
| H1 | `AEvolveEngine` (single-path) | -- | 1 |
| H5 | `NavigationEngine` (inline branching) | `None` | 1 (evolver does everything) |
| H5_multi | `NavigationEngine` (orchestrated) | `PlanDrivenOrchestrator` | 2+N branches |

---

## System Flow Map

### Default Mode: Inline Navigation (H5)

Three LLM-powered agents, two phases. The evolver handles everything in a single
LLM call -- it has full git access in the sandbox and creates/evolves branches
directly. The pipeline validates afterward.

```
===================================================================
  PHASE 1: INFERENCE                  PHASE 2: EVOLUTION (inline)
===================================================================

 Batch of tasks                     Batch results
      |                             (trajectories)
      v                                  |
+-----------+                            v
| NAVIGATOR | -- routes each -->  +------------------+
|   (LLM)   |    task to best     |    EVOLVER       |
|           |    branch            |     (LLM)        |
| Reads each|                     |                  |
| branch's  |                     | Single call:     |
| workspace |                     | 1. Evolve main   |
| (prompt,  |                     |    artifacts     |
| skills,   |                     | 2. git commit    |
| tools)    |                     | 3. If shift:     |
| via git   |                     |    git checkout  |
| show      |                     |    -b branch/x   |
+-----------+                     |    evolve branch |
      |                           |    git commit    |
      v                           | 4. git checkout  |
+-----------+                     |    main          |
|  SOLVER   |                     +------------------+
|   (LLM)   |                          |
|           |                     pipeline validates:
| Runs on   |                     - return to main
| the branch|                     - detect mutations
| workspace |                     - discover new branches
| assigned  |                     - register in StrategyTree
| by the    |                     - tag branch heads
| navigator |                          |
+-----------+                          v
      |                      +-------------------+
      v                      |   STRATEGY TREE    |
 task results                |                    |
                             |  main o--o--o--*   |
                             |            \       |
                             |  branch/A   o--o   |
                             |               \    |
                             |  branch/B      o   |
                             +--------+-----------+
                                      |
                                 next cycle
```

**Agent roles (inline mode):**

| Agent | Phase | Role | Has tools? |
|-------|-------|------|:----------:|
| **Navigator** | Inference | Routes each task to the best-fit branch by reading workspace content from all branches via `git show` | No |
| **Solver** | Inference | Solves tasks using the branch workspace (prompt, skills, tools) assigned by the navigator | Yes (benchmark tools) |
| **Evolver** | Evolution | Single LLM call: evolves main, creates/evolves branches directly via git commands, commits all work. Docker sandbox with bash + git access | Yes (bash + git in sandbox) |

---

## Workspace Layout

```
results/experiment/
+-- solver_workspace/              <- what the agent uses to solve tasks
|   +-- prompts/system.md
|   +-- skills/*/SKILL.md
|   +-- memory/*.jsonl
|   +-- tools/*.py                 <- sandbox tools (--network none)
|   +-- infra/                     <- infrastructure (framework-executed, has network)
|   |   +-- search_pipeline.py
|   |   +-- sandbox_setup.sh
|   |   +-- submit_handler.py
|   +-- .git/                      <- strategy tree (main + branches)
|
+-- routing_log.jsonl              <- append-only routing log (no ground-truth labels)
+-- tree_state.json                <- StrategyTree snapshot for resume
+-- <benchmark>/
    +-- evolution/
        +-- evo_1_trajectory.json          <- standard evolver trajectory
        +-- nav_evo_1_trajectory.json      <- navigation evolution trajectory
        +-- nav_evo_2_trajectory.json
        +-- ...
```

---

## Phase 1: Inference (Solving)

### 1.1 Startup

```
+------------------------------------------------------------------------+
|  STARTUP (solve_all_with_evolution.py)                                 |
|                                                                        |
|  --navigation flag?                                                    |
|       |                                                                |
|       +- NO  -> standard single-path A-Evolve (no branching)          |
|       |                                                                |
|       +- YES ->                                                        |
|            1. Set routing_log_path = out_dir/routing_log.jsonl         |
|            2. Load out_dir/tree_state.json if exists -> StrategyTree   |
|               (branches + metadata for resume)                         |
|               OR create empty StrategyTree()                           |
|            3. Check config.extra["orchestrator"] (legacy key):         |
|               - ""             -> NavigationEngine(config)             |
|                                     (mode="inline", default)           |
|               - "plan_driven"  -> NavigationEngine(config,             |
|                                     mode="orchestrated")               |
+------------------------------------------------------------------------+
```

### 1.2 F_Navigate: Route Tasks to Branches

F_Navigate reads the **actual workspace content** from each git branch (the "leaves"
of the strategy tree) so the LLM can make informed routing decisions based on what
each branch can actually do, not just its name.

```
          for each batch:
                |
                v
+------------------------------------------------------------------------+
|  F_NAVIGATE: Route each task to a branch                               |
|                                                                        |
|  if tree.branches is empty:                                            |
|       -> ALL tasks -> "main"                                           |
|                                                                        |
|  if tree has branches:                                                 |
|       for each task in batch:                                          |
|                                                                        |
|         1. Build rich task context:                                     |
|            Task ID: <t.id>                                             |
|            category: <metadata>                                        |
|            event: <metadata>                                           |
|            challenge: <metadata>                                       |
|            year: <metadata>                                            |
|            <full t.input -- no truncation>                              |
|                                                                        |
|         2. Read branch leaves via _read_branch_leaves():               |
|            For each branch (incl main), read via git show:             |
|              - README.md          (branch purpose & strategy)          |
|              - prompts/system.md  (strategy & approach)                |
|              - skills/ listing    (reusable capabilities)              |
|              - tools/registry.yaml (available tools)                   |
|                                                                        |
|         3. LLM routing decision:                                       |
|            NAVIGATE_SYSTEM_PROMPT + build_navigate_prompt()             |
|              Input: rich task context + full branch workspace content   |
|              Output: {"branch": "...", "confidence": ...,              |
|                       "reason": "..."}                                 |
|                                                                        |
|           branch_groups[branch].append(task)                           |
|           task_branches[task.id] = branch                              |
|                                                                        |
|       Update last_routed_cycle for each active branch                  |
+------------------------------------------------------------------------+
```

**Key design decisions:**

- **Full task input**: The navigator sees the complete task description, not a
  truncated version. Generic task descriptions (e.g., CTF challenges that all say
  "find the flag") are supplemented with structured metadata (category, event, year)
  to give the LLM enough signal to differentiate.

- **Branch leaf inspection**: The navigator reads actual workspace files from each
  branch via `VersionControl.show_file_at()` and `git ls-tree`. This means routing
  decisions are based on what each branch's workspace actually contains (its README,
  system prompt, skills, tools), not just the branch description.

- **Prompt structure**: Each branch is rendered as a full section under
  "Git Tree Leaves (Branch Workspaces)" with its system prompt, skills list, and
  tools registry. The LLM compares branches' actual capabilities against the task.

### 1.3 Per-Branch Solving

```
+------------------------------------------------------------------------+
|  PER-BRANCH SOLVING                                                    |
|                                                                        |
|  for branch_name, branch_tasks in branch_groups:                       |
|                                                                        |
|      1. git checkout <branch_name> in solver_workspace                 |
|         -> workspace now has main + branch-specific artifacts           |
|                                                                        |
|      2. agent.reload_from_fs()                                         |
|         -> loads prompts/skills/tools/memory from branch state          |
|                                                                        |
|      3. backend.build_prompts(agent, branch_tasks)                     |
|         -> generates solver prompts from branch's workspace             |
|                                                                        |
|      4. Submit all branch_tasks to thread/process pool                 |
|                                                                        |
|  After all groups submitted:                                           |
|      git checkout main; agent.reload_from_fs()                         |
|                                                                        |
|  Collect results from futures (with timeout handling)                   |
+------------------------------------------------------------------------+
```

### 1.4 Stats and Persistence

```
+------------------------------------------------------------------------+
|  STATS + PERSISTENCE (after solving, before evolution)                 |
|                                                                        |
|  Framework-internal (not visible to evolver):                          |
|      BranchInfo.total_tasks += 1                                       |
|      BranchInfo.total_passed += 1 (if success)                         |
|      RoutingEntry appended to strategy_tree.routing_log (in-memory)    |
|                                                                        |
|  Persisted to disk:                                                    |
|      Append to routing_log.jsonl (no score, no pass/fail):             |
|          {task_id, properties, branch, cycle}                          |
+------------------------------------------------------------------------+
```

---

## Phase 2: Evolution (Inline Mode -- Default)

The inline mode uses a single evolver LLM call. The evolver has full git access
in its Docker sandbox -- it evolves main, creates branches, and evolves branches
all by itself. No text-marker parsing, no separate LLM call per branch. After
the evolver finishes, the pipeline validates what happened.

```
+------------------------------------------------------------------------+
|  EVOLUTION TRIGGER                                                     |
|                                                                        |
|  Skip if: baseline mode, score above threshold, max_cycles reached,    |
|           or evo_start_cycle not yet reached                           |
|                                                                        |
|  if navigation_enabled:                                                |
|      -> engine.evolve_with_navigation(                                 |
|            solver_workspace, batch_results,                            |
|            strategy_tree, evo_cycle, routing_log_path)                 |
|                                                                        |
|      Delegates to the active EvolutionTemplate:                        |
|        mode="inline"       -> InlineTemplate.execute()                 |
|        mode="orchestrated" -> OrchestratedTemplate.execute()           |
|        template=<instance> -> <custom template>.execute()              |
|                                                                        |
|  else:                                                                 |
|      -> engine.evolve(workspace, evo_number)  [standard A-Evolve]      |
|                                                                        |
|  After evolve: save tree_state.json to out_dir/                        |
|  Save nav trajectory to evolution/nav_evo_{cycle}_trajectory.json      |
+------------------------------------------------------------------------+
```

### Evolver LLM Call (single call does everything)

```
+------------------------------------------------------------------+
|  EVOLVER (branching-aware, with sandbox + git access)            |
|                                                                   |
|  Snapshot: branches_before = set(vc.list_branches())              |
|  git checkout main                                                |
|                                                                   |
|  Build prompt:                                                    |
|    build_evolution_prompt(workspace, batch_results, ...)           |
|    + build_branching_section(tree, batch_results)                  |
|                                                                   |
|  The branching section includes:                                  |
|    - Current strategy tree (branch names, stats)                  |
|    - Batch summary (N tasks, M passed, K failed)                  |
|    - Branch exploration: git diff/show/log to inspect branches    |
|    - Git instructions: commit main, create/update branches,       |
|      evolve artifacts, create/update README.md, commit, return    |
|                                                                   |
|  LLM has full control via workspace_bash in Docker sandbox:       |
|    1. Explores existing branches (git diff, git show, git log)    |
|    2. Evolves main artifacts (prompts, skills, memory, tools)     |
|    3. git add -A && git commit -m "main: ..."                     |
|    4. If shift detected:                                          |
|       git checkout -b branch/regime-name main (or checkout        |
|         existing branch)                                          |
|       Evolves branch-specific artifacts                           |
|       Creates/updates README.md (purpose, strategy, key files)    |
|       git add -A && git commit -m "branch/...: ..."               |
|    5. Repeats step 4 for each branch needed                       |
|    5. git checkout main                                           |
+------------------------------------------------------------------+
```

**Key design: agentic branching**

The evolver creates and evolves branches directly via git commands in the
sandbox. No structured text output to parse, no fragile regex extraction,
no separate LLM call per branch. The evolver verifies its own work
(`git branch --list`, `git status`). If it never creates branches,
the result is identical to standard A-Evolve (H1) -- graceful degradation.

### Post-Hoc Validation (pipeline discovers what happened)

```
+------------------------------------------------------------------+
|  POST-HOC VALIDATION (after LLM finishes)                        |
|                                                                   |
|  1. Validate checkout state:                                      |
|     if evolver left workspace on a branch, return to main         |
|     (evolver should do this, but validate)                        |
|                                                                   |
|  2. Detect main mutations:                                        |
|     diff workspace state (prompt, skills, memory, tools)          |
|     before vs after                                               |
|                                                                   |
|  3. Safety commit:                                                |
|     git add -A && git commit (catch uncommitted main changes)     |
|     tag: evo-{N}-main                                             |
|                                                                   |
|  4. Discover new branches:                                        |
|     branches_after = set(vc.list_branches())                      |
|     new_branches = branches_after - branches_before               |
|                                                                   |
|  5. Register in StrategyTree:                                     |
|     for each new branch:                                          |
|       extract description from README.md (fall back to commit msg)|
|       tree.branches.append(BranchInfo(name, cycle, description))  |
|                                                                   |
|  6. Tag branch heads for traceability:                            |
|     for each branch with new commits since pre-evolution:         |
|       git tag evo-{N}-{branch-slug} <branch>                      |
+------------------------------------------------------------------+
```

### Persist and Return

```
+------------------------------------------------------------------------+
|  PERSIST + RETURN                                                      |
|                                                                        |
|  Log strategy tree visualization                                       |
|                                                                        |
|  Return from evolve_with_navigation():                                 |
|    {evo_number, mutated, plan: {}, branches, trajectory}               |
|                                                                        |
|  trajectory = [                                                        |
|    {step: "evolve_inline", mutated, new_branches: [...],               |
|     total_branches: [...], conversation}                               |
|  ]                                                                     |
|                                                                        |
|  Caller (solve_all_with_evolution.py):                                 |
|    - Saves tree_state.json to out_dir/                                 |
|    - Saves nav_evo_{cycle}_trajectory.json to evolution/               |
|    - git commit solver workspace                                       |
|    - Write history.jsonl                                               |
+------------------------------------------------------------------------+
```

---

## Optional: Multi-Agent Orchestration (H5_multi)

When `orchestrator: plan_driven` is set in the config YAML, evolution uses
the multi-agent orchestration framework. This adds a separate **Analyst** LLM
call before the evolver, decoupling failure analysis from workspace mutation.

```
===================================================================
   ORCHESTRATED EVOLUTION (H5_multi)
===================================================================

 Batch results
      |
      v
+-----------+
| ANALYST   | -- pure analysis, no sandbox
|   (LLM)   |
|           |
| Classifies|    ANALYZE_PLAN_SYSTEM_PROMPT
| patterns  |    + build_analyze_plan_prompt()
| as:       |
|  - statio-|    Output: JSON evolution plan
|    nary   |      {summary, main_evolution, branches}
|  - non-   |
|    statio-|
|    nary   |
+-----------+
      |
 evolution plan
      |
      v
+-----------+
| EVOLVER   | -- plan-guided, with sandbox
|   (LLM)   |
|           |
| Evolves   |    build_evolution_prompt()
| main with |    + plan context from analyst
| stationary|
| improve-  |
| ments     |
+-----------+
      |
 commit main, rebase branches
      |
      v
 for each branch in plan:
+-----------+
| EVOLVER   | -- plan-guided, with sandbox
|   (LLM)   |
|           |
| Evolves   |    build_evolution_prompt()
| branch    |    + plan context for this branch
| with spec-|
| ialized   |
| strategy  |
+-----------+
      |
 commit branch
```

### Framework Architecture

Orchestration is implemented as an `EvolutionTemplate` — the same plug-in
surface every evolution strategy uses — backed by the Activity runtime.
Extensibility comes from two places:

- **Custom templates** subclass `EvolutionTemplate` and implement `execute`.
- **Custom Activities** define new dataflow graphs using the node catalog
  (or new `Action` subclasses) and are wrapped by `ActivityTemplate`.

```
EvolutionTemplate (ABC)           Activity  (UML blueprint)
    |                                 ^
    +-- InlineTemplate                |
    +-- OrchestratedTemplate          |
    +-- ActivityTemplate(spec) -------+  (wraps any Activity)
    +-- (user-defined subclasses)
```

| Concept | File | Description |
|---|---|---|
| `EvolutionTemplate` | `templates/base.py` | ABC for evolution strategies: `execute(vc, workspace, batch_results, tree, evo_number, routing_log_path) -> dict` |
| `InlineTemplate` | `templates/inline.py` | Single sandboxed LLM call + agentic branching. Owns `build_branching_section`. Body = `activity/specs/inline.py`. |
| `OrchestratedTemplate` | `templates/orchestrated.py` | Plan-driven: analyst → main → per-branch. Owns `ANALYZE_PLAN_SYSTEM_PROMPT` and `build_analyze_plan_prompt`. Body = the `branch_cycle` Activity in `activity/specs/plan_driven.py`, plus `_realise_branches` and `_run_analyst` as private helpers. |
| `Activity`, `ActivityRuntime` | `activity/*` | UML-shaped dataflow graph + executor used to compose template bodies. |
| `ActivityTemplate` | `activity/adapters.py` | Wraps any `Activity` as an `EvolutionTemplate`. |

### Orchestration Flow (OrchestratedTemplate)

1. **Analyst step**: `_run_analyst()` — builds the analyze-plan prompt,
   calls `BedrockProvider.converse_loop()` (no tools), parses the JSON plan.
   Sanitises every branch name through `NavigationEngine._sanitize_branch_name`.
   Falls back to a default plan if the LLM is unavailable.

2. **Main step**: `_execute_plan_step(workspace, batch_results, evo_number,
   plan=plan, target="main")` — runs the `branch_cycle` Activity. The
   Activity's nodes are `op.snapshot_workspace → op.build_evolution_prompt
   → op.prepend_plan_context → op.call_llm → op.detect_mutations →
   op.clear_drafts`. If mutated, commits `evo-{N}-main` and rebases every
   non-main branch onto the new main.

3. **Per-branch step**: `_realise_branches` sanitises + creates branches in
   git and registers them in the `StrategyTree`. For each realised branch,
   `vc.checkout_branch(name)` → `_execute_plan_step(…, target=<branch>)` →
   commit `evo-{N}-{branch-slug}`.

4. **Return**: `{evo_number, mutated, plan, branches, trajectory}` with a
   trajectory capturing `analyze_and_plan`, optional `deepen_main`, and
   one `branch_evolution` entry per realised branch.

---

## Navigation Trajectory Recording

Each navigation evolution cycle produces a trajectory JSON file:

```
evolution/nav_evo_{cycle}_trajectory.json
```

### Inline Mode Trajectory

```json
[
  {
    "step": "evolve_inline",
    "mutated": true,
    "new_branches": ["branch/binary-analysis"],
    "total_branches": ["branch/binary-analysis", "branch/high-uncertainty"],
    "conversation": ["<LLM conversation turns>"]
  }
]
```

Single entry -- one LLM call does everything (main + branches).

### Orchestrated Mode Trajectory

```json
[
  {
    "step": "analyze_and_plan",
    "plan_summary": "high-level analysis of what happened",
    "prompt": "<full analyze-plan prompt sent to LLM>",
    "response": "<raw LLM response>"
  },
  {
    "step": "deepen_main",
    "mutated": true,
    "summary": "prompt, skills",
    "conversation": ["<LLM conversation turns>"]
  },
  {
    "step": "branch_evolution",
    "branch": "branch/binary-analysis",
    "mutated": true,
    "summary": "prompt, skills",
    "conversation": ["<LLM conversation turns>"]
  }
]
```

---

## Git Tree Over Time

```
Batch 1-5 (no shift -> single-path = A-Evolve):

  main:  o--o--o--o--o

Batch 6 (shift detected -> branch):

  main:  o--o--o--o--o--o
                         \
         branch/A:        o--o

Batch 7+ (both streams evolve, branches rebased on main updates):

  main:  o--o--o--o--o--o--o--o
                         \
         branch/A:        o--o--o--o
                               \
         branch/B:              o--o
```

---

## Ground-Truth Information Barrier

The evolver LLM must not see ground-truth evaluation labels. This prevents the
evolver from overfitting to historical pass/fail patterns instead of learning from
behavioral signals (conversation transcripts, error messages, task details).

| Data | Where stored | Visible to evolver? |
|------|-------------|:-------------------:|
| Pass/fail per task | `batch_results` in-memory | NO (framework only) |
| `total_passed` per branch | `tree_state.json` in `out_dir/` | NO (not in LLM context) |
| `score` per routing entry | Not persisted | NO (removed from `routing_log.jsonl`) |
| Task routing decision | `routing_log.jsonl` in `out_dir/` | YES (via analyze-plan prompt, orchestrated mode only) |
| Task details | Evolution prompt | YES (needed for analysis) |

---

## Alignment with `challenges.md`

| Paper Concept | Implementation | Mode |
|---|---|---|
| C1: Distribution shift | Git branches isolate non-stationary strategies from main | Both |
| C2: Coupled experience | Branching-aware prompt (inline) or analyst (orchestrated) separates stationary vs non-stationary patterns; F_Navigate routes each task to best-fit branch | Both |
| C3: Evolver capability | Multi-agent orchestration: analyst + evolver collaborate via Orchestrator framework | Orchestrated only |
| F_Navigate | `navigate()`: LLM reads branch leaves (system prompt, skills, tools) via `git show` and picks best branch | Both |
| Branch leaf inspection | `_read_branch_leaves()` reads workspace content per branch via `git show` (README.md, system prompt, skills, tools) | Both |
| Rich task context | Task ID + metadata (category, event, year) + full input passed to navigator | Both |
| Agentic branching | Evolver explores existing branches, creates/evolves branches directly via git commands in sandbox, creates README.md per branch; pipeline discovers new branches post-hoc and reads README for description | Inline only |
| Analyze & Plan | `_analyze_and_plan()` via `AnalystRole`: holistic experience analysis -> JSON evolution plan | Orchestrated only |
| Branch evolution | Evolver does it directly (inline) or `_execute_plan_step()` with plan context per branch (orchestrated) | Both |
| Deepen main | Standard evolution prompt + branching section (inline) or plan-guided main evolution (orchestrated) | Both |
| Navigation trajectory | Per-cycle JSON capturing evolver LLM conversations and branch decisions | Both |
| Graceful degradation | If evolver never creates branches, inline mode = standard A-Evolve (H1) | Inline |
| Promote | Merge high-accuracy branches back to main | Deferred (v2) |
| Prune | Delete stale branches | Deferred (v2) |
| Evolved evaluator/navigator | Self-improving classification and routing | Deferred (v2) |
| Evolved branch_policy | Self-improving promotion/pruning rules | Deferred (v2) |
| routing_log.jsonl | Flushed to disk each batch (no ground-truth scores) | Both |
| tree_state.json | Saved to out_dir/ for resume | Both |

---

## Deferred Features (v2)

These features were removed from v1 to control confounding variables.

| Feature | Rationale for deferral |
|---------|----------------------|
| Promote (branch -> main merge) | Optimization on branch lifecycle -- test branching first |
| Prune (delete stale branches) | Not needed with bounded experiments (~3-5 branches) |
| Evolved evaluator.py | Meta-optimization -- confounding variable with core mechanism |
| Evolved navigator.py | Meta-optimization -- confounding variable with core mechanism |
| Evolved branch_policy.py | Meta-optimization -- confounding variable with core mechanism |
| Step 6 (evolve evolver workspace) | Meta-evolution -- confounding variable |

---

## File Reference

All files involved in the navigation system. Evolution logic is organised
in three layers:

- **Engine** (`navigation/engine.py`) — shared navigation core + a
  pluggable `EvolutionTemplate`.
- **Templates** (`navigation/templates/*.py`) — each concrete template
  implements one evolution strategy (inline, orchestrated) and owns its
  template-specific prompts.
- **Activity framework** (`navigation/activity/`) — UML-Activity-Diagram-
  shaped dataflow runtime. Templates compose their bodies as Activities
  (spec = nodes + typed pins + object/control flows) and hand them to the
  runtime; this eliminates the snapshot-execute-diff duplication that
  previously appeared in three places.

### Navigation package

| File | Role |
|------|------|
| `agent_evolve/algorithms/navigation/__init__.py` | Package exports: `NavigationEngine`, `EvolutionTemplate`, `InlineTemplate`, `OrchestratedTemplate`, `NAVIGATE_SYSTEM_PROMPT`, `build_navigate_prompt`, and re-exports of template-owned prompts (`ANALYZE_PLAN_SYSTEM_PROMPT`, `build_analyze_plan_prompt`, `build_branching_section`) |
| `agent_evolve/algorithms/navigation/engine.py` | `NavigationEngine(AEvolveEngine)` — navigation core (`navigate`, `_read_branch_leaves`, `_resolve_branch_name`, `_viable_branches`, `_sanitize_branch_name`, `_format_tree`) + dispatch to the active `EvolutionTemplate`. Constructor takes `mode="inline"` (default) or `"orchestrated"`, or a custom `template=` instance. |
| `agent_evolve/algorithms/navigation/prompts.py` | Routing prompts only: `NAVIGATE_SYSTEM_PROMPT`, `build_navigate_prompt`. Template-specific prompts live alongside the template that uses them. |

### Templates

| File | Role |
|------|------|
| `agent_evolve/algorithms/navigation/templates/base.py` | `EvolutionTemplate` ABC — a template implements `execute(vc, workspace, batch_results, tree, evo_number, routing_log_path) -> dict`. |
| `agent_evolve/algorithms/navigation/templates/inline.py` | `InlineTemplate` (single sandboxed LLM call, agentic branching) + its owned prompt `build_branching_section`. Body is the Activity at `activity/specs/inline.py`. |
| `agent_evolve/algorithms/navigation/templates/orchestrated.py` | `OrchestratedTemplate` (plan-driven: analyst → main → per-branch) + its owned prompts `ANALYZE_PLAN_SYSTEM_PROMPT` and `build_analyze_plan_prompt`. Uses the `branch_cycle` Activity at `activity/specs/plan_driven.py` for each cycle step. Implements `_realise_branches`, `_run_analyst`, plan parsing inline — no separate `Orchestrator` / `Role` abstractions. |

### Activity framework

| File | Role |
|------|------|
| `agent_evolve/algorithms/navigation/activity/README.md` | Framework overview, UML alignment table, three-step design process, node catalog. |
| `activity/__init__.py` | Public API re-exports: `Activity`, `Type`, `ActivityBuilder`, `ActivityRuntime`, `ActivityTemplate`, validator + exporters. |
| `activity/types.py` | `Type` enum — every semantic type that can flow on a wire (Workspace, GitTree, BatchResults, PromptText, Plan, BranchSpec, MutationReport, …). |
| `activity/spec.py` | `Activity`, `NodeSpec`, `ParameterSpec`, `FlowSpec` — JSON-serialisable dataclasses. |
| `activity/pin.py`, `activity_node.py`, `action.py`, `call_activity.py`, `control.py`, `flow.py` | UML metamodel: `ActivityNode` ABC, `Action`, `CallActivity`, `DecisionNode`, `ForkNode`, `JoinNode`, `ExpansionRegion`, `InitialNode`, `FinalNode`, `InputPin`, `OutputPin`. |
| `activity/registry.py` | `ActionRegistry` — maps `kind` / `action_kind` strings to node classes so specs can reference actions by name. |
| `activity/validator.py` | Pre-flight validation: typechecks every ObjectFlow's source/target pins, detects cycles, checks required-pin wiring, resolves sub-Activity references. |
| `activity/runtime.py` | `ActivityRuntime` — topologically sorts an Activity and executes each node (Action dispatch, CallActivity recursion, ExpansionRegion iterative/parallel fan-out). |
| `activity/builder.py` | `ActivityBuilder` — fluent Python API for constructing an `Activity` without writing JSON. |
| `activity/exporters.py` | `to_json`, `to_mermaid`, `to_plantuml` — render an Activity to any UML tool or a GitHub README. |
| `activity/adapters.py` | `ActivityTemplate` — wraps an Activity as an `EvolutionTemplate` (drop-in for `NavigationEngine(template=…)`). |
| `activity/nodes/workspace.py` | Actions: `op.snapshot_workspace`, `op.detect_mutations`, `op.clear_drafts`. |
| `activity/nodes/prompt.py` | Actions: `op.build_evolution_prompt`, `op.append_branching_section`, `op.prepend_plan_context`, `op.build_analyze_plan_prompt`. |
| `activity/nodes/llm.py` | Actions: `op.call_llm` (sandboxed evolver call via `AEvolveEngine._run_llm`), `op.call_llm_simple` (one-shot Bedrock completion), `op.parse_plan`. |
| `activity/nodes/git.py` | Actions: `op.git_commit`, `op.git_checkout`, `op.git_ensure_main`, `op.git_list_branches`, `op.git_discover_new_branches`, `op.git_register_branches`, `op.git_tag_branch_heads`, `op.git_realise_branches`, `op.git_rebase_branches`. |
| `activity/nodes/navigation.py` | Actions: `op.read_branch_leaves`, `op.extract_plan_branches`, `op.load_routing_history`. |
| `activity/nodes/agents/analyst.py`, `evolver.py`, `planner.py`, `critic.py` | Pre-built agent sub-Activities — small Activities that compose the above actions into reusable `CallActivity` / `ExpansionRegion` targets. |
| `activity/specs/inline.py` + `inline.json` | The inline template's Activity spec: 13 Actions + ControlFlows reproducing the `_evolve_inline` flow line-by-line. |
| `activity/specs/plan_driven.py` + `plan_driven.json` | The plan-driven reference Activity (top-level `CallActivity→ExpansionRegion` pipeline) plus `_build_branch_cycle_activity()` used by `OrchestratedTemplate._execute_plan_step`. |

### Shared dependencies

| File | Role |
|------|------|
| `agent_evolve/algorithms/aevolve/engine.py` | `AEvolveEngine` base class — `evolve()`, `_run_llm()`, `step()` inherited by `NavigationEngine`. |
| `agent_evolve/algorithms/aevolve/prompts.py` | `build_evolution_prompt()` — standard evolution prompt used by every template. |
| `agent_evolve/algorithms/aevolve/tools.py` | `BASH_TOOL_SPEC`, `make_workspace_bash()` — Docker sandbox for workspace mutation. |
| `agent_evolve/types.py` | `StrategyTree`, `BranchInfo`, `RoutingEntry` — data types + `to_dict()`/`from_dict()`. |
| `agent_evolve/config.py` | Navigation config: `navigation_enabled`, `branch_confidence_threshold`; `config.extra["orchestrator"]` (legacy YAML key) maps to `NavigationEngine(mode="orchestrated")`. |
| `agent_evolve/engine/versioning.py` | `VersionControl` — `show_file_at()`, `create_branch()`, `rebase_branch()`, `list_branches()`, tagging. |
| `solve_all_with_evolution.py` | Routing loop, batch stats, `routing_log.jsonl` persistence, `tree_state.json`, trajectory recording, engine instantiation. Passes `mode=` to `NavigationEngine` (translating the legacy `orchestrator` config key). |

### Tests

| File | Scope |
|------|-------|
| `tests/test_navigation_branches.py` | Branch sanitisation, realise, resolve, viable filtering. |
| `tests/test_navigation_readme.py` | Per-branch README extraction + branch-leaf reading in `NavigationEngine`. |
| `tests/test_activity_metamodel.py` | `Type` enum, JSON round-trip, `ActionRegistry`, pin declarations. |
| `tests/test_activity_runtime.py` | Validator (type mismatches, cycles, unwired pins, missing sub-activities), topological execution, `CallActivity` recursion, `ExpansionRegion` iterative + parallel, mermaid / plantuml exporters. |
| `tests/test_activity_nodes.py` | Every built-in Action exercised against a real tmp_path workspace + git repo; pre-built agent sub-Activity structure. |
| `tests/test_activity_adapters.py` | `ActivityTemplate` satisfies the `EvolutionTemplate` contract and plugs into `NavigationEngine(template=…)`. |
| `tests/test_activity_parity.py` | Reference specs round-trip; the inline spec covers every step in `InlineTemplate.execute`; the plan_driven spec covers every phase of `OrchestratedTemplate`; `evolve_one_branch` is referenced by both the main `CallActivity` and the per-branch `ExpansionRegion` (the former 3x-duplication collapses to a single sub-Activity). |
| `tests/test_activity_layering.py` | Import-audit: no file imports from a higher layer than its own (types < metamodel < catalog < tooling < adapters). |
| `tests/test_activity_template_behaviour.py` | End-to-end behavioural parity for both templates (git commits, tags, `StrategyTree` mutations, return-dict shape) against a stub engine. |
| `paper/navigation_implementation.md` | This file. |
