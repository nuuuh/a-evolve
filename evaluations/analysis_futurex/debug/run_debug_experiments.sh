#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/../../.."

WORKERS=10
MAX_TURNS=50
TIMEOUT=300
LOG_DIR="logs/debug_l3l4"
OUT_BASE="evaluations/analysis_futurex/debug"
mkdir -p "$LOG_DIR"

COMMON="python solve_all_with_evolution.py
  --benchmark futurex
  --evolver-prompt experiments/futurex/evolver_prompt.md
  --task-timeout $TIMEOUT
  --workers $WORKERS
  --max-turns $MAX_TURNS
  --solver-temp 0.0
  --evolver-temp 0.0
  --no-infra-evo"

echo "=== FutureX L3+L4 Debug Experiments ==="
echo "Output: $OUT_BASE"
echo ""

# ── D0: No search baseline (pure LLM) ──
echo "[D0] Starting no_search_l3l4..."
$COMMON \
  --seed-workspace experiments/futurex/seed \
  --output-dir "$OUT_BASE/no_search_l3l4" \
  --config experiments/futurex/configs/debug_no_search_l3l4.yaml \
  > "$LOG_DIR/D0_no_search.log" 2>&1 &
D0_PID=$!
echo "[D0] PID=$D0_PID"

# ── D1: Baseline with strict search ──
echo "[D1] Starting baseline_l3l4..."
$COMMON \
  --seed-workspace experiments/futurex/seed \
  --output-dir "$OUT_BASE/baseline_l3l4" \
  --config experiments/futurex/configs/debug_baseline_l3l4.yaml \
  > "$LOG_DIR/D1_baseline.log" 2>&1 &
D1_PID=$!
echo "[D1] PID=$D1_PID"

echo ""
echo "Waiting for D0 and D1 to finish..."
wait $D0_PID
echo "[D0] Done (exit $?)"
wait $D1_PID
echo "[D1] Done (exit $?)"

# ── D2: H1 evolution ──
echo ""
echo "[D2] Starting evo_l3l4..."
$COMMON \
  --seed-workspace experiments/futurex/seed \
  --output-dir "$OUT_BASE/evo_l3l4" \
  --config experiments/futurex/configs/debug_evo_l3l4.yaml \
  --stride 6 \
  --batch-size 20 \
  > "$LOG_DIR/D2_evo.log" 2>&1 &
D2_PID=$!
echo "[D2] PID=$D2_PID"

# ── D3: No-hedge prompt ──
echo "[D3] Starting no_hedge_l3l4..."
$COMMON \
  --seed-workspace experiments/futurex/seed_no_hedge \
  --output-dir "$OUT_BASE/no_hedge_l3l4" \
  --config experiments/futurex/configs/debug_no_hedge_l3l4.yaml \
  > "$LOG_DIR/D3_no_hedge.log" 2>&1 &
D3_PID=$!
echo "[D3] PID=$D3_PID"

echo ""
echo "Waiting for D2 and D3 to finish..."
wait $D2_PID
echo "[D2] Done (exit $?)"
wait $D3_PID
echo "[D3] Done (exit $?)"

echo ""
echo "=== All debug experiments complete ==="
echo "Run comparison: python evaluations/analysis_futurex/debug/compare_debug.py"
