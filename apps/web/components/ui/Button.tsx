import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'destructive';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled,
  style,
  ...props
}) => {
  const getVariantStyles = (): React.CSSProperties => {
    switch (variant) {
      case 'secondary':
        return {
          backgroundColor: 'transparent',
          color: 'var(--color-text-primary)',
          border: '1px solid var(--color-border-strong)'
        };
      case 'ghost':
        return {
          backgroundColor: 'transparent',
          color: 'var(--color-text-secondary)',
          border: 'none'
        };
      case 'destructive':
        return {
          backgroundColor: 'var(--status-overdue-bg)',
          color: 'var(--status-overdue)',
          border: '1px solid transparent'
        };
      case 'primary':
      default:
        return {
          backgroundColor: 'var(--color-primary-900)',
          color: 'var(--color-text-inverse)',
          border: 'none'
        };
    }
  };

  const getSizeStyles = (): React.CSSProperties => {
    switch (size) {
      case 'sm':
        return { padding: '6px 12px', fontSize: '13px', borderRadius: 'var(--radius-sm)' };
      case 'lg':
        return { padding: '12px 24px', fontSize: '16px', borderRadius: 'var(--radius-md)' };
      case 'md':
      default:
        return { padding: '8px 16px', fontSize: '14px', borderRadius: 'var(--radius-md)' };
    }
  };

  return (
    <button
      disabled={disabled || isLoading}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '8px',
        fontWeight: 600,
        cursor: disabled || isLoading ? 'not-allowed' : 'pointer',
        opacity: disabled || isLoading ? 0.6 : 1,
        transition: 'all 0.15s ease',
        minHeight: size === 'lg' ? '48px' : size === 'sm' ? '32px' : '40px',
        ...getVariantStyles(),
        ...getSizeStyles(),
        ...style
      }}
      {...props}
    >
      {isLoading ? 'Loading...' : children}
    </button>
  );
};
