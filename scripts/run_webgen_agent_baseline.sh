#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="/ssd1/liaokunpeng/agent-py310-cu/bin/python3"
IMAGE="iregistry.baidu-int.com/liyunhuan01/vibe-coding:latest"
WEBGEN_ROOT="${WEBGEN_ROOT:-/tmp/webgen-agent-audit}"
PYDEPS_ROOT="${PYDEPS_ROOT:-/tmp/webgen-pydeps}"
CHROMEDRIVER="${CHROMEDRIVER:-/tmp/webgen-chromedriver150/chromedriver-linux64/chromedriver}"
DATA_PATH="${DATA_PATH:-$ROOT/benchmark/external_baseline_all200_sample0_webgen.jsonl}"
MAX_ITER="${MAX_ITER:-5}"
NUM_WORKERS="${NUM_WORKERS:-8}"
EVAL_TAG="${EVAL_TAG:-all200_sample0_budget5}"

for path in "$WEBGEN_ROOT/src/infer_batch.py" "$PYDEPS_ROOT" "$CHROMEDRIVER" "$DATA_PATH" "$ROOT/api_settings.json"; do
  if [[ ! -e "$path" ]]; then
    echo "Missing required path: $path" >&2
    exit 1
  fi
done

sudo -n docker run --rm --shm-size=4g \
  -v /ssd1:/ssd1 \
  -v "$WEBGEN_ROOT:/opt/WebGen-Agent:ro" \
  -v "$PYDEPS_ROOT:/tmp/webgen-pydeps:ro" \
  -v "$CHROMEDRIVER:/usr/local/bin/chromedriver:ro" \
  -e PYTHONPATH=/tmp/webgen-pydeps:/opt/WebGen-Agent/src \
  -e ANTHROPIC_VLM_API_KEY=unused \
  -e ANTHROPIC_VLM_BASE_URL=https://api.anthropic.com \
  -e HTTP_PROXY=http://agent.baidu.com:8891 \
  -e HTTPS_PROXY=http://agent.baidu.com:8891 \
  -e NO_PROXY=oneapi-comate.baidu-int.com,baidu-int.com,localhost,127.0.0.1,baidu.com,baidubce.com,bj.bcebos.com,bfsu.edu.cn,tsinghua.edu.cn \
  --entrypoint bash "$IMAGE" -lc "
set -euo pipefail
export OPENAILIKE_API_KEY=\"\$($PYTHON -c 'import json; print(json.load(open(\"$ROOT/api_settings.json\"))[\"api_key\"])')\"
export OPENAILIKE_BASE_URL=https://oneapi-comate.baidu-int.com/v1
export OPENAILIKE_FB_API_KEY=\"\$OPENAILIKE_API_KEY\"
export OPENAILIKE_FB_BASE_URL=\"\$OPENAILIKE_BASE_URL\"
export OPENAILIKE_VLM_API_KEY=\"\$OPENAILIKE_API_KEY\"
export OPENAILIKE_VLM_BASE_URL=\"\$OPENAILIKE_BASE_URL\"
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
