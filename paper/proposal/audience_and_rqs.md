# Audience and Research Questions

## Challenges: What Temporal Distribution Shift Introduces

Three challenges emerge when agentic evolution operates on temporally ordered, non-stationary task streams — absent from static/i.i.d. benchmarks:

### C1: Non-monotonic evolution scaling

Agentic evolution assumes past experience transfers to future tasks. On temporal benchmarks, this assumption breaks: strategy-relevant properties shift over time (not topic labels, but techniques required, information availability, decision structure). Heavily evolved harnesses may not help and can actively hurt.

| Benchmark | Full Evo | Early Freeze |
|---|---|---|
| **PolyBench** | 80.4% | **81.9%** |
| **CTF-Dojo** | 47.9% | **54.8%** |
| **FutureX** | 45.2% | **46.7%** |

*Theory link: the unconditional harness incurs navigation loss $L_{\text{nav}}$ that grows with shift magnitude $\Sigma_t$.*

### C2: Long-horizon Poses Non-stationarity

Distribution shift is not all-or-nothing — part of accumulated experience transfers and part does not. Evidence: fully evolved agent still beats baseline (stationary knowledge helps). But a single-path evolver cannot decompose this: one harness loads ALL experience for EVERY task.

- Stationary (helps all tasks): flag verification, illiquidity detection, temporal disambiguation, data API patterns
- Non-stationary (helps only originating regime): classical crypto skills, memorized results, regime-specific rules

The system must determine **which knowledge to load** per task, not load everything globally.

*Theory link: the distinction between unconditional harness $\varphi(\mathcal{H}_t)$ and conditional harness $\varphi(\mathcal{H}_t, x_t)$.*

### C3: Evolver capability bottleneck

C1 and C2 show that evolution quality degrades under shift. C3 identifies an obstacle to fixing this: the evolver is too weak to construct the harnesses that would actually help.

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

Temporal domains often start with near-zero infrastructure. The evolver must build everything from scratch (diagnose → find APIs → write tools → debug → integrate). This demands multi-step reasoning far beyond prompt tweaks — requiring stronger evolution systems (multi-agent, structured planning) and human-in-the-loop under severe shift.

*Theory link: the evolver class $\Phi$ determines $L_{\text{evo}}$; expanding $\Phi$ (multi-agent, HITL) reduces it.*

---

## Primary Audience

> **Already familiar with:** deploying LLM agents into production environments with temporal tasks. Their tasks are (1) long horizon, and (2) shifting across multiple dimensions over time.

> ***Attraction: they have needs from real-world application challenges (long-horizon deployment; robust to environment and task shifts), which aligns with ours***

**What they may ask/care:**
- Why does current agent/evolution fail under task with distribution shifts?
- How do I prevent my agent from degrading as the environment shifts?
- How to build a robust system that can support long-horizon deployment.
- What architecture supports long-horizon improvement without catastrophic overfitting / context exploding?



Audience examples:

- **Autonomous trading/forecasting agents** — market regimes shift (bull→bear, low→high volatility), data sources appear/disappear, APIs change; agent must adapt strategies without losing general risk management
- **Continuous coding assistants** — codebases evolve, frameworks update, team conventions shift; agent must accumulate project knowledge without overfitting to stale patterns
- **Monitoring/SRE agents** — infrastructure topology changes, new failure modes emerge, old alerts become irrelevant; agent must build detection capability while pruning obsolete knowledge
- **Research assistants over multi-month projects** — literature landscape shifts, new methods appear, problem understanding evolves; agent must deepen without anchoring to early misconceptions
- **Cybersecurity/CTF agents** — attack techniques evolve across years, toolchains change, defense surfaces shift; skills from 2015 may actively mislead on 2024 challenges
- **Prediction market agents** — information availability, market liquidity, and resolution criteria shift across time windows; strategies that work in high-certainty periods fail under ambiguity

#### **Why consider them?**

They are the most direct users of our work. They've already experienced the pain (agents degrade over time) but lack both a theoretical explanation and a principled architecture. They will immediately try to apply our findings to their own deployed systems.

#### **What can they get from our paper?**

- A theoretical framework explaining why their agents degrade (non-monotonic scaling under shift, $L_{\text{nav}}$ grows with $\Sigma_t$)
- An architecture (multi-agent evolution + navigation) that addresses both the capability and the shift problem simultaneously
- Empirical evidence across three temporal benchmarks showing the approach works

#### **Their likely take-home message:**

Long-horizon agent deployment requires separating domain-level context (evolved unconditionally) from problem-specific context (loaded conditionally per task). Both stronger evolution and adaptive navigation are needed — and they address independent failure modes.

