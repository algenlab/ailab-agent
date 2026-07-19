
// =====================
// 数据与算法核心
// =====================

const INPUT_DATA = {
  p: "5",
  q: "1",
  tree: {
    edges: [
      ["3", "5"],
      ["3", "1"],
      ["5", "6"],
      ["5", "2"],
      ["1", "0"],
      ["1", "8"],
      ["2", "7"],
      ["2", "4"]
    ],
    nodes: [
      { id: "3" },
      { id: "5" },
      { id: "1" },
      { id: "6" },
      { id: "2" },
      { id: "0" },
      { id: "8" },
      { id: "7" },
      { id: "4" }
    ]
  }
};

const EXPECTED_ANSWER = "3";

// 构建二叉树节点对象
function buildTree(treeData) {
  const nodes = {};
  treeData.nodes.forEach(n => { nodes[n.id] = { id: n.id, left: null, right: null, parent: null }; });
  const childSet = new Set();
  treeData.edges.forEach(([parentId, childId]) => {
    childSet.add(childId);
    const parentNode = nodes[parentId];
    const childNode = nodes[childId];
    childNode.parent = parentNode;
    if (!parentNode.left) {
      parentNode.left = childNode;
    } else {
      parentNode.right = childNode;
    }
  });
  const rootId = treeData.nodes.find(n => !childSet.has(n.id)).id;
  return { root: nodes[rootId], nodes };
}

// 生成 LCA 算法的步骤记录
function generateSteps(root, p, q) {
  const steps = [];
  function dfs(node) {
    if (!node) {
      steps.push({ type: 'enter_null', nodeId: null, returnValue: null });
      return null;
    }
    steps.push({ type: 'enter', nodeId: node.id });
    if (node.id === p || node.id === q) {
      steps.push({ type: 'return', nodeId: node.id, value: node.id, reason: 'match' });
      return node.id;
    }
    const left = dfs(node.left);
    steps.push({ type: 'after_left', nodeId: node.id, leftValue: left });
    const right = dfs(node.right);
    steps.push({ type: 'after_right', nodeId: node.id, rightValue: right, leftValue: left });
    if (left && right) {
      steps.push({ type: 'return', nodeId: node.id, value: node.id, reason: 'lca' });
      return node.id;
    }
    const ret = left || right;
    steps.push({ type: 'return', nodeId: node.id, value: ret, reason: ret ? 'propagate' : 'none' });
    return ret;
  }
  dfs(root);
  return steps;
}

// =====================
// 树布局计算
// =====================

function computeLayout(root) {
  const positions = new Map();
  let inorderIndex = 0;

  function inorder(node, depth = 0) {
    if (!node) return;
    inorder(node.left, depth + 1);
    inorderIndex++;
    positions.set(node.id, { x: 0, y: depth, inorderIdx: inorderIndex });
    inorder(node.right, depth + 1);
  }
  inorder(root, 0);

  const totalNodes = inorderIndex;
  const xSpacing = 700 / (totalNodes + 1);
  const ySpacing = 90;
  const offsetX = 50;
  const offsetY = 45;

  const finalPos = {};
  positions.forEach((pos, id) => {
    finalPos[id] = {
      x: pos.inorderIdx * xSpacing + offsetX,
      y: pos.y * ySpacing + offsetY
    };
  });
  return { positions: finalPos };
}

// =====================
// SVG 绘制
// =====================

let svg, stepIndex, steps, treeData, nodeMap, rootNode, positions;

function initVisualization() {
  svg = document.getElementById('tree-svg');
  treeData = buildTree(INPUT_DATA.tree);
  nodeMap = treeData.nodes;
  rootNode = treeData.root;
  steps = generateSteps(rootNode, INPUT_DATA.p, INPUT_DATA.q);
  positions = computeLayout(rootNode).positions;
  stepIndex = 0;
  drawTree();
  updateUI();
}

