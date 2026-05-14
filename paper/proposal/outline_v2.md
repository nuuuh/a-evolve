# Paper Outline — Multi-Agent Evolution + Navigation + HITL

## Thesis (one sentence)

Self-evolving agents on real-world deployments fail along three orthogonal **task-intrinsic** challenges — non-monotonic evolution under shift (C1), construction bottleneck under open-endedness (C2), and experience insufficiency under novel regimes (C3) — that a regret decomposition ($L_{\text{evo}} + L_{\text{nav}}$, augmented by an experience-availability axis) explains, and that three composable architectural contributions (agentic navigation, multi-agent evolution, HITL integration) address.

---

## 1. Introduction

One-paragraph role for each subsection.

### 1.1 Opening — agentic evolution and why "more evolution ≠ better"
One paragraph: standard A-Evolve pitch; headline puzzle — early-freeze beats full-evo on all three of our temporal benchmarks; this doesn't happen on i.i.d. benchmarks.

### 1.2 Three dimensions of real-world difficulty
One paragraph: introduce D1 (long-horizon), D2 (non-stationarity), D3 (open-endedness); state they are orthogonal; D1 amplifies D2 and D3 over time. Our three benchmarks exercise all three.

> **Figure 1** (placeholder)

### 1.3 Three task-intrinsic challenges — preliminary evidence
One paragraph introducing the three challenges. Each is a property of the task stream itself, not a method pathology — a human-designed agent would face each one. Each gets one sentence + the pre-experimental signature.

- **C1 (D2 moderate) — Non-monotonic evolution.** Accumulated experience contains both stationary signal (transfers across regimes) and regime-specific signal (helpful only in the originating regime). One unconditional harness must compromise. *Signature*: early-freeze beats full-evo.
- **C2 (D3) — Construction bottleneck.** Required capability vocabulary is not pre-enumerable; evolver must construct multi-file infrastructure (research → API integration → tool → pipeline), not just edit prompts. *Signature*: artifact-type distribution stays at prompt level under weak evolvers; performance plateaus on tasks needing infrastructure.
- **C3 (D2 severe) — Experience insufficiency.** Under shift to a regime with no prior signal in $\mathcal{H}_t$ (novel language, missing credentials, unfamiliar source), no evolver can extract direction from absent data. External input is required. *Signature*: repeated evolver failures localized on novel-regime task slices; failure rate does not improve with more cycles or stronger evolvers.

> **Figure 2** (placeholder): show the evidence — early-freeze table, artifact-type histogram, novel-regime failure rate.

### 1.4 Three contributions — what each addresses
One paragraph: agentic navigation conditions the harness on the task (addresses C1); multi-agent evolution adds architectural patterns that enable infrastructure construction (addresses C2); HITL integration provides external direction at evolver phase boundaries when history is insufficient (addresses C3). The three are composable and independent in what they fix. Forward-reference §2.

### 1.5 Contributions

1. **Three task-intrinsic empirical challenges** on PolyBench, CTF-Dojo, FutureX, each tied to one dimension and absent from i.i.d. benchmarks: C1 non-monotonic scaling (early-freeze > full-evo), C2 construction bottleneck (no infrastructure from prompt-level evolvers), C3 experience insufficiency (severe-shift slice failure).
2. **Conceptual framework** for self-evolving agents: regret decomposes into $L_{\text{evo}}(\Phi, K) + L_{\text{nav}}(\varphi)$ — diagnostic vocabulary that separates evolver-class limits from per-task conditioning. Asymmetric by design: $L_{\text{nav}}$ side admits empirical predictions tested in RQ3; $L_{\text{evo}}$ side organizes architectural patterns tested in RQ2. A third axis (experience availability) sits outside the decomposition and motivates HITL.
3. **Agentic navigation** (addresses C1): git-backed strategy tree with per-task routing over branch workspaces. Theory-motivated (navigation gain predicted by Propositions 3–4 to grow with shift and over time); architecture is a specific pattern set (branch-keyed workspaces, README/system-prompt-based routing, inline and orchestrated modes).
4. **Multi-agent evolution** (addresses C2): a set of architectural patterns that prior multi-step evolvers verifiably lack — persistent cross-cycle state (`task_board.md`, `research_log.jsonl`, `architecture.md`), parallel independent research agents, role-distinct builder/verifier with separate objectives. Justified by ablation (RQ2) rather than by class-expansion theorem.
5. **HITL integration** (addresses C3): phase-specific human-in-the-loop hooks at credential-request and task-board stages of the evolver. Triggered by experience-insufficiency signals (failed authentications, novel-vocabulary slices, repeated regime-specific failures). Provides external direction when $\mathcal{H}_t$ structurally cannot.

