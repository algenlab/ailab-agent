#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/output/external_baselines/htmlcure_all200_sample0"

cleanup_once() {
  for trace in "$OUT"/shard_*/traces/*.json; do
    [[ -e "$trace" ]] || continue
    shard_dir="$(dirname "$(dirname "$trace")")"
    case_id="$(basename "$trace" .json)"
    sudo -n rm -rf -- \
      "$shard_dir/htmlcure_workspace/reports/${case_id}_original" \
      "$shard_dir/htmlcure_workspace/reports/${case_id}_repair_1_repair"
  done
}

while pgrep -f '[r]un_htmlcure_full200.sh' >/dev/null; do
  cleanup_once
  sleep 60
done
cleanup_once
