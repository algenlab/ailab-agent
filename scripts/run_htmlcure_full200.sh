#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
IMAGE="${ALGOLAB_PLAYWRIGHT_IMAGE:-mcr.microsoft.com/playwright/python:v1.59.0-noble}"
OUT="$ROOT/output/external_baselines/htmlcure_all200_sample0"

mkdir -p "$OUT/logs"

for shard in $(seq 0 7); do
  sudo -n docker run --rm --shm-size=2g \
    -v "$ROOT:$ROOT" \
    -v /tmp/htmlcure-audit:/opt/HTMLCure:ro \
    -v /tmp/htmlcure-pydeps:/tmp/htmlcure-pydeps:ro \
    -e PYTHONPATH=/tmp/htmlcure-pydeps:/opt/HTMLCure:$ROOT \
    -e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    -e ALGOLAB_LLM_API_KEY \
    -e ALGOLAB_LLM_BASE_URL \
    -e ALGOLAB_LLM_MODEL \
    -e HTTP_PROXY \
    -e HTTPS_PROXY \
    -e NO_PROXY \
    --entrypoint bash "$IMAGE" -lc "
set -euo pipefail
$PYTHON '$ROOT/scripts/run_htmlcure_baseline.py' \\
  --htmlcure-root /opt/HTMLCure \\
  --htmlcure-commit 18d68e8f1e5c2bcef7f3c00bcab3147e2a99d4db \\
  --direct-report '$ROOT/output/experiments/algotutorgen_full_200_20260706/direct_html_expected_visible/llm_benchmark_report.json' \\
  --manifest '$ROOT/benchmark/external_baseline_all200_sample0.json' \\
  --output-dir '$OUT/shard_$shard' \\
  --shard-id '$shard' --num-shards 8 \\
  --repair-model DeepSeek-V4-Pro \\
  --evaluator-model gemini-3-flash-preview \\
  --max-iterations 1 --candidates 1 --max-screenshots 8 --record-timeout 600
" >"$OUT/logs/shard_$shard.log" 2>&1 &
done

wait
