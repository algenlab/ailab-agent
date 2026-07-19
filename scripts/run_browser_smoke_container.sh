#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${ALGOLAB_PLAYWRIGHT_IMAGE:-iregistry.baidu-int.com/liyunhuan01/vibe-coding:latest}"
REQUIREMENTS="${ALGOLAB_BROWSER_SMOKE_REQUIREMENTS:-requirements-browser-smoke.txt}"
INSTALL_DEPS="${ALGOLAB_CONTAINER_INSTALL_DEPS:-0}"
USER_SPEC="${ALGOLAB_CONTAINER_USER:-$(id -u):$(id -g)}"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required for containerized browser smoke" >&2
  exit 127
fi

DOCKER_CMD=(docker)
if ! "${DOCKER_CMD[@]}" info >/dev/null 2>&1; then
  if command -v sudo >/dev/null 2>&1 && sudo -n docker info >/dev/null 2>&1; then
    DOCKER_CMD=(sudo -n docker)
  else
    echo "cannot access Docker daemon; add the current user to the docker group, run with passwordless sudo docker, or use a CI/container host with Docker access" >&2
    exit 126
  fi
fi

if [ "$#" -eq 0 ]; then
  CONTAINER_COMMAND="python scripts/capture_phase17_screenshots.py --output-dir output/phase17_screenshots"
else
  printf -v CONTAINER_COMMAND "%q " "$@"
fi

"${DOCKER_CMD[@]}" run --rm --init --ipc=host \
  --user "${USER_SPEC}" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PIP_DISABLE_PIP_VERSION_CHECK=1 \
  -e ALGOLAB_HOST_PROJECT_ROOT="${PROJECT_ROOT}" \
  -e ALGOLAB_CONTAINER_INSTALL_DEPS="${INSTALL_DEPS}" \
  -e ALGOLAB_BROWSER_SMOKE_REQUIREMENTS="${REQUIREMENTS}" \
  -e http_proxy="${http_proxy:-}" \
  -e https_proxy="${https_proxy:-}" \
  -e no_proxy="${no_proxy:-}" \
  -e HTTP_PROXY="${HTTP_PROXY:-}" \
  -e HTTPS_PROXY="${HTTPS_PROXY:-}" \
  -e NO_PROXY="${NO_PROXY:-}" \
  -e ALGOLAB_LLM_MODEL="${ALGOLAB_LLM_MODEL:-}" \
  -e ALGOLAB_LLM_BASE_URL="${ALGOLAB_LLM_BASE_URL:-}" \
  -e ALGOLAB_LLM_API_KEY="${ALGOLAB_LLM_API_KEY:-}" \
  -e ALGOLAB_LLM_TIMEOUT_S="${ALGOLAB_LLM_TIMEOUT_S:-}" \
  -e ALGOLAB_LLM_MAX_TOKENS="${ALGOLAB_LLM_MAX_TOKENS:-}" \
  -e ALGOLAB_LLM_JSON_RETRIES="${ALGOLAB_LLM_JSON_RETRIES:-}" \
  -e ALGOLAB_LLM_API_RETRIES="${ALGOLAB_LLM_API_RETRIES:-}" \
  -e ALGOLAB_LLM_API_RETRY_DELAY_S="${ALGOLAB_LLM_API_RETRY_DELAY_S:-}" \
  -e ALGOLAB_VLM_MODEL="${ALGOLAB_VLM_MODEL:-}" \
  -e ALGOLAB_VLM_TIMEOUT_S="${ALGOLAB_VLM_TIMEOUT_S:-}" \
  -e ALGOLAB_VLM_MAX_TOKENS="${ALGOLAB_VLM_MAX_TOKENS:-}" \
  -v "${PROJECT_ROOT}:/work" \
  -w /work \
  "${IMAGE}" \
  bash -lc "
    set -euo pipefail
    python -m venv --system-site-packages /tmp/algolab-browser-smoke-venv
    . /tmp/algolab-browser-smoke-venv/bin/activate
    if [ \"\${ALGOLAB_CONTAINER_INSTALL_DEPS}\" != \"0\" ]; then
      python -m pip install --no-cache-dir -r \"\${ALGOLAB_BROWSER_SMOKE_REQUIREMENTS}\"
    fi
    ${CONTAINER_COMMAND}
  "
