import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'subtle';
}

export const Card: React.FC<CardProps> = ({
  children,
  variant = 'default',
  style,
  ...props
}) => {
  return (
    <div
      style={{
        backgroundColor: variant === 'subtle' ? 'var(--color-surface-subtle)' : 'var(--color-surface-card)',
        border: '1px solid var(--color-border-subtle)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-4)',
        boxShadow: variant === 'default' ? 'var(--shadow-subtle)' : 'none',
        ...style
      }}
      {...props}
    >
      {children}
    </div>
  );
};
