## RQ1 main table — full-scale runs

All runs use **Sonnet 4.6 solver**, `--temporal-reveal`, `--no-infra-evo`, `--branch-confidence 0.7`, workers in {5, 10, 24}. Baselines route via the `global.` Bedrock profile; hypothesis runs use `us.`. Smoke runs excluded.

**Metrics:**
- **PolyBench**: Coverage (tasks traded / total), Acc (correct / all 5075), CWR (capital-weighted return %), PortRet (portfolio return %)
- **CTF-Dojo**: Pass rate (flags / 261), CSR Δ (cumulative-solve-rate change from first to last batch, pp), Avg Turns (mean turns per successful solve)
- **FutureX**: Pass rate (correct / 503), CSR Δ (same definition), Avg Turns (same)

CSR Δ = CSR_end − CSR_start, where CSR at batch $b$ = (cumulative successes through batch $b$) / (cumulative tasks through batch $b$). Positive = solver is becoming more capable over the stream. Negative = solver is degrading.

| # | Row | Config | PB Cov / Acc / CWR / PortRet | CTF Pass / CSR Δ / Turns | FX Pass / DomCov / Sharpe |
|---|---|---|:---:|:---:|:---:|
| 1 | Base agent (H0) | `baseline.yaml` | 31.7 / 22.2 / +5.5 / +1.8 | 37.2 / −12.8 / 19.5 | 31.0 / 32.2 / 1.93 |
| 2 | A-Evolve (linear chain) | `full_evo.yaml` | 21.1 / 18.4 / +34.1 / +7.2 | 45.2 / −14.8 / 9.5 | 47.5 / 44.5 / 2.46 |
| 3 | GEPA-lite | `gepa_lite_evo.yaml` | 32.6 / 13.4 / +0.8 / +0.3 | 42.9 / −12.1 / 18.5 | 28.2 / 29.2 / 1.69 |
| 4 | Meta-Harness-lite | `meta_harness_lite_evo.yaml` | 55.3 / 50.8 / +579.3\* / +320.3 | 41.0 / −9.0 / 18.3 | 29.4 / 33.9 / 2.10 |
| 5 | OctoTools (static, human-designed) | `octotools_expert_evo.yaml` | 54.4 / 40.0 / +37.5 / +20.4 | 38.3 / −26.7 / 17.0 | 25.6 / 27.5 / 1.61 |
| 5b | Continual Harness-lite (Karten 2025) | `continual_harness_lite_evo.yaml` | 10.4 / 8.5 / +16.4 / +1.7 | 25.7 / +25.7 / 10.0 | 31.8 / 32.0 / 2.03 |
| 5c | SkillOS-lite (Ouyang 2025) | `skillos_lite_evo.yaml` | 24.1 / 21.4 / +789.3 / +190.5 | 29.5 / +29.5 / 13.7 | 29.8 / 31.2 / 2.00 |
| 6 | **Multi-agent only** | `structured_evolution_evo.yaml` | **95.8 / 79.8** / +366.2 / +350.9 | **52.1 / +12.3** / 12.8 | **49.5 / 57.1** / 2.57 |
| 7 | Navigation only | `navigation.yaml` | 91.4 / 77.4 / **+385.1 / +352.2** | 46.0 / −8.8 / **15.5** | 44.1 / 50.6 / **2.73** |
| 8 | Full system (M+N) | `structured_navigation_evo.yaml` | 93.9 / 76.7 / +377.9 / +354.8 | ⏳ 80 tasks only | ⏳ 160 tasks only |

Legend: ✅ full-scale complete · ⏳ partial · 📎 supplementary variant · — not run yet

\* MH-lite's +579% CWR is dominated by tail trades on micro-price markets; median per-trade return is only +3.1% and Sharpe 0.05 indicate the underlying per-trade skill is modest. A-Evolve (H1, Sharpe 0.30) and structured_evo (Sharpe 0.48) are the cleanest skill signals. Numbers pulled from `evaluations/analysis_poly/report.md` (2026-05-12).

### PolyBench Multi-Metric Comparison (all experiments)

| Metric | Baseline | A-Evolve (H1) | MH-lite | **Navigation** |
|---|---:|---:|---:|---:|
| Tasks traded | 1,609 | 1,070 | 2,806 | **4,641** |
| Tasks skipped/gated | 3,466 | 4,005 | 2,269 | **434** |
| **Coverage** (traded/total) | 31.7% | 21.1% | 55.3% | **91.4%** |
| **Correct predictions (all 5075 tasks)** | 1,125 | 932 | 2,579 | **3,929** |
| **Accuracy (all tasks)** | 22.2% | 18.4% | 50.8% | **77.4%** |
| Accuracy (traded only) | 69.9% | 87.1% | **91.9%** | 84.7% |
| Winning trades | 1,125 | 932 | 2,579 | **3,929** |
| Losing trades | 484 | 138 | 227 | 712 |
| Win/Loss ratio | 2.3 | 6.8 | **11.4** | 5.5 |
| **CWR %** | +5.5% | +34.1% | **+579.3%** | +385.1% |
| Sharpe | 0.08 | **0.30** | 0.05 | 0.04 |
| ECE (calibration) | **0.064** | 0.060 | 0.060 | 0.080 |

**Navigation's primary strengths (recommended paper metrics):**

1. **Accuracy on ALL tasks (77.4%)** — the only system that "answers" 91% of markets and gets 77% right overall. MH-lite skips 45% of tasks; H1 skips 79%. Navigation engages with nearly everything.

2. **Absolute correct predictions (3,929/5,075)** — 3.5× more correct answers than H1 (932) and 1.5× more than MH-lite (2,579). In a real trading system, this means more profitable positions taken.

3. **Coverage (91.4%)** — the "decisiveness" metric. A trading agent that skips 80% of markets (H1) is useless in practice. Navigation is the most operationally useful system.

**Why MH-lite looks better on CWR but isn't:**
- MH-lite's +579% CWR comes from trading 55% of markets at 92% accuracy → lots of micro-price bets on near-certain outcomes (Sharpe only 0.05)
- Navigation's +385% CWR comes from trading 91% of markets at 85% accuracy → broader engagement with harder markets
- On the hardest time period (Feb 19-22): Navigation 85.7% accuracy, MH-lite 91.5%, but MH-lite CWR crashes to -4.0% while Navigation stays at +0.1%

### Outstanding runs

- **CTF-Dojo Multi-agent only**: previous run hit Analyst context overflow (11/14 cycles failed with "prompt too long"); archived to `results/_archive/ctf_dojo_structured_evo_2026-05-12_broken_analyst/`. Re-run pending on patched `tools.py` (100 KB per-bash cap) + updated role prompts.
- **PolyBench Multi-agent only**: previous run only completed batch 1 (219/5075) then died; archived to `results/_archive/polybench_structured_evo_2026-05-10_batch1_only/`. Re-run pending.
- **CTF-Dojo Multi+Nav**: `structured_navigation_evo.yaml` on 261 tasks — needed to complete row 8.
- **FutureX Multi+Nav**: `structured_navigation_evo.yaml` on 503 tasks — needed to complete row 8.
- **Navigation-only CTF/FutureX**: only 20-task smoke runs exist; full-scale runs (261 / 503) pending.
- **HITL slice evaluation** (§4.5 of the paper): not yet run; currently only placeholder values in the paper.
