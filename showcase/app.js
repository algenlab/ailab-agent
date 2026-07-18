const methods = [
  {
    id: 'algotutorgen',
    name: 'AlgoTutorGen',
    short: 'AlgoTutorGen',
    load: 200,
    answer: 200,
    interaction: 200,
    correctFb: 199,
    wrongFb: 198,
    hint: 200,
    show: 200,
    log: 200,
    mutationFree: 200,
    machineOk: 198,
  },
  {
    id: 'browser-repair',
    name: 'Direct-BrowserRepair（1-call first-call control）',
    short: 'Direct-BrowserRepair',
    load: 186,
    answer: 200,
    interaction: 155,
    correctFb: 128,
    wrongFb: 133,
    hint: 137,
    show: 138,
    log: 143,
    mutationFree: 155,
    machineOk: 106,
  },
  {
    id: 'direct',
    name: 'Direct HTML',
    short: 'Direct HTML',
    load: 188,
    answer: 200,
    interaction: 149,
    correctFb: 120,
    wrongFb: 125,
    hint: 132,
    show: 133,
    log: 135,
    mutationFree: 149,
    machineOk: 98,
  },
  {
    id: 'webgen',
    name: 'WebGen-Agent',
    short: 'WebGen-Agent',
    load: 194,
    answer: 169,
    interaction: 154,
    correctFb: 74,
    wrongFb: 89,
    hint: 136,
    show: 148,
    log: 109,
    mutationFree: 154,
    machineOk: 45,
  },
  {
    id: 'htmlcure',
    name: 'Direct + HTMLCure（strict）',
    short: 'Direct + HTMLCure',
    load: 75,
    answer: 75,
    interaction: 62,
    correctFb: 52,
    wrongFb: 51,
    hint: 53,
    show: 53,
    log: 59,
    mutationFree: 62,
    machineOk: 40,
  },
];

const metrics = {
  machineOk: 'Machine OK',
  load: 'Load',
  answer: 'Answer',
  interaction: 'Interaction',
  correctFb: 'Correct feedback',
  wrongFb: 'Wrong feedback',
  hint: 'Hint',
  show: 'Show answer',
  log: 'Learning log',
  mutationFree: 'Mutation-free',
};

const gateDetails = {
  result: {
    code: 'Cₛ · RESULT GATE',
    title: '答案先通过，再允许下游物化。',
    body: '执行 solve，标准化输出，并与 expected oracle 对齐。失败停在 spec 层，不把错误答案包装成网页。',
  },
  trace: {
    code: 'Cₜ · TRACE GATE',
    title: '轨迹必须能被沙箱执行并连接到结果。',
    body: 'SemanticTrace 检查事件、引用、结果一致性与覆盖边界，让过程状态成为可审计数据，而不是页面里的隐式 JavaScript。',
  },
  process: {
    code: 'Cₚ · PROCESS GATE',
    title: '过程状态必须连续，而不只是首尾正确。',
    body: '逐步检查指针、依赖、阶段和关键对象，使每个 frame 都能追溯到 canonical algorithmic state。',
  },
  scene: {
    code: 'Cɢ · SCENE GATE',
    title: '场景是经过验证的投影，不是第二份算法实现。',
    body: '确定性 compiler 把 trace 投影为 SceneGraph，并拒绝断引用、非法对象和不满足布局合同的场景。',
  },
  release: {
    code: 'Cʙ · RELEASE GATE',
    title: '浏览器行为与教学非干扰一起进入发布审计。',
    body: '固定 Runtime 提供播放、提示、反馈、日志与答案显示；只读 teaching overlay 不得改写最终答案或算法事实。',
  },
};

