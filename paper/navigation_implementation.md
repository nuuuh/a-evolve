# Navigation Implementation: Decoupled Evolution with Agentic Navigation

Full implementation reference for Section 3 of `challenges.md`.

**Version:** v1 (simplified) — tests core hypothesis (C1+C2) without meta-evolution.

---

## System Flow Map

Four LLM-powered agents collaborate across two phases per cycle:

```
═══════════════════════════════════════════════════════════════════
  PHASE 1: INFERENCE                         PHASE 2: EVOLUTION
═══════════════════════════════════════════════════════════════════

 Batch of tasks                            Batch results
      │                                    (trajectories)
      ▼                                         │
┌───────────┐                                   ▼
│ NAVIGATOR │ ── routes each task ──►  ┌──────────────┐
│   (LLM)   │    to best branch        │   PLANNER    │
│           │                           │    (LLM)     │
│ Reads each│                           │              │
│ branch's  │                           │ Analyzes all │
│ workspace │                           │ trajectories,│
│ (prompt,  │                           │ classifies   │
│  skills,  │                           │ patterns as  │
│  tools)   │                           │ stationary   │
│ via git   │                           │ vs non-      │
│ show      │                           │ stationary   │
└───────────┘                           └──────┬───────┘
      │                                        │
      ▼                                   evolution plan
┌───────────┐                            ╱            ╲
│  SOLVER   │                           ▼              ▼
│   (LLM)   │                   ┌────────────┐  ┌────────────┐
│           │                   │  EVOLVER   │  │  EVOLVER   │
│ Runs on   │                   │   (LLM)    │  │   (LLM)    │
│ the branch│                   │            │  │            │
│ workspace │                   │  Deepens   │  │  Evolves   │
│ assigned  │                   │  main with │  │  branches  │
│ by the    │                   │  general   │  │  with      │
│ navigator │                   │  improve-  │  │  special-  │
│           │                   │  ments     │  │  ized      │
└───────────┘                   │            │  │  strategies│
      │                         │  (sandbox) │  │  (sandbox) │
      ▼                         └─────┬──────┘  └─────┬──────┘
 task results                         │  rebase       │
                                      │  branches     │
                                      └───────┬───────┘
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │   STRATEGY TREE   │
                                    │                   │
                                    │  main ○──○──○──●  │
                                    │            ╲      │
                                    │  branch/A   ○──○  │
                                    │               ╲   │
                                    │  branch/B      ○  │
                                    └────────┬─────────┘
                                             │
                                        next cycle
```

**Agent roles:**

| Agent | Phase | Role | Has tools? |
|-------|-------|------|:----------:|
| **Navigator** | Inference | Routes each task to the best-fit branch by reading workspace content from all branches via `git show` | No |
| **Solver** | Inference | Solves tasks using the branch workspace (prompt, skills, tools) assigned by the navigator | Yes (benchmark tools) |
| **Planner** | Evolution Step 1 | Analyzes all batch trajectories holistically; produces a structured evolution plan splitting work between main and branches | No |
| **Evolver** | Evolution Steps 2-3 | Executes the plan: edits workspace artifacts (prompt, skills, memory, tools) in a Docker sandbox, first for main then for each branch | Yes (bash in sandbox) |

---

## Workspace Layout

```
results/experiment/
├── solver_workspace/              <- what the agent uses to solve tasks
│   ├── prompts/system.md
│   ├── skills/*/SKILL.md
│   ├── memory/*.jsonl
│   ├── tools/*.py                 <- sandbox tools (--network none)
│   ├── infra/                     <- infrastructure (framework-executed, has network)
│   │   ├── search_pipeline.py
│   │   ├── sandbox_setup.sh
│   │   └── submit_handler.py
│   └── .git/                      <- strategy tree (main + branches)
│
├── routing_log.jsonl              <- append-only routing log (no ground-truth labels)
├── tree_state.json                <- StrategyTree snapshot for resume
└── <benchmark>/
    └── evolution/
        ├── evo_1_trajectory.json          <- standard evolver trajectory
        ├── nav_evo_1_trajectory.json      <- navigation evolution trajectory (Steps 1-3)
        ├── nav_evo_2_trajectory.json
        └── ...
```

