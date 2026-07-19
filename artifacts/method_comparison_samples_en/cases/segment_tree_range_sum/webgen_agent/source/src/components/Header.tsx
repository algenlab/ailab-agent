import React from 'react';

const headerStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, #1e3a5f 0%, #1e293b 60%, #0f172a 100%)',
  borderBottom: '2px solid #3b82f6',
  padding: '20px 0',
  marginBottom: '20px',
};

const titleStyle: React.CSSProperties = {
  fontSize: '1.8rem',
  fontWeight: 700,
  color: '#f1f5f9',
  letterSpacing: '-0.02em',
};

const subtitleStyle: React.CSSProperties = {
  fontSize: '0.95rem',
  color: '#94a3b8',
  marginTop: '4px',
};

const tagStyle: React.CSSProperties = {
  display: 'inline-block',
  background: '#7c3aed',
  color: '#e2e8f0',
  padding: '3px 12px',
  borderRadius: '20px',
  fontSize: '0.8rem',
  fontWeight: 600,
  marginTop: '8px',
};

export default function Header() {
  return (
    <header style={headerStyle}>
      <div className="container">
        <h1 style={titleStyle}>Segment Tree Range Sum</h1>
        <p style={subtitleStyle}>
          Interactive visualization of segment tree construction, range query, and point update
        </p>
        <span style={tagStyle}>Range Structure</span>
      </div>
    </header>
  );
}
