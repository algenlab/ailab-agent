#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="python3"
IMAGE="iregistry.baidu-int.com/liyunhuan01/vibe-coding:latest"
OUT="$ROOT/output/external_baselines/htmlcure_all200_sample0"

mkdir -p "$OUT/logs"

for shard in $(seq 0 7); do
  sudo -n docker run --rm --shm-size=2g \
    -v /ssd1:/ssd1 \
    -v /tmp/htmlcure-audit:/opt/HTMLCure:ro \
    -v /tmp/htmlcure-pydeps:/tmp/htmlcure-pydeps:ro \
    -e PYTHONPATH=/tmp/htmlcure-pydeps:/opt/HTMLCure:$ROOT \
    -e ALGOLAB_LLM_SETTINGS_FILE="$ROOT/api_settings.json" \
    -e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    -e HTTP_PROXY=http://agent.baidu.com:8891 \
    -e HTTPS_PROXY=http://agent.baidu.com:8891 \
    -e NO_PROXY=oneapi-comate.baidu-int.com,baidu-int.com,localhost,127.0.0.1,baidu.com,baidubce.com,bj.bcebos.com,bfsu.edu.cn,tsinghua.edu.cn \
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
