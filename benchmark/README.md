# AlgoLab Benchmark Reproducibility

本目录记录可复现实验入口。运行命令时必须在项目根目录使用固定解释器：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3
```

## Deterministic Benchmark

确定性路径不调用 LLM，输入来自 `tests/benchmark_cases.py`，题目清单见 `benchmark/benchmark_cases_list.md`。

一条命令运行本地确定性质量检查：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_quality_checks.py
```

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
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/run_llm_benchmark.py --output-dir output/llm_benchmark --condition algolab_full
```

常用输出：

- `output/llm_benchmark/llm_benchmark_report.json`
- `output/llm_benchmark/llm_benchmark_report.md`
- `output/llm_benchmark/llm_<case_id>_<sample_index>.json`
- `output/llm_benchmark/llm_<case_id>_<sample_index>.html`

## Package Manifest

生成结构化可复现包：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 scripts/build_reproducibility_package.py --output-dir output/reproducibility
```

该命令输出环境、模型配置入口、样例输入、运行命令和输出路径，并明确区分 deterministic benchmark 与 LLM benchmark。
