# Theoretical Analysis: Agentic Evolution and Navigation

## Definitions and Setup

**Configuration space.** Let `Π` be the space of system configurations. Each `π ∈ Π` has true performance `V(π) = E_{t∼D}[Y(π,t)]` where `Y(π,t) ∈ {0,1}` is the binary outcome on task `t`.

**Evaluation model.** Evaluating configuration `π` on `n` tasks produces:
- Outcome observations: `Y₁,...,Yₙ`, i.i.d. Bernoulli with `E[Yᵢ] = V(π)`, `Var(Yᵢ) = V(π)(1-V(π)) ≤ 1/4`
- Diagnostic observations: `D₁,...,Dₙ ∈ ℝᵐ`, i.i.d. with `E[Dᵢ] = d(π)`, `Cov(Dᵢ) = Σ_D`

**Parent-child structure.** A modification `a ∈ A` applied to parent `π₀` produces child `π' = a(π₀)`. Define:

```
Δ_V = V(π') − V(π₀)                       (outcome gap)
Δ_d = d(π') − d(π₀) ∈ ℝᵐ                 (diagnostic gap)
```

---

## Theorem 1: Information-Theoretic Advantage of Process Feedback

**Problem.** Estimate `Δ_V` to determine whether a modification improves the system. We compare the statistical efficiency of outcome-only versus process-enriched estimation.

**Definition 1 (Diagnostic coupling).** The diagnostic vector `D` is `(κ, Σ_ξ)`-coupled to the outcome `Y` if there exists `κ ∈ ℝᵐ` such that:

```
Δ_d = κ · Δ_V + ξ
```

where `κ = (κ₁,...,κₘ)ᵀ` is the **amplification vector** (`κⱼ` measures how much diagnostic component `j` responds per unit outcome change) and `ξ` is zero-mean noise independent of `Δ_V` with `Cov(ξ) = Σ_ξ`.

This is a linear measurement model: the diagnostics are noisy linear observations of the quantity of interest `Δ_V`, with different components having different sensitivities `κⱼ`.

**Theorem 1 (Fisher information gain).** Under the coupled model, the Fisher information for `Δ_V` from a single paired evaluation is:

**(a) Outcome only:**

```
I_out(Δ_V) = 1 / σ²_Y
```

where `σ²_Y = Var(Yᵢ(π') − Yᵢ(π₀)) ≤ 1/2`.

**(b) Process-enriched (outcome + diagnostics):**

```
I_proc(Δ_V) = 1/σ²_Y + κᵀΣ_ξ⁻¹κ
```

**(c) The information gain ratio is:**

```
I_proc / I_out = 1 + σ²_Y · κᵀΣ_ξ⁻¹κ ≥ 1
```

with equality iff `κ = 0` (diagnostics carry no information about `Δ_V`).

**Proof.** Consider the joint observation from a single paired evaluation: `X = (Z, W)` where `Z = Y'ᵢ − Yᵢ` (paired outcome) and `W = D'ᵢ − Dᵢ` (paired diagnostic). The parameter of interest is `θ = Δ_V`.

Under the model:

```
Z = θ + ε_Y,     ε_Y ~ (0, σ²_Y)
W = κθ + ε_D,    ε_D ~ (0, Σ_ξ)
```

where `ε_Y` and `ε_D` are independent conditional on `θ`.

The log-likelihood of `(Z, W)` is:

```
ℓ(θ) = −(Z−θ)²/(2σ²_Y) − (W−κθ)ᵀΣ_ξ⁻¹(W−κθ)/2 + const
```

The score function:

```
∂ℓ/∂θ = (Z−θ)/σ²_Y + κᵀΣ_ξ⁻¹(W−κθ)
```

The Fisher information:

```
I(θ) = −E[∂²ℓ/∂θ²] = 1/σ²_Y + κᵀΣ_ξ⁻¹κ
```

For outcome only (`W` discarded): `I_out = 1/σ²_Y`.

The second term `κᵀΣ_ξ⁻¹κ` is a positive semi-definite quadratic form, so `I_proc ≥ I_out` with equality iff `κ = 0`. When `Σ_ξ = diag(σ²_{ξ,1},...,σ²_{ξ,m})`:

```
κᵀΣ_ξ⁻¹κ = Σⱼ κⱼ²/σ²_{ξ,j}
```

Each diagnostic component contributes `κⱼ²/σ²_{ξ,j}` — an additive, independent information increment. ∎

