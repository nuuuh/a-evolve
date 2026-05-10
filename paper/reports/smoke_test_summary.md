# Smoke Test Results Summary

Solver: Sonnet 4.6. Evolver: Opus 4.6. Batch size: 10. Stride: 6.

## FutureX (Temporal Prediction, 84 tasks)

| Experiment | Correct | Acc% | Notes |
|---|---:|---:|---|
| H1 (single-agent evo) | 39/84 | 46.4 | from clean full run (240/503 overall) |
| H5_multi (structured evo) | 19/40 | 47.5 | **in progress** (40/84 done) |

## PolyBench (Prediction Markets, 51 tasks)

| Experiment | Traded | Trade Acc% | CWR% | Profit |
|---|---:|---:|---:|---:|
| H0 (no evolution) | 13/51 | 53.8 | −25.2 | −$24.01 |
| H1 (single-agent evo) | 10/51 | 70.0 | +0.2 | +$0.17 |
| H5_multi (structured evo) | 20/51 | 70.0 | **+2.9** | +$4.60 |
| H5_nav (navigation) | 11/51 | 72.7 | +2.7 | +$2.36 |

## CTF-Dojo (Security Challenges, 53 tasks)

| Experiment | Correct | Acc% |
|---|---:|---:|
| H0 (no evolution) | 15/53 | 28.3 |
| H1 (single-agent evo) | 20/53 | 37.7 |
| H5_multi (structured evo) | 23/53 | **43.4** |
| H5_nav (navigation) | 28/53 | 52.8 |

## Notes

- H1 FutureX: Clean full run (240/503 = 47.7%) is the reliable baseline. On the same 84 smoke tasks: H1 scores 39/84 = 46.4%. Structured evo tracking at 47.5% through 40/84 tasks — effectively tied.
- H5_multi FutureX is still running (37/84 tasks complete). Current trajectory: B1=20%, B2=70%, B3=60%.
- PolyBench primary metric is CWR% (capital-weighted return), not accuracy. Base agent loses money; evolution breaks even; structured evo and navigation are profitable.
- CTF-Dojo H5_nav (navigation) result is from a previous run with different code (older template). H5_multi is the current structured evo with fixed templates.
