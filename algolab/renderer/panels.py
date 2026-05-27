"""Panel shell markup for the teaching runtime."""

from __future__ import annotations


def workspace_markup(render_target: str = "teaching_2d") -> str:
    return f"""<body>
<div class="app" data-render-target="{render_target}">
  <header class="topbar">
    <div class="top-title"><h1 id="title"></h1><p id="subtitle" class="subtitle"></p></div>
    <div class="top-summary" aria-label="当前任务摘要">
      <div class="summary-card"><span>当前输出</span><strong id="top-result"></strong></div>
      <div class="summary-card"><span>当前解法</span><strong id="top-solution"></strong></div>
    </div>
    <div id="badges" class="badges"></div>
  </header>
  <main class="workspace">
    <aside class="col task-col">
      <section class="panel section task-panel">
        <h2>题目与输入</h2>
        <div id="problem-description" class="problem-description"></div>
        <h3 class="subhead">当前输入</h3>
        <pre id="input" class="jsonbox"></pre>
        <h3 class="subhead">修改输入</h3>
        <textarea id="input-editor" class="jsonbox input-editor" aria-label="修改 JSON 输入"></textarea>
        <h3 class="subhead">期望输出</h3>
        <pre id="expected" class="jsonbox compact"></pre>
      </section>
      <section class="panel section">
        <h2>解法</h2>
        <div id="tabs" class="tabs"></div>
      </section>
      <section id="variant-compare-panel" class="panel section variant-compare-panel">
        <h2>解法对比</h2>
        <div id="variant-compare" class="variant-compare"></div>
      </section>
      <section id="regeneration-panel" class="panel section regeneration-panel">
        <h2>输入重新生成</h2>
        <p class="regen-note">修改 JSON 后需要重新走 pipeline：ProblemInput -> BuildArtifact -> HTML。</p>
        <p class="regen-note">静态 HTML 无法在线调用后端；这里仅准备 artifact 输入，不修改当前 trace 或 SceneGraph。</p>
        <button id="regenerate" class="secondary-action" type="button">准备重新生成请求</button>
        <div id="regenerate-status" class="regen-status" role="status">等待修改输入。需要重新生成时，请将下方 artifact 输入交给主 pipeline。</div>
        <pre id="regenerate-payload" class="jsonbox compact regenerate-payload"></pre>
      </section>
    </aside>
    <section class="col">
      <div class="panel hero">
        <div class="step-head">
          <div><h2 id="step-title"></h2><p id="step-desc"></p></div>
          <div id="op" class="pill"></div>
        </div>
        <div id="canvas" class="canvas"></div>
        <div class="controls">
          <button id="prev">上一步</button>
          <button id="play" class="primary">播放</button>
          <button id="next">下一步</button>
          <input id="range" class="range" type="range" min="0" value="0">
          <div id="counter" class="counter"></div>
        </div>
        <div id="timeline" class="timeline" aria-label="语义时间线"></div>
      </div>
    </section>
    <aside class="col teaching-col">
      <section id="teaching-panel" class="panel section"><h2>讲解</h2><div id="teaching"></div></section>
      <section class="panel section"><h2>系统校验</h2><div id="evidence" class="evidence"></div></section>
      <section class="panel section"><h2>本步证据</h2><div id="step-evidence" class="step-evidence"></div></section>
      <section class="panel section"><h2>当前状态</h2><div id="state" class="state-grid"></div></section>
      <section class="panel section"><h2>交互</h2><div id="interaction"></div></section>
      <section class="panel section"><h2>代码</h2><div id="code" class="code"></div></section>
    </aside>
  </main>
  <details id="debug-drawer" class="debug-drawer">
    <summary><span>Debug Drawer</span><small>原始校验、状态和 artifact 证据</small></summary>
    <div class="debug-grid">
      <section class="panel section"><h2>raw validation report</h2><div id="debug-evidence" class="evidence"></div><pre id="debug-validation-json" class="jsonbox debug-json"></pre></section>
      <section class="panel section"><h2>raw state JSON</h2><div id="debug-state" class="state-grid"></div></section>
      <section class="panel section"><h2>release gate</h2><div id="debug-release" class="evidence"></div></section>
      <section class="panel section"><h2>artifact JSON</h2><a id="debug-artifact-download" class="debug-download" download="algolab-artifact.json">下载 artifact JSON</a><pre id="debug-artifact" class="jsonbox debug-json"></pre></section>
    </div>
  </details>
</div>"""
