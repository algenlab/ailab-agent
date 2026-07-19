#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${ALGOLAB_PYTHON_BIN:-python3}"
NUM_SHARDS=16
ALGOLAB_REPORT=""
DIRECT_REPORT=""
OUTPUT_DIR=""
ALGOLAB_CONDITION="algolab_full"
DIRECT_CONDITION="direct_html"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --algolab-report)
      ALGOLAB_REPORT="$2"
      shift 2
      ;;
    --direct-report)
      DIRECT_REPORT="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --algolab-condition)
      ALGOLAB_CONDITION="$2"
      shift 2
      ;;
    --direct-condition)
      DIRECT_CONDITION="$2"
      shift 2
      ;;
    --num-shards)
      NUM_SHARDS="$2"
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [ -z "$ALGOLAB_REPORT" ] || [ -z "$DIRECT_REPORT" ] || [ -z "$OUTPUT_DIR" ]; then
  echo "--algolab-report, --direct-report, and --output-dir are required" >&2
  exit 2
fi
if ! [[ "$NUM_SHARDS" =~ ^[1-9][0-9]*$ ]]; then
  echo "--num-shards must be a positive integer" >&2
  exit 2
fi

cd "$PROJECT_ROOT"
mkdir -p "$OUTPUT_DIR/logs"

pids=()
for shard in $(seq 0 $((NUM_SHARDS - 1))); do
  shard_dir="$OUTPUT_DIR/shard_$shard"
  mkdir -p "$shard_dir"
  scripts/run_browser_smoke_container.sh \
    env ALGOLAB_BLOCK_EXTERNAL_RESOURCES=1 \
    python3 scripts/run_interaction_semantic_eval.py \
    --algolab-report "$ALGOLAB_REPORT" \
    --direct-report "$DIRECT_REPORT" \
    --output-dir "$shard_dir" \
    --algolab-condition "$ALGOLAB_CONDITION" \
    --direct-condition "$DIRECT_CONDITION" \
    --shard-id "$shard" \
    --num-shards "$NUM_SHARDS" \
    >"$OUTPUT_DIR/logs/shard_$shard.log" 2>&1 &
  pids+=("$!")
done

failed=0
for index in "${!pids[@]}"; do
  if ! wait "${pids[$index]}"; then
    echo "audit shard $index failed; see $OUTPUT_DIR/logs/shard_$index.log" >&2
    failed=1
  fi
done
if [ "$failed" -ne 0 ]; then
  exit 1
fi

merge_args=()
for shard in $(seq 0 $((NUM_SHARDS - 1))); do
  merge_args+=(--input "$OUTPUT_DIR/shard_$shard/interaction_semantic_eval_report.json")
done
"$PYTHON_BIN" scripts/merge_interaction_semantic_reports.py \
  "${merge_args[@]}" \
  --output "$OUTPUT_DIR/interaction_semantic_eval_report.json"
