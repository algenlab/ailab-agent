#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PLAN2_PYTHON:-python3}"
MODE="${1:-pilot}"
BASE="${PLAN2_OUTPUT_BASE:-$ROOT/output/experiments/plan2_20260722/p0_2_prompt_ablation}"
MANIFEST="${PLAN2_PILOT_MANIFEST:-$BASE/pilot_manifest.json}"
FULL200_BENCHMARK="${PLAN2_FULL200_BENCHMARK:-$ROOT/benchmark/algo_learn_env_benchmark.json}"
PROFILE_CONCURRENCY="${PLAN2_PROFILE_CONCURRENCY:-8}"
MODEL="DeepSeek-V4-Pro"

export TMPDIR="/tmp"
export ALGOLAB_LLM_MODEL="$MODEL"
export ALGOLAB_LLM_TIMEOUT_S="600"
export ALGOLAB_LLM_MAX_TOKENS="32768"
export ALGOLAB_LLM_JSON_RETRIES="3"
export ALGOLAB_LLM_API_RETRIES="1"

case_args=()
pilot_case_ids_json='[]'
expected_case_ids_json='[]'
if [[ ! -f "$FULL200_BENCHMARK" ]]; then
  echo "Missing Full-200 benchmark: $FULL200_BENCHMARK" >&2
  exit 2
fi
if ! jq -e '
  (.cases | type) == "array"
  and (.cases | length) == 200
  and ([.cases[].id] | unique | length) == 200
  and ([.cases[] | select((.problem | type) != "string")] | length) == 0
  and ([.cases[] | select((.strategy | type) != "string")] | length) == 0
  and ([.cases[] | select((.samples | type) != "array" or (.samples | length) == 0)] | length) == 0
' "$FULL200_BENCHMARK" >/dev/null; then
  echo "Invalid frozen Full-200 benchmark: $FULL200_BENCHMARK" >&2
  exit 2
fi
if [[ "$MODE" == "pilot" ]]; then
  if [[ ! -f "$MANIFEST" ]]; then
    echo "Missing pilot manifest: $MANIFEST" >&2
    exit 2
  fi
  if ! pilot_case_ids_json="$(jq -ce '
    .case_ids as $ids
    | if ($ids | type) != "array" then error("case_ids must be an array")
      elif ($ids | length) != 60 then error("case_ids must contain exactly 60 entries")
      elif ([$ids[] | select(type != "string")] | length) != 0 then error("case_ids must contain only strings")
      elif ([$ids[] | select(length == 0)] | length) != 0 then error("case_ids must not contain empty strings")
      elif ($ids | unique | length) != 60 then error("case_ids must be unique")
      else $ids
      end
  ' "$MANIFEST")"; then
    echo "Invalid pilot manifest: $MANIFEST" >&2
    exit 2
  fi
  if ! pilot_case_lines="$(jq -er '.[]' <<<"$pilot_case_ids_json")"; then
    echo "Failed to read pilot case IDs: $MANIFEST" >&2
    exit 2
  fi
  mapfile -t pilot_case_ids <<<"$pilot_case_lines"
  if [[ "${#pilot_case_ids[@]}" -ne 60 ]]; then
    echo "Invalid pilot manifest case count after parsing: ${#pilot_case_ids[@]}" >&2
    exit 2
  fi
  for case_id in "${pilot_case_ids[@]}"; do
    case_args+=(--case "$case_id")
  done
  expected_case_ids_json="$pilot_case_ids_json"
  expected_cases=60
