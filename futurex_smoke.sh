#!/usr/bin/env bash
# Prevent Python from using stale bytecode cache (.pyc files)
export PYTHONDONTWRITEBYTECODE=1
# Smoke tests for FutureX temporal prediction evolution.
#
# Six short experiments (~56 temporally-spread tasks each, batch_size=10)
# exercising every evolution mode:
#
#   H0a_smoke        Baseline — no evolution, NO web search (pure LLM)
#   H0b_smoke        Baseline — no evolution, strict web search
#   H1_smoke         Naive evolution (single-agent)
#   H1_multi_smoke   Multi-agent naive evolution (plan-driven, no routing)
#   H5_smoke         Navigation (inline branching)
#   H5_multi_smoke   Multi-agent navigation (plan-driven + routing)
#
# Usage:
#   bash futurex_smoke.sh                   # run all
#   bash futurex_smoke.sh H5_smoke          # single experiment
#   bash futurex_smoke.sh --stride 6 ...    # with overrides
#
# Options:
#   --stride N           Pick every Nth task for temporal spread (default: 6)
#   --batch-size N       Batch size for evolution cycles (default: 10)
#   --evolver-temp T     Evolver LLM temperature (default: 0.0)
#   --solver-temp T      Solver LLM temperature (default: 0.0)
#   --search-mode MODE   Search mode: strict or live (default: strict)
set -uo pipefail
cd "$(dirname "$0")"

# Parse named options (with smoke-friendly defaults).
STRIDE=6
BATCH_SIZE=10
EVOLVER_TEMP=0.0
SOLVER_TEMP=0.0
SEARCH_MODE=strict
BRANCH_CONFIDENCE=0.7
NO_INFRA_EVO=true
MAX_TASKS=0
TARGETS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --stride)              STRIDE="$2"; shift 2 ;;
    --batch-size)          BATCH_SIZE="$2"; shift 2 ;;
    --evolver-temp)        EVOLVER_TEMP="$2"; shift 2 ;;
    --solver-temp)         SOLVER_TEMP="$2"; shift 2 ;;
    --search-mode)         SEARCH_MODE="$2"; shift 2 ;;
    --branch-confidence)   BRANCH_CONFIDENCE="$2"; shift 2 ;;
    --no-infra-evo)        NO_INFRA_EVO=true; shift ;;
    --limit)               MAX_TASKS="$2"; shift 2 ;;
    *)                     TARGETS+=("$1"); shift ;;
  esac
done

if [ "$SEARCH_MODE" != "strict" ] && [ "$SEARCH_MODE" != "live" ]; then
  echo "ERROR: --search-mode must be 'strict' or 'live' (got: $SEARCH_MODE)" >&2
  exit 1
fi

# Validate FutureX data availability.
echo "Checking FutureX dataset availability..."
TASK_COUNT=$(python3 -c "
import logging
logging.getLogger().setLevel(logging.ERROR)
try:
    from agent_evolve.benchmarks.futurex.data_loader import FutureXDataLoader
    loader = FutureXDataLoader()
    past_tasks, online_tasks = loader.load_datasets()
    print(len(past_tasks))
except Exception as e:
    print('0')
" 2>/dev/null || echo "0")

if [ "$TASK_COUNT" -eq 0 ]; then
  echo "ERROR: FutureX dataset not found or empty" >&2
  echo "Ensure FutureX data is downloaded in data/futurex/" >&2
  exit 1
fi

echo "Dataset: FutureX-Past ($TASK_COUNT tasks; stride=$STRIDE → ~$((TASK_COUNT / STRIDE)) sampled)"
echo "Search mode: $SEARCH_MODE"

EXTRA_ARGS="--stride $STRIDE --batch-size $BATCH_SIZE --evolver-temp $EVOLVER_TEMP --solver-temp $SOLVER_TEMP --branch-confidence $BRANCH_CONFIDENCE"
if [ "$MAX_TASKS" -gt 0 ]; then
  EXTRA_ARGS="$EXTRA_ARGS --limit $MAX_TASKS"
fi

WORKERS=10

COMMON="python solve_all_with_evolution.py
  --benchmark futurex
  --seed-workspace experiments/futurex/seed
  --evolver-prompt experiments/futurex/evolver_prompt.md
  --temporal-reveal
  --task-timeout 300
  --workers $WORKERS
  --max-turns 80
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
  local logfile="$LOG_DIR/${id}_futurex_${label}.log"
  echo "=== $id: $label === (logging to $logfile)"
  # shellcheck disable=SC2086
  $COMMON "$@" > "$logfile" 2>&1 &
  local pid=$!
  echo "Started experiment $id (PID: $pid)"
  wait $pid
  local rc=$?
  echo ""
  echo "=== $id: Experiment Summary ==="
  tail -10 "$logfile" | head -5
  echo "=== $id: exit $rc ==="
  echo ""
  return $rc
}

# ─── Smoke experiments ────────────────────────────────────────────────

# H0a_smoke: Baseline — no evolution, NO web search (pure LLM reasoning)
run H0a_smoke baseline_no_search_smoke \
  --output-dir results/futurex_smoke_baseline_no_search \
  --config experiments/futurex/configs/baseline_no_search.yaml

