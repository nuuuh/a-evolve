# Proposal — Endogenous Action Spaces: Self-Evolving Agents that Grow and Internalize Their Own Capabilities

> Working proposal. Companion to `EMNLP26/agent_evolution_framing.md` (the high-level
> framing); this file is the concrete project: motivation → thesis → loop → contributions
> → experiments. Scope is deliberately bounded.

---

## 1. Intuition (the human truth)

Human capability never scaled by growing bigger brains — it scaled by **building tools and then internalizing their use**. A novice multiplies on paper; an expert does it in their head; eventually we build the calculator and offload arithmetic entirely. Capability is first **manufactured** (construct new instruments that expand what we can do) and then **automated** (repeated use becomes reflex). The set of actions available to an agent — its **action space** — is not fixed; it is *endogenous*, grown over a lifetime and over history, from stone tools to rockets.

---

## 2. The gap

LLM agents are improved two ways; **neither grows the action space**:

| Approach | Improves | But assumes given |
|---|---|---|
| **RL / RLVR** | a policy **over a fixed action space** | the action space (tool API) **and** the reward/grounding |
| **Agentic self-evolution** | skills/tools/memory (**frozen weights**) | the environment interface **and** the verifier |

Both silently assume someone already told the agent **(a) what it can do** and **(b) how it is graded**. Real deployment violates both at once: drop an agent onto a Linux server, or into a new domain, with only a natural-language goal — it knows neither its action space nor its grounding.

**Two overlooked consequences:**
- *Conceptual.* Treating the action space as exogenous is a category error. **Competence *is* an enlarged, internalized action space.** A richer policy over a fixed action space cannot express what the action space does not contain → a hard capability ceiling no policy optimization can cross.
- *Practical.* The **cold-start problem** — *discover your own action space and your own grounding in an unknown environment* — is essentially unstudied, because every self-improving system hand-wires it away (a Python executor, a Minecraft API, a labeled reward).

---

## 3. Thesis

Recast self-improvement as **endogenous action-space construction and internalization**. One loop, driven only by a natural-language goal in an unknown environment:

> **discover** latent affordances → **build** new artifacts that enlarge the action space → **refine** the artifacts it owns → **internalize** the current action space into weights via RL.

Two design commitments (these are what distinguish it from prior work):

1. **The action space compounds; weights are recompiled.** Across rounds, external artifacts (the action space) grow monotonically and carry forward; weights are **re-internalized from the *initial* checkpoint each round** (expert-iteration, not iterative fine-tuning). Separates durable, inspectable **capital** (the action space) from a recomputed parametric **reflection** of it (competence) → avoids catastrophic forgetting, gives clean per-round credit assignment.
2. **RL internalizes the *use* of the action space, not the artifacts.** Step 4 is RLVR whose reward is the discovered grounded score; it bakes into weights *when to invoke / compose / sequence* the grown action space (the selection-and-composition policy), while artifacts stay external. The two-substrate boundary never collapses.

**Grounding = the real, external, unfakeable signal that decides "did it help?"** It is the reward of the loop. We use environments where grounding is **crisp but hidden from the agent** — known to *us* (so we can measure), unknown to *it* (so it must discover). This bridges "unknown-environment deployment" and "cleanly measurable RL."

---

## 4. The loop (fully specified)

```
BASE = initial agent (frozen LLM checkpoint θ₀)
Round N:
  reset weights → θ₀                                  # always from initial
  1. DISCOVER   : explore env → reveal latent affordances        (frozen-LLM + intrinsic signal)
  2. BUILD      : create new tools/entities → enlarge action space (frozen-LLM)
  3. REFINE     : compose / prune / improve OWNED artifacts        (frozen-LLM + grounded gate)
                  → action space  A_N   (artifacts/vocabulary; carried forward)
  4. INTERNALIZE:
       roll out solver on grounded tasks using A_N
       keep grounded-successful trajectories  D_N
       RLVR(GRPO): train θ₀ → θ_N on D_N               ← THE RL (step 4 only)
  evaluate (θ_N , A_N) on held-out downstream tasks
Round N+1: A_{N+1} builds on A_N ; weights reset to θ₀ again
```

- **Carries across rounds:** `A_N` (action space / artifacts) — grown.
- **Resets each round:** weights (always from θ₀).
- **RL location:** step 4 only — a self-contained RLVR run per round (pattern: STaR / ReST / Absolute-Zero expert-iteration, *not* continual fine-tuning).
- **Refinement constraint (step 3):** restricted to the agent's **own possessions** (its artifacts, contracts, APIs) — it may rewrite what it *owns*, only *interface* what it does not (the ownership boundary).

---

## 5. Positioning

> **Absolute Zero grows a *task curriculum* and iteratively trains *weights* over a *fixed* action space against a *hand-wired* executor. We grow the *action space itself*, re-internalize it from the initial checkpoint each round, and *discover* the grounding from a natural-language goal.**

