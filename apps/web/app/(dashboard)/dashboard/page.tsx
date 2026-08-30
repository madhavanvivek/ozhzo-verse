'use client';

import React, { useState, useEffect, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import {
  CheckCircle2,
  AlertTriangle,
  Receipt,
  ShoppingCart,
  Bell,
  RefreshCw,
  Sparkles,
  Users,
  Check,
  Home,
  Plus,
  X,
  Package,
  ArrowRight,
  Phone,
  ShieldCheck
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

interface DashboardData {
  greeting: {
    greeting: string;
    user_display_name: string;
    date_formatted: string;
    time_period: string;
  };
  summary: {
    home_id: string;
    home_name: string;
    currency: string;
    timezone: string;
    members_count: number;
    active_tasks_count: number;
    low_stock_count: number;
    unpaid_bills_count: number;
    unpaid_bills_sum: number;
    upcoming_events_count: number;
    unread_notifications_count: number;
  };
  pending_tasks: Array<{
    id: string;
    title: string;
    priority: string;
    status: string;
    due_date?: string | null;
  }>;
  upcoming_bills: Array<{
    id: string;
    title: string;
    amount: number;
    currency: string;
    due_date: string;
    status: string;
  }>;
  upcoming_events: Array<{
    id: string;
    title: string;
    start_time: string;
    end_time: string;
    is_all_day: boolean;
    location?: string | null;
  }>;
  low_stock_inventory: Array<{
    id: string;
    name: string;
    quantity: number;
    unit: string;
    status: string;
  }>;
  shopping_items: Array<{
    id: string;
    name: string;
    quantity: number;
    unit: string;
    is_checked: boolean;
  }>;
  notifications: Array<{
    id: string;
    title: string;
    body: string;
    type: string;
    created_at: string;
  }>;
  role: string;
}

function DashboardPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [userHomes, setUserHomes] = useState<Array<{ id: string; name: string; role: string }>>([]);
  const [activeHomeId, setActiveHomeId] = useState<string | null>(null);
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [userProfile, setUserProfile] = useState<{
    id?: string;
    email?: string | null;
    phone_number?: string | null;
    mobile_verified?: boolean;
    display_name?: string;
  } | null>(null);

  // Modal states for State A (Create Home & Join Home)
  const [isCreateHomeOpen, setIsCreateHomeOpen] = useState(false);
  const [isJoinHomeOpen, setIsJoinHomeOpen] = useState(false);

  // Create Home Form State
  const [newHomeName, setNewHomeName] = useState('');
  const [newHomeCurrency, setNewHomeCurrency] = useState('USD');
  const [newHomeTimezone, setNewHomeTimezone] = useState('UTC');
  const [newHomeCountry, setNewHomeCountry] = useState('US');
  const [isCreatingHome, setIsCreatingHome] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Join Home Form State
  const [invitationToken, setInvitationToken] = useState('');
  const [isJoiningHome, setIsJoiningHome] = useState(false);
  const [joinError, setJoinError] = useState<string | null>(null);

  const loadDashboard = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const initialHomeId = apiClient.getActiveHomeId();

      // 1. Fetch user profile, accessible homes, and dashboard data in parallel
      const [profileRes, homesRes, initialDashboardRes] = await Promise.allSettled([
        apiClient.get<any>('/users/me'),
        apiClient.get<Array<{ id: string; name: string; role: string }>>('/homes'),
        initialHomeId ? apiClient.get<any>(`/homes/${initialHomeId}/dashboard`) : Promise.resolve(null)
      ]);

      if (profileRes.status === 'rejected') {
        throw new Error(profileRes.reason?.message || 'Failed to authenticate user profile.');
      }
      if (homesRes.status === 'rejected') {
        throw new Error(homesRes.reason?.message || 'Failed to load user homes.');
      }

      const profileData = profileRes.value;
      setUserProfile(profileData);

      const accessibleHomes: Array<{ id: string; name: string; role: string }> = Array.isArray(homesRes.value) ? homesRes.value : [];
      setUserHomes(accessibleHomes);

      // STATE A: User has zero homes -> Onboarding State
      if (accessibleHomes.length === 0) {
        setActiveHomeId(null);
        setData(null);
        setIsLoading(false);
        return;
      }

      // STATE B: User has 1 or more homes -> Resolve and load active home dashboard
      const resolvedHomeId = apiClient.resolveActiveHome(accessibleHomes);
      setActiveHomeId(resolvedHomeId);

      if (!resolvedHomeId) {
        setData(null);
        setIsLoading(false);
        return;
      }

      // Fetch or use parallel home-scoped dashboard data
      try {
        let res: any = null;
        if (resolvedHomeId === initialHomeId && initialDashboardRes.status === 'fulfilled' && initialDashboardRes.value) {
          res = initialDashboardRes.value;
        } else {
          res = await apiClient.get<any>(`/homes/${resolvedHomeId}/dashboard`);
        }

        if (res) {
          const currentHome = accessibleHomes.find((h) => h.id === resolvedHomeId);
          const normalizedData: DashboardData = {
            greeting: res.greeting || {
              greeting: 'Welcome',
              user_display_name: profileData?.display_name || 'Home',
              date_formatted: '',
              time_period: ''
            },
            summary: res.summary || {
              home_id: resolvedHomeId,
              home_name: currentHome?.name || res.home_name || 'Home',
              currency: res.currency || 'USD',
              timezone: res.timezone || 'UTC',
              members_count: 1,
              active_tasks_count: 0,
              low_stock_count: 0,
              unpaid_bills_count: 0,
              unpaid_bills_sum: 0,
              upcoming_events_count: 0,
              unread_notifications_count: 0
            },
            pending_tasks: Array.isArray(res.pending_tasks) ? res.pending_tasks : [],
            upcoming_bills: Array.isArray(res.upcoming_bills) ? res.upcoming_bills : [],
            upcoming_events: Array.isArray(res.upcoming_events) ? res.upcoming_events : [],
            low_stock_inventory: Array.isArray(res.low_stock_inventory) ? res.low_stock_inventory : [],
            shopping_items: Array.isArray(res.shopping_items) ? res.shopping_items : [],
            notifications: Array.isArray(res.notifications) ? res.notifications : [],
            role: res.role || currentHome?.role || 'MEMBER'
          };
          setData(normalizedData);
          setError(null);
        }
      } catch (dashErr: any) {
        console.error('Failed to load active home dashboard:', dashErr);
        setError(dashErr?.message || 'Unable to load dashboard for this home.');
      }
    } catch (err: any) {
      console.error('Failed to initialize dashboard:', err);
      setError(err?.message || 'Unable to load dashboard. Please check your connection.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();

    const handleHomeChanged = () => {
      loadDashboard();
    };

    window.addEventListener('home-changed', handleHomeChanged);
    return () => window.removeEventListener('home-changed', handleHomeChanged);
  }, []);

  useEffect(() => {
    const action = searchParams.get('action');
    if (action === 'create_home') {
      setIsCreateHomeOpen(true);
      if (typeof window !== 'undefined') {
        const savedDraft = localStorage.getItem('draft_home_name');
        if (savedDraft) {
          setNewHomeName(savedDraft);
          localStorage.removeItem('draft_home_name');
        }
      }
    } else if (action === 'join_home') {
      setIsJoinHomeOpen(true);
    }
  }, [searchParams]);

  const handleCreateHome = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newHomeName.trim()) return;

    setIsCreatingHome(true);
    setCreateError(null);

    try {
      const res = await apiClient.post<{ id: string; name: string }>('/homes', {
        name: newHomeName.trim(),
        currency: newHomeCurrency,
        timezone: newHomeTimezone,
        country: newHomeCountry
      });

      const createdHomeId = res?.id;
      if (createdHomeId) {
        apiClient.setActiveHomeId(createdHomeId);
        localStorage.setItem('active_home_id', createdHomeId);
        window.dispatchEvent(new Event('home-changed'));
      }

      setIsCreateHomeOpen(false);
      setNewHomeName('');
      await loadDashboard();
    } catch (err: any) {
      console.error('Create home failed:', err);
      const msg = err?.message || '';
      if (
        msg.includes('MOBILE_VERIFICATION_REQUIRED') ||
        msg.includes('Mobile number verification is required') ||
        msg.includes('verification is required')
      ) {
        router.push('/verify-mobile?redirect=/dashboard&action=create_home');
        return;
      }
      setCreateError(msg || 'Failed to create Home workspace.');
    } finally {
      setIsCreatingHome(false);
    }
  };

  const handleJoinHome = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!invitationToken.trim()) return;

    setIsJoiningHome(true);
    setJoinError(null);

    try {
      const res = await apiClient.post<{ home_id?: string }>(`/invitations/${invitationToken.trim()}/accept`);
      if (res?.home_id) {
        apiClient.setActiveHomeId(res.home_id);
        localStorage.setItem('active_home_id', res.home_id);
        window.dispatchEvent(new Event('home-changed'));
      }

      setIsJoinHomeOpen(false);
      setInvitationToken('');
      await loadDashboard();
    } catch (err: any) {
      console.error('Join home failed:', err);
      setJoinError(err?.message || 'Invalid or expired invitation token.');
    } finally {
      setIsJoiningHome(false);
    }
  };

  const maskPhoneNumber = (phone?: string | null): string => {
    if (!phone) return '';
    const clean = phone.trim();
    if (clean.length <= 4) return clean;
    const lastFour = clean.slice(-4);
    const prefix = clean.slice(0, Math.min(3, clean.length - 4));
    return `${prefix} •••• ••${lastFour}`;
  };

  const renderCreateHomeModal = () => {
    if (!isCreateHomeOpen) return null;

    const isUnverified = userProfile ? userProfile.mobile_verified === false : false;
    const isVerifiedJustNow = !isUnverified && userProfile?.mobile_verified === true && searchParams.get('action') === 'create_home';

    const handleNavigateToVerify = () => {
      if (newHomeName.trim()) {
        localStorage.setItem('draft_home_name', newHomeName.trim());
      }
      router.push('/verify-mobile?redirect=/dashboard&action=create_home');
    };

    return (
      <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px' }}>
        <div style={{ width: '100%', maxWidth: '480px', maxHeight: '90vh', overflowY: 'auto', backgroundColor: 'var(--color-surface-card)', borderRadius: 'var(--radius-lg)', padding: '24px', boxShadow: 'var(--shadow-modal)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Home size={20} color="var(--color-primary-900)" />
              <h3 style={{ fontSize: '18px', fontWeight: 700 }}>Create Your Home</h3>
            </div>
            <button
              onClick={() => setIsCreateHomeOpen(false)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              aria-label="Close dialog"
            >
              <X size={18} />
            </button>
          </div>

          {/* Unverified Guidance Banner */}
          {isUnverified && (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                padding: '14px 16px',
                backgroundColor: 'rgba(217, 119, 6, 0.08)',
                border: '1px solid rgba(217, 119, 6, 0.3)',
                borderRadius: 'var(--radius-md)',
                marginBottom: '16px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '24px',
                    height: '24px',
                    borderRadius: '50%',
                    backgroundColor: 'rgba(217, 119, 6, 0.2)',
                    color: '#d97706',
                    flexShrink: 0
                  }}
                >
                  <Phone size={13} />
                </div>
                <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                  Verify your mobile number to continue
                </div>
              </div>

              <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>
                A verified mobile number is required before you can create a Home.
                {userProfile?.phone_number && (
                  <span style={{ display: 'block', marginTop: '2px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                    Linked mobile: {maskPhoneNumber(userProfile.phone_number)}
                  </span>
                )}
              </div>

              <button
                type="button"
                id="modal-verify-mobile-action-btn"
                onClick={handleNavigateToVerify}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                  minHeight: '44px',
                  padding: '0 16px',
                  backgroundColor: 'var(--color-primary-900)',
                  color: 'var(--color-primary-contrast)',
                  border: 'none',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  alignSelf: 'flex-start',
                  marginTop: '4px'
                }}
              >
                <ShieldCheck size={15} /> Verify Mobile Number
              </button>
            </div>
          )}

          {/* Verified Success Banner */}
          {isVerifiedJustNow && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 14px',
                backgroundColor: 'rgba(16, 185, 129, 0.08)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                borderRadius: 'var(--radius-md)',
                color: '#047857',
                fontSize: '13px',
                fontWeight: 600,
                marginBottom: '16px'
              }}
            >
              <CheckCircle2 size={16} style={{ color: '#10b981', flexShrink: 0 }} />
              <div>
                Mobile number verified. You can now create your Home.
              </div>
            </div>
          )}

          {createError && (
            <div style={{ padding: '10px 14px', backgroundColor: 'var(--status-overdue-bg)', color: 'var(--status-overdue)', borderRadius: 'var(--radius-md)', fontSize: '13px', marginBottom: '16px' }}>
              {createError}
            </div>
          )}

          <form onSubmit={handleCreateHome} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ opacity: isUnverified ? 0.75 : 1 }}>
              <Input
                id="homeName"
                label="Household Name"
                placeholder="e.g. Sunnyvale Haven"
                value={newHomeName}
                onChange={(e) => setNewHomeName(e.target.value)}
                required={!isUnverified}
                disabled={isUnverified}
                autoFocus={!isUnverified}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', opacity: isUnverified ? 0.75 : 1 }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label htmlFor="modalCountry" style={{ fontSize: '13px', fontWeight: 600 }}>Country</label>
                <select
                  id="modalCountry"
                  value={newHomeCountry}
                  onChange={(e) => setNewHomeCountry(e.target.value)}
                  disabled={isUnverified}
                  style={{
                    height: '40px',
                    padding: '0 10px',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--color-border-strong)',
                    fontSize: '13px',
                    backgroundColor: isUnverified ? 'var(--color-surface-subtle)' : 'var(--color-surface-card)',
                    cursor: isUnverified ? 'not-allowed' : 'default'
                  }}
                >
                  <option value="US">United States (US)</option>
                  <option value="IN">India (IN)</option>
                  <option value="GB">United Kingdom (GB)</option>
                  <option value="CA">Canada (CA)</option>
                  <option value="AU">Australia (AU)</option>
                  <option value="DE">Germany (DE)</option>
                </select>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label htmlFor="modalCurrency" style={{ fontSize: '13px', fontWeight: 600 }}>Primary Currency</label>
                <select
                  id="modalCurrency"
                  value={newHomeCurrency}
                  onChange={(e) => setNewHomeCurrency(e.target.value)}
                  disabled={isUnverified}
                  style={{
                    height: '40px',
                    padding: '0 10px',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--color-border-strong)',
                    fontSize: '13px',
                    backgroundColor: isUnverified ? 'var(--color-surface-subtle)' : 'var(--color-surface-card)',
                    cursor: isUnverified ? 'not-allowed' : 'default'
                  }}
                >
                  <option value="USD">USD ($)</option>
                  <option value="EUR">EUR (€)</option>
                  <option value="GBP">GBP (£)</option>
                  <option value="CAD">CAD ($)</option>
                  <option value="AUD">AUD ($)</option>
                  <option value="INR">INR (₹)</option>
                </select>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', opacity: isUnverified ? 0.75 : 1 }}>
              <label htmlFor="modalTimezone" style={{ fontSize: '13px', fontWeight: 600 }}>Timezone</label>
              <select
                id="modalTimezone"
                value={newHomeTimezone}
                onChange={(e) => setNewHomeTimezone(e.target.value)}
                disabled={isUnverified}
                style={{
                  height: '40px',
                  padding: '0 10px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border-strong)',
                  fontSize: '13px',
                  backgroundColor: isUnverified ? 'var(--color-surface-subtle)' : 'var(--color-surface-card)',
                  cursor: isUnverified ? 'not-allowed' : 'default'
                }}
              >
                <option value="UTC">UTC</option>
                <option value="America/New_York">America/New York (EST)</option>
                <option value="America/Chicago">America/Chicago (CST)</option>
                <option value="America/Los_Angeles">America/Los Angeles (PST)</option>
                <option value="Europe/London">Europe/London (GMT)</option>
                <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
              </select>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '8px' }}>
              <Button type="button" variant="secondary" onClick={() => setIsCreateHomeOpen(false)} style={{ minHeight: '44px' }}>
                Cancel
              </Button>
              {isUnverified ? (
                <Button
                  type="button"
                  id="modal-primary-verify-btn"
                  variant="primary"
                  onClick={handleNavigateToVerify}
                  style={{ minHeight: '44px' }}
                >
                  <ShieldCheck size={16} style={{ marginRight: '6px' }} /> Verify Mobile Number
                </Button>
              ) : (
                <Button
                  type="submit"
                  id="modal-primary-create-btn"
                  variant="primary"
                  isLoading={isCreatingHome}
                  style={{ minHeight: '44px' }}
                >
                  Create Home
                </Button>
              )}
            </div>
          </form>
        </div>
      </div>
    );
  };

  const renderJoinHomeModal = () => {
    if (!isJoinHomeOpen) return null;

    return (
      <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px' }}>
        <div style={{ width: '100%', maxWidth: '480px', maxHeight: '90vh', overflowY: 'auto', backgroundColor: 'var(--color-surface-card)', borderRadius: 'var(--radius-lg)', padding: '24px', boxShadow: 'var(--shadow-modal)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Users size={20} color="var(--color-primary-900)" />
              <h3 style={{ fontSize: '18px', fontWeight: 700 }}>Join a Home</h3>
            </div>
            <button
              onClick={() => setIsJoinHomeOpen(false)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              aria-label="Close dialog"
            >
              <X size={18} />
            </button>
          </div>

          {joinError && (
            <div style={{ padding: '10px 14px', backgroundColor: 'var(--status-overdue-bg)', color: 'var(--status-overdue)', borderRadius: 'var(--radius-md)', fontSize: '13px', marginBottom: '16px' }}>
              {joinError}
            </div>
          )}

          <form onSubmit={handleJoinHome} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <Input
              id="invitationToken"
              label="Invitation Code / Token"
              placeholder="Paste invitation code here"
              value={invitationToken}
              onChange={(e) => setInvitationToken(e.target.value)}
              required
              autoFocus
            />

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '8px' }}>
              <Button type="button" variant="secondary" onClick={() => setIsJoinHomeOpen(false)} style={{ minHeight: '44px' }}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" isLoading={isJoiningHome} style={{ minHeight: '44px' }}>
                Join Home
              </Button>
            </div>
          </form>
        </div>
      </div>
    );
  };

  if (isLoading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', padding: 'var(--space-4)' }}>
        <div style={{ height: '60px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: 'var(--radius-md)', animation: 'pulse 1.5s infinite' }} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 'var(--space-4)' }}>
          {[1, 2, 3, 4].map((i) => (
            <div key={i} style={{ height: '90px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: 'var(--radius-lg)' }} />
          ))}
        </div>
      </div>
    );
  }

  // ===========================================================================
  // STATE A — USER HAS NO HOME (Pre-Dashboard / Empty State / Onboarding)
  // Strictly applies ONLY when the backend confirms user belongs to ZERO homes
  // ===========================================================================
  if (userHomes.length === 0 && !activeHomeId) {
    return (
      <div style={{ maxWidth: '840px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 'var(--space-8)', padding: 'var(--space-6) var(--space-4)' }}>
        {error && (
          <div style={{ padding: '10px 14px', backgroundColor: 'var(--status-overdue-bg)', color: 'var(--status-overdue)', borderRadius: 'var(--radius-md)', fontSize: '13px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span>{error}</span>
            <Button size="sm" variant="secondary" onClick={loadDashboard}>
              <RefreshCw size={14} /> <span>Retry</span>
            </Button>
          </div>
        )}

        <Card style={{ padding: 'var(--space-8)', textAlign: 'center', backgroundColor: 'var(--color-surface-card)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-card)' }}>
          <div style={{ width: '56px', height: '56px', borderRadius: '50%', backgroundColor: 'var(--color-primary-100)', color: 'var(--color-primary-900)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto var(--space-4)' }}>
            <Home size={28} />
          </div>

          <h1 style={{ fontSize: '24px', fontWeight: 700, color: 'var(--color-primary-900)', marginBottom: 'var(--space-2)', letterSpacing: '-0.02em' }}>
            Welcome to Ozhzo Verse
          </h1>

          <p style={{ fontSize: '15px', color: 'var(--color-text-secondary)', maxWidth: '520px', margin: '0 auto var(--space-6)', lineHeight: 1.5 }}>
            You haven't created or joined a Home yet. Get started by setting up a dedicated workspace for your household or join with an invitation code.
          </p>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', justifyContent: 'center', alignItems: 'center' }}>
            <Button
              variant="primary"
              size="lg"
              onClick={() => setIsCreateHomeOpen(true)}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
            >
              <Plus size={18} />
              <span>Create Your Home</span>
            </Button>

            <Button
              variant="secondary"
              size="lg"
              onClick={() => setIsJoinHomeOpen(true)}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
            >
              <Users size={18} />
              <span>Join a Home</span>
            </Button>
          </div>
        </Card>

        {/* Feature Overview Grid */}
        <div>
          <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 'var(--space-3)', textAlign: 'center' }}>
            Everything you can organize in your Home
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 'var(--space-4)' }}>
            <Card variant="subtle" style={{ padding: 'var(--space-4)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: 'var(--space-2)' }}>
                <Package size={20} color="var(--color-primary-900)" />
                <h3 style={{ fontSize: '15px', fontWeight: 600 }}>Home Memory</h3>
              </div>
              <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>
                Keep track of physical assets, tools, pantry supply levels, and exact item locations.
              </p>
            </Card>

            <Card variant="subtle" style={{ padding: 'var(--space-4)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: 'var(--space-2)' }}>
                <CheckCircle2 size={20} color="var(--color-accent-warm)" />
                <h3 style={{ fontSize: '15px', fontWeight: 600 }}>Tasks & Chores</h3>
              </div>
              <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>
                Coordinate recurring chore routines, household maintenance schedules, and assignments.
              </p>
            </Card>

            <Card variant="subtle" style={{ padding: 'var(--space-4)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: 'var(--space-2)' }}>
                <ShoppingCart size={20} color="var(--status-in-stock)" />
                <h3 style={{ fontSize: '15px', fontWeight: 600 }}>Purchase Lists</h3>
              </div>
              <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>
                Collaborative grocery and domestic shopping lists updated in real-time by family members.
              </p>
            </Card>

            <Card variant="subtle" style={{ padding: 'var(--space-4)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: 'var(--space-2)' }}>
                <Receipt size={20} color="var(--status-low-stock)" />
                <h3 style={{ fontSize: '15px', fontWeight: 600 }}>Bills & Reminders</h3>
              </div>
              <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', lineHeight: 1.4 }}>
                Track utility bills, household subscriptions, due dates, and payment history.
              </p>
            </Card>
          </div>
        </div>

        {renderCreateHomeModal()}
        {renderJoinHomeModal()}
      </div>
    );
  }

  // Error State for user WITH homes (e.g. temporary API failure)
  if (error && !data) {
    return (
      <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div
          style={{
            padding: '16px 20px',
            backgroundColor: 'var(--status-overdue-bg, #fef2f2)',
            border: '1px solid #fecaca',
            borderRadius: 'var(--radius-lg, 16px)',
            color: 'var(--status-overdue, #ef4444)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '16px'
          }}
        >
          <div>
            <div style={{ fontWeight: 700, fontSize: '15px' }}>Unable to load household dashboard</div>
            <div style={{ fontSize: '13px', color: '#991b1b', marginTop: '4px' }}>{error}</div>
          </div>
          <Button variant="secondary" onClick={loadDashboard}>
            <RefreshCw size={14} /> <span>Retry</span>
          </Button>
        </div>
        {renderCreateHomeModal()}
        {renderJoinHomeModal()}
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', padding: 'var(--space-4)' }}>
        <div style={{ height: '60px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: 'var(--radius-md)', animation: 'pulse 1.5s infinite' }} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 'var(--space-4)' }}>
          {[1, 2, 3, 4].map((i) => (
            <div key={i} style={{ height: '90px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: 'var(--radius-lg)' }} />
          ))}
        </div>
        {renderCreateHomeModal()}
        {renderJoinHomeModal()}
      </div>
    );
  }

  // ===========================================================================
  // STATE B — FULL APPROVED HOME DASHBOARD
  // ===========================================================================
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      {/* Dynamic Time-Contextual Greeting Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-3)' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-primary-900)', letterSpacing: '-0.02em' }}>
            {data?.greeting?.greeting || 'Welcome'}, {data?.greeting?.user_display_name || userProfile?.display_name || 'Home'}
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>{data?.greeting?.date_formatted || 'Today'}</span>
            <span>•</span>
            <span style={{ fontWeight: 600, color: 'var(--color-primary-900)' }}>{data?.summary?.home_name || 'Home'}</span>
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <Button onClick={loadDashboard} variant="secondary" size="sm">
            <RefreshCw size={14} />
            <span>Refresh</span>
          </Button>
        </div>
      </div>

      {/* 1. Attention Banner (If Overdue Chores, Low Stock, or Due Bills exist) */}
      {(data.summary.low_stock_count > 0 || data.summary.unpaid_bills_count > 0) && (
        <Card style={{ backgroundColor: 'var(--status-low-stock-bg)', borderColor: 'var(--status-low-stock)', padding: '14px 18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <AlertTriangle size={20} color="var(--status-low-stock)" />
              <div>
                <strong style={{ fontSize: '14px', color: 'var(--color-primary-900)' }}>Household Attention Required</strong>
                <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
                  {data.summary.low_stock_count > 0 && `${data.summary.low_stock_count} item(s) low on stock. `}
                  {data.summary.unpaid_bills_count > 0 && `${data.summary.unpaid_bills_count} bill(s) pending payment.`}
                </div>
              </div>
            </div>
            <Link href="/today" style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-primary-900)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              <span>View Action Items</span>
              <ArrowRight size={14} />
            </Link>
          </div>
        </Card>
      )}

      {/* 2. Summary KPI Cards Grid (Home Status) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 'var(--space-3)' }}>
        <Link href="/tasks">
          <Card variant="subtle" style={{ padding: '14px 16px', cursor: 'pointer' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>Chores Due</span>
              <CheckCircle2 size={18} color="var(--color-accent-warm)" />
            </div>
            <div style={{ fontSize: '24px', fontWeight: 700, marginTop: '6px', color: 'var(--color-primary-900)' }}>
              {data.summary.active_tasks_count}
            </div>
          </Card>
        </Link>

        <Link href="/inventory">
          <Card variant="subtle" style={{ padding: '14px 16px', cursor: 'pointer' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>Low Stock</span>
              <AlertTriangle size={18} color="var(--status-low-stock)" />
            </div>
            <div style={{ fontSize: '24px', fontWeight: 700, marginTop: '6px', color: 'var(--color-primary-900)' }}>
              {data.summary.low_stock_count}
            </div>
          </Card>
        </Link>

        <Link href="/bills">
          <Card variant="subtle" style={{ padding: '14px 16px', cursor: 'pointer' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>Unpaid Bills</span>
              <Receipt size={18} color="var(--color-primary-900)" />
            </div>
            <div style={{ fontSize: '24px', fontWeight: 700, marginTop: '6px', color: 'var(--color-primary-900)' }}>
              {data.role !== 'CHILD' && data.role !== 'GUEST' ? `$${Number(data.summary.unpaid_bills_sum || 0).toFixed(2)}` : '—'}
            </div>
          </Card>
        </Link>

        <Link href="/settings">
          <Card variant="subtle" style={{ padding: '14px 16px', cursor: 'pointer' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>Family</span>
              <Users size={18} color="var(--color-text-secondary)" />
            </div>
            <div style={{ fontSize: '24px', fontWeight: 700, marginTop: '6px', color: 'var(--color-primary-900)' }}>
              {data.summary.members_count}
            </div>
          </Card>
        </Link>
      </div>

      {/* 3. Main Multi-Column Pulse Grid (Tasks, Low Stock, Bills, Shopping, Activity) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--space-4)' }}>
        
        {/* Chores & Tasks Module */}
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)', paddingBottom: 'var(--space-2)', borderBottom: '1px solid var(--color-border-subtle)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <CheckCircle2 size={18} color="var(--color-accent-warm)" />
              <h2 style={{ fontSize: '15px', fontWeight: 600 }}>Chores & Tasks</h2>
            </div>
            <Badge variant="neutral">{data.pending_tasks.length} Pending</Badge>
          </div>

          {data.pending_tasks.length === 0 ? (
            <div style={{ padding: 'var(--space-6) var(--space-4)', textAlign: 'center', color: 'var(--color-text-secondary)' }}>
              <Sparkles size={24} color="var(--status-in-stock)" style={{ marginBottom: '6px' }} />
              <p style={{ fontSize: '13px', fontWeight: 500 }}>All caught up! No chores due.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {data.pending_tasks.map((task) => (
                <div
                  key={task.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '10px 12px',
                    backgroundColor: 'var(--color-surface-subtle)',
                    borderRadius: 'var(--radius-md)'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{ width: '16px', height: '16px', borderRadius: '4px', border: '1.5px solid var(--color-border-strong)', backgroundColor: 'var(--color-surface-card)' }} />
                    <div>
                      <div style={{ fontSize: '13px', fontWeight: 600 }}>{task.title}</div>
                      <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>
                        {task.due_date ? new Date(task.due_date).toLocaleDateString() : 'No due date'}
                      </div>
                    </div>
                  </div>
                  <Badge variant={task.priority === 'HIGH' || task.priority === 'URGENT' ? 'overdue' : 'neutral'}>
                    {task.priority}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Low Stock & Pantry Alerts */}
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)', paddingBottom: 'var(--space-2)', borderBottom: '1px solid var(--color-border-subtle)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertTriangle size={18} color="var(--status-low-stock)" />
              <h2 style={{ fontSize: '15px', fontWeight: 600 }}>Low Stock & Restock</h2>
            </div>
            <Badge variant={data.low_stock_inventory.length > 0 ? 'low-stock' : 'in-stock'}>
              {data.low_stock_inventory.length > 0 ? 'Action Needed' : 'Stocked'}
            </Badge>
          </div>

          {data.low_stock_inventory.length === 0 ? (
            <div style={{ padding: 'var(--space-6) var(--space-4)', textAlign: 'center', color: 'var(--color-text-secondary)' }}>
              <Check size={24} color="var(--status-in-stock)" style={{ marginBottom: '6px' }} />
              <p style={{ fontSize: '13px', fontWeight: 500 }}>Household pantry is fully stocked.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {data.low_stock_inventory.map((item) => (
                <div
                  key={item.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '10px 12px',
                    backgroundColor: 'var(--color-surface-subtle)',
                    borderRadius: 'var(--radius-md)'
                  }}
                >
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 600 }}>{item.name}</div>
                    <div style={{ fontSize: '11px', color: 'var(--status-low-stock)', fontWeight: 500 }}>
                      Remaining: {item.quantity} {item.unit}
                    </div>
                  </div>
                  <Link href="/shopping">
                    <Button size="sm" variant="secondary">
                      + Add to List
                    </Button>
                  </Link>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Upcoming Bills (Role-Protected) */}
        {data.role !== 'CHILD' && data.role !== 'GUEST' && (
          <Card>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)', paddingBottom: 'var(--space-2)', borderBottom: '1px solid var(--color-border-subtle)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Receipt size={18} color="var(--color-primary-900)" />
                <h2 style={{ fontSize: '15px', fontWeight: 600 }}>Upcoming Bills</h2>
              </div>
              <Badge variant="completed">Upcoming</Badge>
            </div>

            {data.upcoming_bills.length === 0 ? (
              <div style={{ padding: 'var(--space-6) var(--space-4)', textAlign: 'center', color: 'var(--color-text-secondary)' }}>
                <Receipt size={24} color="var(--status-in-stock)" style={{ marginBottom: '6px' }} />
                <p style={{ fontSize: '13px', fontWeight: 500 }}>No bills due in the next 14 days.</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {data.upcoming_bills.map((bill) => (
                  <div
                    key={bill.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '10px 12px',
                      backgroundColor: 'var(--color-surface-subtle)',
                      borderRadius: 'var(--radius-md)'
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '13px', fontWeight: 600 }}>{bill.title}</div>
                      <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>
                        Due {new Date(bill.due_date).toLocaleDateString()}
                      </div>
                    </div>
                    <span style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                      ${Number(bill.amount).toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </Card>
        )}

        {/* Shopping List Quick View */}
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)', paddingBottom: 'var(--space-2)', borderBottom: '1px solid var(--color-border-subtle)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShoppingCart size={18} color="var(--color-primary-900)" />
              <h2 style={{ fontSize: '15px', fontWeight: 600 }}>Shopping List</h2>
            </div>
            <Badge variant="neutral">{data.shopping_items.length} Items</Badge>
          </div>

          {data.shopping_items.length === 0 ? (
            <div style={{ padding: 'var(--space-6) var(--space-4)', textAlign: 'center', color: 'var(--color-text-secondary)' }}>
              <ShoppingCart size={24} color="var(--color-text-tertiary)" style={{ marginBottom: '6px' }} />
              <p style={{ fontSize: '13px', fontWeight: 500 }}>Shopping list is empty.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {data.shopping_items.map((item) => (
                <div
                  key={item.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    backgroundColor: 'var(--color-surface-subtle)',
                    borderRadius: 'var(--radius-md)'
                  }}
                >
                  <span style={{ fontSize: '13px', fontWeight: 500 }}>{item.name}</span>
                  <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>{item.quantity} {item.unit}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Recent Household Notifications / Activity */}
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)', paddingBottom: 'var(--space-2)', borderBottom: '1px solid var(--color-border-subtle)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Bell size={18} color="var(--color-primary-900)" />
              <h2 style={{ fontSize: '15px', fontWeight: 600 }}>Recent Activity</h2>
            </div>
            <Badge variant="neutral">{data.notifications.length} Alerts</Badge>
          </div>

          {data.notifications.length === 0 ? (
            <div style={{ padding: 'var(--space-6) var(--space-4)', textAlign: 'center', color: 'var(--color-text-secondary)' }}>
              <Bell size={24} color="var(--color-text-tertiary)" style={{ marginBottom: '6px' }} />
              <p style={{ fontSize: '13px', fontWeight: 500 }}>No recent household activity alerts.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {data.notifications.map((notif) => (
                <div
                  key={notif.id}
                  style={{
                    padding: '10px 12px',
                    backgroundColor: 'var(--color-surface-subtle)',
                    borderRadius: 'var(--radius-md)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '2px'
                  }}
                >
                  <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-primary-900)' }}>{notif.title}</div>
                  <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>{notif.body}</div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {renderCreateHomeModal()}
        {renderJoinHomeModal()}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense
      fallback={
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
          <RefreshCw size={28} className="animate-spin" style={{ color: 'var(--color-primary-900)' }} />
        </div>
      }
    >
      <DashboardPageContent />
    </Suspense>
  );
}