const artifacts = [
  {
    id: 'binary-search',
    title: '二分查找',
    family: 'Search',
    frames: 5,
    image: './assets/binary-search.png',
    href: '../output/current_flow_5cases/demos/binary_search/stable.html',
    summary: '在固定 Runtime 中播放闭区间二分的指针收缩，并在预测检查点提供反馈。',
  },
  {
    id: 'dijkstra',
    title: 'Dijkstra 最短路',
    family: 'Graph',
    frames: 12,
    image: './assets/dijkstra-shortest-path.png',
    href: '../output/current_flow_5cases/demos/dijkstra_shortest_path/stable.html',
    summary: '把距离松弛、当前节点与前驱变化投影到可播放图场景，同时保留本步证据。',
  },
  {
    id: 'unique-paths',
    title: '不同路径',
    family: 'Dynamic Programming',
    frames: 25,
    image: './assets/unique-paths.png',
    href: '../output/current_flow_5cases/demos/unique_paths/stable.html',
    summary: '逐格展示二维 DP 的依赖窗口和状态转移，让公式、表格与当前 frame 保持一致。',
  },
  {
    id: 'trie',
    title: 'Trie 前缀匹配',
    family: 'String / Tree',
    frames: 15,
    image: './assets/trie-prefix-match.png',
    href: '../output/current_flow_5cases/demos/trie_prefix_match_string/stable.html',
    summary: '沿前缀路径推进 current node，并把 prefix count、字符串对齐与教学提示连接到同一状态。',
  },
];

const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

function renderMetric(metricKey) {
  if (!Object.prototype.hasOwnProperty.call(metrics, metricKey)) return;

  document.querySelectorAll('[data-metric]').forEach((button) => {
    button.setAttribute('aria-pressed', String(button.dataset.metric === metricKey));
  });

  document.querySelectorAll('[data-method]').forEach((row) => {
    const method = methods.find((item) => item.id === row.dataset.method);
    if (!method) return;

    const value = method[metricKey];
    const percentage = value / 2;
    const track = row.querySelector('.method-track');
    const count = row.querySelector('.method-value strong');
    const rate = row.querySelector('.method-value span');

    track.style.setProperty('--score', String(percentage));
    track.setAttribute('aria-valuenow', String(percentage));
    track.setAttribute('aria-label', `${method.name} ${metrics[metricKey]} ${percentage.toFixed(1)}%`);
    count.textContent = `${value}/200`;
    rate.textContent = `${percentage.toFixed(1)}%`;
  });

  document.querySelector('#method-chart').dataset.activeMetric = metricKey;
}

function setupMetricSwitcher() {
  const buttons = [...document.querySelectorAll('[data-metric]')];
  buttons.forEach((button, index) => {
    button.addEventListener('click', () => renderMetric(button.dataset.metric));
    button.addEventListener('keydown', (event) => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      let nextIndex = index;
      if (event.key === 'ArrowRight') nextIndex = (index + 1) % buttons.length;
      if (event.key === 'ArrowLeft') nextIndex = (index - 1 + buttons.length) % buttons.length;
      if (event.key === 'Home') nextIndex = 0;
      if (event.key === 'End') nextIndex = buttons.length - 1;
      buttons[nextIndex].focus();
      renderMetric(buttons[nextIndex].dataset.metric);
    });
  });
}

function selectGate(id) {
  const detail = gateDetails[id];
  if (!detail) return;

  document.querySelectorAll('[data-gate]').forEach((gate) => {
    const selected = gate.dataset.gate === id;
    gate.classList.toggle('is-active', selected);
    gate.setAttribute('aria-pressed', String(selected));
  });

  const detailElement = document.querySelector('#gate-detail');
  detailElement.replaceChildren();

  const code = document.createElement('span');
  code.textContent = detail.code;
  const title = document.createElement('strong');
  title.textContent = detail.title;
  const body = document.createElement('p');
  body.textContent = detail.body;
  detailElement.append(code, title, body);
}

function setupGates() {
  const gates = [...document.querySelectorAll('[data-gate]')];
  gates.forEach((gate, index) => {
    gate.addEventListener('click', () => selectGate(gate.dataset.gate));
    gate.addEventListener('keydown', (event) => {
      if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
      event.preventDefault();
      const delta = event.key === 'ArrowRight' ? 1 : -1;
      const next = gates[(index + delta + gates.length) % gates.length];
      next.focus();
      selectGate(next.dataset.gate);
    });
  });
}

