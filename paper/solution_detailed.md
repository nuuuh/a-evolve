# Solution: Detailed Framework and Theory

This document contains the full formal framework, git instantiation,
pseudocode, and theoretical analysis for the decoupled evolution solution.
See `challenges.md` Section 3 for the concise presentation version.

---

## Formal Framework

### Notation

| Symbol | Definition |
|--------|-----------|
| t ∈ {1,...,T} | Episode index (time step in the task stream) |
| x_t | Task presented at episode t |
| s(x) ∈ S | **Strategy-relevant properties** of task x — the features that determine which approach is needed to solve it. Not the topic label, but the structural properties that govern strategy selection. |
| | CTF: s = (crypto_primitive, artifact_format, competition_style) |
| | PolyBench: s = (certainty_level, liquidity, outcome_type) |
| | FutureX: s = (data_accessibility, language, precision_required) |
| P_t(x) | Task distribution at time t |
| F_t(s) = P_t(s(x) = s) | Distribution over strategy-relevant properties at time t. **Distribution shift = F_t evolving** — the same topic (crypto, markets, predictions) now requires different strategies because the underlying properties changed. |
| π_θ | Frozen parametric backbone (LLM weights) |
| π_S | Evolvable non-parametric artifact state (prompts, skills, tools, memory) |
| π = (π_θ, π_S) | Composite policy |
| R(π, x) ∈ [0,1] | Reward for solving task x under policy π |
| V(π_S, s) | Expected reward on tasks with properties s: E[R((π_θ, π_S), x) \| s(x) = s] |
| T | Strategy tree (set of nodes organized as a rooted tree) |
| π_S^(root) | Root node artifact state (stationary knowledge, shared by all) |
| Δ^(k) | Diff at node k (specialization for a region of property space) |
| π_S^(k) = π_S^(root) ⊕ Δ^(k) | Materialized artifact state at node k |
| ⊕ | Workspace composition: merge prompts, skills, tools, memory |
| S_k ⊆ S | Region of property space served by node k |
| F_Navigate | Navigation function: maps task to a leaf node |
| F_Evaluate | Diagnostic function: extracts behavioral signals from trajectories |
| F_Evolve | Evolution function: proposes artifact mutations |

### The Non-Stationary Task Stream

Each task x_t has strategy-relevant properties s(x_t) drawn from a
time-varying distribution F_t. **Distribution shift is the evolution of F_t**
— not a change in topic proportions, but a change in the properties that
determine which strategy works:

- **CTF-Dojo.** The topic stays "crypto." What shifts is the property
  `crypto_primitive`: from classical (hex, Vigenere, XOR) in 2011–14 to
  algebraic (RSA, ECC, BLS) in 2022–24.
- **PolyBench.** The topic stays "prediction market." What shifts are the
  properties `liquidity` (80% → 14% tradeable) and `certainty` (47% → 14%
  decided).
- **FutureX.** The topic stays "prediction." What shifts is
  `data_accessibility`: from searchable English events (L1) to unsearchable
  Chinese platform rankings (L3/L4).

On static benchmarks (e.g., SWE-verified), F_t ≈ F for all t.

The agent's performance at time t is:

```
V(π_S, t) = E_{x ~ P_t}[R((π_θ, π_S), x)] = E_{s ~ F_t}[V(π_S, s)]
```

### A-Evolve: Single-Path Evolution

A-Evolve maintains one artifact state π_S applied to all tasks:

```
V_single(t) = E_{s ~ F_t}[V(π_S*, s)]

π_S* = argmax_{π_S}  E_{s ~ F̄}[V(π_S, s)]
```

where F̄ = (1/T) Σ_t F_t is the time-averaged property distribution.

### Decoupled Evolution

We partition the property space S into regions {S_0, S_1, ..., S_K}:

```
π_S^(root)                         — stationary: artifacts effective across all of S
{Δ^(k)}_{k=1}^K                   — non-stationary: specialization for region S_k
π_S^(k) = π_S^(root) ⊕ Δ^(k)     — materialized state for tasks in S_k
π_S^(0) = π_S^(root)              — tasks with no matching branch use root only
```

**Two evolution objectives:**

```
Root (stationary):     max_{π_S^(root)}  E_{s ~ F̄}[V(π_S^(root), s)]
Branch k:              max_{Δ^(k)}  E_{s ~ F̄|_{S_k}}[V(π_S^(root) ⊕ Δ^(k), s)]
```

**Navigation:**

```
k_t = F_Navigate(x_t, T) = argmax_{k ∈ {0,...,K}}  E[R((π_θ, π_S^(k)), x_t)]
```

**Branching condition:**

```
∃ S' ⊂ S_k :  E_{s ∈ S'}[V(π_S^(k), s)]  <<  E_{s ∈ S'}[max_Δ V(π_S^(k) ⊕ Δ, s)]
```

**Promotion condition:**

```
E_{s ~ F̄|_{S_parent}}[V(π_S^(parent) ⊕ Δ^(k), s)]  ≥  E_{s ~ F̄|_{S_parent}}[V(π_S^(parent), s)]
```

**Degrades to A-Evolve** when F_t ≈ F (static), K = 0.

---

## Instantiation: Git-Managed Strategy Tree

The evolution state is a **git repository** where:
- The **main branch** is the root node — it holds stationary knowledge.
- **Commits on main** are stationary improvements.
- **Feature branches** are child nodes — non-stationary adaptations.

