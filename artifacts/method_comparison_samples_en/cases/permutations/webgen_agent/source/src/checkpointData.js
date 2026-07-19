export const checkpoints = [
  {
    id: 1,
    question:
      'In the backtracking search, the current path is [1], used is [True, False, False], and nums = [1, 2, 3]. Predict the next number to be added to path.',
    options: ['1', '2', '3'],
    correctIndex: 1,
    hint: 'Look at the used array: [True, False, False]. The element at index 0 is already used (True). The algorithm iterates from index 0 and finds the first index where used[i] is False. Which index is that?',
    answerExplanation:
      'Since used[0] is True (meaning 1 is already in the path), the algorithm checks used[1] next. used[1] is False, so it selects nums[1] = 2. The next number added will be 2.',
    feedbackCorrect: 'Correct! The algorithm scans from left to right and picks the first unused number, which is 2 at index 1.',
    feedbackIncorrect:
      'Not quite. Think about which numbers are still available (where used[i] is False). The first such number is selected.'
  },
  {
    id: 2,
    question:
      'During the process of generating all permutations, what does the length of the path array always equal?',
    options: [
      'The recursion depth',
      'The number of True values in the used array',
      'Both of the above',
      'Neither of the above'
    ],
    correctIndex: 2,
    hint: 'When you push an element onto path, you also mark one used entry as True and go one level deeper in recursion. When you pop, the reverse happens. All three quantities change together.',
    answerExplanation:
      'The path length always equals both the recursion depth and the count of True values in the used array. This is a key invariant: when you push, all three increase by 1; when you pop, all three decrease by 1.',
    feedbackCorrect:
      'Exactly right! The path length, recursion depth, and count of used elements are always equal — this is a fundamental invariant of the backtracking algorithm.',
    feedbackIncorrect:
      'Consider: when you add an element to path, you also go one level deeper in recursion AND mark one more used entry as True. All three quantities increase together. When you backtrack, all three decrease together.'
  },
  {
    id: 3,
    question:
      "If the input array nums becomes ['a', 'b', 'c'] (characters instead of numbers), does the backtracking algorithm that uses index-based tracking with the used array need to be adjusted?",
    options: [
      'Yes, the algorithm needs significant changes for characters.',
      'No, the index-based backtracking works regardless of the element type.',
      'Yes, but only the comparison logic needs to change.',
      'No, but only if all characters are unique.'
    ],
    correctIndex: 1,
    hint: 'The used array tracks indices (positions), not the values themselves. The algorithm decides which element to pick based on whether its index is marked used, regardless of what value is stored at that index.',
    answerExplanation:
      'No adjustment is needed. The backtracking algorithm uses index-based tracking with the used array. It selects elements by index, not by value. As long as elements are unique (or you want permutations of positions), the algorithm works identically for numbers, characters, strings, or any other data type.',
    feedbackCorrect:
      'Correct! The algorithm operates on indices, not values. The used array tracks which positions have been selected, so the element type is irrelevant.',
    feedbackIncorrect:
      'Think about what the used array actually tracks. It tracks indices (0, 1, 2), not the values at those indices. The algorithm selects by position, so the type of data does not matter.'
  },
  {
    id: 4,
    question:
      'After completing the permutation [1, 2, 3] for nums = [1, 2, 3], the algorithm executes path.pop() and sets used[2] = False. Explain what this state transition represents.',
    options: [
      'The algorithm is starting over from the beginning.',
      'The algorithm is backtracking: undoing the choice of 3 to try alternative numbers at depth 2.',
      'The algorithm found a duplicate and is removing it.',
      'The algorithm has finished generating all permutations.'
    ],
    correctIndex: 1,
    hint: 'After finding [1,2,3], the path is [1,2,3] and used is [T,T,T]. Popping 3 and unmarking used[2] returns to path=[1,2], used=[T,T,F]. At this point, the loop at depth 2 has exhausted index 2, so it will also backtrack further. What is the purpose of undoing choices?',
    answerExplanation:
      'This is the backtracking step. After completing [1,2,3], the algorithm pops 3 (the last choice) and unmarks it, returning to the state path=[1,2], used=[T,T,F]. From here, the for-loop at depth 2 has no more choices (only index 2 was left and we just tried it), so it will continue backtracking by popping 2 as well, eventually allowing the algorithm to try [1,3,...] next.',
    feedbackCorrect:
      'Correct! This is the essence of backtracking — undoing the most recent choice to explore alternative paths. After popping 3, the algorithm can try other numbers at that position, and if none remain, it backtracks further.',
    feedbackIncorrect:
      'Consider: after finishing [1,2,3], popping the last element returns the algorithm to path=[1,2]. This allows it to try a different number instead of 3 (if any remain) or to backtrack further. This undoing is the core mechanism of backtracking.'
  }
];