**Corollary 1 (Sample complexity reduction).** By the Cramér-Rao bound, the minimum-variance unbiased estimator of `Δ_V` under `n` evaluations has variance `≥ 1/(n · I(θ))`. To achieve estimation precision `ε` at confidence `1−α`:

```
n_out  ≥ z²_α / (ε² · I_out)   = z²_α · σ²_Y / ε²
n_proc ≥ z²_α / (ε² · I_proc)  = z²_α / (ε² · (1/σ²_Y + κᵀΣ_ξ⁻¹κ))
```

The reduction factor:

```
n_proc / n_out = I_out / I_proc = 1 / (1 + σ²_Y · κᵀΣ_ξ⁻¹κ)
```

**Corollary 2 (Optimal combined estimator).** The maximum likelihood estimator achieving the Cramér-Rao bound is:

```
Δ̂_V^{MLE} = (Z̄/σ²_Y + κᵀΣ_ξ⁻¹W̄) / (1/σ²_Y + κᵀΣ_ξ⁻¹κ)
```

This is a precision-weighted average of the outcome estimator and the diagnostic estimators, where each is weighted by its Fisher information contribution. Its variance is:

```
Var(Δ̂_V^{MLE}) = 1 / (n · (1/σ²_Y + κᵀΣ_ξ⁻¹κ))
```

**Proof.** Under the linear model, `Δ̂_V^{MLE}` is the generalized least squares estimator:

```
Δ̂_V^{GLS} = (κᵀΣ_ξ⁻¹κ + 1/σ²_Y)⁻¹ · (κᵀΣ_ξ⁻¹W̄ + Z̄/σ²_Y)
```

By the Gauss-Markov theorem for the linear model `(Z̄, W̄)ᵀ = (1, κ)ᵀθ + noise`, this is BLUE (best linear unbiased estimator) and achieves the Cramér-Rao bound. ∎

**Corollary 3 (Unbounded information gain).** The total information from `m` diagnostic components with amplification ratios `κ₁,...,κₘ` is additive:

```
I_proc = I_out + Σⱼ κⱼ²/σ²_{ξ,j}
```

The information gain from process feedback is **unbounded** as `κⱼ → ∞` or `m → ∞` — fundamentally different from outcome-only evaluation, which is bounded by `I_out ≤ 4` (since `σ²_Y ≥ 1/4` for Bernoulli outcomes).

**Remark (SWE-bench instantiation).** From our data, for the premature submission rate diagnostic:
- `κ_j ≈ 10` (20% diagnostic change per 2% outcome change)
- `σ²_Y ≈ 0.25`, `σ²_{ξ,j} ≈ 0.16`
- `κⱼ²/σ²_{ξ,j} = 100/0.16 = 625`
- `I_proc/I_out = 1 + 0.25 · 625 ≈ 157`

A single diagnostic component provides ~157× more information than the outcome alone.

---

## Theorem 2: Submartingale Property of the Active Configuration

**Setting.** Evolution proceeds for `K` steps on the main branch. At step `k`:

1. Propose child `π'_k` with true improvement `Δₖ = V(π'_k) − V(π^(k−1))`
2. Evaluate on `n` paired tasks: `Z̄ₖ = (1/n)Σᵢ(Yᵢ(π'_k) − Yᵢ(π^(k−1)))`
3. Accept iff `Z̄ₖ ≥ −ε`; otherwise fallback to parent

Active configuration: `π^(k) = π'_k` if accepted, `π^(k−1)` otherwise.

**Definition 2 (Proposal quality).** The proposal distribution at step `k` has parameters:

```
p = P(Δₖ ≥ 0)                    (probability of non-degrading proposal)
μ₊ = E[Δₖ | Δₖ ≥ 0]              (expected gain from good proposals)
μ₋ = E[|Δₖ| | Δₖ < 0]            (expected loss from bad proposals)
```

**Definition 3 (Acceptance function).** For the test `Z̄ₖ ≥ −ε`:

```
α(Δ) = P(Z̄ ≥ −ε | true gap = Δ)
```

**Lemma 2 (False acceptance bound).** For paired differences `Zᵢ ∈ [−1,1]`, by Hoeffding's inequality:

```
α(Δ) ≤ exp(−n(Δ+ε)² / 2)     when Δ < −ε
1 − α(Δ) ≤ exp(−n(Δ+ε)² / 2) when Δ > −ε
```