function drawTree() {
  svg.innerHTML = '';
  // 图例
  const legend = document.createElementNS('http://www.w3.org/2000/svg','g');
  legend.setAttribute('transform','translate(10,10)');
  [
    { label:'p="5"',color:'#38a169' },
    { label:'q="1"',color:'#3182ce' }
  ].forEach((item,i) => {
    const r = document.createElementNS('http://www.w3.org/2000/svg','rect');
    r.setAttribute('x', 0);
    r.setAttribute('y', i * 18);
    r.setAttribute('width', 10);
    r.setAttribute('height', 10);
    r.setAttribute('fill', item.color);
    r.setAttribute('rx', 2);
    legend.appendChild(r);
    const t = document.createElementNS('http://www.w3.org/2000/svg','text');
    t.setAttribute('x', 14);
    t.setAttribute('y', i * 18 + 9);
    t.setAttribute('font-size','11');
    t.setAttribute('fill','#4a5568');
    t.textContent = item.label;
    legend.appendChild(t);
  });
  svg.appendChild(legend);
  // 绘制边
  for (const nodeId of Object.keys(nodeMap)) {
    const node = nodeMap[nodeId];
    const pos = positions[nodeId];
    if (!pos) continue;
    [node.left, node.right].forEach(child => {
      if (!child) return;
      const childPos = positions[child.id];
      if (!childPos) return;
      const line = document.createElementNS('http://www.w3.org/2000/svg','line');
      line.setAttribute('x1', pos.x);
      line.setAttribute('y1', pos.y);
      line.setAttribute('x2', childPos.x);
      line.setAttribute('y2', childPos.y);
      line.setAttribute('stroke', '#cbd5e0');
      line.setAttribute('stroke-width', '2');
      line.setAttribute('data-parent', nodeId);
      line.setAttribute('data-child', child.id);
      svg.appendChild(line);
    });
  }
  // 绘制节点
  for (const nodeId of Object.keys(nodeMap)) {
    const pos = positions[nodeId];
    if (!pos) continue;
    const g = document.createElementNS('http://www.w3.org/2000/svg','g');

    const circle = document.createElementNS('http://www.w3.org/2000/svg','circle');
    circle.setAttribute('cx', pos.x);
    circle.setAttribute('cy', pos.y);
    circle.setAttribute('r', 22);
    circle.setAttribute('fill', '#ffffff');
    circle.setAttribute('stroke', '#718096');
    circle.setAttribute('stroke-width', '2');
    circle.setAttribute('data-node-id', nodeId);
    circle.classList.add('node-circle');
    g.appendChild(circle);

    const text = document.createElementNS('http://www.w3.org/2000/svg','text');
    text.setAttribute('x', pos.x);
    text.setAttribute('y', pos.y + 5);
    text.setAttribute('text-anchor', 'middle');
    text.setAttribute('dominant-baseline', 'middle');
    text.setAttribute('fill', '#2d3748');
    text.setAttribute('font-size', '14');
    text.setAttribute('font-weight', '600');
    text.textContent = nodeId;
    g.appendChild(text);

    svg.appendChild(g);
  }
}

