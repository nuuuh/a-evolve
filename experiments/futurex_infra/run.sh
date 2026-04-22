#!/usr/bin/env bash
# Experiment: Infrastructure-Level Evolution with Opus 1M evolver
# Starts from ZERO search capability — evolver must build everything
#
# Usage:
#   bash experiments/futurex_infra_opus/run.sh
#
export PYTHONDONTWRITEBYTECODE=1
set -uo pipefail
cd "$(dirname "$0")/../.."   # project root

echo "=== FutureX Infrastructure Evolution (Opus 1M evolver) ==="
echo "Output:  results/futurex_infra_opus/"
echo "Config:  experiments/futurex_infra_opus/configs/full_evo.yaml"
echo "Prompt:  experiments/futurex_infra_opus/evolver_prompt.md"
echo ""

mkdir -p logs

python experiments/futurex_infra_opus/run.py \
  --benchmark futurex \
  --max-turns 20 \
  --task-timeout 300 \
  --workers 10 \
  --batch-size 20 \
  --evolver-temp 0.0 \
  --solver-temp 0.0 \
  --seed-workspace experiments/futurex_infra_opus/seed \
  --output-dir results/futurex_infra_opus \
  --config experiments/futurex_infra_opus/configs/full_evo.yaml \
  "$@" \
  2>&1 | tee logs/futurex_infra_opus.log