*Proof.* `Z̄ = Δ + (Z̄ − Δ)` where `Z̄ − Δ` is centered with bounded increments in `[−1,1]`. When `Δ < −ε`:

```
P(Z̄ ≥ −ε) = P(Z̄ − Δ ≥ −ε − Δ)
```

Since `Δ < −ε`, we have `−ε − Δ > 0`. By Hoeffding on `n` terms each in `[−1,1]` (range 2):

```
P(Z̄ − Δ ≥ −ε − Δ) ≤ exp(−2n(−ε−Δ)²/4) = exp(−n(ε+Δ)²/2)
```

Note: `Δ < −ε` so `|ε+Δ| = |ε − |Δ|| `. When `Δ < −2ε`, `(ε+Δ)² > ε²`, giving `α(Δ) < exp(−nε²/2)`. The case `Δ > −ε` is symmetric. ∎

**Theorem 2 (Submartingale).** Let `Xₖ = V(π^(k))` be the performance of the active configuration. Define the filtration `ℱₖ = σ(Δ₁, Z̄₁,..., Δₖ, Z̄ₖ)`. Then:

```
E[Xₖ − Xₖ₋₁ | ℱₖ₋₁] ≥ p · μ₊ − (1−p) · 2ε − R(n,ε)
```

where:

```
R(n,ε) = (p · μ₊ + 1) · exp(−nε²/2)
```

In particular, `{Xₖ}` is a **submartingale** when:

```
p · μ₊ > (1−p) · 2ε + R(n,ε)                    (*)
```

**Proof.** Condition on `ℱₖ₋₁`. The increment is:

```
Xₖ − Xₖ₋₁ = Δₖ · 𝟙(Z̄ₖ ≥ −ε)
```

Partition the expectation into three regions of `Δₖ`:

**Region I: `Δₖ ≥ 0` (non-degrading proposals).** Acceptance probability `α(Δₖ) ≥ 1 − exp(−n(Δₖ+ε)²/2) ≥ 1 − exp(−nε²/2)` since `Δₖ ≥ 0`.

```
E[Δₖ · 𝟙(accept) | Δₖ ≥ 0] ≥ E[Δₖ | Δₖ ≥ 0] · (1 − exp(−nε²/2))
                              = μ₊ · (1 − exp(−nε²/2))
```

Weighted by `P(Δₖ ≥ 0) = p`:

```
Contribution I ≥ p · μ₊ · (1 − exp(−nε²/2))
```

**Region II: `−2ε ≤ Δₖ < 0` (small degradations, gray zone).** These may pass the test since `|Δₖ|` is within the detection threshold. Worst case: always accepted with `Δₖ = −2ε`.

```
|Contribution II| ≤ 2ε · P(−2ε ≤ Δₖ < 0) ≤ 2ε · (1 − p)
```

**Region III: `Δₖ < −2ε` (large degradations).** By Lemma 2, `α(Δₖ) ≤ exp(−n(ε + Δₖ)²/2) ≤ exp(−nε²/2)` (using `|Δₖ| > 2ε` so `(ε+Δₖ)² ≥ ε²` for the relevant range). Since `|Δₖ| ≤ 1`:

```
|Contribution III| ≤ 1 · exp(−nε²/2) · P(Δₖ < −2ε) ≤ exp(−nε²/2)
```

**Combining all three regions:**

```
E[Xₖ − Xₖ₋₁] ≥ p·μ₊·(1 − exp(−nε²/2)) − 2ε(1−p) − exp(−nε²/2)
              = p·μ₊ − (1−p)·2ε − (p·μ₊ + 1)·exp(−nε²/2)
              = p·μ₊ − (1−p)·2ε − R(n,ε)
```

The submartingale condition (*) follows by requiring the right-hand side to be non-negative. ∎

**Theorem 2' (Process-feedback-enhanced submartingale).** When the acceptance test uses the optimal combined estimator from Theorem 1 (with amplification gain `G = I_proc/I_out`), the effective detection power improves. The acceptance function becomes:

```
α_proc(Δ) ≤ exp(−n · G · (Δ+ε)² / 2)     when Δ < −ε
```

and the residual reduces to:

```
R_proc(n,ε) = (p·μ₊ + 1) · exp(−n · G · ε² / 2)
```

