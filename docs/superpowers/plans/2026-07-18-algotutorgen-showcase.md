# AlgoTutorGen Showcase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a polished, responsive, self-contained project showcase that presents AlgoTutorGen's method, frozen Full-200 results, contract evidence, real browser artifacts, and paper resources.

**Architecture:** Add a dependency-free static site under `showcase/` with semantic HTML, a single design-system stylesheet, and one progressive-enhancement JavaScript module. Keep all comparison values in one JavaScript data structure, copy selected real repository images into a local asset directory, and link back to authoritative HTML/PDF/Markdown artifacts in the repository.

**Tech Stack:** HTML5, CSS3, native ES2020 JavaScript, Node.js static validation script, local HTTP server, agent-browser.

---

## File map

- Create `showcase/index.html`: semantic page structure, all readable fallback content, navigation, chart and gallery mount points.
- Create `showcase/styles.css`: design tokens, layout, motion, responsive rules, focus states, print/reduced-motion behavior.
- Create `showcase/app.js`: frozen results data, chart rendering, gate selection, gallery selection, navigation state, counters, canvas trace animation.
- Create `showcase/tests/validate-showcase.mjs`: zero-dependency static contract and asset/link checks.
- Create `showcase/README.md`: run and verification commands plus data provenance.
- Create `showcase/design/concept-reference.svg`: local visual extraction of the five approved Image Gen section concepts for final fidelity comparison.
- Create `showcase/assets/*.png`: copied real screenshots and paper figures only.

### Task 1: Establish the failing showcase contract

**Files:**
- Create: `showcase/tests/validate-showcase.mjs`

- [ ] **Step 1: Write the static contract test before production files exist**

```js
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const requiredFiles = ['index.html', 'styles.css', 'app.js', 'README.md'];
const requiredAssets = [
  'design/concept-reference.svg',
  'assets/binary-search.png',
  'assets/dijkstra-shortest-path.png',
  'assets/unique-paths.png',
  'assets/trie-prefix-match.png',
  'assets/system-detailed-architecture.png',
  'assets/method-paradigm-comparison.png',
];

const failures = [];
for (const file of [...requiredFiles, ...requiredAssets]) {
  if (!fs.existsSync(path.join(root, file))) failures.push(`missing ${file}`);
}

if (fs.existsSync(path.join(root, 'index.html'))) {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  for (const token of [
    '从可执行语义到可验证的交互式算法导师',
    '同一浏览器合同下，谁真正完成了任务？',
    '不是截图，是可以打开、播放、作答的 HTML',
    'AlgoTutorGen: Contract-Guided Compositional Synthesis',
    '55,108', '2,198', '1,561,298',
  ]) {
    if (!html.includes(token)) failures.push(`missing copy: ${token}`);
  }
  for (const id of ['method', 'results', 'artifacts', 'paper']) {
    if (!html.includes(`id="${id}"`)) failures.push(`missing section #${id}`);
  }
  if (!html.includes('prefers-reduced-motion')) failures.push('missing reduced-motion bootstrap');
}

if (fs.existsSync(path.join(root, 'app.js'))) {
  const js = fs.readFileSync(path.join(root, 'app.js'), 'utf8');
  const expectedPairs = [
    ['AlgoTutorGen', 'machineOk: 198'],
    ['Direct HTML', 'machineOk: 98'],
    ['WebGen-Agent', 'machineOk: 45'],
    ['Direct + HTMLCure', 'machineOk: 40'],
    ['Direct-BrowserRepair', 'machineOk: 106'],
  ];
  for (const [name, value] of expectedPairs) {
    if (!js.includes(name) || !js.includes(value)) failures.push(`missing frozen result ${name} ${value}`);
  }
  for (const behavior of ['renderMetric', 'selectArtifact', 'selectGate', 'setupTraceCanvas']) {
    if (!js.includes(behavior)) failures.push(`missing behavior ${behavior}`);
  }
}

