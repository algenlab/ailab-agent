// Algorithm steps for Two Sum in Sorted Array
// nums = [1, 2, 4, 6, 10], target = 8

export const problemData = {
  nums: [1, 2, 4, 6, 10],
  target: 8,
  expectedAnswer: [1, 3]
};

export const algorithmSteps = [
  {
    id: 0,
    phase: 'init',
    leftIdx: 0,
    rightIdx: 4,
    leftVal: 1,
    rightVal: 10,
    sum: 11,
    target: 8,
    compareResult: 'greater',
    actionText: '11 > 8 (target) — sum is too large, move right pointer left to decrease sum',
    pointerMovement: 'right',
    isFound: false,
    description: 'Initialize both pointers at the ends of the sorted array. Compare the sum with the target.'
  },
  {
    id: 1,
    phase: 'searching',
    leftIdx: 0,
    rightIdx: 3,
    leftVal: 1,
    rightVal: 6,
    sum: 7,
    target: 8,
    compareResult: 'less',
    actionText: '7 < 8 (target) — sum is too small, move left pointer right to increase sum',
    pointerMovement: 'left',
    isFound: false,
    description: 'The sum is still below the target. Since the array is sorted, moving the left pointer right will point to a larger value.'
  },
  {
    id: 2,
    phase: 'found',
    leftIdx: 1,
    rightIdx: 3,
    leftVal: 2,
    rightVal: 6,
    sum: 8,
    target: 8,
    compareResult: 'equal',
    actionText: '8 == 8 (target) — match found! Return indices [1, 3]',
    pointerMovement: null,
    isFound: true,
    description: 'The sum equals the target. The two items with prices 2 and 6 (indices 1 and 3) satisfy the voucher amount of 8.'
  }
];

export const checkpoints = {
  q1: {
    id: 'q1',
    stepId: 0,
    title: 'Checkpoint: Pointer Decision',
    question: 'At the current state — left pointer at index 0 (price 1), right pointer at index 4 (price 10), sum = 11, target = 8. Which pointer should be moved next?',
    options: [
      'Move left pointer right (increase left index)',
      'Move right pointer left (decrease right index)',
      'Move both pointers inward simultaneously',
      'Stop searching — no solution exists'
    ],
    correctIndex: 1,
    hint: 'Compare the current sum (11) with the target (8). Since 11 > 8, the sum exceeds the target. To decrease the sum in a sorted ascending array, which pointer should move?',
    explanation: 'Since the current sum (11) is greater than the target (8), we need a smaller sum. Because the array is sorted in ascending order, moving the right pointer left selects a smaller element (from 10 down to 6), which decreases the sum toward the target.',
    feedbackCorrect: 'Correct! Since 11 > 8, the sum exceeds the target. Moving the right pointer left decreases the sum by selecting a smaller element.',
    feedbackIncorrect: 'Not quite. The sum (11) is greater than the target (8), so we need to decrease the sum. In a sorted ascending array, moving the right pointer left achieves this.'
  },
  q2: {
    id: 'q2',
    stepId: 1,
    title: 'Checkpoint: Why Not Move Right Pointer Right?',
    question: 'At step 1, sum = 7 < target = 8. The algorithm correctly moves the left pointer right to increase the sum. Why would moving the right pointer right be the wrong choice here?',
    options: [
      'Moving the right pointer right would immediately go out of bounds',
      'Moving the right pointer right would revisit larger elements that were already eliminated from consideration, breaking the algorithm\'s O(n) efficiency',
      'Moving the right pointer right would make the sum even smaller',
      'The right pointer is not allowed to move at all in this algorithm'
    ],
    correctIndex: 1,
    hint: 'Think about the history of the right pointer. It started at the end and moved left past certain positions. What does moving it back mean for the pairs we have already ruled out?',
    explanation: 'The right pointer started at the maximum element and has only moved left. Each time it moved left past a position, the algorithm implicitly ruled out all pairs involving that position with any left-side element. Moving the right pointer back to the right would reconsider already-eliminated pairs, violating the algorithm\'s invariant and potentially causing an infinite loop.',
    feedbackCorrect: 'Exactly! The right pointer has already eliminated those positions. Moving it back would reconsider pairs that have been ruled out, breaking the O(n) guarantee.',
    feedbackIncorrect: 'Consider: the right pointer previously moved left past certain positions. Those positions were eliminated because even the largest remaining element combined with the current left element was too large (or too small). Moving right again would undo that progress.'
  },
  q3: {
    id: 'q3',
    stepId: 2,
    title: 'Checkpoint: Algorithm Invariant',
    question: 'During the entire execution of the two-pointer algorithm on a sorted array, which of the following conditions is guaranteed to always hold true?',
    options: [
      'A. left <= right (the left pointer never crosses past the right pointer during search)',
      'B. nums[left] + nums[right] == target (the sum always equals the target)',
      'C. left + right == len(nums) - 1 (the indices always sum to n-1)',
      'D. There is always at least one valid pair in the array'
    ],
    correctIndex: 0,
    hint: 'Consider the starting positions (left = 0, right = n-1) and how they move. Left only increases, right only decreases. What must be true until they meet?',
    explanation: 'Option A is correct. The left pointer starts at index 0 and only moves right (increases). The right pointer starts at index n-1 and only moves left (decreases). The algorithm terminates when left >= right, so during the active search, left <= right always holds. Options B and D are not guaranteed (there may be no solution), and C is only true at the very first step.',
    feedbackCorrect: 'Correct! The invariant left <= right holds throughout the search because left only increases and right only decreases, and the algorithm stops when they meet or cross.',
    feedbackIncorrect: 'Think about how the pointers move: left starts at 0 and only goes up; right starts at n-1 and only goes down. Which relationship between them is always maintained?'
  },
  q4: {
    id: 'q4',
    stepId: 2,
    title: 'Checkpoint: No-Solution Scenario',
    question: 'Which of the following modified arrays (still in ascending order) would cause the two-pointer algorithm to return an empty list for target = 8? In other words, which array has no two elements summing to 8?',
    options: [
      '[1, 2, 4, 7, 10]',
      '[1, 3, 4, 6, 10]',
      '[1, 2, 4, 6, 8]',
      '[0, 2, 4, 6, 10]'
    ],
    correctIndex: 1,
    hint: 'For each array, check all possible pairs. Is there any pair of numbers that adds up to exactly 8? Remember: the two numbers must be at different indices.',
    explanation: '[1, 3, 4, 6, 10] has no pair summing to 8:\n- 1+3=4, 1+4=5, 1+6=7, 1+10=11\n- 3+4=7, 3+6=9, 3+10=13\n- 4+6=10, 4+10=14\n- 6+10=16\n\nThe other arrays all contain valid pairs: [1,2,4,7,10] has 1+7=8; [1,2,4,6,8] has 2+6=8; [0,2,4,6,10] has 2+6=8.',
    feedbackCorrect: 'Correct! [1, 3, 4, 6, 10] has no pair summing to 8. Every other option contains at least one valid pair.',
    feedbackIncorrect: 'Check each array carefully. Do any two elements sum to exactly 8? Try every combination.'
  }
};

// Map step IDs to the checkpoints that should appear at that step
export const stepCheckpointsMap = {
  0: ['q1'],
  1: ['q2'],
  2: ['q3', 'q4']
};