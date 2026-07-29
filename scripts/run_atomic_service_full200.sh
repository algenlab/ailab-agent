#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="/ssd1/liaokunpeng/agent-py310-cu/bin/python3"
BASE="${PLAN3_ATOMIC_FULL200_BASE:-$ROOT/output/experiments/plan3_20260725/atomic_service_manual_claim_full200}"
PILOT_MANIFEST="${PLAN3_ATOMIC_PILOT_MANIFEST:-$ROOT/output/experiments/plan3_20260725/atomic_service_manual_claim_pilot/pilot_manifest.json}"
DIRECT_REPORT="$ROOT/output/experiments/algotutorgen_full_200_20260706/direct_html_expected_visible/llm_benchmark_report.json"
IMAGE="${ALGOLAB_PLAYWRIGHT_IMAGE:-iregistry.baidu-int.com/liyunhuan01/vibe-coding:latest}"
NUM_SHARDS="${NUM_SHARDS:-8}"
CONCURRENCY_PER_CONDITION="${CONCURRENCY_PER_CONDITION:-16}"
PHASE="${1:-all}"
EXPECTED=200
EXPECTED_PROFILE_VERSION="single-execution-pilot-v2"

export TMPDIR="/ssd1/liaokunpeng/.tmp"
mkdir -p "$TMPDIR" "$BASE"

expected_generation_hash() {
  local mode="$1"
  PYTHONPATH="$ROOT" "$PYTHON" -c \
    'import sys; from algolab.generation.execution_modes import execution_mode_metadata; print(execution_mode_metadata(sys.argv[1], "hybrid_current")["generation_prompt_sha256"])' \
    "$mode"
}

generation_complete() {
  local report="$1"
  local mode="$2"
  local condition="$3"
  local prompt_hash="$4"
  [[ -f "$report" ]] || return 1
  jq -e \
    --arg mode "$mode" \
    --arg condition "$condition" \
    --arg profile_version "$EXPECTED_PROFILE_VERSION" \
    --arg prompt_hash "$prompt_hash" \
    --argjson expected "$EXPECTED" \
    '(.total == $expected) and
     ((.config.cases | length) == 0) and
     (.config.sample == 0) and
     (.config.all_samples == false) and
     (.config.execution_mode == $mode) and
     (.config.benchmark_condition == $condition) and
     (.config.execution_mode_metadata.profile_version == $profile_version) and
     (.config.execution_mode_metadata.generation_prompt_sha256 == $prompt_hash)' \
    "$report" >/dev/null
}

run_generation() {
  local mode="$1"
  local condition="${mode}_service"
  local output_dir="$BASE/$mode"
  local report="$output_dir/llm_benchmark_report.json"
  local prompt_hash
  prompt_hash="$(expected_generation_hash "$mode")"
  if generation_complete "$report" "$mode" "$condition" "$prompt_hash"; then
    echo "SKIP complete generation mode=$mode"
    return
  fi
  mkdir -p "$output_dir"
  local benchmark_status=0
  "$PYTHON" "$ROOT/scripts/run_llm_benchmark.py" \
    --sample 0 \
    --solutions 2 \
    --max-rounds 2 \
    --max-candidates 2 \
    --timeout-s 3000 \
    --strict-warnings \
    --no-browser-smoke \
    --teaching-enrichment \
    --write-each \
    --resume \
    --concurrency "$CONCURRENCY_PER_CONDITION" \
    --prompt-profile hybrid_current \
    --execution-mode "$mode" \
    --condition "$condition" \
    --output-dir "$output_dir" || benchmark_status=$?
  if generation_complete "$report" "$mode" "$condition" "$prompt_hash"; then
    echo "COMPLETE generation mode=$mode benchmark_status=$benchmark_status"
    return 0
  fi
  echo "Incomplete generation mode=$mode benchmark_status=$benchmark_status" >&2
  if [[ "$benchmark_status" -eq 0 ]]; then
    benchmark_status=1
  fi
  return "$benchmark_status"
}

