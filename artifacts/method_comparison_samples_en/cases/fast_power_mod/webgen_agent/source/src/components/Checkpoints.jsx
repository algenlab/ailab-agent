import React, { useState } from 'react';
import './Checkpoints.css';

const questions = [
  {
    id: 'q1',
    title: 'Question 1: Predict Next Answer',
    description: 'Given base=3, exponent=5, mod=13. Currently processing the 1st bit (LSB) bit=1, answer=1, cur=3. What will answer become in the next step?',
    type: 'number',
    correctAnswer: 3,
    hint: 'Since the bit is 1, multiply: new answer = (current answer × cur) % mod = (1 × 3) % 13 = 3.',
    placeholder: 'Enter a number'
  },
  {
    id: 'q2',
    title: 'Question 2: Loop Invariant',
    description: 'Before the loop starts: answer=1, cur=3, e=5. Which equation represents the invariant maintained by the loop throughout execution?',
    type: 'choice',
    choices: [
      'answer × cur^e ≡ base^exponent (mod mod)',
      'answer + cur × e = base^exponent',
      'answer × e ≡ cur^base (mod mod)',
      'cur^answer ≡ base × e (mod mod)'
    ],
    correctAnswer: 0,
    hint: 'At each step, cur is squared and e is halved, while answer is multiplied by cur only when the bit is 1. The product answer × cur^e stays constant modulo mod.'
  },
  {
    id: 'q3',
    title: 'Question 3: Large Exponent, Small Mod',
    description: 'If exponent = 1,000,000 and mod = 2, compute for base = 2. Modify: base=2, exponent=1000000, mod=2. Predict the final answer.',
    type: 'number',
    correctAnswer: 0,
    hint: 'Any even number raised to any positive integer power stays even, so modulo 2 it yields 0.',
    placeholder: 'Enter a number'
  },
  {
    id: 'q4',
    title: 'Question 4: Understanding cur Changes',
    description: 'During execution cur changes from 3 (k=0) → 9 (k=1) → 3 (k=2). Why does cur change this way when base=3, mod=13?',
    type: 'choice',
    choices: [
      'cur is squared each iteration: 3→9 (3²=9), then 9→3 (81 mod 13 = 3)',
      'cur is multiplied by base each iteration',
      'cur toggles randomly between values',
      'cur resets to base % mod each iteration'
    ],
    correctAnswer: 0,
    hint: 'cur = (cur × cur) % mod. Starting from cur = base % mod = 3. Step 1: 3² = 9. Step 2: 9² = 81, 81 mod 13 = 3.'
  }
];

export default function Checkpoints({ onComplete }) {
  return (
    <section className="checkpoints" aria-label="Checkpoint Questions">
      <h2 className="section-title">Checkpoints</h2>
      <p className="checkpoints-intro">
        Test your understanding of the fast power modulo algorithm by answering these questions.
      </p>
      <div className="checkpoints-list">
        {questions.map((q) => (
          <CheckpointWidget
            key={q.id}
            question={q}
            onComplete={onComplete}
          />
        ))}
      </div>
    </section>
  );
}

function CheckpointWidget({ question, onComplete }) {
  const [answer, setAnswer] = useState('');
  const [feedback, setFeedback] = useState(null);
  const [showHint, setShowHint] = useState(false);
  const [completed, setCompleted] = useState(false);

  const handleSubmit = () => {
    let correct = false;
    if (question.type === 'number') {
      const num = parseFloat(answer);
      correct = !isNaN(num) && num === question.correctAnswer;
    } else if (question.type === 'choice') {
      correct = parseInt(answer, 10) === question.correctAnswer;
    }
    setFeedback(correct);
    if (correct) {
      setCompleted(true);
    }
    onComplete(question.id, question.title, correct);
  };

  const handleHint = () => setShowHint(true);

  return (
    <div className="checkpoint-item" aria-label={`Question: ${question.id}`}>
      <h3 className="checkpoint-title">{question.title}</h3>
      <p className="checkpoint-desc">{question.description}</p>

      {question.type === 'number' && (
        <div className="checkpoint-input-group">
          <input
            type="number"
            className="checkpoint-input"
            placeholder={question.placeholder}
            value={answer}
            onChange={e => setAnswer(e.target.value)}
            disabled={completed}
            onKeyDown={e => {
              if (e.key === 'Enter' && answer !== '' && !completed) {
                handleSubmit();
              }
            }}
          />
          <button
            className="checkpoint-submit"
            onClick={handleSubmit}
            disabled={completed || answer === ''}
          >
            Check
          </button>
        </div>
      )}

      {question.type === 'choice' && (
        <div className="checkpoint-choices">
          {question.choices.map((choice, i) => (
            <label key={i} className={`choice-option ${completed ? 'disabled' : ''}`}>
              <input
                type="radio"
                name={`${question.id}-choice`}
                value={i}
                checked={answer === i.toString()}
                onChange={() => {
                  if (!completed) setAnswer(i.toString());
                }}
                disabled={completed}
              />
              <span>{choice}</span>
            </label>
          ))}
          <button
            className="checkpoint-submit"
            onClick={handleSubmit}
            disabled={completed || answer === ''}
          >
            Check
          </button>
        </div>
      )}

      <div className="checkpoint-actions">
        <button className="hint-btn-small" onClick={handleHint} disabled={completed || showHint}>
          💡 Hint
        </button>
        {showHint && (
          <div className="hint-box">{question.hint}</div>
        )}
      </div>

      {feedback !== null && (
        <div className={`feedback ${feedback ? 'correct' : 'incorrect'}`} role="alert">
          {feedback ? '✓ Correct! Well done.' : '✗ Incorrect. Try again!'}
        </div>
      )}

      {completed && (
        <div className="completed-badge">Completed</div>
      )}
    </div>
  );
}
