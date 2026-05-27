#!/usr/bin/env bash
# Prevent Python from using stale bytecode cache (.pyc files)
export PYTHONDONTWRITEBYTECODE=1
# Hypothesis experiments for RQ1 baselines across all three benchmarks.
#
# Runs two recent (late-2025 / 2026) self-evolving-agent baselines, each
# with the same solver, batch order, reveal gate, and compute budget as
# our other RQ1 methods — so differences come from the evolution
# algorithm alone.
#
#   B_gepa_lite   GEPA-lite (Agrawal et al., NeurIPS 2025)
#                 Reflective prompt evolution. Phase 1 reflects on
#                 trajectories; Phase 2 rewrites prompts/system.md
#                 (prompts-only edit surface, matching the paper's
#                 prompt-only framing). Pareto archive dropped —
#                 trajectory-only feedback makes scalar-validation
#                 selection inapplicable.
#
#   B_mh_lite     Meta-Harness-lite (Lee et al., 2026)
#                 Archive-based proposer. Snapshots every cycle into
#                 evolution/candidates/ and gives the proposer bash
#                 access to browse the archive. Multi-file edits
#                 (prompts, skills, memory, tools, infra). k=1 per
#                 cycle to equalize per-cycle proposer compute with
#                 all other baselines; score-gated rollback dropped
#                 (trajectory-only).
#
# Three benchmarks are run for each baseline:
#   polybench (5,075 markets, 16 days, prediction-market reasoning)
#   ctf_dojo  (261 challenges, 13 years, cybersecurity)
#   futurex   (503 tasks, 82 days, temporal forecasting)
#
# When invoked with no target args, all 9 cells run in 3 phases:
#   Phase 1: FutureX  (3 cells in parallel — fastest, validates pipeline)
#   Phase 2: CTF-Dojo (3 cells in parallel — medium)
#   Phase 3: PolyBench (3 cells in parallel — longest, run last)
# Cells within a phase run concurrently; phases run sequentially so that
# each benchmark completes before the next one starts (resource
# isolation + early exit on catastrophic bug).
#
# When invoked with explicit targets, only the named targets run, still
# grouped into their benchmark phase.
#
# Usage:
#   bash baselines_hypothesis.sh                          # all 9 cells, phased
#   bash baselines_hypothesis.sh gepa_poly                # one specific cell
#   bash baselines_hypothesis.sh gepa_poly mh_poly        # subset of cells
#   bash baselines_hypothesis.sh --suffix _run2 mh_futurex
#
# Targets:
#   gepa_poly       mh_poly       octo_poly
#   gepa_ctf        mh_ctf        octo_ctf
#   gepa_futurex    mh_futurex    octo_futurex
#
# Options:
#   --suffix S           Suffix for result folder names (e.g. _run2)
#   --limit N            Cap tasks per benchmark (0 = all)
#   --evolver-temp T     Evolver LLM temperature (default: 0)
#   --solver-temp T      Solver LLM temperature (default: 0)
set -uo pipefail
cd "$(dirname "$0")/.."

# ─── Option parsing ──────────────────────────────────────────────────
SUFFIX=""
MAX_TASKS=0
EVOLVER_TEMP=0
SOLVER_TEMP=0
BRANCH_CONFIDENCE=0.7
# Solver + evolver inference profiles. Default: GLOBAL cross-region
# profiles, which isolate baseline traffic from the US-profile PolyBench /
# FutureX navigation experiments that consume most of the US bucket.
# Override per-call with ``--model-id <solver-model-id>`` and
# ``--evolver-model <evolver-model-id>`` if needed.
MODEL_ID="${SOLVER_MODEL:-<solver-model-id>}"
EVOLVER_MODEL="${EVOLVER_MODEL:-<evolver-model-id>}"
TARGETS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --suffix)              SUFFIX="$2"; shift 2 ;;
    --limit)               MAX_TASKS="$2"; shift 2 ;;
    --evolver-temp)        EVOLVER_TEMP="$2"; shift 2 ;;
    --solver-temp)         SOLVER_TEMP="$2"; shift 2 ;;
    --branch-confidence)   BRANCH_CONFIDENCE="$2"; shift 2 ;;
    --model-id)            MODEL_ID="$2"; shift 2 ;;
    --evolver-model)       EVOLVER_MODEL="$2"; shift 2 ;;
    *)                     TARGETS+=("$1"); shift ;;
  esac