function selectArtifact(id) {
  const artifact = artifacts.find((item) => item.id === id);
  if (!artifact) return;

  const imageWrap = document.querySelector('.artifact-image-wrap');
  const image = document.querySelector('#artifact-image');
  imageWrap.classList.add('is-switching');

  const settle = () => {
    imageWrap.classList.remove('is-switching');
    image.removeEventListener('load', settle);
  };
  image.addEventListener('load', settle);
  image.src = artifact.image;
  image.alt = `${artifact.title} 交互式算法导师截图`;
  if (image.complete) requestAnimationFrame(settle);

  const index = artifacts.indexOf(artifact) + 1;
  document.querySelector('#artifact-index').textContent = `${String(index).padStart(2, '0')} / ${String(artifacts.length).padStart(2, '0')}`;
  document.querySelector('#artifact-title').textContent = artifact.title;
  document.querySelector('#artifact-summary').textContent = artifact.summary;
  document.querySelector('#artifact-family').textContent = artifact.family;
  document.querySelector('#artifact-frames').textContent = String(artifact.frames);
  document.querySelector('#artifact-link').href = artifact.href;
  document.querySelector('#artifact-link').setAttribute('aria-label', `打开 ${artifact.title} 真实 HTML 产物`);

  document.querySelectorAll('[data-artifact]').forEach((button) => {
    const selected = button.dataset.artifact === id;
    button.setAttribute('aria-selected', String(selected));
    button.closest('.artifact-tab').classList.toggle('is-active', selected);
  });
}

function setupArtifacts() {
  const tabs = [...document.querySelectorAll('[data-artifact]')];
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectArtifact(tab.dataset.artifact));
    tab.addEventListener('keydown', (event) => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      let nextIndex = index;
      if (event.key === 'ArrowRight') nextIndex = (index + 1) % tabs.length;
      if (event.key === 'ArrowLeft') nextIndex = (index - 1 + tabs.length) % tabs.length;
      if (event.key === 'Home') nextIndex = 0;
      if (event.key === 'End') nextIndex = tabs.length - 1;
      tabs[nextIndex].focus();
      selectArtifact(tabs[nextIndex].dataset.artifact);
    });
  });
}

function setupRevealObserver() {
  const elements = document.querySelectorAll('[data-reveal]');
  if (reduceMotion.matches || !('IntersectionObserver' in window)) {
    elements.forEach((element) => element.classList.add('is-visible'));
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-visible');
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });

  elements.forEach((element) => observer.observe(element));
}

function setupActiveNavigation() {
  if (!('IntersectionObserver' in window)) return;
  const sections = document.querySelectorAll('section[id]');
  const links = document.querySelectorAll('.desktop-nav a, .mobile-nav a');
  const observer = new IntersectionObserver((entries) => {
    const visible = entries
      .filter((entry) => entry.isIntersecting)
      .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (!visible) return;
    links.forEach((link) => link.classList.toggle('is-active', link.hash === `#${visible.target.id}`));
  }, { threshold: [0.2, 0.45, 0.7], rootMargin: '-20% 0px -55% 0px' });
  sections.forEach((section) => observer.observe(section));
}

function setupScrollChrome() {
  const header = document.querySelector('.site-header');
  const progress = document.querySelector('#scroll-progress-bar');
  let scheduled = false;

  const update = () => {
    const scrollable = Math.max(document.documentElement.scrollHeight - window.innerHeight, 1);
    const ratio = Math.min(Math.max(window.scrollY / scrollable, 0), 1);
    progress.style.transform = `scaleX(${ratio})`;
    header.classList.toggle('is-scrolled', window.scrollY > 24);
    scheduled = false;
  };

  window.addEventListener('scroll', () => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(update);
  }, { passive: true });
  window.addEventListener('resize', update, { passive: true });
  update();
}

function setupMobileNavigation() {
  const toggle = document.querySelector('.menu-toggle');
  const menu = document.querySelector('#mobile-nav');
  const close = () => {
    toggle.setAttribute('aria-expanded', 'false');
    toggle.setAttribute('aria-label', '打开导航菜单');
    menu.hidden = true;
  };

  toggle.addEventListener('click', () => {
    const open = toggle.getAttribute('aria-expanded') === 'true';
    toggle.setAttribute('aria-expanded', String(!open));
    toggle.setAttribute('aria-label', open ? '打开导航菜单' : '关闭导航菜单');
    menu.hidden = open;
  });
  menu.querySelectorAll('a').forEach((link) => link.addEventListener('click', close));
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !menu.hidden) {
      close();
      toggle.focus();
    }
  });
  window.matchMedia('(min-width: 720px)').addEventListener('change', (event) => {
    if (event.matches) close();
  });
}

