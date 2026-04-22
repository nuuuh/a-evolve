# F_Evaluate as Reward Model for RL Training of the Solver

## Motivation

The agentic evolution and navigation framework produces domain-specific process-level signals through `F_Evaluate`. These signals currently serve two purposes: guiding navigation (which configuration to explore) and guiding evolution (what infrastructure to modify). But the same signals can also train the **solver model itself** via reinforcement learning — closing a third optimization loop that adapts the model parameters `π_θ`, not just the artifacts `π_S` and infrastructure `π_I`.

A-Evolve keeps `π_θ` frozen and adapts only through non-parametric artifacts. Our framework additionally adapts infrastructure. RL training using `F_Evaluate`'s output would add **parametric adaptation**:

```
Level 1: Evolution     — modify π_S, π_I (artifacts + infrastructure)   ← A-Evolve + ours
Level 2: Navigation    — search over configurations                     ← ours
Level 3: RL training   — modify π_θ (model parameters)                 ← extension
```

---

## F_Evaluate as a Dense Reward Signal

In standard RL for LLMs (RLHF, RLVR), the reward is typically sparse:

```
r(τ) = 𝟙[task solved]     — binary, sparse
```

Most trajectory groups contain all failures or all successes, yielding zero gradient (all advantages equal zero within the group).

`F_Evaluate` provides a fundamentally denser signal:

```
r(τ) = v(τ) = f(solve_rate, regression_rate, premature_rate, context_util, turn_efficiency, ...)
```

Even within a group of all-failing trajectories, `F_Evaluate` differentiates: one trajectory tried more tests before submitting, another explored more approaches, another used context more efficiently. These differences provide non-zero advantages and meaningful gradients.

This is the PRM vs ORM distinction applied to RL training:

| | Reward signal | RL efficiency | Information per trajectory |
|---|---|---|---|
| ORM-based RL | pass/fail (binary) | Low — most groups have degenerate advantages | 1 bit |
| PRM-based RL (F_Evaluate) | per-stage diagnostics | Higher — continuous signal even within all-fail groups | m-dimensional diagnostic vector |

---

## Connection to GRPO

GRPO (Group Relative Policy Optimization; DeepSeek-R1, Shao et al. 2024) is particularly natural for this extension.

**Standard GRPO:**

1. For prompt `x`, sample group of `G` outputs `{y₁,...,y_G}` from policy `π_θ`
2. Score each: `rᵢ = R(x, yᵢ)`
3. Group-relative advantage: `Âᵢ = (rᵢ − μ_r) / σ_r`
4. Policy gradient: `∇J ≈ (1/G) Σᵢ Âᵢ · ∇log π_θ(yᵢ|x)`
5. KL penalty: `L = ∇J − β · KL(π_θ || π_ref)`

No separate critic/value network needed — group statistics serve as baseline.

**Our instantiation (F_Evaluate as reward model):**

1. For task `t`, solver produces `G` trajectories `{τ₁,...,τ_G}` under configuration `π`
2. `F_Evaluate` scores each: `(vᵢ, dᵢ) = F_Evaluate(τᵢ, π, D)`
3. Group-relative advantage using composite value: `Âᵢ = (vᵢ − μ_v) / σ_v`
4. Policy gradient on the solver's LLM backbone
5. KL penalty against the pre-deployment model

The mapping:

```
GRPO component          Our instantiation
─────────────           ─────────────────
Reward model R(x,y)     F_Evaluate(τ, π, D) — agentic, domain-specific
Group sampling          Multiple solver trajectories per task
Advantage               Group-relative v_t scores
Policy                  Solver LLM π_θ
Reference policy        Pre-deployment model
```

**Key advantage over standard GRPO:** The reward model is not a trained neural network — it is an **agentic process** (`F_Evaluate`) that uses tool use and multi-step reasoning to compute domain-specific scores. This means:
- No reward model training required (no reward hacking risk from a learned reward model)
- Reward adapts automatically to new domains (F_Evaluate reasons about domain-specific diagnostics)
- Reward captures process-level information (not just outcome)

---

## Connection to Other RL Methods

### PPO (Proximal Policy Optimization)

`F_Evaluate` can serve as the value function `V(s)` for PPO. The diagnostic vector at each stage of solving provides state-dependent value estimates:

```
V(s_t) ≈ f(diagnostics at stage t) = predicted final outcome given current solving state
```

This replaces the learned critic with an agentic evaluator. The advantage estimate becomes:

```
A_t = r_t + γV(s_{t+1}) − V(s_t)
```

where `r_t` is the per-stage reward from `F_Evaluate`'s diagnostic decomposition.

### DPO (Direct Preference Optimization)

`F_Evaluate` naturally creates preference pairs without a separate reward model:

```
Given two trajectories τ_w, τ_l for the same task:
    τ_w ≻ τ_l  iff  v(τ_w) > v(τ_l)
```

The DPO loss:

```
L_DPO = −E[log σ(β(log π_θ(τ_w|x) − log π_ref(τ_w|x)) − β(log π_θ(τ_l|x) − log π_ref(τ_l|x)))]
```

With `F_Evaluate`, the preference ordering is richer than pass/fail — two failing trajectories can still be ordered by diagnostic quality (one that ran tests before submitting is preferred over one that submitted immediately).

### RLVR (RL with Verifiable Rewards)

DeepSeek-R1 uses verifiable rewards (math correctness, code test passing) as the RL signal. Our extension: use verifiable outcomes **plus behavioral diagnostics**:

```
RLVR:    r = 𝟙[tests pass]
Ours:    r = 𝟙[tests pass] + w₁·verification_depth + w₂·context_efficiency + ...
```

