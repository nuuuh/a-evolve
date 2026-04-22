# Agentic Evolution and Navigation

## Problem

Current LLM agents are trained on general corpora, then deployed into specific domains with specific APIs, failure modes, and operational constraints — the **train-deploy gap** (A-Evolve). Agentic evolution (A-Evolve) established that deployment-time adaptation should be performed by an autonomous evolver agent, not a fixed heuristic. This is the right foundation — but A-Evolve's evolver operates on a linear chain of artifact updates, with no mechanism to explore alternative evolution paths, no domain-specific evaluation beyond pass rate, and no infrastructure-level modifications.

DGM extends the scope to full-codebase evolution with an archive-based search, demonstrating that system-level self-improvement works (SWE-bench 20% → 50%). But DGM is designed for offline benchmark optimization: evaluation is `count(pass)/count(total)`, search is unguided (unconstrained code diffs into a flat archive), and there is no regression protection.

**Our position:** A-Evolve made evolution agentic. We argue that in the deploy-gap setting, **navigation of the evolution search space must also be agentic** — because the signals that drive the search (domain-specific value and diagnostic signals) are non-trivial to acquire, requiring the same tool use and multi-step reasoning that makes evolution itself agentic.

---

## Motivations

### M1. The train-deploy gap is an infrastructure problem, not just an artifact problem.

Our SWE-bench analysis shows every effective intervention was an infrastructure change (verification stage, dynamic loading, adaptive triggering). DGM confirms this at scale — its top discoveries are all infrastructure: patch validation, granular editing, context management, multi-attempt strategies. But DGM finds *general* infrastructure improvements that work across any coding task. Deployment domains need *specific* infrastructure: SWE needs tight edit-test-feedback loops, MCP needs scoped tool routing, Terminal needs persistent state tracking. Closing the train-deploy gap means evolving domain-appropriate infrastructure, not just generally better code. This requires expanding A-Evolve's evolvable state from artifacts to the full system — pipeline topology, control flow, stage parameters, and artifacts together.

### M2. Scaling system-level evolution requires structured search with non-degradation guarantees.

Expanding the evolvable scope from artifacts to full infrastructure (M1) dramatically enlarges the configuration space. A-Evolve's linear chain cannot explore this space — it follows a single path with no ability to try alternatives or recover from bad steps. DGM addresses this with a flat archive, but provides no mechanism to ensure each step actually improves the system. Its `keep_all` archive admits variants that regress on existing tasks, and these regressions compound as modifications chain — a regressed variant becomes a parent, propagating degradation forward. Our SWE-bench data shows this concretely: 69% of regressions come from agents that solve faster but wrong (premature confidence), and 3 tasks regress across 7/8 experiments with the same wrong approach. Navigating a large configuration space while ensuring consistent improvement requires a **versioned search structure** (tree, not linear chain or flat archive) with branching for exploration, fallback for safety, and history to learn from past attempts.

### M3. Domain-specific evolution signals are essential and non-trivial to acquire.

Even with the right search structure (M2), the search must be **guided** — and the signals that guide it cannot be reduced to a simple outcome metric. DGM, ADAS, and other evolutionary approaches use **outcome-level** feedback — final benchmark pass rate — to accept or reject modifications. This is analogous to outcome reward models (ORMs) in reasoning: the system knows *whether* it improved but not *why* or *what to fix next*. The evolver proposes modifications into an unconstrained space, evaluates the result, and discards failures without extracting actionable signal from them.

This is a well-known limitation. In mathematical reasoning, process reward models (PRMs) that supervise individual reasoning steps consistently outperform ORMs that only check the final answer (Lightman et al., 2023). In neural architecture search, predictor-based methods that model per-operation contribution (e.g., DARTS, surrogate models) are more sample-efficient than evolution that only sees final accuracy. The pattern is general: when evaluation is expensive and the action space is large, modeling the **per-step improvement** — not just the final outcome — is essential for efficient search.

In system-level evolution, the equivalent of process supervision is **behavioral diagnostics**: not just "did pass rate change?" but "what solving behaviors changed and how?" — premature submission rate, context utilization, failure clustering, turn efficiency. These signals both **guide the search** (which node in the tree to expand, which modification to prioritize) and **constrain the evolution** (mapping observed failure patterns to specific infrastructure modifications).