---

## 2. Method

Structured as framework first, then three architectural contributions.

### 2.1 Problem setting
One paragraph: bounded-harness history-conditioned formulation. Define task stream, harness $C_t = \varphi(\mathcal{H}_t)$, capacity $K$.

### 2.2 Conceptual framework

#### 2.2.1 Harness and regret
One paragraph: define $V(C, x)$, regret of harness.

#### 2.2.2 Regret decomposition (Proposition 1)
One paragraph: state $\mathbb{E}[\text{Regret}] = L_{\text{evo}}(\Phi, K) + L_{\text{nav}}(\varphi)$ as a definitional partition; interpret as separating evolver class limits from per-task conditioning. Frame this explicitly as *vocabulary*, not as a non-trivial theorem.

#### 2.2.3 When each loss matters (Propositions 2, 3, 4)
One paragraph: $L_{\text{nav}} = 0$ under stationarity (Prop 2 — explains why linear evolution succeeds on static benchmarks); $L_{\text{nav}}$ grows with shift magnitude $\Sigma_t$ (Prop 3 — qualitative prediction tested in RQ3 static); $dL_{\text{nav}}/dt > 0$ under accumulation (Prop 4 — predicts non-monotonic learning curves, explains early-freeze > full-evo, tested in RQ3 dynamic).

#### 2.2.4 Methodological asymmetry — predictive vs diagnostic
One paragraph (drawn from theory_v2.md §2.2.5): $L_{\text{nav}}$ side is empirically predictive because shift magnitude is measurable; $L_{\text{evo}}$ side is diagnostic vocabulary because evolver class has no natural scalar parameterization. This asymmetry is faithful to the underlying problem structure, not a weakness. **A third axis — experience availability — sits outside both losses and motivates HITL** as a separate intervention type, applied at the evolver's input rather than acting on either loss term.

### 2.3 Contribution 1 — Agentic Navigation (conditioning the harness)

One paragraph: motivated by Propositions 3–4 — per-task conditioning is the principled response to $L_{\text{nav}}$. Architecture: git-backed strategy tree; F_Navigate reads each branch's workspace (README, system prompt, skills, tools) via `git show`; routes task to best-fit branch; inline (single sandboxed evolver LLM call with agentic branching) and orchestrated (plan-driven) modes.

**Positioning vs RAG / MoE.** A short paragraph explicitly distinguishing: (i) retrieval units are git branches (executable workspaces) not document chunks; (ii) branches have evolutionary lineage (fork / merge) not static collection; (iii) router operates on README / system-prompt content not embedding similarity; (iv) total capacity is partitioned across branches, not retrieved as top-k.

> **Figure 3** (placeholder) — Strategy tree + per-task routing diagram.

> **Figure 4** (placeholder) — Example evolved strategy tree (from CTF-Dojo):
>
> ```
>    main  (stationary content, inherited by every task)
>      • flag verification routines
>      • sandbox inspection recipes
>      • generic recon / enumeration tools
>      │
>      ├── branch/crypto-classical       (era: 2011–2014)
>      ├── branch/binary-reversing       (era: 2017–2018)
>      └── branch/web-modern             (era: 2022–2024)
> ```

### 2.4 Contribution 2 — Multi-Agent Evolution (architectural patterns)

One paragraph: motivated by C2 (open-ended construction requires multi-file infrastructure). **Not** framed as class-expansion theorem (see §2.2.4); instead, four specific architectural patterns whose presence/absence is verifiable by inspection of the evolver pipeline:

- **Persistent cross-cycle state** — `task_board.md`, `research_log.jsonl`, `architecture.md` retained across cycles; enables build-on-prior-work that single-cycle chain evolvers (A-Evolve, A-Evolve variants) cannot.
- **Parallel independent research agents** — multiple researchers explore disjoint hypothesis branches in isolation; reduces premature convergence vs. sequential refine.
- **Role-distinct objectives** — Analyst (decompose), Researcher (investigate), Builder (implement), Verifier (test). Verifier uses a different success criterion from Builder, unlike single-objective self-critique (Reflexion / Self-Refine).
- **HITL hooks at phase boundaries** — forward-reference §2.5.

Each pattern's contribution is justified by ablation in RQ2.

> **Figure 5** (placeholder) — Multi-agent orchestration flow diagram.

### 2.5 Contribution 3 — HITL Integration (handling experience insufficiency)

One paragraph: motivated by C3 — when $\mathcal{H}_t$ contains no useful signal for $x_t$'s regime, the evolver's *input* is inadequate, not its *capability*. No amount of multi-agent expansion or task-conditional routing fixes this; external direction is required.

**Two structurally distinct hook points.** They differ along the axis of *what the human supplies*: direction (semantic guidance) vs. resource (a credential the evolver cannot discover from trajectories).

- *Taskboard / Analyst phase — direction injection.* When the Analyst flags a novel regime with no prior coverage in `task_board.md`, a HITL line is offered ("describe how to approach `<regime>` or skip"). Addresses **C3** directly: $\mathcal{H}_t$ has no transferable signal, so the human supplies the missing prior. Cheap and high-leverage when triggered (one direction line shapes the whole research cycle).
- *Builder phase — credential / token injection.* When the Builder's pipeline-construction step encounters a `401`/`403` or a configuration prompt for missing credentials, a HITL line is offered ("provide `<KEY_NAME>` or skip"). Strictly a *resource* gate — the evolver knows what to build but cannot execute without auth. Distinct from C3 in mechanism (the data exists, access is gated) but shares its empirical signature (no amount of evolution closes the gap).

**Triggering.** Hooks are not always-on. They activate on evolver-internal signals: Analyst-flagged "novel regime" markers (taskboard hook); failed authentications during Builder-phase API calls (credential hook). Both are silent when not triggered. Typical cost when invoked is <30 seconds of human time per cycle; zero cost otherwise.

> **Figure 6** (placeholder) — Two HITL trigger points in the evolver pipeline: taskboard-direction (C3 steering) and builder-credential (resource gate).

---

## 3. Experiments

Setup first, then four RQs, each mapped to one challenge or system-level claim.

### 3.1 Experimental setup

#### 3.1.1 Benchmarks and data
One paragraph per benchmark (PolyBench, CTF-Dojo, FutureX): size, time span, evaluation metric, how temporal order is enforced, which D dimensions exercised, and (new) which slices exhibit C3-style experience insufficiency.

> **Table 1** (placeholder) — Benchmark statistics: tasks, time span, batch size, shift signature, open-ended domain, novel-regime slice, evaluation metric.

#### 3.1.2 Experimental configuration
One paragraph: solver model, evolver model, batch size, number of evolution cycles, seeds, evaluation details (metrics, decoding temperature, timeouts).

#### 3.1.3 Research questions (forward reference)
One sentence per RQ.

- RQ1: Does our system outperform existing self-evolve methods, and how much room remains vs. an expert-designed reference?
- RQ2 (C2 / $L_{\text{evo}}$ side): Which multi-agent architectural patterns are load-bearing, and what artifact types do they produce?
- RQ3 (C1 / $L_{\text{nav}}$ side): Is navigation gain predicted by shift magnitude (static) and shift accumulation (dynamic), as Propositions 3–4 require?
- RQ4 (C3): Does HITL produce gains *specifically and only* on experience-insufficient task slices?

### 3.2 RQ1 — Does our system outperform existing self-evolve methods?

**Hypothesis.** The full system (multi-agent + navigation + HITL) outperforms (i) no-evolution baselines, (ii) multiple representative self-evolve methods covering linear-chain, archive-based, and meta-program search paradigms, and (iii) sits within range of an expert-designed harness reference. Each contribution helps alone (one-on ablation rows); the full system helps more (composition).

