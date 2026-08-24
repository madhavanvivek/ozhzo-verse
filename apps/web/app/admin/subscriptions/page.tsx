'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Plus,
  RefreshCw,
  Tag,
  Layers,
  CheckCircle,
  Percent,
  X,
  Users,
  ExternalLink
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';
import { AdminBadge } from '../components/AdminBadge';
import { SubscriptionPlan, SubscriptionFeature, Promotion, AdminSubscriberListItem } from '../types';

export default function AdminSubscriptionsPage() {
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [features, setFeatures] = useState<SubscriptionFeature[]>([]);
  const [promotions, setPromotions] = useState<Promotion[]>([]);
  const [subscribers, setSubscribers] = useState<AdminSubscriberListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Tab State
  const [activeTab, setActiveTab] = useState<'plans' | 'subscribers' | 'promotions' | 'features'>('plans');

  // Promotion Creation Modal
  const [isPromoModalOpen, setIsPromoModalOpen] = useState(false);
  const [isSubmittingPromo, setIsSubmittingPromo] = useState(false);
  const [promoForm, setPromoForm] = useState({
    code: '',
    name: '',
    description: '',
    discount_type: 'PERCENTAGE',
    discount_value: '20.00',
    currency: '',
    country: '',
    start_date: '',
    end_date: '',
    new_users_only: false,
    maximum_redemptions: '',
    maximum_redemptions_per_user: '1'
  });
  const [promoModalError, setPromoModalError] = useState<string | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [plansData, featuresData, promotionsData, subscribersData] = await Promise.all([
        apiClient.get<SubscriptionPlan[]>('/admin/subscriptions/plans'),
        apiClient.get<SubscriptionFeature[]>('/admin/subscriptions/features'),
        apiClient.get<Promotion[]>('/admin/subscriptions/promotions'),
        apiClient.get<AdminSubscriberListItem[]>('/admin/subscriptions/subscribers')
      ]);
      setPlans(plansData || []);
      setFeatures(featuresData || []);
      setPromotions(promotionsData || []);
      setSubscribers(subscribersData || []);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch subscription configuration.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreatePromotion = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmittingPromo(true);
    setPromoModalError(null);
    try {
      await apiClient.post('/admin/subscriptions/promotions', {
        code: promoForm.code.toUpperCase().trim(),
        name: promoForm.name.trim(),
        description: promoForm.description.trim() || undefined,
        discount_type: promoForm.discount_type,
        discount_value: parseFloat(promoForm.discount_value) || 0,
        currency: promoForm.currency.trim() ? promoForm.currency.toUpperCase().trim() : undefined,
        country: promoForm.country.trim() ? promoForm.country.toUpperCase().trim() : undefined,
        start_date: promoForm.start_date ? new Date(promoForm.start_date).toISOString() : undefined,
        end_date: promoForm.end_date ? new Date(promoForm.end_date).toISOString() : undefined,
        new_users_only: promoForm.new_users_only,
        maximum_redemptions: promoForm.maximum_redemptions ? parseInt(promoForm.maximum_redemptions) : undefined,
        maximum_redemptions_per_user: promoForm.maximum_redemptions_per_user ? parseInt(promoForm.maximum_redemptions_per_user) : undefined,
        status: 'ACTIVE'
      });
      setIsPromoModalOpen(false);
      setSuccessMessage(`Promotion code "${promoForm.code.toUpperCase()}" launched successfully.`);
      fetchData();
    } catch (err: any) {
      setPromoModalError(err?.message || 'Failed to create promotion.');
    } finally {
      setIsSubmittingPromo(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px'
        }}
      >
        <div>
          <h1
            style={{
              fontSize: '22px',
              fontWeight: 700,
              color: 'var(--color-text-primary, #0f172a)',
              margin: 0
            }}
          >
            Subscription & Pricing Matrix
          </h1>
          <p
            style={{
              fontSize: '14px',
              color: 'var(--color-text-secondary, #64748b)',
              marginTop: '4px'
            }}
          >
            Configure tier plans, multi-currency regional price versions, and promotional campaign discounts.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <Link
            href="/admin/coupons"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 16px',
              borderRadius: 'var(--radius-md, 10px)',
              backgroundColor: 'var(--color-primary-900, #0f172a)',
              color: 'var(--color-text-inverse, #ffffff)',
              fontSize: '13px',
              fontWeight: 600,
              border: 'none',
              textDecoration: 'none',
              cursor: 'pointer',
              minHeight: '44px'
            }}
          >
            <Tag size={16} />
            <span>Manage Coupons & Grants</span>
          </Link>

          <button
            onClick={fetchData}
            disabled={isLoading}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 16px',
              borderRadius: 'var(--radius-md, 10px)',
              border: '1px solid var(--color-border-subtle, #e2e8f0)',
              backgroundColor: 'var(--color-surface-card, #ffffff)',
              fontSize: '13px',
              fontWeight: 600,
              color: 'var(--color-text-primary, #0f172a)',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              minHeight: '44px'
            }}
          >
            <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Success Notification */}
      {successMessage && (
        <div
          style={{
            padding: '14px 18px',
            backgroundColor: 'var(--status-in-stock-bg, #ecfdf5)',
            border: '1px solid #a7f3d0',
            borderRadius: 'var(--radius-md, 10px)',
            color: 'var(--status-in-stock, #10b981)',
            fontSize: '14px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <CheckCircle size={18} />
          <span>{successMessage}</span>
        </div>
      )}

      {/* Error Alert */}
      {error && (
        <div
          style={{
            padding: '16px',
            backgroundColor: 'var(--status-overdue-bg, #fef2f2)',
            border: '1px solid #fecaca',
            borderRadius: 'var(--radius-md, 10px)',
            color: 'var(--status-overdue, #ef4444)',
            fontSize: '14px'
          }}
        >
          {error}
        </div>
      )}

      {/* Navigation Tabs */}
      <div
        style={{
          display: 'flex',
          gap: '8px',
          borderBottom: '1px solid var(--color-border-subtle, #e2e8f0)',
          paddingBottom: '8px',
          flexWrap: 'wrap'
        }}
      >
        <button
          onClick={() => setActiveTab('plans')}
          style={{
            padding: '10px 16px',
            borderRadius: 'var(--radius-md, 10px)',
            border: 'none',
            backgroundColor: activeTab === 'plans' ? 'var(--color-primary-900, #0f172a)' : 'transparent',
            color: activeTab === 'plans' ? 'var(--color-text-inverse, #ffffff)' : 'var(--color-text-secondary, #64748b)',
            fontSize: '13px',
            fontWeight: 600,
            cursor: 'pointer',
            minHeight: '44px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          <Layers size={16} />
          <span>Subscription Plans & Regional Prices ({plans.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('subscribers')}
          style={{
            padding: '10px 16px',
            borderRadius: 'var(--radius-md, 10px)',
            border: 'none',
            backgroundColor: activeTab === 'subscribers' ? 'var(--color-primary-900, #0f172a)' : 'transparent',
            color: activeTab === 'subscribers' ? 'var(--color-text-inverse, #ffffff)' : 'var(--color-text-secondary, #64748b)',
            fontSize: '13px',
            fontWeight: 600,
            cursor: 'pointer',
            minHeight: '44px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          <Users size={16} />
          <span>Active Subscribers ({subscribers.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('promotions')}
          style={{
            padding: '10px 16px',
            borderRadius: 'var(--radius-md, 10px)',
            border: 'none',
            backgroundColor: activeTab === 'promotions' ? 'var(--color-primary-900, #0f172a)' : 'transparent',
            color: activeTab === 'promotions' ? 'var(--color-text-inverse, #ffffff)' : 'var(--color-text-secondary, #64748b)',
            fontSize: '13px',
            fontWeight: 600,
            cursor: 'pointer',
            minHeight: '44px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          <Percent size={16} />
          <span>Promotions & Discounts ({promotions.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('features')}
          style={{
            padding: '10px 16px',
            borderRadius: 'var(--radius-md, 10px)',
            border: 'none',
            backgroundColor: activeTab === 'features' ? 'var(--color-primary-900, #0f172a)' : 'transparent',
            color: activeTab === 'features' ? 'var(--color-text-inverse, #ffffff)' : 'var(--color-text-secondary, #64748b)',
            fontSize: '13px',
            fontWeight: 600,
            cursor: 'pointer',
            minHeight: '44px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          <Tag size={16} />
          <span>Feature Flags ({features.length})</span>
        </button>
      </div>

      {/* Tab: Subscribers */}
      {activeTab === 'subscribers' && (
        <div
          style={{
            backgroundColor: 'var(--color-surface-card, #ffffff)',
            borderRadius: 'var(--radius-lg, 16px)',
            border: '1px solid var(--color-border-subtle, #e2e8f0)',
            overflow: 'hidden',
            boxShadow: 'var(--shadow-subtle)'
          }}
        >
          {subscribers.length === 0 ? (
            <div style={{ padding: '48px 24px', textAlign: 'center', color: 'var(--color-text-secondary, #64748b)', fontSize: '14px' }}>
              No active subscriber records found in the authoritative database.
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                <thead>
                  <tr
                    style={{
                      borderBottom: '1px solid var(--color-border-subtle, #e2e8f0)',
                      backgroundColor: 'var(--color-surface-subtle, #f1f5f9)',
                      color: 'var(--color-text-secondary, #64748b)',
                      fontWeight: 600
                    }}
                  >
                    <th style={{ padding: '12px 16px' }}>Subscriber / Owner</th>
                    <th style={{ padding: '12px 16px' }}>Household Workspace</th>
                    <th style={{ padding: '12px 16px' }}>Plan</th>
                    <th style={{ padding: '12px 16px' }}>Status</th>
                    <th style={{ padding: '12px 16px' }}>Coupon Applied</th>
                    <th style={{ padding: '12px 16px' }}>Paid Extra Seats</th>
                    <th style={{ padding: '12px 16px' }}>Renewal Date</th>
                    <th style={{ padding: '12px 16px', textAlign: 'right' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {subscribers.map((s) => (
                    <tr
                      key={s.id}
                      style={{
                        borderBottom: '1px solid var(--color-border-subtle, #e2e8f0)',
                        transition: 'background-color 0.15s ease'
                      }}
                    >
                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ fontWeight: 600, color: 'var(--color-text-primary, #0f172a)' }}>
                          {s.user_name}
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                          {s.user_email || '—'}
                        </div>
                      </td>

                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ fontWeight: 600, color: 'var(--color-text-primary, #0f172a)' }}>
                          {s.home_name}
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--color-text-secondary, #64748b)' }}>
                          ID: {s.home_id.slice(0, 8)}...
                        </div>
                      </td>

                      <td style={{ padding: '12px 16px' }}>
                        <AdminBadge variant="purple">{s.plan_name}</AdminBadge>
                      </td>

                      <td style={{ padding: '12px 16px' }}>
                        <AdminBadge
                          variant={
                            s.status === 'ACTIVE'
                              ? 'success'
                              : s.status === 'TRIALING'
                              ? 'info'
                              : 'danger'
                          }
                        >
                          {s.status}
                        </AdminBadge>
                      </td>

                      <td style={{ padding: '12px 16px' }}>
                        {s.coupon_code ? (
                          <AdminBadge variant="warning">{s.coupon_code}</AdminBadge>
                        ) : (
                          <span style={{ color: 'var(--color-text-tertiary, #94a3b8)' }}>Standard Pricing</span>
                        )}
                      </td>

                      <td style={{ padding: '12px 16px', color: 'var(--color-text-primary, #0f172a)' }}>
                        <strong>{s.paid_seats}</strong> seats
                      </td>

                      <td style={{ padding: '12px 16px', color: 'var(--color-text-secondary, #64748b)' }}>
                        {s.renewal_date ? new Date(s.renewal_date).toLocaleDateString() : '—'}
                      </td>

                      <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                        <Link
                          href={`/admin/homes/${s.home_id}`}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '6px 10px',
                            borderRadius: 'var(--radius-md, 8px)',
                            border: '1px solid var(--color-border-subtle, #e2e8f0)',
                            backgroundColor: 'var(--color-surface-subtle, #f1f5f9)',
                            fontSize: '12px',
                            fontWeight: 600,
                            color: 'var(--color-text-primary, #0f172a)',
                            minHeight: '32px'
                          }}
                        >
                          <span>Inspect Workspace</span>
                          <ExternalLink size={12} />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 1: Plans & Regional Prices */}
      {activeTab === 'plans' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {plans.map((p) => (
            <div
              key={p.id}
              style={{
                backgroundColor: 'var(--color-surface-card, #ffffff)',
                borderRadius: 'var(--radius-lg, 16px)',
                border: '1px solid var(--color-border-subtle, #e2e8f0)',
                padding: '24px',
                boxShadow: 'var(--shadow-subtle)',
                display: 'flex',
                flexDirection: 'column',
                gap: '16px'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <h2 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)', margin: 0 }}>
                      {p.name}
                    </h2>
                    <AdminBadge variant="purple">{p.code}</AdminBadge>
                    <AdminBadge variant="success">{p.status}</AdminBadge>
                  </div>
                  <p style={{ fontSize: '13px', color: 'var(--color-text-secondary, #64748b)', margin: '4px 0 0' }}>
                    {p.description || 'Full digital operating system subscription plan.'}
                  </p>
                </div>

                <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)', textAlign: 'right' }}>
                  <div>Included Members: <strong>{p.included_members}</strong></div>
                  <div>Introductory Admin: <strong>{p.introductory_enabled ? 'Free 1 Year' : 'Paid'}</strong></div>
                </div>
              </div>

              {/* Regional Pricing Versions Matrix */}
              <div>
                <h3 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)', margin: '0 0 10px' }}>
                  Regional Pricing Versions
                </h3>
                {(!p.prices || p.prices.length === 0) ? (
                  <div style={{ fontSize: '13px', color: 'var(--color-text-secondary, #64748b)' }}>
                    No regional price versions recorded for this plan.
                  </div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
                    {p.prices.map((pr) => (
                      <div
                        key={pr.id}
                        style={{
                          padding: '14px',
                          borderRadius: 'var(--radius-md, 10px)',
                          border: '1px solid var(--color-border-subtle, #e2e8f0)',
                          backgroundColor: 'var(--color-surface-subtle, #f1f5f9)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '6px',
                          fontSize: '12px'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontWeight: 700, color: 'var(--color-text-primary, #0f172a)' }}>
                            {pr.country} ({pr.currency})
                          </span>
                          <AdminBadge variant={pr.is_active ? 'success' : 'neutral'}>
                            v{pr.version} {pr.is_active ? 'Active' : 'Archived'}
                          </AdminBadge>
                        </div>
                        <div style={{ color: 'var(--color-text-secondary, #64748b)' }}>
                          Period: <strong>{pr.billing_period}</strong>
                        </div>
                        <div style={{ color: 'var(--color-text-primary, #0f172a)', fontSize: '13px', fontWeight: 600 }}>
                          Base List: {pr.currency} {pr.list_price}
                        </div>
                        <div style={{ color: 'var(--color-text-secondary, #64748b)' }}>
                          Extra Seat List: {pr.currency} {pr.additional_member_list_price} / seat
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tab 2: Promotions */}
      {activeTab === 'promotions' && (
        <div
          style={{
            backgroundColor: 'var(--color-surface-card, #ffffff)',
            borderRadius: 'var(--radius-lg, 16px)',
            border: '1px solid var(--color-border-subtle, #e2e8f0)',
            padding: '24px',
            boxShadow: 'var(--shadow-subtle)'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)', margin: 0 }}>
              Marketing Promotions & Price Reductions
            </h2>
            <button
              onClick={() => {
                setPromoModalError(null);
                setIsPromoModalOpen(true);
              }}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: 'var(--radius-md, 10px)',
                backgroundColor: 'var(--color-primary-900, #0f172a)',
                color: 'var(--color-text-inverse, #ffffff)',
                fontSize: '12px',
                fontWeight: 600,
                border: 'none',
                cursor: 'pointer',
                minHeight: '36px'
              }}
            >
              <Plus size={14} />
              <span>Create Promotion</span>
            </button>
          </div>

          {promotions.length === 0 ? (
            <div style={{ padding: '32px', textAlign: 'center', color: 'var(--color-text-secondary, #64748b)', fontSize: '14px' }}>
              No active marketing promotions found. Click "+ Create Promotion" to launch one.
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
              {promotions.map((p) => (
                <div
                  key={p.id}
                  style={{
                    padding: '16px',
                    borderRadius: 'var(--radius-md, 10px)',
                    border: '1px solid var(--color-border-subtle, #e2e8f0)',
                    backgroundColor: 'var(--color-surface-subtle, #f1f5f9)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)' }}>
                        {p.code}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                        {p.name}
                      </div>
                    </div>
                    <AdminBadge variant="success">{p.status}</AdminBadge>
                  </div>

                  <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-accent-warm, #f97316)' }}>
                    {p.discount_type === 'PERCENTAGE'
                      ? `${p.discount_value}% Discount`
                      : `$${p.discount_value} Off Base Price`}
                  </div>

                  <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                    Redemptions: <strong>{p.redemptions_count}</strong> {p.maximum_redemptions ? `/ ${p.maximum_redemptions}` : '(Unlimited)'}
                  </div>

                  {p.new_users_only && (
                    <AdminBadge variant="info">New Users Only</AdminBadge>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Feature Capabilities */}
      {activeTab === 'features' && (
        <div
          style={{
            backgroundColor: 'var(--color-surface-card, #ffffff)',
            borderRadius: 'var(--radius-lg, 16px)',
            border: '1px solid var(--color-border-subtle, #e2e8f0)',
            padding: '24px',
            boxShadow: 'var(--shadow-subtle)'
          }}
        >
          <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)', margin: '0 0 16px' }}>
            System Feature Flag Modules
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '12px' }}>
            {features.map((f) => (
              <div
                key={f.id}
                style={{
                  padding: '16px',
                  borderRadius: 'var(--radius-md, 10px)',
                  border: '1px solid var(--color-border-subtle, #e2e8f0)',
                  backgroundColor: 'var(--color-surface-subtle, #f1f5f9)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)' }}>
                    {f.name}
                  </span>
                  <AdminBadge variant={f.is_active ? 'success' : 'neutral'}>
                    {f.is_active ? 'Active' : 'Disabled'}
                  </AdminBadge>
                </div>
                <div style={{ fontSize: '11px', color: 'var(--color-text-secondary, #64748b)' }}>
                  Code: <code>{f.code}</code>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)', margin: 0 }}>
                  {f.description || 'Core feature module available to subscribers.'}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modal: Create Promotion */}
      {isPromoModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.6)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px',
            zIndex: 9999
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget && !isSubmittingPromo) setIsPromoModalOpen(false);
          }}
        >
          <div
            style={{
              backgroundColor: 'var(--color-surface-card, #ffffff)',
              borderRadius: 'var(--radius-lg, 16px)',
              padding: '24px',
              maxWidth: '500px',
              width: '100%',
              boxShadow: 'var(--shadow-modal)',
              border: '1px solid var(--color-border-subtle, #e2e8f0)',
              position: 'relative'
            }}
          >
            <button
              onClick={() => setIsPromoModalOpen(false)}
              aria-label="Close"
              style={{
                position: 'absolute',
                top: '16px',
                right: '16px',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: '8px',
                minHeight: '44px',
                minWidth: '44px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              <X size={20} />
            </button>

            <h2 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)', margin: '0 0 16px' }}>
              Launch New Promotion
            </h2>

            {promoModalError && (
              <div
                style={{
                  padding: '12px',
                  backgroundColor: 'var(--status-overdue-bg, #fef2f2)',
                  border: '1px solid #fecaca',
                  borderRadius: 'var(--radius-md, 10px)',
                  color: 'var(--status-overdue, #ef4444)',
                  fontSize: '13px',
                  marginBottom: '16px'
                }}
              >
                {promoModalError}
              </div>
            )}

            <form onSubmit={handleCreatePromotion} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                  Promotion Code (e.g. SUMMER50) *
                </label>
                <input
                  type="text"
                  required
                  placeholder="LAUNCH50"
                  value={promoForm.code}
                  onChange={(e) => setPromoForm({ ...promoForm, code: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: 'var(--radius-md, 10px)',
                    border: '1px solid var(--color-border-subtle, #e2e8f0)',
                    fontSize: '14px',
                    minHeight: '44px'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                  Campaign Display Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Early Adopter 50% Launch Discount"
                  value={promoForm.name}
                  onChange={(e) => setPromoForm({ ...promoForm, name: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: 'var(--radius-md, 10px)',
                    border: '1px solid var(--color-border-subtle, #e2e8f0)',
                    fontSize: '14px',
                    minHeight: '44px'
                  }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                    Discount Type
                  </label>
                  <select
                    value={promoForm.discount_type}
                    onChange={(e) => setPromoForm({ ...promoForm, discount_type: e.target.value })}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: 'var(--radius-md, 10px)',
                      border: '1px solid var(--color-border-subtle, #e2e8f0)',
                      fontSize: '14px',
                      minHeight: '44px'
                    }}
                  >
                    <option value="PERCENTAGE">Percentage (%)</option>
                    <option value="FIXED_AMOUNT">Fixed Currency Amount</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                    Discount Value *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={promoForm.discount_value}
                    onChange={(e) => setPromoForm({ ...promoForm, discount_value: e.target.value })}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: 'var(--radius-md, 10px)',
                      border: '1px solid var(--color-border-subtle, #e2e8f0)',
                      fontSize: '14px',
                      minHeight: '44px'
                    }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                    Start Date
                  </label>
                  <input
                    type="date"
                    value={promoForm.start_date}
                    onChange={(e) => setPromoForm({ ...promoForm, start_date: e.target.value })}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: 'var(--radius-md, 10px)',
                      border: '1px solid var(--color-border-subtle, #e2e8f0)',
                      fontSize: '14px',
                      minHeight: '44px'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                    End Date
                  </label>
                  <input
                    type="date"
                    value={promoForm.end_date}
                    onChange={(e) => setPromoForm({ ...promoForm, end_date: e.target.value })}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: 'var(--radius-md, 10px)',
                      border: '1px solid var(--color-border-subtle, #e2e8f0)',
                      fontSize: '14px',
                      minHeight: '44px'
                    }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                    Max Total Redemptions
                  </label>
                  <input
                    type="number"
                    min="1"
                    placeholder="Unlimited"
                    value={promoForm.maximum_redemptions}
                    onChange={(e) => setPromoForm({ ...promoForm, maximum_redemptions: e.target.value })}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: 'var(--radius-md, 10px)',
                      border: '1px solid var(--color-border-subtle, #e2e8f0)',
                      fontSize: '14px',
                      minHeight: '44px'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                    Per-User Usage Limit
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={promoForm.maximum_redemptions_per_user}
                    onChange={(e) => setPromoForm({ ...promoForm, maximum_redemptions_per_user: e.target.value })}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: 'var(--radius-md, 10px)',
                      border: '1px solid var(--color-border-subtle, #e2e8f0)',
                      fontSize: '14px',
                      minHeight: '44px'
                    }}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                <input
                  type="checkbox"
                  id="new-users-checkbox"
                  checked={promoForm.new_users_only}
                  onChange={(e) => setPromoForm({ ...promoForm, new_users_only: e.target.checked })}
                  style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                />
                <label htmlFor="new-users-checkbox" style={{ fontSize: '13px', fontWeight: 500, cursor: 'pointer' }}>
                  Restrict promotion to new users only
                </label>
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '12px' }}>
                <button
                  type="button"
                  onClick={() => setIsPromoModalOpen(false)}
                  disabled={isSubmittingPromo}
                  style={{
                    padding: '10px 18px',
                    borderRadius: 'var(--radius-md, 10px)',
                    border: '1px solid var(--color-border-subtle, #e2e8f0)',
                    backgroundColor: 'transparent',
                    fontSize: '14px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    minHeight: '44px'
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingPromo}
                  style={{
                    padding: '10px 20px',
                    borderRadius: 'var(--radius-md, 10px)',
                    border: 'none',
                    backgroundColor: 'var(--color-primary-900, #0f172a)',
                    color: 'var(--color-text-inverse, #ffffff)',
                    fontSize: '14px',
                    fontWeight: 600,
                    cursor: isSubmittingPromo ? 'not-allowed' : 'pointer',
                    minHeight: '44px'
                  }}
                >
                  {isSubmittingPromo ? 'Creating...' : 'Launch Promotion'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
