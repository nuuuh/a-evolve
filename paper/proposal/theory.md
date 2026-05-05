# Theory: Bounded Harness Construction under Non-Stationarity

## Setting

A stream of tasks indexed by time:

$$x_1, x_2, \ldots, x_T, \quad x_t \sim P_t$$

where $P_t$ is the task distribution at time $t$, potentially shifting. Each task $x_t$ has a fixed ground truth $y^*(x_t)$.

The agent observes history:

$$\mathcal{H}_t = \{(x_1, r_1, \tau_1), \ldots, (x_{t-1}, r_{t-1}, \tau_{t-1})\}$$

and must produce action $a_t$ for task $x_t$.

---

## Definition 1: Harness and Utility

> **Assumption.** The agent with full history can always do at least as well as the agent with the compressed harness, since $\mathcal{H}_t$ contains strictly more information, under the same agents.

A **harness** $C$ is a bounded representation constructed from history:

$$C = \varphi(\mathcal{H}_t), \quad |C| \leq K$$

where $K$ is the harness capacity (total size of prompts, tools, skills, memory, infrastructure).

**Definition (Utility of harness).** Each task $x$ has fixed ground truth $y^*(x)$. The agent's policy $\pi(a|x,C)$ is a distribution over actions, shaped by the harness $C$. The utility of harness $C$ for task $x$:

$$V(C, x) = \mathbb{E}_{a \sim \pi(a|x,C)}[r(a, y^*(x))]$$

The ground truth is fixed. The stochasticity is in the **agent** (LLM sampling, reasoning paths), not the world. A better harness concentrates the agent's policy on correct actions → higher utility.

**Definition (Regret of harness).** The gap between the utility with full history and the utility with the harness:

$$\text{Regret}(\varphi, x_t) = V(\mathcal{H}_t, x_t) - V(\varphi(\mathcal{H}_t), x_t)$$

This is non-negative: the agent with full history can always do at least as well as the agent with a compressed harness, since $\mathcal{H}_t$ contains strictly more information.

---

## Definition 2: Two Dimensions of Harness Construction

**Dimension 1: Construction quality** — how effectively the evolver encodes task-relevant information into the harness.

Given an evolver class $\Phi$, define the best achievable task-conditional harness:

$$C^*_\Phi(x) = \arg\max_{C : C = \varphi(\mathcal{H}_t, x), \varphi \in \Phi, |C| \leq K} V(C, x)$$

This is the best harness that evolver class $\Phi$ can build for task $x$ specifically, given capacity $K$.

**Dimension 2: Conditioning** — whether the harness depends on the current task.

- **Unconditional:** $C_t = \varphi(\mathcal{H}_t)$ — one harness for all tasks (standard evolution)
- **Conditional:** $C_t(x_t) = \varphi(\mathcal{H}_t, x_t)$ — harness adapted to the current task (navigation)

---

## Theorem 1: Regret Decomposition

For any evolver $\varphi \in \Phi$ producing an unconditional harness with capacity $K$, the expected regret decomposes as:

$$\mathbb{E}_{x_t \sim P_t}[\text{Regret}(\varphi, x_t)] = \underbrace{L_{\text{evo}}(\Phi, K)}_{\text{evolution loss}} + \underbrace{L_{\text{nav}}(\varphi)}_{\text{navigation loss}}$$

where:

$$L_{\text{evo}}(\Phi, K) = \mathbb{E}_{x_t}\left[ V(\mathcal{H}_t, x_t) - V(C^*_\Phi(x_t), x_t) \right]$$

is the loss from the **evolver class limitation** — even the best task-conditional harness within $\Phi$ at capacity $K$ cannot fully recover what full history provides. And:

$$L_{\text{nav}}(\varphi) = \mathbb{E}_{x_t}\left[ V(C^*_\Phi(x_t), x_t) - V(\varphi(\mathcal{H}_t), x_t) \right]$$

is the loss from using a **single unconditional harness** instead of the best task-conditional harness.

**Proof:**

By non-negativity of regret components:

$$V(\mathcal{H}_t, x_t) \geq V(C^*_\Phi(x_t), x_t) \geq V(\varphi(\mathcal{H}_t), x_t)$$