function updateUI() {
  // 清空高亮
  svg.querySelectorAll('.node-circle').forEach(c => {
    c.setAttribute('fill','#ffffff');
    c.setAttribute('stroke','#718096');
    c.setAttribute('stroke-width','2');
  });
  svg.querySelectorAll('line').forEach(l => {
    l.setAttribute('stroke','#cbd5e0');
    l.setAttribute('stroke-width','2');
  });
  svg.querySelectorAll('.return-label,.stack-marker').forEach(el => el.remove());

  const stepNum = document.getElementById('step-number');
  const stepDesc = document.getElementById('step-description');
  const callStackDiv = document.getElementById('call-stack');
  const returnInfo = document.getElementById('return-info');

  // 始终标记 p 和 q 节点
  [INPUT_DATA.p, INPUT_DATA.q].forEach(id => {
    const circ = svg.querySelector(`[data-node-id="${id}"]`);
    if (circ) {
      const isP = id === INPUT_DATA.p;
      circ.setAttribute('stroke', isP ? '#38a169' : '#3182ce');
      circ.setAttribute('stroke-width','3');
      circ.setAttribute('fill','#f0fff4');
    }
  });

  if (steps.length === 0) {
    stepNum.textContent = '步骤 0 / 0';
    stepDesc.textContent = '无步骤数据';
    callStackDiv.innerHTML = '<div class="stack-empty">空</div>';
    returnInfo.textContent = '—';
    return;
  }

  stepNum.textContent = `步骤 ${stepIndex} / ${steps.length}`;

  const stack = [];
  let currentStepType = '';
  let currentStepNode = null;
  let currentStepData = null;

  for (let i = 0; i <= stepIndex && i < steps.length; i++) {
    const step = steps[i];
    currentStepType = step.type;
    currentStepNode = step.nodeId;
    currentStepData = step;

    if (step.type === 'enter') {
      stack.push({ nodeId: step.nodeId, state: 'enter' });
    } else if (step.type === 'enter_null') {
      // null不入栈
    } else if (step.type === 'after_left') {
      const top = stack[stack.length-1];
      if (top && top.nodeId === step.nodeId) top.state = 'after_left';
    } else if (step.type === 'after_right') {
      const top = stack[stack.length-1];
      if (top && top.nodeId === step.nodeId) top.state = 'after_right';
    } else if (step.type === 'return') {
      if (stack.length && stack[stack.length-1].nodeId === step.nodeId) stack.pop();
    }
  }

  // 调用栈
  callStackDiv.innerHTML = '';
  if (stack.length === 0) {
    callStackDiv.innerHTML = '<div class="stack-empty">空</div>';
  } else {
    stack.slice().reverse().forEach((frame, idx) => {
      const frameEl = document.createElement('div');
      frameEl.className = 'stack-item' + (idx === 0 ? ' current' : '');
      const stateLabel = frame.state === 'enter' ? '进入' : frame.state === 'after_left' ? '左子返回' : '右子返回';
      frameEl.textContent = `DFS(${frame.nodeId}) [${stateLabel}]`;
      callStackDiv.appendChild(frameEl);
    });
  }

  // 高亮当前节点
  if (currentStepNode) {
    const circle = svg.querySelector(`[data-node-id="${currentStepNode}"]`);
    if (circle) {
      circle.setAttribute('fill','#fefcbf');
      circle.setAttribute('stroke','#d69e2e');
      circle.setAttribute('stroke-width','3.5');
    }
  }

  // 返回步骤标注
  if (currentStepType === 'return' && currentStepNode) {
    const pos = positions[currentStepNode];
    if (pos) {
      const label = document.createElementNS('http://www.w3.org/2000/svg','text');
      label.setAttribute('x', pos.x);
      label.setAttribute('y', pos.y + 32);
      label.setAttribute('text-anchor','middle');
      label.setAttribute('font-size','11');
      label.setAttribute('font-weight','bold');
      label.classList.add('return-label');
      const val = currentStepData.value || 'null';
      const colors = { match:'#38a169', lca:'#2b6cb0', propagate:'#d69e2e', none:'#a0aec0' };
      label.setAttribute('fill', colors[currentStepData.reason] || '#4a5568');
      label.textContent = `返回: ${val}`;
      svg.appendChild(label);
      const circle = svg.querySelector(`[data-node-id="${currentStepNode}"]`);
      if (circle) {
        const fills = { match:'#c6f6d5', lca:'#bee3f8', propagate:'#fefcbf', none:'#edf2f7' };
        const strokes = { match:'#38a169', lca:'#3182ce', propagate:'#d69e2e', none:'#a0aec0' };
        circle.setAttribute('fill', fills[currentStepData.reason] || '#ffffff');
        circle.setAttribute('stroke', strokes[currentStepData.reason] || '#718096');
        circle.setAttribute('stroke-width','3.5');
      }
    }
  }

  // after_left/after_right 边标注
  if ((currentStepType === 'after_left' || currentStepType === 'after_right') && currentStepNode) {
    const childSide = currentStepType === 'after_left' ? 'left' : 'right';
    const childNode = nodeMap[currentStepNode]?.[childSide];
    if (childNode) {
      const parentPos = positions[currentStepNode];
      const childPos = positions[childNode.id];
      if (parentPos && childPos) {
        const mx = (parentPos.x + childPos.x) / 2;
        const my = (parentPos.y + childPos.y) / 2;
        const label = document.createElementNS('http://www.w3.org/2000/svg','text');
        label.setAttribute('x', mx);
        label.setAttribute('y', my - 5);
        label.setAttribute('text-anchor','middle');
        label.setAttribute('font-size','10');
        label.setAttribute('fill','#c05621');
        label.classList.add('return-label');
        const val = currentStepType === 'after_left' ? currentStepData.leftValue : currentStepData.rightValue;
        label.textContent = `返回:${val || 'null'}`;
        svg.appendChild(label);
      }
    }
  }

  // 步骤描述
  let desc = '';
  if (currentStepType === 'enter') {
    desc = `🔍 递归进入节点 ${currentStepNode}`;
  } else if (currentStepType === 'enter_null') {
    desc = `⬅ 遇到空节点，返回 null`;
  } else if (currentStepType === 'after_left') {
    desc = `⬅ 节点 ${currentStepNode} 的左子树返回: ${currentStepData.leftValue || 'null'}`;
  } else if (currentStepType === 'after_right') {
    desc = `➡ 节点 ${currentStepNode} 的右子树返回: ${currentStepData.rightValue || 'null'}`;
  } else if (currentStepType === 'return') {
    desc = `↩ 节点 ${currentStepNode} 返回: ${currentStepData.value || 'null'} (${reasonLabel(currentStepData.reason)})`;
  }
  stepDesc.textContent = desc;

  // 返回信息区
  returnInfo.innerHTML = '';
  if (currentStepType === 'after_right' && currentStepData) {
    const leftVal = currentStepData.leftValue || 'null';
    const rightVal = currentStepData.rightValue || 'null';
    returnInfo.innerHTML = `左: ${leftVal}   右: ${rightVal}<br>`;
    if (leftVal !== 'null' && rightVal !== 'null') {
      returnInfo.innerHTML += '<span style="color:#2b6cb0;font-weight:600;">→ 左右均非空 → LCA</span>';
    } else if (leftVal !== 'null' || rightVal !== 'null') {
      returnInfo.innerHTML += '<span style="color:#d69e2e;">→ 仅一侧非空，向上传播</span>';
    } else {
      returnInfo.innerHTML += '<span style="color:#a0aec0;">→ 均为空，返回 null</span>';
    }
  } else if (currentStepType === 'return' && currentStepData) {
    const notes = {
      match: '<span style="color:#38a169;">命中 p 或 q，直接返回</span>',
      lca: '<span style="color:#2b6cb0;font-weight:600;">🎯 找到 LCA！</span>',
      propagate: '<span style="color:#d69e2e;">将非空值向上传播</span>',
      none: '<span style="color:#a0aec0;">返回 null</span>'
    };
    returnInfo.innerHTML = notes[currentStepData.reason] || '—';
  }

  // 按钮
  document.getElementById('btn-prev').disabled = (stepIndex === 0);
  document.getElementById('btn-next').disabled = (stepIndex >= steps.length);
  document.getElementById('btn-reset').disabled = (stepIndex === 0);
  document.getElementById('btn-auto').disabled = (stepIndex >= steps.length);
}

