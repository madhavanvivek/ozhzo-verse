'use client';

import React, { useState, useEffect } from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import {
  CheckCircle2,
  AlertTriangle,
  Receipt,
  Calendar as CalendarIcon,
  ShoppingCart,
  Bell,
  Plus,
  RefreshCw,
  Clock,
  Sparkles,
  Users,
  Check
} from 'lucide-react';

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

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // In production/dev this fetches GET /api/v1/homes/{home_id}/dashboard
      // For initial load, we query the live backend API
      const token = localStorage.getItem('access_token');
      const homeId = localStorage.getItem('active_home_id') || 'default';
      
      const res = await fetch(`/api/v1/homes/${homeId}/dashboard`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });

      if (res.ok) {
        const json = await res.json();
        if (json.success) {
          setData(json.data);
          return;
        }
      }

      // Fallback clean state if API has no home yet
      setData({
        greeting: {
          greeting: 'Welcome to your Household Workspace',
          user_display_name: 'Household Member',
          date_formatted: new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }),
          time_period: 'morning'
        },
        summary: {
          home_id: 'default',
          home_name: 'My Home',
          currency: 'USD',
          timezone: 'UTC',
          members_count: 1,
          active_tasks_count: 0,
          low_stock_count: 0,
          unpaid_bills_count: 0,
          unpaid_bills_sum: 0,
          upcoming_events_count: 0,
          unread_notifications_count: 0
        },
        pending_tasks: [],
        upcoming_bills: [],
        upcoming_events: [],
        low_stock_inventory: [],
        shopping_items: [],
        notifications: [],
        role: 'OWNER'
      });
    } catch (err: any) {
      setError('Unable to load dashboard data. Please verify your connection.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

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

  if (error) {
    return (
      <div style={{ padding: 'var(--space-8)', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--space-4)' }}>
        <AlertTriangle size={36} color="var(--status-overdue)" />
        <h2 style={{ fontSize: '18px', fontWeight: 700 }}>Something went wrong</h2>
        <p style={{ color: 'var(--color-text-secondary)', maxWidth: '400px', fontSize: '14px' }}>{error}</p>
        <Button onClick={fetchDashboard} variant="secondary">
          <RefreshCw size={16} />
          <span>Try Again</span>
        </Button>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      {/* Dynamic Time-Contextual Greeting */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-3)' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-primary-900)', letterSpacing: '-0.02em' }}>
            {data.greeting.greeting}
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>{data.greeting.date_formatted}</span>
            <span>•</span>
            <span style={{ fontWeight: 600, color: 'var(--color-primary-900)' }}>{data.summary.home_name}</span>
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <Button onClick={fetchDashboard} variant="secondary" size="sm">
            <RefreshCw size={14} />
            <span>Refresh</span>
          </Button>
        </div>
      </div>

      {/* Summary KPI Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--space-3)' }}>
        <Card variant="subtle" style={{ padding: '14px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>Chores Due</span>
            <CheckCircle2 size={18} color="var(--color-accent-warm)" />
          </div>
          <div style={{ fontSize: '24px', fontWeight: 700, marginTop: '6px', color: 'var(--color-primary-900)' }}>
            {data.summary.active_tasks_count}
          </div>
        </Card>

        <Card variant="subtle" style={{ padding: '14px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>Low Stock</span>
            <AlertTriangle size={18} color="var(--status-low-stock)" />
          </div>
          <div style={{ fontSize: '24px', fontWeight: 700, marginTop: '6px', color: 'var(--color-primary-900)' }}>
            {data.summary.low_stock_count}
          </div>
        </Card>

        <Card variant="subtle" style={{ padding: '14px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>Unpaid Bills</span>
            <Receipt size={18} color="var(--color-primary-900)" />
          </div>
          <div style={{ fontSize: '24px', fontWeight: 700, marginTop: '6px', color: 'var(--color-primary-900)' }}>
            {data.role !== 'CHILD' && data.role !== 'GUEST' ? `$${Number(data.summary.unpaid_bills_sum).toFixed(2)}` : '—'}
          </div>
        </Card>

        <Card variant="subtle" style={{ padding: '14px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>Family</span>
            <Users size={18} color="var(--color-text-secondary)" />
          </div>
          <div style={{ fontSize: '24px', fontWeight: 700, marginTop: '6px', color: 'var(--color-primary-900)' }}>
            {data.summary.members_count}
          </div>
        </Card>
      </div>

      {/* Main Multi-Column Pulse Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 'var(--space-4)' }}>
        
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
                    <button style={{ width: '18px', height: '18px', borderRadius: '4px', border: '1px solid var(--color-border-strong)', background: 'none', cursor: 'pointer' }} />
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
                  <Button size="sm" variant="secondary">
                    + Add to List
                  </Button>
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

        {/* Recent Household Notifications */}
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)', paddingBottom: 'var(--space-2)', borderBottom: '1px solid var(--color-border-subtle)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Bell size={18} color="var(--color-primary-900)" />
              <h2 style={{ fontSize: '15px', fontWeight: 600 }}>Recent Alerts</h2>
            </div>
            <Badge variant="neutral">{data.notifications.length} New</Badge>
          </div>

          {data.notifications.length === 0 ? (
            <div style={{ padding: 'var(--space-6) var(--space-4)', textAlign: 'center', color: 'var(--color-text-secondary)' }}>
              <Bell size={24} color="var(--color-text-tertiary)" style={{ marginBottom: '6px' }} />
              <p style={{ fontSize: '13px', fontWeight: 500 }}>No unread household notifications.</p>
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

      </div>
    </div>
  );
}
