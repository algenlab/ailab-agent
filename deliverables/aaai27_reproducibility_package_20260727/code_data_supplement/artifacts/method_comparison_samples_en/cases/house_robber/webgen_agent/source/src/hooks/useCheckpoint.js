import { useState, useCallback, useEffect } from 'react';

const CHECKPOINTS = [
  {
    // Triggered when the user is at step index 1 (i=1, about to compute i=2)
    stepTrigger: 1,
    question: 'Given the house amounts nums = [2,7,9,3,1], the dp array has been completed up to dp[0]=2, dp[1]=7. When computing i=2, what should be the value of dp[2]?',
    correctAnswer: '11',
    feedbackCorrect: 'Correct! dp[2] = max(dp[1]=7, dp[0]+nums[2]=2+9=11) = 11.',
    feedbackIncorrect: 'Not quite. Remember the recurrence: dp[i] = max(dp[i-1], dp[i-2] + nums[i]). Here dp[2] = max(7, 2+9) = 11.',
    hint: 'Use the recurrence dp[i] = max(dp[i-1], dp[i-2] + nums[i]) with i=2.',
    answerValue: '11'
  }
];

export function useCheckpoint(currentStepIndex, addLog) {
  const [state, setState] = useState({
    active: false,
    question: '',
    correctAnswer: '',
    userAnswer: '',
    feedback: null, // { type: 'correct' | 'incorrect', message: string }
    hintVisible: false,
    answerVisible: false,
    answerValue: '',
    locked: false,
    questionId: null,
  });

  // Reset when step changes
  useEffect(() => {
    const cp = CHECKPOINTS.find(q => q.stepTrigger === currentStepIndex);
    if (cp) {
      setState({
        active: true,
        question: cp.question,
        correctAnswer: cp.correctAnswer,
        userAnswer: '',
        feedback: null,
        hintVisible: false,
        answerVisible: false,
        answerValue: cp.answerValue,
        locked: false,
        questionId: currentStepIndex,
      });
    } else {
      setState(prev => ({
        ...prev,
        active: false,
      }));
    }
  }, [currentStepIndex]);

  const checkAnswer = useCallback((input) => {
    if (state.locked || !state.active) return;
    const trimmed = input.trim();
    setState(prev => ({ ...prev, userAnswer: trimmed }));
    if (trimmed === state.correctAnswer) {
      setState(prev => ({
        ...prev,
        feedback: {
          type: 'correct',
          message: CHECKPOINTS.find(q => q.stepTrigger === currentStepIndex)?.feedbackCorrect || 'Correct!'
        },
        locked: true,
      }));
      addLog(`Predicted dp[2] = ${trimmed} (Correct)`);
    } else {
      const fb = CHECKPOINTS.find(q => q.stepTrigger === currentStepIndex)?.feedbackIncorrect || 'Incorrect. Try again.';
      setState(prev => ({
        ...prev,
        feedback: {
          type: 'incorrect',
          message: fb
        },
      }));
      addLog(`Predicted dp[2] = ${trimmed} (Incorrect)`);
    }
  }, [state.active, state.locked, state.correctAnswer, currentStepIndex, addLog]);

  const showHint = useCallback(() => {
    if (!state.active) return;
    setState(prev => ({ ...prev, hintVisible: true }));
    addLog('Viewed hint');
  }, [state.active, addLog]);

  const showAnswer = useCallback(() => {
    if (!state.active) return;
    setState(prev => ({ ...prev, answerVisible: true, locked: true, userAnswer: state.answerValue }));
    addLog(`Revealed answer: ${state.answerValue}`);
  }, [state.active, state.answerValue, addLog]);

  const resetCheckpoint = useCallback(() => {
    const cp = CHECKPOINTS.find(q => q.stepTrigger === currentStepIndex);
    if (!cp) return;
    setState({
      active: true,
      question: cp.question,
      correctAnswer: cp.correctAnswer,
      userAnswer: '',
      feedback: null,
      hintVisible: false,
      answerVisible: false,
      answerValue: cp.answerValue,
      locked: false,
      questionId: currentStepIndex,
    });
    addLog('Reset checkpoint');
  }, [currentStepIndex, addLog]);

  return {
    checkpointState: state,
    checkAnswer,
    showHint,
    showAnswer,
    resetCheckpoint,
  };
}