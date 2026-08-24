'use client';

import React, { useState, useEffect } from 'react';
import {
  Tag,
  Plus,
  RefreshCw,
  Gift,
  Award,
  CheckCircle,
  X
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';
import { AdminBadge } from '../components/AdminBadge';
import { Coupon, Campaign, SubscriptionGrant, CouponAnalytics } from '../types';

export default function AdminCouponsPage() {
  const [coupons, setCoupons] = useState<Coupon[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [grants, setGrants] = useState<SubscriptionGrant[]>([]);
  const [analytics, setAnalytics] = useState<CouponAnalytics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Active Tab
  const [activeTab, setActiveTab] = useState<'coupons' | 'campaigns' | 'grants'>('coupons');

  // Coupon Modal State
  const [isCouponModalOpen, setIsCouponModalOpen] = useState(false);
  const [isSubmittingCoupon, setIsSubmittingCoupon] = useState(false);
  const [couponModalError, setCouponModalError] = useState<string | null>(null);
  const [couponForm, setCouponForm] = useState({
    name: '',
    code: '',
    description: '',
    coupon_type: 'FREE_PERIOD',
    discount_value: '0.00',
    free_period_value: 6,
    free_period_unit: 'MONTHS',
    eligibility_type: 'ANY_USER',
    maximum_total_redemptions: '',
    maximum_redemptions_per_user: 1,
    start_date: '',
    end_date: '',
    country: '',
    state: ''
  });

  // Grant Modal State
  const [isGrantModalOpen, setIsGrantModalOpen] = useState(false);
  const [isSubmittingGrant, setIsSubmittingGrant] = useState(false);
  const [grantModalError, setGrantModalError] = useState<string | null>(null);
  const [grantForm, setGrantForm] = useState({
    home_id: '',
    grant_type: 'FREE_PERIOD',
    duration_value: 6,
    duration_unit: 'MONTHS',
    reason: 'VIP Early Adopter Direct Access'
  });

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [couponsData, campaignsData, grantsData, analyticsData] = await Promise.all([
        apiClient.get<Coupon[]>('/admin/coupons'),
        apiClient.get<Campaign[]>('/admin/coupons/campaigns'),
        apiClient.get<SubscriptionGrant[]>('/admin/coupons/grants'),
        apiClient.get<CouponAnalytics>('/admin/coupons/analytics')
      ]);

      setCoupons(couponsData || []);
      setCampaigns(campaignsData || []);
      setGrants(grantsData || []);
      setAnalytics(analyticsData || null);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch coupon records.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateCoupon = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmittingCoupon(true);
    setCouponModalError(null);
    try {
      await apiClient.post('/admin/coupons', {
        name: couponForm.name.trim(),
        code: couponForm.code.toUpperCase().trim(),
        description: couponForm.description.trim() || undefined,
        coupon_type: couponForm.coupon_type,
        discount_value: parseFloat(couponForm.discount_value) || 0,
        free_period_value: Number(couponForm.free_period_value) || 0,
        free_period_unit: couponForm.free_period_unit,
        eligibility_type: couponForm.eligibility_type,
        start_date: couponForm.start_date ? new Date(couponForm.start_date).toISOString() : undefined,
        end_date: couponForm.end_date ? new Date(couponForm.end_date).toISOString() : undefined,
        maximum_total_redemptions: couponForm.maximum_total_redemptions
          ? parseInt(couponForm.maximum_total_redemptions)
          : undefined,
        maximum_redemptions_per_user: Number(couponForm.maximum_redemptions_per_user) || 1,
        country: couponForm.country.trim() ? couponForm.country.toUpperCase().trim() : undefined,
        state: couponForm.state.trim() || undefined,
        status: 'ACTIVE'
      });
      setIsCouponModalOpen(false);
      setSuccessMessage(`Coupon code "${couponForm.code.toUpperCase()}" created successfully.`);
      fetchData();
    } catch (err: any) {
      setCouponModalError(err?.message || 'Failed to create coupon.');
    } finally {
      setIsSubmittingCoupon(false);
    }
  };

  const handleCreateGrant = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmittingGrant(true);
    setGrantModalError(null);
    try {
      await apiClient.post('/admin/coupons/grants', {
        home_id: grantForm.home_id.trim(),
        grant_type: grantForm.grant_type,
        duration_value: Number(grantForm.duration_value) || 6,
        duration_unit: grantForm.duration_unit,
        discount_value: 0,
        reason: grantForm.reason.trim()
      });
      setIsGrantModalOpen(false);
      setSuccessMessage('Direct entitlement grant issued successfully to workspace.');
      fetchData();
    } catch (err: any) {
      setGrantModalError(err?.message || 'Failed to issue direct entitlement grant.');
    } finally {
      setIsSubmittingGrant(false);
    }
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return '—';
    try {
      return new Date(dateStr).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return dateStr;
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
            Coupons, Campaigns & Grants
          </h1>
          <p
            style={{
              fontSize: '14px',
              color: 'var(--color-text-secondary, #64748b)',
              marginTop: '4px'
            }}
          >
            Issue free period codes, manage regional campaign allocations, and grant direct workspace entitlements.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <button
            onClick={() => {
              setCouponModalError(null);
              setIsCouponModalOpen(true);
            }}
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
              cursor: 'pointer',
              minHeight: '44px'
            }}
          >
            <Plus size={16} />
            <span>Create Coupon</span>
          </button>

          <button
            onClick={() => {
              setGrantModalError(null);
              setIsGrantModalOpen(true);
            }}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 16px',
              borderRadius: 'var(--radius-md, 10px)',
              backgroundColor: 'var(--status-in-stock, #10b981)',
              color: 'var(--color-text-inverse, #ffffff)',
              fontSize: '13px',
              fontWeight: 600,
              border: 'none',
              cursor: 'pointer',
              minHeight: '44px'
            }}
          >
            <Award size={16} />
            <span>Grant Entitlement</span>
          </button>

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

      {/* Analytics Metric Bar */}
      {analytics && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '12px'
          }}
        >
          <div style={{ padding: '16px', backgroundColor: 'var(--color-surface-card, #ffffff)', borderRadius: 'var(--radius-lg, 16px)', border: '1px solid var(--color-border-subtle, #e2e8f0)' }}>
            <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)', fontWeight: 600 }}>Active Coupons</div>
            <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)', marginTop: '4px' }}>
              {analytics.active_coupons} / {analytics.total_coupons}
            </div>
          </div>
          <div style={{ padding: '16px', backgroundColor: 'var(--color-surface-card, #ffffff)', borderRadius: 'var(--radius-lg, 16px)', border: '1px solid var(--color-border-subtle, #e2e8f0)' }}>
            <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)', fontWeight: 600 }}>Total Redemptions</div>
            <div style={{ fontSize: '24px', fontWeight: 700, color: '#2563eb', marginTop: '4px' }}>
              {analytics.total_redemptions}
            </div>
          </div>
          <div style={{ padding: '16px', backgroundColor: 'var(--color-surface-card, #ffffff)', borderRadius: 'var(--radius-lg, 16px)', border: '1px solid var(--color-border-subtle, #e2e8f0)' }}>
            <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)', fontWeight: 600 }}>Direct Entitlement Grants</div>
            <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--status-in-stock, #10b981)', marginTop: '4px' }}>
              {analytics.active_direct_grants}
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div
        style={{
          display: 'flex',
          gap: '8px',
          borderBottom: '1px solid var(--color-border-subtle, #e2e8f0)',
          paddingBottom: '8px'
        }}
      >
        <button
          onClick={() => setActiveTab('coupons')}
          style={{
            padding: '10px 16px',
            borderRadius: 'var(--radius-md, 10px)',
            border: 'none',
            backgroundColor: activeTab === 'coupons' ? 'var(--color-primary-900, #0f172a)' : 'transparent',
            color: activeTab === 'coupons' ? 'var(--color-text-inverse, #ffffff)' : 'var(--color-text-secondary, #64748b)',
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
          <span>Coupons ({coupons.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('campaigns')}
          style={{
            padding: '10px 16px',
            borderRadius: 'var(--radius-md, 10px)',
            border: 'none',
            backgroundColor: activeTab === 'campaigns' ? 'var(--color-primary-900, #0f172a)' : 'transparent',
            color: activeTab === 'campaigns' ? 'var(--color-text-inverse, #ffffff)' : 'var(--color-text-secondary, #64748b)',
            fontSize: '13px',
            fontWeight: 600,
            cursor: 'pointer',
            minHeight: '44px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          <Gift size={16} />
          <span>Marketing Campaigns ({campaigns.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('grants')}
          style={{
            padding: '10px 16px',
            borderRadius: 'var(--radius-md, 10px)',
            border: 'none',
            backgroundColor: activeTab === 'grants' ? 'var(--color-primary-900, #0f172a)' : 'transparent',
            color: activeTab === 'grants' ? 'var(--color-text-inverse, #ffffff)' : 'var(--color-text-secondary, #64748b)',
            fontSize: '13px',
            fontWeight: 600,
            cursor: 'pointer',
            minHeight: '44px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          <Award size={16} />
          <span>Direct Super Admin Grants ({grants.length})</span>
        </button>
      </div>

      {/* Tab 1: Coupons */}
      {activeTab === 'coupons' && (
        <div
          style={{
            backgroundColor: 'var(--color-surface-card, #ffffff)',
            borderRadius: 'var(--radius-lg, 16px)',
            border: '1px solid var(--color-border-subtle, #e2e8f0)',
            padding: '24px',
            boxShadow: 'var(--shadow-subtle)'
          }}
        >
          {coupons.length === 0 ? (
            <div style={{ padding: '32px', textAlign: 'center', color: 'var(--color-text-secondary, #64748b)', fontSize: '14px' }}>
              No coupons created. Click "+ Create Coupon" to generate a free trial code.
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '14px' }}>
              {coupons.map((c) => (
                <div
                  key={c.id}
                  style={{
                    padding: '18px',
                    borderRadius: 'var(--radius-md, 10px)',
                    border: '1px solid var(--color-border-subtle, #e2e8f0)',
                    backgroundColor: 'var(--color-surface-subtle, #f1f5f9)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '10px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)' }}>
                        {c.code}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                        {c.name}
                      </div>
                    </div>
                    <AdminBadge variant={c.status === 'ACTIVE' ? 'success' : 'neutral'}>{c.status}</AdminBadge>
                  </div>

                  <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-accent-amber, #f59e0b)' }}>
                    {c.coupon_type === 'FREE_PERIOD'
                      ? `🎁 ${c.free_period_value} ${c.free_period_unit} 100% Free`
                      : c.coupon_type === 'PERCENTAGE_DISCOUNT'
                      ? `${c.discount_value}% Off`
                      : `$${c.discount_value} Off`}
                  </div>

                  <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                    Eligibility: <strong>{c.eligibility_type}</strong>
                  </div>

                  <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                    Usage: <strong>{c.redemptions_count}</strong> {c.maximum_total_redemptions ? `/ ${c.maximum_total_redemptions}` : '(Unlimited)'}
                  </div>

                  <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary, #94a3b8)' }}>
                    Created: {formatDate(c.created_at)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Campaigns */}
      {activeTab === 'campaigns' && (
        <div
          style={{
            backgroundColor: 'var(--color-surface-card, #ffffff)',
            borderRadius: 'var(--radius-lg, 16px)',
            border: '1px solid var(--color-border-subtle, #e2e8f0)',
            padding: '24px',
            boxShadow: 'var(--shadow-subtle)'
          }}
        >
          {campaigns.length === 0 ? (
            <div style={{ padding: '32px', textAlign: 'center', color: 'var(--color-text-secondary, #64748b)', fontSize: '14px' }}>
              No marketing campaigns configured.
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
              {campaigns.map((camp) => (
                <div
                  key={camp.id}
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
                        {camp.name}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                        Code: <code>{camp.code}</code>
                      </div>
                    </div>
                    <AdminBadge variant="success">{camp.status}</AdminBadge>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                    Redemptions: <strong>{camp.redemptions_count}</strong> {camp.maximum_redemptions ? `/ ${camp.maximum_redemptions}` : ''}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Grants */}
      {activeTab === 'grants' && (
        <div
          style={{
            backgroundColor: 'var(--color-surface-card, #ffffff)',
            borderRadius: 'var(--radius-lg, 16px)',
            border: '1px solid var(--color-border-subtle, #e2e8f0)',
            padding: '24px',
            boxShadow: 'var(--shadow-subtle)'
          }}
        >
          {grants.length === 0 ? (
            <div style={{ padding: '32px', textAlign: 'center', color: 'var(--color-text-secondary, #64748b)', fontSize: '14px' }}>
              No direct entitlement grants issued yet.
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '14px' }}>
              {grants.map((g) => (
                <div
                  key={g.id}
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
                    <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)' }}>
                      Home ID: {g.home_id.slice(0, 8)}...
                    </div>
                    <AdminBadge variant="success">{g.status}</AdminBadge>
                  </div>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--status-in-stock, #10b981)' }}>
                    Grant: {g.duration_value} {g.duration_unit} Free Entitlement
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                    Reason: {g.reason}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary, #94a3b8)' }}>
                    Expires: {formatDate(g.expiry_date)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Modal: Create Coupon */}
      {isCouponModalOpen && (
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
            if (e.target === e.currentTarget && !isSubmittingCoupon) setIsCouponModalOpen(false);
          }}
        >
          <div
            style={{
              backgroundColor: 'var(--color-surface-card, #ffffff)',
              borderRadius: 'var(--radius-lg, 16px)',
              padding: '24px',
              maxWidth: '520px',
              width: '100%',
              boxShadow: 'var(--shadow-modal)',
              border: '1px solid var(--color-border-subtle, #e2e8f0)',
              position: 'relative',
              maxHeight: '90vh',
              overflowY: 'auto'
            }}
          >
            <button
              onClick={() => setIsCouponModalOpen(false)}
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
              Create New Coupon Code
            </h2>

            {couponModalError && (
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
                {couponModalError}
              </div>
            )}

            <form onSubmit={handleCreateCoupon} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                  Coupon Code (e.g. WELCOME6M) *
                </label>
                <input
                  type="text"
                  required
                  placeholder="WELCOME6M"
                  value={couponForm.code}
                  onChange={(e) => setCouponForm({ ...couponForm, code: e.target.value })}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                  Display Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="6 Months Free Early Adopter Access"
                  value={couponForm.name}
                  onChange={(e) => setCouponForm({ ...couponForm, name: e.target.value })}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                    Coupon Type
                  </label>
                  <select
                    value={couponForm.coupon_type}
                    onChange={(e) => setCouponForm({ ...couponForm, coupon_type: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                  >
                    <option value="FREE_PERIOD">100% Free Period</option>
                    <option value="PERCENTAGE_DISCOUNT">Percentage Discount</option>
                    <option value="FIXED_DISCOUNT">Fixed Currency Discount</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                    Eligibility
                  </label>
                  <select
                    value={couponForm.eligibility_type}
                    onChange={(e) => setCouponForm({ ...couponForm, eligibility_type: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                  >
                    <option value="ANY_USER">Any User</option>
                    <option value="NEW_USER">New Users Only</option>
                    <option value="EXISTING_USER">Existing Users</option>
                  </select>
                </div>
              </div>

              {couponForm.coupon_type === 'FREE_PERIOD' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                      Free Duration Value *
                    </label>
                    <input
                      type="number"
                      min="1"
                      required
                      value={couponForm.free_period_value}
                      onChange={(e) => setCouponForm({ ...couponForm, free_period_value: parseInt(e.target.value) || 1 })}
                      style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                      Unit
                    </label>
                    <select
                      value={couponForm.free_period_unit}
                      onChange={(e) => setCouponForm({ ...couponForm, free_period_unit: e.target.value })}
                      style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                    >
                      <option value="DAYS">Days</option>
                      <option value="MONTHS">Months</option>
                      <option value="YEARS">Years</option>
                    </select>
                  </div>
                </div>
              )}

              {couponForm.coupon_type !== 'FREE_PERIOD' && (
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                    Discount Value *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={couponForm.discount_value}
                    onChange={(e) => setCouponForm({ ...couponForm, discount_value: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                  />
                </div>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                    Redemption Valid From
                  </label>
                  <input
                    type="date"
                    value={couponForm.start_date}
                    onChange={(e) => setCouponForm({ ...couponForm, start_date: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                    Redemption Valid Until
                  </label>
                  <input
                    type="date"
                    value={couponForm.end_date}
                    onChange={(e) => setCouponForm({ ...couponForm, end_date: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '12px' }}>
                <button
                  type="button"
                  onClick={() => setIsCouponModalOpen(false)}
                  disabled={isSubmittingCoupon}
                  style={{ padding: '10px 18px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', backgroundColor: 'transparent', fontSize: '14px', fontWeight: 600, cursor: 'pointer', minHeight: '44px' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingCoupon}
                  style={{ padding: '10px 20px', borderRadius: 'var(--radius-md, 10px)', border: 'none', backgroundColor: 'var(--color-primary-900, #0f172a)', color: 'var(--color-text-inverse, #ffffff)', fontSize: '14px', fontWeight: 600, cursor: isSubmittingCoupon ? 'not-allowed' : 'pointer', minHeight: '44px' }}
                >
                  {isSubmittingCoupon ? 'Creating...' : 'Create Coupon'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Direct Grant */}
      {isGrantModalOpen && (
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
            if (e.target === e.currentTarget && !isSubmittingGrant) setIsGrantModalOpen(false);
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
              onClick={() => setIsGrantModalOpen(false)}
              aria-label="Close"
              style={{ position: 'absolute', top: '16px', right: '16px', background: 'none', border: 'none', cursor: 'pointer', padding: '8px', minHeight: '44px', minWidth: '44px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            >
              <X size={20} />
            </button>

            <h2 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)', margin: '0 0 16px' }}>
              Issue Direct Entitlement Grant
            </h2>

            {grantModalError && (
              <div style={{ padding: '12px', backgroundColor: 'var(--status-overdue-bg, #fef2f2)', border: '1px solid #fecaca', borderRadius: 'var(--radius-md, 10px)', color: 'var(--status-overdue, #ef4444)', fontSize: '13px', marginBottom: '16px' }}>
                {grantModalError}
              </div>
            )}

            <form onSubmit={handleCreateGrant} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                  Target Home Workspace UUID *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 123e4567-e89b-12d3-a456-426614174000"
                  value={grantForm.home_id}
                  onChange={(e) => setGrantForm({ ...grantForm, home_id: e.target.value })}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                    Duration Value *
                  </label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={grantForm.duration_value}
                    onChange={(e) => setGrantForm({ ...grantForm, duration_value: parseInt(e.target.value) || 1 })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                    Unit
                  </label>
                  <select
                    value={grantForm.duration_unit}
                    onChange={(e) => setGrantForm({ ...grantForm, duration_unit: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                  >
                    <option value="MONTHS">Months</option>
                    <option value="DAYS">Days</option>
                    <option value="YEARS">Years</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                  Administrative Grant Reason *
                </label>
                <textarea
                  required
                  rows={2}
                  value={grantForm.reason}
                  onChange={(e) => setGrantForm({ ...grantForm, reason: e.target.value })}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
                />
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '12px' }}>
                <button
                  type="button"
                  onClick={() => setIsGrantModalOpen(false)}
                  disabled={isSubmittingGrant}
                  style={{ padding: '10px 18px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', backgroundColor: 'transparent', fontSize: '14px', fontWeight: 600, cursor: 'pointer', minHeight: '44px' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingGrant}
                  style={{ padding: '10px 20px', borderRadius: 'var(--radius-md, 10px)', border: 'none', backgroundColor: 'var(--status-in-stock, #10b981)', color: 'var(--color-text-inverse, #ffffff)', fontSize: '14px', fontWeight: 600, cursor: isSubmittingGrant ? 'not-allowed' : 'pointer', minHeight: '44px' }}
                >
                  {isSubmittingGrant ? 'Issuing...' : 'Grant Entitlement'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
