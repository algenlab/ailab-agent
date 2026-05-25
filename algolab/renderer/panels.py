"""Panel shell markup for the teaching runtime."""

from __future__ import annotations


def workspace_markup(render_target: str = "teaching_2d") -> str:
    return f"""<body>
<div class="app" data-render-target="{render_target}">
  <header class="topbar">
    <div><h1 id="title"></h1><p id="subtitle" class="subtitle"></p></div>
    <div id="badges" class="badges"></div>
  </header>
  <main class="workspace">
    <aside class="col">
      <section class="panel section"><h2>解法</h2><div id="tabs" class="tabs"></div></section>
      <section class="panel section"><h2>输入</h2><pre id="input" class="jsonbox"></pre></section>
      <section class="panel section"><h2>输出</h2><pre id="result" class="jsonbox"></pre></section>
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
        <div id="timeline" class="timeline"></div>
      </div>
    </section>
    <aside class="col">
      <section class="panel section"><h2>校验证据</h2><div id="evidence" class="evidence"></div></section>
      <section class="panel section"><h2>讲解</h2><div id="teaching"></div></section>
      <section class="panel section"><h2>步骤证据</h2><div id="step-evidence" class="step-evidence"></div></section>
      <section class="panel section"><h2>状态</h2><div id="state" class="state-grid"></div></section>
      <section class="panel section"><h2>交互</h2><div id="interaction"></div></section>
      <section class="panel section"><h2>代码</h2><div id="code" class="code"></div></section>
    </aside>
  </main>
</div>"""
