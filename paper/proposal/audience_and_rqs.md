# Audience and Research Questions

## Three Dimensions of Difficult Agentic Tasks

We study agentic evolution on tasks that are "difficult" in a ***real-world deployment sense***. Three dimensions define this setting; any one makes a task hard, and the hardest real-world deployments span all three:

**D1: Long-horizon.** The agent operates over an extended *temporal extent* — many tasks, many cycles, accumulated history — so decisions at time $t$ depend on experience from time $1, \ldots, t{-}1$. Tasks arrive sequentially; the harness accumulates.

**D2: Non-stationarity.** Along that extent, the task distribution $P_t$ *changes over time* — strategy-relevant properties (techniques required, information availability, decision structure) shift across the stream. Past experience no longer uniformly transfers forward. (Equivalently: "distribution shift over time"; we reserve "non-stationarity" for the property of the stream and "shift" for a specific transition within it.)

**D3: Open-endedness.** The *scope* of required capabilities is not pre-enumerable. The agent must integrate APIs, data sources, tools, and domain logic that were not known at design time. Closed benchmarks (e.g., MATH, ARC) specify the capability vocabulary in advance; open-ended tasks do not.

These dimensions are orthogonal:

- Long-horizon alone (D1 only) — stationary deployment over time, e.g., standard SWE-bench-style evaluation repeated. Past experience transfers.
- Non-stationarity without horizon (D2 only) — one-shot prediction under covariate shift. No chance to evolve.
- Open-ended without horizon or non-stationarity — single hard task with an unknown capability budget. Tool discovery matters but accumulation does not.

Our three benchmarks are chosen to exercise all three simultaneously:

| Benchmark | D1 (Horizon) | D2 (Non-stationarity) | D3 (Open-endedness) |
|---|:---:|:---:|:---:|
| **PolyBench** (5,075 markets / 16 days) | ✓ | Regime shift (certainty ↓, liquidity ↓) | Market-domain tooling (price feeds, resolution rules) |
| **CTF-Dojo** (261 challenges / 13 yrs) | ✓ | Format & runtime shift (text → scripts; glibc → Python) | Exploit toolchain (binary analysis, crypto libs, web fuzzers) |
| **FutureX** (332 tasks / 82 days) | ✓ | Language & source shift (EN → ZH; Wikipedia → platform APIs) | Search infrastructure (multi-source data pipelines) |

---

## Challenges

Three structural challenges arise when agentic evolution operates across these dimensions. Each anchors to a distinct dimension. C1 and C2 each map 1:1 to one contribution (navigation and multi-agent evolution respectively); C3 is the failure mode that requires both contributions *jointly*.

### C1: Non-stationarity introduces non-monotonic evolution

**Driven by:** D2 (non-stationarity), over the substrate of D1 (long-horizon).

Agentic evolution assumes past experience transfers to future tasks. Under non-stationarity — strategy-relevant properties changing over time (techniques required, information availability, decision structure) — this assumption breaks. Accumulated experience is not uniformly useful: part transfers (stationary knowledge) and part is regime-specific (non-stationary knowledge). A single unconditional harness must compromise between conflicting task needs, and on every temporal benchmark we tested, *stopping evolution early outperforms continuing*:

| Benchmark | Full Evo | Early Freeze |
|---|---|---|
| **PolyBench** | 80.4% | **81.9%** |
| **CTF-Dojo** | 47.9% | **54.8%** |
| **FutureX** | 45.2% | **46.7%** |

The decomposition inside accumulated experience:

- Stationary (helps all tasks): flag verification, illiquidity detection, temporal disambiguation, data API patterns
- Non-stationary (helps only originating regime): classical crypto skills, memorized results, regime-specific rules

The system must determine **which knowledge to load** per task, not load everything globally. This is the core motivation for conditional harness construction (navigation).

*Theory link:* the unconditional harness incurs navigation loss $L_{\text{nav}} \geq \Sigma_t/4$ that grows with shift magnitude. Reducing it requires conditioning the harness on the current task: $\varphi(\mathcal{H}_t, x_t)$ rather than $\varphi(\mathcal{H}_t)$.

### C2: Evolver capability bottleneck

**Driven by:** D3 (open-endedness) primarily; severe D2 introduces a second sub-mode.

C1 shows that evolution quality degrades under non-stationarity. C2 identifies a separate obstacle: the evolver itself is too weak to construct the harnesses that would actually help. A weak evolver fails in two distinct ways — each demanding a different capability expansion, both sharing one theoretical bottleneck.

