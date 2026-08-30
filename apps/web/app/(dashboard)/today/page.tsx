'use client';

import React, { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui/Card';
import {
  Sparkles,
  AlertTriangle,
  Calendar as CalendarIcon,
  CheckCircle2,
  Receipt,
  ShoppingCart,
  Package,
  Plus,
  Users,
  Clock,
  ShieldAlert,
  Bell,
  RefreshCw
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

interface TodayAttentionItem {
  id: string;
  source_type: 'TASK' | 'BILL' | 'EVENT' | 'INVENTORY' | 'PURCHASE' | 'ASSET' | 'NOTIFICATION' | 'MEMBER';
  source_id: string;
  title: string;
  subtitle?: string | null;
  priority: 'CRITICAL' | 'HIGH' | 'NORMAL' | 'LOW';
  badge_text?: string | null;
  due_date?: string | null;
  due_time?: string | null;
  navigation_target: string;
  amount?: number | null;
  currency?: string | null;
  status?: string | null;
  category_name?: string | null;
  assignee_id?: string | null;
  assignee_name?: string | null;
  is_assigned_to_me?: boolean;
  location?: string | null;
  meta_info?: Record<string, any> | null;
}

interface TodayTasksSection {
  overdue: TodayAttentionItem[];
  due_today: TodayAttentionItem[];
  my_tasks: TodayAttentionItem[];
  family_tasks: TodayAttentionItem[];
  upcoming: TodayAttentionItem[];
  completed_today_count: number;
}

interface TodayBillsSection {
  overdue: TodayAttentionItem[];
  due_today: TodayAttentionItem[];
  upcoming: TodayAttentionItem[];
  total_due_today_amount: number;
  currency: string;
}

interface TodayCalendarSection {
  today_events: TodayAttentionItem[];
  upcoming_events: TodayAttentionItem[];
}

interface TodayInventorySection {
  out_of_stock: TodayAttentionItem[];
  low_stock: TodayAttentionItem[];
  expiring_soon: TodayAttentionItem[];
}

interface TodayShoppingSection {
  urgent_items: TodayAttentionItem[];
  pending_items: TodayAttentionItem[];
  total_pending_count: number;
}

interface TodayFamilySection {
  active_members_count: number;
  pending_invitations_count: number;
  member_workloads: Array<{
    member_id: string;
    user_id: string;
    display_name: string;
    role: string;
    open_tasks_count: number;
    is_current_user: boolean;
  }>;
}

interface TodayNotificationsSection {
  unread_count: number;
  important_alerts: TodayAttentionItem[];
}

interface TodayResponse {
  date: string;
  timezone: string;
  home_id?: string | null;
  home_name?: string | null;
  summary: {
    total_items: number;
    critical_count: number;
    high_count: number;
    normal_count: number;
    low_count: number;
    events_count: number;
    tasks_count: number;
    bills_count: number;
    purchase_urgent_count: number;
    inventory_alerts_count: number;
  };
  needs_attention?: TodayAttentionItem[];
  timeline?: TodayAttentionItem[];
  tasks?: TodayTasksSection;
  bills?: TodayBillsSection;
  calendar?: TodayCalendarSection;
  inventory?: TodayInventorySection;
  shopping?: TodayShoppingSection;
  family?: TodayFamilySection;
  notifications?: TodayNotificationsSection;
}

export default function TodayPage() {
  const [data, setData] = useState<TodayResponse | null>(null);
  const [userName, setUserName] = useState<string>('Household Member');
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [activeTab, setActiveTab] = useState<'all' | 'critical' | 'high' | 'normal'>('all');

  const fetchTodayData = useCallback(async () => {
    setIsLoading(true);
    setHasError(false);
    try {
      const activeHomeId = apiClient.getActiveHomeId() || (await apiClient.getValidActiveHome());
      if (!activeHomeId) {
        setIsLoading(false);
        return;
      }

      // Fetch user profile from cache or API
      const cachedUser = apiClient.getUser();
      if (cachedUser?.display_name) {
        setUserName(cachedUser.display_name);
      } else {
        apiClient.get<any>('/users/me').then((profile) => {
          if (profile?.display_name) setUserName(profile.display_name);
        }).catch(() => {});
      }

      const res = await apiClient.get<TodayResponse>(`/homes/${activeHomeId}/today`);
      setData(res);
    } catch (err) {
      console.error('Failed to load today data:', err);
      setHasError(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTodayData();

    const handleHomeChange = () => {
      fetchTodayData();
    };

    window.addEventListener('home-changed', handleHomeChange);
    return () => {
      window.removeEventListener('home-changed', handleHomeChange);
    };
  }, [fetchTodayData]);

  // Greeting helper
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  };

  const getSourceIcon = (type: string) => {
    switch (type) {
      case 'EVENT':
        return <CalendarIcon size={18} color="var(--color-primary-900)" />;
      case 'TASK':
        return <CheckCircle2 size={18} color="var(--status-in-stock)" />;
      case 'BILL':
        return <Receipt size={18} color="var(--status-overdue)" />;
      case 'PURCHASE':
        return <ShoppingCart size={18} color="var(--status-low-stock)" />;
      case 'INVENTORY':
      case 'ASSET':
        return <Package size={18} color="#8b5cf6" />;
      case 'NOTIFICATION':
        return <Bell size={18} color="#0284c7" />;
      case 'MEMBER':
        return <Users size={18} color="#0d9488" />;
      default:
        return <Sparkles size={18} color="var(--color-text-secondary)" />;
    }
  };

  const getPriorityBadgeStyle = (priority: string) => {
    switch (priority) {
      case 'CRITICAL':
        return { background: '#fef2f2', color: '#b91c1c', border: '1px solid #fecaca' };
      case 'HIGH':
        return { background: '#fffbeb', color: '#b45309', border: '1px solid #fde68a' };
      case 'NORMAL':
        return { background: '#f0f9ff', color: '#0369a1', border: '1px solid #bae6fd' };
      default:
        return { background: 'var(--color-surface-subtle)', color: 'var(--color-text-secondary)', border: '1px solid var(--color-border-subtle)' };
    }
  };

  const summary = data?.summary || {
    total_items: 0,
    critical_count: 0,
    high_count: 0,
    normal_count: 0,
    low_count: 0,
    events_count: 0,
    tasks_count: 0,
    bills_count: 0,
    purchase_urgent_count: 0,
    inventory_alerts_count: 0
  };

  const allAttentionItems = data?.needs_attention || [];
  const filteredAttention = activeTab === 'all'
    ? allAttentionItems
    : allAttentionItems.filter((i) => i.priority.toLowerCase() === activeTab);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '1000px', margin: '0 auto' }}>
      {/* Personalized Header Briefing */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {data?.home_name ? `${data.home_name} • Household Intelligence` : 'Household Intelligence'}
            </span>
          </div>
          <h1 style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--color-primary-900)', letterSpacing: '-0.02em', margin: 0 }}>
            {getGreeting()}, {userName.split(' ')[0]}!
          </h1>
          <p style={{ fontSize: '15px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
            Here is your definitive briefing on what needs your attention in your home today.
          </p>
        </div>

        {/* Quick Priority Pill Badges */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <button
            onClick={() => setActiveTab('all')}
            style={{
              padding: '6px 14px',
              borderRadius: '999px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              border: 'none',
              background: activeTab === 'all' ? 'var(--color-primary-900)' : 'var(--color-surface-subtle)',
              color: activeTab === 'all' ? '#fff' : 'var(--color-text-primary)',
              transition: 'all 0.15s ease'
            }}
          >
            All Items ({summary.total_items})
          </button>

          {summary.critical_count > 0 && (
            <button
              onClick={() => setActiveTab('critical')}
              style={{
                padding: '6px 14px',
                borderRadius: '999px',
                fontSize: '13px',
                fontWeight: 700,
                cursor: 'pointer',
                border: '1px solid #fecaca',
                background: activeTab === 'critical' ? '#dc2626' : '#fef2f2',
                color: activeTab === 'critical' ? '#fff' : '#b91c1c',
                transition: 'all 0.15s ease'
              }}
            >
              🚨 Critical ({summary.critical_count})
            </button>
          )}

          {summary.high_count > 0 && (
            <button
              onClick={() => setActiveTab('high')}
              style={{
                padding: '6px 14px',
                borderRadius: '999px',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
                border: '1px solid #fde68a',
                background: activeTab === 'high' ? '#d97706' : '#fffbeb',
                color: activeTab === 'high' ? '#fff' : '#b45309',
                transition: 'all 0.15s ease'
              }}
            >
              ⚠️ High Priority ({summary.high_count})
            </button>
          )}
        </div>
      </div>

      {/* Quick Action Shortcuts Bar */}
      <Card style={{ padding: '12px 18px', background: 'var(--color-surface)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>
          <Sparkles size={16} color="var(--color-primary-900)" />
          <span>Quick Actions:</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <Link
            href="/tasks"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: 'var(--radius-md)',
              fontSize: '13px',
              fontWeight: 600,
              background: 'var(--color-surface-subtle)',
              color: 'var(--color-text-primary)',
              textDecoration: 'none',
              border: '1px solid var(--color-border-subtle)'
            }}
          >
            <Plus size={14} /> New Task
          </Link>
          <Link
            href="/bills"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: 'var(--radius-md)',
              fontSize: '13px',
              fontWeight: 600,
              background: 'var(--color-surface-subtle)',
              color: 'var(--color-text-primary)',
              textDecoration: 'none',
              border: '1px solid var(--color-border-subtle)'
            }}
          >
            <Plus size={14} /> Record Bill
          </Link>
          <Link
            href="/shopping"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: 'var(--radius-md)',
              fontSize: '13px',
              fontWeight: 600,
              background: 'var(--color-surface-subtle)',
              color: 'var(--color-text-primary)',
              textDecoration: 'none',
              border: '1px solid var(--color-border-subtle)'
            }}
          >
            <Plus size={14} /> Add Item
          </Link>
          <Link
            href="/calendar"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: 'var(--radius-md)',
              fontSize: '13px',
              fontWeight: 600,
              background: 'var(--color-surface-subtle)',
              color: 'var(--color-text-primary)',
              textDecoration: 'none',
              border: '1px solid var(--color-border-subtle)'
            }}
          >
            <Plus size={14} /> Schedule Event
          </Link>
        </div>
      </Card>

      {/* Loading Skeleton */}
      {isLoading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {[1, 2, 3].map((i) => (
            <div key={i} style={{ height: '80px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: 'var(--radius-lg)', animation: 'pulse 1.5s infinite' }} />
          ))}
        </div>
      )}

      {/* Error Fallback */}
      {hasError && !isLoading && (
        <Card style={{ padding: 'var(--space-8)', textAlign: 'center', border: '1px solid #fecaca', background: '#fef2f2' }}>
          <AlertTriangle size={36} color="#dc2626" style={{ margin: '0 auto 10px' }} />
          <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#991b1b' }}>
            Unable to load Today Intelligence
          </h3>
          <p style={{ fontSize: '13px', color: '#7f1d1d', marginTop: '4px', maxWidth: '400px', margin: '4px auto 16px' }}>
            There was an issue connecting to the household intelligence engine. Please try again.
          </p>
          <button
            onClick={fetchTodayData}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              borderRadius: 'var(--radius-md)',
              background: '#dc2626',
              color: '#fff',
              fontWeight: 600,
              fontSize: '13px',
              border: 'none',
              cursor: 'pointer'
            }}
          >
            <RefreshCw size={14} /> Retry
          </button>
        </Card>
      )}

      {!isLoading && !hasError && (
        <>
          {/* 1. NEEDS ATTENTION (TOP URGENT ITEMS) */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: '14px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--status-overdue)', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <ShieldAlert size={16} /> Needs Attention ({filteredAttention.length})
              </div>
            </div>

            {filteredAttention.length === 0 ? (
              <Card style={{ padding: '24px', textAlign: 'center', background: 'var(--color-surface)' }}>
                <Sparkles size={32} color="var(--status-in-stock)" style={{ margin: '0 auto 8px' }} />
                <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                  You are all caught up!
                </div>
                <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
                  No urgent or overdue tasks, bills, or pantry shortages require immediate action.
                </p>
              </Card>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '12px' }}>
                {filteredAttention.map((item) => {
                  const isCritical = item.priority === 'CRITICAL';
                  const borderCol = isCritical ? '#dc2626' : '#d97706';
                  return (
                    <Card
                      key={item.id}
                      style={{
                        padding: '16px',
                        borderLeft: `4px solid ${borderCol}`,
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                        gap: '12px'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '10px' }}>
                        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                          <div style={{ marginTop: '2px' }}>{getSourceIcon(item.source_type)}</div>
                          <div>
                            <div style={{ fontWeight: 700, fontSize: '14px', color: 'var(--color-text-primary)' }}>
                              {item.title}
                            </div>
                            {item.subtitle && (
                              <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
                                {item.subtitle}
                              </div>
                            )}
                          </div>
                        </div>

                        {item.badge_text && (
                          <span style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 700, whiteSpace: 'nowrap', ...getPriorityBadgeStyle(item.priority) }}>
                            {item.badge_text}
                          </span>
                        )}
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid var(--color-border-subtle)', paddingTop: '8px' }}>
                        <Link
                          href={item.navigation_target || '/dashboard'}
                          style={{
                            fontSize: '12px',
                            fontWeight: 700,
                            color: 'var(--color-primary-900)',
                            textDecoration: 'none',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px'
                          }}
                        >
                          Resolve ➔
                        </Link>
                      </div>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>

          {/* 2. TODAY'S AGENDA (TASKS, BILLS, EVENTS DUE TODAY) */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ fontSize: '14px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-primary-900)', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Clock size={16} /> Today's Scheduled Agenda
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
              {/* Tasks Due Today */}
              <Card style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-primary-900)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <CheckCircle2 size={16} color="var(--status-in-stock)" />
                    Tasks Due Today ({(data?.tasks?.due_today || []).length})
                  </div>
                  <Link href="/tasks" style={{ fontSize: '12px', color: 'var(--color-text-secondary)', textDecoration: 'none' }}>
                    View all ➔
                  </Link>
                </div>

                {(data?.tasks?.due_today || []).length === 0 ? (
                  <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)', padding: '12px 0' }}>
                    ✓ No tasks due today.
                  </div>
                ) : (
                  (data?.tasks?.due_today || []).map((t) => (
                    <div key={t.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--color-border-subtle)' }}>
                      <div>
                        <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text-primary)' }}>{t.title}</div>
                        {t.category_name && <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>{t.category_name}</div>}
                      </div>
                      <Link href={t.navigation_target} style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-primary-900)', textDecoration: 'none' }}>
                        Open
                      </Link>
                    </div>
                  ))
                )}
              </Card>

              {/* Bills Due Today */}
              <Card style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-primary-900)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Receipt size={16} color="var(--status-overdue)" />
                    Bills Due Today ({(data?.bills?.due_today || []).length})
                  </div>
                  <Link href="/bills" style={{ fontSize: '12px', color: 'var(--color-text-secondary)', textDecoration: 'none' }}>
                    View all ➔
                  </Link>
                </div>

                {(data?.bills?.due_today || []).length === 0 ? (
                  <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)', padding: '12px 0' }}>
                    ✓ No bills due today.
                  </div>
                ) : (
                  (data?.bills?.due_today || []).map((b) => (
                    <div key={b.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--color-border-subtle)' }}>
                      <div>
                        <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text-primary)' }}>{b.title}</div>
                        <div style={{ fontSize: '11px', color: 'var(--status-overdue)', fontWeight: 600 }}>{b.subtitle}</div>
                      </div>
                      <Link href={b.navigation_target} style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-primary-900)', textDecoration: 'none' }}>
                        Pay
                      </Link>
                    </div>
                  ))
                )}
              </Card>

              {/* Calendar Events Today */}
              <Card style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-primary-900)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <CalendarIcon size={16} color="var(--color-primary-900)" />
                    Events Today ({(data?.calendar?.today_events || []).length})
                  </div>
                  <Link href="/calendar" style={{ fontSize: '12px', color: 'var(--color-text-secondary)', textDecoration: 'none' }}>
                    View all ➔
                  </Link>
                </div>

                {(data?.calendar?.today_events || []).length === 0 ? (
                  <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)', padding: '12px 0' }}>
                    ✓ No calendar events scheduled for today.
                  </div>
                ) : (
                  (data?.calendar?.today_events || []).map((e) => (
                    <div key={e.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--color-border-subtle)' }}>
                      <div>
                        <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text-primary)' }}>{e.title}</div>
                        {e.location && <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>📍 {e.location}</div>}
                      </div>
                      <Link href={e.navigation_target} style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-primary-900)', textDecoration: 'none' }}>
                        Details
                      </Link>
                    </div>
                  ))
                )}
              </Card>
            </div>
          </div>

          {/* 3. PANTRY & SHOPPING INTELLIGENCE */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ fontSize: '14px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-primary-900)', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Package size={16} /> Pantry & Shopping Intelligence
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '14px' }}>
              {/* Inventory Stock Status */}
              <Card style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                    Inventory Warnings ({((data?.inventory?.out_of_stock || []).length + (data?.inventory?.low_stock || []).length)})
                  </div>
                  <Link href="/inventory" style={{ fontSize: '12px', color: 'var(--color-text-secondary)', textDecoration: 'none' }}>
                    Open Pantry ➔
                  </Link>
                </div>

                {(data?.inventory?.out_of_stock || []).length === 0 && (data?.inventory?.low_stock || []).length === 0 ? (
                  <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)', padding: '10px 0' }}>
                    ✓ Inventory looks good. No items are out of stock or low.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {(data?.inventory?.out_of_stock || []).map((i) => (
                      <div key={i.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 8px', background: '#fef2f2', borderRadius: 'var(--radius-sm)' }}>
                        <span style={{ fontSize: '13px', fontWeight: 600, color: '#991b1b' }}>🚨 {i.title}</span>
                        <Link href={i.navigation_target} style={{ fontSize: '11px', fontWeight: 700, color: '#b91c1c', textDecoration: 'none' }}>Restock</Link>
                      </div>
                    ))}
                    {(data?.inventory?.low_stock || []).map((i) => (
                      <div key={i.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 8px', background: '#fffbeb', borderRadius: 'var(--radius-sm)' }}>
                        <span style={{ fontSize: '13px', fontWeight: 600, color: '#92400e' }}>⚠️ {i.title}</span>
                        <Link href={i.navigation_target} style={{ fontSize: '11px', fontWeight: 700, color: '#b45309', textDecoration: 'none' }}>Add to List</Link>
                      </div>
                    ))}
                  </div>
                )}
              </Card>

              {/* Shopping List Items */}
              <Card style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                    Pending Shopping ({(data?.shopping?.pending_items || []).length})
                  </div>
                  <Link href="/shopping" style={{ fontSize: '12px', color: 'var(--color-text-secondary)', textDecoration: 'none' }}>
                    Shopping List ➔
                  </Link>
                </div>

                {(data?.shopping?.pending_items || []).length === 0 ? (
                  <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)', padding: '10px 0' }}>
                    ✓ Your shopping list is clear.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {(data?.shopping?.pending_items || []).slice(0, 5).map((p) => (
                      <div key={p.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: '1px solid var(--color-border-subtle)' }}>
                        <span style={{ fontSize: '13px', color: 'var(--color-text-primary)' }}>🛒 {p.title}</span>
                        {p.subtitle && <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>{p.subtitle}</span>}
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </div>
          </div>

          {/* 4. FAMILY WORKLOAD & MEMBER ACTIVITY */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ fontSize: '14px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-primary-900)', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Users size={16} /> Household Members & Workload
            </div>

            <Card style={{ padding: '18px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
                {(data?.family?.member_workloads || []).map((m) => (
                  <div
                    key={m.member_id}
                    style={{
                      padding: '12px 14px',
                      borderRadius: 'var(--radius-md)',
                      background: m.is_current_user ? 'var(--color-surface-subtle)' : 'var(--color-surface)',
                      border: m.is_current_user ? '1px solid var(--color-primary-900)' : '1px solid var(--color-border-subtle)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between'
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                        {m.display_name} {m.is_current_user && '(You)'}
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', textTransform: 'capitalize' }}>
                        {m.role.toLowerCase().replace('_', ' ')}
                      </div>
                    </div>
                    <span style={{ padding: '2px 8px', borderRadius: '999px', fontSize: '12px', fontWeight: 700, background: 'var(--color-surface)', border: '1px solid var(--color-border-subtle)', color: 'var(--color-primary-900)' }}>
                      {m.open_tasks_count} tasks
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

