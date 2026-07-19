/**
 * Computes all intermediate states of Dijkstra's algorithm for visualization.
 * Returns an array of step objects and the final distance map.
 */
export function computeSteps(start, graph) {
  const nodes = Object.keys(graph);
  const dist = {};
  const heap = [];
  const steps = [];

  // Initialize distances
  nodes.forEach(n => dist[n] = Infinity);
  dist[start] = 0;
  heap.push({ d: 0, node: start });

  // Helper to get sorted copy of heap (min-heap simulation)
  const getHeapSnapshot = () =>
    [...heap].sort((a, b) => a.d - b.d).map(h => ({ d: h.d, node: h.node }));

  // Initial state
  steps.push({
    description:
      'Initialize distances: start node ' +
      start +
      ' = 0, all others = \u221E. Push (0, ' +
      start +
      ') onto the min-heap.',
    dist: { ...dist },
    heap: getHeapSnapshot(),
    visited: [],
    current: null,
    relaxed: [],
    skipped: false,
    done: false
  });

  while (heap.length > 0) {
    // Sort to simulate min-heap pop
    heap.sort((a, b) => a.d - b.d);
    const { d, node: u } = heap.shift();

    // Stale entry check
    if (d > dist[u]) {
      steps.push({
        description:
          'Pop (' +
          u +
          ', ' +
          d +
          ') \u2013 distance ' +
          d +
          ' > current distance ' +
          dist[u] +
          '. Stale entry, skip.',
        dist: { ...dist },
        heap: getHeapSnapshot(),
        visited: [...steps[steps.length - 1].visited],
        current: u,
        relaxed: [],
        skipped: true,
        done: false
      });
      continue;
    }

    // Relax edges
    const relaxed = [];
    const edges = graph[u] || [];
    for (const [v, w] of edges) {
      const newDist = d + w;
      if (newDist < dist[v]) {
        const oldDist = dist[v];
        dist[v] = newDist;
        heap.push({ d: newDist, node: v });
        relaxed.push({ from: u, to: v, weight: w, oldDist, newDist });
      }
    }

    const visited = [...steps[steps.length - 1].visited, u];

    const descParts = ['Pop node ' + u + ' (distance ' + d + ').'];
    if (relaxed.length) {
      descParts.push(' Relax outgoing edges.');
    } else {
      descParts.push(' No outgoing edges.');
    }

    steps.push({
      description: descParts.join(''),
      dist: { ...dist },
      heap: getHeapSnapshot(),
      visited,
      current: u,
      relaxed,
      skipped: false,
      done: false
    });
  }

  // Final step
  steps.push({
    description: 'Heap empty. Algorithm complete. Shortest distances to all reachable nodes found.',
    dist: { ...dist },
    heap: [],
    visited: [...steps[steps.length - 1].visited],
    current: null,
    relaxed: [],
    skipped: false,
    done: true
  });

  return { steps, finalDist: dist };
}
