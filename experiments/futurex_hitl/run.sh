#!/usr/bin/env bash
# Experiment: Human-in-the-Loop Evolution via Telegram
# Same as futurex_infra_opus but with Telegram-based human interaction.
# The evolver can request API keys mid-conversation via Telegram.
#
# Setup:
#   1. Create a Telegram bot via @BotFather
#   2. Get your chat ID (see test_telegram.py)
#   3. Fill in telegram_bot_token and telegram_chat_id in the config YAML
#   4. Test with: python experiments/futurex_hitl/test_telegram.py
#
# Usage:
#   bash experiments/futurex_hitl/run.sh
#
export PYTHONDONTWRITEBYTECODE=1
set -uo pipefail
cd "$(dirname "$0")/../.."   # project root

echo "=== FutureX Human-in-the-Loop Evolution (Telegram) ==="
echo "Output:  results/futurex_hitl/"
echo "Config:  experiments/futurex_hitl/configs/full_evo.yaml"
echo "Prompt:  experiments/futurex_hitl/evolver_prompt.md"
echo ""

mkdir -p logs

python experiments/futurex_hitl/run.py \
  --benchmark futurex \
  --max-turns 20 \
  --task-timeout 300 \
  --workers 3 \
  --batch-size 3 \
  --evolver-temp 0.0 \
  --solver-temp 0.0 \
  --seed-workspace experiments/futurex_hitl/seed \
  --output-dir results/futurex_hitl \
  --config experiments/futurex_hitl/configs/full_evo.yaml \
  "$@" \
  2>&1 | tee logs/futurex_hitl.log
# --verbose