function reasonLabel(reason) {
  const map = { match:'命中', lca:'LCA', propagate:'传播', none:'无' };
  return map[reason] || reason;
}

// =====================
// 步骤导航
// =====================

function stepForward() {
  if (stepIndex < steps.length) {
    stepIndex++;
    updateUI();
    checkAutoCheckpoint();
    logAction(`前进至步骤 ${stepIndex}`);
  }
}

function stepBack() {
  if (stepIndex > 0) {
    stepIndex--;
    updateUI();
    logAction(`回退至步骤 ${stepIndex}`);
  }
}

function reset() {
  stepIndex = 0;
  updateUI();
  closeCheckpoint();
  document.getElementById('log-container').innerHTML = '<div class="log-empty">暂无记录</div>';
  logAction('重置');
}

let autoInterval;
function autoPlay() {
  if (autoInterval) {
    clearInterval(autoInterval);
    autoInterval = null;
    document.getElementById('btn-auto').textContent = '▶ 自动播放';
    return;
  }
  if (stepIndex >= steps.length) {
    stepIndex = 0;
    updateUI();
  }
  document.getElementById('btn-auto').textContent = '⏸ 暂停';
  autoInterval = setInterval(() => {
    if (stepIndex < steps.length) {
      stepIndex++;
      updateUI();
      checkAutoCheckpoint();
      logAction(`自动前进至步骤 ${stepIndex}`);
    } else {
      clearInterval(autoInterval);
      autoInterval = null;
      document.getElementById('btn-auto').textContent = '▶ 自动播放';
    }
  }, 1200);
}

// =====================
// 检查点系统
// =====================

