# Barrier-existence experiment design

This document designs the experiments that empirically prove the two barriers from the regret decomposition exist on our benchmarks, independently of our proposed system.

**Goal.** Not "our system wins" — that is RQ1–4. The goal is "the binding capability requirement that the harness must achieve exists on each benchmark, and is benchmark-specific."

If on each benchmark we can name a measurable capability axis whose level *determines* end-of-stream performance, we have proved $\Levo$ exists: the regret decomposition's "ceiling utility under bounded harness capacity" $V(\Hist, x_t)$ is bounded above by what that capability allows, so a class that cannot reach the required capability level necessarily incurs $\Levo > 0$.

This is much weaker than asserting saturation curves. It is also much easier to prove and much harder to attack.

---

## 0. Framing recap

From Proposition 1 (§3.2):
$$
\mathbb{E}_{x_t}[\text{Regret}(\varphi, x_t)] = \Levo(\Phi) + \Ladapt(\varphi)
$$

- $\Levo(\Phi)$ — the gap between what is achievable from history and the best the *evolver class* $\Phi$ can produce.
- $\Ladapt(\varphi)$ — the gap from the per-task class-optimum to the harness an actually-deployed evolver $\varphi$ commits to before seeing $x_t$.

This document treats $\Levo$ first ($\Ladapt$ is a stub at the bottom).

---

## 1. The strategy: capability bottlenecks, not saturation curves

Earlier drafts proposed three different designs in succession (all discarded, see §6):

1. compute-saturation sweeps,
2. failure-mode atlases of generic LLM pathologies,
3. cross-benchmark 3×2 mechanism grids.

Each was over-engineered. The simplest sufficient design is to show, on each benchmark, the **stair-step pattern of performance vs. capability level**: as the system is granted progressively more of the capability the benchmark cares about, performance climbs in measurable steps.

