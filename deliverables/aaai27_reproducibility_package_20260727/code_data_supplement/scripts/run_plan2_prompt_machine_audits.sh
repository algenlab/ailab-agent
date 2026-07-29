#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="python3"
IMAGE="${ALGOLAB_PLAYWRIGHT_IMAGE:-iregistry.baidu-int.com/liyunhuan01/vibe-coding:latest}"
MODE="${1:-pilot}"
NUM_SHARDS="${NUM_SHARDS:-8}"
BASE="$ROOT/output/experiments/plan2_20260722/p0_2_prompt_ablation"
DIRECT_REPORT="$ROOT/output/experiments/algotutorgen_full_200_20260706/direct_html_expected_visible/llm_benchmark_report.json"

export TMPDIR="/tmp"
mkdir -p "$TMPDIR"

case "$MODE" in
  pilot) expected_cases=60 ;;
  full200) expected_cases=200 ;;
  *) echo "Usage: $0 [pilot|full200]" >&2; exit 2 ;;
esac

if sudo -n docker info >/dev/null 2>&1; then
  DOCKER=(sudo -n docker)
elif docker info >/dev/null 2>&1; then
  DOCKER=(docker)
else
  echo "Cannot access Docker daemon" >&2
  exit 126
fi

shard_complete() {
  local report="$1"
  local profile="$2"
  local expected="$3"
  [[ -f "$report" ]] || return 1
  "$PYTHON" - "$report" "$profile" "$expected" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], encoding="utf-8"))
profile = sys.argv[2]
expected = int(sys.argv[3])
rows = report.get("records") or []
keys = {(row.get("condition"), row.get("case_id")) for row in rows}
raise SystemExit(
    0
    if len(rows) == expected
    and len(keys) == len(rows)
    and all(row.get("condition") == profile for row in rows)
    else 1
)
PY
}

profiles=(hybrid_current service_only)
for profile in "${profiles[@]}"; do
  source_report="$BASE/$MODE/$profile/llm_benchmark_report.json"
  condition_out="$BASE/$MODE/machine_audits/$profile"
  merged_report="$condition_out/interaction_semantic_eval_report.json"
  mkdir -p "$condition_out/logs"
  if [[ ! -f "$source_report" ]]; then
    echo "Missing generation report: $source_report" >&2
    exit 2
  fi
  if ! jq -e --arg profile "$profile" --argjson expected "$expected_cases" \
    '.total == $expected and .config.prompt_profile == $profile' "$source_report" >/dev/null; then
    echo "Generation report is incomplete or has the wrong profile: $source_report" >&2
    exit 3
  fi
  if shard_complete "$merged_report" "$profile" "$expected_cases"; then
    echo "SKIP complete profile=$profile report=$merged_report"
    continue
  fi

  pids=()
  for shard in $(seq 0 $((NUM_SHARDS - 1))); do
    shard_out="$condition_out/shard_$shard"
    shard_report="$shard_out/interaction_semantic_eval_report.json"
    expected=$((expected_cases / NUM_SHARDS))
    if [[ "$shard" -lt $((expected_cases % NUM_SHARDS)) ]]; then
      expected=$((expected + 1))
    fi
    if shard_complete "$shard_report" "$profile" "$expected"; then
      echo "SKIP profile=$profile shard=$shard records=$expected"
      continue
    fi
    mkdir -p "$shard_out"
    rm -f "$shard_report"
    "${DOCKER[@]}" run --rm --init --shm-size=2g \
      -v /ssd1:/ssd1 \
      -e PYTHONPATH="$ROOT" \
      -e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
      -e ALGOLAB_CHROMIUM_EXECUTABLE=/ms-playwright/chromium-1223/chrome-linux64/chrome \
      -e ALGOLAB_BLOCK_EXTERNAL_RESOURCES=1 \
      --entrypoint bash "$IMAGE" -lc "
set -euo pipefail
$PYTHON '$ROOT/scripts/run_interaction_semantic_eval.py' \\
  --algolab-report '$source_report' \\
  --direct-report '$DIRECT_REPORT' \\
  --output-dir '$shard_out' \\
  --algolab-only \\
  --algolab-condition \"$profile\" \\
  --shard-id '$shard' \\
  --num-shards '$NUM_SHARDS'
" >"$condition_out/logs/shard_$shard.log" 2>&1 &
    pids+=("$!")
  done

  failed=0
  for pid in "${pids[@]}"; do
    if ! wait "$pid"; then
      failed=1
    fi
  done
  if [[ "$failed" -ne 0 ]]; then
    echo "Machine audit failed for profile=$profile; inspect $condition_out/logs" >&2
    exit 1
  fi

  merge_args=()
  for shard in $(seq 0 $((NUM_SHARDS - 1))); do
    merge_args+=(--input "$condition_out/shard_$shard/interaction_semantic_eval_report.json")
  done
  "$PYTHON" "$ROOT/scripts/merge_interaction_semantic_reports.py" \
    "${merge_args[@]}" \
    --output "$merged_report"
  shard_complete "$merged_report" "$profile" "$expected_cases"
done
