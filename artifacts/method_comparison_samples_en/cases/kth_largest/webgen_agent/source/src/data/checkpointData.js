export const checkpointQuestion = {
  id: 'predict-heap-after-6',
  title: 'Predict the heap after pushing 6',
  scenario: {
    heapBefore: [4, 5],
    k: 2,
    nextElement: 6
  },
  options: [
    { id: 'a', text: 'Heap: [4, 5, 6], top: 4', heap: [4, 5, 6], top: 4 },
    { id: 'b', text: 'Heap: [4, 5], top: 4', heap: [4, 5], top: 4 },
    { id: 'c', text: 'Heap: [5, 6], top: 5', heap: [5, 6], top: 5 },
    { id: 'd', text: 'Heap: [4, 6], top: 4', heap: [4, 6], top: 4 }
  ],
  correctOptionId: 'c',
  hint: 'Remember: the heap is a min-heap. After pushing 6, the size exceeds k, so the smallest element is removed. Think about which element is smallest in [4,5,6] and will be popped.',
  explanation: 'The heap is a min-heap. Pushing 6 gives [4,5,6] (4 remains top). Since size now 3 > k=2, we pop the min (4). After popping, the heap becomes [5,6] with top 5.'
};
  