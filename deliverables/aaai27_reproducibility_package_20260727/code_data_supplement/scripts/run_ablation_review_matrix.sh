#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="python3"
BASE="$ROOT/output/experiments/algotutorgen_completion_20260713"
FULL="$ROOT/output/experiments/algotutorgen_full_200_20260706/semantic_eval_machine_rendered_text/interaction_semantic_eval_report.json"

mkdir -p "$BASE/ablation_pair_reviews/logs"

run_condition() {
  local condition="$1"
  "$PYTHON" "$ROOT/scripts/run_ablation_pair_reviews.py" \
    --full-report "$FULL" \
    --ablation-report "$BASE/ablation_audits/$condition/interaction_semantic_eval_report.json" \
    --condition "$condition" \
    --output-dir "$BASE/ablation_pair_reviews/$condition" \
    --model DeepSeek-V4-Pro \
    --blind-order frozen \
    --concurrency 8 \
    >"$BASE/ablation_pair_reviews/logs/$condition.log" 2>&1
}

pids=()
run_condition no_teaching & pids+=("$!")
run_condition no_interaction & pids+=("$!")
run_condition no_teaching_interaction & pids+=("$!")

failed=0
for pid in "${pids[@]}"; do
  if ! wait "$pid"; then
    failed=1
  fi
done
if [ "$failed" -ne 0 ]; then
  echo "Ablation review matrix failed; inspect $BASE/ablation_pair_reviews/logs" >&2
  exit 1
fi