**Table 2 — Main results** (illustrative; expanded baseline set):

| Method | PB-CWR% ↑ | PB-Sharpe ↑ | CTF-Acc% ↑ | CTF-Solve@1 ↑ | FX-Acc% ↑ | FX-F1 ↑ | Avg Rank ↓ |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Base agent (no evolution)** | | | | | | | |
| Sonnet 4.6 | −25.2 | −0.41 | 41.8 | 28.3 | 47.6 | 0.52 | 9.0 |
| DeepSeek V3.2 | −31.4 | −0.58 | 38.4 | 25.1 | 44.1 | 0.47 | 10.5 |
| Kimi K2.5 | −34.1 | −0.63 | 36.1 | 23.4 | 42.9 | 0.45 | 11.0 |
| **Human-designed baselines** | | | | | | | |
| MiroFlow (hand-crafted pipeline) | — | — | — | — | 56.0 | 0.61 | — |
| Domain-expert toolset | +8.3 | 1.24 | 59.3 | 42.7 | — | — | — |
| **Self-evolve baselines** | | | | | | | |
| A-Evolve (linear chain) | +0.2 | 0.08 | 47.9 | 34.0 | 45.2 | 0.49 | 5.8 |
| DGM (archive-based) | −2.1 | −0.12 | 49.2 | 35.8 | 46.1 | 0.50 | 5.5 |
| ADAS / AFlow (meta-program search) | +1.0 | 0.15 | 48.7 | 34.6 | 44.9 | 0.48 | 5.3 |
| **Our contributions (ablation)** | | | | | | | |
| Multi-agent only | +2.9 | 0.38 | 52.4 | 38.2 | 48.9 | 0.54 | 3.8 |
| Navigation only | +2.7 | 0.35 | 54.1 | 39.6 | 48.3 | 0.53 | 3.5 |
| Multi + Nav | +5.1 | 0.72 | 56.8 | 41.5 | 50.5 | 0.56 | 2.0 |
| **Full system (Multi + Nav)** | **+6.2** | **0.89** | **57.6** | **42.1** | **53.4** | **0.59** | **1.0** |

Solver fixed at Sonnet 4.6 in main table. Multi-backbone results (DeepSeek V3.2, Kimi K2.5) reported in Appendix.

**Reading the table.** (i) Human-designed baselines represent upper-bound reference points — hand-crafted by domain experts with full knowledge of the benchmark. (ii) Across self-evolve baselines (rows 3–5), no single method dominates — A-Evolve is strongest on PolyBench, DGM on CTF-Dojo, ADAS on PolyBench (close ties). (iii) Each of our contributions individually exceeds all self-evolve baselines on average. (iv) The full system approaches or matches human-designed references, with the remaining gap concentrated on experience-insufficient slices (addressed by HITL in RQ4).

### 3.3 RQ2 — What makes evolution stronger? (C2 / $L_{\text{evo}}$)

**Hypothesis.** The multi-agent evolution's strength derives from three independent dimensions: feedback signal quality, knowledge accumulation, and cognitive decomposition. Each reduces $L_{\text{evo}}$ through a distinct mechanism; removing any one degrades performance.

**Three dimensions of stronger evolution:**

1. **Feedback signal** (temporal-reveal) — The evolver sees which tasks succeeded/failed (not just solver behavior). Richer signal → more targeted improvements. *Without*: evolution learns blind from trajectories only.

2. **Accumulated knowledge** (persistent cross-cycle state) — task_board.md, research_log.jsonl, and architecture.md carry forward across cycles. Each cycle builds on prior discoveries. *Without*: each cycle starts fresh — no learning curve, rediscovers from scratch.

3. **Decomposed reasoning** (4-phase role separation) — Analyst decomposes failures, researcher explores solutions, builder implements, verifier quality-checks. Specialized labor produces infrastructure that monolithic reasoning cannot. *Without*: single-agent evolver does everything (= A-Evolve baseline).

**Design.** Ablate each dimension on all three benchmarks:

| Configuration | Signal | Memory | Decomposition |
|---|:---:|:---:|:---:|
| Full system | ✓ | ✓ | ✓ |
| −feedback signal | ✗ | ✓ | ✓ |
| −accumulated knowledge | ✓ | ✗ | ✓ |
| −decomposed reasoning (= A-Evolve) | ✓ | ✓ | ✗ |

**Table 4 — Ablation results (illustrative):**

| Configuration | PB-CWR% | CTF-Acc% | FX-Acc% |
|---|---:|---:|---:|
| Full system | +6.2 | 57.6 | 53.4 |
| −feedback signal | +3.8 | 53.1 | 49.7 |
| −accumulated knowledge | +4.1 | 54.2 | 50.1 |
| −decomposed reasoning (A-Evolve) | +0.2 | 47.9 | 45.2 |

**Reading.** (i) Decomposed reasoning is the largest contributor — removing it (→ A-Evolve) drops performance to the single-agent baseline. (ii) Feedback signal and accumulated knowledge contribute independently; each accounts for ~3–4 pts. (iii) All three are necessary — no single dimension subsumes the others.

> **Figure 7a — RQ2 statistics: artifact-type distribution by ablation.** Stacked horizontal bars per ablation row (full / −feedback / −knowledge / −decomposed / A-Evolve), with each bar partitioned into Prompt / Tool / Pipeline / Distill. The visual claim is that *the construction shifts qualitatively, not just quantitatively*: only the full configuration populates the Pipeline and Distill tails. Numbers seeded from `experiment.tex` Table 4 / `tab:rq2_ablation`.

> **Figure 7b — RQ2 demonstration: a real CTF-Dojo evolution cycle.** Drawn from a logged run (cycle to be selected from a successful "binary-reversing" branch; provenance = `experiments/ctf_dojo/<run_id>/cycle_<N>/`). Five panels left-to-right with the actual artifacts produced between phases:
>
> 1. **Analyst.** Trajectory excerpts from the failing batch + the resulting `task_board.md` diff (new failure regime entry, e.g., "stripped ELF reverse-engineering — repeated solver failures").
> 2. **Researchers (parallel).** Three side-by-side `research_log.jsonl` rows from independent agents (e.g., R1 = `radare2`, R2 = `Ghidra-headless`, R3 = `angr`), each with `works:true/false`, coverage, runtime.
> 3. **Builder.** The `infra/binary_analysis.py` file written, plus the `architecture.md` diff that records what was added.
> 4. **Verifier.** Test invocations of the new pipeline against held-out tasks, with pass/fail counts and the retry signal back to Builder if any failed.
> 5. **Downstream.** The task that triggered the cycle, re-solved on the next batch with the new pipeline routed in.
>
> Goal: make "persistent state + parallel research + role separation" tangible, so the §3.3 ablation rows have a concrete referent.

**Compute-matched sanity check (appendix).** Single-agent evolver given the full multi-agent token budget (self-critique loops, best-of-N) does not close the gap — confirming the difference is structural, not compute.

### 3.4 RQ3 — Measuring navigation loss $L_{\text{nav}}$ (C1)

**Hypothesis.** $L_{\text{nav}}$ is directly measurable and significantly non-zero on temporal benchmarks. The gap grows over the stream as shift accumulates, and vanishes under temporal shuffling (falsification).

**Three readings from one evolved tree.** A single navigation run per benchmark. On the *same* tree, on the *same* tasks, we measure:

- **Unconditional** — force every task through one fixed branch (e.g., `main`). $V(\varphi(\mathcal{H}_t), x_t)$.
- **Navigator** — let the navigator route each task. $V(\varphi(\mathcal{H}_t, x_t), x_t)$ realized.
- **Oracle-branch** — run solver on every branch for every task; per-task max. Lower bound on $V(C^*_\Phi(x_t), x_t)$.

All three share identical evolver effort (zero extra evolution); only the solver's branch choice changes.

**Metrics:**
- $L_{\text{nav}}$ upper bound: oracle − unconditional
- Realized navigation gain: navigator − unconditional
- Routing quality loss: oracle − navigator (diagnostic)

**Statistical test.** Paired Wilcoxon signed-rank on per-task (oracle − unconditional). Null: no gap.

**Falsification.** Same measurement on temporally shuffled benchmark. Under shuffling, non-stationarity is destroyed; the gap should collapse to noise (Prop 2). Reported in appendix.