---

## Phase 1: Inference (Solving)

### 1.1 Startup

```
┌────────────────────────────────────────────────────────────────────────┐
│  STARTUP (solve_all_with_evolution.py)                                │
│                                                                      │
│  --navigation flag?                                                  │
│       │                                                              │
│       ├─ NO  → standard single-path A-Evolve (no branching)         │
│       │                                                              │
│       └─ YES →                                                       │
│            1. Set routing_log_path = out_dir/routing_log.jsonl       │
│            2. Load out_dir/tree_state.json if exists → StrategyTree  │
│               (branches + metadata for resume)                       │
│               OR create empty StrategyTree()                         │
└────────────────────────────────────────────────────────────────────────┘
```

### 1.2 F_Navigate: Route Tasks to Branches

F_Navigate reads the **actual workspace content** from each git branch (the "leaves"
of the strategy tree) so the LLM can make informed routing decisions based on what
each branch can actually do, not just its name.

```
          for each batch:
                │
                ▼
┌────────────────────────────────────────────────────────────────────────┐
│  F_NAVIGATE: Route each task to a branch                             │
│                                                                      │
│  if tree.branches is empty:                                          │
│       → ALL tasks → "main"                                           │
│                                                                      │
│  if tree has branches:                                               │
│       for each task in batch:                                        │
│                                                                      │
│         1. Build rich task context:                                   │
│            Task ID: <t.id>                                           │
│            category: <metadata>                                      │
│            event: <metadata>                                         │
│            challenge: <metadata>                                     │
│            year: <metadata>                                          │
│            <full t.input — no truncation>                             │
│                                                                      │
│         2. Read branch leaves via _read_branch_leaves():             │
│            For each branch (incl main), read via git show:           │
│              - prompts/system.md  (strategy & approach)              │
│              - skills/ listing    (reusable capabilities)            │
│              - tools/registry.yaml (available tools)                 │
│                                                                      │
│         3. LLM routing decision:                                     │
│            NAVIGATE_SYSTEM_PROMPT + build_navigate_prompt()           │
│              Input: rich task context + full branch workspace content │
│              Output: {"branch": "...", "confidence": ...,            │
│                       "reason": "..."}                               │
│                                                                      │
│           branch_groups[branch].append(task)                         │
│           task_branches[task.id] = branch                            │
│                                                                      │
│       Update last_routed_cycle for each active branch                │
└────────────────────────────────────────────────────────────────────────┘
```

**Key design decisions:**

- **Full task input**: The navigator sees the complete task description, not a
  truncated version. Generic task descriptions (e.g., CTF challenges that all say
  "find the flag") are supplemented with structured metadata (category, event, year)
  to give the LLM enough signal to differentiate.

- **Branch leaf inspection**: The navigator reads actual workspace files from each
  branch via `VersionControl.show_file_at()` and `git ls-tree`. This means routing
  decisions are based on what each branch's workspace actually contains (its system
  prompt, skills, tools), not just the branch description.

- **Prompt structure**: Each branch is rendered as a full section under
  "Git Tree Leaves (Branch Workspaces)" with its system prompt, skills list, and
  tools registry. The LLM compares branches' actual capabilities against the task.

### 1.3 Per-Branch Solving

```
┌────────────────────────────────────────────────────────────────────────┐
│  PER-BRANCH SOLVING                                                  │
│                                                                      │
│  for branch_name, branch_tasks in branch_groups:                     │
│                                                                      │
│      1. git checkout <branch_name> in solver_workspace               │
│         → workspace now has main + branch-specific artifacts         │
│                                                                      │
│      2. agent.reload_from_fs()                                       │
│         → loads prompts/skills/tools/memory from branch state        │
│                                                                      │
│      3. backend.build_prompts(agent, branch_tasks)                   │
│         → generates solver prompts from branch's workspace           │
│                                                                      │
│      4. Submit all branch_tasks to thread/process pool               │
│                                                                      │
│  After all groups submitted:                                         │
│      git checkout main; agent.reload_from_fs()                       │
│                                                                      │
│  Collect results from futures (with timeout handling)                │
└────────────────────────────────────────────────────────────────────────┘
```

