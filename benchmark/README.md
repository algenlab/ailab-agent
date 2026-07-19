# AlgoLab Benchmark Reproducibility

本目录记录可复现实验入口。运行命令时必须在项目根目录使用固定解释器：

```bash
python3
```

## Deterministic Benchmark

确定性路径不调用 LLM，输入来自 `benchmark/cases.py` 的 `benchmark_cases()`。当前 deterministic benchmark 为 200 cases / 646 samples，其中 `family_core=62 cases / 222 samples`，`expansion=138 cases / 424 samples`。

当前保留两个 JSON 版本：

- `benchmark/algo_learn_env_benchmark.json`：内部全量版，包含 plan 核心字段、可执行 solver/tracker/verifier、Stage2 visual brief、hint/misconception、实验 gate/oracle bookkeeping 等完整元数据。
- `benchmark/algo_learn_env_benchmark_core.json`：plan-aligned core 版，由 `scripts/export_algo_learn_env_core_benchmark.py` 从全量版导出；每题仅保留 20 个字段，包括 plan 明确的 task-bundle 字段，以及 `id/title/problem/samples/code/tracker_code/verifier_code` 等可验证所需字段。

一条命令运行本地确定性质量检查：

```bash
python3 scripts/run_quality_checks.py
```

浏览器截图或真实 DOM 验证需要 Playwright 兼容容器，并且现在只在需要浏览器证据时显式运行：

```bash
bash scripts/run_browser_smoke_container.sh
```

原因：当前宿主机 glibc 2.17 不能运行 Playwright 自带 node。执行 AI 不应把该宿主机环境失败当作代码失败。默认镜像为当前机器已缓存的 `mcr.microsoft.com/playwright/python:v1.59.0-noble`；外部 CI 可通过 `ALGOLAB_PLAYWRIGHT_IMAGE` 覆盖。

容器命令要求能访问 Docker daemon。脚本会优先使用普通 `docker`，失败后自动尝试 `sudo -n docker`；若两者都不可用，应切到有 Docker 权限的执行环境后再跑门禁。

常用输出：

- `output/dashboard/dashboard.json`
- `output/dashboard/index.html`
- `output/evaluation/evaluation_manifest.json`
- `output/evaluation/evaluation_report.json`

## LLM Benchmark

LLM 路径单独运行，需要通过环境变量或本地 ignored settings 文件配置模型：

- `ALGOLAB_LLM_BASE_URL`
- `ALGOLAB_LLM_API_KEY`
- `ALGOLAB_LLM_MODEL`
- `ALGOLAB_LLM_TIMEOUT_S`
- `ALGOLAB_LLM_MAX_TOKENS`
- `ALGOLAB_LLM_JSON_RETRIES`
- `ALGOLAB_LLM_SETTINGS_FILE`

运行示例：

```bash
python3 scripts/run_llm_benchmark.py --output-dir output/llm_benchmark --condition algolab_full
```

按算法族分层抽样：

```bash
python3 scripts/run_llm_benchmark.py \
  --output-dir output/llm_benchmark \
  --condition algolab_full \
  --family array_pointer \
  --gate-layer family_core \
  --limit-per-family 1
```

分层配置位于 `benchmark/llm_family_sets.json`。默认 sample 0 作为 `seen_style`，sample 1 及之后样例作为 `unseen_style`，LLM benchmark 失败不会影响 deterministic release gate。

独立 unseen family evaluation：

```bash
python3 scripts/run_llm_benchmark.py \
  --output-dir output/llm_benchmark_unseen \
  --condition algolab_full \
  --case-set unseen \
  --limit-per-family 1
```

`benchmark/unseen_family_cases.json` 覆盖当前 strong family，只保存题目描述、family 元数据、样例输入和 expected output，不保存 deterministic `code`、`tracker_code` 或 `verifier_code`。unseen 运行仍走 LLM 生成、repair、校验和编译链路；报告中通过 `case_set=unseen` 与 `case_style=unseen_style` 区分独立未见题目。

常用输出：

- `output/llm_benchmark/llm_benchmark_report.json`
- `output/llm_benchmark/llm_benchmark_report.md`
- `output/llm_benchmark/family_summary.json`
- `output/llm_benchmark/llm_<case_id>_<sample_index>.json`
- `output/llm_benchmark/llm_<case_id>_<sample_index>.html`

## Package Manifest

生成结构化可复现包：

```bash
python3 scripts/build_reproducibility_package.py --output-dir output/reproducibility
```

该命令输出环境、模型配置入口、样例输入、运行命令和输出路径，并明确区分 deterministic benchmark 与 LLM benchmark。
