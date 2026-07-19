import React, { useState, useCallback } from 'react';

/**
 * A small copy-to-clipboard button that appears in the top-right of a code block.
 */
export default function CopyButton({ text, label = 'Copy' }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }).catch(() => {
      // Fallback for older browsers
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand('copy');
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch (e) {
        // silent fail
      }
      document.body.removeChild(ta);
    });
  }, [text]);

  return (
    <button
      className="copy-btn"
      onClick={handleCopy}
      aria-label={copied ? 'Copied' : label}
      title={copied ? 'Copied!' : label}
    >
      {copied ? '✓ Copied' : '📋 ' + label}
    </button>
  );
}