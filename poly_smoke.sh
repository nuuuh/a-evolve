#!/usr/bin/env bash
# Prevent Python from using stale bytecode cache (.pyc files)
export PYTHONDONTWRITEBYTECODE=1
# Smoke tests for PolyBench prediction-market evolution.
#
# Five short experiments (~51 temporally-spread markets, batch_size=10)
# exercising every evolution mode:
#
#   H0_smoke         Baseline (no evolution)
#   H1_smoke         Naive evolution (single-agent)
#   H1_multi_smoke   Multi-agent naive evolution (plan-driven, no routing)
#   H4_smoke         Navigation (inline branching)
#   H4_multi_smoke   Multi-agent navigation (plan-driven + routing)
#
# Usage:
#   bash poly_smoke.sh                         # run all
#   bash poly_smoke.sh H4_smoke                # single experiment
#   bash poly_smoke.sh --stride 237 H1_smoke   # with overrides
set -uo pipefail
cd "$(dirname "$0")"

# First arg is DB path if it ends in .db/.sqlite, otherwise all args are targets.
DB_PATH="data/polymarket_analysis.db"
if [ $# -gt 0 ]; then
  case "$1" in
    *.db|*.sqlite) DB_PATH="$1"; shift ;;
  esac
fi

STRIDE=100
BATCH_SIZE=10
EVOLVER_TEMP=0
SOLVER_TEMP=0
BRANCH_CONFIDENCE=0.7
SUFFIX=""
NO_INFRA_EVO=true
MAX_TASKS=0
TARGETS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --stride)              STRIDE="$2"; shift 2 ;;
    --batch-size)          BATCH_SIZE="$2"; shift 2 ;;
    --evolver-temp)        EVOLVER_TEMP="$2"; shift 2 ;;
    --solver-temp)         SOLVER_TEMP="$2"; shift 2 ;;
    --branch-confidence)   BRANCH_CONFIDENCE="$2"; shift 2 ;;
    --suffix)              SUFFIX="$2"; shift 2 ;;
    --no-infra-evo)        NO_INFRA_EVO=true; shift ;;
    --limit)               MAX_TASKS="$2"; shift 2 ;;
    *)                     TARGETS+=("$1"); shift ;;
  esac
done

if [ ! -f "$DB_PATH" ]; then
  echo "ERROR: database not found: $DB_PATH" >&2
  echo "Download from the PolyBench repo and place at $DB_PATH" >&2
  exit 1
fi

TASK_COUNT=$(sqlite3 "$DB_PATH" "
  SELECT COUNT(*) FROM market_snapshots ms
  JOIN resolutions r ON ms.market_id = r.market_id
  WHERE ms.ready_for_analysis = 1;
" 2>/dev/null || echo "?")
echo "Database: $DB_PATH ($TASK_COUNT markets; stride=$STRIDE → ~$((TASK_COUNT / STRIDE)) sampled)"

EXTRA_ARGS="--stride $STRIDE --batch-size $BATCH_SIZE --evolver-temp $EVOLVER_TEMP --solver-temp $SOLVER_TEMP --branch-confidence $BRANCH_CONFIDENCE"
if [ "$MAX_TASKS" -gt 0 ]; then
  EXTRA_ARGS="$EXTRA_ARGS --limit $MAX_TASKS"
fi

COMMON="python solve_all_with_evolution.py
  --benchmark polybench
  --dataset $DB_PATH
  --seed-workspace experiments/polybench/seed
  --evolver-prompt experiments/polybench/evolver_prompt.md
  --temporal-reveal
  --max-turns 80
  --task-timeout 300
  --workers 24
  $EXTRA_ARGS"
if [ "$NO_INFRA_EVO" = true ]; then
  COMMON="$COMMON --no-infra-evo"
fi

LOG_DIR="logs"
mkdir -p "$LOG_DIR"

run() {
  local id="$1"; shift
  local label="$1"; shift
  if [ ${#TARGETS[@]} -gt 0 ]; then
    local match=0
    for t in "${TARGETS[@]}"; do [ "$t" = "$id" ] && match=1; done
    [ "$match" -eq 0 ] && return 0
  fi
  local logfile="$LOG_DIR/${id}_polybench_${label}${SUFFIX}.log"
  echo "=== $id: $label === (logging to $logfile)"
  # shellcheck disable=SC2086
  $COMMON "$@" > "$logfile" 2>&1
  local rc=$?
  tail -5 "$logfile"
  echo "=== $id: exit $rc ==="
  return $rc
}

# ─── Smoke experiments ────────────────────────────────────────────────

# H0_smoke: Baseline — no evolution
run H0_smoke baseline_smoke \
  --output-dir "results/polybench_smoke_baseline${SUFFIX}" \
  --config experiments/polybench/configs/baseline.yaml

# H1_smoke: Naive full evolution
run H1_smoke full_evo_smoke \
  --output-dir "results/polybench_smoke_full_evo${SUFFIX}" \
  --config experiments/polybench/configs/full_evo.yaml

# H1_multi_smoke: Structured evolution (4-phase: analyze → research → build → verify)
run H1_multi_smoke structured_evo_smoke \
  --output-dir "results/polybench_smoke_structured_evo${SUFFIX}" \
  --config experiments/polybench/configs/structured_evolution_evo.yaml

# H4_smoke: Navigation — inline branching + task routing
run H4_smoke navigation_smoke \
  --navigation \
  --output-dir "results/polybench_smoke_navigation${SUFFIX}" \
  --config experiments/polybench/configs/navigation.yaml

# H4_multi_smoke: Navigation + multi-agent orchestrated evolution
run H4_multi_smoke navigation_multi_smoke \
  --navigation \
  --output-dir "results/polybench_smoke_navigation_multi${SUFFIX}" \
  --config experiments/polybench/configs/navigation_multi.yaml

# ─── Summary ──────────────────────────────────────────────────────────
echo ""
echo "=== All requested smoke experiments complete ==="
echo ""
echo "Smoke experiments:"
echo "  H0_smoke         Baseline (no evolution)"
echo "  H1_smoke         Naive evolution"
echo "  H1_multi_smoke   Multi-agent naive evolution (plan-driven, no routing)"
echo "  H4_smoke         Navigation (inline branching)"
echo "  H4_multi_smoke   Navigation + multi-agent (plan-driven + routing)"
echo ""
echo "Key comparisons:"
echo "  H1_smoke        vs H0_smoke:      Value of naive evolution"
echo "  H1_multi_smoke  vs H1_smoke:      Value of multi-agent (no navigation)"
echo "  H4_smoke        vs H1_smoke:      Value of navigation"
echo "  H4_multi_smoke  vs H4_smoke:      Value of multi-agent on top of navigation"
echo ""
echo "Analysis:  python evaluations/analysis_poly/analyze_all.py --db $DB_PATH"