if (failures.length) {
  console.error(failures.join('\n'));
  process.exit(1);
}
console.log('showcase static contract: PASS');
```

- [ ] **Step 2: Run the test and verify RED**

Run: `node showcase/tests/validate-showcase.mjs`

Expected: exit 1 with at least `missing index.html`, proving the contract detects the absent site.

- [ ] **Step 3: Commit the test**

```bash
git add showcase/tests/validate-showcase.mjs
git commit -m "test: define showcase content contract"
```

### Task 2: Add real assets and semantic fallback content

**Files:**
- Create: `showcase/assets/binary-search.png`
- Create: `showcase/assets/dijkstra-shortest-path.png`
- Create: `showcase/assets/unique-paths.png`
- Create: `showcase/assets/trie-prefix-match.png`
- Create: `showcase/assets/system-detailed-architecture.png`
- Create: `showcase/assets/method-paradigm-comparison.png`
- Create: `showcase/design/concept-reference.svg`
- Create: `showcase/index.html`
- Create: `showcase/README.md`

- [ ] **Step 1: Copy the selected real repository assets without transforming them**

```bash
mkdir -p showcase/assets
cp output/current_flow_5cases_screenshots/binary_search_desktop.png showcase/assets/binary-search.png
cp output/current_flow_5cases_screenshots/dijkstra_shortest_path_desktop.png showcase/assets/dijkstra-shortest-path.png
cp output/current_flow_5cases_screenshots/unique_paths_desktop.png showcase/assets/unique-paths.png
cp output/current_flow_5cases_screenshots/trie_prefix_match_string_desktop.png showcase/assets/trie-prefix-match.png
cp latex/figures/system-detailed-architecture.png showcase/assets/system-detailed-architecture.png
cp latex/figures/method-paradigm-comparison.png showcase/assets/method-paradigm-comparison.png
```

- [ ] **Step 2: Create semantic `index.html` with complete no-JavaScript content**

The document must contain:

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="AlgoTutorGen：从可执行语义到可验证交互式算法导师。">
  <title>AlgoTutorGen · Contract Observatory</title>
  <link rel="stylesheet" href="./styles.css">
  <script>document.documentElement.classList.add('js');if(matchMedia('(prefers-reduced-motion: reduce)').matches)document.documentElement.classList.add('reduce-motion');</script>
</head>
<body>
  <a class="skip-link" href="#main">跳到正文</a>
  <header class="site-header">
    <a class="brand" href="#main" aria-label="AlgoTutorGen 首页">ATG <span>AlgoTutorGen</span></a>
    <nav class="desktop-nav" aria-label="主要导航">
      <a href="#method">方法</a><a href="#results">结果</a><a href="#artifacts">产物</a><a href="#paper">论文</a>
    </nav>
    <a class="header-action" href="#artifacts">浏览产物</a>
  </header>
  <main id="main">
    <section class="hero" aria-labelledby="hero-title">
      <div><h1 id="hero-title">从可执行语义到可验证的交互式算法导师</h1><p>Contract-guided synthesis from executable specs to trustworthy browser artifacts.</p><a href="#results">查看实验结果</a><a href="#artifacts">打开真实产物</a></div>
      <div class="contract-orbit" aria-label="Spec 到 Fixed Runtime 的契约链"><span>Spec</span><span>SemanticTrace</span><span>SceneGraph</span><span>Fixed Runtime</span><strong>198 / 200 <small>Machine OK</small></strong></div>
      <dl class="evidence-rail"><div><dt>tasks</dt><dd>200</dd></div><div><dt>algorithm families</dt><dd>23</dd></div><div><dt>inputs</dt><dd>646</dd></div></dl>
    </section>
    <section id="results" class="section results" aria-labelledby="results-title">
      <h2 id="results-title">同一浏览器合同下，谁真正完成了任务？</h2>
      <p>Machine OK requires all nine browser behaviors to pass together — it is a conjunction, not an average.</p>
      <div class="metric-switcher" aria-label="选择比较指标"></div>
      <div id="method-chart" aria-live="polite"></div>
      <table class="fallback-results"><caption>Full-200 冻结结果</caption><thead><tr><th>方法</th><th>Load</th><th>Answer</th><th>Interaction</th><th>Correct FB</th><th>Wrong FB</th><th>Hint</th><th>Show</th><th>Log</th><th>Mutation-free</th><th>Machine OK</th></tr></thead><tbody>
        <tr><th>AlgoTutorGen</th><td>200</td><td>200</td><td>200</td><td>199</td><td>198</td><td>200</td><td>200</td><td>200</td><td>200</td><td>198</td></tr>
        <tr><th>Direct-BrowserRepair</th><td>186</td><td>200</td><td>155</td><td>128</td><td>133</td><td>137</td><td>138</td><td>143</td><td>155</td><td>106</td></tr>
        <tr><th>Direct HTML</th><td>188</td><td>200</td><td>149</td><td>120</td><td>125</td><td>132</td><td>133</td><td>135</td><td>149</td><td>98</td></tr>
        <tr><th>WebGen-Agent</th><td>194</td><td>169</td><td>154</td><td>74</td><td>89</td><td>136</td><td>148</td><td>109</td><td>154</td><td>45</td></tr>
        <tr><th>Direct + HTMLCure（strict）</th><td>75</td><td>75</td><td>62</td><td>52</td><td>51</td><td>53</td><td>53</td><td>59</td><td>62</td><td>40</td></tr>
      </tbody></table>
    </section>
    <section id="method" class="section method" aria-labelledby="method-title">
      <h2 id="method-title">可验证性不是一句承诺，而是一条可执行链</h2>
      <div class="pipeline" aria-label="Problem 到 Interactive HTML 的方法链"></div>
      <div id="gate-detail" aria-live="polite"></div>
      <div class="evidence-grid"><article><strong>55,108 / 55,108</strong><p>跨表示帧一致</p></article><article><strong>2,198 / 2,198</strong><p>定义的语义违规被拒绝</p></article><article><strong>1,561,298 actions</strong><p>0 个观察到的教学状态污染反例</p></article></div>
    </section>
    <section id="artifacts" class="section artifacts" aria-labelledby="artifacts-title">
      <h2 id="artifacts-title">不是截图，是可以打开、播放、作答的 HTML</h2>
      <div class="artifact-stage"><img id="artifact-image" src="./assets/binary-search.png" alt="二分查找交互式算法导师截图"><div><h3 id="artifact-title">二分查找</h3><p id="artifact-family">Search · 13 frames</p><a id="artifact-link" href="../output/current_flow_5cases/demos/binary_search/stable.html" target="_blank" rel="noreferrer">打开真实产物</a></div></div>
      <div class="artifact-rail" role="tablist" aria-label="真实算法产物"></div>
    </section>
    <section id="paper" class="section paper" aria-labelledby="paper-title">
      <h2 id="paper-title">AlgoTutorGen: Contract-Guided Compositional Synthesis of Verifiable Interactive Algorithm Tutors</h2>
      <p>把答案、过程、界面与教学行为放在同一条可审计链上。</p>
      <a href="../docs/EXPERIMENT_RESULTS.md">阅读完整实验结果</a><a href="../latex/main.pdf" target="_blank" rel="noreferrer">查看论文 PDF</a>
      <p class="limitations">更多模型调用 · 长轨迹仍会膨胀 · 不声称真人学习效果</p>
    </section>
  </main>
  <footer class="site-footer"><strong>AlgoTutorGen</strong><nav aria-label="页脚导航"><a href="#method">方法</a><a href="#results">结果</a><a href="#artifacts">产物</a><a href="#paper">论文</a></nav><p>Built from executable evidence.</p></footer>
  <script type="module" src="./app.js"></script>
</body>
</html>
```

