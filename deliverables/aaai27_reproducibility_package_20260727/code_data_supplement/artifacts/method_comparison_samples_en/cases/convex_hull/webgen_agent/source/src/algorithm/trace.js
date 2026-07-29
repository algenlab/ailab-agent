// Cross product: (a - o) x (b - o)
// Positive = counterclockwise (left turn), Negative = clockwise (right turn), Zero = collinear
export function cross(o, a, b) {
  return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
}

export const inputPoints = [[0, 0], [1, 1], [2, 0], [1, 2]];

// Sorted lexicographically: by x, then by y
export const sortedPoints = [[0, 0], [1, 1], [1, 2], [2, 0]];

export const expectedOutput = [[0, 0], [2, 0], [1, 2]];

// Full algorithm trace with every intermediate state
export const trace = [
  {
    step: 0,
    title: 'Initial State',
    description:
      'We are given 4 delivery points. The goal is to compute the convex hull — the smallest convex polygon enclosing all points — using Andrew\u2019s monotone chain algorithm.',
    phase: 'initial',
    currentPointIdx: -1,
    lowerHull: [],
    upperHull: [],
    finalHull: null,
    crossInfo: null,
    action: null,
    highlightLowerIdx: -1,
    poppedIndices: [],
  },
  {
    step: 1,
    title: 'Sort Points',
    description:
      'Andrew\u2019s algorithm begins by sorting all points lexicographically: first by x-coordinate, then by y-coordinate. Sorted order: [(0,0), (1,1), (1,2), (2,0)].',
    phase: 'sort',
    currentPointIdx: -1,
    lowerHull: [],
    upperHull: [],
    finalHull: null,
    crossInfo: null,
    action: 'sort',
    highlightLowerIdx: -1,
    poppedIndices: [],
  },
  {
    step: 2,
    title: 'Lower Hull — Add First Point',
    description:
      'Start building the lower hull from left to right. The first sorted point (0,0) is added to the empty lower hull.',
    phase: 'lower',
    currentPointIdx: 0,
    lowerHull: [[0, 0]],
    upperHull: [],
    finalHull: null,
    crossInfo: null,
    action: 'add',
    highlightLowerIdx: -1,
    poppedIndices: [],
  },
  {
    step: 3,
    title: 'Lower Hull — Add Second Point',
    description:
      'Point (1,1) is added. With only two points in the hull, no cross-product check is needed yet.',
    phase: 'lower',
    currentPointIdx: 1,
    lowerHull: [[0, 0], [1, 1]],
    upperHull: [],
    finalHull: null,
    crossInfo: null,
    action: 'add',
    highlightLowerIdx: -1,
    poppedIndices: [],
  },
  {
    step: 4,
    title: 'Lower Hull — Process (1,2), Cross > 0',
    description:
      'Processing point (1,2). Cross product of the last two hull points and the new point: cross((0,0), (1,1), (1,2)) = 1 > 0. Since cross > 0, the turn is counterclockwise — valid for the lower hull. Point (1,2) is added.',
    phase: 'lower',
    currentPointIdx: 2,
    lowerHull: [[0, 0], [1, 1], [1, 2]],
    upperHull: [],
    finalHull: null,
    crossInfo: { o: [0, 0], a: [1, 1], b: [1, 2], value: 1, decision: 'add' },
    action: 'add',
    highlightLowerIdx: -1,
    poppedIndices: [],
  },
  {
    step: 5,
    title: 'Lower Hull — Process (2,0), Cross \u2264 0 — Backtrack',
    description:
      'Processing point (2,0). Cross((1,1), (1,2), (2,0)) = \u22121 \u2264 0. The turn is clockwise — this breaks convexity! Pop (1,2). Then cross((0,0), (1,1), (2,0)) = \u22122 \u2264 0 — still not convex. Pop (1,1). Finally, add (2,0). Lower hull: [(0,0), (2,0)].',
    phase: 'lower',
    currentPointIdx: 3,
    lowerHull: [[0, 0], [2, 0]],
    upperHull: [],
    finalHull: null,
    crossInfo: { o: [1, 1], a: [1, 2], b: [2, 0], value: -1, decision: 'pop', extraChecks: [{ o: [0, 0], a: [1, 1], b: [2, 0], value: -2, decision: 'pop' }] },
    action: 'pop-add',
    highlightLowerIdx: -1,
    poppedIndices: [1, 2],
  },
  {
    step: 6,
    title: 'Lower Hull — Complete',
    description:
      'The lower hull construction is finished. Result: [(0,0), (2,0)]. These two points form the bottom edge of the convex hull.',
    phase: 'lower-done',
    currentPointIdx: -1,
    lowerHull: [[0, 0], [2, 0]],
    upperHull: [],
    finalHull: null,
    crossInfo: null,
    action: null,
    highlightLowerIdx: -1,
    poppedIndices: [],
  },
  {
    step: 7,
    title: 'Upper Hull — Start from Right',
    description:
      'Now we build the upper hull, traversing the sorted points from right to left. The rightmost point (2,0) is added to the empty upper hull.',
    phase: 'upper',
    currentPointIdx: 3,
    lowerHull: [[0, 0], [2, 0]],
    upperHull: [[2, 0]],
    finalHull: null,
    crossInfo: null,
    action: 'add',
    highlightLowerIdx: -1,
    poppedIndices: [],
  },
  {
    step: 8,
    title: 'Upper Hull — Process (1,2)',
    description:
      'Point (1,2) is added to the upper hull. With only two points, no cross-product check is needed.',
    phase: 'upper',
    currentPointIdx: 2,
    lowerHull: [[0, 0], [2, 0]],
    upperHull: [[2, 0], [1, 2]],
    finalHull: null,
    crossInfo: null,
    action: 'add',
    highlightLowerIdx: -1,
    poppedIndices: [],
  },
  {
    step: 9,
    title: 'Upper Hull — Process (1,1), Cross > 0',
    description:
      'Processing point (1,1). Cross((2,0), (1,2), (1,1)) = 1 > 0. Valid counterclockwise turn — point is added.',
    phase: 'upper',
    currentPointIdx: 1,
    lowerHull: [[0, 0], [2, 0]],
    upperHull: [[2, 0], [1, 2], [1, 1]],
    finalHull: null,
    crossInfo: { o: [2, 0], a: [1, 2], b: [1, 1], value: 1, decision: 'add' },
    action: 'add',
    highlightLowerIdx: -1,
    poppedIndices: [],
  },
  {
    step: 10,
    title: 'Upper Hull — Process (0,0), Backtrack',
    description:
      'Processing point (0,0). Cross((1,2), (1,1), (0,0)) = \u22121 \u2264 0 — backtrack! Pop (1,1). Re-check: cross((2,0), (1,2), (0,0)) = 4 > 0 — valid. Add (0,0). Upper hull: [(2,0), (1,2), (0,0)].',
    phase: 'upper',
    currentPointIdx: 0,
    lowerHull: [[0, 0], [2, 0]],
    upperHull: [[2, 0], [1, 2], [0, 0]],
    finalHull: null,
    crossInfo: { o: [1, 2], a: [1, 1], b: [0, 0], value: -1, decision: 'pop', extraChecks: [{ o: [2, 0], a: [1, 2], b: [0, 0], value: 4, decision: 'add' }] },
    action: 'pop-add',
    highlightLowerIdx: -1,
    poppedIndices: [],
  },
  {
    step: 11,
    title: 'Upper Hull — Complete',
    description:
      'The upper hull construction is finished. Result: [(2,0), (1,2), (0,0)].',
    phase: 'upper-done',
    currentPointIdx: -1,
    lowerHull: [[0, 0], [2, 0]],
    upperHull: [[2, 0], [1, 2], [0, 0]],
    finalHull: null,
    crossInfo: null,
    action: null,
    highlightLowerIdx: -1,
    poppedIndices: [],
  },
  {
    step: 12,
    title: 'Combine Hulls',
    description:
      'Remove the last point from each hull to avoid duplicate endpoints, then concatenate: lower[:-1] + upper[:-1] = [(0,0)] + [(2,0), (1,2)] = [(0,0), (2,0), (1,2)].',
    phase: 'combine',
    currentPointIdx: -1,
    lowerHull: [[0, 0], [2, 0]],
    upperHull: [[2, 0], [1, 2], [0, 0]],
    finalHull: [[0, 0], [2, 0], [1, 2]],
    crossInfo: null,
    action: 'combine',
    highlightLowerIdx: -1,
    poppedIndices: [],
  },
  {
    step: 13,
    title: 'Done — Convex Hull Found',
    description:
      'The convex hull vertices in counterclockwise order are [(0,0), (2,0), (1,2)]. The algorithm has successfully found the smallest convex polygon enclosing all delivery points.',
    phase: 'done',
    currentPointIdx: -1,
    lowerHull: [[0, 0], [2, 0]],
    upperHull: [[2, 0], [1, 2], [0, 0]],
    finalHull: [[0, 0], [2, 0], [1, 2]],
    crossInfo: null,
    action: null,
    highlightLowerIdx: -1,
    poppedIndices: [],
  },
];

