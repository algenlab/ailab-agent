#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="python3"
IMAGE="iregistry.baidu-int.com/liyunhuan01/vibe-coding:latest"
OUT="$ROOT/output/external_baselines/htmlcure_all200_sample0"
ALGOLAB_REPORT="$ROOT/output/experiments/algotutorgen_full_200_20260706/algolab_full_final/llm_benchmark_report.json"
AUDIT_OUT="$OUT/behavior_audit_external_blocked"

mkdir -p "$AUDIT_OUT/logs"
for shard in $(seq 0 7); do
  sudo -n docker run --rm --shm-size=2g \
    -v /ssd1:/ssd1 \
    -e PYTHONPATH="$ROOT" \
    -e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    -e ALGOLAB_CHROMIUM_EXECUTABLE=/ms-playwright/chromium-1223/chrome-linux64/chrome \
    -e ALGOLAB_BLOCK_EXTERNAL_RESOURCES=1 \
    --entrypoint bash "$IMAGE" -lc "
set -euo pipefail
$PYTHON '$ROOT/scripts/run_interaction_semantic_eval.py' \\
  --algolab-report '$ALGOLAB_REPORT' \\
  --direct-report '$OUT/llm_benchmark_report.json' \\
  --output-dir '$AUDIT_OUT/shard_$shard' \\
  --direct-only --shard-id '$shard' --num-shards 8
" >"$AUDIT_OUT/logs/shard_$shard.log" 2>&1 &
done
wait

merge_args=()
for shard in $(seq 0 7); do
  merge_args+=(--input "$AUDIT_OUT/shard_$shard/interaction_semantic_eval_report.json")
done
"$PYTHON" "$ROOT/scripts/merge_interaction_semantic_reports.py" \
  "${merge_args[@]}" \
  --output "$AUDIT_OUT/interaction_semantic_eval_report.json"