Expand this exact structure during implementation without changing its visible copy or section order. Add the remaining menu control, all contract nodes, the four artifact controls, and direct links to the other three `output/current_flow_5cases/demos/*/stable.html` files.

- [ ] **Step 3: Save the approved concept extraction as `showcase/design/concept-reference.svg`**

Create a 1600×1000 SVG overview with five horizontal dark bands that preserve the Image Gen concepts: asymmetric hero and cyan contract orbit; open five-row method chart; cyan canonical pipeline with purple teaching branch; large light browser media stage with four-item filmstrip; editorial paper title and evidence ledger. Use the exact palette tokens from the design spec and label each band with its approved heading. This file is documentation only and is not used as a production UI screenshot.

- [ ] **Step 4: Add `showcase/README.md`**

````markdown
# AlgoTutorGen Showcase

Serve the repository root so links to real HTML artifacts, PDFs, and result documents remain valid:

```bash
/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m http.server 4173
```

Open `http://127.0.0.1:4173/showcase/`.

The page is dependency-free. Frozen comparison values come from `docs/EXPERIMENT_RESULTS.md`; screenshots and diagrams are copied unchanged from `output/current_flow_5cases_screenshots/` and `latex/figures/`.
````

- [ ] **Step 5: Run the contract test**

Run: `node showcase/tests/validate-showcase.mjs`

Expected: still FAIL because `styles.css` and `app.js` are not present, while asset and HTML failures disappear.

- [ ] **Step 6: Commit semantic content and assets**

```bash
git add showcase/index.html showcase/README.md showcase/design/concept-reference.svg showcase/assets
git commit -m "feat: add showcase content and real artifacts"
```

