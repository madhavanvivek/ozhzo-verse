'use client';

import React, { useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { ShieldAlert, ArrowLeft, RefreshCw, AlertOctagon } from 'lucide-react';
import { apiClient } from '@/lib/apiClient';
import { AdminNav } from './components/AdminNav';
import { AdminHeader } from './components/AdminHeader';

export default function AdminLayout({
  children
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const isLoginPage = pathname === '/admin/login' || pathname.startsWith('/admin/login');

  const [user, setUser] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(!isLoginPage);
  const [isForbidden, setIsForbidden] = useState(false);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

  const checkSuperAdminAuth = async () => {
    if (isLoginPage) return;

    setIsLoading(true);
    setIsForbidden(false);

    try {
      const token = apiClient.getAccessToken();
      if (!token) {
        router.replace(`/admin/login?redirect=${encodeURIComponent(pathname || '/admin')}`);
        return;
      }

      // Authoritative backend identity check
      const profile = await apiClient.get<any>('/users/me');

      if (!profile) {
        router.replace(`/admin/login?redirect=${encodeURIComponent(pathname || '/admin')}`);
        return;
      }

      // Check if user is Super Admin
      const isSuper = Boolean(profile.is_super_admin || profile.system_role === 'SUPER_ADMIN');

      if (!isSuper) {
        setIsForbidden(true);
        setUser(profile);
      } else {
        setUser(profile);
        setIsForbidden(false);
      }
    } catch (err: any) {
      const msg = err?.message || '';
      if (msg.includes('401') || msg.includes('sign in') || msg.includes('Unauthorized')) {
        router.replace(`/admin/login?redirect=${encodeURIComponent(pathname || '/admin')}`);
      } else if (msg.includes('403') || msg.includes('privileges required')) {
        setIsForbidden(true);
      } else {
        // Retry or assume not authenticated
        router.replace(`/admin/login?redirect=${encodeURIComponent(pathname || '/admin')}`);
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!isLoginPage) {
      checkSuperAdminAuth();
    }
  }, [pathname, isLoginPage]);

  const handleLogout = () => {
    apiClient.clearTokens();
    apiClient.setActiveHomeId(null);
    router.replace('/admin/login');
  };

  // If on /admin/login, bypass the admin console layout frame
  if (isLoginPage) {
    return <>{children}</>;
  }

  // 1. Loading State
  if (isLoading) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          backgroundColor: '#0b1120',
          color: '#f8fafc',
          gap: '16px',
          padding: '24px'
        }}
      >
        <RefreshCw size={32} className="animate-spin" color="var(--color-accent-amber, #f59e0b)" />
        <div style={{ fontSize: '15px', fontWeight: 600 }}>Authenticating Platform Operations Console...</div>
      </div>
    );
  }

  // 2. Forbidden State (403 for normal users, OWNER, ADMIN, MEMBER, etc.)
  if (isForbidden) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          backgroundColor: 'var(--color-bg-canvas, #f8fafc)',
          padding: '24px'
        }}
      >
        <div
          style={{
            maxWidth: '520px',
            width: '100%',
            backgroundColor: 'var(--color-surface-card, #ffffff)',
            borderRadius: 'var(--radius-lg, 16px)',
            padding: '32px',
            border: '1px solid var(--color-border-subtle, #e2e8f0)',
            boxShadow: 'var(--shadow-card)',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '16px'
          }}
        >
          <div
            style={{
              width: '56px',
              height: '56px',
              borderRadius: 'var(--radius-full, 9999px)',
              backgroundColor: 'var(--status-overdue-bg, #fef2f2)',
              color: 'var(--status-overdue, #ef4444)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <AlertOctagon size={28} />
          </div>

          <h2
            style={{
              fontSize: '22px',
              fontWeight: 700,
              color: 'var(--color-text-primary, #0f172a)',
              margin: 0
            }}
          >
            403 Forbidden: Access Restricted
          </h2>

          <div
            style={{
              fontSize: '14px',
              color: 'var(--color-text-secondary, #64748b)',
              lineHeight: 1.6
            }}
          >
            The <strong>Ozhzo Platform Operations Console</strong> requires <code>SUPER_ADMIN</code> privileges.
            Household roles such as <code>OWNER</code>, <code>HOME_ADMIN</code>, and <code>MEMBER</code> are restricted to household workspace operations and cannot administer the platform.
          </div>

          <div
            style={{
              width: '100%',
              padding: '12px',
              backgroundColor: 'var(--color-surface-subtle, #f1f5f9)',
              borderRadius: 'var(--radius-md, 10px)',
              fontSize: '13px',
              color: 'var(--color-text-secondary, #64748b)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px'
            }}
          >
            <ShieldAlert size={16} color="var(--status-low-stock, #f59e0b)" />
            <span>Authenticated user: <strong>{user?.email || 'Active Account'}</strong></span>
          </div>

          <button
            onClick={() => router.replace('/dashboard')}
            style={{
              marginTop: '8px',
              minHeight: '44px',
              padding: '12px 24px',
              borderRadius: 'var(--radius-md, 10px)',
              backgroundColor: 'var(--color-primary-900, #0f172a)',
              color: 'var(--color-text-inverse, #ffffff)',
              fontSize: '14px',
              fontWeight: 600,
              border: 'none',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              width: '100%',
              justifyContent: 'center'
            }}
          >
            <ArrowLeft size={16} />
            <span>Return to Household Dashboard</span>
          </button>
        </div>
      </div>
    );
  }

  // 3. Authorized Super Admin Layout
  return (
    <div
      style={{
        display: 'flex',
        minHeight: '100vh',
        backgroundColor: 'var(--color-bg-canvas, #f8fafc)',
        color: 'var(--color-text-primary, #0f172a)'
      }}
    >
      <AdminNav
        currentUser={user}
        onLogout={handleLogout}
        isMobileOpen={isMobileNavOpen}
        onCloseMobile={() => setIsMobileNavOpen(false)}
      />

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <AdminHeader
          onOpenMobileNav={() => setIsMobileNavOpen(true)}
          currentUser={user}
        />
        <main
          style={{
            flex: 1,
            padding: '24px 20px',
            maxWidth: '1400px',
            width: '100%',
            margin: '0 auto'
          }}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
