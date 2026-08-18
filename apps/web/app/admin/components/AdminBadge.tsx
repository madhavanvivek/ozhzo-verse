'use client';

import React from 'react';

interface AdminBadgeProps {
  variant?: 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'purple';
  children: React.ReactNode;
  size?: 'sm' | 'md';
}

export function AdminBadge({ variant = 'neutral', children, size = 'sm' }: AdminBadgeProps) {
  const styles: Record<string, { bg: string; text: string; border: string }> = {
    success: {
      bg: 'var(--status-in-stock-bg, #ecfdf5)',
      text: 'var(--status-in-stock, #10b981)',
      border: '#a7f3d0'
    },
    warning: {
      bg: 'var(--status-low-stock-bg, #fffbeb)',
      text: 'var(--status-low-stock, #b45309)',
      border: '#fde68a'
    },
    danger: {
      bg: 'var(--status-overdue-bg, #fef2f2)',
      text: 'var(--status-overdue, #ef4444)',
      border: '#fecaca'
    },
    info: {
      bg: '#eff6ff',
      text: '#2563eb',
      border: '#bfdbfe'
    },
    purple: {
      bg: '#faf5ff',
      text: '#7e22ce',
      border: '#e9d5ff'
    },
    neutral: {
      bg: 'var(--color-surface-subtle, #f1f5f9)',
      text: 'var(--color-text-secondary, #64748b)',
      border: 'var(--color-border-subtle, #e2e8f0)'
    }
  };

  const current = styles[variant] || styles.neutral;
  const padding = size === 'sm' ? '2px 8px' : '4px 12px';
  const fontSize = size === 'sm' ? '11px' : '13px';

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        padding,
        fontSize,
        fontWeight: 600,
        borderRadius: 'var(--radius-full, 9999px)',
        backgroundColor: current.bg,
        color: current.text,
        border: `1px solid ${current.border}`,
        whiteSpace: 'nowrap',
        letterSpacing: '0.02em',
        lineHeight: 1.2
      }}
    >
      {children}
    </span>
  );
}