### Task 3: Implement the visual system and responsive layout

**Files:**
- Create: `showcase/styles.css`

- [ ] **Step 1: Define the frozen tokens and base accessibility styles**

```css
:root {
  --ink-950: #07101f;
  --ink-900: #0b1728;
  --paper: #f2f7fb;
  --muted: #91a1b6;
  --cyan: #34e8d3;
  --cyan-soft: #7eeadf;
  --orange: #ff9a62;
  --violet: #a78bfa;
  --rule: rgba(160, 190, 220, .18);
  --display: Inter, "Noto Sans SC", "PingFang SC", system-ui, sans-serif;
  --mono: "IBM Plex Mono", "SFMono-Regular", Consolas, monospace;
  --page: min(1440px, calc(100vw - 64px));
}
* { box-sizing: border-box; }
html { color-scheme: dark; scroll-behavior: smooth; }
body { margin: 0; overflow-x: clip; background: var(--ink-950); color: var(--paper); font-family: var(--display); }
a, button { font: inherit; }
:focus-visible { outline: 2px solid var(--cyan); outline-offset: 4px; }
```

- [ ] **Step 2: Implement desktop section compositions**

Add explicit styles for `.site-header`, `.hero`, `.contract-orbit`, `.evidence-rail`, `.metric-switcher`, `.method-row`, `.pipeline`, `.teaching-branch`, `.evidence-grid`, `.artifact-stage`, `.artifact-rail`, `.paper-grid`, and `.site-footer`. Preserve open bands and rails; only `.browser-frame` and actual buttons may use prominent rounded containers.

- [ ] **Step 3: Add motion and responsive rules**

```css
@media (max-width: 1099px) {
  :root { --page: min(100% - 40px, 900px); }
  .hero-grid, .artifact-stage, .paper-grid { grid-template-columns: 1fr; }
  .pipeline-scroll { overflow-x: auto; }
}
@media (max-width: 719px) {
  :root { --page: min(100% - 32px, 640px); }
  .desktop-nav { display: none; }
  .menu-toggle { display: grid; }
  .hero-title { font-size: clamp(3rem, 16vw, 4.8rem); }
  .evidence-grid { grid-template-columns: 1fr; }
  .method-row { grid-template-columns: minmax(112px, 40%) 1fr; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; }
  #trace-canvas { display: none; }
}
```

- [ ] **Step 4: Run the static contract**

Run: `node showcase/tests/validate-showcase.mjs`

Expected: FAIL only on missing `app.js` and JavaScript behaviors.

- [ ] **Step 5: Commit styling**

```bash
git add showcase/styles.css
git commit -m "feat: style contract observatory showcase"
```

### Task 4: Implement data-driven interactions

**Files:**
- Create: `showcase/app.js`

- [ ] **Step 1: Add the single frozen result source**

```js
const methods = [
  { id: 'algotutorgen', name: 'AlgoTutorGen', short: 'AlgoTutorGen', load: 200, answer: 200, interaction: 200, correctFb: 199, wrongFb: 198, hint: 200, show: 200, log: 200, mutationFree: 200, machineOk: 198 },
  { id: 'browser-repair', name: 'Direct-BrowserRepair（1-call first-call control）', short: 'BrowserRepair', load: 186, answer: 200, interaction: 155, correctFb: 128, wrongFb: 133, hint: 137, show: 138, log: 143, mutationFree: 155, machineOk: 106 },
  { id: 'direct', name: 'Direct HTML', short: 'Direct HTML', load: 188, answer: 200, interaction: 149, correctFb: 120, wrongFb: 125, hint: 132, show: 133, log: 135, mutationFree: 149, machineOk: 98 },
  { id: 'webgen', name: 'WebGen-Agent', short: 'WebGen-Agent', load: 194, answer: 169, interaction: 154, correctFb: 74, wrongFb: 89, hint: 136, show: 148, log: 109, mutationFree: 154, machineOk: 45 },
  { id: 'htmlcure', name: 'Direct + HTMLCure（strict）', short: 'HTMLCure', load: 75, answer: 75, interaction: 62, correctFb: 52, wrongFb: 51, hint: 53, show: 53, log: 59, mutationFree: 62, machineOk: 40 },
];
```

- [ ] **Step 2: Implement `renderMetric(metricKey)`**

For every `.method-row`, set `--score` to `value / 2`, update the count to `${value}/200`, update the percentage to `${(value / 2).toFixed(1)}%`, and update `aria-valuenow`. Metric buttons must use `aria-pressed` and roving visible selection.