// Checkpoints triggered at specific steps
export const checkpoints = [
  {
    id: 1,
    triggerStep: 5,
    title: 'Checkpoint: Predict Backtracking',
    question:
      'The lower hull currently contains [(0,0), (1,1), (1,2)]. When processing point (2,0), the cross product cross((1,1), (1,2), (2,0)) = \u22121, which is \u2264 0. What will the algorithm do next?',
    options: [
      { key: 'A', text: 'Add (2,0) directly: lower becomes [(0,0), (1,1), (1,2), (2,0)]' },
      { key: 'B', text: 'Pop (1,2) from the lower hull and re-check the cross product' },
      { key: 'C', text: 'Skip (2,0) and immediately start upper hull construction' },
      { key: 'D', text: 'Restart the entire lower hull from scratch' },
    ],
    correctKey: 'B',
    hint: 'When cross \u2264 0, the last added point creates a non-convex (clockwise or collinear) turn. The algorithm removes it to restore convexity before re-checking.',
    explanation:
      'Correct! Since cross = \u22121 \u2264 0, point (1,2) breaks convexity. The algorithm pops it and re-checks with the new last point (1,1). After cross((0,0), (1,1), (2,0)) = \u22122 \u2264 0 as well, (1,1) is also popped. Finally, (2,0) is added, yielding lower = [(0,0), (2,0)].',
  },
  {
    id: 2,
    triggerStep: 10,
    title: 'Checkpoint: Upper Hull Backtracking',
    question:
      'During upper hull construction, the hull contains [(2,0), (1,2), (1,1)]. When processing (0,0), cross((1,2), (1,1), (0,0)) = \u22121 \u2264 0. What happens?',
    options: [
      { key: 'A', text: '(0,0) is simply appended to the upper hull' },
      { key: 'B', text: '(1,1) is popped first, then (0,0) is added after a successful re-check' },
      { key: 'C', text: 'The upper hull construction is abandoned and restarted' },
      { key: 'D', text: 'The algorithm skips (0,0) entirely' },
    ],
    correctKey: 'B',
    hint: 'The upper hull uses the same cross \u2264 0 rule to detect when backtracking is needed — just like the lower hull.',
    explanation:
      'Correct! The cross value of \u22121 indicates a non-convex turn involving (1,1). After popping (1,1) and re-checking, cross((2,0), (1,2), (0,0)) = 4 > 0 is valid, so (0,0) is added. Upper hull becomes [(2,0), (1,2), (0,0)].',
  },
  {
    id: 3,
    triggerStep: 12,
    title: 'Checkpoint: Final Combination',
    question:
      'To form the final convex hull, how are the lower hull [(0,0), (2,0)] and upper hull [(2,0), (1,2), (0,0)] combined?',
    options: [
      { key: 'A', text: 'Concatenate directly: lower + upper = [(0,0), (2,0), (2,0), (1,2), (0,0)]' },
      { key: 'B', text: 'Remove the last point of each hull, then concatenate: lower[:-1] + upper[:-1]' },
      { key: 'C', text: 'Only the upper hull is used as the final result' },
      { key: 'D', text: 'Re-sort all hull points by polar angle around the centroid' },
    ],
    correctKey: 'B',
    hint: 'Both hulls share the first and last sorted points. Removing the last point from each before concatenation avoids duplicate endpoints.',
    explanation:
      'Correct! lower[:-1] = [(0,0)] and upper[:-1] = [(2,0), (1,2)]. Concatenating gives [(0,0), (2,0), (1,2)] — the final convex hull vertices in counterclockwise order.',
  },
];