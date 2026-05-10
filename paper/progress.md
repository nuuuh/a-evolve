## RQ1 main table — full-run progress

All runs use **Sonnet 4.6 solver**, `--temporal-reveal`, `--no-infra-evo`, `--branch-confidence 0.7`, `--workers 5`. Per-benchmark batch / turns / timeout match `{benchmark}_hypothesis.sh` defaults.

| # | Row in RQ1 table | Config | PolyBench (5,075) | CTF-Dojo (261) | FutureX (503) |
|---|---|---|:---:|:---:|:---:|
| 1 | Base agent (no evolution) | `baseline.yaml` (H0) | ✅ 1125/5075 | ⏳ 14/23 | ✅ 156/503 |
| 2 | A-Evolve (linear chain) | `full_evo.yaml` (H1) | ✅ 932/5075 | ⏳ 9/20 | ✅ 239/503 |
| 3 | GEPA-lite (NeurIPS 2025, reflective prompt evo — prompts-only port) | `gepa_lite_evo.yaml` — run via `baselines_hypothesis.sh gepa_{poly,ctf,futurex}` | ❌ | ❌ | ❌ |
| 4 | Meta-Harness-lite (Lee et al. 2026, archive proposer, k=1) | `meta_harness_lite_evo.yaml` — run via `baselines_hypothesis.sh mh_{poly,ctf,futurex}` | ❌ | ❌ | ❌ |
| 5 | OctoTools (Lu et al., ACL 2026 oral — Stanford generalist Planner+Executor+ToolCards, static harness) | `octotools_expert_evo.yaml` — run via `baselines_hypothesis.sh octo_{poly,ctf,futurex}` | ❌ | ❌ | ❌ |
| 6 | Multi-agent only (structured_evolution) | `structured_evolution_evo.yaml` | ⏳ 49/219 | ⏳ 8/19 | ✅ 249/503 |
| 7 | Navigation only | `navigation.yaml` (H4/H5) | 🔄 273/2700 (batch 27/51) | ⏳ 11/21 | ❌ |
| 8 | **Full system (Multi + Nav)** | needs `structured_evolution` + `navigation_enabled: true` (no config yet) | ❌ | ❌ | ❌ |

Legend: ✅ full-scale complete · ⏳ partial · 🔄 in progress · ❌ not started.

Numbers are `passed/total_tasks_run_so_far`; target denominators are 5075 (PolyBench), 261 (CTF-Dojo), 503 (FutureX).

## Time estimation — remaining baseline full-runs

Per-task mean elapsed measured from partial runs (solver = Sonnet 4.6, workers = 5):

| Benchmark | Tasks | Batch | Per-task | Per-batch solve | Batches | Evo/cycle |
|---|---:|---:|---:|---:|---:|---|
| PolyBench | 5,075 | 100 | 47.6s | ~20.6 min | 51 | gepa 75s · mh 300s · octo ~0s |
| CTF-Dojo | 261 | 20 | 228s | ~19.7 min | 14 | gepa 75s · mh 250s · octo ~0s |
| FutureX | 503 | 20 | 7.7s\* | ~0.7 min | 26 | gepa 120s · mh 220s · octo ~0s |

\* FutureX elapsed is low because baselines are prompts-only (no search tool in seed, `evolve_tools=false`); solvers essentially guess. Realistic full-system FutureX runs take 60+ s/task.

### Per-cell wall-clock estimates

| Cell | PolyBench | CTF-Dojo | FutureX |
|---|---:|---:|---:|
| gepa | ~19.6 h | ~5.2 h | ~1.7 h |
| mh | ~22 h (likely +20% as archive grows) | ~5.6 h | ~2.3 h |
| octo | ~17.5 h | ~4.6 h | ~0.3 h |

**Total 9 baseline cells sequentially: ~79 hours (~3.3 days).**
Cost-optimal launch order: FutureX triple (~4.3 h) → CTF-Dojo triple (~15.4 h) → PolyBench triple (~58.9 h).

### Caveats

- **H4 navigation** currently running on PolyBench (batch 27/51, ~11 h elapsed). Keeping it running alongside baselines will cause Bedrock rate-limit contention and slow baselines 1.5–2×.
- **MH-lite proposer time grows with archive size**. Later PolyBench cycles (≥20) may take 1000+ seconds each. Factor ~20% overage into MH budgets.
- **OctoTools is cheapest** by a wide margin because it installs prompts at cycle 1 and freezes — zero evolution cost for 50+ subsequent cycles.
