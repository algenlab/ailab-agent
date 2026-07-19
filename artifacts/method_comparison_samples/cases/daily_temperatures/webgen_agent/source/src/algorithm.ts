import { AlgorithmStep } from './types';

export function generateSteps(temperatures: number[]): AlgorithmStep[] {
  const n = temperatures.length;
  const steps: AlgorithmStep[] = [];

  steps.push({
    id: 0,
    processingIndex: -1,
    processingTemp: null,
    stackBefore: [],
    pops: [],
    stackAfter: [],
    answerState: new Array(n).fill(0),
    description: '初始状态：栈为空，answer 数组全部为 0。准备从左到右扫描温度数组。',
  });

  const stack: number[] = [];
  const answer: number[] = new Array(n).fill(0);

  for (let i = 0; i < n; i++) {
    const stackBefore = [...stack];
    const pops: { index: number; answerValue: number }[] = [];
    const descriptionParts: string[] = [];

    const currentTemp = temperatures[i];
    descriptionParts.push(`处理下标 ${i} (${currentTemp}°C)`);

    while (stack.length > 0 && temperatures[stack[stack.length - 1]] < currentTemp) {
      const poppedIdx = stack.pop()!;
      const waitDays = i - poppedIdx;
      answer[poppedIdx] = waitDays;
      pops.push({ index: poppedIdx, answerValue: waitDays });
      descriptionParts.push(
        `${currentTemp}°C > ${temperatures[poppedIdx]}°C (栈顶下标 ${poppedIdx}) → 弹出 ${poppedIdx}，answer[${poppedIdx}] = ${i} - ${poppedIdx} = ${waitDays}`
      );
    }

    stack.push(i);
    if (pops.length === 0) {
      if (stackBefore.length === 0) {
        descriptionParts.push('栈为空 → 直接压入');
      } else {
        descriptionParts.push(
          `${currentTemp}°C ≤ ${temperatures[stackBefore[stackBefore.length - 1]]}°C (栈顶) → 压入下标 ${i}`
        );
      }
    } else {
      if (stack.length === 1) {
        descriptionParts.push('栈已清空 → 压入当前下标');
      } else {
        descriptionParts.push(
          `${currentTemp}°C ≤ ${temperatures[stack[stack.length - 2]]}°C → 压入下标 ${i}`
        );
      }
    }

    const description = descriptionParts.join('；');

    steps.push({
      id: i + 1,
      processingIndex: i,
      processingTemp: currentTemp,
      stackBefore,
      pops,
      stackAfter: [...stack],
      answerState: [...answer],
      description,
    });
  }

  return steps;
}

export function getCellState(
  index: number,
  currentStep: AlgorithmStep,
  allSteps: AlgorithmStep[]
): 'pending' | 'current' | 'in-stack' | 'resolved' | 'no-answer' {
  if (currentStep.id === 0) return 'pending';

  if (index === currentStep.processingIndex) return 'current';

  if (currentStep.stackAfter.includes(index)) return 'in-stack';

  const answerVal = currentStep.answerState[index];
  if (answerVal > 0) return 'resolved';
  if (answerVal === 0 && index < currentStep.processingIndex) return 'no-answer';

  const wasPopped = currentStep.pops.some((p) => p.index === index);
  if (wasPopped) return 'resolved';

  return 'pending';
}

export const DEFAULT_TEMPERATURES = [73, 74, 75, 71, 69, 72, 76, 73];
export const EXPECTED_ANSWER = [1, 1, 4, 2, 1, 1, 0, 0];