| | Classical RL / RLVR | Agentic self-evolution | **Ours** |
|---|---|---|---|
| action space | **fixed, given** | grown (frozen weights) | **grown *and* internalized** |
| weights | trained iteratively | frozen | **recompiled from init each round** |
| env + grounding | hand-wired | hand-wired | **unknown; discovered from an NL goal** |
| what compounds | weights | artifacts | **the action space (capital); weights reflect it** |

Nearest prior art to distinguish from: **Absolute Zero** (grows tasks, trains weights, fixed action space, given executor); **Voyager** (grows skills, frozen weights, given Minecraft API); **AgentEvolver / FlowReasoner** (RL over agent systems, but given env + per-query/agent-training, not a compounding discovered action space).

---

## 6. Contributions

1. **Reframing: self-improvement = endogenous action-space growth-and-internalization.** Competence is an enlarged, internalized action space. Formalize the two substrates (external action space = compounding capital; weights = recompiled reflection) and place classical RL (fixed action space) and self-evolution (frozen weights) as the two degenerate corners.
2. **A domain-agnostic loop (discover→build→refine→internalize)** with two principled commitments: **always-from-initial** internalization (action space is the sole compounding substrate → stability + clean attribution) and **RL internalizes *use*, not content** (artifact/weight boundary intact). RL's role is precise: the **converter** turning a grown action space into fluent parametric behavior.
3. **The cold-start grounding-discovery formulation.** Given only an NL goal, the agent must discover *both* its action space and its grounding in an unknown environment; an NL-goal → verifiable-score decomposition routes to the domain's native, unfakeable signal. Isolates a practical bottleneck every prior system assumes away.
4. **Empirical validation** across **ARC-AGI**, **Polymarket** (resolved order-book archive), and a **verifiable market simulator**, with the decisive ablation triple (§7). Headline result: *an agent that discovers and grows its own action space, then internalizes it via RL, bootstraps from zero environment knowledge to competence — approaching the ceiling of an agent handed its action space and grounding upfront.*

---

## 7. Experimental design

**Environments (crisp, unfakeable grounding; hidden from the agent):**

| Env | NL goal | Native grounding (the hidden verifier) | Action-space story |
|---|---|---|---|
| **ARC-AGI** | "solve the puzzle" | inferred rule must reproduce the example pairs (+ match held-out output) | rich **build/refine**: grow a library of grid-transformation primitives |
| **Polymarket** (archive) | "forecast accurately" | market **resolution** (offline, already known → free calibrated grounding) | **discover** sources, **build** connectors, **refine** a calibration playbook |
| **Verifiable simulator** | "trade profitably" | realized **PnL** | discover + build + refine under a clean reward |

**The decisive ablation triple** (de-circularizes "competence grew because the action space grew"):

| Condition | Holds fixed | Isolates |
|---|---|---|
| `(θ_N , A_N)` | — | full system |
| `(θ_N , A_1)` | RL-internalize, but with the **initial** action space | **does action-space growth help?** |
| `(θ_0 , A_N)` | grown action space, **no** internalization | **does internalization help?** |

Compounding = `(θ_N,A_N)` exceeds both. Plus: **transfer** to held-out downstream tasks; **action-space growth** curve over rounds (measured independently — count of *distinct reliable* artifacts, composition reach).

**RL stack to implement (Goal: gain RL depth):** GRPO/RLVR for step 4; rollout collection + grounded keep-filter; (optional, later) intrinsic-motivation signal for step-1 discovery.

---

## 8. Honesty caveats (bake in, or reviewers will)

- **Measure action-space growth independently of task performance** (distinct reliable artifacts, composition reach) — else the central claim is circular. The §7 triple is the de-circularizer.
- **Scope grounding to *routing*, not *synthesis*.** In these three domains the NL goal maps to an *already-present* verifier; the agent **discovers and connects to** native grounding — it does **not** invent grounding where none exists (the dropped-CDC trap). State this explicitly.
- **"Always-from-initial" means weights don't compound — the action space does.** Frame RL as the *converter* of action-space growth into parametric fluency; the novelty is the **endogenous, growing action space**, not the RL algorithm.
- **Step 4's value depends on steps 1–3 actually enlarging the action space.** The interesting dynamics live in discover/build/refine; if they stall, internalization just re-bakes the same repertoire.

---

## 9. Staging

- **v1 (core):** one environment (simulator or Polymarket — cheap, crisp, offline grounding); steps 1–3 (frozen-LLM + grounded gate) + step-4 RLVR; show the ablation triple + bootstrap-from-zero result.
- **v2 (generality):** plug in a second environment (ARC) behind the same interface → "domain-agnostic, same cold-start method adapts."

---

## 10. One-line thesis

> **The agent never evolves its weights iteratively; it evolves its *action space* (discover → build → refine), and each round RL re-internalizes the current action space into a fresh copy of the base model. Capability compounds in the externalized, inspectable action space; weights are a recompiled reflection of it. RL's job is internalization — converting a grown action space into fluent parametric behavior — not iterative self-modification.**
