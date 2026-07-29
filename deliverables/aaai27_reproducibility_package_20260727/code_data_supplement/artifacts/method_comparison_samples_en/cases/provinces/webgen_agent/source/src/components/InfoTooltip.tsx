import React, { useState } from 'react';

interface InfoTooltipProps {
  text: string;
  ariaLabel?: string;
}

const InfoTooltip: React.FC<InfoTooltipProps> = ({ text, ariaLabel }) => {
  const [visible, setVisible] = useState(false);

  return (
    <span
      style={styles.wrapper}
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
      tabIndex={0}
      role="tooltip"
      aria-label={ariaLabel ?? text}
    >
      <span style={styles.icon} aria-hidden="true">
        ?
      </span>
      {visible && <span style={styles.tooltip}>{text}</span>}
    </span>
  );
};

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    position: 'relative',
    display: 'inline-flex',
    alignItems: 'center',
    cursor: 'help',
    marginLeft: '0.25rem',
  },
  icon: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '18px',
    height: '18px',
    borderRadius: '50%',
    background: 'var(--border)',
    color: 'var(--text-muted)',
    fontSize: '0.7rem',
    fontWeight: 700,
    lineHeight: 1,
  },
  tooltip: {
    position: 'absolute',
    bottom: '120%',
    left: '50%',
    transform: 'translateX(-50%)',
    background: '#1a202c',
    color: '#fff',
    padding: '0.375rem 0.625rem',
    borderRadius: 'var(--radius-sm)',
    fontSize: '0.75rem',
    whiteSpace: 'nowrap',
    zIndex: 100,
    pointerEvents: 'none',
    boxShadow: 'var(--shadow-lg)',
  },
};

export default InfoTooltip;