### 1.4 Stats and Persistence

```
┌────────────────────────────────────────────────────────────────────────┐
│  STATS + PERSISTENCE (after solving, before evolution)               │
│                                                                      │
│  Framework-internal (not visible to evolver):                        │
│      BranchInfo.total_tasks += 1                                     │
│      BranchInfo.total_passed += 1 (if success)                       │
│      RoutingEntry appended to strategy_tree.routing_log (in-memory)  │
│                                                                      │
│  Persisted to disk:                                                  │
│      Append to routing_log.jsonl (no score, no pass/fail):           │
│          {task_id, properties, branch, cycle}                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 2: Holistic Evolution (Steps 1-3)

```
┌────────────────────────────────────────────────────────────────────────┐
│  EVOLUTION TRIGGER                                                   │
│                                                                      │
│  Skip if: baseline mode, score above threshold, max_cycles reached,  │
│           or evo_start_cycle not yet reached                         │
│                                                                      │
│  if navigation_enabled:                                              │
│      → engine.evolve_with_navigation(                                │
│            solver_workspace, batch_results,                          │
│            strategy_tree, evo_cycle, routing_log_path)               │
│  else:                                                               │
│      → engine.evolve(workspace, evo_number)  [standard A-Evolve]     │
│                                                                      │
│  After evolve: save tree_state.json to out_dir/                      │
│  Save nav trajectory to evolution/nav_evo_{cycle}_trajectory.json    │
└────────────────────────────────────────────────────────────────────────┘
```

### Step 1: Analyze & Plan (Holistic Experience Analysis)

```
┌────────────────────────────────────────────────────────────────────────┐
│  STEP 1: ANALYZE & PLAN (pure analysis, no sandbox)                  │
│                                                                      │
│  1. Load routing_log.jsonl as evolution_history                       │
│  2. Pass ALL batch_results (successes AND failures) to LLM           │
│                                                                      │
│  LLM produces holistic evolution plan (no tools, no sandbox):        │
│     ANALYZE_PLAN_SYSTEM_PROMPT + build_analyze_plan_prompt()          │
│     → JSON evolution plan                                            │
│                                                                      │
│  Plan structure:                                                     │
│     summary: "high-level batch analysis"                             │
│     main_evolution:                                                  │
│       description: "stationary improvements for main"                │
│       insights: [...]                                                │
│       task_ids: [...]                                                │
│     branches: [                                                      │
│       { name, action, description, evolution_guidance, task_ids }    │
│     ]                                                                │
│                                                                      │
│  Trajectory captured:                                                │
│     plan["_trajectory"] = {prompt, response}                         │
│     → recorded in trajectory list as "analyze_and_plan" step         │
│                                                                      │
│  Fallback: if LLM fails → all failures go to main, no branches      │
└──────────┬──────────────────────────┬─────────────────────────────────┘
           │                          │
  plan.main_evolution         plan.branches
           │                          │
           ▼                          ▼
