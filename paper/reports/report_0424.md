# Smoke report — 2026-04-24

Results captured from the smoke runs under `results/*_smoke_*`.

## Performance summary

### FutureX — pass rate (n=56 per mode)

| Mode | Pass rate |
|---|---:|
| H0a baseline (no built-in search)       | 33.9% |
| H0b baseline (built-in strict search)   | 37.5% |
| H1 full_evo                             | 30.4% |
| H1_multi                                | 35.7% |
| H5 navigation                           | 37.5% |

### PolyBench — Accuracy on traded tasks (n=51 per mode)

Metric matches `evaluations/analysis_poly/analyze_all.py::_compute_official_metrics`: accuracy over traded tasks only (non-gated, non-SKIP).

| Mode | n_traded | Accuracy |
|---|---:|---:|
| H0 baseline   |  9 | 55.6% |
| H1 full_evo   |  9 | 44.4% |
| H1_multi      | 14 | 57.1% |
| H4 navigation | 34 | 67.6% |

### CTF-Dojo — pass rate (53 overlapping tasks across all 4 runs)

| Mode | Pass rate |
|---|---:|
| H0 baseline   | 28.3% |
| H1 full_evo   | 32.1% |
| H1_multi      | 45.3% |
| H4 navigation | 52.8% |

## Tool-use summary

### FutureX

| Mode | n | Top tool_use | bash→evolved |
|---|---:|---|---:|
| H0a (no search)       | 56 | sequentialthinking=270, submit=46 | 0/0 |
| H0b (built-in search) | 56 | web_search=743, sequentialthinking=199, submit=3 | 0/0 |
| H1 full_evo           | 56 | web_search=639, sequentialthinking=105, bash=4, submit=1 | 4/4 |
| H1_multi              | 56 | web_search=409, sequentialthinking=195, submit=9 | 0/0 |
| H5 navigation         | 56 | web_search=591, sequentialthinking=120, submit=3 | 0/0 |

| Mode | Evolved tools written |
|---|---|
| H1 full_evo   | chinese_index, crypto_price, espn_scores, football_data, fred_data, nhl_standings, yahoo_finance |
| H1_multi      | (none) |
| H5 navigation | ddg_search, wayback_fetch, yahoo_finance |

### PolyBench

| Mode | n | Top tool_use | bash→evolved |
|---|---:|---|---:|
| H0 baseline   | 51 | sequentialthinking=170, submit=51 | 0/0 |
| H1 full_evo   | 51 | sequentialthinking=173, bash=108, submit=51 | 98/108 |
| H1_multi      | 51 | sequentialthinking=179, submit=51, bash=50 | 31/50 |
| H4 navigation | 51 | sequentialthinking=157, bash=61, submit=51 | 60/61 |

| Mode | Evolved tools written |
|---|---|
| H1 full_evo   | calc_edge, detect_post_event, sports_base_rate |
| H1_multi      | market_analyzer |
| H4 navigation | ev_calculator, market_analyzer, sports_base_rates |

### CTF-Dojo (n=53 per mode; counts include tasks whose trajectory file was truncated)

| Mode | Trajectories parsed | Top tool_use | bash→evolved |
|---|---:|---|---:|
| H0 baseline   | 53 | bash=2529, submit=49 | 0/2529 |
| H1 full_evo   | 53 | bash=1642, submit=46 | 43/1642 |
| H1_multi      | 50 | bash=2145, submit=41 | 47/2145 |
| H4 navigation | 50 | bash=2258, submit=45 | 71/2258 |

| Mode | Evolved tools written |
|---|---|
| H1 full_evo   | decode_string, extract_challenge, solve_offline, verify_flag, xor_solver |
| H1_multi      | angr_solve, check_flag, crypto_factor, extract_flagcheck_hash, flag_search, ghidra_decompile, pwn_recon, rev_dynamic_recon |
| H4 navigation | crack_classical_cipher, extract_flagcheck_hash, extract_pyinstaller, fetch_writeup, hash_flag_crack, search_writeups, setup_z3 |

## Multi-agent evolution — evolvers spawned per round

| Benchmark | Min | Max | Avg |
|---|---:|---:|---:|
| FutureX H1_multi   | 1 | 2 | 1.17 |
| PolyBench H1_multi | 1 | 1 | 1.00 |
| CTF-Dojo H1_multi  | 2 | 3 | 2.50 |
