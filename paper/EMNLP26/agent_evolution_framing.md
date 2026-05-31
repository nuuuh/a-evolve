# Agent Evolution as Whole-System Domain-Fitting

**Thesis.** Agent evolution = **online fitting of a whole problem-solving *system* to a *domain***. Model-fitting lifted one level: *parameters→dataset→task* becomes *system→observation-stream→domain*. The fitted artifact is a **domain expert**.

It automates the half of science gradient descent can't: **structure search** (revise the apparatus), not just **parameter fitting** (tune a frozen apparatus's dials). Newton→quantum wasn't curve-fitting — a human posited new *structure*; observation *selected* it. Classical ML: human searches structure, machine fits params. Agent evolution: **machine does both.**

---

### 1. Five primitives of a learning problem

| # | Primitive | Classical ML | Agent evolution |
|---|---|---|---|
| 1 | **World** | static dataset stands in for it | non-stationary reality, **partly unowned** |
| 2 | **System** | point in fixed param space | organism: reasoner+tools+skills+memory+protocols+(weights)+**world-interfaces** |
| 3 | **Objective** | one fixed labeled task | external **or self-generated** |
| 4 | **Observation** | passive, i.i.d., curated | **endogenous: action-conditioned, costly, bounded by current system** |
| 5 | **Optimizer** | fixed SGD (implicit) | **agent-as-structure-searcher** (LLM prior) + gradient/RL |

- **Observation ≠ data** is the load-bearing refinement: *what you can observe is a function of the system you have*. Makes the fit **active**, not batch.
- **Closure:** exactly 5 primitives. Everything else is a *relation*: generalization=(obs,world); overfitting=capacity≫obs-coverage; cost=price on the other four.
- **Frontier = the blurrings:** optimizer⊂system (self-referential) and objective⊂search (self-generated) define the most advanced agents.

**Endogenization (the synthesis):** ML history = the machine swallowing one human-fixed component after another (params→features→architecture→**system→observation→objective→optimizer**). *Everything is becoming endogenous except the **world** — the fixed point. The residual gap (system→world) is exactly where overfitting and human-in-the-loop live.*

---

### 2. Why not just bake everything into the LLM? (the motivation — must be fundamental, not practical)

**Test:** grant a *perfect trainer* (unlimited data/compute, one-shot gradient steps). What does an artifact still do that weights cannot? Practical reasons (cost, API access, no weight access) fail this test → would make artifacts mere scaffolding-until-models-improve. Only **representational-property** reasons survive — and they do, because they are about *update dynamics & structure*, not storage location.

> **THE MOTIVATION.** Agent evolution exists because expertise requires **two representational substrates that no single update rule can serve**: a **slow, statistical, distributed** one (weights, via gradient) and a **fast, exact, one-shot, revisable, compositional, inspectable** one (artifacts, via edit). This division is **forced by the structure of knowledge** — the same reason brains have both a **cortex and a hippocampus** (complementary learning systems) — **not by the limitations of today's models**. Therefore a complete learning agent must optimize **both substrates from one experience signal**, which is precisely the **unified-reward problem**.

**Why no single substrate suffices** (these survive the perfect trainer; ranked by depth):

| Property | Weights (gradient) | Artifacts (edit) | Fundamental? |
|---|---|---|---|
| **update rule** | statistical, slow, many-sample | **one-shot, exact, instant** | ✓✓ *deepest* |
| **interference** | new learning corrupts old (forgetting) | **local, non-interfering** | ✓✓ |
| **revisability** | clean unlearning ~unsolved | **delete/edit one entry** (→ non-stationarity) | ✓✓ |
| **composition** | monolithic | **combinatorial — N skills compose freely** (→ systematicity) | ✓✓ |
| **retrieval / inspection** | approximate, opaque (hallucinates the value) | **exact, readable, addressable** | ✓ |
| **auditability / locality** | delocalized | provenance + one-bad-file (→ enables credit assignment) | ✓ |

