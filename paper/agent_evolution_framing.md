# Agent Evolution as Whole-System Domain-Fitting — Framing Notes

> Working synthesis of our discussion. Goal: settle the *high-level insight* that
> should anchor the next paper(s), before hunting concrete gaps. Distilled to the
> sharp claims only; supporting literature in §6.

---

## 0. The one-line thesis (three equivalent statements)

| Flavor | Statement |
|---|---|
| **Constructive** | Agent evolution = **online fitting of a whole problem-solving *system* to a *domain***. Model-fitting lifted one level: from *parameters → dataset → task* to *system → observation-stream → domain*. The fitted artifact is a **domain expert**. |
| **Operational** | It automates the half of science gradient descent **cannot** do: **structure search** (revise the apparatus), not just **parameter fitting** (tune the dials of a frozen apparatus). |
| **Analytical** | "Domain fit" is measured as **regret against an oracle-fitted system**, which decomposes into **system-level approximation + estimation + irreducible** error (= our \(L_\text{evo}+L_\text{adapt}+\) HITL). |

**Why it is not "just optimize the LLM":** see §4 (competence vs. capital). **Why it is not AutoML/meta-learning:** the search space is **non-differentiable, open-ended, heterogeneous, and includes interfaces to a world the agent does not own**; the optimizer is **LLM-prior structure search**, not gradient/Bayesian search over a fixed parametrization; the scope is a **drifting domain stream**, not a static dataset.

---

## 1. The five primitives of a learning problem (minimal complete set)

A learning problem = *(fit **to** what / fit **what** / **toward** what / via what **evidence** / by what **procedure**)*. Agent evolution instantiates all five — classical ML froze four of them.

| # | Primitive | Classical ML | Agent evolution | Why it is distinct |
|---|---|---|---|---|
| 1 | **World** \( \mathcal{D}\) | static dataset stands in for it | non-stationary reality, **partly unowned** | never observed directly; the gap *system→world* is where overfitting & HITL live |
| 2 | **System / hypothesis** \(\mathcal{H}\) | point in fixed parametric space | **organism**: reasoner + tools + skills + memory + protocols + (opt.) weights **+ world-interfaces** | open-ended, structured, includes things it doesn't own |
| 3 | **Objective / task** \(\mathcal{L}\) | one labeled task, fixed | external **or self-generated** (self-play, auto-curriculum); terminal **or** proxy/intrinsic | trend: objective becomes **endogenous** |
| 4 | **Observation** \(\mathcal{S}\) (≠ data) | exogenous, passive, i.i.d., curated | **endogenous**: action-conditioned, costly, **bounded by the current system** | *what you can observe is a function of the system you have* (= FutureX source-acquisition) |
| 5 | **Optimizer / search** \(\mathcal{A}\) | fixed (SGD) — implicit | the **agent-as-structure-searcher** (LLM prior) + gradient/RL | the paradigm's defining organ; must be first-class, not implicit |

**Closure:** exactly five primitives. Everything else is a **relation** among them, not a sixth component:

| Apparent "component" | Actually a relation |
|---|---|
| Generalization | relation(observation, world): does fit to \(\mathcal{S}\) transfer to \(\mathcal{D}\)? |
| Overfitting (our Fig. c1, `news_from_future.md`) | system capacity ≫ observation's coverage of the world |
| Regularization (nemo token-cap, kill-list) | constraint on system relative to observation |
| Credit assignment / exploration | relations among optimizer, observation, objective |
| **Cost / budget** | cross-cutting **price** on observing, optimizing, maintaining organs; objective = cumulative utility − cost |