function setupCounters() {
  const counters = document.querySelectorAll('[data-count]');
  if (!counters.length || reduceMotion.matches || !('IntersectionObserver' in window)) return;

  const formatter = new Intl.NumberFormat('en-US');
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      const element = entry.target;
      const finalValue = Number(element.dataset.count);
      const startValue = Math.floor(finalValue * 0.86);
      const startTime = performance.now();
      const duration = 900;

      const tick = (now) => {
        const progress = Math.min((now - startTime) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 4);
        element.textContent = formatter.format(Math.round(startValue + (finalValue - startValue) * eased));
        if (progress < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
      observer.unobserve(element);
    });
  }, { threshold: 0.65 });
  counters.forEach((counter) => observer.observe(counter));
}

function setupTraceCanvas() {
  if (reduceMotion.matches) return;
  const canvas = document.querySelector('#trace-canvas');
  const context = canvas.getContext('2d');
  const traces = [
    { y: .18, bend: .10, speed: .000055, phase: .10, alpha: .13 },
    { y: .32, bend: -.07, speed: .000042, phase: .46, alpha: .09 },
    { y: .51, bend: .08, speed: .000061, phase: .72, alpha: .11 },
    { y: .72, bend: -.09, speed: .000048, phase: .28, alpha: .08 },
  ];
  let width = 0;
  let height = 0;
  let frame = 0;
  let paused = false;

  const resize = () => {
    const rect = canvas.getBoundingClientRect();
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    width = rect.width;
    height = rect.height;
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
  };

  const pointOnCurve = (trace, progress) => {
    const startX = width * .02;
    const endX = width * .98;
    const baseY = height * trace.y;
    const controlY = baseY + height * trace.bend;
    const x = startX + (endX - startX) * progress;
    const y = (1 - progress) * (1 - progress) * baseY + 2 * (1 - progress) * progress * controlY + progress * progress * baseY;
    return { x, y };
  };

  const draw = (time) => {
    if (paused) return;
    context.clearRect(0, 0, width, height);

    traces.forEach((trace) => {
      const startX = width * .02;
      const endX = width * .98;
      const baseY = height * trace.y;
      const controlY = baseY + height * trace.bend;
      context.beginPath();
      context.moveTo(startX, baseY);
      context.quadraticCurveTo(width * .5, controlY, endX, baseY);
      context.strokeStyle = `rgba(126, 234, 223, ${trace.alpha})`;
      context.lineWidth = 1;
      context.setLineDash([2, 10]);
      context.stroke();

      const progress = (time * trace.speed + trace.phase) % 1;
      const point = pointOnCurve(trace, progress);
      const glow = context.createRadialGradient(point.x, point.y, 0, point.x, point.y, 14);
      glow.addColorStop(0, 'rgba(52, 232, 211, .92)');
      glow.addColorStop(.2, 'rgba(52, 232, 211, .52)');
      glow.addColorStop(1, 'rgba(52, 232, 211, 0)');
      context.fillStyle = glow;
      context.beginPath();
      context.arc(point.x, point.y, 14, 0, Math.PI * 2);
      context.fill();
      context.fillStyle = '#7eeadf';
      context.beginPath();
      context.arc(point.x, point.y, 2.2, 0, Math.PI * 2);
      context.fill();
    });

    context.setLineDash([]);
    frame = requestAnimationFrame(draw);
  };

  document.addEventListener('visibilitychange', () => {
    paused = document.hidden;
    if (paused) cancelAnimationFrame(frame);
    else frame = requestAnimationFrame(draw);
  });
  window.addEventListener('resize', resize, { passive: true });
  resize();
  frame = requestAnimationFrame(draw);
}

setupMetricSwitcher();
setupGates();
setupArtifacts();
setupRevealObserver();
setupActiveNavigation();
setupScrollChrome();
setupMobileNavigation();
setupCounters();
setupTraceCanvas();
renderMetric('machineOk');
selectGate('result');
selectArtifact('binary-search');