*Proof.* The combined estimator `Δ̂_V^{MLE}` has variance `1/(n · I_proc) = 1/(n · G · I_out)`. Substituting into the Hoeffding-type bound: the exponent scales with `n · I_proc` rather than `n · I_out`, giving the factor `G` improvement. ∎

**Corollary (Submartingale condition comparison).** The submartingale condition (*) becomes:

| Feedback type | Condition for `E[Xₖ − Xₖ₋₁] ≥ 0` |
|---|---|
| Outcome only | `p·μ₊ > (1−p)·2ε + (p·μ₊+1)·exp(−nε²/2)` |
| Process-enriched | `p·μ₊ > (1−p)·2ε + (p·μ₊+1)·exp(−nGε²/2)` |

With `G ≈ 157` (SWE-bench, Theorem 1 remark), the residual under process feedback is `exp(−157nε²/2)` versus `exp(−nε²/2)` — negligible even for very small `n`.

**Theorem 2'' (Concentration of cumulative improvement).** Summing over `K` steps, let `S_K = X_K − X_0 = Σₖ (Xₖ − Xₖ₋₁)`.

**(a) Expected improvement:**

```
E[S_K] ≥ K · (p·μ₊ − (1−p)·2ε − R(n,ε))
```

**(b) Concentration (Azuma-Hoeffding).** Since each increment `Xₖ − Xₖ₋₁ ∈ [−1, 1]` (bounded by the worst-case single-task flip), and `{Xₖ}` is adapted to `{ℱₖ}`:

```
P(S_K ≤ E[S_K] − t) ≤ exp(−t² / (2K))
```

**(c)** Setting `t = E[S_K]` (probability that the system is worse than it started):

```
P(V(π^(K)) < V(π^(0))) ≤ exp(−(E[S_K])² / (2K))
                        = exp(−K · (p·μ₊ − (1−p)·2ε − R)² / 2)
```

This probability decreases **exponentially in K** when the submartingale condition holds — longer evolution trajectories are **more likely** to show net improvement, not less. ∎

---

## Theorem 3: Regret Bound for Diagnostic-Guided Navigation

**Setting.** At each of `T` rounds, the navigator selects a modification `aₜ ∈ A` from `K` candidates. Each has unknown expected improvement `μₐ = E[Δ_V | a]`. Define `a* = argmax_a μₐ`, `μ* = μ_{a*}`, and `Δₐ = μ* − μₐ`.

**Instantaneous regret:** `rₜ = μ* − μ_{aₜ}`

**Cumulative regret:** `R_T = Σₜ rₜ`

**Definition 4 (Diagnostic informativeness).** The diagnostic function partitions `A` into `L` groups `A₁,...,A_L` where `|Aₗ| = kₗ` and `Σₗ kₗ = K`. At each round, diagnostics identify the group containing `a*` with probability `≥ 1−γ`:

```
P(a* ∈ A_{ℓ*}) ≥ 1 − γ
```

where `ℓ*` is the diagnostically indicated group. Define `k = max_ℓ kₗ`.

This models the diagnostic-to-action mapping from the framework: diagnostics like "high premature submission rate" narrow the relevant actions to a small group (e.g., {AddStage(verify), ModifyParam(more_turns)}) out of all possible modifications.

**Theorem 3a (Outcome-only regret, standard UCB1).** Without diagnostics, UCB1 over `K` arms achieves:

```
R_T^{out} ≤ Σ_{a≠a*} (8 ln T)/Δₐ + (1 + π²/3) · K
```

In the worst case (`Δₐ ≥ Δ_min` for all suboptimal `a`):

```
R_T^{out} ≤ 8(K−1) ln T / Δ_min + (1 + π²/3) · K = O(K ln T / Δ_min)
```

*Proof.* Standard result of Auer et al. (2002), Theorem 1. ∎

**Theorem 3b (Diagnostic-guided regret).** With `(L, γ, k)`-informative diagnostics, the following two-phase strategy achieves:

```
R_T^{diag} ≤ 8(k−1) ln T / Δ_min + γ · T · μ* + (1 + π²/3) · k
```

**Strategy:**
1. Compute diagnostics `dₜ`, identify group `A_{ℓ*}` with `|A_{ℓ*}| ≤ k`
2. Run UCB1 restricted to `A_{ℓ*}`

**Proof.** Decompose the regret by the diagnostic correctness event:

Let `E_t = {a* ∈ A_{ℓ*,t}}` be the event that diagnostics correctly identify the group at round `t`.

