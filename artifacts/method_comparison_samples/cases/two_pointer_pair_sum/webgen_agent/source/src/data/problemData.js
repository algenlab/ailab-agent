export const PROBLEM_DATA = {
  nums: [1, 2, 4, 6, 10],
  target: 8,
  expectedAnswer: [1, 3],
};

export const LEARNING_OBJECTIVES = [
  "理解双指针在升序价格列表中通过比较当前和与 target 决定移动方向的状态转移。",
  "识别左指针递增、右指针递减的不变式，以及搜索区间的收缩性质。",
  "能够根据任意一步的 nums[left]、nums[right] 和 sum 预测下一步指针移动。",
];

export const QUIZ_QUESTIONS = [
  {
    id: 'pointer_direction',
    template: '当前左指针下标 {left}，价格 {leftVal}，右指针下标 {right}，价格 {rightVal}，总和 {sum}，target={target}。下一步应移动哪个指针？',
    optionsTemplate: ['左指针右移（left++）', '右指针左移（right--）'],
    getCorrectIndex: (sum, target) => sum < target ? 0 : 1,
    getCorrectAnswer: (sum, target) => sum < target ? '左指针右移（left++）' : '右指针左移（right--）',
  }
];