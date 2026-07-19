export const problemData = {
  title: "合并区间",
  family: "贪心",
  description:
    "会议中心收到多批场地占用申请，intervals 中每个闭区间 [开始时间, 结束时间] 表示一个预约时段。由于同房间不能同时使用，需要将所有相互重叠或首尾相接的时段合并，返回按开始时间排序且互不重叠的最终占用区间列表。",
  input: {
    intervals: [
      [1, 3],
      [2, 6],
      [8, 10],
      [15, 18],
    ],
  },
  expectedOutput: [
    [1, 6],
    [8, 10],
    [15, 18],
  ],
  objectives: [
    "理解排序后线性扫描时 merged 列表的状态变化（追加新区间 vs 扩展右端点）。",
    "根据当前区间与 merged 最后一区间的重叠关系，预测下一次操作结果。",
    "运用不变式（如 merged 始终保持不重叠且按起点排序）验证中间状态。",
  ],
  referenceStrategy: "按起点排序，维护已合并结果的最后一个区间并按需扩展。",
};

// Pre-computed algorithm steps for visualization
export function computeSteps(intervals) {
  // Sort by start time
  const sorted = [...intervals].sort((a, b) => a[0] - b[0]);
  const merged = [];
  const steps = [];

  // Step 0: initial state (before processing)
  steps.push({
    index: -1,
    currentInterval: null,
    merged: [],
    action: "开始：区间已按起点升序排序，merged 为空。",
    sorted: [...sorted],
  });

  for (let i = 0; i < sorted.length; i++) {
    const curr = sorted[i];
    const beforeMerged = JSON.parse(JSON.stringify(merged));

    if (merged.length === 0 || merged[merged.length - 1][1] < curr[0]) {
      // No overlap: append
      merged.push([...curr]);
      steps.push({
        index: i,
        currentInterval: curr,
        merged: JSON.parse(JSON.stringify(merged)),
        prevMerged: beforeMerged,
        action:
          merged.length === 1
            ? `merged 为空，追加第一个区间 [${curr[0]}, ${curr[1]}]。`
            : `当前区间 [${curr[0]}, ${curr[1]}] 与 merged 最后区间 [${beforeMerged[beforeMerged.length - 1][0]}, ${beforeMerged[beforeMerged.length - 1][1]}] 不重叠（${curr[0]} > ${beforeMerged[beforeMerged.length - 1][1]}），追加新区间。`,
        overlapType: "none",
        sorted: [...sorted],
      });
    } else {
      // Overlap: extend right endpoint
      const last = merged[merged.length - 1];
      const oldRight = last[1];
      last[1] = Math.max(last[1], curr[1]);
      steps.push({
        index: i,
        currentInterval: curr,
        merged: JSON.parse(JSON.stringify(merged)),
        prevMerged: beforeMerged,
        action:
          curr[1] > oldRight
            ? `当前区间 [${curr[0]}, ${curr[1]}] 与 merged 最后区间重叠（${curr[0]} ≤ ${oldRight}），扩展右端点：${oldRight} → ${last[1]}。`
            : `当前区间 [${curr[0]}, ${curr[1]}] 被 merged 最后区间完全包含（${curr[1]} ≤ ${oldRight}），无需扩展。`,
        overlapType: curr[1] > oldRight ? "extend" : "contained",
        sorted: [...sorted],
      });
    }
  }

  return { steps, sorted };
}

export const quizQuestions = [
  {
    id: "q1",
    question: "当前 merged 为 [[1,3]]，即将处理区间 [2,5]。请预测 merged 的下一步状态。",
    options: [
      { key: "A", text: "[[1,3], [2,5]]" },
      { key: "B", text: "[[1,5]]" },
      { key: "C", text: "[[1,3]]" },
      { key: "D", text: "[[2,5]]" },
    ],
    correctKey: "B",
    explanation:
      "[2,5] 的起点 2 ≤ 3（merged 最后区间的终点），存在重叠，应扩展右端点：max(3,5)=5，结果为 [[1,5]]。",
  },
  {
    id: "q2",
    question:
      "给出排序后 intervals = [[1,4],[2,3],[5,6]] 和某步 merged = [[1,3],[5,6]]。违反了哪个不变式？",
    options: [
      { key: "A", text: "merged 不保持按起点排序" },
      { key: "B", text: "merged 中存在重叠区间" },
      { key: "C", text: "第一个区间的右端点未正确扩展" },
      { key: "D", text: "所有选项都不对" },
    ],
    correctKey: "C",
    explanation:
      "处理 [2,3] 后 merged 应为 [[1,4]]（因为 [2,3] 被包含，但注意 [1,4] 右端点已是 4），而这里显示 [[1,3]]，说明未正确扩展。处理 [5,6] 时无重叠，追加即可。正确结果应为 [[1,4],[5,6]]。",
  },
  {
    id: "q3",
    question:
      "现有 intervals = [[1,3],[2,6],[8,10]]，若希望合并结果变为 [[1,6],[8,9]]，该如何修改其中一个输入区间？",
    options: [
      { key: "A", text: "将 [8,10] 改为 [8,9]" },
      { key: "B", text: "将 [2,6] 改为 [2,9]" },
      { key: "C", text: "将 [1,3] 改为 [1,4]" },
      { key: "D", text: "将 [2,6] 改为 [2,5]" },
    ],
    correctKey: "A",
    explanation:
      "原合并结果为 [[1,6],[8,10]]。要让第二个区间变为 [8,9]，只需将 [8,10] 的右端点从 10 缩短为 9 即可。",
  },
  {
    id: "q4",
    question:
      "当处理区间 [4,5] 且 merged = [[1,3]] 时，为何会追加新区间而不是扩展？",
    options: [
      { key: "A", text: "因为 4 > 3，两个区间不重叠" },
      { key: "B", text: "因为 [4,5] 在 [1,3] 之前" },
      { key: "C", text: "因为 merged 为空" },
      { key: "D", text: "因为两个区间长度相同" },
    ],
    correctKey: "A",
    explanation:
      "合并条件是当前区间起点 ≤ merged 最后区间的终点时才重叠。这里 4 > 3，所以不重叠，应追加新区间 [[1,3],[4,5]]。",
  },
];