The first inequality holds because $C^*_\Phi(x_t)$ is a compression of $\mathcal{H}_t$ (information can only be lost). The second holds because $C^*_\Phi(x_t)$ is the best harness for task $x_t$ specifically, while $\varphi(\mathcal{H}_t)$ must serve all tasks — it cannot be better for any specific task than the task-optimal harness.

Total regret:

$$V(\mathcal{H}_t, x_t) - V(\varphi(\mathcal{H}_t), x_t)$$

Insert the intermediate term $V(C^*_\Phi(x_t), x_t)$:

$$= \underbrace{\left[ V(\mathcal{H}_t, x_t) - V(C^*_\Phi(x_t), x_t) \right]}_{L_{\text{evo}}} + \underbrace{\left[ V(C^*_\Phi(x_t), x_t) - V(\varphi(\mathcal{H}_t), x_t) \right]}_{L_{\text{nav}}}$$

Taking expectation over $x_t \sim P_t$ yields the decomposition. $\square$

**Interpretation:**
- $L_{\text{evo}}$: the evolver is not capable enough — even with unlimited task-specific tuning, it cannot encode all relevant information from history into capacity $K$. **Reduced by stronger evolvers.**
- $L_{\text{nav}}$: the harness is not task-specific — one harness cannot be simultaneously optimal for all tasks. **Reduced by conditioning on the current task.**

---

## Theorem 2: Navigation Loss is Zero Under Stationarity

**Definition (Stationarity).** The task stream is stationary if all tasks in the support of $P_t$ benefit from the same harness content. Formally: there exists a single harness $C^*$ such that:

$$C^* = \arg\max_{C: |C| \leq K} V(C, x) \quad \text{for all } x \in \text{support}(P_t)$$

(The same harness is optimal for every task.)

**Theorem.** Under stationarity, $L_{\text{nav}} = 0$ for the optimal unconditional harness.

**Proof:**

Under stationarity, $C^*_\Phi(x) = C^*$ for all $x$ — the best task-conditional harness is the same regardless of which task is being solved. Therefore the optimal unconditional harness $\varphi^*(\mathcal{H}_t) = C^*$ achieves:

$$V(\varphi^*(\mathcal{H}_t), x_t) = V(C^*_\Phi(x_t), x_t) \quad \text{for all } x_t$$

and the navigation loss vanishes. $\square$

**Corollary.** Under stationarity, only evolution quality matters. Stronger harness construction (reducing $L_{\text{evo}}$) is the sole improvement axis. Navigation adds no value. This explains why A-Evolve's linear evolution succeeds on static benchmarks.

---

## Theorem 3: Navigation Loss Grows with Distribution Shift

**Definition (Harness divergence).** For two tasks $x, x'$, define:

$$d(x, x') = V(C^*_\Phi(x), x) + V(C^*_\Phi(x'), x') - V(C^*_\Phi(x), x') - V(C^*_\Phi(x'), x)$$

This measures how much two tasks **disagree on which harness is better**. If $d(x,x') = 0$, both tasks perform equally well under each other's optimal harness. If $d(x,x') > 0$, each task strictly prefers its own harness.

**Definition (Shift magnitude).** The distribution shift at time $t$ is:

$$\Sigma_t = \mathbb{E}_{x \sim P_t, \; x' \sim P_t}[d(x, x')]$$

**Theorem.** The navigation loss of the optimal unconditional harness satisfies:

$$L_{\text{nav}}(\varphi^*_{\text{uncond}}) \geq \frac{\Sigma_t}{4}$$

**Proof:**

Let $\varphi^*$ be the optimal unconditional harness, and let $C^* = \varphi^*(\mathcal{H}_t)$.

For any task $x$, the navigation loss for that task is:

$$V(C^*_\Phi(x), x) - V(C^*, x) \geq 0$$

Now consider two tasks $x_A, x_B$ drawn from $P_t$. The unconditional harness $C^*$ maximizes average utility:

$$C^* = \arg\max_C \; \mathbb{E}_{x \sim P_t}[V(C, x)]$$

For the two-task case ($P_t$ uniform over $\{x_A, x_B\}$), the best unconditional harness maximizes:

$$\frac{1}{2}V(C, x_A) + \frac{1}{2}V(C, x_B)$$

The navigation loss is:

$$L_{\text{nav}} = \frac{1}{2}\left[V(C^*_\Phi(x_A), x_A) - V(C^*, x_A)\right] + \frac{1}{2}\left[V(C^*_\Phi(x_B), x_B) - V(C^*, x_B)\right]$$

Since $C^*$ must compromise between what $x_A$ needs and what $x_B$ needs, and $d(x_A, x_B)$ quantifies how much they disagree:

$$L_{\text{nav}} \geq \frac{d(x_A, x_B)}{4}$$

(The factor of 4 comes from: in the worst case, $C^*$ splits capacity equally between what each task needs, each task loses half its task-specific utility, and averaging over the two tasks gives $d/4$.)

Taking expectation over pairs:

$$L_{\text{nav}} \geq \frac{1}{4}\mathbb{E}_{x,x' \sim P_t}[d(x,x')] = \frac{\Sigma_t}{4}$$

$\square$

**Corollary.** As the task distribution diversifies over time (different tasks need different harness content), $\Sigma_t$ grows, and navigation loss grows with it. This is precisely why linear evolution shows non-monotonic performance: the unconditional harness must increasingly compromise between conflicting task needs.

---

## Theorem 4: Multi-Agent Evolution Reduces Evolution Loss

**Definition (Evolver class).** An evolver $\varphi \in \Phi$ is limited by:
- The structural complexity of harness artifacts it can construct (prompt edits vs. multi-file infrastructure)
- The reasoning depth available during construction (single-pass vs. iterative multi-agent)

**Theorem.** If $\Phi_{\text{multi}} \supset \Phi_{\text{single}}$ (multi-agent evolver class strictly contains single-agent class), then:

$$L_{\text{evo}}(\Phi_{\text{multi}}, K) \leq L_{\text{evo}}(\Phi_{\text{single}}, K)$$

with strict inequality when the best harness for some task requires construction operations outside $\Phi_{\text{single}}$.

**Proof:**

$$L_{\text{evo}}(\Phi, K) = \mathbb{E}_{x_t}\left[ V(\mathcal{H}_t, x_t) - V(C^*_\Phi(x_t), x_t) \right]$$

Since $\Phi_{\text{multi}} \supset \Phi_{\text{single}}$, we have $C^*_{\Phi_\text{multi}}(x) \in \{C : \varphi \in \Phi_{\text{multi}}\} \supseteq \{C : \varphi \in \Phi_{\text{single}}\}$.

The maximum over a larger set is at least the maximum over a subset:

$$V(C^*_{\Phi_\text{multi}}(x), x) \geq V(C^*_{\Phi_\text{single}}(x), x) \quad \text{for all } x$$

Therefore:

$$V(\mathcal{H}_t, x) - V(C^*_{\Phi_\text{multi}}(x), x) \leq V(\mathcal{H}_t, x) - V(C^*_{\Phi_\text{single}}(x), x)$$

Taking expectations: $L_{\text{evo}}(\Phi_{\text{multi}}, K) \leq L_{\text{evo}}(\Phi_{\text{single}}, K)$.

Strict inequality holds when there exists a task $x$ with positive probability under $P_t$ such that the utility-maximizing harness of capacity $K$ requires multi-agent construction (e.g., research → build → verify pipeline) that $\Phi_{\text{single}}$ cannot execute.

**Concrete example:** A single-agent evolver writes "use Yahoo Finance API for prices" in a prompt. A multi-agent evolver builds a working `finance.py` module returning parsed, date-filtered data. Same harness capacity, but:

$$V(C_{\text{multi}}, x_{\text{finance}}) > V(C_{\text{single}}, x_{\text{finance}})$$

because the solver with the working module produces correct answers more reliably than the solver with a text instruction. $\square$

---

## Theorem 5: Evolution Loss and Navigation Loss are Orthogonal

**Theorem.** The two losses act on independent terms:

$$\mathbb{E}[\text{Regret}] = L_{\text{evo}}(\Phi, K) + L_{\text{nav}}(\varphi)$$

Multi-agent evolution reduces $L_{\text{evo}}$ (by expanding $\Phi$). Navigation reduces $L_{\text{nav}}$ (by conditioning harness on task). They compose:

$$\mathbb{E}[\text{Regret}_{\text{multi+nav}}] = L_{\text{evo}}(\Phi_{\text{multi}}, K) + L_{\text{nav}}(\varphi_{\text{cond}})$$

$$\leq \min\left( \mathbb{E}[\text{Regret}_{\text{multi only}}], \; \mathbb{E}[\text{Regret}_{\text{nav only}}] \right)$$

**Proof:**

From Theorem 1, regret decomposes as $L_{\text{evo}} + L_{\text{nav}}$ by telescoping. 

$L_{\text{evo}}(\Phi, K) = \mathbb{E}[V(\mathcal{H}_t, x_t) - V(C^*_\Phi(x_t), x_t)]$ depends only on what harnesses the evolver class can construct — not on whether conditioning is applied.

$L_{\text{nav}}(\varphi) = \mathbb{E}[V(C^*_\Phi(x_t), x_t) - V(\varphi(\mathcal{H}_t), x_t)]$ depends only on whether the harness is task-conditional — not on how capable the evolver is at building each individual harness.

Reducing one does not affect the other. The full system addresses both:
- Multi-agent: $\Phi_{\text{multi}}$ → lower $L_{\text{evo}}$
- Navigation: $\varphi(\mathcal{H}_t, x_t)$ → lower $L_{\text{nav}}$

$\square$

**Corollary (Regime table):**

| Regime | $L_{\text{evo}}$ | $L_{\text{nav}}$ | What reduces regret |
|---|---|---|---|
| Stationary, simple domain | Low | 0 | Neither needed |
| Stationary, complex domain | High | 0 | Stronger evolution only |
| Non-stationary, simple domain | Low | High | Navigation only |
| Non-stationary, complex domain | High | High | Both (our full system) |

---

## Corollary: Why Linear Evolution Degrades over Time

Linear evolution is unconditional + single-agent: it incurs both $L_{\text{evo}}(\Phi_{\text{single}}, K)$ and $L_{\text{nav}} > 0$.

As the stream progresses under non-stationarity:

$$\Sigma_t \text{ increases with } t \quad \Rightarrow \quad L_{\text{nav}} \geq \frac{\Sigma_t}{4} \text{ increases with } t$$

Even if the evolver learns (reducing $L_{\text{evo}}$), navigation loss grows. Total regret dynamics:

$$\frac{d}{dt}\mathbb{E}[\text{Regret}] = \underbrace{\frac{dL_{\text{evo}}}{dt}}_{\leq 0 \text{ (evolver learns)}} + \underbrace{\frac{dL_{\text{nav}}}{dt}}_{> 0 \text{ (shift accumulates)}}$$

Performance improves while learning outpaces shift, then degrades when shift dominates. This produces non-monotonic evolution scaling: early_freeze outperforms full_evo because it stops before $L_{\text{nav}}$ overwhelms $L_{\text{evo}}$ gains.

---

## Summary: Connection to Research Questions

| Theory | Maps to | Empirical question |
|---|---|---|
| $L_{\text{nav}} = 0$ under stationarity | Static benchmarks | Why A-Evolve works without navigation |
| $L_{\text{nav}} \geq \Sigma_t / 4$ | Temporal benchmarks | Why full evolution degrades under shift (RQ1) |
| $\Phi_{\text{multi}} \supset \Phi_{\text{single}}$ | Evolver class expansion | Why multi-agent builds better harnesses (RQ2) |
| $\varphi(\mathcal{H}, x)$ vs $\varphi(\mathcal{H})$ | Conditional harness | Why navigation helps under shift (RQ3) |
| Orthogonality | Composition | Why the full system outperforms either alone |
| $dL_{\text{nav}}/dt > 0$ | Accumulation | Why early-freeze outperforms full evolution |

---

## Interpretation for Target Audiences

**For time series / forecasting readers (primary + flanking B):**
- Harness = fitted model / learned representation
- Evolution = offline model training from historical data
- Navigation = online model selection / test-time adaptation per instance
- Capacity $K$ = model complexity budget
- Theorem 3 = one-size-fits-all model becomes suboptimal under regime change
- Theorem 5 = better training AND adaptive selection are independently valuable

**For self-evolving agent readers (flanking A):**
- $L_{\text{evo}}$ = evolver capability bottleneck (how expressive are the harness updates?)
- $L_{\text{nav}}$ = the navigation gap (does one harness fit all tasks?)
- Linear evolution conflates both into one undifferentiated system
- Our decomposition makes both visible and separately improvable
- Multi-agent evolution is not just "more compute" — it expands the class of constructible harnesses