> **Figure 8a — RQ3 statistics: per-batch accuracy + harness size.** Two-panel stats figure on a shared x-axis (batch index over the CTF-Dojo stream).
> - *Top panel*: per-batch accuracy of three readings from the same evolved tree — unconditional (force `main`), navigator (route per task), oracle-branch (per-task max). The gap *navigator − unconditional* widens with batch index, as Prop 4 predicts; the gap *oracle − navigator* is the routing-quality residual.
> - *Bottom panel*: per-solve harness size in KB. Linear evolution grows monotonically (~60 KB by end of CTF-Dojo, ~176 KB by end of FutureX); navigation stays bounded (~12 KB) because each task loads only one branch. This is a *symptom* of $L_{\text{nav}}$ accumulation, not an independent claim.
>
> Numbers and curves seeded from `experiment.tex` `fig:rq3_dynamic` and `fig:rq3_harness_size`.

> **Figure 8b — RQ3 demonstration (combined): tree growth + routing trace.** One figure, two stacked panels, both from a single CTF-Dojo run.
> - *Top panel — strategy tree as it grew*. Time-axis annotated with branch-creation events: `main` at t=0; `branch/crypto-classical` forked at cycle 2 after Analyst flagged repeated classical-cipher failures; `branch/binary-reversing` at cycle 4 after stripped-ELF tasks appeared; `branch/web-modern` at cycle 7 after a JWT/SQLi cluster. Each fork annotated with the trigger ("3 consecutive classical-cipher failures on `main`") so the *causal chain from shift detection to branch creation* is visible.
> - *Bottom panel — routing for one task*. A single CTF-Dojo task header (e.g., "RE/2018 — stripped x86-64 ELF, find the flag"). Show what $F_{\text{Navigate}}$ reads: three side-by-side `git show <branch>:README.md` excerpts (one per branch). Show the navigator's structured output: `{"branch": "binary-reversing", "confidence": 0.83, "reason": "stripped ELF + reverse-engineering keywords match this branch's tools/registry; main lacks radare2/Ghidra"}`. Then show the solver checking out `branch/binary-reversing` and producing the flag.
>
> Goal: make navigation concrete — *how* the tree grew (creation), and *how* a task gets routed at solve time. Replaces the §2.3 placeholder Figure 4 (which should now just forward-reference here).

### 3.5 RQ4 — HITL on experience-insufficient task slices (C3)

**Hypothesis.** On task slices where $\mathcal{H}_t$ contains no useful signal (novel regime, missing credentials, unfamiliar source), HITL provides direction that experience-driven evolution structurally cannot. The accuracy gain concentrates *specifically and only* on the experience-insufficient slice; no inflation on other slices (rules out "HITL helps in general" — distinguishes C3 from a generic compute-help effect).

**Design.** FutureX case study (the benchmark with the clearest novel-regime slice). Identify the experience-insufficient slice **a priori** (Chinese-language platform-data tasks; English Wikipedia / mainstream-news priors do not transfer; APIs require credentials). Compare two configurations:

