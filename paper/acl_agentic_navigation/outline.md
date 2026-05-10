# Paper Outline — Agentic Navigation + Multi-Agent Evolution

## Thesis (one sentence)

Agentic evolution on real-world deployments fails along three orthogonal task dimensions — long-horizon (D1), non-stationarity (D2), and open-endedness (D3) — producing three named failure modes that a regret decomposition ($L_{\text{evo}} + L_{\text{nav}}$) explains and that two composable architectural contributions (multi-agent evolution, navigation) address.

---

## 1. Introduction

One-paragraph role for each subsection.

### 1.1 Opening — agentic evolution and why "more evolution ≠ better"
One paragraph: standard A-Evolve pitch; headline puzzle — early-freeze beats full-evo on all three of our temporal benchmarks; this doesn't happen on i.i.d. benchmarks.

### 1.2 Three dimensions of real-world difficulty
One paragraph: introduce D1 (long-horizon), D2 (non-stationarity), D3 (open-endedness); state they are orthogonal; our three benchmarks exercise all three.

> **Figure 1** (placeholder)

### 1.3 Three challenges — preliminary evidence
One paragraph introducing the three challenges grounded in preliminary experiments. Each challenge gets one sentence + the pre-experimental signature.

- **C1 (D2) — Non-monotonic evolution.** Early-freeze beats full-evo; signature = accuracy curve inverts over cycles.
- **C2 (D3) — Evolver capability bottleneck.** Weak evolver vs strong evolver; signature = artifact-type distribution.
- **C3 (D1) — Harness accumulation exceeds capacity.** 18–60× harness growth end-of-run under H1; signature = monotone size curve.

> **Figure 2** (placeholder): show the evidence here

### 1.4 Our approach — what each contribution fixes
One paragraph: multi-agent evolution expands the evolver class $\Phi$ (addresses C2); navigation conditions the harness on the task (addresses C1); both are jointly required to handle long-horizon accumulation (C3). Forward-reference §2.

### 1.5 Contributions

1. **Three empirical challenges** on PolyBench, CTF-Dojo, FutureX — each tied to one dimension and absent from i.i.d. benchmarks: C1 non-monotonic scaling (early-freeze > full-evo), C2 capability bottleneck (no infrastructure from prompt-level evolvers), C3 harness accumulation (18–60× growth).
2. **Theoretical framework explaining the failures.** Regret decomposes into $L_{\text{evo}}(\Phi, K) + L_{\text{nav}}(\varphi)$ — orthogonal terms that diagnose C1 ($L_{\text{nav}} \geq \Sigma_t/4$), C2 (weak $\Phi$), and C3 (both, with horizon).
3. **Multi-agent evolution** (addresses C2, contributes to C3): 4-phase pipeline (Analyst → Researchers → Builder → Verifier) with persistent cross-cycle state and HITL hooks — expands $\Phi$ from prompt-level to multi-file infrastructure and distills history across cycles.
4. **Agentic navigation** (addresses C1, contributes to C3): git-backed strategy tree with per-task routing over branch workspaces — conditions the harness on $x_t$ and partitions capacity across branches. Jointly with (3), bounds harness size over long horizons.

---

## 2. Method

Structured as theory-first, then the two concrete architectures.

### 2.1 Problem setting
One paragraph: bounded-harness history-conditioned formulation (v2 from `audience_and_rqs.md`). Define task stream, harness $C_t = \varphi(\mathcal{H}_t)$, capacity $K$.

### 2.2 Theoretical framework

#### 2.2.1 Harness and regret
One paragraph: define $V(C, x)$, regret of harness.

#### 2.2.2 Regret decomposition (Theorem 1)
One paragraph: state $\mathbb{E}[\text{Regret}] = L_{\text{evo}}(\Phi, K) + L_{\text{nav}}(\varphi)$ and interpret.

#### 2.2.3 When each loss matters (Theorems 2, 3)
One paragraph: $L_{\text{nav}} = 0$ under stationarity; $L_{\text{nav}} \geq \Sigma_t / 4$ under shift — maps to C1.


