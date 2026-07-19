import { StepData, ProblemInput } from './types';

class MinHeap {
  private data: number[] = [];

  clone(): number[] {
    return [...this.data];
  }

  size(): number {
    return this.data.length;
  }

  top(): number | null {
    return this.data.length > 0 ? this.data[0] : null;
  }

  push(val: number): void {
    this.data.push(val);
    let i = this.data.length - 1;
    while (i > 0) {
      const p = Math.floor((i - 1) / 2);
      if (this.data[p] <= this.data[i]) break;
      [this.data[p], this.data[i]] = [this.data[i], this.data[p]];
      i = p;
    }
  }

  pop(): number | undefined {
    if (this.data.length === 0) return undefined;
    if (this.data.length === 1) return this.data.pop();
    const top = this.data[0];
    this.data[0] = this.data.pop()!;
    let i = 0;
    while (true) {
      let smallest = i;
      const l = 2 * i + 1;
      const r = 2 * i + 2;
      if (l < this.data.length && this.data[l] < this.data[smallest])
        smallest = l;
      if (r < this.data.length && this.data[r] < this.data[smallest])
        smallest = r;
      if (smallest === i) break;
      [this.data[i], this.data[smallest]] = [this.data[smallest], this.data[i]];
      i = smallest;
    }
    return top;
  }
}

function describeAction(
  val: number,
  action: 'push' | 'push-and-pop' | 'ignore',
  heapBefore: number[],
  heapAfter: number[],
  k: number
): string {
  const topAfter = heapAfter.length > 0 ? heapAfter[0] : null;
  switch (action) {
    case 'push':
      return `堆未满(size=${heapBefore.length}<k=${k})，直接将元素 ${val} 加入堆。堆顶现在是 ${topAfter}。`;
    case 'push-and-pop':
      return `堆已满且新元素 ${val} > 堆顶 ${heapBefore[0]}，先弹出堆顶 ${heapBefore[0]}，再插入 ${val}。堆顶更新为 ${topAfter}。`;
    case 'ignore':
      return `堆已满且新元素 ${val} ≤ 堆顶 ${heapBefore[0]}，该元素不可能是前 ${k} 大，直接忽略。堆顶保持 ${topAfter}。`;
  }
}

export function generateSteps(input: ProblemInput): StepData[] {
  const { nums, k } = input;
  const heap = new MinHeap();
  const steps: StepData[] = [];

  for (let i = 0; i < nums.length; i++) {
    const val = nums[i];
    const heapBefore = heap.clone();
    let action: 'push' | 'push-and-pop' | 'ignore';

    if (heap.size() < k) {
      heap.push(val);
      action = 'push';
    } else if (val > (heap.top() ?? -Infinity)) {
      heap.pop();
      heap.push(val);
      action = 'push-and-pop';
    } else {
      action = 'ignore';
    }

    const heapAfter = heap.clone();

    steps.push({
      stepIndex: i,
      element: val,
      heapBefore,
      heapAfter,
      action,
      heapTop: heap.top(),
      heapSize: heap.size(),
      description: describeAction(val, action, heapBefore, heapAfter, k),
    });
  }

  return steps;
}

export function getFinalAnswer(input: ProblemInput): number | null {
  const heap = new MinHeap();
  for (const val of input.nums) {
    if (heap.size() < input.k) {
      heap.push(val);
    } else if (val > (heap.top() ?? -Infinity)) {
      heap.pop();
      heap.push(val);
    }
  }
  return heap.top();
}

export const PROBLEM_INPUT: ProblemInput = {
  k: 2,
  nums: [3, 2, 1, 5, 6, 4],
};

export const QUIZ_QUESTIONS: import('./types').QuizQuestion[] = [
  {
    id: 1,
    question:
      '当前堆内容为 [4, 5]（小顶堆），k=2，下一个元素为 6。执行操作后堆会变成什么？堆顶是多少？',
    type: 'multiple-choice',
    options: [
      '[4, 5, 6]，堆顶 = 4',
      '[5, 6]，堆顶 = 5',
      '[4, 5]，堆顶 = 4',
      '[6, 4]，堆顶 = 4',
    ],
    correctAnswer: '[5, 6]，堆顶 = 5',
    hint: '提示：堆已满(k=2)，新元素 6 > 堆顶 4。回忆 push-and-pop 规则：先弹出堆顶，再插入新元素。',
    explanation:
      '堆 [4, 5] 已满（大小=k=2），且新元素 6 > 堆顶 4，因此先弹出堆顶 4，再 push 6。堆变为 [5, 6]，新的堆顶是 5。这正是第 2 大的元素！',
  },
  {
    id: 2,
    question: '在所有步骤中，堆的大小有什么不变的性质？',
    type: 'multiple-choice',
    options: [
      '堆大小始终严格等于 k',
      '堆大小 ≤ k，且在填满后始终等于 k（假设 nums.length ≥ k）',
      '堆大小可以超过 k',
      '堆大小始终等于已处理的元素个数',
    ],
    correctAnswer:
      '堆大小 ≤ k，且在填满后始终等于 k（假设 nums.length ≥ k）',
    hint: '提示：考虑前 k 步（填满阶段）和之后步骤中堆大小的变化。',
    explanation:
      '前 k 步填满堆，堆大小从 0 增长到 k。之后堆始终保持大小为 k，因为每次 push 前都会先 pop（如果需要的话）。这是小顶堆 TopK 算法的核心不变式。',
  },
  {
    id: 3,
    question:
      '如果将 nums 中的元素 5 改为 -5，对最终答案有何影响？请选出正确的结果。',
    type: 'multiple-choice',
    options: [
      '最终答案不变，仍然是 5',
      '最终答案变为 4（因为 -5 被忽略，6 和 4 成为前两大）',
      '最终答案变为 6',
      '算法会出错',
    ],
    correctAnswer: '最终答案变为 4（因为 -5 被忽略，6 和 4 成为前两大）',
    hint: '提示：-5 远小于堆顶，在处理 -5 时会发生什么？处理后剩下的最大两个元素是什么？',
    explanation:
      '原输入 [3,2,1,5,6,4] 改为 [3,2,1,-5,6,4]。处理 -5 时堆为 [2,3]，堆顶=2，-5<2 所以被忽略。最终堆中有 6 和 4，堆顶=4。因此第 2 大元素从 5 变为 4。',
  },
  {
    id: 4,
    question:
      '当堆大小等于 k 且新元素比堆顶小时，会发生什么？为什么？',
    type: 'multiple-choice',
    options: [
      '新元素替换堆顶',
      '新元素被加入堆，堆大小变为 k+1',
      '新元素被忽略，因为它不可能是前 K 大元素',
      '堆顶被弹出，新元素插入',
    ],
    correctAnswer: '新元素被忽略，因为它不可能是前 K 大元素',
    hint: '提示：小顶堆的堆顶是当前前 K 大元素中最小的那个。如果一个元素比这个最小值还小，它能进入前 K 大吗？',
    explanation:
      '堆中维护的是当前已见元素中最大的 K 个（用小顶堆方便取最小值即第 K 大）。堆顶是这 K 个中最小的。如果新元素比堆顶还小，说明它比这 K 个元素都小，绝无可能进入前 K 大，因此直接忽略。',
  },
];