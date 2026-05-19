#!/usr/bin/env bash
# Run the Continual Harness baseline on a benchmark.
# Usage: bash run_continual_harness.sh ctf_dojo|futurex|polybench [--suffix TAG]
set -euo pipefail

BENCH="${1:?Usage: $0 <benchmark> [--suffix TAG]}"
SUFFIX="${2:---suffix continual_harness}"

python solve_all_with_evolution.py \
  --benchmark "$BENCH" \
  --config "experiments/${BENCH}/configs/continual_harness_evo.yaml" \
  --temporal-reveal \
  $SUFFIX
