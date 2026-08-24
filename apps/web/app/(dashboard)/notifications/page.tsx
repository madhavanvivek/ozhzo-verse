'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import {
  Bell,
  CheckCircle2,
  AlertTriangle,
  Receipt,
  Calendar,
  UserPlus,
  Settings,
  Sparkles,
  Check
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

interface NotificationItem {
  id: string;
  title: string;
  body: string;
  type: string;
  is_read: boolean;
  created_at: string;
}

interface PaginatedNotifications {
  items: NotificationItem[];
  unread_count: number;
  total: number;
}

export default function NotificationsPage() {
  const [filter, setFilter] = useState<'ALL' | 'UNREAD'>('ALL');
  const [showSettings, setShowSettings] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchNotifications = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<PaginatedNotifications>('/notifications');
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

  const unreadCount = notifications.filter(n => !n.is_read).length;

  const handleMarkRead = async (id: string) => {
    try {
      await apiClient.patch(`/notifications/${id}/read`, {});
      setNotifications(notifications.map(n => n.id === id ? { ...n, is_read: true } : n));
    } catch (err) {
      console.error('Failed to mark notification read:', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await apiClient.post('/notifications/mark-all-read', {});
      setNotifications(notifications.map(n => ({ ...n, is_read: true })));
    } catch (err) {
      console.error('Failed to mark all notifications read:', err);
    }
  };

  const filtered = notifications.filter(n => {
    if (filter === 'UNREAD') return !n.is_read;
    return true;
  });

  const getIcon = (type: string) => {
    switch (type) {
      case 'LOW_STOCK':
        return <AlertTriangle size={18} color="var(--status-low-stock)" />;
      case 'TASK_ASSIGNED':
        return <CheckCircle2 size={18} color="var(--color-primary-900)" />;
      case 'BILL_REMINDER':
        return <Receipt size={18} color="var(--status-overdue)" />;
      case 'EVENT_REMINDER':
        return <Calendar size={18} color="var(--color-accent-warm)" />;
      case 'HOME_INVITATION':
        return <UserPlus size={18} color="var(--color-primary-900)" />;
      default:
        return <Bell size={18} color="var(--color-text-secondary)" />;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '850px' }}>
      {/* Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-3)' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-primary-900)' }}>
            Household Notifications
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)' }}>
            Stay updated with chore assignments, bill deadlines, and low-stock alerts.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          {unreadCount > 0 && (
            <Button variant="secondary" size="sm" onClick={handleMarkAllRead}>
              <Check size={14} />
              <span>Mark all as read</span>
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
        <Card style={{ backgroundColor: 'var(--color-surface-overlay)', border: '1px solid var(--color-primary-900)' }}>
          <h3 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '12px' }}>Notification Channels & Alerts</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px', fontSize: '13px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input type="checkbox" defaultChecked /> In-App Notifications
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input type="checkbox" defaultChecked /> Task & Chore Assignments
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input type="checkbox" defaultChecked /> Bill Due Reminders
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input type="checkbox" defaultChecked /> Low Stock Inventory Alerts
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input type="checkbox" defaultChecked /> Event & Calendar Reminders
            </label>
          </div>
        </Card>
      )}

      {/* Filter Tabs */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: 'var(--space-2)' }}>
        <button
          onClick={() => setFilter('ALL')}
          style={{
            padding: '6px 14px',
            borderRadius: 'var(--radius-md)',
            border: 'none',
            backgroundColor: filter === 'ALL' ? 'var(--color-primary-900)' : 'transparent',
            color: filter === 'ALL' ? 'var(--color-text-inverse)' : 'var(--color-text-secondary)',
            fontWeight: 600,
            fontSize: '13px',
            cursor: 'pointer'
          }}
        >
          All Notifications ({notifications.length})
        </button>
        <button
          onClick={() => setFilter('UNREAD')}
          style={{
            padding: '6px 14px',
            borderRadius: 'var(--radius-md)',
            border: 'none',
            backgroundColor: filter === 'UNREAD' ? 'var(--color-primary-900)' : 'transparent',
            color: filter === 'UNREAD' ? 'var(--color-text-inverse)' : 'var(--color-text-secondary)',
            fontWeight: 600,
            fontSize: '13px',
            cursor: 'pointer'
          }}
        >
          Unread ({unreadCount})
        </button>
      </div>

      {error && (
        <div style={{ padding: '10px 14px', backgroundColor: 'var(--status-overdue-bg)', color: 'var(--status-overdue)', borderRadius: 'var(--radius-md)', fontSize: '13px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span>{error}</span>
          <Button size="sm" variant="ghost" onClick={fetchNotifications}>
            Retry
          </Button>
        </div>
      )}

      {/* Notifications List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
        {isLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                style={{
                  height: '72px',
                  backgroundColor: 'var(--color-surface-subtle)',
                  borderRadius: 'var(--radius-md)',
                  animation: 'pulse 1.5s infinite'
                }}
              />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <Card style={{ padding: 'var(--space-12) var(--space-4)', textAlign: 'center' }}>
            <Sparkles size={36} color="var(--status-in-stock)" style={{ margin: '0 auto 10px' }} />
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-primary-900)' }}>
              You are all caught up!
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
              No unread notifications at this time.
            </p>
          </Card>
        ) : (
          filtered.map((item) => (
            <Card
              key={item.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '14px 18px',
                backgroundColor: item.is_read ? 'var(--color-surface-card)' : 'var(--color-surface-subtle)',
                borderLeft: item.is_read ? '1px solid var(--color-border-subtle)' : '4px solid var(--color-primary-900)',
                transition: 'all 0.15s ease'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
                <div style={{ width: '36px', height: '36px', borderRadius: '50%', backgroundColor: 'var(--color-surface-card)', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid var(--color-border-subtle)' }}>
                  {getIcon(item.type)}
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                  <div style={{ fontSize: '14px', fontWeight: item.is_read ? 600 : 700, color: 'var(--color-primary-900)' }}>
                    {item.title}
                  </div>
                  <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
                    {item.body}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)', marginTop: '2px' }}>
                    {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} • {new Date(item.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                {item.type === 'HOME_INVITATION' && (
                  <Link href="/join" style={{ textDecoration: 'none' }}>
                    <Button size="sm" style={{ minHeight: '36px', padding: '0 10px', fontSize: '12px' }}>
                      <span>Join Home</span>
                    </Button>
                  </Link>
                )}

                {!item.is_read && (
                  <Button size="sm" variant="ghost" onClick={() => handleMarkRead(item.id)}>
                    <span>Mark read</span>
                  </Button>
                )}
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