- [ ] **Step 3: Implement gate and gallery state**

```js
function selectGate(id) {
  document.querySelectorAll('[data-gate]').forEach((gate) => gate.classList.toggle('is-active', gate.dataset.gate === id));
  const detail = gateDetails[id];
  document.querySelector('#gate-detail').innerHTML = `<span>${detail.code}</span><strong>${detail.title}</strong><p>${detail.body}</p>`;
}

function selectArtifact(id) {
  const artifact = artifacts.find((item) => item.id === id);
  const image = document.querySelector('#artifact-image');
  image.src = artifact.image;
  image.alt = `${artifact.title} 交互式算法导师截图`;
  document.querySelector('#artifact-title').textContent = artifact.title;
  document.querySelector('#artifact-family').textContent = artifact.family;
  document.querySelector('#artifact-link').href = artifact.href;
  document.querySelectorAll('[data-artifact]').forEach((item) => item.setAttribute('aria-selected', String(item.dataset.artifact === id)));
}
```

- [ ] **Step 4: Implement navigation, counters, and trace canvas**

Use `IntersectionObserver` to mark active navigation and reveal elements. Counters must store final values in data attributes and immediately settle when reduced motion is active. `setupTraceCanvas()` must resize for device pixel ratio, draw only restrained lines and moving points, pause when the document is hidden, and skip initialization under reduced motion.

- [ ] **Step 5: Run GREEN contract**

Run: `node showcase/tests/validate-showcase.mjs`

Expected: `showcase static contract: PASS` with exit 0.

- [ ] **Step 6: Commit interactions**

```bash
git add showcase/app.js
git commit -m "feat: add showcase evidence interactions"
```

### Task 5: Browser verification and visual repair

**Files:**
- Modify: `showcase/index.html`
- Modify: `showcase/styles.css`
- Modify: `showcase/app.js`
- Create temporarily, then remove: `showcase/.qa/*`

- [ ] **Step 1: Start the repository-root server**

Run: `/ssd1/liaokunpeng/agent-py310-cu/bin/python3 -m http.server 4173`

Expected: server listens at `http://127.0.0.1:4173` and keeps running in a PTY session.

- [ ] **Step 2: Verify desktop behavior at 1440×1000**

Open `http://127.0.0.1:4173/showcase/`; check the console, hero composition, all navigation anchors, ten metric choices, five method rows, gate selection, four gallery entries, real artifact link, result document link, and PDF link. Save a full-page screenshot under `showcase/.qa/desktop.png`.

- [ ] **Step 3: Verify mobile behavior at 390×844**

Check the menu, hero line breaks, method rail, pipeline overflow, gallery controls, focus visibility, and zero page-level horizontal overflow. Save `showcase/.qa/mobile.png`.

- [ ] **Step 4: Compare the accepted concept and render**

Use `view_image` on `showcase/design/concept-reference.svg` and on `showcase/.qa/desktop.png`. Record at least five checks: first-viewport balance, palette, typography, open container model, evidence hierarchy, real screenshot framing, and section rhythm. Fix every material mismatch.

- [ ] **Step 5: Remove temporary QA artifacts after final inspection**

Run: `rm -rf showcase/.qa`

### Task 6: Final verification and handoff

**Files:**
- Verify only.

- [ ] **Step 1: Run the complete static verification**

Run: `node showcase/tests/validate-showcase.mjs`

Expected: `showcase static contract: PASS`.

- [ ] **Step 2: Verify syntax and whitespace**

Run: `node --check showcase/app.js && git diff --check -- showcase docs/superpowers`

Expected: exit 0 with no output from syntax or whitespace checks.

- [ ] **Step 3: Confirm only task files are staged or committed**

Run: `git status --short -- showcase docs/superpowers/specs/2026-07-18-algotutorgen-showcase-design.md docs/superpowers/plans/2026-07-18-algotutorgen-showcase.md`

Expected: only showcase-related paths, with all pre-existing unrelated work untouched.

- [ ] **Step 4: Commit final verified repairs if needed**

```bash
git add showcase
git commit -m "feat: deliver AlgoTutorGen research showcase"
```

## Plan self-review

- The tasks cover every section and interaction in the design spec.
- The static test is created and observed failing before production code.
- Frozen method keys and values stay consistent between the test and implementation.
- No implementation step changes the AlgoTutorGen generation, renderer, or verification pipeline.
- All commands use the required project Python interpreter when Python is involved.