```
Evolver capability ──────────────────────────────────────────▶

Weak Evolver          Strong Evolver          Stronger + HITL
    │                      │                        │
    │  prompt tweaks       │  + individual tools    │  + infra pipelines
    │  memory edits        │  + API wrappers        │  + wrapped strategies
    │                      │                        │  + business logic
    ▼                      ▼                        ▼
 ───┤──────────────────────┤────────────────────────┤──────
  artifacts              tools                  infrastructure
  (easy, limited)        (explicit, verbose)    (implicit, effective)
```

**C2(a) Construction gap** — *driven by D3.*
The required capability vocabulary is not pre-enumerable: each new task may demand APIs, data sources, or domain logic never seen before. A prompt-level evolver can tweak existing skills but cannot construct multi-file infrastructure (research → API integration → tool → pipeline). The optimal harness for the task lies outside what $\Phi_{\text{single}}$ can produce.

**C2(b) Direction gap** — *driven by D2 in the severe regime.*
Experience-driven evolution assumes $\mathcal{H}_t$ contains useful signal for $x_t$. Under severe shift to a novel regime, it does not — the evolver has no relevant history to learn from. No amount of construction within $\Phi$ fixes this; the *input* to the evolver is inadequate. Credentials, domain priors, and strategic direction must come from outside — human-in-the-loop during evolution.

Each sub-mode maps to a distinct capability expansion: construction (a) demands multi-agent orchestration with research/build/verify roles; direction (b) demands HITL integration points. Both share one theoretical bottleneck: the evolver class $\Phi$ is the limit.

*Theory link:* the evolver class $\Phi$ determines $L_{\text{evo}}(\Phi, K)$. Expanding $\Phi$ — through multi-agent construction and HITL steering — reduces it. $\Phi_{\text{multi}} \supset \Phi_{\text{single}}$ gives $L_{\text{evo}}(\Phi_{\text{multi}}, K) \leq L_{\text{evo}}(\Phi_{\text{single}}, K)$.

### C3: Long-horizon accumulation exceeds harness capacity

**Driven by:** D1 (long-horizon), independently of D2 and D3.

Harness capacity is bounded: $|C| \leq K$ (context windows, prompt budgets, solver input limits). History grows: $|\mathcal{H}_t|$ scales with $t$. Even under stationary distribution and closed vocabulary, the evolver cannot append indefinitely — eventually $K$ binds. The system must do two things at once:

- **Distill** — extract stationary signal from accumulating experience, so only what generalizes enters the harness.
- **Condition** — partition the distilled content so no single solver invocation pays for content irrelevant to its task.

Without distillation, the harness accumulates raw experience and thrashes $K$. Without conditioning, even a distilled harness must compromise between every task's needs within $K$.

Preliminary evidence: in our single-agent runs (H1), the solver's harness grows explosively across a short horizon (~batch-20). Totals below are bytes of prompt + skills + tools + memory at the end of evolution, compared against the seed.

| Benchmark | Seed | End of H1 | Growth | End-state composition |
|---|---:|---:|:---:|---|
| **PolyBench** | 3.4 KB | 60.6 KB | **~18×** | prompt 15 KB · 10 skills (26 KB) · 3 tools (14 KB) · memory 5 KB |
| **FutureX** | 8.0 KB | 175.8 KB | **~22×** | prompt 23 KB · 13 skills (30 KB) · 20 tools (116 KB) · memory 6 KB |
| **CTF-Dojo** | 1.2 KB | 75.5 KB | **~60×** | prompt 9 KB · 19 skills (41 KB) · 6 tools (14 KB) · memory 12 KB |

The evolver keeps appending — new skills, new tools, ever-longer prompts — and never consolidates. Growth is monotone, not bounded; capacity $K$ binds long before the stream ends. The `cap_prompt_size` guardrail in the structured-evolution template exists precisely because uncapped growth triggered failures during development.

*Theory link:* C3 lives in $L_{\text{evo}}$ with a horizon-dependent $\Phi$. Persistent-state multi-agent evolvers form a class $\Phi_{\text{persistent}} \supset \Phi_{\text{single}}$ because the former can condition on prior-cycle state; Theorem 4 applies. Navigation contributes orthogonally: it reshapes the $K$-bound from per-system to per-branch, so the effective capacity for distilled content scales with the number of branches.


---

## Primary Audience: Self-evolving agent researchers (Lean toward AI method)

> **Already familiar with:** agentic evolution systems — concepts, designs, engineering details. They build evolvers but mostly evaluate on static / i.i.d. benchmarks (SWE-bench, Terminal-Bench, ARC-AGI), where D2 and D3 are absent and D1 is bounded.

> ***Attraction:*** **(1)** a task setting that simultaneously exercises all three difficulty dimensions (D1 long-horizon, D2 non-stationarity, D3 open-endedness), revealing failure modes invisible in i.i.d. settings; **(2)** three named challenges (C1 non-monotonic scaling, C2 evolver capability bottleneck, C3 long-horizon accumulation) with concrete empirical signatures (early-freeze > full-evo; 18–60× harness growth; construction/steering gaps); **(3)** a theoretical decomposition ($L_{\text{evo}} + L_{\text{nav}}$) that separates evolver capability from per-task conditioning — both independently improvable and composable; **(4)** two general architectural upgrades (multi-agent evolution, navigation) that transfer to their own systems.