**The killer move:** "just build a perfect *neural* memory (one-shot, exact, non-interfering, inspectable)" doesn't absorb artifacts — it **reinvents them inside the net**. To absorb artifacts you must give weights the *properties* of artifacts → you've built a symbolic, addressable, edit-updated substrate, i.e. the artifact. **The boundary can move; it cannot collapse.** Two more that are about the *world*, so trivially irreducible: **statelessness** (a forward pass can't hold persistent mutable cross-task state) and **externality** (a DB/API/human is not the agent — the agent builds an *interface*, which is an artifact because the interfaced thing is outside it).

*Demoted — true but contingent:* **depreciation** (weight-baked competence is model-specific → orphaned each base-model upgrade; capital is model-agnostic → compounds). Real and rhetorically strong, but *practical* — it makes the case **urgent now**, not **fundamental**. The closer, not the opener.

**Three fates of experience** (the routing the LLM-only view collapses):

| Fate | Store | When | Optimizer |
|---|---|---|---|
| **Consolidate** | weights (**competence**) | general·stable·approx-OK | gradient/**RLVR** |
| **Externalize** | organism (**capital**) | specific·exact·structural·external·fresh·revisable·composable | **agentic edit** |
| **Discard** | context | one-shot | — |

The **routing decision is non-differentiable** — gradient descent can't make it; the agent-optimizer can. *Managing this flux is the irreducibly "agent-evolution" operation* → **two irreducible substrates ⟹ one reward, two credit-assignment operators** (the unified-reward program).

---

### 3. Domain-fitting = statistical learning, lifted to systems

"Domain fit" is measured as **regret against an oracle-fitted system**, which decomposes exactly like statistical learning:

| Statistical learning | System-level analogue | Reading |
|---|---|---|
| approximation error (class too small) | **evolver-class capability gap** | a weak optimizer can't *construct* the missing organ → need a richer optimizer class, **not** more cycles |
| estimation error (commit before test pt) | **single-system commitment gap** | one system is fitted before the task is seen → solve-time adaptation/routing |
| irreducible (truth ∉ sample) | **resource-boundary gap** | signal absent from observation → close only by **acquiring more world** (human-in-the-loop / acquisition) |

⇒ **System-level overfitting is real** ⇒ all generalization theory transfers (capacity, temporal CV, complexity penalty). "Fit"→"**track**" a drifting non-stationary target. Precondition: the domain must have **reusable structure**.

---

### 4. The field, read through "what is frozen?"

Sweep: 106 papers → 20 deep-read + verified. **Every method = block-coordinate descent on a coupled organism, most blocks bolted down.**

| Cluster | Evolves | **Frozen** |
|---|---|---|
| Prompt (GEPA, DSPy, OPRO, TextGrad) | prompt | **weights, env**, +rest |
| Skill (Voyager, ExpeL, AWM) | skills | **weights, env** |
| Tool (Toolformer, CRAFT, Alita) | tools | **weights** (mostly), env |
| Topology (ADAS, AFlow, GPTSwarm, MaAS) | wiring | **weights, env** |
| Self-mod code (DGM, AlphaEvolve, STOP) | code→many organs | **weights, env** |
| Weights/RL (R1, RAGEN, Absolute Zero) | weights | **whole scaffold + env** |
| Harness-holistic (A-Evolve, Meta-Harness) | scaffold (broad) | **weights, env** |

**Three findings the field's own "what do you evolve?" taxonomies hide:**
1. **Gains live in cross-organ coupling** single-organ methods can't reach — tuning one organ against frozen others doesn't converge, it **overfits into the frozen structure**.
2. **Two organs are frozen everywhere = the two an expert invests in most: weights + the resource boundary.** No deployed system does *"I don't have what I need — let me go get it."* ⇒ **human-in-the-loop is the manual operator for the one organ everyone freezes.**
3. **Two camps never touch** (artifact of closed APIs, not principle): **A** = evolve scaffold from *experience* via frozen-LLM, freeze weights; **B** = evolve weights from *reward* via RL, freeze scaffold. **Almost no one evolves both with both** — yet a real expert improves toolkit *and* trained intuition together, and better tools change which skills are worth internalizing.

---

### 5. Where RL is load-bearing (the organs text-search can't reach)

| Level | RL does | Why it's the right tool |
|---|---|---|
| **L1 inner** | weights from verifiable reward (RLVR) | only principled way to move the weight organ from reward |
| **L2 optimizer** | train the **evolver policy** (action = which organ to edit, reward = downstream stream utility) | each evolution decision commits all downstream tasks = a sequential decision under delayed reward |
| **L3 router** | solve-time system/skill selection = contextual bandit | frozen-LLM routers degrade under shift |
| **L4 flux/budget** | allocate {observe / edit system / consolidate to weights / solve}; exploration + credit assignment under non-stationarity | the cost relation; nobody makes this allocation a learned policy |

**"Agent evolution on a stream" is already a hierarchical non-stationary MDP; the field solves it with frozen-LLM heuristics instead of learning.** Frontier = **LLM-prior proposal × RL value/credit/exploration.**

---

### 6. Open territories the framework exposes

| Territory | One-line | RL |
|---|---|---|
| **Flux controller** | learned policy routing each unit of experience → consolidate / externalize / discard | L4+L1 — the empty diagonal |
| **Autonomous acquisition** | make *extending the resource boundary* a first-class learned action (autonomous HITL) | L3/L4 |
| **Camp A↔B unification** | one organism evolving scaffold **and** weights from experience **and** reward | L1+L2 |
| **System-level regularization** | capacity control + temporal cross-validation + edit rollback to fight system-level overfitting | — |

**Three framing choices before writing:** (1) headline = *"fit system→domain→expert"* (paradigm) vs. *"regret = approx + estimation + irreducible"* (theorem); (2) endogenization blurrings — suppress or embrace as the frontier; (3) two stages — one optimizer at two timescales (wake/sleep) vs. two optimizers (RL + LLM).

---

### 7. What unlocked LLMs vs. what agent evolution has now

| # | Ingredient | LLMs have | Agent evolution has *now* | Grade |
|---|---|---|---|---|
| 1 | **General substrate** | Transformer — one canonical, expressive architecture that **scales predictably** (scaling laws) | the LLM as reasoner; but **no canonical representation of the agent-system space** (code is Turing-complete but unsearchable), no agent-evolution scaling law | **B–** (borrowed) |
| 2 | **Observations** | internet of text — abundant, cheap, **pre-existing, static, parallel, self-labeling** | trajectories — **scarce, expensive, must-be-generated, action-conditioned, serial, system-bounded** | **D** |
| 3 | **Optimizer** | **single algorithm**, SGD/Adam — mature, scalable, convergence theory, "just works"; cleanly *separate* from the model | a **heterogeneous optimizer-*system*** that *composes* SGD/Adam (weights) + RL/RLVR (policy) + evolutionary search (AlphaEvolve, FunSearch, DGM archive) + bandit/MCTS (AFlow) + **LLM-proposal** (the semantic-prior operator) + verification gates — *no unified theory, no single scaling knob, hand-wired per system* | **C** |
| 4 | **Objective** | NTP — **dense, self-supervised, universal**, induces general capability + clean SFT/RLHF stage | sparse per-domain task reward; **no dense self-supervised "NTP for agency"** | **D** |
| 5 | **Domain** | closed world — **finite vocabulary, fully observable** | open world — unbounded/growing action+tool vocabulary, partial obs, non-stationary, costly, irreversible | **mismatch** |

*Scorecard ≈ 1.5 / 5. The substrate is borrowed from the prior paradigm; the optimizer is **rich but theory-free** (a portfolio of heterogeneous optimizers with no unified scaling knob — the LLM is demoted to the variation operator of an outer search); the three ingredients that actually did the work in LLMs — **self-labeling observations (#2), a dense self-supervised objective (#4), a closed world (#5)** — are the ones still missing. Bottleneck is the **observation×objective economics**, not the model or the scaffold.*

---

### 8. What objective & optimizer for the agent system? (NTP vs. RL is the wrong cut)

**Sparsity ≠ RL.** NTP vs. RL differ on *label-vs-reward*, *given-vs-self-generated data*, *single-vs-delayed credit* — not density. On those axes system-optimization is RL-**shaped** (self-generated rollouts, delayed compounding credit, no free label). But two refinements flip the naive "sparse → RL":

- **Much sparsity is self-inflicted.** A trajectory is information-*dense*; current optimizers crush it to a scalar reward, then call the signal sparse. Fix: **process-supervision, not outcome-supervision** (read the trace — cf. Meta-Harness's "raw traces are the load-bearing ingredient").
- **The human-researcher decomposition:** generate rollouts → **search for the diagnostic failure** → **diagnose root cause** → edit (cheap) → validate. ~90% of effort is *find + diagnose*, not the edit. Humans succeed under sparse signal **not** by reward-climbing but by **priors + dense-trace reading + information-seeking** — i.e. the *opposite* of model-free RL, which is **worst** in the sparse + expensive + huge-action-space regime.

**Resolution — RL's frame, not RL's algorithm; objective = information, not reward:** NTP doesn't vanish, it survives as **density-manufacturing** (predict/compress experience → a *world model* for cheap counterfactual diagnosis / Dyna), not as the score. Organ-dependent: **RLVR (gradient RL) is right for the weight organ** (consolidate competence, verifiable domain); model-free reward-RL is wrong for evolving the **system/optimizer**.

> **THE CLEAN LINE.** The system-optimizer's job is **not to maximize reward but to seek the diagnostic observation** — it is **active experimental design under delayed credit**. RL is the right **frame** (exploration + credit assignment), **information-gain** is the right **objective**, and the **dense process trace + LLM prior** are what make the sparse search tractable. Naive sparse-reward RL is exactly the wrong tool; the human researcher succeeds by being a **model-based, prior-rich information-seeker**, and that is what we must automate.

**Two open holes in current schemes** (all are greedy *propose-edit → held-out-accept* = coordinate ascent + ERM gate): **temporal credit assignment** (which past edit caused today's gain/overfit — the RL-shaped hole; why Fig-c1 decline goes undetected) and **portfolio routing** (which organ-specific sub-optimizer handles each change). Trust-region step-size is understood (textual learning rate; too big → collapse, e.g. ACE 18k→122 tokens); the held-out acceptance gate is the load-bearing primitive that makes it *learning*, not *drift*.

---

### 9. Agent evolution as vocabulary-learning, and the ownership spectrum

**Vocabulary asymmetry (not a parallel).** The token-vocab↔action-vocab analogy is wrong as a *parallel* — an LLM's vocabulary is **complete + composable + fixed** (vocab size is *not* its binding constraint; composition is). The force is an **asymmetry**: an agent's action vocabulary is **incomplete, sometimes non-composable (at the world boundary), but growable**. So **agent evolution = vocabulary expansion** — and that *is* the representational-ceiling half of L_evo (expanding the agent class Φ raises the ceiling C\*_Φ).

**Abstraction = handle vs. body.** A tool/skill is **one word to *select*, an arbitrarily large passage to *execute*** — selection cost stays O(1) while expressive power grows O(N). Expertise = growing the execution-power : selection-cost ratio. This decoupling also re-explains **skill-shadowing collapse**: adding words doesn't raise execution cost, it raises **selection** cost (more handles to disambiguate) → L_evo has *two opposed halves*: **representational ceiling** ("can express", raised by adding vocabulary) vs. **realization gap** ("can select/run", *inflated* by adding vocabulary). Naive expansion moves both → the evolver's real job is **structured expansion** (raise the first without inflating the second).

**Latent vs. known vocabulary (the binding constraint on a Linux box).** A computer + internet = near-infinite *latent* vocabulary (every installable tool × every composition) that the agent **does not know it has**. An LLM's vocab is *declared* (known a priori, uniform cost); an agent's is **latent + self-opaque** — discovered by acting (`which`, `man`, `pip list`, docs). ⇒ most failures are **vocabulary-unawareness, not incapability**; the evolver's job is **discovery (latent→known) + coining (gaps) + promotion (reliable composition→named word)**, and the skill library is the agent's *self-model of its own vocabulary* (which must stay searchable). On a Turing-complete box, raw capability is nearly unbounded → **L_evo relocates from "can't do X" to "doesn't know it can / can't find the word in time."**

**Selection vs. execution = two substrates.** The LLM *emits the word*; the **system executes the passage** (interpreter/OS/tool). Selection and execution are **different substrates** (unlike an LLM, where they're the same forward pass) — which is *why the unit of analysis must be the whole system*: one organism-behavior = LLM-selection ⊕ system-execution.

**Software vs. data (don't conflate).** Software/tools = **verbs** (reusable across domains; humanity's pre-built vocabulary the agent *inherits*, so evolution is more *discover/assemble* than *build-from-scratch*). Data/DB = **nouns/referents + persistent memory** (the specific world + §2's statelessness organ). Different update rules: *build/discover* verbs vs. *accumulate/curate* nouns.

> **THE BOUNDARY.** There is **no clean agent/environment boundary**. There is a **spectrum of ownership**, and agent evolution is the act of **pulling slices of the environment across it — internalizing the world**.

The boundary is where **ownership / controllability / determinism** ends, not where the agent ends. Three zones: **agent core** (LLM + weights + artifacts, fully owned) → **owned execution / internalized env** (interpreter, filesystem, local cache/DB, the sandbox — *the agent's **body***, deterministic, provisioned) → **outer environment** (live API, market, robot physics, human — not owned, has its own dynamics). A fired skill is a **trajectory through ownership space** (its body crosses the boundary mid-execution). So **the Linux box is the agent's *body*, not the environment**; the evolved expert is largely **a well-furnished body** (installed tools + cached data + written skills) — concrete and inspectable. This *completes* §2's externality argument: §2's "external by definition" holds for the **outer** env; the **owned/internalized** env is also-not-the-LLM yet *is* the agent. **Acquisition/HITL = moving the inner boundary outward.** New knob: the evolver must **manage** that boundary — internalize what's *stable* (cache it → fast, owned), keep a *live interface* to what *drifts*; **over-internalization = building a confident model of a stale world** (= `news_from_future` overfitting, restated).
