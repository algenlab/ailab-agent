import React, { useState } from 'react';

const checkpointQuestions = [
  {
    id: 'q1',
    question: 'When text="ababc", pattern="abc", currently i=3, j=2 and pattern[2]=\'c\' mismatches with text[3]=\'b\', and pi[1]=0, what is the next state? (Hint: how will the j pointer change?)',
    type: 'text',
    hint: 'When a mismatch occurs and j > 0, the KMP algorithm sets j = pi[j-1]. Here j=2, so j becomes pi[1].',
    answer: 'j=0, i=3 (or i stays at 3, j becomes 0)',
    validate: (userAnswer) => {
      const normalized = userAnswer.toLowerCase().replace(/\s+/g, '');
      return normalized.includes('j=0') && (normalized.includes('i=3') || normalized.includes('i=3'));
    },
    feedback: {
      correct: 'Correct! When mismatch occurs at j=2, j becomes pi[1] = 0, and i remains at 3. The algorithm will then compare text[3] with pattern[0].',
      incorrect: 'Not quite. Remember: on mismatch with j>0, j = pi[j-1] and i does not change. Here j=2 and pi[1]=0, so j becomes 0, i stays 3.'
    }
  },
  {
    id: 'q2',
    question: 'At any moment in the KMP matching process, what invariant relationship exists between the matched prefix length j and the index i?',
    type: 'choice',
    options: [
      'A) i always equals j',
      'B) text[i-j...i-1] is equal to pattern[0...j-1]',
      'C) pattern[0...i] equals text'
    ],
    answer: 'B',
    hint: 'Think about what j represents: it is the length of the prefix of the pattern that has been matched so far. The current matching window in the text starts at i-j and ends at i-1.',
    feedback: {
      correct: 'Correct! Option B is the key invariant: the substring text[i-j...i-1] always matches pattern[0...j-1]. This is what allows KMP to skip characters safely.',
      incorrect: 'That is not correct. The fundamental invariant of KMP is that text[i-j...i-1] == pattern[0...j-1]. This ensures that when a mismatch occurs, we can use the prefix table to find the next valid alignment without re-examining characters we have already matched.'
    }
  },
  {
    id: 'q3',
    question: 'Suppose we have a pattern where pi[2]=0. How would you modify the pattern so that pi[2] becomes 1 instead? (Hint: what condition makes pi[2]=1?)',
    type: 'text',
    hint: 'pi[2]=1 means that the prefix of length 1 equals the suffix of length 1 ending at position 2. So pattern[0] must equal pattern[2].',
    answer: 'Change the third character to match the first character, e.g., "aba" (where pattern[0]=\'a\' equals pattern[2]=\'a\')',
    validate: (userAnswer) => {
      const lower = userAnswer.toLowerCase();
      return lower.includes('aba') || lower.includes('change') || lower.includes('first') || lower.includes('match');
    },
    feedback: {
      correct: 'Correct! To get pi[2]=1, we need pattern[0] == pattern[2], so that the proper prefix of length 1 equals the suffix of length 1 ending at position 2. For example, modifying the pattern to "aba" achieves this because the first and third characters are both \'a\'.',
      incorrect: 'Not quite. For pi[2] to be 1, we need pattern[0] == pattern[2]. This means the third character must equal the first character. For instance, changing the pattern to "aba" would give pi[2]=1.'
    }
  },
  {
    id: 'q4',
    question: 'When building the prefix table, suppose i=4, j=2, and pattern[4]=\'a\' matches pattern[2]=\'a\'. Why does j become 3? Please explain the meaning behind this state transition.',
    type: 'text',
    hint: 'j represents the length of the longest proper prefix that is also a suffix for the substring ending at the previous position. When pattern[i] matches pattern[j], it means we can extend that match by one character.',
    answer: 'Because the matched prefix-suffix length increases by 1. The proper prefix of length j=2 (pattern[0..1]) is already a suffix ending at i-1=3. Since pattern[4] matches pattern[2], the prefix of length 3 now matches the suffix ending at position 4, so j increments to 3.',
    validate: (userAnswer) => {
      const lower = userAnswer.toLowerCase();
      return lower.includes('increment') || lower.includes('extend') || lower.includes('length') || lower.includes('increase') || lower.includes('become') || (lower.includes('prefix') && lower.includes('suffix'));
    },
    feedback: {
      correct: 'Excellent! When pattern[i] matches pattern[j], it means we can extend the previously matched prefix-suffix pair by one more character. The longest proper prefix that is also a suffix for the substring pattern[0..i] now has length j+1 = 3, so j becomes 3.',
      incorrect: 'Think about it: j tracks the length of the longest proper prefix that is also a suffix for the pattern up to position i-1. When we find a match at position i, we can extend that prefix-suffix pair by one character, so j becomes j+1 = 3.'
    }
  }
];