**Caveat (and it's the frontier, not noise):** the five are separable *roles*, not always separate *objects*. Two blurrings define the most advanced systems:
- reward ⊂ observation (pure RL),
- **optimizer ⊂ system** (self-referential self-improvement) and **objective ⊂ search** (self-generated tasks) → the *direction of travel*.

---

## 2. The boundary that moved (the historical trend)

ML's history = the machine swallowing one human-fixed component after another, while the *scope of the fit* widens.

| Era | Structure searched by | Machine fits | Scope |
|---|---|---|---|
| Classical ML | human (features + model) | parameters | one task |
| Deep learning | human (architecture + loss) | features + params | one task |
| AutoML / NAS | machine (architecture) | params | one task, **differentiable** |
| **Agent evolution** | **machine (whole system + world-interfaces)** | **system + opt. weights** | **a domain (task stream)** |

This is the **Bitter Lesson at the system level**: searched systems beat hand-designed systems given compute. The LLM is the enabler — it supplies **priors over a non-differentiable, open-ended structural space** where random search and gradients both fail.

**Endogenization view (the synthesis):** *a self-evolving agent is a learning system in which every component except the world has become endogenous and co-adapts. The one irreducibly exogenous component — the fixed point of endogenization — is reality.* Your three live-components (system, observation, task) are **exactly the three being endogenized now**; world is the one that never can be → that is precisely **where the residual error and the human (HITL) belong.**

---

## 3. The Newton test (why "data-driven" is too weak)

Newton → quantum is **not** curve-fitting; nobody regressed Schrödinger from blackbody data. A human **posited new structure**; anomalous **observation selected** it. Science = **hypothesis generation (structure search) + empirical selection**.

| | Classical ML/DL | Agent evolution |
|---|---|---|
| structure search | **human** | **machine** |
| empirical selection | machine (param fit) | machine (run-and-keep) |
| the frozen part | the apparatus/theory | — (apparatus is revisable) |

⇒ Agent evolution automates the creative half of the scientific loop — structure revision under observation — which gradient descent **structurally cannot** reach.

---

## 4. Why not just bake everything into the LLM? (competence vs. capital)

Push to the extreme (free, lossless training): what *still* must live outside the weights? Two arguments survive any model; the rest are practical (cost, forgetting, API access).

| Argument | Survives perfect-model limit? | Content |
|---|---|---|
| **Boundary** (control theory) | **Yes — always** | a DB / API / market / human is **not the agent**; a forward pass cannot *be* persistent external state or concurrent orchestration. The agent can build an *interface* + *internal model*, never internalize the thing. |
| **Depreciation** (lead with this in 2026) | **Yes — always** | weight-baked competence is **model-specific → orphaned on every base-model upgrade**; externalized capital is **model-agnostic → compounds across generations**. Reasoner = *rented, depreciating*; capital = *owned, compounding*. |
| Compression destroys specificity | weakens in perfect limit | a generalizer used as an exact/fresh store is lossy (hallucinates the value) and interference-prone; retrieval wins for anything exact or non-stationary. |

**The trichotomy — three fates of experience** (the routing the LLM-only view collapses):

| Fate | Goes where | When | Optimizer | Prototype |
|---|---|---|---|---|
| **Consolidate** | weights (**competence**) | general · stable · approx-OK | gradient / **RLVR** | reasoning ability |
| **Externalize** | organism (**capital**) | specific-but-reusable · exact · structural · external · fresh | **agentic edit** | database, orchestration protocol, tool, skill |
| **Keep / discard** | context / scratchpad | instance-specific · one-shot | — | today's prices |

Routing variable: **generality × stability × (1−need-exactness) × (1−need-separability)** → high ⇒ weights, low ⇒ externalize. The **routing decision itself is non-differentiable** (discrete choice over heterogeneous stores) — gradient descent can't make it; the agent-optimizer can. *Managing this flux is the irreducibly "agent-evolution" operation.*

Analogies (both legitimate): **complementary learning systems** (cortex=slow/general/consolidated vs. hippocampus=fast/specific/episodic; sleep replays only the stable-general part) and the **memory hierarchy** (you don't bake disk or today's data into CPU microcode).

---

## 5. Our \(L_\text{evo}+L_\text{adapt}\) decomposition = statistical learning, lifted to systems

The framing earns its keep by **re-deriving the EMNLP theorem as a corollary** (evidence it's the right generalization, not a metaphor):

| Statistical learning | Our decomposition | Reading |
|---|---|---|
| **Approximation error** — best hypothesis in class \(\mathcal{H}\) (property of class, not effort) | \(L_\text{evo}(\Phi)\) — best system the evolver **class** can build | "single-agent editor can't build multi-file infra" = "model class too small"; fix = richer class, **not** more cycles |
| **Estimation error** — committing to one fitted hypothesis before the test point | \(L_\text{adapt}(\varphi)\) — committing to one system before seeing \(x_t\) | oracle conditions on \(x_t\); deployed evolver can't → solve-time routing |
| **Irreducible / out-of-sample** — truth not a function of the sample | **HITL axis** — domain signal absent from \(\mathcal{H}_t\) (resource boundary) | close it only by **acquiring more world** |

Two consequences:
- **System-level overfitting is real** ⇒ *all* of generalization theory transfers (capacity, bias–variance, temporal cross-validation, complexity penalties). Fig. c1 is the canonical instance; nemo's discipline is the canonical (heuristic) fix.
- **"Fit" → "track":** a domain is a *non-stationary distribution* (D3); we never converge, we **track a drifting target** ⇒ the verb is **online system identification**, not batch fitting. (Precondition: the domain must have **reusable structure / capital to accumulate** — true for PolyBench/CTF/FutureX recurring regimes; false for a stream of unrelated one-offs.)

---

## 6. Literature, read through the lens "what is frozen?"

Survey sweep: 106 collected → 95 unique → 20 deep-read + adversarially verified (19 confirmed). **Every method = block-coordinate descent on a coupled organism, with most blocks bolted down.**

| Cluster | Representatives | Evolved organs | **Frozen organs** | Optimizer |
|---|---|---|---|---|
| Prompt-only | GEPA, DSPy, OPRO, TextGrad, EvoPrompt, MIPRO, Promptbreeder, ProTeGi | prompt | **weights, env**, tools, topology, memory | frozen-LLM / textual-grad / evolutionary |
| Skill-only | Voyager, ExpeL, AWM, SSO, GITM, JARVIS-1 | skill lib (+retrieval) | **weights, env**, prompt, tools, topology | frozen-LLM-proposal |
| Tool-only | Toolformer, CREATOR, CRAFT, TroVE, LATM, DynaSaur, **Alita**, ToolMaker | tools/code | **weights** (mostly), env, topology | frozen-LLM + execution-verify |
| Memory-only | MemGPT, Reflexion, A-MEM | memory | **weights, env**, rest | frozen-LLM-proposal |
| Topology search | ADAS, AFlow, GPTSwarm, AgentSquare, MaAS, ScoreFlow, G-Designer, FlowReasoner, MASS | wiring (+node prompts) | **weights, env**, operator pool | frozen-LLM **or trained controller** |
| Self-modifying code | **DGM**, Gödel Agent, STOP, **AlphaEvolve**, FunSearch, ELM | code (→ many organs at once) | **weights, env** | frozen-LLM + evolutionary archive |
| Weights / RL | STaR, **DeepSeek-R1**, RAGEN, Absolute Zero | weights (+self-gen data) | **entire scaffold + env** | RL / SFT-distillation |
| Env co-evolution | POET, OMNI-EPIC | environment + weights | scaffold; the env *encoding* | evolutionary + per-task RL |
| **Harness-holistic (our lineage)** | **A-Evolve, Meta-Harness, Continual Harness** | prompt+skill+tool+infra+memory+topology | **weights, env** | frozen-LLM-proposal |

**Three findings the field's own "what do you evolve?" taxonomies hide:**
1. **Gains live in cross-organ coupling terms** single-organ methods structurally can't reach. Optimizing one organ to exhaustion against frozen others doesn't converge — it **overfits into the frozen structure** (mechanistic explanation of Fig. c1).
2. **Two organs are frozen almost everywhere — the exact two a human expert invests in most:** **weights** (internalized skill) and the **resource boundary** (ability to *go acquire* a feed/API/instrument/collaborator). No deployed system does the expert's defining move: *"I don't have what I need — let me go get it."* ⇒ **HITL is not a bolt-on axis; it is the manual operator for the one organ everyone freezes.**
3. **The field bifurcated into two camps that never touch**, and the split is an artifact (closed APIs), not a principle:

| | Camp A (scaffold) | Camp B (weights) |
|---|---|---|
| evolves | prompt/skill/tool/memory/topology | weights |
| freezes | **weights** | **entire scaffold + env** |
| driven by | **experience** (trajectories, text/exec feedback) | **scalar reward** |
| optimizer | **frozen LLM** | **RL / gradient** |

Our "experience **and** reward" splits exactly along this seam. **Almost no system uses both to evolve both** — but a real expert improves toolkit *and* trained intuition together, and better tools change which skills are worth internalizing.

---

## 7. Where our two systems sit (and why they look in tension but aren't)

| System | Camp | Organs evolved | Frozen | Note |
|---|---|---|---|---|
| **EMNLP Adaptive Auto-Harness** | A (broadest tier) | prompt+skill+tool+infra+memory+**branch-topology** | weights, env | near the **ceiling of scaffold-only** evolution; HITL patches the frozen resource organ |
| **nemo_scientist** | **A↔B crossing** | scaffold (`research_prompt.md`, data pipeline, reasoners) **+ LoRA weights** | base model, env | rare **whole-organism** evolver; **existence proof** the camps unify — uses experience *and* reward, but narrowly (1 domain, SFT not RL, env fixed) |

nemo also instantiates §4 in miniature: `research_prompt.md → DISCOVERY.md` is a (toy) **consolidation ladder**; token-cap + kill-list + best-step = (heuristic) **system-level regularization**.

---

## 8. Where RL becomes load-bearing (not a competing paradigm)

RL is the optimizer for the organs **structure-search-by-text cannot reach**, at four distinct levels (don't conflate):

| Level | RL does what | Maps to |
|---|---|---|
| **L1 — inner** | produce **weights** from verifiable reward (RLVR); agent designs the reward/data/curriculum | fate-1 consolidation; CTF/PolyBench are verifiable |
| **L2 — optimizer** | train the **evolver policy** (state=organism+history, action=which organ to edit, reward=downstream **stream** utility) | our **D1** stated as an MDP; only topology cluster does this, only for wiring |
| **L3 — router** | solve-time branch/skill selection as a **contextual bandit** | our **\(L_\text{adapt}\)**; frozen-LLM router *fails on FutureX* |
| **L4 — flux/budget controller** | allocate budget across **{observe more / edit system / consolidate to weights / just solve}**; exploration + credit assignment under non-stationarity | the §1 cost-relation; "evolution-scaling" knob, but **learned** |

Unifying line: **"agent evolution on a stream" is already a hierarchical, non-stationary MDP; the field solves it with frozen-LLM heuristics instead of learning.** Frontier = **LLM-prior proposal × RL value/credit/exploration.**

---

## 9. Open territories the framework exposes (candidate directions)

| Territory | One-line | RL level | Notes |
|---|---|---|---|
| **Flux controller** | learned policy routing each unit of experience to consolidate / externalize / discard; manage promotion–demotion across the competence↔capital boundary | L4 (+L1) | the empty diagonal; uniquely enabled by owning **both** codebases |
| **Autonomous acquisition** | make *extending the resource boundary* (new sources/APIs/tools) a first-class **learned action** — the autonomous version of HITL | L3/L4 | directly attacks FutureX bottleneck where routing fails |
| **Camp A↔B unification** | one organism evolving scaffold **and** weights from experience **and** reward | L1+L2 | nemo is the narrow existence proof; generalize |
| **System-level regularization** | port nemo's bounded-state/kill-list/temporal-CV + **git rollback** into the general framework; flatten Fig. c1 peak-then-decline | — | turns our headline failure into a solved contribution |
| **Online L_evo/L_adapt estimation** | turn the analytical losses into online estimators a controller acts on | L4 | closes our own stated limitation; fits UnifiedEngine Controller |

---

## 10. Two open framing choices (decide before writing)

1. **Headline:** *"fit a system to a domain → expert"* (constructive/position energy) **vs.** *"regret = system-level approximation + estimation + irreducible"* (theorem energy). Same idea; one **sells a paradigm**, one **proves a result**.
2. **Endogenization edges** (optimizer⊂system, objective⊂search): **suppress as messy edges** or **embrace as the frontier**? They define the most advanced self-evolving agents — likely the direction of travel.
3. **Two stages → one or two loops?** "utilize past experience" (slow consolidation) + "adapt online" (fast tracking) as **two timescales of one optimizer** (wake/sleep / Dyna) **vs.** **two optimizers** (RL + frozen-LLM). Decides: unified controller vs. two-loop architecture.

---

*Anchors already in the paper:* the regret decomposition (§5) and the HITL third axis (§1, §5) are the formal seeds; "experience ≠ data," "competence vs. capital," "endogenization," and the "frozen-organ" literature critique are the new connective tissue to develop.