```

### Step 2: Deepen Main (Stationary Improvements)

```
┌──────────────────────────────────────────────────────────────────┐
│  STEP 2: DEEPEN MAIN (plan-guided, with sandbox)                │
│                                                                  │
│  Skip if: plan.main_evolution.description is empty               │
│                                                                  │
│  checkout main                                                   │
│  Build prompt = plan_context + build_evolution_prompt()           │
│                                                                  │
│  _execute_plan_step(workspace, main_logs, evo_number,            │
│                     plan_context=plan context for main)           │
│    → LLM sees plan + workspace state, edits artifacts            │
│      via Docker sandbox                                          │
│                                                                  │
│  Trajectory captured:                                            │
│    {step: "deepen_main", mutated, summary, conversation}         │
│                                                                  │
│  If mutated:                                                     │
│    rebase ALL branches onto updated main                         │
│    → propagates stationary fixes to every branch                 │
└──────────────────────────────────────────────────────────────────┘
```

### Step 3: Branch (Non-Stationary Patterns)

```
┌──────────────────────────────────────────────────────────────────┐
│  STEP 3: BRANCH (plan-guided, with sandbox)                     │
│                                                                  │
│  for each branch in plan.branches:                               │
│                                                                  │
│    if no branch name → skip                                      │
│                                                                  │
│    if branch doesn't exist:                                      │
│      git checkout -b <branch> main                               │
│      tree.branches.append(BranchInfo)                            │
│    else:                                                         │
│      git checkout <branch>                                       │
│                                                                  │
│    _execute_plan_step(workspace, branch_logs, evo_number,        │
│                       plan_context=plan context for branch)      │
│      → LLM sees plan + workspace state, edits artifacts          │
│        via Docker sandbox                                        │
│                                                                  │
│    Trajectory captured:                                          │
│      {step: "branch_evolution", branch, mutated, summary,        │
│       conversation}                                              │
└──────────────────────────────────────────────────────────────────┘
```

### Persist and Return

```
┌────────────────────────────────────────────────────────────────────────┐
│  PERSIST + RETURN                                                    │
│                                                                      │
│  git checkout main                                                   │
│  Log strategy tree visualization                                     │
│                                                                      │
│  Return from evolve_with_navigation():                               │
│    {evo_number, mutated, plan, branches, trajectory}                 │
│                                                                      │
│  trajectory = [                                                      │
│    {step: "analyze_and_plan", plan_summary, prompt, response},       │
│    {step: "deepen_main", mutated, summary, conversation},            │
│    {step: "branch_evolution", branch, mutated, summary, conversation}│
│  ]                                                                   │
│                                                                      │
│  Orchestrator:                                                       │
│    - Saves tree_state.json to out_dir/                               │
│    - Saves nav_evo_{cycle}_trajectory.json to evolution/             │
│    - git commit solver workspace                                     │
│    - Write history.jsonl                                             │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Navigation Trajectory Recording

Each navigation evolution cycle produces a trajectory JSON file capturing the full
LLM interaction for each step of the pipeline:

```
evolution/nav_evo_{cycle}_trajectory.json
```

Structure:
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

This enables post-hoc analysis of:
- What patterns the planner identified (stationary vs non-stationary)
- What mutations the evolver made to main vs branches
- Whether the planner's analysis was coherent with the batch results

---

## Git Tree Over Time

