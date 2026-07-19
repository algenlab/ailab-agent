/**
 * Checkpoint definitions.
 * Each checkpoint has a type: 'numeric' or 'mcq'.
 * Numeric checkpoints accept an integer answer.
 * MCQ checkpoints accept the index of the correct option (0-based).
 */
const checkpoints = [
  {
    id: 1,
    type: 'numeric',
    question:
      'Currently computing dp[2][3]; above it dp[1][3] = 4, to its left dp[2][2] = 6. Predict what the value of dp[2][3] should be.',
    answer: 10,
    hints: [
      'The recurrence is dp[i][j] = dp[i-1][j] + dp[i][j-1].',
      'Add the value above (4) and the value to the left (6).',
      '4 + 6 = ?',
    ],
    answerDisplay: '10',
    relatedStep: 16,
    explanation:
      'dp[2][3] = dp[1][3] + dp[2][2] = 4 + 6 = 10. The robot can reach (2,3) either by coming down from (1,3) or coming right from (2,2).',
  },
  {
    id: 2,
    type: 'mcq',
    question:
      'Observe the DP table; the values of the first row dp[0][j] and first column dp[i][0] are always 1. Why do they not change?',
    options: [
      'Because the robot can only move right or down. To reach any cell in the first row, the robot must move only right from the start — exactly one path. Similarly, to reach any cell in the first column, the robot must move only down — exactly one path.',
      'Because 1 is the smallest positive integer and all DP tables must start with 1 as a convention.',
      'Because the grid initializes every cell to 1 before the DP computation begins, and those cells are never updated.',
      'Because those cells are boundary padding with no physical meaning in the warehouse.',
    ],
    answer: 0,
    hints: [
      'Think about the movement constraints: the robot can only go right or down.',
      'If the robot can only go right, how many distinct ways are there to reach any cell in the top row? Just one — keep going right.',
      'The correct answer is the first option. The movement rules force exactly one path for first-row and first-column cells.',
    ],
    answerDisplay: 'Option A',
    relatedStep: null,
  },
  {
    id: 3,
    type: 'numeric',
    question:
      'If the grid changes from m = 3, n = 7 to m = 4, n = 7 (adding one more row), what will be the new total number of paths? Use the combination formula C(m+n-2, n-1) or reason from the DP table.',
    answer: 84,
    hints: [
      'With m = 4 and n = 7, the robot must make (m-1) = 3 down moves and (n-1) = 6 right moves, for a total of 9 moves.',
      'The number of paths is C(9, 3) = C(9, 6) — choose which 3 of the 9 moves are down moves.',
      'C(9, 3) = 9 × 8 × 7 / (3 × 2 × 1) = 504 / 6 = 84.',
    ],
    answerDisplay: '84',
    relatedStep: null,
    explanation:
      'C(m+n-2, n-1) = C(4+7-2, 6) = C(9, 6) = C(9, 3) = 84. You can also extend the DP table: row 3 becomes [1, 4, 10, 20, 35, 56, 84].',
  },
  {
    id: 4,
    type: 'mcq',
    question:
      'Explain why dp[2][3] equals the sum of dp[1][3] and dp[2][2]. Use the robot movement rules in your reasoning.',
    options: [
      'Because 2 + 3 = 5 and the DP formula is always dp[i][j] = i + j regardless of the grid.',
      'Because the robot can only move right or down. To reach cell (2,3), the very last move must be either a down-move from (1,3) or a right-move from (2,2). All paths to (2,3) are therefore exactly the paths to (1,3) plus the paths to (2,2).',
      'Because DP tables always sum the row and column indices, and dp[2][3] sits at the intersection.',
      'Because the problem requires the total sum of all paths and addition is the only arithmetic operation allowed in DP.',
    ],
    answer: 1,
    hints: [
      'Consider the last move the robot makes before reaching (2,3). Where could it have come from?',
      'The robot can only step right or down. So the cell before (2,3) must be either the cell above or the cell to the left.',
      'The correct answer is the second option. Every path to (2,3) passes through either (1,3) or (2,2) on its final step.',
    ],
    answerDisplay: 'Option B',
    relatedStep: 16,
  },
];

export default checkpoints;