```
main (root node: stationary knowledge)
│
│  commit: "add flag verification tool"
│  commit: "add illiquidity detection"
│  commit: "add temporal disambiguation for search"
│
├── branch/algebraic-reasoning (child: forked from main, for RSA/ECC)
│   │  commit: "add RSA factoring tool"
│   │  commit: "add ECC discrete log skill"
│
├── branch/skip-illiquid (child: forked from main, for untradeable markets)
│   │  commit: "add volume-based skip rule"
│
└── branch/platform-data (child: forked from main, for Chinese rankings)
    │  commit: "add Maoyan/Douban query strategy"
```

**Main = root node.** Shared foundation. All branches inherit via rebase.

**Every node is a complete workspace.** Checking out any branch produces a
valid agent workspace.

**Degrades to single-path.** No branches = A-Evolve's linear chain.

---

## Two Evolution Modes

**Deepen main** — stationary failure (recurs across batches):
- CTF: flag verification tool. PolyBench: illiquidity detector. FutureX: temporal disambiguation.
- Signal: recurrence across batches/regimes.
- Git: `git commit` on main → `git rebase` all branches.

**Branch** — non-stationary (approach mismatch):
- CTF: RSA/ECC tools. PolyBench: skip-illiquid. FutureX: platform-data strategy.
- Signal: trajectory shows wrong approach for task properties.
- Git: `git checkout -b` from main → `git commit` on branch.

---

## Solver: Per-Task Navigation

```
SOLVE(task x_t, tree T):
  leaf_t ← F_NAVIGATE(x_t, T)
  git checkout leaf_t
  π_t ← load_workspace()
  τ_t ← AGENT.solve(x_t, π_t)
  f_t ← BENCHMARK.evaluate(x_t, τ_t)
  return (τ_t, f_t, leaf_t)
```

## Evolver: Adaptive Tree Evolution

```
EVOLVE(batch B, tree T):
  # B = [(x₁, τ₁, f₁, leaf₁), ...] from SOLVE

  # 1. Diagnose
  diag ← F_EVALUATE(B)

  # 2. Classify failures
  stationary  ← []
  nonstationary ← {}
  for (x, τ, f, leaf) in B where f.failed:
    if diag.is_recurrent(f, across=T.history):
      stationary.append((x, τ, f))
    elif diag.approach_mismatch(leaf, τ):
      nonstationary.setdefault(leaf, []).append((x, τ, f))

  # 3. Deepen main
  if stationary:
    git checkout main
    Δ ← F_EVOLVE(main, stationary, diag)
    if VALIDATE_CROSS_REGION(Δ, T):
      git commit -m "stationary: {Δ.summary}"
      for br in T.branches:
        git checkout br && git rebase main

  # 4. Branch
  for leaf, failures in nonstationary:
    target ← T.find_branch_by_properties(s(failures))
    if target is None:
      git checkout -b new_branch main
      target ← new_branch
    git checkout target
    Δ ← F_EVOLVE(target, failures, diag)
    if VALIDATE_WITHIN_REGION(Δ, target):
      git commit -m "adapt: {Δ.summary}"

  # 5. Promote
  for br in T.branches:
    if VALIDATE_CROSS_REGION(br.diff, T):
      git checkout main && git merge br
      git branch -d br

  # 6. Lifecycle
  for br in T.branches:
    if br.last_routed > staleness_window:
      git branch -d br

  # 7. Evolve navigation
  routing_log ← [(x, s(x), leaf, f.score) for (x, τ, f, leaf) in B]
  git checkout main
  Δ_nav ← F_EVOLVE_NAV(routing_log, T)
  if Δ_nav:
    git commit -m "nav: {Δ_nav.summary}"

  return T
```

---

## Theoretical Analysis: Why Single-Path Evolution Is Suboptimal

### Single-Path Performance

```
V_single(t) = E_{s ~ F_t}[V(π_S*, s)]
π_S* = argmax_{π_S}  E_{s ~ F̄}[V(π_S, s)]
```

### Decoupled Performance

```
V_decouple(t) = Σ_k  P_{F_t}(s ∈ S_k) · E_{s ~ F_t|_{S_k}}[V(π_S^(root) ⊕ Δ^(k)*, s)]
Δ^(k)* = argmax_Δ  E_{s ∈ S_k}[V(π_S^(root) ⊕ Δ, s)]
```

### Performance Gap

**Proposition.** V_decouple(t) ≥ V_single(t) for all t.

```
Gap(t) = Σ_k  P_{F_t}(s ∈ S_k) · E_{s ∈ S_k}[V(π_S^(root) ⊕ Δ^(k)*, s) - V(π_S*, s)]
```

The gap is large when: (1) different property regions require different
strategies, (2) F_t concentrates on regions where π_S* is weak, (3) the
single-path compromise is far from any region's optimum.

### The Over-Adaptation / Under-Adaptation Dilemma

```
π_S^(t+1) = π_S^(t) ⊕ Δ_t
```

**Over-adaptation:** Δ_t specializes for the dominant region in F_t,
degrading other regions in F_{t+1}.

**Under-adaptation:** Δ_t avoids region-specific changes, achieving nothing.

**Decoupled escape:**

```
Single-path:   π_S^(t+1) = π_S^(t) ⊕ Δ_t       (serves all, helps none fully)
Decoupled:     π_S^(root) ⊕ Δ_root              (stationary, benefits all)
               Δ^(k) ⊕ Δ_k                      (region k only, no interference)
```