```
Batch 1-5 (no shift → single-path = A-Evolve):

  main:  ○──○──○──○──○

Batch 6 (shift detected → branch):

  main:  ○──○──○──○──○──○
                          ╲
         branch/A:         ○──○

Batch 7+ (both streams evolve, branches rebased on main updates):

  main:  ○──○──○──○──○──○──○──○
                          ╲
         branch/A:         ○──○──○──○
                                ╲
         branch/B:               ○──○
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
| Task routing decision | `routing_log.jsonl` in `out_dir/` | YES (via analyze-plan prompt) |
| Task details | Analyze-plan prompt | YES (needed for holistic analysis) |

---

## Alignment with `challenges.md`

| Paper Concept | Section | Status |
|---|---|---|
| C1: Distribution shift | Branching isolates non-stationary artifacts from main | Implemented |
| C2: Coupled experience | Holistic analysis separates stationary vs non-stationary; F_Navigate gives each task main + 1 branch | Implemented |
| C3: Evolver capability | infra/ layer + `--no-infra-evo` flag | Implemented (infra evo disabled by default) |
| Analyze & Plan | Step 1: holistic experience analysis -> evolution plan (pure, no sandbox) | Implemented |
| F_Navigate | Routing: LLM reads branch leaves (system prompt, skills, tools) and picks best branch | Implemented |
| Branch leaf inspection | `_read_branch_leaves()` reads workspace content per branch via `git show` | Implemented |
| Rich task context | Task ID + metadata (category, event, year) + full input passed to navigator | Implemented |
| Branch | Step 3: plan-guided branch creation/evolution for non-stationary patterns | Implemented |
| Deepen main | Step 2: plan-guided main evolution with stationary improvements, rebases branches | Implemented |
| Navigation trajectory | Per-cycle JSON capturing planner + evolver LLM conversations | Implemented |
| Promote | Merge high-accuracy branches back to main | Deferred (v2) |
| Prune | Delete stale branches | Deferred (v2) |
| Evolved evaluator/navigator | Self-improving classification and routing | Deferred (v2) |
| Evolved branch_policy | Self-improving promotion/pruning rules | Deferred (v2) |
| Step 6 (evolve evolver workspace) | Meta-evolution of evaluation/navigation | Deferred (v2) |
| routing_log.jsonl | Flushed to disk each batch (no ground-truth scores) | Implemented |
| tree_state.json | Saved to out_dir/ for resume | Implemented |
| HITL | `--hitl` flag via `experiments/futurex_hitl/` -- orthogonal to navigation | Separate feature |

---

## Deferred Features (v2)

These features were removed from v1 to control confounding variables. If the core
analyze-plan-execute mechanism (Steps 1-3) shows improvement, they can be re-added
incrementally to test their individual contribution.

| Feature | Rationale for deferral |
|---------|----------------------|
| Promote (branch -> main merge) | Optimization on branch lifecycle -- test branching first |
| Prune (delete stale branches) | Not needed with bounded experiments (~3-5 branches) |
| Evolved evaluator.py | Meta-optimization -- confounding variable with core mechanism |
| Evolved navigator.py | Meta-optimization -- confounding variable with core mechanism |
| Evolved branch_policy.py | Meta-optimization -- confounding variable with core mechanism |
| Step 6 (evolve evolver workspace) | Meta-evolution -- confounding variable |
| Evolver workspace directory | Only needed for evolved scripts (v2) |

---

## File Reference

All files involved in the navigation system. When revising navigation, check each
file for required updates.

| File | Role |
|------|------|
| `agent_evolve/algorithms/aevolve/navigation.py` | `NavigationEngine(AEvolveEngine)` -- holistic pipeline: `navigate()`, `_read_branch_leaves()`, `evolve_with_navigation()`, `_analyze_and_plan()`, `_execute_plan_step()`, `_format_tree()`, `_format_plan_context()`, `_parse_plan()` |
| `agent_evolve/algorithms/aevolve/engine.py` | `AEvolveEngine` base class -- `evolve()`, `_run_llm()`, `step()` inherited by NavigationEngine |
| `agent_evolve/algorithms/aevolve/prompts.py` | `ANALYZE_PLAN_SYSTEM_PROMPT`, `NAVIGATE_SYSTEM_PROMPT`, `build_analyze_plan_prompt()`, `build_navigate_prompt()`, `build_evolution_prompt()` |
| `agent_evolve/algorithms/aevolve/tools.py` | `BASH_TOOL_SPEC`, `make_workspace_bash()` -- Docker sandbox for solver workspace |
| `agent_evolve/algorithms/aevolve/__init__.py` | Exports `NavigationEngine`, `AEvolveEngine` |
| `agent_evolve/types.py` | `StrategyTree`, `BranchInfo`, `RoutingEntry` -- data types + `to_dict()`/`from_dict()` |
| `agent_evolve/config.py` | Navigation config fields: `navigation_enabled`, `branch_confidence_threshold`, `promotion_threshold`, `staleness_window` |
| `agent_evolve/engine/versioning.py` | `VersionControl` -- `show_file_at(ref, filepath)` used by `_read_branch_leaves()` to read files from branches without checkout |
| `solve_all_with_evolution.py` | Orchestrator -- routing loop (rich task context + branch leaf reading), batch stats, `routing_log.jsonl` persistence, `tree_state.json` save/load, navigation trajectory recording |
| `tests/test_navigation.py` | Navigation tests -- plan parsing, routing, branching, stats, ground-truth barrier, branch content in navigate prompt |
| `paper/navigation_implementation.md` | This file -- architecture docs, flow diagrams, alignment table |
