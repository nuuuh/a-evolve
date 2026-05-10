# Conceptual Framework: Bounded Harness Construction under Non-Stationarity

## Note on this section

This section provides a *conceptual framework* — a regret decomposition that names and separates two distinct sources of failure in self-evolving agents. It is **not** a quantitative theory: only the navigation-loss side admits empirically meaningful predictions, while the evolution-loss side is best understood as a diagnostic vocabulary that organizes our architectural contributions. We address this asymmetry explicitly in §2.2.5. A third failure mode — *experience insufficiency* — sits outside the loss decomposition and motivates a separate intervention (HITL).

---

## Setting

A stream of tasks indexed by time:

$$x_1, x_2, \ldots, x_T, \quad x_t \sim P_t$$

where $P_t$ is the task distribution at time $t$, potentially shifting. Each task $x_t$ has a fixed ground truth $y^*(x_t)$.

The agent observes history:

$$\mathcal{H}_t = \{(x_1, r_1, \tau_1), \ldots, (x_{t-1}, r_{t-1}, \tau_{t-1})\}$$

and must produce action $a_t$ for task $x_t$.

---

## Definition 1: Harness, Utility, and Regret

> **Assumption.** The agent with full history can always do at least as well as the agent with the compressed harness, since $\mathcal{H}_t$ contains strictly more information, under the same agents.

A **harness** $C$ is a bounded representation constructed from history:

$$C = \varphi(\mathcal{H}_t), \quad |C| \leq K$$

where $K$ is the harness capacity (total size of prompts, tools, skills, memory, infrastructure).

**Utility of harness.** Each task $x$ has fixed ground truth $y^*(x)$. The agent's policy $\pi(a|x,C)$ is shaped by harness $C$. The utility is:

$$V(C, x) = \mathbb{E}_{a \sim \pi(a|x,C)}[r(a, y^*(x))]$$

The ground truth is fixed; stochasticity is in the agent (LLM sampling, reasoning paths). A better harness concentrates the agent's policy on correct actions → higher utility.

**Regret of harness.** The gap between full-history utility and harness-mediated utility:

$$\text{Regret}(\varphi, x_t) = V(\mathcal{H}_t, x_t) - V(\varphi(\mathcal{H}_t), x_t)$$

Non-negative: full history dominates any compressed harness in information content.

---

## Definition 2: Two Dimensions of Harness Construction

**Dimension 1: Construction quality** — what kinds of harnesses an evolver can build.

Given an evolver class $\Phi$, define the best achievable task-conditional harness:

$$C^*_\Phi(x) = \arg\max_{C : C = \varphi(\mathcal{H}_t, x), \varphi \in \Phi, |C| \leq K} V(C, x)$$

This is the best harness that evolver class $\Phi$ can build for task $x$ specifically, given capacity $K$.

**Dimension 2: Conditioning** — whether the harness depends on the current task.

- **Unconditional:** $C_t = \varphi(\mathcal{H}_t)$ — one harness for all tasks (linear evolution)
- **Conditional:** $C_t(x_t) = \varphi(\mathcal{H}_t, x_t)$ — harness adapted per task (navigation)

---

## Proposition 1: Regret Decomposition

For any evolver $\varphi \in \Phi$ producing an unconditional harness with capacity $K$, the expected regret decomposes as:

$$\mathbb{E}_{x_t \sim P_t}[\text{Regret}(\varphi, x_t)] = \underbrace{L_{\text{evo}}(\Phi, K)}_{\text{evolution loss}} + \underbrace{L_{\text{nav}}(\varphi)}_{\text{navigation loss}}$$

where:

$$L_{\text{evo}}(\Phi, K) = \mathbb{E}_{x_t}\left[ V(\mathcal{H}_t, x_t) - V(C^*_\Phi(x_t), x_t) \right]$$

is the loss from the **evolver class limitation** — even the best task-conditional harness within $\Phi$ at capacity $K$ cannot fully recover what full history provides. And:

$$L_{\text{nav}}(\varphi) = \mathbb{E}_{x_t}\left[ V(C^*_\Phi(x_t), x_t) - V(\varphi(\mathcal{H}_t), x_t) \right]$$

is the loss from using a **single unconditional harness** instead of the best task-conditional harness.