const checkpoints = [
  {
    triggerStepIndex: 5,
    question: '当前递归节点是 5，左子调用返回了 None，接下来会处理哪个节点？',
    options: ['6', '2', '1', '3'],
    correct: 1,
    explanation: '节点5的左子6返回null后，算法将继续递归处理右子2。'
  },
  {
    triggerStepIndex: 11,
    question: '当递归处理节点 2 时，左子返回了 null，右子返回了 null，此时节点 2 的返回值应满足什么不变式？',
    options: ['null', '2', '7', '4'],
    correct: 0,
    explanation: '左右子树均未命中p或q，根据不变式，当前节点也应返回null。'
  },
];

let activeCheckpoint = null;

function checkAutoCheckpoint() {
  const cp = checkpoints.find(c => c.triggerStepIndex === stepIndex);
  if (cp) showCheckpoint(cp);
}

function showCheckpoint(cp) {
  activeCheckpoint = cp;
  const div = document.getElementById('checkpoint');
  div.style.display = 'block';
  document.getElementById('checkpoint-question').textContent = cp.question;
  const optionsDiv = document.getElementById('checkpoint-options');
  optionsDiv.innerHTML = '';
  cp.options.forEach((opt, idx) => {
    const btn = document.createElement('button');
    btn.className = 'checkpoint-btn';
    btn.textContent = opt;
    btn.addEventListener('click', () => answerCheckpoint(idx));
    optionsDiv.appendChild(btn);
  });
  document.getElementById('checkpoint-feedback').style.display = 'none';
  logAction(`检查点出现`);
}

function answerCheckpoint(userIndex) {
  if (!activeCheckpoint) return;
  const cp = activeCheckpoint;
  const feedbackDiv = document.getElementById('checkpoint-feedback');
  feedbackDiv.style.display = 'block';
  if (userIndex === cp.correct) {
    feedbackDiv.textContent = '✅ 正确！' + cp.explanation;
    feedbackDiv.className = 'checkpoint-feedback correct';
    logAction('检查点回答正确');
    document.querySelectorAll('.checkpoint-btn').forEach(b => b.disabled = true);
    setTimeout(closeCheckpoint, 2000);
  } else {
    feedbackDiv.textContent = '❌ 不正确，请再试一次。';
    feedbackDiv.className = 'checkpoint-feedback incorrect';
    logAction('检查点回答错误');
  }
}

function closeCheckpoint() {
  document.getElementById('checkpoint').style.display = 'none';
  activeCheckpoint = null;
}

// =====================
// 日志
// =====================

function logAction(message) {
  const container = document.getElementById('log-container');
  if (container.querySelector('.log-empty')) container.innerHTML = '';
  const entry = document.createElement('div');
  entry.className = 'log-entry';
  const time = new Date().toLocaleTimeString();
  entry.innerHTML = `<span class="time">${time}</span><span>${message}</span>`;
  container.prepend(entry);
  while (container.children.length > 20) container.removeChild(container.lastChild);
}

// =====================
// 事件绑定
// =====================

document.getElementById('btn-next').addEventListener('click', stepForward);
document.getElementById('btn-prev').addEventListener('click', stepBack);
document.getElementById('btn-reset').addEventListener('click', reset);
document.getElementById('btn-auto').addEventListener('click', autoPlay);

document.getElementById('btn-hint').addEventListener('click', () => {
  const hintText = '提示：DFS递归过程中，若当前节点是 p 或 q，直接返回节点id；否则递归左右子树，若左右均非空则当前即为LCA。';
  const returnInfo = document.getElementById('return-info');
  const existingHint = returnInfo.querySelector('.hint-box');
  if (existingHint) existingHint.remove();
  else {
    const hintBox = document.createElement('div');
    hintBox.className = 'hint-box';
    hintBox.textContent = hintText;
    returnInfo.appendChild(hintBox);
    logAction('查看提示');
  }
});

document.getElementById('btn-show-answer').addEventListener('click', () => {
  const display = document.getElementById('answer-display');
  if (display.textContent === EXPECTED_ANSWER) {
    display.textContent = '?';
    logAction('隐藏答案');
  } else {
    display.textContent = EXPECTED_ANSWER;
    logAction('显示答案');
  }
});

// =====================
// 启动
// =====================

window.addEventListener('DOMContentLoaded', () => {
  document.getElementById('input-json').textContent = JSON.stringify(INPUT_DATA, null, 2);
  initVisualization();
  logAction('页面加载完成');
});
