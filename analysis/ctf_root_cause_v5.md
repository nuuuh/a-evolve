# CTF Dojo root-cause analysis: full-system v4 vs multi-only

**Read-only investigation.** Source data: `results/ctf_dojo_structured_evo/` (multi), `results/ctf_dojo_structured_nav/` (full v4).

## 1. Headline numbers

| Run | Pass | Total | Rate | Δ vs multi |
|---|---|---|---|---|
| multi-only | 136 | 261 | 52.1% | — |
| full v4 | 124 | 261 | 47.5% | -4.60pp |

| Cell | Count |
|---|---|
| both_pass | 111 |
| multi_only | 25 |
| full_only | 13 |
| both_fail | 112 |

Net for full = full_only − multi_only = 13 − 25 = **-12**.

## 2. Where the regression concentrates

### By category

| Category | N | Multi | Full | Δpp |
|---|---|---|---|---|
| crypto | 80 | 50/80 (62%) | 49/80 (61%) | -1.2pp |
| rev | 80 | 47/80 (59%) | 43/80 (54%) | -5.0pp |
| pwn | 48 | 5/48 (10%) | 2/48 (4%) | -6.2pp |
| misc | 23 | 17/23 (74%) | 14/23 (61%) | -13.0pp |
| forensics | 14 | 9/14 (64%) | 9/14 (64%) | +0.0pp |
| web | 12 | 5/12 (42%) | 6/12 (50%) | +8.3pp |
| recon | 2 | 2/2 (100%) | 0/2 (0%) | -100.0pp |
| unknown | 1 | 1/1 (100%) | 1/1 (100%) | +0.0pp |
| pwn/misc | 1 | 0/1 (0%) | 0/1 (0%) | +0.0pp |

### By files_count

| files_count | Multi | Full | Δpp |
|---|---|---|---|
| 0 | 10/11 (91%) | 8/11 (73%) | -18.2pp |
| 1 | 107/200 (54%) | 102/200 (51%) | -2.5pp |
| 2 | 15/38 (39%) | 12/38 (32%) | -7.9pp |
| 3 | 2/8 (25%) | 1/8 (12%) | -12.5pp |
| 4 | 1/3 (33%) | 0/3 (0%) | -33.3pp |
| 5 | 1/1 (100%) | 1/1 (100%) | +0.0pp |

### By description-length quartile

| desc-len q | Multi | Full | Δpp |
|---|---|---|---|
| q0 | 28/68 (41%) | 30/68 (44%) | +2.9pp |
| q1 | 32/65 (49%) | 29/65 (45%) | -4.6pp |
| q2 | 39/63 (62%) | 33/63 (52%) | -9.5pp |
| q3 | 37/65 (57%) | 32/65 (49%) | -7.7pp |

## 3. Failure-mode distribution on the 46 lost tasks (full's outcome)

| Mode | Count | % |
|---|---|---|
| max_turns_wrong_submit | 13 | 52.0% |
| wrong_submit_normal | 10 | 40.0% |
| wrong_submit_quick | 2 | 8.0% |

## 4. Failure-mode on the 17 full-only-wins (multi's outcome)

| Mode | Count | % |
|---|---|---|
| max_turns_wrong_submit | 5 | 38.5% |
| wrong_submit_normal | 3 | 23.1% |
| wrong_submit_quick | 3 | 23.1% |
| no_submit_other | 2 | 15.4% |

## 5. Branch routing (full system only)

| Branch | N | Full | Multi (same tasks) | Δpp |
|---|---|---|---|---|
| main | 261 | 124/261 (48%) | 136/261 (52%) | -4.6pp |

## 6. Trajectory pattern presence (the 46 lost tasks)

Counts = #trajectories (out of 46) where the pattern appears at least once.

| Pattern | multi (lost46) | full (lost46) | Δ |
|---|---|---|---|
| RsaCtfTool | 0 | 0 | 0 |
| bash_call | 25 | 25 | 0 |
| binwalk | 0 | 1 | 1 |
| bls_forgery | 0 | 0 | 0 |
| broken_rehost | 2 | 1 | -1 |
| checksec | 3 | 0 | -3 |
| docker_error | 0 | 11 | 11 |
| flagcheck_oracle | 0 | 0 | 0 |
| github_fetch | 18 | 0 | -18 |
| precompute_cands | 0 | 0 | 0 |
| pwntools | 3 | 0 | -3 |
| rsa_solver | 10 | 0 | -10 |
| stego_zsteg | 0 | 1 | 1 |
| submit_call | 25 | 25 | 0 |

## 7. Early-exit-on-broken-rehost hypothesis

- Tasks classified `wrong_submit_quick` (full submitted ≤5 turns, wrong): **2**
- Of those, # with `'broken rehost' | 'MAY BE UNSOLVABLE'` in trajectory: **0**

## 8. No-submit cases

| Run | Total no-submit | max_turns | other | timed_out |
|---|---|---|---|---|
| full | 15 | 0 | 9 | 6 |
| multi | 9 | 1 | 4 | 4 |

## 9. Solver behavioral diff on shared-success tasks

| Run | n | mean turns | p50 | p90 |
|---|---|---|---|---|
| multi | 111 | 11.9 | 7 | 29 |
| full | 111 | 14.7 | 12 | 27 |

## 10. Per-batch pass rate

| batch | Multi | Full |
|---|---|---|
| 1 | 8/20 (40%) | 11/20 (55%) |
| 2 | 2/20 (10%) | 4/20 (20%) |
| 3 | 5/20 (25%) | 6/20 (30%) |
| 4 | 7/20 (35%) | 7/20 (35%) |
| 5 | 14/20 (70%) | 14/20 (70%) |
| 6 | 17/20 (85%) | 14/20 (70%) |
| 7 | 11/20 (55%) | 10/20 (50%) |
| 8 | 12/20 (60%) | 11/20 (55%) |
| 9 | 5/20 (25%) | 7/20 (35%) |
| 10 | 10/20 (50%) | 9/20 (45%) |
| 11 | 13/20 (65%) | 9/20 (45%) |
| 12 | 18/20 (90%) | 11/20 (55%) |
| 13 | 14/20 (70%) | 11/20 (55%) |
| 14 | 0/1 (0%) | 0/1 (0%) |

## 11. Top hypotheses (ranked by evidence weight)

See accompanying chat summary or `ctf_root_cause_summary.json` for full numeric backing. Hypotheses are ordered by the magnitude of evidence. The recommended action will depend on user judgment.
