# Implementation Plan: Decoupled Evolution with Navigation

Based on paper/challenges.md Section 3.

## Problem

Current A-EVOLVE uses linear evolution (evo-0 → evo-1 → ...) on a single workspace.
The paper identifies two failure modes this cannot address:

1. **Strategy interference**: improving one task type hurts another (C3)
2. **Infrastructure gaps**: solver's pipeline (search, sandbox, submission) is hardcoded outside the workspace (C2)

~80% of FutureX failures and ~45% of CTF failures are infrastructure-level.

## Architecture

```
results/experiment/
├── solver_workspace/              ← what the agent uses to solve tasks
│   ├── prompts/system.md
│   ├── skills/*/SKILL.md
│   ├── memory/*.jsonl
│   ├── tools/*.py                 ← sandbox tools (--network none)
│   ├── infra/                     ← NEW: infrastructure (framework-executed, has network)
│   │   ├── search_pipeline.py     ← evolvable search strategy
│   │   ├── sandbox_setup.sh       ← evolvable Docker tool installation
│   │   └── submit_handler.py      ← evolvable submission format
│   └── .git/                      ← strategy tree (main + branches)
│
└── evolver_workspace/             ← meta-strategy (evaluation + navigation)
    ├── evaluator.py               ← F_Evaluate: classify failures
    ├── navigator.py               ← F_Navigate: route tasks to branches
    ├── branch_policy.py           ← branching/promotion/pruning decisions
    ├── routing_log.jsonl          ← accumulated routing outcomes
    └── .git/                      ← evolver's own versioning
```

### Two workspaces, strict access isolation

**Solver workspace**: artifacts the agent loads and uses during task solving.

**Evolver workspace**: the evolver's own tools for analyzing failures and
routing tasks. These are meta-level — they don't affect how the agent solves,
only which workspace state the agent sees and how the evolver decides what
to change.

### Access control

```
┌──────────────────────────┐     ┌──────────────────────────┐
│  Solver Agent             │     │  Evolver Agent            │
│                           │     │                           │
│  CAN access:              │     │  CAN access:              │
│    solver_workspace/*     │     │    evolver_workspace/*    │
│                           │     │    solver_workspace/*     │
│  CANNOT access:           │     │                           │
│    evolver_workspace/*    │     │  CANNOT access:           │
│    framework code         │     │    framework code         │
│    other experiments      │     │    other experiments      │
└──────────────────────────┘     └──────────────────────────┘
```

**Enforcement mechanism:**

- **Solver**: runs in Docker sandbox. Only `solver_workspace/tools/` is
  mounted at `/tools/`. `solver_workspace/infra/` is loaded by the framework
  before the agent starts — the agent never sees `infra/` directly. The
  evolver workspace is never mounted.

- **Evolver**: runs in Docker sandbox with two bind mounts:
  - `/solver_workspace` → `solver_workspace/` (read-write)
  - `/evolver_workspace` → `evolver_workspace/` (read-write)
  - Working directory: `/evolver_workspace`
  No other paths are accessible.

**Verification**: a test asserts that:
1. Solver sandbox has no mount to `evolver_workspace/`
2. Evolver sandbox mounts only the two workspaces
3. No workspace code can `import` or `open()` paths outside its mounts

### infra/ vs tools/

| | `tools/*.py` | `infra/*.py` |
|---|---|---|
| Runs in | Docker sandbox (`--network none`) | Host process (framework) |
| Network | No internet | Full internet (guarded by htmldate) |
| Called by | Solver agent (via `bash` tool) | Framework (before agent starts) |
| Purpose | Computation, analysis | Data fetching, setup, submission |

## Activation

```bash
# Current A-EVOLVE (unchanged):
bash futurex_hypothesis.sh H1

# Decoupled evolution:
bash futurex_hypothesis.sh --navigation H1
```

Without `--navigation`: identical to current behavior. No evolver workspace,
no branching, no routing. Linear evolution on single solver workspace.

## Strategy Tree

The solver workspace uses git branches for strategy isolation:

```
main (root: stationary knowledge shared by all tasks)
│
├── branch/algebraic-reasoning (specialized for RSA/ECC crypto)
├── branch/platform-data (specialized for Chinese platform rankings)
└── branch/skip-illiquid (specialized for untradeable markets)
```