```
E[R_T] = Σ_t E[r_t · 𝟙(E_t)] + Σ_t E[r_t · 𝟙(E_tᶜ)]
```

**Term 1 (correct diagnostics).** Conditional on `E_t`, the optimal arm is among `k` candidates. By Auer et al. (2002) applied to the restricted arm set:

```
Σ_t E[r_t · 𝟙(E_t)] ≤ Σ_{a∈A_{ℓ*}, a≠a*} (8 ln T)/Δₐ + (1 + π²/3) · k
                      ≤ 8(k−1) ln T / Δ_min + (1 + π²/3) · k
```

**Term 2 (incorrect diagnostics).** When `E_tᶜ` occurs (`a* ∉ A_{ℓ*,t}`), the per-round regret is at most `μ*` (the best arm's value, since the worst we can do is gain 0). By Definition 4, `P(E_tᶜ) ≤ γ`:

```
Σ_t E[r_t · 𝟙(E_tᶜ)] ≤ T · γ · μ*
```

Combining both terms yields the claimed bound. ∎

**Corollary 1 (Regret reduction ratio).** Comparing Theorems 3a and 3b in the dominant term:

```
R_T^{diag} / R_T^{out} ≈ (k−1)/(K−1) + γ·T·μ*·Δ_min / (8(K−1) ln T)
```

When diagnostics are reliable (`γ ≪ 1`) and `T` is moderate:

```
R_T^{diag} / R_T^{out} → k/K
```

The regret reduction equals the action space reduction ratio.

**Theorem 3c (Lower bound).** For any algorithm using outcome-only feedback over `K` arms with gaps `Δₐ`:

```
R_T ≥ Σ_{a≠a*} (Δₐ / 8) · ln(T / (K · e))     for T ≥ K·e
```

In particular: `R_T = Ω(K ln T / Δ_max)` — no outcome-only algorithm achieves regret scaling with fewer than `K` arms.

*Proof.* By Lai & Robbins (1985), any consistent algorithm must sample each suboptimal arm `a` at least `(1 + o(1)) · ln T / KL(μₐ, μ*)` times, where `KL` is the KL divergence. For Bernoulli arms with gap `Δₐ`, `KL ≥ 2Δₐ²` (Pinsker's inequality), giving the bound.

The key structural point: outcome observations from arm `a` provide information **only about `μₐ`** — they carry no information about other arms. Every arm must be explored independently. Diagnostic observations break this barrier by providing simultaneous information about which arms are plausible, enabling `K − k` arms to be eliminated without direct evaluation. ∎

---

## Connecting the Three Results

The three theorems form a coherent argument for the agentic evolution and navigation paradigm:

**Theorem 1 → M3 (evolution signals).** Process feedback provides strictly more Fisher information per evaluation than outcome alone: `I_proc = I_out + κᵀΣ_ξ⁻¹κ ≥ I_out`. The gain is additive across diagnostic components and unbounded in principle. This formalizes why domain-specific behavioral diagnostics are essential — they amplify the signal.

**Theorem 2 → M2 (scaling with non-degradation).** The parent-fallback rule makes the active configuration a submartingale under the condition `p·μ₊ > (1−p)·2ε + R(n,ε)`. Crucially, process feedback reduces the residual `R` by factor `G = I_proc/I_out` (Theorem 2'), making the submartingale condition achievable with smaller evaluation batches. The concentration result (Theorem 2'') shows that the probability of net degradation decreases **exponentially in the number of evolution steps** — longer trajectories are safer, not riskier.

**Theorem 3 → Navigation-scaling hypothesis.** Diagnostic-guided navigation achieves `O(k ln T)` regret versus `O(K ln T)` for outcome-only navigation, where `k/K` is the action space reduction from diagnostics. The lower bound (Theorem 3c) proves this reduction is impossible without process-level information — outcome-only algorithms **must** explore all `K` arms. This formalizes the advantage of agentic navigation: the navigator uses diagnostic signals to focus search on the most promising modifications.

**Compound effect.** The three gains interact multiplicatively. Process feedback (Thm 1) amplifies the signal → this makes each evolution step more reliable (Thm 2, smaller `R`) → and makes navigation more efficient (Thm 3, smaller `k`). A system with all three properties needs fewer evaluations per step, makes better steps, and searches more efficiently — the compound effect is the theoretical foundation for the navigation-scaling hypothesis.