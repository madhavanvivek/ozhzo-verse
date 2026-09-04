'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import {
  Bell,
  CheckCircle2,
  AlertTriangle,
  Receipt,
  Calendar,
  UserPlus,
  Settings,
  Sparkles,
  Check,
  ShieldAlert,
  ArrowRight,
  Home,
  CheckCheck,
  Eye,
  XCircle,
  Clock,
  Gift
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

interface NotificationItem {
  id: string;
  home_id?: string | null;
  home_name?: string | null;
  user_id: string;
  title: string;
  body: string;
  type: string;
  priority: 'CRITICAL' | 'HIGH' | 'NORMAL' | 'LOW' | 'PRIORITY';
  requires_action: boolean;
  action_status: 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED' | 'DISMISSED';
  action_type?: string | null;
  action_url?: string | null;
  action_label?: string | null;
  extra_metadata?: Record<string, any> | null;
  is_read: boolean;
  read_at?: string | null;
  resolved_at?: string | null;
  dismissed_at?: string | null;
  created_at: string;
}

interface PaginatedNotifications {
  items: NotificationItem[];
  unread_count: number;
  priority_unread_count?: number;
  action_required_count?: number;
  total: number;
}

export default function NotificationsPage() {
  const [activeTab, setActiveTab] = useState<'ACTION_REQUIRED' | 'ALL' | 'RESOLVED'>('ACTION_REQUIRED');
  const [priorityFilter, setPriorityFilter] = useState<string>('ALL');
  const [showSettings, setShowSettings] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionInProgressId, setActionInProgressId] = useState<string | null>(null);
  const [feedbackToast, setFeedbackToast] = useState<string | null>(null);

  const fetchNotifications = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<PaginatedNotifications>('/notifications?page_size=50');
      setNotifications(data?.items || []);
    } catch (err: any) {
      console.error('Failed to fetch notifications:', err);
      setError(err?.message || 'Unable to load notifications.');
      setNotifications([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  const showToast = (msg: string) => {
    setFeedbackToast(msg);
    setTimeout(() => setFeedbackToast(null), 3000);
  };

  const handleMarkRead = async (id: string) => {
    setActionInProgressId(id);
    try {
      await apiClient.patch(`/notifications/${id}/read`, {});
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true, read_at: new Date().toISOString() } : n))
      );
      showToast('Marked as read');
    } catch (err: any) {
      alert(err?.message || 'Failed to mark notification read.');
    } finally {
      setActionInProgressId(null);
    }
  };

  const handleAcknowledge = async (id: string) => {
    setActionInProgressId(id);
    try {
      await apiClient.patch(`/notifications/${id}/acknowledge`, {});
      setNotifications((prev) =>
        prev.map((n) =>
          n.id === id
            ? { ...n, action_status: 'ACKNOWLEDGED', is_read: true, read_at: new Date().toISOString() }
            : n
        )
      );
      showToast('Notification acknowledged');
    } catch (err: any) {
      alert(err?.message || 'Failed to acknowledge notification.');
    } finally {
      setActionInProgressId(null);
    }
  };

  const handleResolve = async (id: string) => {
    setActionInProgressId(id);
    try {
      await apiClient.patch(`/notifications/${id}/resolve`, {});
      setNotifications((prev) =>
        prev.map((n) =>
          n.id === id
            ? {
                ...n,
                action_status: 'RESOLVED',
                resolved_at: new Date().toISOString(),
                is_read: true
              }
            : n
        )
      );
      showToast('Marked as resolved');
    } catch (err: any) {
      alert(err?.message || 'Failed to resolve notification.');
    } finally {
      setActionInProgressId(null);
    }
  };

  const handleDismiss = async (id: string) => {
    setActionInProgressId(id);
    try {
      await apiClient.patch(`/notifications/${id}/dismiss`, {});
      setNotifications((prev) =>
        prev.map((n) =>
          n.id === id
            ? {
                ...n,
                action_status: 'DISMISSED',
                dismissed_at: new Date().toISOString(),
                is_read: true
              }
            : n
        )
      );
      showToast('Notification dismissed');
    } catch (err: any) {
      alert(err?.message || 'Failed to dismiss notification.');
    } finally {
      setActionInProgressId(null);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await apiClient.post('/notifications/mark-all-read', {});
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      showToast('All notifications marked as read');
    } catch (err: any) {
      alert(err?.message || 'Failed to mark all notifications read.');
    }
  };

  // Metrics
  const actionRequiredItems = notifications.filter(
    (n) => n.requires_action && (n.action_status === 'OPEN' || n.action_status === 'ACKNOWLEDGED')
  );
  const resolvedItems = notifications.filter(
    (n) => n.action_status === 'RESOLVED' || n.action_status === 'DISMISSED'
  );
  const unreadCount = notifications.filter((n) => !n.is_read).length;

  // Filter items by tab and priority
  const displayedItems = notifications.filter((n) => {
    if (activeTab === 'ACTION_REQUIRED') {
      if (!n.requires_action || (n.action_status !== 'OPEN' && n.action_status !== 'ACKNOWLEDGED')) {
        return false;
      }
    } else if (activeTab === 'RESOLVED') {
      if (n.action_status !== 'RESOLVED' && n.action_status !== 'DISMISSED') {
        return false;
      }
    }

    if (priorityFilter !== 'ALL') {
      if (priorityFilter === 'CRITICAL' && n.priority !== 'CRITICAL' && n.priority !== 'PRIORITY') {
        return false;
      }
      if (priorityFilter === 'HIGH' && n.priority !== 'HIGH') {
        return false;
      }
      if (priorityFilter === 'NORMAL' && n.priority !== 'NORMAL') {
        return false;
      }
    }
    return true;
  });

  const getIcon = (type: string, priority: string) => {
    if (priority === 'CRITICAL' || priority === 'PRIORITY' || type === 'PAYMENT_FAILED') {
      return <ShieldAlert size={20} color="var(--status-overdue, #ef4444)" />;
    }
    if (priority === 'HIGH' || type.startsWith('SUBSCRIPTION_') || type.startsWith('ACCESS_')) {
      return <AlertTriangle size={20} color="var(--status-low-stock, #f59e0b)" />;
    }
    switch (type) {
      case 'HOME_INVITATION':
      case 'INVITATION_RECEIVED':
        return <UserPlus size={20} color="var(--color-primary-900)" />;
      case 'JOIN_REQUEST':
      case 'JOIN_REQUEST_RECEIVED':
        return <Home size={20} color="var(--color-primary-900)" />;
      case 'TASK_ASSIGNED':
        return <CheckCircle2 size={20} color="var(--color-primary-900)" />;
      case 'BILL_REMINDER':
        return <Receipt size={20} color="var(--status-overdue)" />;
      case 'EVENT_REMINDER':
        return <Calendar size={20} color="var(--color-accent-warm)" />;
      default:
        return <Bell size={20} color="var(--color-text-secondary)" />;
    }
  };

  const isReserved = (item: NotificationItem) => {
    return (
      item.extra_metadata?.is_reserved === true ||
      item.body.toLowerCase().includes('subscription reserved')
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '900px' }}>
      {/* Toast Feedback */}
      {feedbackToast && (
        <div
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            backgroundColor: 'var(--color-primary-900)',
            color: 'white',
            padding: '10px 18px',
            borderRadius: '8px',
            fontSize: '13px',
            fontWeight: 600,
            zIndex: 100,
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <Check size={16} />
          <span>{feedbackToast}</span>
        </div>
      )}

      {/* Header */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 'var(--space-3)'
        }}
      >
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--color-primary-900)' }}>
            Notification & Alert Center
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
            Centralized intelligence for action-required items, access lifecycle, and household activity.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          {unreadCount > 0 && (
            <Button variant="secondary" size="sm" onClick={handleMarkAllRead}>
              <CheckCheck size={14} />
              <span>Mark all read</span>
            </Button>
          )}
          <Button variant="ghost" size="sm" onClick={() => setShowSettings(!showSettings)}>
            <Settings size={16} />
            <span>Preferences</span>
          </Button>
        </div>
      </div>

      {/* Preferences Panel */}
      {showSettings && (
        <Card
          style={{
            backgroundColor: 'var(--color-surface-overlay)',
            border: '1px solid var(--color-primary-900)',
            padding: '16px'
          }}
        >
          <h3 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '12px' }}>
            Notification Channels & Preferences
          </h3>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '12px',
              fontSize: '13px'
            }}
          >
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input type="checkbox" defaultChecked /> In-App Alerts
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input type="checkbox" defaultChecked /> Home Invitations & Joins
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input type="checkbox" defaultChecked /> Access & Subscription Reminders
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input type="checkbox" defaultChecked /> Task & Chore Assignments
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input type="checkbox" defaultChecked /> Low Stock Inventory Alerts
            </label>
          </div>
        </Card>
      )}

      {/* Main Tabs Navigation */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid var(--color-border-subtle)',
          paddingBottom: '8px',
          gap: '12px'
        }}
      >
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setActiveTab('ACTION_REQUIRED')}
            style={{
              padding: '8px 16px',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              backgroundColor: activeTab === 'ACTION_REQUIRED' ? 'var(--color-primary-900)' : 'transparent',
              color: activeTab === 'ACTION_REQUIRED' ? 'white' : 'var(--color-text-secondary)',
              fontWeight: 700,
              fontSize: '13px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <ShieldAlert size={15} />
            <span>Action Required</span>
            {actionRequiredItems.length > 0 && (
              <span
                style={{
                  backgroundColor:
                    activeTab === 'ACTION_REQUIRED' ? 'rgba(255,255,255,0.25)' : 'var(--status-overdue)',
                  color: 'white',
                  borderRadius: '10px',
                  padding: '1px 7px',
                  fontSize: '11px',
                  fontWeight: 800
                }}
              >
                {actionRequiredItems.length}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('ALL')}
            style={{
              padding: '8px 16px',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              backgroundColor: activeTab === 'ALL' ? 'var(--color-primary-900)' : 'transparent',
              color: activeTab === 'ALL' ? 'white' : 'var(--color-text-secondary)',
              fontWeight: 700,
              fontSize: '13px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Bell size={15} />
            <span>All Notifications ({notifications.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('RESOLVED')}
            style={{
              padding: '8px 16px',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              backgroundColor: activeTab === 'RESOLVED' ? 'var(--color-primary-900)' : 'transparent',
              color: activeTab === 'RESOLVED' ? 'white' : 'var(--color-text-secondary)',
              fontWeight: 700,
              fontSize: '13px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <CheckCheck size={15} />
            <span>Resolved / History ({resolvedItems.length})</span>
          </button>
        </div>

        {/* Priority Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
          <span style={{ color: 'var(--color-text-tertiary)', fontWeight: 600 }}>Priority:</span>
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            style={{
              padding: '4px 8px',
              borderRadius: '6px',
              border: '1px solid var(--color-border-subtle)',
              backgroundColor: 'var(--color-surface-card)',
              fontSize: '12px',
              fontWeight: 600,
              color: 'var(--color-text-primary)'
            }}
          >
            <option value="ALL">All Priorities</option>
            <option value="CRITICAL">Critical Only</option>
            <option value="HIGH">High Only</option>
            <option value="NORMAL">Normal Only</option>
          </select>
        </div>
      </div>

      {error && (
        <div
          style={{
            padding: '12px 16px',
            backgroundColor: 'var(--status-overdue-bg)',
            color: 'var(--status-overdue)',
            borderRadius: 'var(--radius-md)',
            fontSize: '13px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}
        >
          <span>{error}</span>
          <Button size="sm" variant="ghost" onClick={fetchNotifications}>
            Retry
          </Button>
        </div>
      )}

      {/* Notifications List */}
      {isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              style={{
                height: '80px',
                backgroundColor: 'var(--color-surface-subtle)',
                borderRadius: 'var(--radius-md)',
                animation: 'pulse 1.5s infinite'
              }}
            />
          ))}
        </div>
      ) : displayedItems.length === 0 ? (
        <Card style={{ padding: 'var(--space-12) var(--space-4)', textAlign: 'center' }}>
          <Sparkles size={36} color="var(--status-in-stock)" style={{ margin: '0 auto 10px' }} />
          <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
            {activeTab === 'ACTION_REQUIRED'
              ? 'No pending actions required!'
              : activeTab === 'RESOLVED'
              ? 'No resolved notifications yet.'
              : 'You are all caught up!'}
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
            {activeTab === 'ACTION_REQUIRED'
              ? 'All critical household tasks and access requests have been addressed.'
              : 'New updates, invitations, and alerts will appear here.'}
          </p>
        </Card>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {displayedItems.map((item) => {
            const isCritical = item.priority === 'CRITICAL' || item.priority === 'PRIORITY';
            const isHigh = item.priority === 'HIGH';
            const isActionOpen =
              item.requires_action && (item.action_status === 'OPEN' || item.action_status === 'ACKNOWLEDGED');

            return (
              <Card
                key={item.id}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                  padding: '16px 20px',
                  backgroundColor: !item.is_read
                    ? isCritical
                      ? 'rgba(239, 68, 68, 0.04)'
                      : 'var(--color-surface-subtle)'
                    : 'var(--color-surface-card)',
                  border: isCritical
                    ? '1px solid rgba(239, 68, 68, 0.3)'
                    : isHigh
                    ? '1px solid rgba(245, 158, 11, 0.3)'
                    : '1px solid var(--color-border-subtle)',
                  borderLeft: isCritical
                    ? '5px solid var(--status-overdue, #ef4444)'
                    : isHigh
                    ? '5px solid var(--status-low-stock, #f59e0b)'
                    : item.is_read
                    ? '1px solid var(--color-border-subtle)'
                    : '4px solid var(--color-primary-900)',
                  borderRadius: 'var(--radius-md)',
                  transition: 'all 0.15s ease'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px', flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        width: '40px',
                        height: '40px',
                        borderRadius: '50%',
                        backgroundColor: isCritical
                          ? 'rgba(239, 68, 68, 0.1)'
                          : isHigh
                          ? 'rgba(245, 158, 11, 0.1)'
                          : 'var(--color-surface-subtle)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0
                      }}
                    >
                      {getIcon(item.type, item.priority)}
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                        <span style={{ fontSize: '15px', fontWeight: item.is_read ? 600 : 800, color: 'var(--color-primary-900)' }}>
                          {item.title}
                        </span>

                        {/* Priority Badge */}
                        {isCritical ? (
                          <Badge variant="overdue">CRITICAL</Badge>
                        ) : isHigh ? (
                          <Badge variant="low-stock">HIGH</Badge>
                        ) : null}

                        {/* Home Scope Badge */}
                        {item.home_name && (
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              padding: '2px 8px',
                              borderRadius: '12px',
                              backgroundColor: 'var(--color-surface-subtle)',
                              color: 'var(--color-text-secondary)',
                              fontSize: '11px',
                              fontWeight: 600
                            }}
                          >
                            <Home size={11} />
                            <span>{item.home_name}</span>
                          </span>
                        )}

                        {/* Action Status Badge */}
                        {item.requires_action && (
                          <span
                            style={{
                              padding: '2px 8px',
                              borderRadius: '12px',
                              fontSize: '11px',
                              fontWeight: 700,
                              backgroundColor:
                                item.action_status === 'RESOLVED'
                                  ? 'rgba(16, 185, 129, 0.1)'
                                  : item.action_status === 'DISMISSED'
                                  ? 'rgba(107, 114, 128, 0.1)'
                                  : item.action_status === 'ACKNOWLEDGED'
                                  ? 'rgba(59, 130, 246, 0.1)'
                                  : 'rgba(239, 68, 68, 0.1)',
                              color:
                                item.action_status === 'RESOLVED'
                                  ? 'var(--status-in-stock, #10b981)'
                                  : item.action_status === 'DISMISSED'
                                  ? 'var(--color-text-tertiary)'
                                  : item.action_status === 'ACKNOWLEDGED'
                                  ? 'var(--color-primary-900)'
                                  : 'var(--status-overdue, #ef4444)'
                            }}
                          >
                            {item.action_status === 'RESOLVED'
                              ? 'Resolved'
                              : item.action_status === 'DISMISSED'
                              ? 'Dismissed'
                              : item.action_status === 'ACKNOWLEDGED'
                              ? 'Acknowledged'
                              : 'Action Required'}
                          </span>
                        )}
                      </div>

                      <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                        {item.body}
                      </div>

                      {/* Subscription Reserved Callout */}
                      {isReserved(item) && (
                        <div
                          style={{
                            marginTop: '6px',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            padding: '4px 10px',
                            backgroundColor: 'rgba(16, 185, 129, 0.08)',
                            border: '1px solid rgba(16, 185, 129, 0.3)',
                            borderRadius: '6px',
                            fontSize: '12px',
                            fontWeight: 700,
                            color: 'var(--status-in-stock, #10b981)'
                          }}
                        >
                          <Gift size={14} />
                          <span>Subscription seat pre-reserved and paid by Home Admin.</span>
                        </div>
                      )}

                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', color: 'var(--color-text-tertiary)', marginTop: '4px' }}>
                        <span>{new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} • {new Date(item.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                        {item.is_read && <span>• Read</span>}
                        {item.resolved_at && <span>• Resolved {new Date(item.resolved_at).toLocaleDateString()}</span>}
                      </div>
                    </div>
                  </div>

                  {/* Actions Toolbar */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', alignSelf: 'flex-start' }}>
                    {/* Primary Action Button (Deep link / CTA) */}
                    {item.action_url ? (
                      <Link href={item.action_url} style={{ textDecoration: 'none' }}>
                        <Button
                          size="sm"
                          style={{
                            minHeight: '34px',
                            padding: '0 14px',
                            fontSize: '12px',
                            fontWeight: 700,
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px'
                          }}
                        >
                          <span>{item.action_label || 'View'}</span>
                          <ArrowRight size={14} />
                        </Button>
                      </Link>
                    ) : item.type === 'HOME_INVITATION' ? (
                      <Link href="/join" style={{ textDecoration: 'none' }}>
                        <Button size="sm" style={{ minHeight: '34px', padding: '0 14px', fontSize: '12px', fontWeight: 700 }}>
                          <span>Join Home</span>
                        </Button>
                      </Link>
                    ) : null}

                    {/* Mark Read Button (Preserves Read ≠ Resolved invariant) */}
                    {!item.is_read && (
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={actionInProgressId === item.id}
                        onClick={() => handleMarkRead(item.id)}
                        style={{ minHeight: '34px', fontSize: '12px' }}
                      >
                        <Eye size={13} />
                        <span>Read</span>
                      </Button>
                    )}

                    {/* Action-Required Lifecycle Controls */}
                    {isActionOpen && item.action_status === 'OPEN' && (
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={actionInProgressId === item.id}
                        onClick={() => handleAcknowledge(item.id)}
                        style={{ minHeight: '34px', fontSize: '12px' }}
                      >
                        <Clock size={13} />
                        <span>Acknowledge</span>
                      </Button>
                    )}

                    {isActionOpen && (
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={actionInProgressId === item.id}
                        onClick={() => handleResolve(item.id)}
                        style={{ minHeight: '34px', fontSize: '12px', color: 'var(--status-in-stock, #10b981)' }}
                      >
                        <Check size={13} />
                        <span>Resolve</span>
                      </Button>
                    )}

                    {isActionOpen && (
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={actionInProgressId === item.id}
                        onClick={() => handleDismiss(item.id)}
                        style={{ minHeight: '34px', fontSize: '12px', color: 'var(--color-text-tertiary)' }}
                      >
                        <XCircle size={13} />
                        <span>Dismiss</span>
                      </Button>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
