'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Users,
  Home,
  CreditCard,
  Tag,
  Activity,
  ArrowLeft,
  LogOut,
  ShieldCheck,
  X
} from 'lucide-react';
import { Logo } from '@/components/brand/Logo';

interface AdminNavProps {
  currentUser?: {
    email?: string | null;
    display_name?: string | null;
    is_super_admin?: boolean;
    system_role?: string;
  } | null;
  onLogout?: () => void;
  isMobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export function AdminNav({
  currentUser,
  onLogout,
  isMobileOpen = false,
  onCloseMobile
}: AdminNavProps) {
  const pathname = usePathname();

  const navItems = [
    { href: '/admin', label: 'Dashboard', icon: LayoutDashboard, exact: true },
    { href: '/admin/users', label: 'Users', icon: Users, exact: false },
    { href: '/admin/homes', label: 'Homes', icon: Home, exact: false },
    { href: '/admin/subscriptions', label: 'Subscriptions', icon: CreditCard, exact: false },
    { href: '/admin/coupons', label: 'Coupons & Grants', icon: Tag, exact: false },
    { href: '/admin/activity', label: 'Activity Logs', icon: Activity, exact: false }
  ];

  const isLinkActive = (item: (typeof navItems)[0]) => {
    if (item.exact) {
      return pathname === item.href;
    }
    return pathname.startsWith(item.href);
  };

  const navContent = (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: '#0b1120',
        color: '#f8fafc',
        padding: '20px 16px',
        justifyContent: 'space-between'
      }}
    >
      <div>
        {/* Logo & Platform Tag */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Logo variant="mark" width={32} height={32} href="/admin" />
            <div>
              <div style={{ fontSize: '15px', fontWeight: 700, color: '#ffffff', letterSpacing: '-0.01em' }}>
                OZHZO VERSE
              </div>
              <div
                style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  color: 'var(--color-accent-amber, #f59e0b)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  marginTop: '1px'
                }}
              >
                <ShieldCheck size={12} />
                Platform Admin
              </div>
            </div>
          </div>

          {onCloseMobile && (
            <button
              onClick={onCloseMobile}
              style={{
                background: 'none',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                padding: '8px',
                minHeight: '44px',
                minWidth: '44px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
              className="ozhzo-mobile-only"
              aria-label="Close menu"
            >
              <X size={22} />
            </button>
          )}
        </div>

        {/* Section Label */}
        <div
          style={{
            fontSize: '11px',
            fontWeight: 700,
            color: '#64748b',
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            padding: '0 8px',
            marginBottom: '12px'
          }}
        >
          Operations Console
        </div>

        {/* Navigation Items */}
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {navItems.map((item) => {
            const active = isLinkActive(item);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onCloseMobile}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '10px 12px',
                  borderRadius: 'var(--radius-md, 10px)',
                  fontSize: '14px',
                  fontWeight: active ? 600 : 500,
                  color: active ? '#ffffff' : '#94a3b8',
                  backgroundColor: active ? '#1e293b' : 'transparent',
                  border: active ? '1px solid #334155' : '1px solid transparent',
                  transition: 'all 0.15s ease',
                  minHeight: '44px'
                }}
              >
                <Icon size={18} color={active ? 'var(--color-accent-amber, #f59e0b)' : '#94a3b8'} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer Section */}
      <div
        style={{
          borderTop: '1px solid #1e293b',
          paddingTop: '16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px'
        }}
      >
        {/* Super Admin Info */}
        <div
          style={{
            padding: '8px 12px',
            backgroundColor: '#131d31',
            borderRadius: 'var(--radius-md, 10px)',
            border: '1px solid #1e293b'
          }}
        >
          <div style={{ fontSize: '11px', fontWeight: 600, color: '#94a3b8' }}>SUPER ADMIN</div>
          <div
            style={{
              fontSize: '13px',
              fontWeight: 600,
              color: '#ffffff',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap'
            }}
          >
            {currentUser?.email || currentUser?.display_name || 'Administrator'}
          </div>
        </div>

        {/* Back to Household Dashboard */}
        <Link
          href="/dashboard"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: '10px 12px',
            borderRadius: 'var(--radius-md, 10px)',
            fontSize: '13px',
            fontWeight: 500,
            color: '#cbd5e1',
            backgroundColor: 'transparent',
            minHeight: '44px'
          }}
        >
          <ArrowLeft size={16} />
          <span>Exit to Household</span>
        </Link>

        {/* Logout */}
        {onLogout && (
          <button
            onClick={onLogout}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '10px 12px',
              borderRadius: 'var(--radius-md, 10px)',
              fontSize: '13px',
              fontWeight: 500,
              color: '#f87171',
              backgroundColor: 'transparent',
              border: 'none',
              cursor: 'pointer',
              width: '100%',
              minHeight: '44px',
              textAlign: 'left'
            }}
          >
            <LogOut size={16} />
            <span>Sign Out</span>
          </button>
        )}
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop / Tablet Persistent Sidebar */}
      <aside
        style={{
          width: '260px',
          height: '100vh',
          position: 'sticky',
          top: 0,
          flexShrink: 0,
          display: 'none',
          zIndex: 40
        }}
        className="admin-sidebar-desktop"
      >
        {navContent}
      </aside>

      {/* Mobile Drawer Backdrop */}
      {isMobileOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.7)',
            backdropFilter: 'blur(4px)',
            zIndex: 999
          }}
          onClick={onCloseMobile}
        />
      )}

      {/* Mobile Drawer */}
      <aside
        style={{
          position: 'fixed',
          top: 0,
          bottom: 0,
          left: 0,
          width: '280px',
          zIndex: 1000,
          transform: isMobileOpen ? 'translateX(0)' : 'translateX(-100%)',
          transition: 'transform 0.25s ease-in-out',
          boxShadow: isMobileOpen ? 'var(--shadow-modal)' : 'none'
        }}
        className="ozhzo-mobile-drawer"
      >
        {navContent}
      </aside>

      <style jsx global>{`
        @media (min-width: 1024px) {
          .admin-sidebar-desktop {
            display: block !important;
          }
          .admin-mobile-header-btn {
            display: none !important;
          }
        }
      `}</style>
    </>
  );
}