- **Full system, no HITL** — multi-agent + navigation, fully experience-driven (same as RQ1's "Multi + Nav" row).
- **Full system, with HITL** — same, plus credential prompts at Research phase and task-board direction at Build phase, triggered by evolver-internal signals.

Report per-configuration:
- Accuracy on **experience-insufficient slice** (zh-finance) — primary outcome
- Accuracy on **other slices** (English news, Wikipedia-covered topics) — control; should not change
- Number of HITL invocations and total human time

> **Figure 9a — RQ4 statistics: targeting pattern.** Grouped bar chart, two slices × two conditions. Slices = {zh-finance (experience-insufficient), other (control)}. Conditions = {no HITL, +HITL}. The two zh-finance bars span a large gap (+18.6 pts); the two control bars are within seed noise (+0.1 pt). A single visual makes the C3 *signature* — gain is concentrated on the experience-insufficient slice — readable at a glance. Numbers from Table 3.

> **Figure 9b — RQ4 demonstration: two HITL hooks across two cycles (FutureX).** Drawn from one logged FutureX run (provenance = `experiments/futurex/<run_id>/`). The two hooks fire in *different* cycles because the triggers are sequential by construction: direction must arrive before the Builder has anything to authenticate against. Each row in the figure is one cycle.
>
> - **Cycle $k$ — Taskboard / Analyst hook (C3 direction injection).** Analyst processes the failing batch; the routing log shows the navigator returning `{"branch": null, "confidence": 0.21}` on three zh-finance tasks (no covering branch, low confidence). Analyst writes `task_board.md` with a "novel regime, no prior coverage" tag. *HITL fires*: human supplies a one-line direction ("Chinese-language equity prediction; Eastmoney/Sina Finance are canonical sources; use ZH news + macro indicator joins"). Direction line is appended to `task_board.md` and read by Researchers in the same cycle. Show: routing log → analyst diff → HITL prompt → human response → researcher pickup.
>
> - **Cycle $k+m$ — Builder hook (credential / token injection).** With direction from cycle $k$, parallel Researchers identify Eastmoney as a viable source. Builder begins constructing `infra/chinese_finance_pipeline.py`; first execution returns `403 Forbidden` from the Eastmoney endpoint. *HITL fires*: human supplies `EASTMONEY_API_KEY`. Builder retries; pipeline runs to completion; Verifier confirms coverage on held-out zh-finance tasks. Show: builder execution log → 403 → HITL prompt → token injection → successful execution → verifier pass.
>
> The figure caption notes: *cycles $k$ and $k+m$ are taken from the same run; the actual indices depend on when each trigger first fires (typical: $k=2$, $k+m=3$ on FutureX).* Goal: show the two structurally distinct interventions (direction vs. resource) and that they fire on independent triggers, not as a packaged "human help" event.

**Table 3 — HITL impact on experience-insufficient slice (illustrative):**

| Configuration | zh-finance slice | Other slices (control) | Overall | HITL invocations | Human time |
|---|---:|---:|---:|---:|---:|
| Full system, no HITL | 34.6% | 52.3% | 50.5% | 0 / 4 cycles | 0 s |
| Full system, with HITL | **53.2%** | 52.4% | **53.4%** | 4 / 4 cycles | ~95 s |
| *Human-designed reference (MiroFlow)* | *58.0%* | *55.2%* | *56.0%* | — | *weeks* |
| Δ (HITL vs no-HITL) | **+18.6** pts | +0.1 (noise) | +2.9 | | |
| Gap to human reference | −4.8 pts | −2.8 pts | −2.6 | | |

**Discussion.** (i) The +18.6 point gain concentrates on the experience-insufficient slice and is +0.1 on the control slice (within seed noise). This pattern is the empirical signature of C3: when $\mathcal{H}_t$ has no signal for the task regime, direction must come from outside, and the intervention's effect is *targeted* — not diffuse. (ii) With HITL, the system closes most of the gap to the human-designed reference — from −5.5 pts (no HITL) to −2.6 pts (with HITL) — using ~95 seconds of human time total vs. weeks of expert engineering. (iii) The remaining gap (−4.8 pts on zh-finance) represents the margin where human domain expertise in API integration still outperforms evolved infrastructure, even with credential guidance. HITL is therefore not an "always-on" cost but a structurally-triggered intervention that achieves near-expert performance at orders-of-magnitude less human effort.

---

## Conclusions

Self-evolving agents on long-horizon, non-stationary, open-ended task streams exhibit three task-intrinsic failure modes (C1–C3). A regret decomposition $L_{\text{evo}} + L_{\text{nav}}$, augmented by an experience-availability axis, explains them — with $L_{\text{nav}}$ admitting empirical predictions (validated in RQ3) and $L_{\text{evo}}$ organizing architectural patterns (validated in RQ2). Three composable architectural contributions — agentic navigation, multi-agent evolution, HITL integration — each address one challenge, each is independently effective in ablation, and together they close most of the gap to an expert-designed reference.

**Open questions.** Branch lifecycle (promote / prune), self-evolving navigator, automated detection of HITL trigger conditions, cross-domain transfer of D1/D2/D3, and quantification of experience availability as a third measurable axis alongside shift magnitude.
