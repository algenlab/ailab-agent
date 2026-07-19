#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
IMAGE="${ALGOLAB_PLAYWRIGHT_IMAGE:-mcr.microsoft.com/playwright/python:v1.59.0-noble}"
OUT="$ROOT/output/external_baselines/htmlcure_all200_sample0"
ALGOLAB_REPORT="$ROOT/output/experiments/algotutorgen_full_200_20260706/algolab_full_final/llm_benchmark_report.json"
ORIGINAL_AUDIT="$ROOT/output/experiments/algotutorgen_full_200_20260706/semantic_eval_machine/interaction_semantic_eval_report.json"

shard_args=()
for shard in $(seq 0 7); do
  report="$OUT/shard_$shard/llm_benchmark_report.json"
  if [[ ! -f "$report" ]]; then
    echo "missing HTMLCure shard report: $report" >&2
    exit 1
  fi
  shard_args+=(--shard-report "$report")
done

"$PYTHON" "$ROOT/scripts/analyze_htmlcure_smoke.py" \
  --manifest "$ROOT/benchmark/external_baseline_all200_sample0.json" \
  "${shard_args[@]}" \
  --output-report "$OUT/llm_benchmark_report.json" \
  --merge-only

mkdir -p "$OUT/behavior_audit/logs"
for shard in $(seq 0 7); do
  sudo -n docker run --rm --shm-size=2g \
    -v "$ROOT:$ROOT" \
    -e PYTHONPATH="$ROOT" \
    -e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    --entrypoint bash "$IMAGE" -lc "
set -euo pipefail
$PYTHON '$ROOT/scripts/run_interaction_semantic_eval.py' \\
  --algolab-report '$ALGOLAB_REPORT' \\
  --direct-report '$OUT/llm_benchmark_report.json' \\
  --output-dir '$OUT/behavior_audit/shard_$shard' \\
  --direct-only --shard-id '$shard' --num-shards 8
" >"$OUT/behavior_audit/logs/shard_$shard.log" 2>&1 &
done
wait

merge_args=()
for shard in $(seq 0 7); do
  merge_args+=(--input "$OUT/behavior_audit/shard_$shard/interaction_semantic_eval_report.json")
done
"$PYTHON" "$ROOT/scripts/merge_interaction_semantic_reports.py" \
  "${merge_args[@]}" \
  --output "$OUT/behavior_audit/interaction_semantic_eval_report.json"

"$PYTHON" "$ROOT/scripts/analyze_htmlcure_smoke.py" \
  --manifest "$ROOT/benchmark/external_baseline_all200_sample0.json" \
  "${shard_args[@]}" \
  --output-report "$OUT/llm_benchmark_report.json" \
  --original-audit "$ORIGINAL_AUDIT" \
  --repaired-audit "$OUT/behavior_audit/interaction_semantic_eval_report.json" \
  --output-analysis "$OUT/htmlcure_full200_analysis.json" \
  --output-markdown "$OUT/htmlcure_full200_analysis.md"
