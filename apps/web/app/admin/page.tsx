'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Users,
  Home,
  CreditCard,
  Tag,
  Activity,
  UserCheck,
  UserX,
  Building,
  Server,
  RefreshCw,
  ArrowRight,
  AlertTriangle
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';
import { AdminStatCard } from './components/AdminStatCard';
import { AdminBadge } from './components/AdminBadge';
import { AdminAnalyticsSummary, AdminSystemConfig } from './types';

export default function AdminDashboardPage() {
  const [analytics, setAnalytics] = useState<AdminAnalyticsSummary | null>(null);
  const [config, setConfig] = useState<AdminSystemConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [analyticsData, configData] = await Promise.all([
        apiClient.get<AdminAnalyticsSummary>('/admin/system/analytics-summary'),
        apiClient.get<AdminSystemConfig>('/admin/system/config')
      ]);

      setAnalytics(analyticsData);
      setConfig(configData);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch platform metrics from the backend.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

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
                fontWeight: 700,
                color: 'var(--color-text-primary, #0f172a)',
                margin: 0
              }}
            >
              Platform Overview
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
            Live database aggregate telemetry across all Ozhzo Verse tenants and user accounts.
          </p>
        </div>

        <button
          onClick={fetchDashboardData}
          disabled={isLoading}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 16px',
            borderRadius: 'var(--radius-md, 10px)',
            border: '1px solid var(--color-border-subtle, #e2e8f0)',
            backgroundColor: 'var(--color-surface-subtle, #f1f5f9)',
            fontSize: '13px',
            fontWeight: 600,
            color: 'var(--color-text-primary, #0f172a)',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            minHeight: '44px'
          }}
        >
          <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
          <span>Refresh Telemetry</span>
        </button>
      </div>

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

      {/* Primary Analytics Telemetry Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: '16px'
        }}
      >
        <AdminStatCard
          title="Total Users"
          value={isLoading ? '—' : analytics?.total_users ?? 0}
          subtitle={`${analytics?.active_users ?? 0} active | ${analytics?.suspended_users ?? 0} suspended`}
          icon={<Users size={20} />}
          variant="default"
        />
        <AdminStatCard
          title="Active Users"
          value={isLoading ? '—' : analytics?.active_users ?? 0}
          subtitle="Authorized platform accounts"
          icon={<UserCheck size={20} />}
          variant="success"
        />
        <AdminStatCard
          title="Suspended Users"
          value={isLoading ? '—' : analytics?.suspended_users ?? 0}
          subtitle="Deactivated / Restricted accounts"
          icon={<UserX size={20} />}
          variant={analytics?.suspended_users ? 'danger' : 'default'}
        />
        <AdminStatCard
          title="Total Homes"
          value={isLoading ? '—' : analytics?.total_homes ?? 0}
          subtitle={`${analytics?.active_homes ?? 0} active workspaces`}
          icon={<Home size={20} />}
          variant="info"
        />
        <AdminStatCard
          title="Active Subscriptions"
          value={isLoading ? '—' : analytics?.total_active_subscriptions ?? 0}
          subtitle="Current active entitlements"
          icon={<CreditCard size={20} />}
          variant="success"
        />
        <AdminStatCard
          title="Paid Member Seats"
          value={isLoading ? '—' : analytics?.total_paid_member_seats ?? 0}
          subtitle={`${analytics?.average_members_per_home ?? 0} avg members / home`}
          icon={<Building size={20} />}
          variant="warning"
        />
      </div>

      {/* Operations Quick Actions & Management Modules */}
      <div>
        <h2
          style={{
            fontSize: '18px',
            fontWeight: 700,
            color: 'var(--color-text-primary, #0f172a)',
            marginBottom: '16px'
          }}
        >
          Administrative Management Consoles
        </h2>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: '16px'
          }}
        >
          {/* Users Card */}
          <Link
            href="/admin/users"
            style={{
              backgroundColor: 'var(--color-surface-card, #ffffff)',
              border: '1px solid var(--color-border-subtle, #e2e8f0)',
              borderRadius: 'var(--radius-lg, 16px)',
              padding: '20px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              boxShadow: 'var(--shadow-subtle)',
              transition: 'transform 0.15s ease, box-shadow 0.15s ease'
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                <div
                  style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: 'var(--radius-md, 10px)',
                    backgroundColor: '#eff6ff',
                    color: '#2563eb',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  <Users size={22} />
                </div>
                <AdminBadge variant="info">User Ops</AdminBadge>
              </div>
              <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)', margin: '0 0 6px' }}>
                User Accounts & Access
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--color-text-secondary, #64748b)', margin: 0 }}>
                Inspect registered users, manage platform roles, and execute suspensions/reactivations with audit logs.
              </p>
            </div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                marginTop: '16px',
                fontSize: '13px',
                fontWeight: 600,
                color: '#2563eb'
              }}
            >
              <span>Manage Platform Users</span>
              <ArrowRight size={16} />
            </div>
          </Link>

          {/* Homes Card */}
          <Link
            href="/admin/homes"
            style={{
              backgroundColor: 'var(--color-surface-card, #ffffff)',
              border: '1px solid var(--color-border-subtle, #e2e8f0)',
              borderRadius: 'var(--radius-lg, 16px)',
              padding: '20px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              boxShadow: 'var(--shadow-subtle)'
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                <div
                  style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: 'var(--radius-md, 10px)',
                    backgroundColor: 'var(--status-in-stock-bg, #ecfdf5)',
                    color: 'var(--status-in-stock, #10b981)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  <Home size={22} />
                </div>
                <AdminBadge variant="success">Workspace Ops</AdminBadge>
              </div>
              <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)', margin: '0 0 6px' }}>
                Household Workspaces
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--color-text-secondary, #64748b)', margin: 0 }}>
                Review tenant home workspaces, inspect member rosters, creator identity, and workspace status.
              </p>
            </div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                marginTop: '16px',
                fontSize: '13px',
                fontWeight: 600,
                color: 'var(--status-in-stock, #10b981)'
              }}
            >
              <span>Inspect Households</span>
              <ArrowRight size={16} />
            </div>
          </Link>

          {/* Subscriptions Card */}
          <Link
            href="/admin/subscriptions"
            style={{
              backgroundColor: 'var(--color-surface-card, #ffffff)',
              border: '1px solid var(--color-border-subtle, #e2e8f0)',
              borderRadius: 'var(--radius-lg, 16px)',
              padding: '20px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              boxShadow: 'var(--shadow-subtle)'
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                <div
                  style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: 'var(--radius-md, 10px)',
                    backgroundColor: 'var(--status-low-stock-bg, #fffbeb)',
                    color: 'var(--status-low-stock, #f59e0b)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  <CreditCard size={22} />
                </div>
                <AdminBadge variant="warning">Billing Matrix</AdminBadge>
              </div>
              <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)', margin: '0 0 6px' }}>
                Plans & Regional Pricing
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--color-text-secondary, #64748b)', margin: 0 }}>
                Configure subscription plans, seat scaling prices, regional currencies, and feature entitlements.
              </p>
            </div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                marginTop: '16px',
                fontSize: '13px',
                fontWeight: 600,
                color: 'var(--status-low-stock, #f59e0b)'
              }}
            >
              <span>Manage Pricing & Plans</span>
              <ArrowRight size={16} />
            </div>
          </Link>

          {/* Coupons Card */}
          <Link
            href="/admin/coupons"
            style={{
              backgroundColor: 'var(--color-surface-card, #ffffff)',
              border: '1px solid var(--color-border-subtle, #e2e8f0)',
              borderRadius: 'var(--radius-lg, 16px)',
              padding: '20px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              boxShadow: 'var(--shadow-subtle)'
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                <div
                  style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: 'var(--radius-md, 10px)',
                    backgroundColor: '#faf5ff',
                    color: '#7e22ce',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  <Tag size={22} />
                </div>
                <AdminBadge variant="purple">Growth</AdminBadge>
              </div>
              <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)', margin: '0 0 6px' }}>
                Coupons & Entitlement Grants
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--color-text-secondary, #64748b)', margin: 0 }}>
                Create free trial coupons, configure geographic campaigns, and issue direct Super Admin home grants.
              </p>
            </div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                marginTop: '16px',
                fontSize: '13px',
                fontWeight: 600,
                color: '#7e22ce'
              }}
            >
              <span>Manage Coupons & Grants</span>
              <ArrowRight size={16} />
            </div>
          </Link>

          {/* Audit Logs Card */}
          <Link
            href="/admin/activity"
            style={{
              backgroundColor: 'var(--color-surface-card, #ffffff)',
              border: '1px solid var(--color-border-subtle, #e2e8f0)',
              borderRadius: 'var(--radius-lg, 16px)',
              padding: '20px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              boxShadow: 'var(--shadow-subtle)'
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                <div
                  style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: 'var(--radius-md, 10px)',
                    backgroundColor: 'var(--color-surface-subtle, #f1f5f9)',
                    color: 'var(--color-text-primary, #0f172a)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  <Activity size={22} />
                </div>
                <AdminBadge variant="neutral">Audit Trail</AdminBadge>
              </div>
              <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)', margin: '0 0 6px' }}>
                Platform Activity & Audits
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--color-text-secondary, #64748b)', margin: 0 }}>
                Inspect administrative actions, entity modifications, and timestamped security events across the system.
              </p>
            </div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                marginTop: '16px',
                fontSize: '13px',
                fontWeight: 600,
                color: 'var(--color-text-primary, #0f172a)'
              }}
            >
              <span>View Audit History</span>
              <ArrowRight size={16} />
            </div>
          </Link>
        </div>
      </div>

      {/* System Runtime Configuration Grid */}
      <div
        style={{
          backgroundColor: 'var(--color-surface-card, #ffffff)',
          border: '1px solid var(--color-border-subtle, #e2e8f0)',
          borderRadius: 'var(--radius-lg, 16px)',
          padding: '24px',
          boxShadow: 'var(--shadow-subtle)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <Server size={20} color="var(--color-text-secondary, #64748b)" />
          <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)', margin: 0 }}>
            Platform System Status & Configuration
          </h2>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '16px'
          }}
        >
          <div style={{ padding: '12px', backgroundColor: 'var(--color-surface-subtle, #f1f5f9)', borderRadius: 'var(--radius-md, 10px)' }}>
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-text-secondary, #64748b)', textTransform: 'uppercase' }}>
              Environment
            </div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)', marginTop: '4px' }}>
              {config?.environment || 'Production'}
            </div>
          </div>

          <div style={{ padding: '12px', backgroundColor: 'var(--color-surface-subtle, #f1f5f9)', borderRadius: 'var(--radius-md, 10px)' }}>
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-text-secondary, #64748b)', textTransform: 'uppercase' }}>
              Supported Currencies
            </div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)', marginTop: '4px' }}>
              {config?.supported_currencies?.join(', ') || 'USD, EUR, GBP, INR, CAD, AUD'}
            </div>
          </div>

          <div style={{ padding: '12px', backgroundColor: 'var(--color-surface-subtle, #f1f5f9)', borderRadius: 'var(--radius-md, 10px)' }}>
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-text-secondary, #64748b)', textTransform: 'uppercase' }}>
              Security Algorithm
            </div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)', marginTop: '4px' }}>
              {config?.password_hashing_algorithm || 'Argon2id'}
            </div>
          </div>

          <div style={{ padding: '12px', backgroundColor: 'var(--color-surface-subtle, #f1f5f9)', borderRadius: 'var(--radius-md, 10px)' }}>
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-text-secondary, #64748b)', textTransform: 'uppercase' }}>
              Default Timezone
            </div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)', marginTop: '4px' }}>
              {config?.default_timezone || 'UTC'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