---

## Flanking Audience A: Self-evolving agent researchers

> **Already familiar with:** agentic evolution systems, including concepts, designs and various engeering details. 

> ***Attraction: (1) a new deployment domain (temporal event prediction) that stress-tests their methods; (2) new challenges absent/unoticed from static benchmarks (long-horizon, distribution shift, non-monotonic scaling); (3) empirical findings that reveal structural limitations in current evolution designs, transfering knowledge to their area.***

**What they may ask/care:**
- Our domain/setting:
    - Why does current agent/evolution fail under task with distribution shifts?
    - same as the primary audience...

- Their domain/setting:
    - What's the limitation of linear evolution both empirically and theorectically?
        - e.g., Why does my method plateau or regress after many evolution cycles on deployed tasks?
    - What's the limitation of single agent evolution
        - e.g., How to prevent overwhelming context during evolution
    - What's the role of human in the agentic evolution
        - e.g., can we have human-in-the-loop during evolution to enable steering?

Audience examples:

- **A-Evolve follow-ups** — linear chain evolvers hitting diminishing returns, looking for structured search alternatives
- **DGM / archive-based evolution** — flat archives accumulating regressions, needing non-degradation guarantees
- **ADAS / AFlow / meta-agent designers** — fixed evaluation (outcome-only) limiting their search efficiency, seeking process-level diagnostics
- **SkillRL / GEPA / DSPy optimizers** — programmatic optimizers that assume stationary skill utility, unaware of temporal decay
- **Self-evolving agent PhD students** — designing next-generation methods, need to understand where single-agent evolvers structurally fail

#### **Why consider them?**

They are the most likely to cite and build on this work. They already have evolution methods but only evaluate on static benchmarks. Our temporal setting exposes failure modes invisible in i.i.d. settings, and our solutions (multi-agent, navigation) are general enough to transfer to their domains.

#### **What can they get from our paper?**

- A new evaluation setting (temporal, non-stationary) that stress-tests existing methods and reveals when "more evolution = better" breaks
- A formal decomposition of evolution loss ($L_{\text{evo}}$) and navigation loss ($L_{\text{nav}}$) that clarifies where to invest in their own systems
- Two concrete architectural upgrades (stronger evolution via multi-agent, navigation via branching/selection) with empirical evidence on when each matters

#### **Their likely take-home message:**

Self-evolution methods should be evaluated under distribution shift, not just i.i.d. settings. Under shift, linear unconditional evolution structurally degrades — the fix requires both expanding evolver capability and conditioning the harness on the current task.

---

## Flanking Audience B: Temporal event / time-series researchers adopting agents

> **Already familiar with:** distribution shift, non-stationarity, and regime change as first-class problems — they are native to temporal event analysis and understand the data challenge deeply but are new to agentic system design.

> ***Attraction: (1) a principled agent architecture designed for their non-stationary setting; (2) empirical characterization of what shifts matter and how they degrade agent performance; (3) adoptable mechanisms (navigation, multi-agent evolution) that don't require deep evolution expertise to apply***


**What they may ask/care:**
- Why does my agent perform well on historical backtests but degrade on live temporal streams?
- What types of distribution shift actually matter for agent performance (not just data distribution)?
- Can I get an agent architecture that handles regime change without manual intervention?
- How do I characterize and measure the shift that's hurting my system?

Audience examples:

- **Prediction market researchers** — building agents for Polymarket/Manifold, seeing performance decay as market regimes shift from high-certainty to ambiguous
- **Financial forecasting teams** — deploying LLM agents for macro/equity prediction, observing that strategies learned in one regime hurt in the next
- **Event prediction / IARPA-style programs** — geopolitical, scientific, or social event forecasting where information landscapes shift drastically
- **News/information retrieval agents** — systems that must adapt to changing source availability, language distributions, and platform access over months
- **Climate/environmental monitoring** — agents processing evolving sensor networks, shifting data formats, and non-stationary physical processes

#### **Why consider them?**
They own the non-stationarity problem natively and are beginning to adopt LLM agents — but they lack a framework for why agent performance degrades over temporal streams. Our paper bridges their domain expertise (distribution shift, regime change) with agentic system design.

#### **What can they get from our paper?**
- A characterization of what types of shift degrade agent performance (information access, platform availability, decision structure — not just data distribution)
- An adoptable architecture that handles regime change without deep evolution expertise — build branches during evolution, route per-task during solving
- Empirical evidence from domains they recognize (prediction markets, event forecasting, temporal data) showing the approach works under real-world shift patterns

