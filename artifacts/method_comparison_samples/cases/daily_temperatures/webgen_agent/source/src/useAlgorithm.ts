import { useState, useCallback, useMemo } from 'react';
import {
  AlgorithmStep,
  LogEntry,
  QuizState,
} from './types';
import { generateSteps, getCellState, DEFAULT_TEMPERATURES } from './algorithm';

let logIdCounter = 0;

export function useAlgorithm() {
  const [temperatures, setTemperatures] = useState<number[]>([...DEFAULT_TEMPERATURES]);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [activityLog, setActivityLog] = useState<LogEntry[]>([]);
  const [hintsRevealed, setHintsRevealed] = useState(0);
  const [showFinalAnswer, setShowFinalAnswer] = useState(false);
  const [quizState, setQuizState] = useState<QuizState>({
    q1Answered: false,
    q1Correct: null,
    q2Answered: false,
    q2Correct: null,
    q3Answered: false,
    q3Correct: null,
    q4Revealed: false,
  });
  const [sliderValue, setSliderValue] = useState(69);
  const [sliderModified, setSliderModified] = useState(false);

  const steps = useMemo(() => generateSteps(temperatures), [temperatures]);
  const currentStep = steps[currentStepIndex];
  const maxStepIndex = steps.length - 1;

  const modifiedTemperatures = useMemo(() => {
    const modified = [...temperatures];
    modified[4] = sliderValue;
    return modified;
  }, [temperatures, sliderValue]);

  const modifiedSteps = useMemo(
    () => generateSteps(modifiedTemperatures),
    [modifiedTemperatures]
  );

  const addLog = useCallback((type: LogEntry['type'], message: string) => {
    setActivityLog((prev) => [
      {
        id: ++logIdCounter,
        timestamp: new Date(),
        type,
        message,
      },
      ...prev.slice(0, 49),
    ]);
  }, []);

  const goToStep = useCallback(
    (index: number) => {
      const clamped = Math.max(0, Math.min(maxStepIndex, index));
      setCurrentStepIndex(clamped);
      if (clamped !== currentStepIndex) {
        addLog('navigation', `跳转到步骤 ${clamped}${clamped === 0 ? '（初始状态）' : ` — 处理下标 ${clamped - 1} (${temperatures[clamped - 1]}°C)`}`);
      }
    },
    [maxStepIndex, currentStepIndex, addLog, temperatures]
  );

  const nextStep = useCallback(() => {
    if (currentStepIndex < maxStepIndex) {
      goToStep(currentStepIndex + 1);
    }
  }, [currentStepIndex, maxStepIndex, goToStep]);

  const prevStep = useCallback(() => {
    if (currentStepIndex > 0) {
      goToStep(currentStepIndex - 1);
    }
  }, [currentStepIndex, goToStep]);

  const reset = useCallback(() => {
    setCurrentStepIndex(0);
    setActivityLog([]);
    setHintsRevealed(0);
    setShowFinalAnswer(false);
    setQuizState({
      q1Answered: false,
      q1Correct: null,
      q2Answered: false,
      q2Correct: null,
      q3Answered: false,
      q3Correct: null,
      q4Revealed: false,
    });
    setSliderValue(69);
    setSliderModified(false);
    setTemperatures([...DEFAULT_TEMPERATURES]);
    addLog('reset', '已重置所有状态');
  }, [addLog]);

  const revealHint = useCallback(() => {
    setHintsRevealed((prev) => {
      const next = Math.min(prev + 1, 3);
      addLog('hint', `查看了提示 ${next} / 3`);
      return next;
    });
  }, [addLog]);

  const revealAnswer = useCallback(() => {
    setShowFinalAnswer(true);
    addLog('show-answer', '查看了最终答案');
  }, [addLog]);

  const submitQuizAnswer = useCallback(
    (questionId: keyof QuizState, answer: string | number, correctAnswer: string | number) => {
      const isCorrect = String(answer) === String(correctAnswer);
      const key = `${questionId}Answered` as keyof QuizState;
      const correctKey = `${questionId}Correct` as keyof QuizState;

      setQuizState((prev) => ({
        ...prev,
        [key]: true,
        [correctKey]: isCorrect,
      }));

      addLog(
        isCorrect ? 'quiz-correct' : 'quiz-incorrect',
        `${String(questionId).toUpperCase()}: ${isCorrect ? '✓ 回答正确' : '✗ 回答错误'}`
      );
    },
    [addLog]
  );

  const revealQ4 = useCallback(() => {
    setQuizState((prev) => ({ ...prev, q4Revealed: true }));
    addLog('show-answer', 'Q4: 查看了参考答案');
  }, [addLog]);

  const handleSliderChange = useCallback(
    (value: number) => {
      setSliderValue(value);
      setSliderModified(true);
      if (value !== 69) {
        addLog('slider-change', `将第 4 天温度从 69°C 修改为 ${value}°C`);
      }
    },
    [addLog]
  );

  const getCellStateForIndex = useCallback(
    (index: number): 'pending' | 'current' | 'in-stack' | 'resolved' | 'no-answer' => {
      return getCellState(index, currentStep, steps);
    },
    [currentStep, steps]
  );

  return {
    temperatures,
    steps,
    currentStep,
    currentStepIndex,
    maxStepIndex,
    activityLog,
    hintsRevealed,
    showFinalAnswer,
    quizState,
    sliderValue,
    sliderModified,
    modifiedTemperatures,
    modifiedSteps,
    goToStep,
    nextStep,
    prevStep,
    reset,
    revealHint,
    revealAnswer,
    submitQuizAnswer,
    revealQ4,
    handleSliderChange,
    getCellStateForIndex,
  };
}