Checking out any branch gives a complete workspace (main's artifacts + branch-specific additions).

### Branching is evolver-driven

The evolver decides when to branch based on failure analysis.
Config controls the threshold:

```yaml
branch_confidence_threshold: 0.7    # evolver must be >70% confident to branch
# -1 = never branch (degrades to current A-EVOLVE)
# 0 = always branch when evolver suggests
```

No predefined branches. The evolver discovers when branching is needed.

## Evolution Flow (per batch)

### Solve phase

```
for each task in batch:
    if --navigation:
        branch = F_Navigate(task, tree)       # evolver_workspace/navigator.py
        git checkout branch                    # solver_workspace
    agent = load_workspace()
    trajectory = agent.solve(task)
    score = evaluate(task, trajectory)
    log routing outcome: (task, branch, score)
```

### Evolve phase

```
if --navigation:
    # Step 1: F_Evaluate — classify failures
    classifications = evaluate(trajectories)   # evolver_workspace/evaluator.py

    # Step 2: Deepen main (stationary failures)
    stationary = [c for c in classifications if c.type == "stationary"]
    git checkout main
    evolve_and_commit(stationary)
    rebase all branches onto main

    # Step 3: Branch (non-stationary failures)
    for group in nonstationary:
        if group.confidence >= threshold:
            git checkout -b branch/name main
            evolve_and_commit(group.failures)

    # Step 4: Promote branches that generalize → merge into main
    # Step 5: Prune stale branches
    # Step 6: Evolve navigator and evaluator (evolver_workspace)
else:
    # Current A-EVOLVE: single-path evolution
    evolve_and_commit(all_failures)
```

### Evaluation and navigation: LLM → evolved code

Both start as LLM-prompted and can be evolved into code:

**Cycle 1**: No `evaluator.py` or `navigator.py` exist → framework uses LLM prompts
**Cycle N**: Evolver writes `evaluator.py` with learned rules → framework uses code
**Cycle N+M**: Evolver refines code based on routing outcomes → faster, more accurate

The framework always checks: does evolved code exist? If yes, use it. If no, fall back to LLM prompt.

### Evolution prompt: explicit workspace paths

The evolver's LLM prompt clearly specifies which directories to work on:

```
You have access to two workspaces:

/solver_workspace/  — The solver agent's artifacts. You can modify:
  prompts/system.md     — system prompt for the solver
  skills/*/SKILL.md     — domain skills
  memory/*.jsonl        — learned memories
  tools/*.py            — computation tools (run in sandbox, no network)
  tools/registry.yaml   — tool registry
  infra/                — infrastructure (run by framework, has network):
    search_pipeline.py  — how the solver searches the web
    sandbox_setup.sh    — what tools are installed in the solver's sandbox
    submit_handler.py   — how answers are formatted and submitted

/evolver_workspace/  — Your own workspace. You can modify:
  evaluator.py          — your failure classification logic
  navigator.py          — your task-to-branch routing logic
  branch_policy.py      — your branching/promotion/pruning decisions
  routing_log.jsonl     — (read-only, appended by framework)

Working directory: /evolver_workspace
To modify solver artifacts: edit files under /solver_workspace/
To modify your own logic: edit files under /evolver_workspace/

Do NOT attempt to access any paths outside these two directories.
```

This prevents the evolver from wasting turns on failed file access attempts
and makes the workspace boundary explicit in the prompt.

## Files to Modify

| File | Change | Lines |
|---|---|---|
| `agent_evolve/engine/versioning.py` | Add `create_branch`, `checkout_branch`, `merge_branch`, `rebase_branch`, `list_branches`, `delete_branch` | +60 |
| `agent_evolve/config.py` | Add `navigation_enabled`, `branch_confidence_threshold`, `promotion_threshold`, `staleness_window` | +10 |
| `agent_evolve/algorithms/aevolve/engine.py` | Add failure classification, branching decisions, promotion, main deepening. Conditional on `navigation_enabled`. | +250 |
| `agent_evolve/algorithms/aevolve/prompts.py` | Add F_Evaluate and F_Navigate LLM prompts | +120 |
| `solve_all_with_evolution.py` | Add `--navigation` flag, routing in solve loop, evolver workspace creation | +80 |
| `backends/futurex.py` | Load `infra/search_pipeline.py` if exists, guard with htmldate | +40 |
| `backends/ctf_dojo.py` | Load `infra/sandbox_setup.sh` and `infra/submit_handler.py` if exist | +30 |
| `agent_evolve/types.py` (new) | `StrategyTree`, `FailureClassification`, `RoutingEntry` types | +60 |
| **Total** | | **~650** |

## Backward Compatibility

| Scenario | Behavior |
|---|---|
| Any existing experiment without `--navigation` | Identical to current — no branching, no routing, linear evolution |
| `--navigation` with `branch_confidence_threshold: -1` | Evolver workspace exists but never branches — degrade to linear |
| `--navigation` with default threshold | Full decoupled evolution |

All existing hypothesis scripts (`futurex_hypothesis.sh`, `ctf_dojo_hypothesis.sh`, `poly_hypothesis.sh`) produce identical results without `--navigation`.

## Verification

1. Run existing experiments WITHOUT `--navigation` — results unchanged
2. Run with `--navigation` — verify evolver workspace created, branches appear
3. Run with `branch_confidence_threshold: -1` — verify linear fallback
4. Check `infra/search_pipeline.py` evolved on FutureX
5. Check `infra/submit_handler.py` evolved on CTF
6. Check routing_log.jsonl captures (task, branch, score)
7. **Access isolation test**: verify solver sandbox cannot read evolver workspace
8. **Access isolation test**: verify evolver sandbox cannot read outside its two mounts
9. **Prompt test**: verify evolver prompt includes explicit workspace paths