#### **Their likely take-home message:**
When deploying agents on non-stationary temporal tasks, naive accumulation of experience (evolution without navigation) will degrade. The key architectural requirement is separating what's always useful (domain context) from what's regime-specific (problem context) — and loading the latter conditionally.

---

## Task Formulation
### v1: more close to agent community

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
```

### v2: more close to time series community

```
Task stream:     D = (x₁, x₂, ..., x_T),    xₜ ~ Pₜ,    ordered by time
History:         Hₜ = {(x₁, r₁, τ₁), ..., (xₜ₋₁, rₜ₋₁, τₜ₋₁)}
Harness:         Cₜ = φ(Hₜ),    |Cₜ| ≤ K
Predict:         aₜ ~ π(a | xₜ, Cₜ)
```

The harness $C$ is a bounded representation constructed from history by the evolver $\varphi$. The agent can only act through the harness — not raw history.

---

## Research Questions

### RQ1: Why does agentic evolution degrade under temporal distribution shift? (prior experiments for empirical findings)

Under what conditions does accumulated experience hurt rather than help? What structural property of temporal tasks causes the non-monotonic scaling observed empirically?

**Addresses:**
- Primary: "Why does current agent/evolution fail under tasks with distribution shifts?"
- Audience A: "What's the limitation of linear evolution both empirically and theoretically?"
- Audience B: "Why does my agent perform well on historical backtests but degrade on live temporal streams?"

**Expected finding:** When the task distribution shifts, a single unconditional harness must compromise between conflicting task needs. The navigation loss $L_{\text{nav}}$ grows proportionally to the shift magnitude $\Sigma_t$, eventually overwhelming evolution gains — producing non-monotonic scaling (early_freeze > full_evo).

---

### RQ2: How to build an agentic evolution system robust to non-stationarity?

Given the degradation identified in RQ1, what system design enables sustained improvement under distribution shift? How do the components (multi-agent evolution, navigation/branching) contribute individually and jointly?

**Addresses:**
- Primary: "How to build a robust system that can support long-horizon deployment?"
- Audience A: "What's the limitation of single-agent/linear evolution?" / "What architecture handles shift?"
- Audience B: "Can I get an agent architecture that handles regime change without manual intervention?"

**Evidence:** Main results table (full system vs baselines across benchmarks) + ablations (multi-agent only, navigation only, single-agent + navigation) + robustness analysis (performance under increasing non-stationarity magnitude).

---

### RQ3: Does stronger evolution produce qualitatively better harnesses? (reducing $L_{\text{evo}}$)

How does evolver capability (weaker single-agent → stronger single-agent → multi-agent) translate to harness quality and solver performance? What can stronger evolvers construct that weaker ones cannot?

**Addresses:**
- Primary: "What architecture supports long-horizon improvement without context exploding?"
- Audience A: "What's the limitation of single-agent evolution?" / "How to scale beyond prompt tweaks to infrastructure?"
- Audience B: "Can I get infrastructure-level adaptation without manual engineering?"

**Evidence:** Evolver scaling analysis (weak→strong single-agent, single→multi-agent), artifact comparison (what each tier constructs: prompt edits vs tools vs multi-file pipelines), solver behavior differences when using each harness type.

---

### RQ4: Does navigation reduce degradation under distribution shift? (reducing $L_{\text{nav}}$)

Does building diverse branches during evolution and routing per-task during solving prevent accumulated experience from hurting on shifted tasks?

**Addresses:**
- Primary: "How do I prevent my agent from degrading as the environment shifts?"
- Audience A: "Why does my method plateau after many evolution cycles?"
- Audience B: "How do I handle regime change without manual intervention?"

**Evidence:** Navigation routing analysis (which tasks go where, routing accuracy), performance comparison: navigation vs full-load vs early-freeze, per-regime breakdown showing navigation selectively avoids loading harmful context.

---

### RQ5: What is the role of human guidance in evolution under severe distribution shift?

When historical experience becomes insufficient or misleading under severe shift, can human-in-the-loop during evolution provide what experience cannot — domain judgment, credentials, proactive direction?

**Addresses:**
- Primary: "How to build a robust system that can support long-horizon deployment?"
- Audience A: "What's the role of human in agentic evolution?" / "Can we have human-in-the-loop to enable steering?"
- Audience B: "Can I get an architecture that handles regime change without full manual intervention but with minimal human input?"

**Expected finding:** Under severe shift where the evolver has no relevant historical signal, human provision during evolution (credentials, domain hints, strategic direction) enables harness improvements that purely experience-driven evolution cannot discover — bridging the gap between what history provides and what the new regime demands.

---
