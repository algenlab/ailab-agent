#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
IMAGE="${WEBGEN_IMAGE:-mcr.microsoft.com/playwright/python:v1.59.0-noble}"
WEBGEN_ROOT="${WEBGEN_ROOT:-/tmp/webgen-agent-audit}"
PYDEPS_ROOT="${PYDEPS_ROOT:-/tmp/webgen-pydeps}"
CHROMEDRIVER="${CHROMEDRIVER:-/tmp/webgen-chromedriver150/chromedriver-linux64/chromedriver}"
DATA_PATH="${DATA_PATH:-$ROOT/benchmark/external_baseline_all200_sample0_webgen.jsonl}"
MAX_ITER="${MAX_ITER:-5}"
NUM_WORKERS="${NUM_WORKERS:-8}"
EVAL_TAG="${EVAL_TAG:-all200_sample0_budget5}"

: "${ALGOLAB_LLM_API_KEY:?Set ALGOLAB_LLM_API_KEY in the environment}"
: "${ALGOLAB_LLM_BASE_URL:?Set ALGOLAB_LLM_BASE_URL in the environment}"

export ANTHROPIC_VLM_API_KEY="${ALGOLAB_LLM_API_KEY}"
export ANTHROPIC_VLM_BASE_URL="${ALGOLAB_LLM_BASE_URL}"
export OPENAILIKE_API_KEY="${ALGOLAB_LLM_API_KEY}"
export OPENAILIKE_BASE_URL="${ALGOLAB_LLM_BASE_URL}"
export OPENAILIKE_FB_API_KEY="${ALGOLAB_LLM_API_KEY}"
export OPENAILIKE_FB_BASE_URL="${ALGOLAB_LLM_BASE_URL}"
export OPENAILIKE_VLM_API_KEY="${ALGOLAB_LLM_API_KEY}"
export OPENAILIKE_VLM_BASE_URL="${ALGOLAB_LLM_BASE_URL}"

for path in "$WEBGEN_ROOT/src/infer_batch.py" "$PYDEPS_ROOT" "$CHROMEDRIVER" "$DATA_PATH"; do
  if [[ ! -e "$path" ]]; then
    echo "Missing required path: $path" >&2
    exit 1
  fi
done

sudo -n docker run --rm --shm-size=4g \
  -v "$ROOT:$ROOT" \
  -v "$WEBGEN_ROOT:/opt/WebGen-Agent:ro" \
  -v "$PYDEPS_ROOT:/tmp/webgen-pydeps:ro" \
  -v "$CHROMEDRIVER:/usr/local/bin/chromedriver:ro" \
  -e PYTHONPATH=/tmp/webgen-pydeps:/opt/WebGen-Agent/src \
  -e ANTHROPIC_VLM_API_KEY \
  -e ANTHROPIC_VLM_BASE_URL \
  -e OPENAILIKE_API_KEY \
  -e OPENAILIKE_BASE_URL \
  -e OPENAILIKE_FB_API_KEY \
  -e OPENAILIKE_FB_BASE_URL \
  -e OPENAILIKE_VLM_API_KEY \
  -e OPENAILIKE_VLM_BASE_URL \
  -e HTTP_PROXY \
  -e HTTPS_PROXY \
  -e NO_PROXY \
  --entrypoint bash "$IMAGE" -lc "
set -euo pipefail
cd /opt/WebGen-Agent
$PYTHON src/infer_batch.py \\
  --model DeepSeek-V4-Pro \\
  --vlm_model gemini-3-flash-preview \\
  --fb_model DeepSeek-V4-Pro \\
  --data-path '$DATA_PATH' \\
  --workspace-root '$ROOT/output/external_baselines/webgen/workspaces' \\
  --log-root '$ROOT/output/external_baselines/webgen/logs' \\
  --eval-tag '$EVAL_TAG' \\
  --max-iter '$MAX_ITER' \\
  --num-workers '$NUM_WORKERS' \\
  --max-tokens 32768 \\
  --temperature 0.5 \\
  --overwrite
"
