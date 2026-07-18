# AlgoTutorGen Showcase

这是 AlgoTutorGen 的静态成果展示站，集中展示方法链、Full-200 冻结结果、契约审计证据、真实浏览器产物和论文入口。

从仓库根目录启动本地服务，确保真实 HTML、PDF 和结果文档的相对链接可用：

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m http.server 4173
```

打开：

```text
http://127.0.0.1:4173/showcase/
```

运行静态完整性检查：

```bash
node showcase/tests/validate-showcase.mjs
node --check showcase/app.js
```

站点不依赖外部 CDN 或构建工具。方法指标来自 `docs/EXPERIMENT_RESULTS.md`；截图和论文图从 `output/current_flow_5cases_screenshots/` 与 `latex/figures/` 原样复制到 `showcase/assets/`。
