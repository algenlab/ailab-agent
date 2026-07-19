import React from 'react';

function syntaxHighlight(json) {
  if (typeof json !== 'string') {
    json = JSON.stringify(json, null, 2);
  }
  // Escape HTML entities
  json = json.replace(/&/g, '&').replace(/</g, '<').replace(/>/g, '>');
  // Apply highlighting
  return json.replace(
    /("(\\u[a-fA-F0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
    (match) => {
      let cls = 'json-number';
      if (/^"/.test(match)) {
        if (/:$/.test(match)) {
          cls = 'json-key';
          return `<span class="${cls}">${match.slice(0, -1)}</span>:`;
        } else {
          cls = 'json-string';
        }
      } else if (/true|false|null/.test(match)) {
        cls = 'json-boolean';
      }
      return `<span class="${cls}">${match}</span>`;
    }
  );
}

export default function JsonDisplay({ data }) {
  const highlighted = syntaxHighlight(data);
  return (
    <pre
      className="json-display"
      dangerouslySetInnerHTML={{ __html: highlighted }}
    />
  );
}