Critically, in deployment domains, acquiring these signals is itself **non-trivial**. "Is this configuration better?" cannot be answered by `count(pass)/count(total)` — it requires analyzing solving trajectories, extracting behavioral patterns, and synthesizing a domain-specific judgment. This acquisition process requires tool use and multi-step reasoning — it must be agentic. **The evolution signal that guides the search is as hard to compute as the evolution step itself.** This is the fundamental reason navigation must be agentic in the deploy-gap setting.

---

## Framework: Agentic Evolution and Navigation

### Extending A-Evolve

A-Evolve defines the solve-evolve loop with one agentic function:

```
Solve:    τ_t = Solve(π_t, x_t)
Evolve:   Δ_t = F_Evolve(π_t, Obs_{1:t})           ← AGENTIC
Commit:   c_t = C(π_t, Δ_t)
```

Where `π_t = (π_θ, π_{S,t})` is the composite policy (frozen LLM + artifact state), and `F_Evolve` is the evolver agent that diagnoses, plans, updates, and verifies.

We extend this in two ways:

**Extended state.** Include system infrastructure in the evolvable state:

```
π_t = (π_θ, π_{S,t}, π_{I,t})
```

Where `π_I` is the pipeline infrastructure — stage topology, control flow, parameters, context management. A-Evolve's `F_Evolve` modifies only `π_S`. Our framework modifies both `π_S` and `π_I`.

**Versioned tree.** Replace A-Evolve's linear chain with a versioned tree `T` (realized as a git repository), maintaining an active configuration `π*` (main branch head). The tree enables branching (explore alternatives), fallback (revert on degradation), and history (learn from past attempts).

### The Evolution-Navigation Loop

```
Solve:       τ_t = Solve(π*, x_t)

Evaluate:    (v_t, d_t) = F_Evaluate(τ_t, π*, D)         ← AGENTIC

Navigate:    (π†, p_t) = F_Navigate(T, v_{1:t}, d_{1:t})  ← AGENTIC

Evolve:      Δ_t = F_Evolve(π†, d_t, p_t)                 ← AGENTIC

Update:      T, π* = Update(T, π†, Δ_t, v_t)
```

Three agentic functions instead of one. Each is agentic for a specific reason.

### F_Evaluate: Agentic Value and Diagnostic Acquisition

```
F_Evaluate: (trajectories, configuration, domain) → (value, diagnostics)
```

**Why agentic (M2).** In benchmark optimization, evaluation is trivial: `v = count(pass)/count(total)`. In deployment, the value signal `v_t` and diagnostic signal `d_t` are domain-specific and require multi-step reasoning and tool use to acquire:

- Analyzing solving trajectories to extract behavioral patterns (tool use: reading logs, running analysis scripts)
- Computing domain-specific metrics with no closed-form definition (reasoning: "is 12 turns premature submission or efficient solving?")
- Comparing against parent configuration on specific failure modes (reasoning: "which tasks regressed and why?")
- Synthesizing a composite judgment (reasoning: "is 2% accuracy gain worth 3x cost increase in this domain?")

`F_Evaluate` produces two signals:

```
v_t ∈ ℝ       — domain-specific composite value
d_t ∈ ℝ^m     — behavioral diagnostic vector
```

The value `v_t` drives selection (which configurations are good). The diagnostics `d_t` drive proposals (what to try next). Together, they are the **process-level feedback** that replaces outcome-only evaluation — analogous to PRMs replacing ORMs.

Examples of domain-specific `F_Evaluate`:

```
SWE:       v = solve_rate − α·regression_rate − β·avg_cost
           d = (premature_submit_rate, context_util, patch_quality, test_coverage_before_submit)

MCP:       v = tool_accuracy − α·api_error_rate − β·latency
           d = (routing_precision, auth_failure_rate, retry_rate, tool_coverage)

Terminal:  v = command_success − α·state_corruption − β·turns
           d = (idempotency_rate, error_recovery_rate, state_diff_size)
```

### F_Navigate: Agentic Search Navigation