### 2.3 Contribution 1 — Multi-Agent Evolution (expanding $\Phi$)
One paragraph: 4-phase structured evolution (Analyst → Researchers → Builder → Verifier) with persistent cross-cycle state (`task_board.md`, `research_log.jsonl`, `architecture.md`). Addresses C2(a) construction + C3 distillation. HITL hooks at credential and task-board stages — addresses C2(b) direction under severe shift.

> **Figure 3** (placeholder) — Multi-agent orchestration flow diagram (reuse the one in `paper/multi_agent_orchestration.md`).

### 2.4 Contribution 2 — Navigation via Strategy Tree (conditioning the harness)
One paragraph: git-backed strategy tree; F_Navigate reads each branch's workspace (README, system prompt, skills, tools) via `git show`; routes task to best-fit branch; inline (single sandboxed evolver LLM call with agentic branching) and orchestrated (plan-driven) modes. Addresses C1 directly + C3 capacity-partitioning.

> **Figure 4** (placeholder) — Strategy tree + per-task routing diagram (reuse the one in `paper/navigation_implementation.md`).

---

## 3. Experiments

Setup first, then one subsection per RQ, each with hypothesis → design → results → discussion.

### 3.1 Experimental setup

#### 3.1.1 Benchmarks and data
One paragraph per benchmark (PolyBench, CTF-Dojo, FutureX): size, time span, evaluation metric, how temporal order is enforced.

> **Table 1** (placeholder) — Benchmark statistics: tasks, time span, batch size, shift signature, open-ended domain, evaluation metric.

#### 3.1.2 Experimental configuration
One paragraph: solver model, evolver model, batch size, number of evolution cycles, seeds, evaluation details (metrics, decoding temperature, timeouts).

#### 3.1.3 Research questions (forward reference)
One sentence per RQ (5 RQs).

### 3.2 RQ1 — Does our system outperform existing agentic evolution on real-world deployment streams?

**Hypothesis.** The full system (multi-agent evolution + agentic navigation) outperforms no-evolution and linear-evolution baselines on every benchmark. The two contributions each help alone; jointly they help more.

**Table 2 — Main results** (fake numbers, illustrative; solver backbone varied within each method):

| Method | Solver backbone | Evolver | Navigation | PolyBench | CTF-Dojo | FutureX | Avg |
|---|---|:---:|:---:|---:|---:|---:|---:|
| *Base agent (no evolution)*            | Claude Sonnet 4.6 | —            | — | 68.7  | 41.8  | 47.6  | 52.7  |
|                                        | DeepSeek V3.2     | —            | — | 65.3  | 38.2  | 44.1  | 49.2  |
|                                        | Kimi K2.5         | —            | — | 61.4  | 35.7  | 41.3  | 46.1  |
| Linear evolution *(A-Evolve engine)*   | Claude Sonnet 4.6 | single-agent | — | 80.4  | 47.9  | 45.2  | 57.8  |
|                                        | DeepSeek V3.2     | single-agent | — | 77.1  | 44.6  | 42.3  | 54.7  |
|                                        | Kimi K2.5         | single-agent | — | 72.8  | 41.2  | 39.0  | 51.0  |
| Multi-agent evolution *(ours)*         | Claude Sonnet 4.6 | multi-agent  | — | 82.1  | 52.4  | 48.9  | 61.1  |
|                                        | DeepSeek V3.2     | multi-agent  | — | 78.9  | 49.1  | 46.0  | 58.0  |
|                                        | Kimi K2.5         | multi-agent  | — | 74.3  | 45.7  | 42.8  | 54.3  |
| Agentic navigation *(ours)*            | Claude Sonnet 4.6 | single-agent | ✓ | 82.6  | 54.1  | 48.3  | 61.7  |
|                                        | DeepSeek V3.2     | single-agent | ✓ | 79.4  | 50.8  | 45.4  | 58.5  |
|                                        | Kimi K2.5         | single-agent | ✓ | 74.9  | 47.3  | 42.1  | 54.8  |
| **Full system *(ours)***               | Claude Sonnet 4.6 | multi-agent  | ✓ | **84.3** | **57.6** | **52.1** | **64.7** |
|                                        | DeepSeek V3.2     | multi-agent  | ✓ | **81.2** | **54.2** | **49.3** | **61.6** |
|                                        | Kimi K2.5         | multi-agent  | ✓ | **76.8** | **50.4** | **46.0** | **57.7** |

