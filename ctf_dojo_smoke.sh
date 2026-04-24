#!/usr/bin/env bash
# Prevent Python from using stale bytecode cache (.pyc files)
export PYTHONDONTWRITEBYTECODE=1
# Smoke tests for CTF-Dojo cybersecurity evolution.
#
# Five short experiments (~53 temporally-spread challenges, batch_size=10)
# exercising every evolution mode:
#
#   H0_smoke         Baseline (no evolution)
#   H1_smoke         Naive evolution (single-agent)
#   H1_multi_smoke   Multi-agent naive evolution (plan-driven, no routing)
#   H4_smoke         Navigation (inline branching)
#   H4_multi_smoke   Multi-agent navigation (plan-driven + routing)
#
# Usage:
#   bash ctf_dojo_smoke.sh                       # run all
#   bash ctf_dojo_smoke.sh H4_smoke              # single experiment
#   bash ctf_dojo_smoke.sh --stride 5 H1_smoke   # with overrides
#
# Options:
#   --stride N           Pick every Nth task for temporal spread (default: 5)
#   --batch-size N       Batch size for evolution cycles (default: 10)
#   --evolver-temp T     Evolver LLM temperature (default: 0)
#   --solver-temp T      Solver LLM temperature (default: 0)
set -uo pipefail
cd "$(dirname "$0")"

# First arg is catalog path if it ends in .json, otherwise all args are targets.
CATALOG="data/ctf_archive.json"
if [ $# -gt 0 ]; then
  case "$1" in
    *.json) CATALOG="$1"; shift ;;
  esac
fi

STRIDE=5
BATCH_SIZE=10
EVOLVER_TEMP=0
SOLVER_TEMP=0
BRANCH_CONFIDENCE=0.7
NO_INFRA_EVO=false
MAX_TASKS=0
TARGETS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --stride)              STRIDE="$2"; shift 2 ;;
    --batch-size)          BATCH_SIZE="$2"; shift 2 ;;
    --evolver-temp)        EVOLVER_TEMP="$2"; shift 2 ;;
    --solver-temp)         SOLVER_TEMP="$2"; shift 2 ;;
    --branch-confidence)   BRANCH_CONFIDENCE="$2"; shift 2 ;;
    --no-infra-evo)        NO_INFRA_EVO=true; shift ;;
    --limit)               MAX_TASKS="$2"; shift 2 ;;
    *)                     TARGETS+=("$1"); shift ;;
  esac
done

if [ ! -f "$CATALOG" ]; then
  echo "ERROR: catalog not found: $CATALOG" >&2
  echo "Prerequisites:" >&2
  echo "  1. Clone ctf-archive: git clone --depth 1 https://github.com/pwncollege/ctf-archive.git data/ctf-archive" >&2
  echo "  2. Build catalog: python scripts/build_ctf_catalog.py" >&2
  exit 1
fi

CHALLENGE_COUNT=$(python -c "import json; print(len(json.load(open('$CATALOG'))))" 2>/dev/null || echo "?")
echo "Catalog: $CATALOG ($CHALLENGE_COUNT challenges; stride=$STRIDE → ~$((CHALLENGE_COUNT / STRIDE)) sampled)"

EXTRA_ARGS="--stride $STRIDE --batch-size $BATCH_SIZE --evolver-temp $EVOLVER_TEMP --solver-temp $SOLVER_TEMP --branch-confidence $BRANCH_CONFIDENCE"
if [ "$MAX_TASKS" -gt 0 ]; then
  EXTRA_ARGS="$EXTRA_ARGS --limit $MAX_TASKS"
fi

COMMON="python solve_all_with_evolution.py
  --benchmark ctf_dojo
  --dataset $CATALOG
  --seed-workspace experiments/ctf_dojo/seed
  --evolver-prompt experiments/ctf_dojo/evolver_prompt.md
  --temporal-reveal
  --max-turns 80
  --task-timeout 600
  --workers 5
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
  local logfile="$LOG_DIR/${id}_ctf_dojo_${label}.log"
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
  --output-dir results/ctf_dojo_smoke_baseline \
  --config experiments/ctf_dojo/configs/baseline.yaml

# H1_smoke: Naive full evolution
run H1_smoke full_evo_smoke \
  --output-dir results/ctf_dojo_smoke_full_evo \
  --config experiments/ctf_dojo/configs/full_evo.yaml

# H1_multi_smoke: Multi-agent naive evolution (plan-driven, no routing)
run H1_multi_smoke full_evo_multi_smoke \
  --output-dir results/ctf_dojo_smoke_full_evo_multi \
  --config experiments/ctf_dojo/configs/full_evo_multi.yaml

# H4_smoke: Navigation — inline branching + task routing
run H4_smoke navigation_smoke \
  --navigation \
  --output-dir results/ctf_dojo_smoke_navigation \
  --config experiments/ctf_dojo/configs/navigation.yaml

# H4_multi_smoke: Navigation + multi-agent orchestrated evolution
run H4_multi_smoke navigation_multi_smoke \
  --navigation \
  --output-dir results/ctf_dojo_smoke_navigation_multi \
  --config experiments/ctf_dojo/configs/navigation_multi.yaml

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
echo "Analysis:  python evaluations/analysis_ctf/analyze_all.py --catalog $CATALOG"
