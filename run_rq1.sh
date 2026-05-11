#!/usr/bin/env bash
# RQ1 Main Table — run all Table 2 experiments across 3 benchmarks.
# Parallelism limited by Bedrock Opus rate (~2 evolving experiments at once).
# Baselines (no Opus) can run fully parallel.
#
# Usage:
#   nohup bash run_rq1.sh > logs/rq1/orchestrator.log 2>&1 &
set -uo pipefail
cd "$(dirname "$0")"

LOG_DIR="logs/rq1"
mkdir -p "$LOG_DIR"

echo "Starting RQ1 experiments at $(date)"

# PolyBench — all experiments parallel within benchmark
echo "=== PolyBench ==="
# bash poly_hypothesis.sh H0          > "$LOG_DIR/pb_h0.log" 2>&1 &
# bash poly_hypothesis.sh H0_ds       > "$LOG_DIR/pb_h0_ds.log" 2>&1 &
# bash poly_hypothesis.sh H0_kimi     > "$LOG_DIR/pb_h0_kimi.log" 2>&1 &
bash poly_hypothesis.sh H1          > "$LOG_DIR/pb_h1.log" 2>&1 &
bash poly_hypothesis.sh H4_multi    > "$LOG_DIR/pb_multi.log" 2>&1 &
bash poly_hypothesis.sh H4          > "$LOG_DIR/pb_nav.log" 2>&1 &
wait
echo "PolyBench done at $(date)"

# CTF-Dojo — all experiments parallel within benchmark.
# ctf_dojo_hypothesis.sh defaults to the GLOBAL cross-region inference
# profile for both solver (Sonnet 4.6) and evolver (Opus 4.6 V1), which
# isolates CTF traffic from the PolyBench / FutureX runs (which use the
# US profile). Nothing extra to pass here.
echo "=== CTF-Dojo ==="
bash ctf_dojo_hypothesis.sh H0       > "$LOG_DIR/ctf_h0.log"    2>&1 &
# bash ctf_dojo_hypothesis.sh H0_ds   > "$LOG_DIR/ctf_h0_ds.log" 2>&1 &
# bash ctf_dojo_hypothesis.sh H0_kimi > "$LOG_DIR/ctf_h0_kimi.log" 2>&1 &
bash ctf_dojo_hypothesis.sh H1       > "$LOG_DIR/ctf_h1.log"    2>&1 &
bash ctf_dojo_hypothesis.sh H4_multi > "$LOG_DIR/ctf_multi.log" 2>&1 &
bash ctf_dojo_hypothesis.sh H4       > "$LOG_DIR/ctf_nav.log"   2>&1 &
wait
echo "CTF-Dojo done at $(date)"

# FutureX — baselines + remaining
# echo "=== FutureX ==="
# bash futurex_hypothesis.sh H0b       > "$LOG_DIR/fx_h0b.log" 2>&1 &
# bash futurex_hypothesis.sh H0c_ds    > "$LOG_DIR/fx_h0_ds.log" 2>&1 &
# bash futurex_hypothesis.sh H0c_kimi  > "$LOG_DIR/fx_h0_kimi.log" 2>&1 &
# bash futurex_hypothesis.sh H1     # DONE: 239/503
# bash futurex_hypothesis.sh H5_multi  # RUNNING
# bash futurex_hypothesis.sh H5_nav # DONE: 190/503
# wait
# echo "FutureX done at $(date)"

# Phase 5: Multi + Nav combined (after above complete)
# echo "=== Phase 5: Multi + Nav ==="
# bash futurex_hypothesis.sh H5_multi_nav   > "$LOG_DIR/fx_multi_nav.log" 2>&1 &
# bash poly_hypothesis.sh H4_multi_nav      > "$LOG_DIR/pb_multi_nav.log" 2>&1 &
# bash ctf_dojo_hypothesis.sh H4_multi_nav  > "$LOG_DIR/ctf_multi_nav.log" 2>&1 &
# wait
# echo "Phase 5 done at $(date)"

echo "=== All RQ1 experiments complete at $(date) ==="
