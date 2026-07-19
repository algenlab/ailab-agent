class TrieNode {
  constructor() {
    this.children = {};
    this.count = 0;
  }
}

export const PROBLEM_INPUT = {
  prefix: 'ap',
  words: ['apple', 'app', 'ape', 'bat'],
};

export const PROBLEM_ANSWER = 3;

export function buildTrieTrace(input) {
  const { prefix, words } = input;
  const root = new TrieNode();

  // First pass: assign persistent IDs to all nodes we'll create
  let nextId = 0;
  function assignId(node, parentChar) {
    node._id = nextId++;
    node._char = parentChar;
    for (const [ch, child] of Object.entries(node.children)) {
      assignId(child, ch);
    }
  }

  function snapshot() {
    assignId(root, null);
    return deepClone(root);
  }

  const steps = [];

  // Step 0: Initial state
  steps.push({
    label: '初始状态 — 空 Trie，仅含根节点',
    nodes: snapshot(),
    activeNodePath: ['__root__'],
    insertedWord: null,
    description: '准备开始。Trie 初始只有一个根节点（虚线圆圈），count=0。接下来依次插入所有单词。',
    phase: 'init',
  });

  const allWords = words;
  allWords.forEach((word) => {
    let current = root;
    current.count += 1;
    steps.push({
      label: `插入 "${word}" — 根节点 count+1`,
      nodes: snapshot(),
      activeNodePath: ['__root__'],
      insertedWord: word,
      description: `插入单词 <strong>"${word}"</strong>：从根节点开始，每经过一个节点 count+1。根节点 count 现为 ${root.count}。`,
      phase: 'insert',
    });

    for (let i = 0; i < word.length; i++) {
      const ch = word[i];
      if (!current.children[ch]) {
        current.children[ch] = new TrieNode();
      }
      current = current.children[ch];
      current.count += 1;
      const path = ['__root__', ...word.slice(0, i + 1).split('')];
      steps.push({
        label: `插入 "${word}" — 处理字符 '${ch}' (位置 ${i})`,
        nodes: snapshot(),
        activeNodePath: path,
        insertedWord: word,
        description: `字符 <strong>'${ch}'</strong>：沿边走到节点 '${ch}'，count+1。当前节点 count=${current.count}，路径: ${path.filter(p => p !== '__root__').join(' → ')}`,
        phase: 'insert',
      });
    }
  });

  // Query phase
  steps.push({
    label: '查询阶段 — 从根节点开始匹配 prefix="ap"',
    nodes: snapshot(),
    activeNodePath: ['__root__'],
    insertedWord: null,
    description: `所有单词插入完毕。现在查询前缀 <strong>"${prefix}"</strong>。从根节点开始沿字符路径匹配。`,
    phase: 'query',
  });

  let queryNode = root;
  let matched = true;
  const queryPath = ['__root__'];

  for (let i = 0; i < prefix.length; i++) {
    const ch = prefix[i];
    if (queryNode && queryNode.children[ch]) {
      queryNode = queryNode.children[ch];
      queryPath.push(ch);
      steps.push({
        label: `查询 — 匹配字符 '${ch}' (位置 ${i})`,
        nodes: snapshot(),
        activeNodePath: [...queryPath],
        insertedWord: null,
        description: `在 Trie 中找到字符 <strong>'${ch}'</strong>，继续沿路径向下。当前节点 count=${queryNode.count}，路径: ${queryPath.filter(p => p !== '__root__').join(' → ')}`,
        phase: 'query',
      });
    } else {
      matched = false;
      steps.push({
        label: `查询 — 未找到字符 '${ch}'，匹配失败`,
        nodes: snapshot(),
        activeNodePath: [...queryPath],
        insertedWord: null,
        description: `字符 <strong>'${ch}'</strong> 不在当前节点的子节点中。匹配失败，答案为 0。`,
        phase: 'query',
      });
      break;
    }
  }

  if (matched && queryNode) {
    steps.push({
      label: `查询完成 — 答案为 ${queryNode.count}`,
      nodes: snapshot(),
      activeNodePath: queryPath,
      insertedWord: null,
      description: `前缀 <strong>"${prefix}"</strong> 匹配完成。最终节点 count=<strong>${queryNode.count}</strong>，表示有 ${queryNode.count} 个单词以 "${prefix}" 开头。`,
      phase: 'result',
    });
  }

  return {
    steps,
    totalSteps: steps.length,
    input,
    answer: PROBLEM_ANSWER,
  };
}

function deepClone(root) {
  // Nodes have _id, _char, count, children (plain objects after snapshot)
  function clone(node) {
    const copy = {
      _id: node._id,
      _char: node._char,
      count: node.count,
      children: {},
    };
    for (const [ch, child] of Object.entries(node.children)) {
      copy.children[ch] = clone(child);
    }
    return copy;
  }
  return clone(root);
}

export function flattenTrieForDisplay(nodesSnapshot, activeNodePath) {
  if (!nodesSnapshot) return { levels: [], activeNodeIds: new Set() };

  const activeNodeIds = new Set();
  const pathSet = new Set(activeNodePath);

  // BFS
  const levels = [];
  const queue = [{ node: nodesSnapshot, depth: 0, path: '' }];

  while (queue.length > 0) {
    const levelSize = queue.length;
    const levelNodes = [];
    let levelDepth = null;

    for (let i = 0; i < levelSize; i++) {
      const { node, depth, path } = queue.shift();
      levelDepth = depth;
      const nodePath = path || '__root__';
      const isActive = activeNodePath.includes(nodePath);

      if (isActive) activeNodeIds.add(node._id);

      levelNodes.push({
        id: node._id,
        char: node._char,
        count: node.count,
        path: nodePath,
        isActive,
        isRoot: path === '',
      });

      for (const [ch, child] of Object.entries(node.children)) {
        queue.push({
          node: child,
          depth: depth + 1,
          path: path ? path + ch : ch,
        });
      }
    }

    if (levelNodes.length > 0 && levelDepth !== null) {
      levels.push({ depth: levelDepth, nodes: levelNodes });
    }
  }

  return { levels, activeNodeIds };
}
