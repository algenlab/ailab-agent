import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
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
    '可验证性不是一句承诺，而是一条可执行链',
    '不是截图，是可以打开、播放、作答的 HTML',
    'AlgoTutorGen: Contract-Guided Compositional Synthesis',
    '55,108',
    '2,198',
    '1,561,298',
  ]) {
    if (!html.includes(token)) failures.push(`missing copy: ${token}`);
  }

  for (const id of ['method', 'results', 'artifacts', 'paper']) {
    if (!html.includes(`id="${id}"`)) failures.push(`missing section #${id}`);
  }

  for (const link of [
    '../output/current_flow_5cases/demos/binary_search/stable.html',
    '../output/current_flow_5cases/demos/dijkstra_shortest_path/stable.html',
    '../output/current_flow_5cases/demos/unique_paths/stable.html',
    '../output/current_flow_5cases/demos/trie_prefix_match_string/stable.html',
    '../docs/EXPERIMENT_RESULTS.md',
    '../latex/main.pdf',
  ]) {
    if (!html.includes(link)) failures.push(`missing link: ${link}`);
  }

  if (!html.includes('prefers-reduced-motion')) failures.push('missing reduced-motion bootstrap');
}

if (fs.existsSync(path.join(root, 'styles.css'))) {
  const css = fs.readFileSync(path.join(root, 'styles.css'), 'utf8');
  for (const token of ['--ink-950: #07101f', '--cyan: #34e8d3', '@media (max-width: 719px)', '@media (prefers-reduced-motion: reduce)']) {
    if (!css.includes(token)) failures.push(`missing CSS contract: ${token}`);
  }
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
