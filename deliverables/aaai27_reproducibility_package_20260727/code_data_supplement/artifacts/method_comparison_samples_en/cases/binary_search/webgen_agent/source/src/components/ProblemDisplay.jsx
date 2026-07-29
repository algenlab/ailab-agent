import React from 'react';

export default function ProblemDisplay({ nums, target, finalAnswer }) {
  const inputJson = JSON.stringify({ nums, target }, null, 2);
  const answerJson = JSON.stringify(finalAnswer, null, 2);

  return (
    <section className="section">
      <h2 className="section-title">
        <span className="icon" role="img" aria-label="data">📦</span>
        Concrete Input & Expected Answer
      </h2>
      <div className="problem-grid">
        <div>
          <div style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
            Input (JSON)
          </div>
          <pre className="code-block">{formatJson(inputJson)}</pre>
        </div>
        <div>
          <div style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
            Expected Final Answer (JSON)
          </div>
          <div className="answer-block">
            <div className="label">Result</div>
            <div className="value">{finalAnswer}</div>
            <div style={{ fontSize: '0.8rem', color: '#16a34a', marginTop: '4px' }}>
              nums[4] = {nums[finalAnswer]} ✓
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function formatJson(jsonStr) {
  return jsonStr
    .replace(/"([^"]+)":/g, '<span class="key">"$1"</span>:')
    .replace(/: (-?\d+)/g, ': <span class="num">$1</span>')
    .replace(/: "([^"]+)"/g, ': <span class="str">"$1"</span>');
}
