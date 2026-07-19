#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="/ssd1/liaokunpeng/agent-py310-cu/bin/python3"
BASE="$ROOT/output/experiments/algotutorgen_completion_20260713/judge_robustness"
MACHINE="$ROOT/output/experiments/algotutorgen_full_200_20260706/semantic_eval_machine_rendered_text/interaction_semantic_eval_report.json"

mkdir -p "$BASE/logs"

run_cell() {
  local name="$1"
  local model="$2"
  local order="$3"
  "$PYTHON" "$ROOT/scripts/run_external_eval_methods.py" \
    --machine-report "$MACHINE" \
    --output-dir "$BASE/$name" \
    --llm-review \
    --model "$model" \
    --blind-order "$order" \
    --concurrency 8 \
    >"$BASE/logs/$name.log" 2>&1
}

pids=()
run_cell deepseek_swapped DeepSeek-V4-Pro swapped & pids+=("$!")
run_cell gemini_frozen gemini-3-flash-preview frozen & pids+=("$!")
run_cell gemini_swapped gemini-3-flash-preview swapped & pids+=("$!")

failed=0
for pid in "${pids[@]}"; do
  if ! wait "$pid"; then
    failed=1
  fi
done
if [ "$failed" -ne 0 ]; then
  echo "Judge robustness matrix failed; inspect $BASE/logs" >&2
  exit 1
fi