```
F_Navigate: (tree, value_history, diagnostic_history) → (target_node, proposal_prior)
```

**Why agentic (M3).** Navigation decides *where in the tree to evolve next* and *what kind of modification to prioritize*. This requires:

- **Interpreting tree state**: which nodes have been explored, what scores they achieved, which diagnostics remain unaddressed — requires reasoning over the full search history
- **Strategic tradeoffs**: deepen the current best path (exploit) vs. branch from an ancestor to try a different direction (explore) — requires judgment about budget, confidence, and domain structure
- **Constructing the proposal prior** `p_t`: given the target node's diagnostics and the history of what's been tried, which modifications are most promising — requires domain-specific causal reasoning (what diagnostic maps to what action)

`F_Navigate` outputs:

```
π† ∈ T            — target node to modify (which point in the tree to branch from)
p_t: A → [0,1]   — prior over actions (which modifications to try first)
```

The prior `p_t` plays the role of the policy network in AlphaGo — it biases the search toward promising modifications before committing evaluation budget. But unlike a trained neural network, `p_t` is constructed agentically through domain-specific reasoning over behavioral diagnostics.

The search strategy that `F_Navigate` implements is **not prescribed** — it can instantiate any search template (tree search, evolutionary, Bayesian, beam search) depending on the domain and budget. What is prescribed is that the navigation is agentic: the agent defines the scoring, constructs the priors, and makes strategic decisions about where to explore.

### F_Evolve: Agentic Update (from A-Evolve)

```
F_Evolve: (target_config, diagnostics, prior) → modification
```

Inherited from A-Evolve: Diagnose → Plan → Update → Verify. Extended to receive the navigation agent's diagnostic signal `d_t` and proposal prior `p_t`, which guide the modification toward domain-specific improvements. The evolver now modifies both artifacts `π_S` and infrastructure `π_I`.

### Update: Tree Maintenance with Non-Degradation

```
Update: (tree, target, modification, value) → (tree', active_config)
```

Non-agentic. Mechanical operations:

```
π' = Apply(π†, Δ_t)                              — create candidate (git commit on branch)
(v', d') = F_Evaluate(Solve(π', x), π', D)       — evaluate candidate
T' = T ∪ {π', history(Δ_t, v', d')}              — add to tree with full record
π* = π'    if v' ≥ v(π†) − ε                      — advance main if non-degrading
     π†    otherwise                               — fallback to parent
```

The non-degradation rule: **main branch only advances on validated improvements.** Failed branches are retained in the tree as negative evidence — they inform `F_Navigate`'s future decisions ("we tried AddStage(verify) from π₁ and it didn't help because..."). Nothing is lost; the tree grows monotonically in knowledge even when individual branches fail.

### The Progression

```
                              Agentic          Search        Evolvable
                              Functions        Structure     Scope
                              ─────────        ─────────     ──────────
Manual design:                0                none          —
Agentic Evolution (A-Evolve): F_Evolve         linear        artifacts π_S
Agentic Evolution and         F_Evaluate       versioned     artifacts π_S +
  Navigation (ours):          F_Navigate       tree          infrastructure π_I
                              F_Evolve
```

A-Evolve's insight: *what to change* requires agency. Our insight: in the deploy-gap setting, *how to evaluate* and *where to search* also require agency — because domain-specific value and policy signals are non-trivial to acquire, requiring the same tool use and multi-step reasoning that makes evolution itself agentic.

### Navigation-Scaling Hypothesis

A-Evolve proposes the evolution-scaling hypothesis: `P*(C_evolve)` is monotonically increasing — more evolution compute yields better performance.

We refine this: **how evolution compute is allocated matters as much as how much is spent.** Navigation determines the allocation — which configurations to evaluate, how deeply, in what order. The navigation-scaling hypothesis:

```
P*(C_evolve, F_Navigate) ≥ P*(C_evolve, linear)     for all C_evolve
```

Guided navigation over a versioned tree achieves at least as good performance as linear evolution for the same budget, and strictly better when the configuration space is large (system-level evolution) or the domain requires specific infrastructure adaptations (deploy-gap setting). Agentic navigation is the mechanism that makes A-Evolve's evolution-scaling hypothesis efficient.