elif [[ "$MODE" == "full200" ]]; then
  if ! full200_case_ids_json="$(jq -ce '
    .cases as $cases
    | if ($cases | type) != "array" then error("cases must be an array")
      elif ($cases | length) != 200 then error("cases must contain exactly 200 entries")
      elif ([$cases[] | .id | select(type != "string")] | length) != 0 then error("case ids must be strings")
      elif ([$cases[] | .id | strings | select(length == 0)] | length) != 0 then error("case ids must not be empty")
      elif ([$cases[].id] | unique | length) != 200 then error("case ids must be unique")
      else [$cases[].id]
      end
  ' "$FULL200_BENCHMARK")"; then
    echo "Invalid Full-200 benchmark: $FULL200_BENCHMARK" >&2
    exit 2
  fi
  if ! full200_case_lines="$(jq -er '.[]' <<<"$full200_case_ids_json")"; then
    echo "Failed to read Full-200 case IDs: $FULL200_BENCHMARK" >&2
    exit 2
  fi
  mapfile -t full200_case_ids <<<"$full200_case_lines"
  if [[ "${#full200_case_ids[@]}" -ne 200 ]]; then
    echo "Invalid Full-200 case count after parsing: ${#full200_case_ids[@]}" >&2
    exit 2
  fi
  for case_id in "${full200_case_ids[@]}"; do
    case_args+=(--case "$case_id")
  done
  expected_case_ids_json="$full200_case_ids_json"
  expected_cases=200
else
  echo "Usage: $0 [pilot|full200]" >&2
  exit 2
fi

mkdir -p "$TMPDIR" "$BASE/logs"

profiles=(hybrid_current service_only)
total_api_concurrency=$((PROFILE_CONCURRENCY * ${#profiles[@]}))
if [[ "$total_api_concurrency" -ne 16 ]]; then
  echo "Total API concurrency must be 16, got $total_api_concurrency" >&2
  exit 2
fi

expected_profile_metadata_json() {
  local profile="$1"
  case "$profile" in
    hybrid_current)
      printf '%s\n' '{"prompt_profile":"hybrid_current","profile_version":"plan2-prompt-profile-v2","removed_algorithm_templates":false,"strategy_hint_policy":"benchmark_strategy","generation_prompt_sha256":"3e8d7b6bdde69e0889b6c440235971a085d5b1a56b52872135d8fd7b669bda71","repair_prompt_sha256":"fda3bc7c61d8aa274f9e581f7f8a2c3d5d6b7f3ab37f8dd1cbe11e081e0a3ac3"}'
      ;;
    service_only)
      printf '%s\n' '{"prompt_profile":"service_only","profile_version":"plan2-prompt-profile-v2","removed_algorithm_templates":true,"strategy_hint_policy":"removed","generation_prompt_sha256":"6271846c0a2491434f08dc48326fbfb34b0a3d79de62f2f344fd1adb58a67c47","repair_prompt_sha256":"54fbf417c774566e7b0ae85eded6cd67550fc83a8eb94b7d6c9641d058896899"}'
      ;;
    *)
      return 2
      ;;
  esac
}

report_matches_protocol() {
  local report_path="$1"
  local profile="$2"
  local profile_metadata_json
  [[ -f "$report_path" ]] || return 1
  profile_metadata_json="$(expected_profile_metadata_json "$profile")" || return 1
  jq -e \
    --arg model "$MODEL" \
    --arg profile "$profile" \
    --argjson expected "$expected_cases" \
    --argjson concurrency "$PROFILE_CONCURRENCY" \
    --argjson expected_case_ids "$expected_case_ids_json" \
    --argjson expected_profile_metadata "$profile_metadata_json" \
    --slurpfile frozen "$FULL200_BENCHMARK" \
    '
      (.total == $expected)
      and (.config.prompt_profile == $profile)
      and (.config.prompt_profile_metadata == $expected_profile_metadata)
      and (.config.model == $model)
      and (.config.sample == 0)
      and (.config.solutions == 2)
      and (.config.max_rounds == 2)
      and (.config.max_candidates == 2)
      and (.config.timeout_s == 3000)
      and (.config.strict_warnings == true)
      and (.config.browser_smoke == false)
      and (.config.teaching_enrichment == true)
      and (.config.write_each == true)
      and (.config.concurrency == $concurrency)
      and (.config.benchmark_condition == "algolab_full")
      and (.config.case_set == "deterministic")
      and (.config.language == "zh")
      and (.config.llm.timeout_s == 600)
      and (.config.llm.max_tokens == 32768)
      and (.config.llm.json_retries == 3)
      and (.config.llm.api_retries == 1)
      and (.config.llm.sdk_max_retries == 0)
      and (.config.llm.json_temperature == 0.2)
      and (.results | type == "array")
      and (.results | length == $expected)
      and (
        [.results[].case_id] as $case_ids
        | ([$case_ids[] | select(type != "string")] | length) == 0
        and ([$case_ids[] | strings | select(length == 0)] | length) == 0
        and (($case_ids | unique | length) == $expected)
        and (($case_ids | sort) == ($expected_case_ids | sort))
      )
      and (
        ($frozen[0].cases | map({key: .id, value: .}) | from_entries) as $frozen_by_id
        | all(
            .results[];
            . as $result
            | ($frozen_by_id[$result.case_id]) as $case
            | ($case != null)
              and ($result.problem == $case.problem)
              and ($result.strategy == $case.strategy)
              and ($result.sample_index == 0)
              and ($result.input_data == $case.samples[0].input_data)
              and ($result.expected == $case.samples[0].expected)
              and (
                if $result.ok == true then
                  (($result.variants | type) == "array")
                  and (($result.variants | length) == 2)
                  and ($result.release_gate.release_ready == true)
                  and ($result.release_gate.multi_solution_ready == true)
                else true
                end
              )
          )
      )
    ' "$report_path" >/dev/null
}

