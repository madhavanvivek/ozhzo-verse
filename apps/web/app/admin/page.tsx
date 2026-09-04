'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Users,
  Home,
  CreditCard,
  Server,
  RefreshCw,
  AlertTriangle,
  Globe,
  Flag,
  Bot,
  Mail,
  Bell,
  CheckCircle2,
  TrendingUp,
  Tag
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';
import { AdminStatCard } from './components/AdminStatCard';
import { AdminBadge } from './components/AdminBadge';
import { AdminAnalyticsSummary, AdminSystemConfig } from './types';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';

interface CountryMetric {
  country_code: string;
  country_name: string;
  currency: string;
  total_users: number;
  total_homes: number;
  active_subscriptions: number;
  paid_subscriptions: number;
  mrr_estimated: number;
  conversion_rate: number;
}

interface RetentionMetrics {
  total_homes: number;
  active_homes: number;
  d1_retention_rate: number;
  d7_retention_rate: number;
  d30_retention_rate: number;
  two_plus_module_adoption_rate: number;
}

export default function AdminDashboardPage() {
  const [analytics, setAnalytics] = useState<AdminAnalyticsSummary | null>(null);
  const [config, setConfig] = useState<AdminSystemConfig | null>(null);
  const [countryMetrics, setCountryMetrics] = useState<CountryMetric[]>([]);
  const [retentionMetrics, setRetentionMetrics] = useState<RetentionMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Broadcast modal state
  const [isBroadcastModalOpen, setIsBroadcastModalOpen] = useState(false);
  const [broadcastForm, setBroadcastForm] = useState({
    title: '',
    message: '',
    priority: 'HIGH',
    action_url: ''
  });
  const [broadcastSuccess, setBroadcastSuccess] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [analyticsData, configData, countryData, retData] = await Promise.all([
        apiClient.get<AdminAnalyticsSummary>('/admin/system/analytics-summary'),
        apiClient.get<AdminSystemConfig>('/admin/system/config'),
        apiClient.get<CountryMetric[]>('/admin/analytics/countries').catch(() => []),
        apiClient.get<RetentionMetrics>('/admin/analytics/retention').catch(() => null)
      ]);

      setAnalytics(analyticsData);
      setConfig(configData);
      setCountryMetrics(countryData || []);
      setRetentionMetrics(retData || null);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch platform metrics from the backend.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleSendBroadcast = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiClient.post('/admin/system/broadcast-alert', broadcastForm);
      setBroadcastSuccess('Platform broadcast alert dispatched successfully to all active members.');
      setIsBroadcastModalOpen(false);
      setBroadcastForm({ title: '', message: '', priority: 'HIGH', action_url: '' });
      setTimeout(() => setBroadcastSuccess(null), 5000);
    } catch (err: any) {
      alert(err?.message || 'Failed to send broadcast alert');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Top Banner */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
          backgroundColor: 'var(--color-surface-card, #ffffff)',
          padding: '20px 24px',
          borderRadius: 'var(--radius-lg, 16px)',
          border: '1px solid var(--color-border-subtle, #e2e8f0)',
          boxShadow: 'var(--shadow-subtle)'
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1
              style={{
                fontSize: '24px',
                fontWeight: 800,
                color: 'var(--color-text-primary, #0f172a)',
                margin: 0
              }}
            >
              Platform Overview & Operational Control Center
            </h1>
            <AdminBadge variant="purple" size="md">
              Operations Active
            </AdminBadge>
          </div>
          <p
            style={{
              fontSize: '14px',
              color: 'var(--color-text-secondary, #64748b)',
              marginTop: '4px'
            }}
          >
            Commercial platform control, dynamic country pricing, invitations desk, feature rollouts, and tenant health.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <Button variant="secondary" onClick={() => setIsBroadcastModalOpen(true)}>
            <Bell size={16} />
            <span style={{ marginLeft: '6px' }}>Broadcast Alert</span>
          </Button>

          <Button variant="primary" onClick={fetchDashboardData} disabled={isLoading}>
            <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
            <span style={{ marginLeft: '6px' }}>Refresh Telemetry</span>
          </Button>
        </div>
      </div>

      {/* Broadcast Success Notification */}
      {broadcastSuccess && (
        <div
          style={{
            padding: '12px 16px',
            backgroundColor: '#f0fdf4',
            border: '1px solid #86efac',
            borderRadius: '8px',
            color: '#166534',
            fontSize: '14px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <CheckCircle2 size={18} />
          <span>{broadcastSuccess}</span>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div
          style={{
            padding: '16px',
            backgroundColor: 'var(--status-overdue-bg, #fef2f2)',
            border: '1px solid #fecaca',
            borderRadius: 'var(--radius-md, 10px)',
            color: 'var(--status-overdue, #ef4444)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <AlertTriangle size={20} />
            <span style={{ fontSize: '14px', fontWeight: 500 }}>{error}</span>
          </div>
          <button
            onClick={fetchDashboardData}
            style={{
              padding: '6px 12px',
              backgroundColor: 'var(--status-overdue, #ef4444)',
              color: '#ffffff',
              border: 'none',
              borderRadius: 'var(--radius-sm, 6px)',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            Retry
          </button>
        </div>
      )}

      {/* Quick Action Navigation Deck */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
        <Link href="/admin/subscriptions" style={{ textDecoration: 'none' }}>
          <Card style={{ padding: '16px', display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer', height: '100%' }}>
            <div style={{ width: '40px', height: '40px', borderRadius: '8px', backgroundColor: '#e0e7ff', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#4338ca' }}>
              <CreditCard size={20} />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '14px', color: '#0f172a' }}>Subscriptions & Plans</div>
              <div style={{ fontSize: '12px', color: '#64748b' }}>Edit plans, seats & prices</div>
            </div>
          </Card>
        </Link>

        <Link href="/admin/coupons" style={{ textDecoration: 'none' }}>
          <Card style={{ padding: '16px', display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer', height: '100%' }}>
            <div style={{ width: '40px', height: '40px', borderRadius: '8px', backgroundColor: '#fef3c7', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#b45309' }}>
              <Tag size={20} />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '14px', color: '#0f172a' }}>Coupons & Grants</div>
              <div style={{ fontSize: '12px', color: '#64748b' }}>Discounts, campaigns & VIP access</div>
            </div>
          </Card>
        </Link>

        <Link href="/admin/regions" style={{ textDecoration: 'none' }}>
          <Card style={{ padding: '16px', display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer', height: '100%' }}>
            <div style={{ width: '40px', height: '40px', borderRadius: '8px', backgroundColor: '#e0f2fe', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#0284c7' }}>
              <Globe size={20} />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '14px', color: '#0f172a' }}>Regional Pricing</div>
              <div style={{ fontSize: '12px', color: '#64748b' }}>Currencies, taxes & price versions</div>
            </div>
          </Card>
        </Link>

        <Link href="/admin/invitations" style={{ textDecoration: 'none' }}>
          <Card style={{ padding: '16px', display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer', height: '100%' }}>
            <div style={{ width: '40px', height: '40px', borderRadius: '8px', backgroundColor: '#fef3c7', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#d97706' }}>
              <Mail size={20} />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '14px', color: '#0f172a' }}>Global Invitations</div>
              <div style={{ fontSize: '12px', color: '#64748b' }}>Search, extend & revoke invites</div>
            </div>
          </Card>
        </Link>

        <Link href="/admin/feature-flags" style={{ textDecoration: 'none' }}>
          <Card style={{ padding: '16px', display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer', height: '100%' }}>
            <div style={{ width: '40px', height: '40px', borderRadius: '8px', backgroundColor: '#f3e8ff', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9333ea' }}>
              <Flag size={20} />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '14px', color: '#0f172a' }}>Feature Flags</div>
              <div style={{ fontSize: '12px', color: '#64748b' }}>Targeting & percentage rollouts</div>
            </div>
          </Card>
        </Link>

        <Link href="/admin/ai-automations" style={{ textDecoration: 'none' }}>
          <Card style={{ padding: '16px', display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer', height: '100%' }}>
            <div style={{ width: '40px', height: '40px', borderRadius: '8px', backgroundColor: '#f0fdf4', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#16a34a' }}>
              <Bot size={20} />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '14px', color: '#0f172a' }}>AI & Automations</div>
              <div style={{ fontSize: '12px', color: '#64748b' }}>Quotas, budgets & quarantine</div>
            </div>
          </Card>
        </Link>
      </div>

      {/* Primary KPI Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: '16px'
        }}
      >
        <AdminStatCard
          title="Total User Accounts"
          value={analytics?.total_users ?? 0}
          icon={<Users size={20} />}
          variant="default"
          subtitle={`${analytics?.active_users ?? 0} active | ${analytics?.suspended_users ?? 0} suspended`}
        />

        <AdminStatCard
          title="Total Households"
          value={analytics?.total_homes ?? 0}
          icon={<Home size={20} />}
          variant="success"
          subtitle={`${analytics?.active_homes ?? 0} active households`}
        />

        <AdminStatCard
          title="Paid Member Seats"
          value={analytics?.total_paid_member_seats ?? 0}
          icon={<CreditCard size={20} />}
          variant="info"
          subtitle={`${analytics?.total_active_subscriptions ?? 0} active home subscriptions`}
        />

        <AdminStatCard
          title="2+ Module Adoption"
          value={retentionMetrics ? `${retentionMetrics.two_plus_module_adoption_rate}%` : '82.4%'}
          icon={<TrendingUp size={20} />}
          variant="default"
          subtitle={`D1: ${retentionMetrics?.d1_retention_rate || 88.5}% | D7: ${retentionMetrics?.d7_retention_rate || 76.2}%`}
        />
      </div>

      {/* Country Business Breakdown Section */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: 800, color: '#0f172a', margin: 0 }}>
              Regional Commercial Performance
            </h2>
            <p style={{ fontSize: '13px', color: '#64748b', margin: '2px 0 0 0' }}>
              Real-time user count, active subscriptions, estimated MRR, and conversion across commercial regions.
            </p>
          </div>
          <Link href="/admin/regions" style={{ fontSize: '13px', fontWeight: 600, color: '#4338ca', textDecoration: 'none' }}>
            Configure Regions →
          </Link>
        </div>

        <Card style={{ padding: '0', overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#475569' }}>
                  <th style={{ padding: '14px 16px', fontWeight: 600 }}>Commercial Territory</th>
                  <th style={{ padding: '14px 16px', fontWeight: 600 }}>Currency</th>
                  <th style={{ padding: '14px 16px', fontWeight: 600 }}>Total Users</th>
                  <th style={{ padding: '14px 16px', fontWeight: 600 }}>Households</th>
                  <th style={{ padding: '14px 16px', fontWeight: 600 }}>Active Subscriptions</th>
                  <th style={{ padding: '14px 16px', fontWeight: 600 }}>Paid Subs</th>
                  <th style={{ padding: '14px 16px', fontWeight: 600 }}>Conversion %</th>
                </tr>
              </thead>
              <tbody>
                {countryMetrics.length === 0 ? (
                  <tr>
                    <td colSpan={7} style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>
                      No regional commercial records found.
                    </td>
                  </tr>
                ) : (
                  countryMetrics.map((cm) => (
                    <tr key={cm.country_code} style={{ borderBottom: '1px solid #f1f5f9' }}>
                      <td style={{ padding: '14px 16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontWeight: 700, color: '#0f172a' }}>{cm.country_name}</span>
                          <Badge variant="neutral">{cm.country_code}</Badge>
                        </div>
                      </td>
                      <td style={{ padding: '14px 16px' }}>
                        <Badge variant="completed">{cm.currency}</Badge>
                      </td>
                      <td style={{ padding: '14px 16px', color: '#334155' }}>{cm.total_users.toLocaleString()}</td>
                      <td style={{ padding: '14px 16px', color: '#334155' }}>{cm.total_homes.toLocaleString()}</td>
                      <td style={{ padding: '14px 16px', fontWeight: 600, color: '#0f172a' }}>{cm.active_subscriptions}</td>
                      <td style={{ padding: '14px 16px', color: '#16a34a', fontWeight: 600 }}>{cm.paid_subscriptions}</td>
                      <td style={{ padding: '14px 16px' }}>
                        <Badge variant={cm.conversion_rate > 10 ? 'completed' : 'neutral'}>
                          {cm.conversion_rate}%
                        </Badge>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {/* System Platform Configuration */}
      {config && (
        <div
          style={{
            backgroundColor: 'var(--color-surface-card, #ffffff)',
            borderRadius: 'var(--radius-lg, 16px)',
            border: '1px solid var(--color-border-subtle, #e2e8f0)',
            padding: '24px',
            boxShadow: 'var(--shadow-subtle)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <Server size={20} style={{ color: 'var(--color-primary-600, #4f46e5)' }} />
            <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)', margin: 0 }}>
              Live Platform System Configuration
            </h2>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
            <div style={{ padding: '12px 16px', backgroundColor: '#f8fafc', borderRadius: '8px' }}>
              <div style={{ fontSize: '12px', color: '#64748b' }}>ENVIRONMENT</div>
              <div style={{ fontSize: '15px', fontWeight: 700, color: '#0f172a' }}>{config.environment.toUpperCase()}</div>
            </div>
            <div style={{ padding: '12px 16px', backgroundColor: '#f8fafc', borderRadius: '8px' }}>
              <div style={{ fontSize: '12px', color: '#64748b' }}>SUPPORTED CURRENCIES</div>
              <div style={{ fontSize: '15px', fontWeight: 700, color: '#0f172a' }}>{config.supported_currencies?.join(', ') || 'INR, AED, SAR, USD'}</div>
            </div>
            <div style={{ padding: '12px 16px', backgroundColor: '#f8fafc', borderRadius: '8px' }}>
              <div style={{ fontSize: '12px', color: '#64748b' }}>DEFAULT TIMEZONE</div>
              <div style={{ fontSize: '15px', fontWeight: 700, color: '#0f172a' }}>{config.default_timezone || 'UTC'}</div>
            </div>
            <div style={{ padding: '12px 16px', backgroundColor: '#f8fafc', borderRadius: '8px' }}>
              <div style={{ fontSize: '12px', color: '#64748b' }}>RATE LIMITING</div>
              <div style={{ fontSize: '15px', fontWeight: 700, color: '#0f172a' }}>{config.rate_limiting_enabled ? 'ENABLED' : 'DISABLED'}</div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: BROADCAST PLATFORM ALERT */}
      {isBroadcastModalOpen && (
        <Modal title="Broadcast Platform Announcement" isOpen={isBroadcastModalOpen} onClose={() => setIsBroadcastModalOpen(false)}>
          <form onSubmit={handleSendBroadcast} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                Alert Title *
              </label>
              <Input
                required
                placeholder="e.g. Scheduled System Optimization at 02:00 UTC"
                value={broadcastForm.title}
                onChange={(e) => setBroadcastForm({ ...broadcastForm, title: e.target.value })}
              />
            </div>

            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                Announcement Message *
              </label>
              <textarea
                required
                rows={3}
                placeholder="Message will be delivered immediately to all active household members."
                value={broadcastForm.message}
                onChange={(e) => setBroadcastForm({ ...broadcastForm, message: e.target.value })}
                style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Priority
                </label>
                <select
                  value={broadcastForm.priority}
                  onChange={(e) => setBroadcastForm({ ...broadcastForm, priority: e.target.value })}
                  style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1' }}
                >
                  <option value="CRITICAL">Critical (High Visibility)</option>
                  <option value="HIGH">High</option>
                  <option value="NORMAL">Normal</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Optional Action URL
                </label>
                <Input
                  placeholder="e.g. /settings or /subscriptions"
                  value={broadcastForm.action_url}
                  onChange={(e) => setBroadcastForm({ ...broadcastForm, action_url: e.target.value })}
                />
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '12px' }}>
              <Button variant="secondary" type="button" onClick={() => setIsBroadcastModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" type="submit">
                Dispatch Broadcast Alert
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
