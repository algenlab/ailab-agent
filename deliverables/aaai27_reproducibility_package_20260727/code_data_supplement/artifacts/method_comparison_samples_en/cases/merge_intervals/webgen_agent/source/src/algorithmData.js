// Problem definition and algorithm step computation for Merge Intervals

export const problemInput = {
  intervals: [[1, 3], [2, 6], [8, 10], [15, 18]]
};

export const expectedAnswer = [[1, 6], [8, 10], [15, 18]];

export const learningObjectives = [
  "Understand the state changes of the merged list during linear scan after sorting (append new interval vs extend right endpoint).",
  "Based on the overlap relationship between the current interval and the last interval in merged, predict the next operation result.",
  "Apply invariants (e.g., merged always remains non-overlapping and sorted by start time) to verify intermediate states."
];

// Compute all algorithm steps for visualization
export function computeSteps(intervals) {
  const sorted = intervals.map((iv) => [...iv]).sort((a, b) => a[0] - b[0]);
  const steps = [];
  const merged = [[...sorted[0]]];

  steps.push({
    id: 0,
    title: 'Initial State',
    description:
      'After sorting intervals by start time, initialize the merged list with the first interval [' +
      sorted[0].join(', ') +
      '].',
    merged: JSON.parse(JSON.stringify(merged)),
    currentInterval: [...sorted[0]],
    currentIndex: 0,
    action: 'init',
    sortedIntervals: sorted.map((iv) => [...iv]),
    highlightedIndex: 0,
    comparisonDetail: null
  });

  for (let i = 1; i < sorted.length; i++) {
    const current = [...sorted[i]];
    const lastBefore = [...merged[merged.length - 1]];
    const mergedBefore = JSON.parse(JSON.stringify(merged));
    let action, comparisonDetail;

    if (current[0] <= merged[merged.length - 1][1]) {
      action = 'extend';
      const oldEnd = merged[merged.length - 1][1];
      merged[merged.length - 1][1] = Math.max(merged[merged.length - 1][1], current[1]);
      comparisonDetail =
        current[0] +
        ' \u2264 ' +
        oldEnd +
        ' \u2192 Overlap detected! Extend right endpoint: max(' +
        oldEnd +
        ', ' +
        current[1] +
        ') = ' +
        merged[merged.length - 1][1];
    } else {
      action = 'append';
      merged.push([...current]);
      comparisonDetail =
        current[0] +
        ' > ' +
        lastBefore[1] +
        ' \u2192 No overlap. Append [' +
        current.join(', ') +
        '] as a new interval.';
    }

    steps.push({
      id: i,
      title: 'Step ' + i + ': Process [' + current.join(', ') + ']',
      description:
        action === 'extend'
          ? 'Since ' +
            current[0] +
            ' \u2264 ' +
            lastBefore[1] +
            ', the intervals overlap. Extend the last merged interval from [' +
            lastBefore.join(', ') +
            '] to [' +
            merged[merged.length - 1].join(', ') +
            '].'
          : 'Since ' +
            current[0] +
            ' > ' +
            lastBefore[1] +
            ', the intervals do not overlap. Append [' +
            current.join(', ') +
            '] as a new separate interval.',
      merged: JSON.parse(JSON.stringify(merged)),
      mergedBefore: mergedBefore,
      currentInterval: current,
      currentIndex: i,
      action: action,
      sortedIntervals: sorted.map((iv) => [...iv]),
      highlightedIndex: i,
      comparisonDetail: comparisonDetail,
      lastBeforeExtend: action === 'extend' ? lastBefore : null
    });
  }

  return { sorted, steps };
}

export const steps = computeSteps(problemInput.intervals).steps;

// Checkpoint definitions
export const checkpoints = [
  {
    id: 'q1',
    question:
      'Currently merged is [[1,3]], about to process interval [2,5]. Please predict the next state of merged.',
    type: 'multiple-choice',
    options: [
      { value: 'a', label: '[[1,3], [2,5]]' },
      { value: 'b', label: '[[1,5]]' },
      { value: 'c', label: '[[1,3]]' },
      { value: 'd', label: '[[2,5]]' }
    ],
    correctAnswer: 'b',
    hint: 'Check if the start of [2,5] (which is 2) overlaps with the end of [1,3] (which is 3). If 2 \u2264 3, then you must extend the right endpoint.',
    explanation:
      'Since 2 \u2264 3, the intervals [1,3] and [2,5] overlap. The merged result extends the right endpoint to max(3,5) = 5, giving [[1,5]].'
  },
  {
    id: 'q2',
    question:
      'Given sorted intervals = [[1,4],[2,3],[5,6]] and at some step merged = [[1,3],[5,6]]. Which invariant is violated?',
    type: 'multiple-choice',
    options: [
      { value: 'a', label: 'Intervals in merged are not sorted by start time.' },
      { value: 'b', label: 'The right endpoint was computed incorrectly — it should be the maximum end time of overlapping intervals processed so far.' },
      { value: 'c', label: 'An interval from the input was skipped entirely.' },
      { value: 'd', label: 'There are too many intervals in the merged list.' }
    ],
    correctAnswer: 'b',
    hint: 'After processing [1,4] and [2,3], what should the last merged interval\'s right endpoint be? Remember that [2,3] is completely inside [1,4].',
    explanation:
      'After processing [1,4] (first interval) and then [2,3], the merged result should be [[1,4]] because [2,3] is entirely contained within [1,4]. Getting [[1,3]] means the right endpoint was incorrectly reduced from 4 to 3. The invariant "the right endpoint of each merged interval equals the maximum end time among all overlapping original intervals it covers" is violated.'
  },
  {
    id: 'q3',
    question:
      'Given intervals = [[1,3],[2,6],[8,10]], if we want the merged result to become [[1,6],[8,9]], how should we modify one input interval?',
    type: 'text-input',
    correctAnswer: '8,9',
    hint: 'The first part [[1,6]] comes from merging [1,3] and [2,6]. The second part [[8,9]] needs to come from modifying the third interval. What should [8,10] become?',
    explanation:
      'Change [8,10] to [8,9]. Then the sorted intervals are [[1,3],[2,6],[8,9]]. Merging [1,3] and [2,6] gives [1,6]. Since 8 > 6, [8,9] is appended as is, yielding the desired result [[1,6],[8,9]].'
  },
  {
    id: 'q4',
    question:
      'When processing interval [4,5] and merged = [[1,3]], why is a new interval appended instead of extended?',
    type: 'multiple-choice',
    options: [
      { value: 'a', label: 'Because [4,5] starts before [1,3] ends.' },
      { value: 'b', label: 'Because 4 > 3, so there is no overlap between the intervals.' },
      { value: 'c', label: 'Because the merged list already has too many intervals.' },
      { value: 'd', label: 'Because [4,5] has a smaller range than [1,3].' }
    ],
    correctAnswer: 'b',
    hint: 'Compare the start of the new interval (4) with the end of the last merged interval (3). What does 4 > 3 tell you about overlap?',
    explanation:
      'The start of the new interval (4) is strictly greater than the end of the last merged interval (3). This means there is a gap between [1,3] and [4,5] — they do not overlap and are not even contiguous. Therefore, [4,5] must be appended as a new separate interval rather than extending [1,3].'
  }
];
