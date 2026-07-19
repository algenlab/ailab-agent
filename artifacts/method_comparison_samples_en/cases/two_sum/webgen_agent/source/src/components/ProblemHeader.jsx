import React from 'react';
import './ProblemHeader.css';

function JsonHighlight({ data }) {
  const json = JSON.stringify(data, null, 2);
  const parts = [];
  let lastIndex = 0;
  const regex = /("(?:[^"\\]|\\.)*")\s*:|("(?:[^"\\]|\\.)*")|(-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b)|(\btrue\b|\bfalse\b|\bnull\b)/g;
  let match;

  while ((match = regex.exec(json)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ text: json.slice(lastIndex, match.index), type: 'plain' });
    }
    if (match[1]) {
      parts.push({ text: match[1], type: 'key' });
    } else if (match[2]) {
      parts.push({ text: match[2], type: 'string' });
    } else if (match[3]) {
      parts.push({ text: match[3], type: 'number' });
    } else if (match[4]) {
      parts.push({ text: match[4], type: 'keyword' });
    }
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < json.length) {
    parts.push({ text: json.slice(lastIndex), type: 'plain' });
  }

  return (
    <code className="io-code-inner">
      {parts.map((part, i) => (
        <span key={i} className={`json-${part.type}`}>{part.text}</span>
      ))}
    </code>
  );
}

function AnswerHighlight({ data }) {
  const json = JSON.stringify(data, null, 2);
  const parts = [];
  let lastIndex = 0;
  const regex = /("(?:[^"\\]|\\.)*")|(-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b)|(\btrue\b|\bfalse\b|\bnull\b)/g;
  let match;

  while ((match = regex.exec(json)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ text: json.slice(lastIndex, match.index), type: 'plain' });
    }
    if (match[1]) {
      parts.push({ text: match[1], type: 'string' });
    } else if (match[2]) {
      parts.push({ text: match[2], type: 'number' });
    } else if (match[3]) {
      parts.push({ text: match[3], type: 'keyword' });
    }
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < json.length) {
    parts.push({ text: json.slice(lastIndex), type: 'plain' });
  }

  return (
    <code className="io-code-inner">
      {parts.map((part, i) => (
        <span key={i} className={`json-${part.type}`}>{part.text}</span>
      ))}
    </code>
  );
}

export default function ProblemHeader({ input, expectedAnswer, customNums, onReset, onCustomInput, onAltInput }) {
  return (
    <section className="problem-header" aria-label="Problem description and input">
      <div className="problem-description">
        <p>
          In an order fulfillment system, <code>nums[i]</code> represents the quantity of goods
          that can be directly picked from the i-th slot, and the order still lacks <code>target</code> units
          of the same goods. Find <strong>two different slots</strong> such that the sum of their quantities
          equals exactly <code>target</code>, and return their 0-based indices. If no such slots exist,
          return an empty array.
        </p>
      </div>

      <div className="problem-io">
        <div className="io-block">
          <h3 className="io-label">Concrete Input</h3>
          <pre className="io-code">
            <JsonHighlight data={input} />
          </pre>
        </div>
        <div className="io-block">
          <h3 className="io-label">Expected Answer</h3>
          <pre className="io-code io-answer">
            <AnswerHighlight data={expectedAnswer} />
          </pre>
        </div>
      </div>

      <div className="problem-actions">
        <button className="btn btn-outline" onClick={onCustomInput} aria-label="Try custom input nums=[3,2,4], target=6">
          Try nums=[3,2,4], target=6
        </button>
        <button className="btn btn-outline" onClick={onAltInput} aria-label="Try modified input nums=[2,8,11,15], target=9">
          Try nums=[2,8,11,15], target=9
        </button>
        {customNums && (
          <button className="btn btn-outline" onClick={onReset} aria-label="Reset to original input">
            Reset to Original
          </button>
        )}
      </div>
    </section>
  );
}