The stair-step pattern proves two things at once:
- The capability is *binding* (otherwise performance would not climb).
- The capability is *benchmark-specific* (each benchmark's stair-step uses a different capability axis).

A reviewer reading three such stair-steps cannot dispute that the harness has a non-trivial capability requirement on each benchmark. That is exactly $\Levo > 0$.

---

## 1.5. The evidence philosophy: link task-intrinsic statistics to model outcomes

> *Pick a statistic of the task input that is computable without the agent ever running. Plot it against a statistic of the model's behaviour. If the harness specialises along the axis the benchmark cares about, the two will be coupled; if it does not, they will be decoupled.*

This is the unifying principle behind every panel in §2. It separates evidence that *binds the bottleneck to the benchmark* from evidence that merely shows the agent does poorly.

**Why this framing is strong.**

1. **Task-grounded.** The x-axis is a property of the task, not of the agent. A reviewer cannot dismiss the result as a quirk of agent behaviour or evolver tuning — the statistic exists in the benchmark independently of every harness.

2. **Mechanism-revealing.** A coupled (x, y) pattern shows the harness *uses* the input to specialise. A decoupled pattern shows it ignores the input and emits one default behaviour everywhere. The shape of the coupling identifies *which* property the harness fails to read.

3. **Visually distillable to one figure per benchmark.** Either a 2D density (single-agent vs. multi-agent) or a conditional-mean curve ($\mathbb{E}[\text{outcome} \mid \text{task statistic}]$) is enough.

4. **Reviewer-attack-resistant.** The three classic objections — "you tuned the baseline poorly", "your metric is biased", "different runs vary" — all dissolve. Any class that ignores a benchmark-determining input incurs $\Levo > 0$ by construction.

**The instantiation per benchmark.**

| Benchmark | Task-intrinsic statistic (x) | Model outcome (y) | What "uses the input" looks like |
|---|---|---|---|
| **PolyBench** | max outcome price (market consensus, from order book) | stated confidence | confidence tracks consensus monotonically along the diagonal |
| **FutureX** | reachable retrieval tier (None / Wiki / DDG / Live / Auth) | accuracy | accuracy climbs the search-tier ladder |
| **CTF-Dojo** | challenge category (crypto / rev / web / misc / forensics / pwn) | category-specific pass rate | pass rate rises uniformly without category B regressing when A's tools are added |

The shape of the failure also unifies. On every benchmark the single-agent class collapses the (x, y) relation: confidence becomes a flat ~0.80 across all consensus values, accuracy is bounded by a single fixed retrieval tier, per-category pass rates regress when adjacent rules are added. The single growing prompt cannot maintain a *function* from task statistic to behaviour — it commits to one behaviour and applies it everywhere.

**Practical consequence for figure design.** Every $\Levo$-evidence figure in §2 must answer one yes/no question per panel: *"does the y-axis statistic depend on the x-axis statistic?"* If yes, the harness specialises; if no, the harness ignores the input. We do not plot performance over evolver cycles, we do not plot saturation curves, we do not plot prompt length. We plot $y(x)$ where $x$ is task-intrinsic.

---

## 2. The three stair-step tables

### 2.1 PolyBench — bottleneck: reading market consensus to calibrate confidence

The task-intrinsic statistic is the **max outcome price** $p_{\max}\in[0.5, 1.0]$ — the order-book's running consensus on which outcome will resolve. It is observable from the input alone; the agent never has to guess it. The model outcome we measure is **stated confidence** $c\in[0.5, 1.0]$ on traded rows (with liquidity $\geq \$1\text{K}$ to drop the illiquid regime where the right action is SKIP regardless).

**Figure.** `analysis/L_evo/output/polybench_kde_final.{pdf,png}` — three panels:
- (a) 2D KDE of $(p_{\max}, c)$ for the **single-agent class** (A-Evolve, GEPA-lite, Continual Harness, SkillOS, MH-lite).
- (b) Same for the **multi-agent class** (structured\_evo, navigation).
- (c) Conditional mean confidence $\mathbb{E}[c \mid p_{\max}]$ for both classes, with 95\% CI bands.

**The shape.**

| consensus band $p_{\max}$ | single-agent $\bar{c}$ | multi-agent $\bar{c}$ |
|---|---|---|
| $<0.7$ (genuinely uncertain) | **0.80** (over-confident, decoupled) | **0.70** (calibrated to consensus) |
| $>0.95$ (decided) | 0.92 | 0.94 |
| traded volume $n$ | 4{,}173 | 5{,}189 |

The 2D density makes the failure mode visually obvious: single-agent collapses to a single tight peak at the obviously-decided corner $(p_{\max}\!\approx\!1, c\!\approx\!0.95)$ and emits ~0.80 confidence almost everywhere else; multi-agent's density follows the diagonal $y=x$ across the full consensus range. The conditional curve confirms it numerically — single-agent's $\bar{c}(p_{\max})$ is essentially flat at 0.8 below $p_{\max}=0.9$; multi-agent's climbs monotonically.

**What this proves.** The benchmark's input contains a calibration signal (market consensus). The multi-agent harness reads it and emits confidence that depends on the input. The single-agent harness ignores it and emits one default confidence regardless of input. A class that cannot maintain $c$ as a *function* of $p_{\max}$ pays $\Levo > 0$.

**Source.** Generated by `analysis/L_evo/scripts/polybench_kde_final.py` from `results/polybench_*/results.jsonl` and the market features in `data/polymarket_analysis.db`.

### 2.2 FutureX — bottleneck: reading the question to acquire the right retrieval tier

The task-intrinsic statistic is the **retrieval tier required to ground the answer** — a property of the question itself: when did the resolving event happen, what platform indexes it, what authentication is needed to query that platform. The model outcome is **accuracy on that question's resolution**.

The mapping from required-tier to achieved-accuracy is the cleanest stair-step in our data:

| Required retrieval tier (task-intrinsic) | Achieved accuracy (model outcome) |
|---|---|
| None (parametric knowledge sufficient) | 34% |
| Wikipedia revision API | 36% |
| DuckDuckGo + htmldate temporal filter | 50% |
| Live unrestricted search | 57% |
| Authenticated APIs (Google Serper + Jina) | 70%+ |

**The shape.** Each row is a different question subpopulation requiring a different retrieval tier; the same harness scores 34–70% depending on which subpopulation it is given. A 36pp range tied entirely to whether the harness can match retrieval to the question.

**Decoupling failure.** The single-agent class plateaus at the live-search tier (~57%) regardless of how many cycles it runs, because the evolver cannot autonomously acquire authenticated API credentials — the capability gap is external to the prompt. Chinese-platform retrieval (Maoyan, Douban, Weibo) sits beyond even authenticated English APIs (~13% on L3 ranking tasks even for leaderboard winners), confirming the bottleneck is *which retrieval tier the question demands*, not how the agent reasons over the retrieved text.

**Source.** `evaluations/analysis_futurex/{leaderboard_comparison.md, l3_l4_performance_progression.md, evolver_api_exploration.md}`.

### 2.3 CTF-Dojo — bottleneck: reading challenge category to load the matching toolkit

The task-intrinsic statistic is the **challenge category** — declared in the task metadata, observable from the input alone. The model outcome is **per-category pass rate**.

| Category | Tasks | Baseline pass | + Category-specific toolkit | Δ |
|---|---|---|---|---|
| Crypto | 80 | 51% | 59% | $+8$ (Caesar/XOR templates, frequency analysis) |
| Reversing | 80 | 45% | 51% | $+6$ (`strings`/`objdump` workflow, XOR-loop reversal) |
| Web | 12 | 67% | 75% | $+8$ (GitHub-first source-checking) |
| Misc | 23 | 43% | 61% | $+18$ (encoding-detection, multi-layer recovery) |
| Forensics | 14 | 71% | 64% | $-7$ (interference: stego rules hurt simple parsing) |
| Pwn | 48 | 4% | 4% | flat (container-timeout binding constraint) |

**The shape — and the interference signature.** Each category has its own capability requirement; gains are unlocked only when the category-matching tool is added. The single-agent harness, forced to merge all toolkits into one growing prompt, exhibits the failure mode predicted by the framing in §1.5: it cannot maintain pass-rate as a *function* of category. Adding stego rules to help one category causes forensics to regress by 7pp; pwn is uniformly unreachable not because the input is hard to read but because the physical container timeout binds.

**Critical caveat.** 87% of CTF-Dojo failures are infrastructure false-negatives from a PyInstaller `flagCheck` binary that cannot execute on Alpine musl. Adjusted true reasoning-failure rate is ~3%. Must acknowledge.

**Source.** `evaluations/analysis_ctf_dojo/{report.md §4.2, infrastructure_failures.md}`.

---

## 3. The figure / table

A single subsection in §4.2 with **three small tables stacked or arranged side-by-side**. No curves. No new computation. All numbers come from already-completed runs.

**Caption.** "Each benchmark has a measurable, benchmark-specific capability requirement. PolyBench performance is gated by *confidence calibration* (under-confidence costs 99.9%-correct trades). FutureX performance is gated by *search-API access* (36pp range across retrieval tiers). CTF-Dojo performance is gated by *per-category specialised toolkits*, with cross-category interference visible as the forensics regression. These requirements diverge across benchmarks but all share one property: meeting them requires the harness to specialise in a direction the evolver class must support, instantiating $\Levo > 0$."

---

## 4. Instrumentation

| Table | New computation needed | Cost |
|---|---|---|
| PolyBench stair-step | None — already in `analysis_poly/report.md` | 0 |
| FutureX stair-step | None — already in `analysis_futurex/leaderboard_comparison.md` | 0 |
| CTF-Dojo stair-step | None — already in `analysis_ctf_dojo/report.md` | 0 |

**Total cost: zero new runs, zero new LLM calls.** All three tables are extracts from existing analysis folders.

---

## 5. Why this is sufficient evidence for $\Levo$

The regret decomposition defines $\Levo(\Phi) = \mathbb{E}_{x_t}[V(\Hist, x_t) - V(C^*_\Phi(x_t), x_t)]$. To prove $\Levo > 0$ we need the deployed harness's utility to be bounded below the history-conditional ceiling for *some* set of tasks.

The three stair-step tables establish exactly this:

- On PolyBench, $V(C^*_\Phi(x_t), x_t)$ is bounded by the harness's coverage-calibration ability. A class whose evolver cannot raise coverage from 31.5% to 90% pays $\sim 90pp$ of CWR.
- On FutureX, $V(C^*_\Phi(x_t), x_t)$ is bounded by the harness's reachable search APIs. A class whose evolver cannot acquire authenticated APIs pays $\sim 20pp$ of accuracy.
- On CTF-Dojo, $V(C^*_\Phi(x_t), x_t)$ is bounded by the harness's per-category toolkit completeness. A class whose evolver cannot maintain disjoint toolkits without interference pays category-specific regressions.

Each capability requirement is measurable, benchmark-specific, and bounded away from zero. Therefore $\Levo(\Phi) > 0$ on every benchmark for any class $\Phi$ that does not meet that benchmark's specific capability bar.

This is the existence-proof formulation: we are not measuring how big $\Levo$ is, we are showing it is non-zero by construction of the capability bottleneck.

---

## 6. Discarded designs

**Discarded — generic five-FM LLM-pathology atlas.** Earlier draft proposed a 7-panel atlas of generic LLM failure modes (context-window pressure, edit dilution, hallucinated references, internal contradictions, absence of verification). Rejected because the three benchmarks stress *different* capability axes; a generic-FM overlay treats them identically and obscures the real story.

**Discarded — compute-saturation sweep.** Earlier draft proposed running A-Evolve at $1\times, 2\times, 4\times, 8\times, 16\times$ on CTF-Dojo. Rejected because (a) cost was ~31× a default run; (b) phenomenological ("performance plateaus") rather than mechanistic; (c) attackable as "tuning"; (d) CTF-Dojo's 87% infrastructure-false-negative rate suppresses the saturation signal.

**Discarded — cross-benchmark 3×2 mechanism grid.** Earlier draft used per-cycle pathology trajectories across all three benchmarks. Strong but over-engineered: required ~21 LLM-judge calls (PolyBench contradiction count) plus log re-analysis. The stair-step tables prove the same thing with zero new computation.

**Why the stair-step version wins.** The capability requirement is the actual content of $\Levo$ in the regret formulation. Saturation curves and pathology atlases are secondary indicators. The stair-step tables are the *primary* evidence: they directly measure the capability bottleneck the framework predicts.

---

## 7. Section placement and budget

**§4.2 subsection.** `\subsection{Empirical evidence for the barriers}`. Three small tables (or a single combined figure showing the three stair-steps), one paragraph of analysis. ~half a page.

A second §4.2 subsection covers $\Ladapt$ (TBD).

Total target for §4.2: one page combined.

---

## 8. $\Ladapt$ barrier design

### 8.1 Goal

From the regret decomposition,
$$
\Ladapt(\varphi) = \mathbb{E}_{x_t}\!\left[V(C^*_\Phi(x_t), x_t) - V(\varphi(\Hist_t), x_t)\right]
$$
is the gap between (a) the *per-task class-optimum* — the harness inside class $\Phi$ that would best handle task $x_t$ if we could pick it after observing $x_t$ — and (b) the harness $\varphi(\Hist_t)$ that an actually-deployed evolver commits to **before** seeing $x_t$.

**Crucial scoping.** The class $\Phi$ for $\Ladapt$ analysis is the **multi-agent (navigation) class**: a class that *can* branch and route by task statistic, so $\Levo$ does not bound it. The $\Ladapt$ barrier therefore concerns the **state of the router at time $t$** — does it have the right entry loaded for the task that just arrived?

The single-agent class is irrelevant to the $\Ladapt$ analysis: it already fails $\Levo$ (its $y(x)$ function is constant in the task statistic), and a class that does not specialise has no router state to drift. Mixing it in confuses the two barriers.

### 8.2 Evidence philosophy (extends §1.5): same $x$, same $y$, ask whether the deployed router has the entry yet

$\Levo$ asks the question of §1.5: *"Does $y$ depend on $x$?"* — is the model-outcome function $y(x)$ non-constant in the task statistic?

$\Ladapt$ asks the **complementary** question on the navigation-only run: *"At time $t$, does the deployed router $\varphi(\Hist_t)$ have an entry that handles tasks with statistic $x$?"* The router accumulates entries throughout the stream; at any given $t$ it is incomplete. A task arriving before its category's routing entry has been added is handled by a generic fallback; the same task arriving after is handled by the specialised entry. Same task statistic, different deployed harness, different outcome.

**Visual signature.** Pick a task-intrinsic categorical statistic (PolyBench: market category from `events.tags`; FutureX: required retrieval tier; CTF-Dojo: challenge category). Plot pass rate per category, split by stream segment. If pass rate within a category jumps when its routing entry lands, the deployed harness is unstable as a function of the task statistic — $\Ladapt > 0$ even within the multi-agent class.

### 8.3 PolyBench instantiation (built; cleanest evidence)

**Data sources.**
- `results/polybench_navigation/results.jsonl` — 5{,}075 trades with `evo_cycle` and `task_id` per row.
- `results/polybench_navigation/evolved_workspace/memory/lessons.jsonl` — 56 routing entries, each tagged with the batch at which it was added.
- `data/polymarket_analysis.db` `events.tags` — categorical labels per market.

**Mapping the routing-entry stream.** Reading `lessons.jsonl` and grepping for category keywords, the first batch at which each category receives a dedicated routing entry:

| Category | First rule arrival batch |
|---|---|
| Crypto | 0 |
| Sports | 2 |
| Politics | 2 |
| Elections | 10 |
| Economy | 27 |
| Culture | 44 |

Categories arrive at the router at drastically different stream positions. **Culture's first dedicated rule lands at batch 44 of 51 — for cycles 1–43, Culture tasks were handled by a generic fallback.**

**Per-(category, stream-third) pass rate** within the navigation run:

| Category | Early (1–17) | Mid (18–34) | Late (35–51) | Δ (late − early) |
|---|---|---|---|---|
| **Finance** | 59\% (n=27) | 80\% (n=46) | 82\% (n=11) | $+23$ |
| **Crypto** | 85\% (n=454) | 91\% (n=103) | 92\% (n=13) | $+7$ |
| Politics | 91\% | 94\% | 91\% | $0$ |
| **Sports** | 79\% (n=789) | 65\% (n=1{,}269) | 76\% (n=1{,}354) | $-14$ mid (interference) |
| Economy | 91\% | 82\% | 85\% | $-6$ |
| Culture | 90\% | 98\% | 91\% | wobble around batch-44 rule arrival |

**The shape.**
- **Finance ($+23$pp)** is the canonical $\Ladapt$ signature: same task statistic, +23pp pass rate as the router accumulates the relevant order-book/last-known-price entries.
- **Sports ($-14$pp mid-stream)** is the cross-category-interference signature *within* the routing class: adding sub-rules for new Sports sub-types (BTTS, CBB, dominant-team override) at later batches degrades pass rate on earlier-handled Sports patterns until the sub-rule space stabilises.

**Conclusion.** Even on the multi-agent navigation class — a class that *can* route by category — the deployed harness $\varphi(\Hist_t)$ at time $t$ is incomplete. The same task statistic produces different outcomes depending on where the task fell in the stream. That residual variance, conditional on category, is exactly the $\Ladapt$ gap.

**Figure.** `analysis/L_adapt/output/polybench_nav_routing_drift.{pdf,png}` — built by `analysis/L_adapt/scripts/polybench_nav_routing_drift.py`.

### 8.4 FutureX instantiation (planned)

Same logic: navigation-class run only. x = required retrieval tier (None / Wiki / DDG / Live / Auth) per question — task-intrinsic. y = pass rate. Split by stream segment.

Hypothesis: at fixed required-tier "Live search", pass rate climbs across stream segments as the router accumulates DuckDuckGo-retry, htmldate-temporal-filter, and sport-specific search-wrapper entries. The lowest-tier (parametric) and highest-tier (auth APIs) bins should be flat (always-fail and always-succeed respectively).

**Cost.** Inspect `results/futurex_navigation/evolved_workspace/memory/lessons.jsonl` (or equivalent), tag each cycle with which retrieval-tool entries had been added, plot pass rate per tier per stream segment. ~30 minutes of code.

### 8.5 CTF-Dojo instantiation (planned)

Same logic: x = challenge category (crypto / rev / web / misc / forensics / pwn) — task-intrinsic. y = per-category pass rate. Split by stream segment.

Hypothesis: within forensics, pass rate decays mid-to-late as stego-rule entries accumulate but the router fails to disambiguate stego-needed vs. parse-only forensics tasks. Crypto and rev should be flat or climb (their toolkit additions do not interfere with each other).

**Cost.** Same recipe: read `results/ctf_dojo_navigation/evolved_workspace/memory/lessons.jsonl`, tag cycle ranges, compute per-(category, segment) pass rate. ~30 minutes of code.

### 8.6 Why this is sufficient evidence for $\Ladapt$

The regret decomposition defines $\Ladapt$ as the variance between class-optimum and deployed harness *at fixed task*. Stream-segment drift at fixed task statistic is the directly observable form of that variance: within the multi-agent class, tasks within the same category are equivalent up to noise, so stream-segment differences in their model outcome must come from differences in $\varphi(\Hist_t)$ — the deployed router state. That is exactly the gap $C^*_\Phi(x_t) \to \varphi(\Hist_t)$.

**Why it must be the multi-agent run.** A class that fails $\Levo$ has no $y(x)$ to drift — the function is constant in $x$, so any per-segment variance reflects $\Levo$ failure modes (over-prescription, contradiction accumulation, prompt bloat) rather than $\Ladapt$ commitment-before-seeing. Restricting $\Ladapt$ analysis to the navigation class isolates the commitment-timing dimension.

**What this is not.** This evidence does not measure the size of $\Ladapt$ (that would require evaluating multiple harness snapshots against a held-out task set, which is expensive). It only proves $\Ladapt > 0$ — the deployed router is incomplete at any finite stream position. The framework's claim is existence, not magnitude.

### 8.7 Section placement

§4.2 subsection 2: `\subsubsection{$\Ladapt$ barrier — even routing classes commit before seeing}`. One figure (1×3 across the three benchmarks) plus one paragraph of analysis. Total §4.2 budget remains one page combined with the $\Levo$ subsection.

### 8.8 Discarded design

**Discarded — split single-agent's $(p_{\max}, c)$ curve by stream-third.** Earlier draft tried plotting the conditional-mean confidence curve from §2.1, split by stream segment, on the *single-agent* class (and by symmetry on the multi-agent class). Output: `analysis/L_adapt/output/polybench_kde_ladapt.{pdf,png}`. Rejected because (a) the single-agent class fails $\Levo$ — its $y(x)$ is essentially constant in $x$, so per-segment "drift" of a near-flat function is barely meaningful and conflates the two barriers, and (b) the multi-agent panel showed coherent per-segment improvement (better calibration as history accumulates), which reads as $\Ladapt > 0$ in a *recoverable* direction but does not isolate the commit-before-seeing signal. Both panels are kept on disk for completeness but are not the primary $\Ladapt$ evidence.
