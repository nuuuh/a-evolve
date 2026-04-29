# Agentic Navigation Paper Outline

## Thesis

Linear agentic evolution is unreliable on temporal benchmarks because it mixes globally useful knowledge with regime-specific heuristics. We propose a strategy tree: keep stationary improvements on `main`, isolate non-stationary strategies on branches, and route each task to the right workspace.

## Core Challenges


> **Weak Evolution hinders temporal tasks with distribution shifts**

### C1. Temporal Shift Breaks Monotonic Evolution

Static benchmarks are shuffleable; temporal benchmarks are not. In PolyBench, CTF-Dojo, and FutureX, task properties shift over time, so more evolution can underperform early stopping.

***A single evolved strategy can overfit to recent experience and fail to transfer to future shifted tasks.***

### C2. Experience Is Coupled

Past trajectories contain both:

- **stationary knowledge:** reusable skills, tools, verification, source checks;
- **non-stationary knowledge:** local heuristics tied to a time period, market regime, challenge type, or data source.

***A single workspace loads both for every task, causing transfer and pollution at the same time.***

### C3. The Evolver Is Overloaded

Under shift, the evolver must diagnose failures, decide what is stationary, create/update branches, edit files, and use git safely. A single LLM call is often too weak for building robust and generalizable strategies.

***1. Single evolver is too weak to address C1 and C2; 2. Need of strong strategy that is generalizable, which can be harder to evolver.***

## Method

### Decoupled Evolution

- `main`: stationary improvements.
- `branch/<name>`: regime-specific strategies.
- Each branch is a real workspace with prompts, skills, memory, tools, README, and git history.

### Agentic Navigation

For each task, the navigator reads the task plus each branch's actual workspace content, then routes the task to `main` or a branch. The solver checks out that workspace and solves only with the selected state.

### Branch-Aware Evolution

After each batch:

- recurrent/general failures deepen `main`;
- regime-specific failures create or update branches.

### Multi-Agent Evolution

- **Planner/Analyst:** emits structured assignments.
- **Evolver:** executes focused mutations on `main` or branches.

## Contributions

1. Diagnose temporal non-monotonicity in agentic evolution.
2. Frame evolution memory as stationary plus non-stationary experience.
3. Introduce a git-backed strategy tree for decoupled evolution.
4. Add per-task agentic navigation over evolved workspaces.
5. Study branching and multi-agent evolution on PolyBench, CTF-Dojo, and FutureX.

## Research Questions

### Main Result

#### RQ1. Does agentic navigation improve evolution under temporal shift?

Compare baseline, full linear evolution, navigation, and multi-agent navigation across all benchmarks.

This is the headline table. It should show whether the proposed method improves accuracy/return while controlling cost and artifact growth.

### Analysis

#### RQ2. When does linear evolution stop helping? (C1)

* Test whether a single evolved strategy overfits to recent batches and fails on future shifted tasks.

* Evidence: full evolution vs early-freeze, per-batch curves, and controlled shift stress tests.

#### RQ3. Does decoupling reduce harmful regressions? (C2)

* Test whether `main` preserves stationary gains while branches isolate regime-specific heuristics.

* Evidence: task-level improvements/regressions, late-stream score, branch-specific gains, and artifact audits.


#### RQ4. Does stronger evolution supervision help? (role of multi agents orchestration and human in the loop)

> ***Case Studies***

* Test whether planner/evolver orchestration or human-in-the-loop guidance improves evolution quality under hard shift.

* Evidence: inline navigation vs multi-agent navigation vs HITL, mutation quality, branch quality, cost, and downstream score.

#### RQ5. Does routing follow strategy-relevant task properties?

* Test whether the navigator chooses branches because of actual workspace capabilities, not branch names or topic labels.

* Evidence: routing logs by time, task property, branch content, and representative routing case studies.


#### RQ6. What failures remain? (failure cases)

Analyze misrouting, stale branches, branch proliferation, weak branch descriptions, delayed labels, and unstable external tools.
