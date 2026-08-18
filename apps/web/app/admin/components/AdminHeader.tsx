'use client';

import React from 'react';
import Link from 'next/link';
import { Menu, ShieldAlert, ArrowLeft, User as UserIcon } from 'lucide-react';

interface AdminHeaderProps {
  title?: string;
  onOpenMobileNav: () => void;
  currentUser?: {
    email?: string | null;
    display_name?: string | null;
    is_super_admin?: boolean;
    system_role?: string;
  } | null;
}

export function AdminHeader({
  title = 'Platform Operations Console',
  onOpenMobileNav,
  currentUser
}: AdminHeaderProps) {
  return (
    <header
      style={{
        height: '64px',
        backgroundColor: 'var(--color-surface-card, #ffffff)',
        borderBottom: '1px solid var(--color-border-subtle, #e2e8f0)',
        padding: '0 20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 30
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <button
          onClick={onOpenMobileNav}
          className="admin-mobile-header-btn"
          aria-label="Open administration menu"
          style={{
            background: 'none',
            border: '1px solid var(--color-border-subtle, #e2e8f0)',
            borderRadius: 'var(--radius-md, 10px)',
            padding: '8px',
            cursor: 'pointer',
            minHeight: '44px',
            minWidth: '44px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--color-text-primary, #0f172a)'
          }}
        >
          <Menu size={20} />
        </button>

        <div>
          <h1
            style={{
              fontSize: '18px',
              fontWeight: 700,
              color: 'var(--color-text-primary, #0f172a)',
              margin: 0,
              lineHeight: 1.2
            }}
          >
            {title}
          </h1>
          <div
            style={{
              fontSize: '11px',
              fontWeight: 600,
              color: 'var(--color-accent-warm, #f97316)',
              letterSpacing: '0.02em',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            <ShieldAlert size={12} />
            <span>PLATFORM SUPER ADMIN SCOPE</span>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        {/* Household App Exit Link */}
        <Link
          href="/dashboard"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '8px 12px',
            borderRadius: 'var(--radius-md, 10px)',
            border: '1px solid var(--color-border-subtle, #e2e8f0)',
            backgroundColor: 'var(--color-surface-subtle, #f1f5f9)',
            fontSize: '13px',
            fontWeight: 600,
            color: 'var(--color-text-secondary, #64748b)',
            minHeight: '40px'
          }}
        >
          <ArrowLeft size={14} />
          <span className="ozhzo-desktop-only">Household Dashboard</span>
        </Link>

        {/* Current Super Admin Identity */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 12px',
            backgroundColor: 'var(--color-primary-900, #0f172a)',
            color: '#ffffff',
            borderRadius: 'var(--radius-full, 9999px)',
            fontSize: '12px',
            fontWeight: 600
          }}
        >
          <UserIcon size={14} color="var(--color-accent-amber, #f59e0b)" />
          <span
            style={{
              maxWidth: '140px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap'
            }}
          >
            {currentUser?.email?.split('@')[0] || 'Super Admin'}
          </span>
        </div>
      </div>
    </header>
  );
}