done

LOG_DIR="logs"
mkdir -p "$LOG_DIR"

# ─── Per-benchmark runner ────────────────────────────────────────────
#
# Each benchmark has its own batch-size / max-turns / timeout / worker
# constants matching the full-scale *_hypothesis.sh scripts. The only
# axis that changes between B_gepa_lite and B_mh_lite is the config
# YAML (which selects the orchestrator and the evolve_* flags).
#

run_polybench() {
  local target_id="$1"
  local config="$2"
  local label="$3"

  DB_PATH="data/polymarket_analysis.db"
  if [ ! -f "$DB_PATH" ]; then
    echo "ERROR: database not found: $DB_PATH" >&2
    return 1
  fi

  local out_dir="results/polybench_${label}${SUFFIX}"
  local logfile="$LOG_DIR/${target_id}_polybench_${label}${SUFFIX}.log"
  echo "=== ${target_id}: polybench / ${label} === (logging to $logfile)"

  local extra=""
  [ "$MAX_TASKS" -gt 0 ] && extra="--limit $MAX_TASKS"

  # Mirrors poly_hypothesis.sh (batch=100, 30 turns, 300s timeout), with
  # workers=5 across all baselines for fair compute parity, --no-infra-evo,
  # branch-confidence 0.7.
  python solve_all_with_evolution.py \
    --benchmark polybench \
    --dataset "$DB_PATH" \
    --seed-workspace experiments/polybench/seed \
    --evolver-prompt experiments/polybench/evolver_prompt.md \
    --model-id "$MODEL_ID" \
    --evolver-model "$EVOLVER_MODEL" \
    --temporal-reveal \
    --max-turns 30 \
    --task-timeout 300 \
    --workers 5 \
    --batch-size 100 \
    --evolver-temp "$EVOLVER_TEMP" \
    --solver-temp "$SOLVER_TEMP" \
    --branch-confidence "$BRANCH_CONFIDENCE" \
    --no-infra-evo \
    $extra \
    --output-dir "$out_dir" \
    --config "$config" \
    > "$logfile" 2>&1
  local rc=$?
  tail -5 "$logfile"
  echo "=== ${target_id}: exit $rc ==="
  return $rc
}

run_ctf_dojo() {
  local target_id="$1"
  local config="$2"
  local label="$3"

  local catalog="data/ctf_archive.json"
  if [ ! -f "$catalog" ]; then
    echo "ERROR: catalog not found: $catalog" >&2
    return 1
  fi

  local out_dir="results/ctf_dojo_${label}${SUFFIX}"
  local logfile="$LOG_DIR/${target_id}_ctf_dojo_${label}${SUFFIX}.log"
  echo "=== ${target_id}: ctf_dojo / ${label} === (logging to $logfile)"

  local extra=""
  [ "$MAX_TASKS" -gt 0 ] && extra="--limit $MAX_TASKS"

  # Mirrors ctf_dojo_hypothesis.sh (batch=20, 50 turns, 600s timeout, 5
  # workers), branch-confidence 0.7. Infra evolution is DISABLED for all
  # baselines (--no-infra-evo) — baselines are compared on the evolution
  # algorithm alone, not on whether they can build new infra pipelines.
  python solve_all_with_evolution.py \
    --benchmark ctf_dojo \
    --dataset "$catalog" \
    --seed-workspace experiments/ctf_dojo/seed \
    --evolver-prompt experiments/ctf_dojo/evolver_prompt.md \
    --model-id "$MODEL_ID" \
    --evolver-model "$EVOLVER_MODEL" \
    --temporal-reveal \
    --max-turns 50 \
    --task-timeout 600 \
    --workers 5 \
    --batch-size 20 \
    --evolver-temp "$EVOLVER_TEMP" \
    --solver-temp "$SOLVER_TEMP" \
    --branch-confidence "$BRANCH_CONFIDENCE" \
    --no-infra-evo \
    $extra \
    --output-dir "$out_dir" \
    --config "$config" \
    > "$logfile" 2>&1
  local rc=$?
  tail -5 "$logfile"
  echo "=== ${target_id}: exit $rc ==="
  return $rc
}