**What they may ask/care:**
- **On the setting (C1/C2/C3):**
    - Why does accumulated experience *hurt* under non-stationarity (C1)? When does early-freeze beat full-evo, and why isn't this visible in i.i.d. benchmarks?
    - What can a prompt-level evolver *not* construct (C2)? How far does the capability tier — artifacts → tools → infrastructure — shape what harnesses are reachable?
    - Why does the harness explode in size over a long horizon (C3), and what structurally prevents an evolver from consolidating rather than appending?
- **On mechanism:**
    - Linear, unconditional evolution: what's its empirical ceiling ($L_{\text{nav}}$ bound)? What's its theoretical ceiling?
    - Single-agent evolution: which artifacts are out-of-class for $\Phi_{\text{single}}$? When does multi-agent unlock a qualitatively different harness (not just "more of the same")?
    - Human-in-the-loop during evolution: under what conditions does historical experience become insufficient, and what does HITL provide that experience cannot?

Audience examples:

- **A-Evolve follow-ups** — linear chain evolvers hitting diminishing returns; C1 and C3 directly explain the plateau
- **DGM / archive-based evolution** — flat archives accumulating across cycles without consolidation; C3's 18–60× growth data speaks to them
- **ADAS / AFlow / meta-agent designers** — outcome-only evaluation that misses process-level degradation; our regret decomposition ($L_{\text{evo}}, L_{\text{nav}}$) gives them diagnostic handles
- **SkillRL / GEPA / DSPy optimizers** — programmatic optimizers assuming stationary skill utility; C1 shows why this assumption costs them under shift
- **Self-evolving agent PhD students** — designing next-generation methods; the three-dimensional difficulty frame + three challenges + two contributions is the scaffolding for their own papers

#### **Why consider them?**

They are the most likely to cite and build on this work. They already have evolution methods but mostly evaluate in i.i.d. / static settings, where D2 and D3 are absent and D1 is short. Our three-dimensional frame exposes failure modes invisible in those settings, and our two contributions (multi-agent, navigation) are general enough to transfer to their own evolvers.

#### **What can they get from our paper?**

- A **three-dimensional characterization** (D1 long-horizon, D2 non-stationarity, D3 open-endedness) of what makes real-world deployment hard — a lens they can use to stress-test their own methods.
- **Three named challenges** with empirical signatures: non-monotonic scaling (C1), evolver capability bottleneck (C2), long-horizon accumulation (C3). Each has a concrete measurement, not just a narrative.
- **Regret decomposition** ($L_{\text{evo}}(\Phi, K) + L_{\text{nav}}(\varphi)$) that separates evolver-class limits from per-task conditioning — reusable for any evolver, independent of our specific instantiation.
- **Two general architectural upgrades** — multi-agent evolution (expanding $\Phi$) and navigation (conditioning the harness) — with ablations showing which challenge each addresses alone and where their joint effect is load-bearing (C3).

#### **Their likely take-home message:**

Self-evolution methods should be evaluated along three dimensions (long-horizon, non-stationarity, open-endedness), not just i.i.d. accuracy. Linear unconditional single-agent evolution structurally degrades across all three: C1 because one harness can't serve conflicting regimes, C2 because prompt-level edits can't construct needed infrastructure, C3 because unbounded history exceeds bounded capacity. Two independent and composable fixes — stronger evolution (multi-agent, expanding $\Phi$) and task conditioning (navigation) — each address one failure mode alone and both are required jointly to handle long-horizon accumulation.

### Subgroup: Production LLM-agent deployers on temporal tasks (Lean toward application)

> **Already familiar with:** deploying LLM agents into production on temporal tasks — they live the three dimensions daily. D1 (long-horizon) because the agent runs for weeks or months; D2 (non-stationarity) because the environment shifts under them (markets, codebases, infra, attack surfaces); D3 (open-endedness) because the agent must integrate APIs and domain logic that didn't exist at design time.

