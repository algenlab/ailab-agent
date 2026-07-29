import { MinHeap } from './minHeap';

export function computeSteps(nums, k) {
  const heap = new MinHeap();
  const steps = [];

  nums.forEach((num, index) => {
    const heapBefore = heap.toArray();
    const topBefore = heap.peek();
    let action = '';
    let reason = '';

    if (heap.size() < k) {
      heap.push(num);
      action = 'push';
      reason = `Heap size < k (${heap.size() - 1} < ${k}), so push ${num}.`;
    } else if (num > heap.peek()) {
      const removed = heap.pop();
      heap.push(num);
      action = `pop ${removed}, push ${num}`;
      reason = `New value ${num} > heap top ${topBefore}. Pop ${removed} and push ${num} to maintain top-k.`;
    } else {
      action = 'ignore';
      reason = `New value ${num} <= heap top ${topBefore}. Ignored.`;
    }

    const heapAfter = heap.toArray();
    const topAfter = heap.peek();

    steps.push({
      stepIndex: index + 1,
      num,
      heapBefore,
      heapAfter,
      topBefore,
      topAfter,
      action,
      reason
    });
  });

  const finalAnswer = heap.peek() !== null ? heap.peek() : null;

  return { steps, finalAnswer };
}
  