machine_complete() {
  local report="$1"
  local condition="$2"
  local expected="$3"
  [[ -f "$report" ]] || return 1
  jq -e \
    --arg condition "$condition" \
    --argjson expected "$expected" \
    '([.records[] | select(.condition == $condition)] | length) == $expected' \
    "$report" >/dev/null
}

docker_command() {
  if sudo -n docker info >/dev/null 2>&1; then
    printf '%s\n' "sudo -n docker"
  elif docker info >/dev/null 2>&1; then
    printf '%s\n' "docker"
  else
    return 126
  fi
}

run_machine_audit() {
  local mode="$1"
  local condition="${mode}_service"
  local source_report="$BASE/$mode/llm_benchmark_report.json"
  local audit_dir="$BASE/machine_audits/$mode"
  local merged="$audit_dir/interaction_semantic_eval_report.json"
  if machine_complete "$merged" "$condition" "$EXPECTED"; then
    echo "SKIP complete machine audit mode=$mode"
    return
  fi
  local docker_text
  docker_text="$(docker_command)"
  read -r -a docker_cmd <<<"$docker_text"
  mkdir -p "$audit_dir/logs"
  local pids=()
  for shard in $(seq 0 $((NUM_SHARDS - 1))); do
    local shard_dir="$audit_dir/shard_$shard"
    local shard_report="$shard_dir/interaction_semantic_eval_report.json"
    local expected=$((EXPECTED / NUM_SHARDS))
    if [[ "$shard" -lt $((EXPECTED % NUM_SHARDS)) ]]; then
      expected=$((expected + 1))
    fi
    if machine_complete "$shard_report" "$condition" "$expected"; then
      continue
    fi
    mkdir -p "$shard_dir"
    "${docker_cmd[@]}" run --rm --init --shm-size=2g \
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
  --output-dir '$shard_dir' \\
  --algolab-only \\
  --algolab-condition '$condition' \\
  --shard-id '$shard' \\
  --num-shards '$NUM_SHARDS'
" >"$audit_dir/logs/shard_$shard.log" 2>&1 &
    pids+=("$!")
  done
  local failed=0
  for pid in "${pids[@]}"; do
    if ! wait "$pid"; then
      failed=1
    fi
  done
  if [[ "$failed" -ne 0 ]]; then
    echo "Machine audit failed for mode=$mode" >&2
    exit 1
  fi
  local merge_args=()
  for shard in $(seq 0 $((NUM_SHARDS - 1))); do
    merge_args+=(--input "$audit_dir/shard_$shard/interaction_semantic_eval_report.json")
  done
  "$PYTHON" "$ROOT/scripts/merge_interaction_semantic_reports.py" \
    "${merge_args[@]}" \
    --output "$merged"
  machine_complete "$merged" "$condition" "$EXPECTED"
}

analyze() {
  "$PYTHON" "$ROOT/scripts/analyze_atomic_service_pilot.py" \
    --atomic-report "$BASE/atomic/llm_benchmark_report.json" \
    --decoupled-report "$BASE/decoupled/llm_benchmark_report.json" \
    --atomic-machine-report "$BASE/machine_audits/atomic/interaction_semantic_eval_report.json" \
    --decoupled-machine-report "$BASE/machine_audits/decoupled/interaction_semantic_eval_report.json" \
    --expected-pairs "$EXPECTED" \
    --exclude-manifest "$PILOT_MANIFEST" \
    --output "$BASE/atomic_service_full200_report.json"
}

case "$PHASE" in
  generate)
    run_generation atomic & atomic_pid=$!
    run_generation decoupled & decoupled_pid=$!
    wait "$atomic_pid"
    wait "$decoupled_pid"
    ;;
  audit)
    run_machine_audit atomic
    run_machine_audit decoupled
    ;;
  analyze)
    analyze
    ;;
  all)
    "$0" generate
    "$0" audit
    "$0" analyze
    ;;
  *)
    echo "Usage: $0 [generate|audit|analyze|all]" >&2
    exit 2
    ;;
esac