Evolver LLM held fixed per row; only the solver backbone varies within each method.

### 3.3 RQ2 — A ceiling the evolver cannot climb: witnessing $L_{\text{evo}}$ (C2 + Theorem 4)

**Hypothesis.** Single-agent evolution *saturates* as we scale its available axes (evolver LLM capability, compute budget), while multi-agent evolution exceeds that plateau — witnessing $V(C^*_{\Phi_\text{multi}}) > V(C^*_{\Phi_\text{single}})$ (Theorem 4's strict inequality).

**Why saturation.** $L_\text{evo}(\Phi, K)$ is defined against an unreachable class-optimum $C^*_\Phi$. We cannot measure it directly. Instead we scale single-agent along every axis available to it until performance saturates — the plateau is the empirical stand-in for $V(C^*_{\Phi_\text{single}})$. If multi-agent sits above this plateau, the gap is compute-independent and structural to the class.

**Design.** Fix solver LLM and benchmark. Scale single-agent along two axes, with all other axes held constant:
- **Evolver LLM capability**: Haiku-3.5 → Sonnet-4.6 → Sonnet-4.6 extended-thinking.
- **Per-cycle LLM call budget**: 1 → 3 → 9 calls (self-critique / retry / refine).

Report accuracy at each scaling point, plus multi-agent as a single horizontal line. The claim is **multi-agent stays above the highest single-agent scaling point**, evidencing the class-structural gap.

**Figure 5** (placeholder — fake numbers, CTF-Dojo):

```
 Accuracy (%)
   ▲
60 │ ── ── ── ── ── ── ── ── ── ── ──●── ── ── ── ── ──  Multi-agent  57.6
   │
55 │                                                   ┌── structural gap
   │                                   ●─────●   52.4  │       +5.2
50 │                             ●
   │
45 │                       ●
   │
40 │                 ●
   │
   └─────┬─────┬─────┬─────┬─────┬─────┬─────────────▶
       Haiku  Sonnet 3×   9×    9× +      (single-agent scaling axis)
       1×    1×          thinking

 Single-agent scales along every available axis, then saturates.
 Multi-agent sits above the plateau --- compute-independent gap.
```


### 3.4 RQ3 — The cost of one-size-fits-all: measuring $L_{\text{nav}}$ (C1 + Theorem 3)

**Hypothesis.** Unlike $L_\text{evo}$, $L_\text{nav}$ is *directly measurable*: the unconditional-harness side $V(\varphi(\mathcal{H}_t), x_t)$ is just accuracy with every task forced through one fixed branch, and the per-task optimum is lower-bounded by the **oracle-branch** reading (best branch per task on the same evolved tree). The gap is genuinely non-zero: it passes a paired significance test on every benchmark, and its sign reverses only on shuffled-order streams where non-stationarity is destroyed.

**Three readings from one evolved tree.** A single navigation run per benchmark. On the *same* tree, on the *same* tasks, we measure:

- **Unconditional** — force every task through one fixed branch (e.g., `main`). → $V(\varphi(\mathcal{H}_t), x_t)$.
- **Navigator** — let the navigator route each task. → $V(\varphi(\mathcal{H}_t, x_t), x_t)$ *(realized)*.
- **Oracle-branch** — run the solver on every branch for every task, keep per-task max. → lower bound on $V(C^*_\Phi(x_t), x_t)$.

All three share identical evolver effort (zero extra evolution); only the solver's branch choice changes. Per-task $L_\text{nav}$ proxy: oracle − unconditional. Navigator $L_\text{nav}$: navigator − unconditional. Navigator routing loss: oracle − navigator (reported for diagnostic transparency).

**Significance.** Paired Wilcoxon signed-rank test on per-task (oracle − unconditional). Null: no gap.

**Falsification control (defensive).** Same measurement re-run on a **temporally shuffled** version of each benchmark. Under shuffling, non-stationarity is destroyed ($\Sigma_t \to 0$), so Theorem 2 predicts the gap collapses to noise. Reported in the appendix.

**Figure 6 — One-benchmark example, per-batch accuracy over the temporal stream (fake numbers, CTF-Dojo):**

```
  Accuracy (%)
     ▲
  62 ┤                                                       ┈┈┈
     │                                          ┈┈┈┈┈┈┈┈ Oracle-branch
  58 ┤                             ┈┈┈┈┈┈┈      │           95% CI
     │                  ┈┈┈┈┈┈┈┈ │              ━━━━━━━━━━
  54 ┤         ┈┈┈┈┈┈┈ │        ━━━━━━━━━━━━━   Navigator
     │  ┈┈┈┈ │         ━━━━━━━━━
  50 ┤┈┈    ━━━━━━━━━━
     │━━━━━
  46 ┤────────────────────────────────────────────────  Unconditional
     │                                                  (reference, L_nav = 0)
  42 ┤
     │
     └──┬─────┬─────┬─────┬─────┬─────┬─────┬─────▶
        5    10    15    20    25    30    35         Batch index (time →)
        ◄─── low-shift early stream ─┼─ high-shift late stream ───►

  Axis:   x = batch index along the temporal stream (early = low Σ_t, late = high Σ_t)
          y = mean per-task accuracy within batch, with 95% CI shown on oracle curve

  Aggregate (whole stream, n = 261 tasks):
      oracle − uncond. = +10.6  ***   ← upper bound on L_nav
      nav    − uncond. =  +8.3  ***   ← realized navigator gain
      oracle − nav     =  +2.3  *     ← routing-quality loss (diagnostic)

      *** p < 0.001 · * p < 0.05 · paired Wilcoxon signed-rank test per task
      Per-batch error bars (│ on oracle curve) are 95% CIs across tasks
      in that batch; the oracle CI stays strictly above the unconditional line
      from batch ~8 onward, a visual confirmation of p < 0.001.
```

*Three curves sharing the same evolved tree: dotted top with CI bars = oracle-branch (per-task lower bound on the unreachable optimum, upper envelope of $L_\text{nav}$); solid middle = navigator's realized accuracy; dashed flat bottom = unconditional (one forced branch, $L_\text{nav}=0$ reference). As the stream progresses (batch index ↑), the envelope widens — the shape of $L_\text{nav}$ growing with shift magnitude $\Sigma_t$. The oracle-line CIs clear the unconditional line once $\Sigma_t$ grows, giving the significance visually; stars in the summary block report the aggregate paired test.*

### 3.5 RQ4 — Does branching mitigate long-horizon harness accumulation? (C3)

**Hypothesis.** Under linear evolution, all accumulated experience piles onto one harness — context inflates monotonically and eventually exceeds any bounded solver input budget (C3). Under our full system, the *strategy tree* partitions accumulated content across branches, so the **per-solve harness size stays roughly constant across horizon**, even though the *tree-wide* content still grows. The solver never pays for irrelevant content.

**The key measurement.** For each method, we measure two quantities over time:
- **Per-solve harness size** — bytes of prompt + skills + tools + memory the solver actually loads for one task at time $t$. This is what hits the context window.
- **Total evolved content** — bytes of everything in the evolved workspace (across all branches, for our method).

Under linear evolution, these two are equal — one harness holds everything. Under navigation, they diverge: total content grows, but per-solve size stays bounded because each task only loads one branch's content.

**Figure 7 — Per-solve harness size across the temporal stream (fake numbers, CTF-Dojo):**

```
  Harness size (KB loaded per solve)
     ▲
 80 ┤                                               ●
    │                                          ●
 60 ┤                                     ●              ●●●  Linear evolution
    │                                ●                        (all content → one harness)
 40 ┤                           ●
    │                      ●
 20 ┤                 ●                          ━━━━━━━━━━  Full system (ours)
    │            ●        ━━━━━━━━━━━━━━━━━━━━━           (per-solve: 1 branch load)
 10 ┤       ●━━━━━━━━
    │  ●━━━
     └──┬─────┬─────┬─────┬─────┬─────┬─────┬─────▶
        5    10    15    20    25    30    35          Batch index (time →)

 Linear evolution: monotone growth, ~60 KB by end of stream
 Full system:      bounded at ~12 KB per solve, regardless of horizon
                   (tree-wide content grows, but solver only sees one branch)
```


**Figure 8 — Example evolved strategy tree (fake structure, CTF-Dojo):**

```
   main
   │   (stationary content, inherited by every task)
   │     • flag verification routines
   │     • sandbox inspection recipes
   │     • generic recon / enumeration tools
   │
   ├── branch/crypto-classical       (era: 2011–2014)
   │     • RSA / ECC helper tools
   │     • legacy cipher scripts
   │     • cryptanalysis skill notes
   │
   ├── branch/binary-reversing       (era: 2017–2018)
   │     • pyinstaller extract
   │     • x86 disassembly helpers
   │     • ROP-gadget enumeration
   │
   └── branch/web-modern             (era: 2022–2024)
         • OAuth / JWT flows
         • web fuzzer setups
         • container / cloud exploit recipes

   Per-solve load:  10–14 KB  (main + one selected branch)
   Tree-wide total: 52.3 KB   (main + all branches combined)
```

### 3.6 RQ5 — Does human-in-the-loop help when experience runs out? (C2(b) case study)

**Hypothesis.** On severe-shift tasks where the evolver's historical signal is insufficient (novel regime, missing credentials, unfamiliar data source), a lightweight human-in-the-loop intervention — supplying a credential or a pointer — unlocks harness improvements that purely experience-driven multi-agent evolution cannot discover.

**Design.** FutureX case study only (one benchmark). On the Chinese-language / platform-data slice of FutureX (highest-shift regime), compare two configurations:
- **Full system, no HITL** — multi-agent + navigation, fully experience-driven.
- **Full system, with HITL** — same, but human can answer credential prompts at the Research phase and add a line to the task board at the Build phase.

**Example trace (fake, illustrative).**

```
  Cycle 3, Phase 2 (Research):
    Research-agent-2 (regime: chinese_finance):
      Tested Eastmoney API endpoint /api/qt/stock/get ... 403 Forbidden
      Credential needed? YES   (env: EASTMONEY_API_KEY)

    ▸ HITL prompt to human:
        "Research found 'Eastmoney API' for regime 'chinese_finance'
         but needs credentials. Provide EASTMONEY_API_KEY or type 'skip':"
    ▸ Human response:
        <provides key>
    ▸ Research-agent-2 retries with credential:
        works=true, latency=420ms, coverage=[stock_ohlc, market_cap, PBOC_rate]

  Cycle 3, Phase 3 (Build):
    Builder reads verified research and constructs
    infra/chinese_finance_pipeline.py — which the solver now
    invokes for all zh-finance tasks in subsequent batches.

  Downstream effect (late stream, zh-finance slice):
    Accuracy before Cycle 3:  31.2 %
    Accuracy after  Cycle 3:  54.8 %
```

**Table 3 — HITL impact on the zh-finance slice (fake numbers):**

| Configuration | Cycles with credential-gated research | zh-finance slice accuracy | Credential asks answered |
|---|---:|---:|---:|
| Full system, no HITL | 4 skipped       | 34.6 % | 0 / 4 |
| Full system, with HITL  | 4 unblocked | 53.2 % | 4 / 4 |

**Discussion.** The HITL-unblocked configuration's gain concentrates *specifically* on the slice where credentials were requested — it does not inflate accuracy on other slices, ruling out "HITL just helps in general." This matches C2(b) exactly: when $\mathcal{H}_t$ has no useful signal for the task regime, the direction must come from outside. One human response per cycle (typing an API key; <30 s) is enough to unblock a multi-file pipeline the evolver could not otherwise build. HITL is therefore not an "always on" cost — it is triggered only at the specific structural point where experience-driven evolution halts.

---

## Conclusions

Agentic evolution on long-horizon, non-stationary, open-ended task streams exhibits three reproducible failure modes (C1–C3) that a regret decomposition $L_{\text{evo}} + L_{\text{nav}}$ explains. Two composable upgrades — multi-agent evolution and agentic navigation — address the two losses, and jointly mitigate long-horizon harness accumulation.

**Open questions.** Branch lifecycle (promote / prune), self-evolving navigator, cross-domain transfer of D1/D2/D3.