**Derivation.** Insert the intermediate term $V(C^*_\Phi(x_t), x_t)$ into the regret expression and split. Non-negativity of both terms follows from $V(\mathcal{H}_t, x_t) \geq V(C^*_\Phi(x_t), x_t) \geq V(\varphi(\mathcal{H}_t), x_t)$ — the first inequality by information dominance, the second by per-task optimality of $C^*_\Phi$ over any unconditional harness. $\square$

**Status of this result.** Proposition 1 is a definitional partition of regret, not a non-trivial mathematical theorem. Its value is in the vocabulary it provides for the rest of the paper: two distinct, separately addressable sources of failure.

**Interpretation.**
- $L_{\text{evo}}$: the evolver is not capable enough — even with task-specific tuning, it cannot encode all relevant information from history into capacity $K$. **Reduced by stronger evolvers.**
- $L_{\text{nav}}$: the harness is not task-specific — one harness cannot be simultaneously optimal for all tasks. **Reduced by conditioning on the current task.**

---

## Proposition 2: Stationarity Eliminates Navigation Loss

**Stationarity.** The task stream is stationary if there exists a single harness $C^*$ such that:

$$C^* = \arg\max_{C: |C| \leq K} V(C, x) \quad \text{for all } x \in \text{support}(P_t)$$

(The same harness is optimal for every task.)

**Claim.** Under stationarity, $L_{\text{nav}} = 0$ for the optimal unconditional harness.

**Why.** Under stationarity, $C^*_\Phi(x) = C^*$ for all $x$ — the per-task optimum is the same regardless of task. The optimal unconditional harness $\varphi^*(\mathcal{H}_t) = C^*$ achieves $V(\varphi^*(\mathcal{H}_t), x_t) = V(C^*_\Phi(x_t), x_t)$ for all $x_t$. $\square$

**Empirical prediction.** On stationary benchmarks, navigation should provide no benefit. This is consistent with linear-evolution methods (e.g., A-Evolve) succeeding on i.i.d. benchmarks without per-task conditioning.

**Corollary.** Under stationarity, only evolution quality matters. Stronger harness construction (reducing $L_{\text{evo}}$) is the sole improvement axis.

---

## Proposition 3: Navigation Loss Grows with Distribution Shift

**Harness divergence.** For two tasks $x, x'$, define:

$$d(x, x') = V(C^*_\Phi(x), x) + V(C^*_\Phi(x'), x') - V(C^*_\Phi(x), x') - V(C^*_\Phi(x'), x)$$

This measures how much two tasks **disagree on which harness is better**. If $d(x,x') = 0$, both tasks perform equally well under each other's optimal harness. If $d(x,x') > 0$, each task strictly prefers its own harness.

**Shift magnitude.** The expected divergence at time $t$:

$$\Sigma_t = \mathbb{E}_{x \sim P_t, \; x' \sim P_t}[d(x, x')]$$

**Claim.** Navigation loss is positive and monotone in shift magnitude:

$$\Sigma_t > 0 \implies L_{\text{nav}}(\varphi^*_{\text{uncond}}) > 0, \quad \text{and } L_{\text{nav}} \text{ grows with } \Sigma_t.$$

**Why (informal).** When $\Sigma_t > 0$, per-task optima for different tasks differ. No single unconditional $C^*$ can simultaneously achieve every task's per-task optimum — it must compromise. The compromise cost grows with how much tasks disagree on the right harness, i.e., with $\Sigma_t$. A precise lower-bound expression in terms of $\Sigma_t$ requires additional structure on the harness space (e.g., metric, capacity allocation across orthogonal sub-spaces) and is not pursued here.

**Status.** We use this proposition as a *qualitative* prediction. It is testable along two axes: across batches with varying measured shift (Proposition 3 static), and across time as shift accumulates (Proposition 4 dynamic).

**Empirical prediction (static).** Across batches with measured shift heterogeneity, navigation gain over unconditional grows with shift magnitude. Tested in RQ3.

---

## Proposition 4: Temporal Dynamics — Non-Monotonic Learning under Accumulating Shift

As tasks accumulate under non-stationarity, the supported task distribution diversifies and $\Sigma_t$ increases:

$$\frac{d\Sigma_t}{dt} > 0 \implies \frac{dL_{\text{nav}}}{dt} > 0$$

Even if the evolver learns over time (reducing $L_{\text{evo}}$), navigation loss grows. Total regret dynamics:

$$\frac{d}{dt}\mathbb{E}[\text{Regret}] = \underbrace{\frac{dL_{\text{evo}}}{dt}}_{\leq 0 \text{ (evolver learns)}} + \underbrace{\frac{dL_{\text{nav}}}{dt}}_{> 0 \text{ (shift accumulates)}}$$

**Empirical prediction.** Linear (unconditional) evolution should exhibit a **non-monotonic accuracy curve** over the temporal stream: improving while learning outpaces shift, then degrading when shift dominates. Conditional methods (navigation), which do not pay growing $L_{\text{nav}}$, should not exhibit this non-monotonicity.

This explains *why* early-freeze outperforms full-evolution in our experiments: stopping evolution before $L_{\text{nav}}$ overwhelms $L_{\text{evo}}$ gains. Tested in RQ3 (dynamic).

---

## Observation: Evolver Class Inclusion

If $\Phi_{\text{multi}} \supset \Phi_{\text{single}}$ (the multi-agent evolver class strictly contains the single-agent class), then by monotonicity of max:

$$L_{\text{evo}}(\Phi_{\text{multi}}, K) \leq L_{\text{evo}}(\Phi_{\text{single}}, K)$$

with strict inequality when the best harness for some task requires construction operations outside $\Phi_{\text{single}}$.

**Honest note on status.** This is **not a predictive theorem**; it follows directly from set inclusion ("max over a larger set ≥ max over a subset"). Critically:

- The evolver class $\Phi$ is **not naturally scalar** — there is no quantitative axis along which "evolver capability" can be measured. Model size, total compute, LLM call count, and number of agent roles are all proxies, none of which prior work uses consistently. Whether existing multi-step evolvers (A-Evolve, Metaharness, etc.) belong to $\Phi_{\text{single}}$ or $\Phi_{\text{multi}}$ is not a well-defined question.
- We therefore do **not** attempt to quantify $L_{\text{evo}}$ directly, nor to establish multi-agent's advantage via a class-expansion theorem.

Instead, our multi-agent contribution is characterized as a set of **specific architectural patterns** — persistent cross-cycle state, parallel independent research, role-distinct objectives — that (i) prior evolvers verifiably lack and (ii) enable construction of artifact types empirically observed to drive performance gains. See §2.4 for the patterns and RQ2 for empirical verification by ablation.

---

## Proposition 5: Orthogonality of L_evo and L_nav

The two losses act on independent terms of the decomposition:

- $L_{\text{evo}}(\Phi, K)$ depends only on what harnesses the evolver class can construct — *not* on whether conditioning is applied.
- $L_{\text{nav}}(\varphi)$ depends only on whether the harness is task-conditional — *not* on how capable the evolver is at building each individual harness.

Reducing one does not affect the other. The full system addresses both:

$$\mathbb{E}[\text{Regret}_{\text{multi+nav}}] = L_{\text{evo}}(\Phi_{\text{multi}}, K) + L_{\text{nav}}(\varphi_{\text{cond}})$$

**Empirical prediction.** In a 2×2 ablation (multi-agent on/off × navigation on/off), the gains should approximately add. Large interaction effects would falsify the orthogonality claim. Tested in RQ1's ablation rows.

**Regime corollary:**

| Regime | $L_{\text{evo}}$ | $L_{\text{nav}}$ | Reduces regret |
|---|---|---|---|
| Stationary, simple domain | Low | 0 | Neither needed |
| Stationary, complex domain | High | 0 | Stronger evolution only |
| Non-stationary, simple domain | Low | High | Navigation only |
| Non-stationary, complex domain | High | High | Both contributions |

---

## §2.2.5 Note on Methodological Asymmetry

The two sides of the regret decomposition admit different kinds of analysis, and we treat them differently in the rest of the paper:

**$L_{\text{nav}}$ side admits empirical predictions.** Navigation loss is driven by shift magnitude $\Sigma_t$, which is *measurable*: we can estimate per-batch task heterogeneity from oracle-branch gaps, compute task-embedding distances, or measure cross-batch performance transfer. Propositions 2–4 then yield falsifiable claims (no nav benefit on stationary streams; nav benefit grows with measured shift; non-monotonic curves under accumulation). RQ3 tests these as static and dynamic predictions on the same evolved tree.

**$L_{\text{evo}}$ side does not admit empirical predictions.** Evolver class capability has no natural scalar parameterization — "stronger evolver" is not a continuous axis. We cannot meaningfully claim "$L_{\text{evo}}$ decreases at rate X as evolver strength increases by Y" without inventing an arbitrary quantification. Our multi-agent contribution is therefore not derived from a class-expansion theorem; it is a set of specific architectural patterns (§2.4) whose value we demonstrate by ablation and artifact-type analysis (RQ2), not by theoretical bound.

This asymmetry is **faithful to the underlying problem structure**, not a weakness of the framework. Non-stationarity admits quantitative analysis because shift is measurable; open-endedness does not, because evolver capability is structural rather than scalar. The framework names both losses, makes one predictive, and uses the other as diagnostic vocabulary.

**A third failure mode sits outside both losses.** *Experience insufficiency* — the case where $\mathcal{H}_t$ contains no useful signal for $x_t$'s regime — is not captured by $L_{\text{evo}}$ or $L_{\text{nav}}$. No amount of evolver class expansion (which improves construction *given* signal) or task conditioning (which routes *among* extracted signal) helps when the input data carries no relevant signal at all. This regime motivates a third architectural intervention (HITL, §2.5) that supplies external direction at the evolver's input rather than acting on either loss term.

---

## Summary: Connection to Research Questions

| Conceptual claim | Status | Empirical validation |
|---|---|---|
| Decomposition $L_{\text{evo}} + L_{\text{nav}}$ (Prop 1) | Definitional vocabulary | Throughout paper |
| $L_{\text{nav}} = 0$ under stationarity (Prop 2) | Direct from definition | Why A-Evolve works on static benchmarks |
| $L_{\text{nav}}$ grows with shift (Prop 3) | Qualitative prediction | RQ3 (static) — addresses C1 |
| $dL_{\text{nav}}/dt > 0$ under accumulation (Prop 4) | Qualitative prediction | RQ3 (dynamic) — explains early-freeze (C1) |
| Multi-agent architectural patterns (Observation + §2.4) | Architectural claim, not theorem | RQ2 — addresses C2 |
| Orthogonality (Prop 5) | Definitional + empirical | 2×2 ablation in RQ1 |
| Experience insufficiency outside framework (§2.2.5) | Outside-of-decomposition | RQ4 — addresses C3 (HITL) |

---

## Interpretation for Self-Evolving Agent Readers

- **$L_{\text{evo}}$** = evolver capability bottleneck (what kinds of harnesses can be built?). Not naturally quantifiable; addressed by adding specific architectural patterns (persistent cross-cycle state, parallel research, role-distinct builder/verifier).
- **$L_{\text{nav}}$** = the per-task conditioning gap (does one harness fit all tasks?). Quantifiable through shift magnitude $\Sigma_t$; addressed by per-task harness routing (navigation).
- Linear evolution conflates both into one undifferentiated system; our decomposition makes both visible and separately improvable.
- A third failure mode — *experience insufficiency* under novel regimes — is structurally outside the framework: when $\mathcal{H}_t$ has no signal, no amount of evolver class expansion or task conditioning helps. This motivates **HITL as a third architectural intervention**, applied at evolver phase boundaries when historical signal runs out.

---

## A Note for Time-Series / Forecasting Readers (Optional)

The framework can be read in time-series language, though the analogy is loose:

- Harness ≈ fitted model / learned representation
- Evolution ≈ offline model training from historical data
- Navigation ≈ online model selection / test-time adaptation per instance
- HITL ≈ expert-in-the-loop for novel-regime detection
- Capacity $K$ ≈ model complexity budget
- Proposition 3 ≈ one-size-fits-all model becomes suboptimal under regime change
- Proposition 5 ≈ better training and adaptive selection are independently valuable

The core claims of the paper, however, are about agentic evolution specifically; the time-series mapping is provided only for orientation.