The verification is a subset of what `F_Evaluate` computes. The diagnostics provide additional signal that shapes *how* the model solves, not just *whether* it solves.

### Process Reward Models (Lightman et al., 2023)

Standard PRMs are trained on human-labeled step-level correctness for math reasoning. Our per-stage diagnostics serve the same role but are:
- **Agentic**: computed by `F_Evaluate` through tool use and reasoning, not a trained classifier
- **Domain-specific**: automatically adapted to the deployment environment
- **Not human-labeled**: derived from trajectory analysis, not manual annotation

The parallel:

```
Math PRM:    r(step_i) = P(step_i is correct)         — trained on human labels
Our PRM:     r(stage_j) = diagnostic_quality(stage_j)  — computed by F_Evaluate
```

---

## The Triple-Duty Architecture

`F_Evaluate` serves three consumers with the same domain-specific process signals:

```
F_Evaluate(τ, π, D) → (v, d)
                          │
           ┌──────────────┼──────────────┐
           ↓              ↓              ↓
    Navigation       Evolution      RL Training
    (where to       (what infra    (update π_θ
     search)        to modify)     parameters)
    F_Navigate      F_Evolve       GRPO/PPO/DPO
```

### Shared Information, Different Consumers

| Consumer | Uses `v` (value) for | Uses `d` (diagnostics) for |
|---|---|---|
| Navigation | Scoring nodes in the tree, UCB selection | Diagnostic potential Φ, proposal prior `p_t` |
| Evolution | Acceptance test (parent-fallback) | Diagnostic-to-action mapping, guiding F_Evolve |
| RL Training | Reward signal for GRPO/PPO advantage | Per-stage reward shaping, process reward |

### Theoretical Connection

Theorem 1 (Fisher information gain) applies to all three consumers: process feedback provides `I_proc = I_out + κᵀΣ_ξ⁻¹κ` information per evaluation, and this information benefits:
- Navigation: fewer evaluations needed to select the right node (Theorem 3, regret bound)
- Evolution: fewer evaluations needed to validate a modification (Theorem 2, submartingale)
- RL training: denser reward signal → lower variance policy gradients → faster convergence

For RL specifically, the variance reduction can be quantified. The policy gradient variance under GRPO with outcome-only reward:

```
Var(∇J_out) ∝ Var(r_out) · E[||∇log π||²]
```

Under process-enriched reward:

```
Var(∇J_proc) ∝ Var(r_proc) · E[||∇log π||²]
```

When `Var(r_proc) < Var(r_out)` (process reward has lower variance because it uses more information per trajectory), the policy gradient has lower variance, leading to faster and more stable RL training.

---

## Connection to Research Plan

### S1 (Evolver Optimization)

RL training of the solver using `F_Evaluate` is a form of **evolver-guided parametric improvement**: the evolution system's diagnostic signals directly shape the solver's behavior through parameter updates, not just artifact/infrastructure changes. This is S1.2 (offline evolver training) realized — but instead of training the evolver, we train the solver using the evolver's evaluation signals.

### S4 (Privacy/Efficiency)

If `F_Evaluate`'s signals can train a smaller model to solve as well as a larger model with evolved artifacts, this is **distillation through evolution**:

```
Phase 1: Large model + evolved artifacts + evolved infrastructure → good performance
Phase 2: F_Evaluate scores trajectories → RL trains smaller model
Phase 3: Smaller model internalizes the infrastructure's benefits → artifacts/infrastructure less needed
```

The long-term vision: evolution discovers domain-specific infrastructure → RL distills the infrastructure's benefits into model parameters → the model becomes self-sufficient → evolution moves to the next frontier.

### Dual-Loop Optimization

The two loops are complementary:

```
Evolution loop (fast, non-parametric):
    Adapts infrastructure and artifacts
    No gradient computation
    Bounded by what artifacts/infrastructure can express

RL loop (slow, parametric):
    Adapts model parameters
    Requires gradient computation
    Bounded by model capacity and training data
```

Evolution provides the exploration (discovering what works) and RL provides the consolidation (compiling discoveries into parameters). This mirrors the relationship between System 1 (fast, learned) and System 2 (slow, deliberate) reasoning — evolution is the deliberate search, RL compiles the results into fast model behavior.

---

## Open Questions

1. **Training frequency.** How often should RL training run relative to evolution cycles? Evolution discovers new infrastructure → new solving patterns → new training signal. Training too early wastes compute on a shifting reward landscape; training too late fails to consolidate gains.

2. **Reward composition.** How to weight the diagnostic components in the RL reward? The optimal weighting for navigation (Theorem 3, minimizing regret) may differ from the optimal weighting for RL training (minimizing policy gradient variance). Should the weights be shared or independently tuned?

3. **Catastrophic forgetting.** RL training on domain-specific `F_Evaluate` signals may specialize the solver to the current domain at the cost of general capability. KL penalty against the reference model mitigates this, but the optimal `β` depends on how domain-specific the deployment is.

4. **Self-referential loop.** If RL improves the solver, and the solver's improved trajectories change `F_Evaluate`'s diagnostics, which change the RL reward signal... is this loop stable? Under what conditions does it converge? This connects to the fixed-point analysis of self-improving systems (DGM, Schmidhuber's Gödel Machine).

5. **When is RL better than evolution?** Evolution adapts infrastructure (routing, verification, context management) — things that can be expressed as code. RL adapts model behavior (reasoning patterns, tool use habits, exploration strategies) — things that live in parameters. When does each loop contribute more? Is there a phase transition as the system matures (early: evolution-dominated; late: RL-dominated)?