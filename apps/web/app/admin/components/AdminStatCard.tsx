'use client';

import React from 'react';

interface AdminStatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  trend?: string;
}

export function AdminStatCard({
  title,
  value,
  subtitle,
  icon,
  variant = 'default',
  trend
}: AdminStatCardProps) {
  const accentColors: Record<string, string> = {
    default: 'var(--color-primary-900, #0f172a)',
    success: 'var(--status-in-stock, #10b981)',
    warning: 'var(--status-low-stock, #f59e0b)',
    danger: 'var(--status-overdue, #ef4444)',
    info: '#2563eb'
  };

  return (
    <div
      style={{
        backgroundColor: 'var(--color-surface-card, #ffffff)',
        border: '1px solid var(--color-border-subtle, #e2e8f0)',
        borderRadius: 'var(--radius-lg, 16px)',
        padding: '20px',
        boxShadow: 'var(--shadow-subtle, 0 1px 2px 0 rgba(15, 23, 42, 0.04))',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        position: 'relative',
        overflow: 'hidden'
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '3px',
          backgroundColor: accentColors[variant] || accentColors.default
        }}
      />
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '12px' }}>
        <span
          style={{
            fontSize: '13px',
            fontWeight: 600,
            color: 'var(--color-text-secondary, #64748b)',
            textTransform: 'uppercase',
            letterSpacing: '0.04em'
          }}
        >
          {title}
        </span>
        {icon && (
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: 'var(--radius-md, 10px)',
              backgroundColor: 'var(--color-surface-subtle, #f1f5f9)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: accentColors[variant] || 'var(--color-text-primary, #0f172a)',
              flexShrink: 0
            }}
          >
            {icon}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
        <span
          style={{
            fontSize: '28px',
            fontWeight: 700,
            color: 'var(--color-text-primary, #0f172a)',
            letterSpacing: '-0.02em',
            lineHeight: 1.1
          }}
        >
          {value}
        </span>
        {trend && (
          <span
            style={{
              fontSize: '12px',
              fontWeight: 600,
              color: 'var(--color-text-secondary, #64748b)'
            }}
          >
            {trend}
          </span>
        )}
      </div>

      {subtitle && (
        <div
          style={{
            marginTop: '8px',
            fontSize: '12px',
            color: 'var(--color-text-tertiary, #94a3b8)'
          }}
        >
          {subtitle}
        </div>
      )}
    </div>
  );
}
