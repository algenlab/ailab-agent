import { ProblemInput, Checkpoint } from './types';

export const INITIAL_INPUT: ProblemInput = {
  nums: [2, 1, 4, 5],
  query: [1, 3],
  update: [2, 6],
};

export const INITIAL_CHECKPOINTS: Checkpoint[] = [
  {
    id: 1,
    question:
      'When querying the range query=[1,3] on the segment tree, the current visited node seg_0_1 (covering [0,1], partial overlap), which two child nodes should be visited next?',
    correctAnswer: 'seg_0_0 and seg_1_1, or nodes [0,0] and [1,1]',
    context: 'query',
  },
  {
    id: 2,
    question:
      'After construction, the sum of node seg_0_3 is 12, its left child seg_0_1 sum=3, right child seg_2_3 sum=9. Write the equation that satisfies the relationship among the three.',
    correctAnswer: 'sum(seg_0_3) = sum(seg_0_1) + sum(seg_2_3), or 12 = 3 + 9',
    context: 'built',
  },
  {
    id: 3,
    question:
      'In the original problem, update=[2,6] changes nums[2] from 4 to 6, and the corrected sum for interval [1,3] is 12. If you want the corrected interval sum to become 15, what should the value in update be changed to?',
    correctAnswer: '9, or value = 9',
    context: 'update',
  },
  {
    id: 4,
    question:
      'When constructing the leaf node seg_3_3 of the segment tree, why does its sum equal nums[3]? Explain using specific values from the array.',
    correctAnswer: 'Because nums[3] = 5, and a leaf covering [3,3] has sum equal to that single element, 5.',
    context: 'built',
  },
];

export const SAMPLE_HINTS: Record<number, string> = {
  1: 'Hint: The node seg_0_1 covers [0,1]. Its children would each cover a single index: one covers [0,0] and the other covers [1,1].',
  2: 'Hint: A parent node in a segment tree always stores the sum of its two children. Write the equation using sum() notation.',
  3: 'Hint: The current after-sum is 12 with update value 6. You need the sum to increase by 3 more (from 12 to 15). Since only one leaf changes, adjust the update value accordingly.',
  4: 'Hint: A leaf node covers exactly one index. Look at the value of nums[3] in the input array [2, 1, 4, 5].',
};

export const SAMPLE_ANSWERS: Record<number, string> = {
  1: 'seg_0_0 and seg_1_1 (nodes covering [0,0] and [1,1])',
  2: 'sum(seg_0_3) = sum(seg_0_1) + sum(seg_2_3) → 12 = 3 + 9',
  3: '9 (because 6 + 3 = 9, and the interval sum becomes 12 + 3 = 15)',
  4: 'nums[3] = 5, so the leaf node seg_3_3 covering [3,3] has sum = 5',
};
