import React from 'react';

/**
 * Clean JSON syntax highlighter using foreground colors only.
 * No background highlights, borders, or box decorations.
 */
export default function JsonHighlight({ jsonString }) {
  const tokens = [];
  let i = 0;
  const len = jsonString.length;

  while (i < len) {
    const ch = jsonString[i];

    // Whitespace and newlines
    if (ch === ' ' || ch === '\n' || ch === '\r' || ch === '\t') {
      const start = i;
      while (i < len && (jsonString[i] === ' ' || jsonString[i] === '\n' || jsonString[i] === '\r' || jsonString[i] === '\t')) {
        i++;
      }
      tokens.push(jsonString.slice(start, i));
      continue;
    }

    // String literals
    if (ch === '"') {
      const start = i;
      i++;
      while (i < len && jsonString[i] !== '"') {
        if (jsonString[i] === '\\') i++;
        i++;
      }
      if (i < len) i++;
      const str = jsonString.slice(start, i);

      let peek = i;
      while (peek < len && (jsonString[peek] === ' ' || jsonString[peek] === '\n' || jsonString[peek] === '\r' || jsonString[peek] === '\t')) {
        peek++;
      }
      if (jsonString[peek] === ':') {
        tokens.push(<span key={start} className="json-key">{str}</span>);
      } else {
        tokens.push(<span key={start} className="json-string">{str}</span>);
      }
      continue;
    }

    // Numbers
    if (/^-?\d/.test(ch)) {
      const start = i;
      i++;
      while (i < len && /[\d.eE+\-]/.test(jsonString[i])) i++;
      if (i > 0 && jsonString[i - 1] === '.' && i < len && !/[\d]/.test(jsonString[i])) i--;
      tokens.push(<span key={start} className="json-number">{jsonString.slice(start, i)}</span>);
      continue;
    }

    // Booleans and null
    const rest = jsonString.slice(i);
    if (rest.startsWith('true')) {
      tokens.push(<span key={i} className="json-boolean">true</span>);
      i += 4;
      continue;
    }
    if (rest.startsWith('false')) {
      tokens.push(<span key={i} className="json-boolean">false</span>);
      i += 5;
      continue;
    }
    if (rest.startsWith('null')) {
      tokens.push(<span key={i} className="json-null">null</span>);
      i += 4;
      continue;
    }

    // Punctuation
    tokens.push(<span key={i} className="json-punctuation">{ch}</span>);
    i++;
  }

  return <code className="json-code">{tokens}</code>;
}