---

## Contributions

### C1. The agentic evolution and navigation paradigm.

We extend A-Evolve's agentic evolution framework with **agentic navigation** — strategic, agent-driven search over the space of system configurations. Where A-Evolve introduced one agentic function (`F_Evolve`: what to change), we introduce two more: `F_Evaluate` (domain-specific value and diagnostic acquisition) and `F_Navigate` (strategic tree navigation and proposal prior construction). The key argument: in the deploy-gap setting, the value and policy signals that guide evolution are non-trivial to compute — they require tool use and multi-step reasoning over deployment-specific data — making navigation inherently agentic. The paradigm expands A-Evolve's evolvable scope from artifacts to full system infrastructure, and replaces the linear evolution chain with a versioned tree that enables exploration, fallback, and history-informed search.

### C2. Domain-specific process-level evaluation as agentic function.

We formalize `F_Evaluate` as an agentic process that acquires domain-specific value and diagnostic signals from solving trajectories — analogous to process reward models (PRMs) replacing outcome reward models (ORMs). Unlike DGM's fixed `count(pass)/count(total)`, `F_Evaluate` extracts behavioral diagnostics (premature submission rate, context utilization, failure clustering, etc.) through multi-step analysis. These diagnostics serve dual purpose: they provide the value signal for navigation (which configurations are good) and the directional signal for evolution (what to change next). Different deployment domains define different diagnostics — the framework does not prescribe metrics but provides the structure for domain-specific agentic evaluation.

### C3. Versioned tree search with non-degradation guarantees.

We propose maintaining evolution history as a versioned tree (git repository) with a **parent-fallback rule**: the active configuration (main branch) only advances when a candidate is validated as non-degrading. Failed branches are retained as negative evidence for future navigation. This provides a structural guarantee absent from both A-Evolve (linear chain, no rollback) and DGM (flat archive, no regression protection): the system's deployed configuration never degrades beyond a bounded tolerance, while the tree accumulates knowledge from all attempts — successful and failed — to inform future search.

### C4. Empirical analysis of the train-deploy gap under agentic evolution.

We provide a comprehensive empirical study across deployment-representative benchmarks (SWE-bench, Terminal-bench, MCP-bench) demonstrating: (1) artifact-only evolution (A-Evolve) fails to close the train-deploy gap — no evolution experiment beats baseline on SWE-bench despite 101x prompt growth and 60-100% wasted evolution time; (2) every effective intervention is an infrastructure change that artifact evolution cannot produce; (3) behavioral diagnostics identify specific failure patterns (premature submission, context waste, approach fixation) that map to concrete infrastructure modifications — validating the need for agentic evaluation (`F_Evaluate`) over outcome-only feedback.

---

## Related Work

| System | Agentic Functions | Search Structure | Evaluation | Scope | Degradation Protection |
|---|---|---|---|---|---|
| **A-Evolve** | F_Evolve | Linear chain | Outcome (pass rate) | Artifacts | Governance gate |
| **ADAS** | Meta-agent (fixed) | Forward archive | Outcome (held-out) | Full agent code | None |
| **AFlow** | LLM expansion | MCTS | Outcome (rollouts) | Workflow operators | None |
| **DGM** | F_Evolve + diagnosis | Flat archive | Outcome (staged pass rate) | Full codebase | None (keep-all) |
| **Ours** | F_Evaluate + F_Navigate + F_Evolve | Versioned tree | Process (behavioral diagnostics) | System infrastructure | Parent-fallback |

**Key distinctions:**
- **vs. A-Evolve:** A-Evolve makes evolution agentic; we additionally make evaluation and navigation agentic. A-Evolve evolves artifacts linearly; we evolve infrastructure over a versioned tree.
- **vs. DGM:** DGM evolves general capabilities on a fixed benchmark with outcome-only feedback; we evolve domain-specific infrastructure with process-level feedback. DGM's flat archive has no regression protection; our versioned tree enforces non-degradation.
- **vs. AFlow:** AFlow applies MCTS to workflow search but with fixed evaluation (outcome-only rollouts); we make both the search navigation and the evaluation agentic and domain-specific.