#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
IMAGE="${ALGOLAB_PLAYWRIGHT_IMAGE:-mcr.microsoft.com/playwright/python:v1.59.0-noble}"
BASE="$ROOT/output/experiments/algotutorgen_completion_20260713"
ABLATIONS="$BASE/ablation_conditions"
AUDITS="$BASE/ablation_audits"
DIRECT_REPORT="$ROOT/output/experiments/algotutorgen_full_200_20260706/direct_html_expected_visible/llm_benchmark_report.json"
NUM_SHARDS="${NUM_SHARDS:-8}"

if sudo -n docker info >/dev/null 2>&1; then
  DOCKER=(sudo -n docker)
elif docker info >/dev/null 2>&1; then
  DOCKER=(docker)
else
  echo "Cannot access Docker daemon" >&2
  exit 126
fi

if [ "$#" -gt 0 ]; then
  CONDITIONS=("$@")
else
  CONDITIONS=(no_teaching no_interaction no_teaching_interaction no_scenegraph_compiler)
fi

shard_complete() {
  local report="$1"
  local expected="$2"
  [ -f "$report" ] || return 1
  "$PYTHON" - "$report" "$expected" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
records = report.get("records") or []
keys = {(row.get("condition"), row.get("case_id")) for row in records}
raise SystemExit(0 if len(records) == int(sys.argv[2]) and len(keys) == len(records) else 1)
PY
}

for condition in "${CONDITIONS[@]}"; do
  source_report="$ABLATIONS/$condition/llm_benchmark_report.json"
  condition_out="$AUDITS/$condition"
  mkdir -p "$condition_out/logs"
  if [ ! -f "$source_report" ]; then
    echo "Missing ablation report: $source_report" >&2
    exit 2
  fi

  pids=()
  for shard in $(seq 0 $((NUM_SHARDS - 1))); do
    shard_out="$condition_out/shard_$shard"
    shard_report="$shard_out/interaction_semantic_eval_report.json"
    expected=$((200 / NUM_SHARDS))
    if [ "$shard" -lt $((200 % NUM_SHARDS)) ]; then
      expected=$((expected + 1))
    fi
    if shard_complete "$shard_report" "$expected"; then
      echo "SKIP condition=$condition shard=$shard records=$expected"
      continue
    fi
    rm -f "$shard_report"
    "${DOCKER[@]}" run --rm --init --shm-size=2g \
      -v "$ROOT:$ROOT" \
      -e PYTHONPATH="$ROOT" \
      -e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
      -e ALGOLAB_BLOCK_EXTERNAL_RESOURCES=1 \
      --entrypoint bash "$IMAGE" -lc "
set -euo pipefail
$PYTHON '$ROOT/scripts/run_interaction_semantic_eval.py' \\
  --algolab-report '$source_report' \\
  --direct-report '$DIRECT_REPORT' \\
  --output-dir '$shard_out' \\
  --algolab-only --algolab-condition '$condition' \\
  --shard-id '$shard' --num-shards '$NUM_SHARDS'
" >"$condition_out/logs/shard_$shard.log" 2>&1 &
    pids+=("$!")
  done

  failed=0
  for pid in "${pids[@]}"; do
    if ! wait "$pid"; then
      failed=1
    fi
  done
  if [ "$failed" -ne 0 ]; then
    echo "One or more shards failed for $condition; inspect $condition_out/logs" >&2
    exit 1
  fi

  merge_args=()
  for shard in $(seq 0 $((NUM_SHARDS - 1))); do
    merge_args+=(--input "$condition_out/shard_$shard/interaction_semantic_eval_report.json")
  done
  "$PYTHON" "$ROOT/scripts/merge_interaction_semantic_reports.py" \
    "${merge_args[@]}" \
    --output "$condition_out/interaction_semantic_eval_report.json"
done