> ***Attraction: they have already hit C1 (agents degrade as they accumulate experience), C2 (their evolvers can't keep up with new tooling requirements), and C3 (context/skill/memory files explode and become unmaintainable). They lack both a theoretical explanation and a principled architecture for all three.***

**What they may ask/care:**
- **C1-shaped concerns:** Why does my agent perform *worse* after months of accumulated experience? How do I prevent regime-specific knowledge from poisoning other regimes' performance?
- **C2-shaped concerns:** How do I get my evolver to build real infrastructure (APIs, pipelines) instead of just tweaking prompts? When is HITL worth integrating, and where?
- **C3-shaped concerns:** My agent's prompt / skills / memory files have grown 50× since deployment and nobody consolidates them — what architecture keeps the harness bounded without losing signal?

Subgroup examples (mapped to the dimensions they span):

- **Autonomous trading/forecasting agents** — D1+D2 heavy (regime shifts across bull/bear cycles); D3 moderate (new data sources, asset classes). Our C1 story maps directly.
- **Continuous coding assistants** — D1+D2 (codebases/frameworks drift) + D3 (new libraries, internal APIs). Our C2 construction story maps directly.
- **Monitoring/SRE agents** — D1+D2+D3 (topology changes, new failure modes, new alert systems). Our C3 accumulation story is what prunes stale detection rules.
- **Research assistants over multi-month projects** — D1+D2+D3 (literature drift, new methods, problem understanding evolves). C3 is the most acute — they've experienced harness bloat firsthand.
- **Cybersecurity/CTF agents** — analogous to our CTF-Dojo benchmark; attack techniques drift across years (D2) and require new toolchains per era (D3).
- **Prediction market agents** — analogous to our PolyBench benchmark; market liquidity/certainty/resolution rules shift within weeks (D2) while requiring domain-specific tooling (D3).

#### **Why consider them?**

Within this audience, deployers are the most direct users of our work. They've already experienced all three challenges — C1 (agents degrade), C2 (prompt tweaks aren't enough), C3 (harness bloat) — but frame them as engineering pain rather than structural failure modes. Our paper gives them a vocabulary and an architecture; they will immediately try both on their deployed systems.

#### **What can they get from our paper?**

- A **three-dimensional diagnostic** (D1/D2/D3) for locating where their own deployment is hardest — a lens to decide whether navigation, multi-agent evolution, or both apply.
- A **theoretical frame** ($L_{\text{evo}} + L_{\text{nav}}$) that explains why agents degrade (non-monotonic scaling under $\Sigma_t$), why prompt-only evolution plateaus, and why harness consolidation matters for long-horizon deployment.
- An **architecture** (multi-agent evolution + navigation) with empirical evidence across three temporal benchmarks, and specific signals (early-freeze > full-evo, 18–60× harness growth) that let them recognize the same failure modes in their own systems.

#### **Their likely take-home message:**

Long-horizon deployment is hard along three dimensions, and each drives a distinct failure mode. Non-stationarity (D2) causes non-monotonic scaling (C1) — fix with per-task conditioning (navigation). Open-endedness (D3) causes the capability bottleneck (C2) — fix with stronger, multi-agent evolution. Long horizon (D1) causes harness accumulation (C3) — this needs *both* fixes jointly: multi-agent to distill, navigation to partition. The two architectural upgrades are independent where they matter (C1, C2) and composable where they must be (C3).

---

## Task Formulation
<!-- ### v1: agent-community formulation

A temporally ordered stream of tasks with non-stationary distribution:

```
D = (x₁, x₂, ..., x_T),    t(x₁) ≤ t(x₂) ≤ ... ≤ t(x_T),    xₜ ~ Pₜ
```

- Each task xₜ has a real-world timestamp t(xₜ) fixing its position in the stream
- The generating distribution Pₜ shifts over time (non-stationary)
- The agent may only access information available before t(xₜ) when solving xₜ

The agent solves tasks sequentially with an evolving harness:

```
Solve:     (aₜ, τₜ) = Solve(Agent(s, Hᵗ⁻¹), xₜ)
Score:     rₜ = Score(aₜ, xₜ)
Evolve:    Hᵗ = U_e(Hᵗ⁻¹, τₜ, rₜ)
```

where:
- s: solver (frozen LLM)
- Hᵗ: agent harness at step t (prompts, tools, memory, skills, infrastructure)
- U_e: evolver that updates the harness from trajectory and feedback
- τₜ: solving trajectory
- rₜ: task outcome (scored before evolver sees it)

Metric (online, no look-ahead):

```
S = (1/T) Σₜ rₜ
``` -->

<!-- ### v2: alternative formulation (history-conditioned harness) -->

An equivalent formulation emphasizing bounded harness construction from task history.

```
Task stream:     D = (x₁, x₂, ..., x_T),    xₜ ~ Pₜ,    ordered by time
History:         Hₜ = {(x₁, r₁, τ₁), ..., (xₜ₋₁, rₜ₋₁, τₜ₋₁)}
Harness:         Cₜ = φ(Hₜ),    |Cₜ| ≤ K
Predict:         aₜ ~ π(a | xₜ, Cₜ)
```

The harness $C$ is a bounded representation constructed from history by the evolver $\varphi$. The agent can only act through the harness — not raw history.

---