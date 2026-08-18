import React, { forwardRef } from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(({
  label,
  error,
  id,
  style,
  ...props
}, ref) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', width: '100%' }}>
      {label && (
        <label htmlFor={id} style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
          {label}
        </label>
      )}
      <input
        ref={ref}
        id={id}
        style={{
          height: '42px',
          padding: '0 12px',
          fontSize: '14px',
          borderRadius: 'var(--radius-md)',
          border: `1px solid ${error ? 'var(--status-overdue)' : 'var(--color-border-strong)'}`,
          outline: 'none',
          backgroundColor: 'var(--color-surface-card)',
          color: 'var(--color-text-primary)',
          ...style
        }}
        {...props}
      />
      {error && (
        <span style={{ fontSize: '12px', color: 'var(--status-overdue)', fontWeight: 500 }}>
          {error}
        </span>
      )}
    </div>
  );
});

Input.displayName = 'Input';
