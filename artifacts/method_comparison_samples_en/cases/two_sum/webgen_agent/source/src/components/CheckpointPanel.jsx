import React, { useState } from 'react';
import './CheckpointPanel.css';

const QUESTIONS = [
  {
    id: 'q1',
    triggerStep: 2,
    triggerCondition: function(step, input) {
      return step && step.i === 2 && !step.found && step.need === -2;
    },
    question: 'Currently scanning to nums[2]=11, seen already contains {2:0, 7:1}, target=9. What operation will the algorithm perform next?',
    options: [
      { value: 'A', text: 'Add 11 to seen and move to i=3' },
      { value: 'B', text: 'Find that 11 matches the complement and return [0, 2]' },
      { value: 'C', text: 'Stop because 11 exceeds the target' },
      { value: 'D', text: 'Remove the smallest key from seen' }
    ],
    correct: 'A',
    explanation: 'The complement needed is 9 - 11 = -2, which is NOT in seen. So the algorithm adds nums[2]=11 to seen and moves to the next index (i=3).'
  },
  {
    id: 'q2',
    triggerStep: 1,
    triggerCondition: function(step, input) {
      return step && step.i === 1 && step.found && step.result && step.result[0] === 0 && step.result[1] === 1;
    },
    question: 'During algorithm execution, which of the following always holds?',
    options: [
      { value: 'A', text: 'seen length equals i' },
      { value: 'B', text: 'need is always positive' },
      { value: 'C', text: 'The keys in seen are the values of elements already visited' }
    ],
    correct: 'C',
    explanation: 'The hash table seen stores previously visited element values as keys, mapping each to its index. Option A is false because seen grows as we add elements; Option B is false because need can be negative.'
  },
  {
    id: 'q3',
    triggerId: 'q3-alt',
    question: 'Change nums[1] from 7 to 8, target unchanged (9). Can the algorithm still find a solution? What are the new indices or is it empty?',
    options: [
      { value: 'A', text: '[0, 2] with sum 13 (no match) - return []' },
      { value: 'B', text: '[0, 1] with sum 10 (no match) - return []' },
      { value: 'C', text: 'No pair sums to 9, return []' },
      { value: 'D', text: '[1, 2] with sum 19 (no match) - return []' }
    ],
    correct: 'C',
    explanation: 'With nums=[2,8,11,15] and target=9: 2+8=10, 2+11=13, 2+15=17, 8+11=19, 8+15=23, 11+15=26. No pair sums exactly to 9, so the algorithm returns [].'
  },
  {
    id: 'q4',
    triggerStep: 1,
    triggerCondition: function(step, input) {
      return step && step.i === 1 && step.found && step.result;
    },
    question: 'When the algorithm goes from i=0 to i=1, what change does seen undergo and why?',
    options: [
      { value: 'A', text: 'seen stays empty because index 0 did not add anything' },
      { value: 'B', text: 'seen adds {2: 0} because nums[0]=2 was visited and recorded before moving to i=1' },
      { value: 'C', text: 'seen adds {7: 1} at the start of processing i=1' },
      { value: 'D', text: 'seen replaces all keys with the complement value' }
    ],
    correct: 'B',
    explanation: 'After processing index 0, the value 2 (nums[0]) is added to seen as {2: 0} before moving to i=1. This way, when processing i=1, seen contains the record of previously visited elements.'
  }
];

function getHintForQuestion(q, input) {
  if (q.id === 'q1') {
    return 'Think about: does the complement (-2) exist in the current seen hash table? If not, what does the algorithm do with the current element?';
  }
  if (q.id === 'q2') {
    return 'Consider what happens at each step: the algorithm adds the just-processed element to seen after checking. Compare the growth of seen with the counter i.';
  }
  if (q.id === 'q3') {
    return 'Compute all possible pairs: 2+8, 2+11, 2+15, 8+11, 8+15, 11+15. Do any of them equal 9?';
  }
  if (q.id === 'q4') {
    return 'Trace what happens after processing i=0: the algorithm checks the complement (not found), then records nums[0] into seen before incrementing i.';
  }
  return 'Think about how the hash table evolves as the algorithm scans the array.';
}

