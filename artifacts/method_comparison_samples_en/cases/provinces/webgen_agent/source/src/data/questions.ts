/**
 * Learner checkpoint questions.
 *
 * All questions correspond to the reference problem input.
 * Answers are derived from the precomputed algorithm steps.
 */

import { allSteps, expectedAnswer, problemInput } from './problemData';

export interface CheckpointQuestion {
  id: number;
  /** The question text */
  question: string;
  /** Multiple choice options */
  options: string[];
  /** Index of the correct option (0-based) */
  correctIndex: number;
  /** Explanation shown after answering */
  explanation: string;
  /** Which step in the algorithm this question relates to */
  relatedStepIndex: number;
}

export const checkpointQuestions: CheckpointQuestion[] = [
  {
    id: 1,
    question:
      'Current state: processing i=0, j=1, isConnected[0][1]=1, and find(0)=0, find(1)=1. Predict how the parent array will change after executing union.',
    options: [
      'parent[0] becomes 1',
      'parent[1] becomes 0',
      'parent[0] and parent[1] both become 0',
      'parent[0] and parent[1] both become 1',
    ],
    correctIndex: 1,
    explanation:
      'Since find(0)=0 and find(1)=1 and they differ, a union is performed. We attach root 1 under root 0, so parent[1] becomes 0. The parent array changes from [0,1,2] to [0,0,2].',
    relatedStepIndex: 1,
  },
  {
    id: 2,
    question:
      'Throughout the algorithm, the parent array maintains a key invariant. Select the correct description:',
    options: [
      'All elements in the parent array are distinct.',
      'For any node i, following parent pointers from i eventually reaches a root node where parent[root] === root.',
      'The parent array is always sorted in ascending order.',
      'Every node directly points to node 0.',
    ],
    correctIndex: 1,
    explanation:
      'The Union-Find (disjoint-set) data structure guarantees that by following parent pointers from any node, you always reach a root where parent[root] === root. This is the fundamental invariant of the data structure.',
    relatedStepIndex: 0,
  },
  {
    id: 3,
    question:
      'In the given isConnected matrix, if we change isConnected[0][2] from 0 to 1 (along with isConnected[2][0] to keep symmetry), what would be the new expected number of provinces?',
    options: ['1 province', '2 provinces', '3 provinces', '0 provinces'],
    correctIndex: 0,
    explanation:
      'Originally, computers 0 and 1 form one province, and computer 2 forms a second province. Adding a connection between 0 and 2 merges all three computers into a single province, so the answer becomes 1.',
    relatedStepIndex: -1,
  },
  {
    id: 4,
    question:
      'During tracing, step 3 (index 1) executed a union operation. Explain why union is needed at this step and how it affects the province structure.',
    options: [
      'Union is needed because both computers are isolated. After union, the province count increases.',
      'Union is needed because isConnected[0][1] = 1 and the two computers belong to different provinces (roots differ). After union, they merge into one province, reducing the province count.',
      'Union is performed at every step regardless of connection. The province count stays the same.',
      'Union is needed to disconnect computers. The province count increases by 1.',
    ],
    correctIndex: 1,
    explanation:
      'When isConnected[0][1] = 1, find(0) = 0 and find(1) = 1 differ, indicating they are in separate provinces. The union merges both into one province, reducing the total province count from 3 to 2.',
    relatedStepIndex: 1,
  },
];