run_futurex() {
  local target_id="$1"
  local config="$2"
  local label="$3"

  # Validate futurex data is available
  local task_count
  task_count=$(python3 -c "
import logging
logging.getLogger().setLevel(logging.ERROR)
try:
    from agent_evolve.benchmarks.futurex.data_loader import FutureXDataLoader
    loader = FutureXDataLoader()
    past_tasks, online_tasks = loader.load_datasets()
    print(len(past_tasks))
except Exception:
    print('0')
" 2>/dev/null || echo "0")
  if [ "$task_count" -eq 0 ]; then
    echo "ERROR: FutureX dataset not found or empty" >&2
    return 1
  fi

  local out_dir="results/futurex_${label}${SUFFIX}"
  local logfile="$LOG_DIR/${target_id}_futurex_${label}${SUFFIX}.log"
  echo "=== ${target_id}: futurex / ${label} === (logging to $logfile)"

  local extra=""
  [ "$MAX_TASKS" -gt 0 ] && extra="--limit $MAX_TASKS"

  # Mirrors futurex_hypothesis.sh (batch=20, 80 turns, 300s timeout), with
  # workers=5 across all baselines for fair compute parity, branch-confidence
  # 0.7. Infra evolution is DISABLED for all baselines (--no-infra-evo) —
  # baselines compete on the evolution algorithm alone, not on whether they
  # build new infra pipelines. The seed workspace's existing
  # infra/search_pipeline.py is still usable by the solver.
  python solve_all_with_evolution.py \
    --benchmark futurex \
    --seed-workspace experiments/futurex/seed \
    --evolver-prompt experiments/futurex/evolver_prompt.md \
    --model-id "$MODEL_ID" \
    --evolver-model "$EVOLVER_MODEL" \
    --temporal-reveal \
    --max-turns 80 \
    --task-timeout 300 \
    --workers 5 \
    --batch-size 20 \
    --evolver-temp "$EVOLVER_TEMP" \
    --solver-temp "$SOLVER_TEMP" \
    --branch-confidence "$BRANCH_CONFIDENCE" \
    --no-infra-evo \
    $extra \
    --output-dir "$out_dir" \
    --config "$config" \
    > "$logfile" 2>&1
  local rc=$?
  tail -5 "$logfile"
  echo "=== ${target_id}: exit $rc ==="
  return $rc
}

# ─── Target registry ─────────────────────────────────────────────────
#
# Each target is one (benchmark × baseline) cell from the RQ1 table.
# All 6 cells share the same shell dispatcher; they differ only in
# benchmark runner + config YAML.
#

should_run() {
  local id="$1"
  if [ ${#TARGETS[@]} -eq 0 ]; then return 0; fi
  for t in "${TARGETS[@]}"; do [ "$t" = "$id" ] && return 0; done
  return 1
}

echo "================================================================"
echo "RQ1 baselines — GEPA-lite & Meta-Harness-lite & OctoTools across 3 benchmarks"
echo "================================================================"
echo "Suffix:         ${SUFFIX:-<none>}"
echo "Max tasks:      ${MAX_TASKS}"
echo "Evolver temp:   ${EVOLVER_TEMP}"
echo "Solver temp:    ${SOLVER_TEMP}"
echo "Model-id:       ${MODEL_ID}"
echo "Evolver-model:  ${EVOLVER_MODEL}"
echo "Targets:        ${TARGETS[*]:-all (phased: FutureX -> CTF-Dojo -> PolyBench)}"
echo ""

# Background-launcher wrapper: runs a cell in the background and echoes
# the PID so the orchestrator can wait on it.
run_bg() {
  local runner_fn="$1"; shift
  "$runner_fn" "$@" &
  local pid=$!
  echo "  launched pid=$pid  $runner_fn $*"
}

# ─── Phase 1 — FutureX (smallest / cheapest first) ───────────────────
# 3 cells in parallel on the `global.` Bedrock profile. Each uses 5
# workers; combined concurrency <= 15 Sonnet calls = well within quota.
phase_futurex() {
  echo ""
  echo "============================================================"
  echo "Phase 1 — FutureX (gepa_futurex / mh_futurex / octo_futurex)"
  echo "============================================================"
  local launched=0
  if should_run gepa_futurex; then
    run_bg run_futurex gepa_futurex experiments/futurex/configs/gepa_lite_evo.yaml gepa_lite
    launched=$((launched+1))
  fi
  if should_run mh_futurex; then
    run_bg run_futurex mh_futurex experiments/futurex/configs/meta_harness_lite_evo.yaml mh_lite
    launched=$((launched+1))
  fi
  if should_run octo_futurex; then
    run_bg run_futurex octo_futurex experiments/futurex/configs/octotools_expert_evo.yaml octo_expert
    launched=$((launched+1))
  fi
  if [ "$launched" -gt 0 ]; then
    echo "  waiting for $launched FutureX cell(s)..."
    wait
    echo "Phase 1 complete."
  else
    echo "  (no FutureX targets requested — skipping)"
  fi
}

# ─── Phase 2 — CTF-Dojo ─────────────────────────────────────────────
phase_ctf_dojo() {
  echo ""
  echo "============================================================"
  echo "Phase 2 — CTF-Dojo (gepa_ctf / mh_ctf / octo_ctf)"
  echo "============================================================"
  local launched=0
  if should_run gepa_ctf; then
    run_bg run_ctf_dojo gepa_ctf experiments/ctf_dojo/configs/gepa_lite_evo.yaml gepa_lite
    launched=$((launched+1))
  fi
  if should_run mh_ctf; then
    run_bg run_ctf_dojo mh_ctf experiments/ctf_dojo/configs/meta_harness_lite_evo.yaml mh_lite
    launched=$((launched+1))
  fi
  if should_run octo_ctf; then
    run_bg run_ctf_dojo octo_ctf experiments/ctf_dojo/configs/octotools_expert_evo.yaml octo_expert
    launched=$((launched+1))
  fi
  if [ "$launched" -gt 0 ]; then
    echo "  waiting for $launched CTF-Dojo cell(s)..."
    wait
    echo "Phase 2 complete."
  else
    echo "  (no CTF-Dojo targets requested — skipping)"
  fi
}

# ─── Phase 3 — PolyBench (longest, run last) ────────────────────────
phase_polybench() {
  echo ""
  echo "============================================================"
  echo "Phase 3 — PolyBench (gepa_poly / mh_poly / octo_poly)"
  echo "============================================================"
  local launched=0
  if should_run gepa_poly; then
    run_bg run_polybench gepa_poly experiments/polybench/configs/gepa_lite_evo.yaml gepa_lite
    launched=$((launched+1))
  fi
  if should_run mh_poly; then
    run_bg run_polybench mh_poly experiments/polybench/configs/meta_harness_lite_evo.yaml mh_lite
    launched=$((launched+1))
  fi
  if should_run octo_poly; then
    run_bg run_polybench octo_poly experiments/polybench/configs/octotools_expert_evo.yaml octo_expert
    launched=$((launched+1))
  fi
  if [ "$launched" -gt 0 ]; then
    echo "  waiting for $launched PolyBench cell(s)..."
    wait
    echo "Phase 3 complete."
  else
    echo "  (no PolyBench targets requested — skipping)"
  fi
}

phase_futurex
phase_ctf_dojo
phase_polybench

# ─── Summary ─────────────────────────────────────────────────────────
echo ""
echo "=== All requested baseline experiments complete ==="
echo ""
echo "Result directories (use with the per-benchmark analysis scripts):"
echo "  results/polybench_gepa_lite${SUFFIX}       results/polybench_mh_lite${SUFFIX}       results/polybench_octo_expert${SUFFIX}"
echo "  results/ctf_dojo_gepa_lite${SUFFIX}        results/ctf_dojo_mh_lite${SUFFIX}        results/ctf_dojo_octo_expert${SUFFIX}"
echo "  results/futurex_gepa_lite${SUFFIX}         results/futurex_mh_lite${SUFFIX}         results/futurex_octo_expert${SUFFIX}"
echo ""
echo "Analysis:"
echo "  grep -h 'SUMMARY' logs/*_futurex_{gepa_lite,mh_lite}${SUFFIX}.log"