export default function CheckpointPanel(props) {
  const currentStepIndex = props.currentStepIndex;
  const allSteps = props.allSteps;
  const input = props.input;
  const showHint = props.showHint;
  const showAnswer = props.showAnswer;
  const onAnswer = props.onAnswer;
  const onHint = props.onHint;
  const onShowAnswer = props.onShowAnswer;

  const [responses, setResponses] = useState({});
  const [submitted, setSubmitted] = useState({});

  const currentStep = (currentStepIndex >= 0 && currentStepIndex < allSteps.length)
    ? allSteps[currentStepIndex]
    : null;

  const isAltInput = input.nums[1] === 8;

  const activeQuestions = QUESTIONS.filter(function(q) {
    if (q.triggerStep !== undefined && q.triggerCondition) {
      return q.triggerCondition(currentStep, input);
    }
    if (q.triggerId === 'q3-alt') {
      return true;
    }
    return false;
  });

  let displayQuestions = activeQuestions.length > 0 ? activeQuestions : [];

  if (isAltInput && displayQuestions.length === 0) {
    displayQuestions = QUESTIONS.filter(function(q) {
      return q.triggerId === 'q3-alt';
    });
  }

  if (displayQuestions.length === 0 && currentStep && currentStep.found && currentStep.i === 1) {
    var q4 = QUESTIONS.find(function(q) { return q.id === 'q4'; });
    if (q4 && q4.triggerCondition(currentStep, input)) {
      displayQuestions = [q4];
    }
  }

  function handleSelect(questionId, value) {
    if (submitted[questionId]) return;
    setResponses(function(prev) {
      var updated = {};
      Object.keys(prev).forEach(function(k) { updated[k] = prev[k]; });
      updated[questionId] = value;
      return updated;
    });
  }

  function handleSubmit(questionId) {
    if (submitted[questionId] || !responses[questionId]) return;
    setSubmitted(function(prev) {
      var updated = {};
      Object.keys(prev).forEach(function(k) { updated[k] = prev[k]; });
      updated[questionId] = true;
      return updated;
    });
    var q = QUESTIONS.find(function(q) { return q.id === questionId; });
    if (!q) return;
    var isCorrect = responses[questionId] === q.correct;
    var shortQ = q.question.length > 60 ? q.question.slice(0, 60) + '...' : q.question;
    onAnswer(isCorrect, isCorrect
      ? 'Checkpoint "' + shortQ + '" - Correct!'
      : 'Checkpoint "' + shortQ + '" - Incorrect.'
    );
  }

  function buildClassName(base, selected, submittedVal, correctVal, isCorrectFlag) {
    var cls = 'cp-option';
    if (selected) {
      cls += ' cp-option-selected';
    }
    if (submittedVal && correctVal === base) {
      cls += ' cp-option-correct';
    }
    if (submittedVal && selected && !isCorrectFlag) {
      cls += ' cp-option-incorrect';
    }
    return cls;
  }

  function buildFeedbackClass(isCorrect) {
    return 'cp-feedback ' + (isCorrect ? 'cp-feedback-correct' : 'cp-feedback-incorrect');
  }

  if (displayQuestions.length === 0) {
    return (
      <section className="checkpoint-panel" aria-label="Checkpoint questions">
        <h2 className="cp-title">Checkpoints</h2>
        <p className="cp-empty">
          Advance through the algorithm steps to unlock checkpoint questions.
          {!isAltInput ? ' Or try the alternate input to trigger question 3.' : ''}
        </p>
        <div className="cp-always-available">
          <p className="cp-hint-text">
            <strong>Question 3 (always available):</strong> Change nums[1] from 7 to 8, target unchanged, can the algorithm still find a solution? Use the "Try nums=[2,8,11,15]" button above to explore this scenario step by step.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="checkpoint-panel" aria-label="Checkpoint questions">
      <h2 className="cp-title">Checkpoints</h2>
      {displayQuestions.map(function(q) {
        var isSubmitted = submitted[q.id];
        var selectedValue = responses[q.id] || '';
        var isCorrect = isSubmitted && selectedValue === q.correct;

        return (
          <div key={q.id} className="cp-question-card">
            <p className="cp-question-text">{q.question}</p>

            <div className="cp-options" role="radiogroup" aria-label={'Options for: ' + q.question}>
              {q.options.map(function(opt) {
                var optSelected = selectedValue === opt.value;
                var optClassName = buildClassName(opt.value, optSelected, isSubmitted, q.correct, isCorrect);
                return (
                  <label key={opt.value} className={optClassName}>
                    <input
                      type="radio"
                      name={'question-' + q.id}
                      value={opt.value}
                      checked={optSelected}
                      onChange={function() { handleSelect(q.id, opt.value); }}
                      disabled={isSubmitted}
                      aria-label={opt.text}
                    />
                    <span className="cp-option-label">{opt.value}. {opt.text}</span>
                  </label>
                );
              })}
            </div>

            <div className="cp-actions">
              <button
                className="btn btn-primary btn-sm"
                onClick={function() { handleSubmit(q.id); }}
                disabled={isSubmitted || !selectedValue}
                aria-label="Submit answer"
              >
                Submit
              </button>
              <button
                className="btn btn-outline btn-sm"
                onClick={onHint}
                aria-label="Show hint"
              >
                Hint
              </button>
              <button
                className="btn btn-outline btn-sm"
                onClick={onShowAnswer}
                aria-label="Show answer"
              >
                Show Answer
              </button>
            </div>

            {isSubmitted && (
              <div className={buildFeedbackClass(isCorrect)} role="alert">
                <strong>{isCorrect ? 'Correct!' : 'Incorrect.'}</strong>
                <p>{q.explanation}</p>
              </div>
            )}

            {showHint && !isSubmitted && (
              <div className="cp-hint" role="status">
                <strong>Hint:</strong> {getHintForQuestion(q, input)}
              </div>
            )}

            {showAnswer && !isSubmitted && (
              <div className="cp-answer-reveal" role="status">
                <strong>Answer:</strong> {q.options.find(function(o) { return o.value === q.correct; }).text}. {q.explanation}
              </div>
            )}
          </div>
        );
      })}
    </section>
  );
}