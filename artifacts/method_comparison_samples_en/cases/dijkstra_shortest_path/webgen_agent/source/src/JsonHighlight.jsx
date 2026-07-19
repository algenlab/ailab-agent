import React from 'react';

/**
 * Simple JSON syntax highlighter using tokenization.
 * Produces color-coded spans for keys, strings, numbers, brackets, and booleans.
 */
export default function JsonHighlight({ data }) {
  const json = JSON.stringify(data, null, 2);

  const tokens = [];
  let i = 0;

  while (i < json.length) {
    // Strings (keys and values)
    if (json[i] === '"') {
      const start = i;
      i++;
      while (i < json.length && json[i] !== '"') {
        if (json[i] === '\\') i++; // skip escaped chars
        i++;
      }
      i++; // closing quote
      const str = json.slice(start, i);

      // Determine if this is a key (followed by ':') or a value string
      let after = i;
      while (after < json.length && json[after] === ' ') after++;
      const isKey = after < json.length && json[after] === ':';

      tokens.push(
        <span key={start} style={{ color: isKey ? '#6c5ce7' : '#00b894', fontWeight: isKey ? 600 : 400 }}>
          {str}
        </span>
      );
      continue;
    }

    // Numbers
    if (/[0-9]/.test(json[i]) || (json[i] === '-' && i + 1 < json.length && /[0-9]/.test(json[i + 1]))) {
      const start = i;
      if (json[i] === '-') i++;
      while (i < json.length && /[0-9.]/.test(json[i])) i++;
      tokens.push(
        <span key={start} style={{ color: '#0984e3', fontWeight: 500 }}>
          {json.slice(start, i)}
        </span>
      );
      continue;
    }

    // Booleans and null
    if (/[a-z]/.test(json[i])) {
      const start = i;
      while (i < json.length && /[a-z]/.test(json[i])) i++;
      tokens.push(
        <span key={start} style={{ color: '#e17055', fontWeight: 500 }}>
          {json.slice(start, i)}
        </span>
      );
      continue;
    }

    // Brackets and punctuation
    const ch = json[i];
    if ('{}[]:,'.includes(ch)) {
      tokens.push(
        <span key={i} style={{ color: '#636e72', fontWeight: 600 }}>
          {ch}
        </span>
      );
      i++;
      continue;
    }

    // Whitespace and other
    tokens.push(<span key={i}>{json[i]}</span>);
    i++;
  }

  return (
    <pre
      style={{
        margin: 0,
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
        fontFamily: "'Courier New', 'Consolas', monospace",
        fontSize: '0.88rem',
        lineHeight: 1.6
      }}
    >
      <code>{tokens}</code>
    </pre>
  );
}