report_has_infrastructure_failure() {
  local report_path="$1"
  jq -e \
    --argjson infrastructure_types '["configuration","runner_error","api_transport","infrastructure_timeout"]' \
    '
      any(
        .results[]?;
        (.failure_type // "") as $failure_type
        | (($infrastructure_types | index($failure_type)) != null)
      )
    ' "$report_path" >/dev/null
}

write_invalid_marker() {
  local output_dir="$1"
  local profile="$2"
  local benchmark_status="$3"
  local reason="$4"
  local report_path="$5"
  local marker_path="$output_dir/invalid_run.json"
  local temporary_path="${marker_path}.tmp.$$"
  mkdir -p "$output_dir"
  jq -n \
    --arg schema_version "plan2-invalid-run-v1" \
    --arg reason "$reason" \
    --arg profile "$profile" \
    --arg mode "$MODE" \
    --argjson benchmark_status "$benchmark_status" \
    --arg report_path "$report_path" \
    '{
      schema_version: $schema_version,
      reason: $reason,
      profile: $profile,
      mode: $mode,
      benchmark_status: $benchmark_status,
      report_path: $report_path
    }' >"$temporary_path"
  mv "$temporary_path" "$marker_path"
}

profile_preflight_state() {
  local profile="$1"
  local output_dir="$BASE/$MODE/$profile"
  local report_path="$output_dir/llm_benchmark_report.json"
  local invalid_marker="$output_dir/invalid_run.json"
  local first_output=""
  if [[ -f "$invalid_marker" ]]; then
    printf '%s\n' "invalid"
    return 0
  fi
  if [[ -f "$report_path" ]]; then
    if ! report_matches_protocol "$report_path" "$profile"; then
      write_invalid_marker "$output_dir" "$profile" null "protocol_mismatch" "$report_path"
      echo "Refusing to overwrite incomplete report: $report_path" >&2
      printf '%s\n' "invalid"
      return 0
    fi
    if report_has_infrastructure_failure "$report_path"; then
      write_invalid_marker "$output_dir" "$profile" null "infrastructure_failure" "$report_path"
      echo "Refusing infrastructure-contaminated report: $report_path" >&2
      printf '%s\n' "invalid"
      return 0
    fi
    printf '%s\n' "complete"
    return 0
  fi
  if [[ -e "$output_dir" ]]; then
    if [[ ! -d "$output_dir" ]]; then
      first_output="$output_dir"
    else
      first_output="$(find "$output_dir" -mindepth 1 -maxdepth 1 -print -quit)"
    fi
  fi
  if [[ -n "$first_output" ]]; then
    write_invalid_marker "$output_dir" "$profile" null "partial_output" "$report_path"
    echo "Refusing partial output without report: profile=$profile output=$first_output" >&2
    printf '%s\n' "invalid"
    return 0
  fi
  printf '%s\n' "missing"
}