# H0b_smoke: Baseline — no evolution, strict search (Wikipedia revision API)
run H0b_smoke baseline_smoke \
  --output-dir results/futurex_smoke_baseline \
  --config experiments/futurex/configs/baseline.yaml

# H1_smoke: Naive full evolution (single-agent)
run H1_smoke full_evo_smoke \
  --output-dir results/futurex_smoke_full_evo \
  --config experiments/futurex/configs/full_evo.yaml

# H1_multi_smoke: Structured evolution (4-phase: analyze → research → build → verify)
# Needs infra evolution — temporarily remove --no-infra-evo from COMMON
COMMON_SAVE="$COMMON"
COMMON="${COMMON//--no-infra-evo/}"
run H1_multi_smoke structured_evo_smoke \
  --evolver-prompt experiments/futurex/evolver_prompt.md \
  --output-dir results/futurex_smoke_structured_evo \
  --config experiments/futurex/configs/structured_evolution_evo.yaml
COMMON="$COMMON_SAVE"

# H5_smoke: Navigation — inline branching + task routing
run H5_smoke navigation_smoke \
  --navigation \
  --output-dir results/futurex_smoke_navigation \
  --config experiments/futurex/configs/navigation.yaml

# H5_multi_smoke: Navigation + multi-agent orchestrated evolution
run H5_multi_smoke navigation_multi_smoke \
  --navigation \
  --output-dir results/futurex_smoke_navigation_multi \
  --config experiments/futurex/configs/navigation_multi.yaml

# H5_struct_nav_smoke: Structured evolution + navigation (4-phase + git branching)
COMMON_SAVE="$COMMON"
COMMON="${COMMON//--no-infra-evo/}"
run H5_struct_nav_smoke structured_nav_smoke \
  --navigation \
  --evolver-prompt experiments/futurex/evolver_prompt.md \
  --output-dir results/futurex_smoke_structured_nav \
  --config experiments/futurex/configs/structured_navigation_evo.yaml
COMMON="$COMMON_SAVE"

# B_gepa_lite_smoke: GEPA-lite baseline (reflective prompt evolution, prompts-only)
run B_gepa_lite_smoke gepa_lite_smoke \
  --output-dir results/futurex_smoke_gepa_lite \
  --config experiments/futurex/configs/gepa_lite_evo.yaml

# B_mh_lite_smoke: Meta-Harness-lite baseline (archive-based proposer, k=1)
# Needs infra evolution — temporarily remove --no-infra-evo from COMMON
COMMON_SAVE="$COMMON"
COMMON="${COMMON//--no-infra-evo/}"
run B_mh_lite_smoke meta_harness_lite_smoke \
  --output-dir results/futurex_smoke_mh_lite \
  --config experiments/futurex/configs/meta_harness_lite_evo.yaml
COMMON="$COMMON_SAVE"

# B_octo_smoke: OctoTools expert baseline (ACL 2026 oral — static harness, no evo)
run B_octo_smoke octotools_expert_smoke \
  --output-dir results/futurex_smoke_octo \
  --config experiments/futurex/configs/octotools_expert_evo.yaml

# ─── Summary ──────────────────────────────────────────────────────────
echo ""
echo "=== All requested smoke experiments complete ==="
echo ""
echo "Smoke experiments:"
echo "  H0a_smoke        Baseline — no built-in search, no evolution (pure-LLM floor)"
echo "  H0b_smoke        Baseline — built-in strict search, no evolution (search upper bound)"
echo "  H1_smoke         Naive evolution starting from H0a floor (builtin_search=off)"
echo "  H1_multi_smoke   Multi-agent naive evolution, same floor"
echo "  H5_smoke         Navigation (inline branching), same floor"
echo "  H5_multi_smoke   Navigation + multi-agent, same floor"
echo "  B_gepa_lite_smoke   GEPA-lite baseline (reflect+mutate, prompts only)"
echo "  B_mh_lite_smoke     Meta-Harness-lite baseline (archive proposer, k=1)"
echo "  B_octo_smoke        OctoTools expert baseline (ACL 2026 oral — static harness)"
echo ""
echo "All H1/H5 experiments start with NO built-in search — evolution must"
echo "earn search capability by writing tools under /tools/*.py that the"
echo "solver invokes via the bash tool."
echo ""
echo "Key comparisons:"
echo "  H0b_smoke       vs H0a_smoke:     Value of handwritten search"
echo "  H1_smoke        vs H0a_smoke:     Value of evolution (from same floor)"
echo "  H1_smoke        vs H0b_smoke:     Can evolution match handwritten search?"
echo "  H1_multi_smoke  vs H1_smoke:      Value of multi-agent (no navigation)"
echo "  H5_smoke        vs H1_smoke:      Value of navigation"
echo "  H5_multi_smoke  vs H5_smoke:      Value of multi-agent on top of navigation"
echo "  B_gepa_lite     vs H1_smoke:      Ours vs reflective prompt evo (NeurIPS 2025)"
echo "  B_mh_lite       vs H1_smoke:      Ours vs archive-proposer baseline (2026)"
echo "  B_octo_smoke    vs H1_smoke:      Ours (evolving) vs static expert harness (ACL 2026)"
echo ""
echo "Analysis:"
echo "  grep -h 'SUMMARY' logs/*_smoke_*_futurex_*.log"