export default function Checkpoint({ onLogEntry }) {
  const [answers, setAnswers] = useState({});
  const [feedback, setFeedback] = useState({});
  const [showHints, setShowHints] = useState({});
  const [showAnswers, setShowAnswers] = useState({});

  const handleAnswerChange = (questionId, value) => {
    setAnswers(prev => ({ ...prev, [questionId]: value }));
    setFeedback(prev => ({ ...prev, [questionId]: null }));
  };

  const handleCheck = (q) => {
    const userAnswer = answers[q.id] || '';
    const isCorrect = q.type === 'choice' 
      ? userAnswer.startsWith(q.answer) 
      : q.validate(userAnswer);
    
    setFeedback(prev => ({ ...prev, [q.id]: isCorrect ? 'correct' : 'incorrect' }));
    onLogEntry({
      type: 'checkpoint',
      questionId: q.id,
      question: q.question.substring(0, 60) + '...',
      userAnswer: userAnswer,
      correct: isCorrect
    });
  };

  const handleHint = (q) => {
    setShowHints(prev => ({ ...prev, [q.id]: !prev[q.id] }));
    if (!showHints[q.id]) {
      onLogEntry({
        type: 'hint',
        questionId: q.id,
        question: q.question.substring(0, 60) + '...'
      });
    }
  };

  const handleShowAnswer = (q) => {
    setShowAnswers(prev => ({ ...prev, [q.id]: true }));
    onLogEntry({
      type: 'show_answer',
      questionId: q.id,
      question: q.question.substring(0, 60) + '...'
    });
  };

  return (
    <div className="checkpoint-panel">
      <h3>Checkpoint Questions</h3>
      <p className="checkpoint-intro">Test your understanding of the KMP algorithm by answering these questions.</p>
      
      {checkpointQuestions.map((q, idx) => (
        <div key={q.id} className="checkpoint-item">
          <h4>Question {idx + 1}</h4>
          <p className="q-text">{q.question}</p>
          
          {q.type === 'choice' ? (
            <div className="options-list">
              {q.options.map((opt, optIdx) => (
                <label key={optIdx} className={`option-label ${feedback[q.id] && opt.startsWith(q.answer) ? 'correct-answer' : ''} ${feedback[q.id] === 'incorrect' && answers[q.id] === opt ? 'wrong-answer' : ''}`}>
                  <input
                    type="radio"
                    name={`q-${q.id}`}
                    value={opt}
                    checked={answers[q.id] === opt}
                    onChange={(e) => handleAnswerChange(q.id, e.target.value)}
                    disabled={showAnswers[q.id]}
                  />
                  <span>{opt}</span>
                </label>
              ))}
            </div>
          ) : (
            <div className="text-input-group">
              <input
                type="text"
                className="q-input"
                placeholder="Type your answer..."
                value={answers[q.id] || ''}
                onChange={(e) => handleAnswerChange(q.id, e.target.value)}
                disabled={showAnswers[q.id]}
                aria-label={`Answer for question ${idx + 1}`}
              />
            </div>
          )}

          <div className="q-actions">
            <button 
              className="action-btn check-btn" 
              onClick={() => handleCheck(q)}
              disabled={!answers[q.id] || showAnswers[q.id]}
            >
              Check Answer
            </button>
            <button 
              className="action-btn hint-btn" 
              onClick={() => handleHint(q)}
            >
              {showHints[q.id] ? 'Hide Hint' : 'Hint'}
            </button>
            <button 
              className="action-btn show-answer-btn" 
              onClick={() => handleShowAnswer(q)}
              disabled={showAnswers[q.id]}
            >
              Show Answer
            </button>
          </div>

          {showHints[q.id] && (
            <div className="hint-box">
              <strong>Hint:</strong> {q.hint}
            </div>
          )}

          {showAnswers[q.id] && (
            <div className="answer-box">
              <strong>Answer:</strong> {q.answer}
            </div>
          )}

          {feedback[q.id] === 'correct' && (
            <div className="feedback-box correct">
              ✅ {q.feedback.correct}
            </div>
          )}
          {feedback[q.id] === 'incorrect' && (
            <div className="feedback-box incorrect">
              ❌ {q.feedback.incorrect}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}