run_profile() {
  local profile="$1"
  local output_dir="$BASE/$MODE/$profile"
  local log_path="$BASE/logs/${MODE}_${profile}.log"
  local report_path="$output_dir/llm_benchmark_report.json"
  local invalid_marker="$output_dir/invalid_run.json"
  if [[ -f "$invalid_marker" ]]; then
    echo "Refusing invalidated profile: profile=$profile marker=$invalid_marker" >&2
    return 5
  fi
  if [[ -f "$report_path" ]]; then
    if ! report_matches_protocol "$report_path" "$profile"; then
      write_invalid_marker "$output_dir" "$profile" null "protocol_mismatch" "$report_path"
      echo "Refusing to overwrite incomplete report: $report_path" >&2
      return 3
    fi
    if report_has_infrastructure_failure "$report_path"; then
      write_invalid_marker "$output_dir" "$profile" null "infrastructure_failure" "$report_path"
      echo "Refusing infrastructure-contaminated report: $report_path" >&2
      return 3
    fi
    echo "SKIP complete profile=$profile report=$report_path"
    return 0
  fi
  mkdir -p "$output_dir"
  echo "START mode=$MODE profile=$profile expected_cases=$expected_cases profile_concurrency=$PROFILE_CONCURRENCY total_api_concurrency=$total_api_concurrency"
  local benchmark_status=0
  if "$PYTHON" "$ROOT/scripts/run_llm_benchmark.py" \
      "${case_args[@]}" \
      --sample 0 \
      --solutions 2 \
      --max-rounds 2 \
      --max-candidates 2 \
      --timeout-s 3000 \
      --strict-warnings \
      --no-browser-smoke \
      --teaching-enrichment \
      --write-each \
      --concurrency "$PROFILE_CONCURRENCY" \
      --case-set deterministic \
      --language zh \
      --case-overrides "$FULL200_BENCHMARK" \
      --prompt-profile "$profile" \
      --condition algolab_full \
      --output-dir "$output_dir" \
      >"$log_path" 2>&1; then
    benchmark_status=0
  else
    benchmark_status=$?
  fi
  if [[ "$benchmark_status" -gt 1 ]]; then
    write_invalid_marker "$output_dir" "$profile" "$benchmark_status" "benchmark_exit_status" "$report_path"
    echo "Benchmark infrastructure exit: profile=$profile status=$benchmark_status report=$report_path" >&2
    return 4
  fi
  if ! report_matches_protocol "$report_path" "$profile"; then
    write_invalid_marker "$output_dir" "$profile" "$benchmark_status" "protocol_mismatch" "$report_path"
    echo "Benchmark did not produce a complete protocol-matching report: profile=$profile status=$benchmark_status report=$report_path" >&2
    return 4
  fi
  if report_has_infrastructure_failure "$report_path"; then
    write_invalid_marker "$output_dir" "$profile" "$benchmark_status" "infrastructure_failure" "$report_path"
    echo "Benchmark report contains infrastructure failure: profile=$profile status=$benchmark_status report=$report_path" >&2
    return 4
  fi
  echo "COMPLETE profile=$profile benchmark_status=$benchmark_status report=$report_path"
  return 0
}

profile_states=()
for profile in "${profiles[@]}"; do
  profile_states+=("$(profile_preflight_state "$profile")")
done

status=0
if [[ "${profile_states[0]}" == "missing" && "${profile_states[1]}" == "missing" ]]; then
  pids=()
  for profile in "${profiles[@]}"; do
    run_profile "$profile" &
    pids+=("$!")
  done
  for pid in "${pids[@]}"; do
    if ! wait "$pid"; then
      status=1
    fi
  done
elif [[ "${profile_states[0]}" == "complete" && "${profile_states[1]}" == "complete" ]]; then
  for profile in "${profiles[@]}"; do
    echo "SKIP complete profile=$profile report=$BASE/$MODE/$profile/llm_benchmark_report.json"
  done
else
  echo "Pair preflight rejected mode=$MODE states=${profile_states[*]}" >&2
  exit 6
fi

for profile in "${profiles[@]}"; do
  report="$BASE/$MODE/$profile/llm_benchmark_report.json"
  invalid_marker="$BASE/$MODE/$profile/invalid_run.json"
  if [[ ! -f "$invalid_marker" ]] && report_matches_protocol "$report" "$profile"; then
    jq -c '{profile:.config.prompt_profile,total,passed,failed,pass_rate}' "$report"
  fi
done

exit "$status"
