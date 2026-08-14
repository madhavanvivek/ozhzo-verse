import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'in-stock' | 'low-stock' | 'overdue' | 'completed' | 'neutral';
}

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'neutral' }) => {
  const getColors = () => {
    switch (variant) {
      case 'in-stock':
        return { bg: 'var(--status-in-stock-bg)', text: 'var(--status-in-stock)' };
      case 'low-stock':
        return { bg: 'var(--status-low-stock-bg)', text: 'var(--status-low-stock)' };
      case 'overdue':
        return { bg: 'var(--status-overdue-bg)', text: 'var(--status-overdue)' };
      case 'completed':
        return { bg: 'var(--status-completed-bg)', text: 'var(--status-completed)' };
      case 'neutral':
      default:
        return { bg: 'var(--color-surface-subtle)', text: 'var(--color-text-secondary)' };
    }
  };

  const { bg, text } = getColors();

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '2px 8px',
        fontSize: '11px',
        fontWeight: 600,
        borderRadius: 'var(--radius-sm)',
        backgroundColor: bg,
        color: text,
        textTransform: 'uppercase',
        letterSpacing: '0.04em'
      }}
    >
      {children}
    </span>
  );
};
