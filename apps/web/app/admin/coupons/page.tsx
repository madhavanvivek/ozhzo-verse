'use client';

import React, { useState, useEffect } from 'react';
import {
  Tag,
  Plus,
  RefreshCw,
  Gift,
  Award,
  CheckCircle,
  Edit2,
  Search,
  Eye,
  Archive,
  Power
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';
import { AdminBadge } from '../components/AdminBadge';
import { Modal } from '@/components/ui/Modal';
import { Coupon, Campaign, SubscriptionGrant, CouponAnalytics } from '../types';
import { ControlledCountrySelector, RegionConfig, getCountryFlag } from '../components/ControlledCountrySelector';

export default function AdminCouponsPage() {
  const [coupons, setCoupons] = useState<Coupon[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [grants, setGrants] = useState<SubscriptionGrant[]>([]);
  const [analytics, setAnalytics] = useState<CouponAnalytics | null>(null);
  const [regions, setRegions] = useState<RegionConfig[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Active Tab
  const [activeTab, setActiveTab] = useState<'coupons' | 'campaigns' | 'grants'>('coupons');

  // Filter & Search State
  const [couponSearch, setCouponSearch] = useState('');
  const [couponStatusFilter, setCouponStatusFilter] = useState('ALL');

  // Create Coupon Modal State
  const [isCouponModalOpen, setIsCouponModalOpen] = useState(false);
  const [isSubmittingCoupon, setIsSubmittingCoupon] = useState(false);
  const [couponModalError, setCouponModalError] = useState<string | null>(null);
  const [couponForm, setCouponForm] = useState({
    name: '',
    code: '',
    description: '',
    coupon_type: 'PERCENTAGE_DISCOUNT',
    discount_value: '50.00',
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

  // Edit Coupon Modal State
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isSubmittingEdit, setIsSubmittingEdit] = useState(false);
  const [editModalError, setEditModalError] = useState<string | null>(null);
  const [selectedCoupon, setSelectedCoupon] = useState<Coupon | null>(null);
  const [editForm, setEditForm] = useState({
    name: '',
    description: '',
    coupon_type: 'PERCENTAGE_DISCOUNT',
    discount_value: '0.00',
    free_period_value: 0,
    free_period_unit: 'MONTHS',
    eligibility_type: 'ANY_USER',
    country: '',
    state: '',
    status: 'ACTIVE',
    end_date: '',
    maximum_total_redemptions: '',
    maximum_redemptions_per_user: 1,
    internal_reason: ''
  });

  // Redemptions History Modal
  const [isRedemptionsModalOpen, setIsRedemptionsModalOpen] = useState(false);
  const [redemptionsList, setRedemptionsList] = useState<any[]>([]);
  const [isLoadingRedemptions, setIsLoadingRedemptions] = useState(false);
  const [viewingCouponCode, setViewingCouponCode] = useState('');

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
      const [couponsData, campaignsData, grantsData, analyticsData, regionsData] = await Promise.all([
        apiClient.get<Coupon[]>('/admin/coupons'),
        apiClient.get<Campaign[]>('/admin/coupons/campaigns'),
        apiClient.get<SubscriptionGrant[]>('/admin/coupons/grants'),
        apiClient.get<CouponAnalytics>('/admin/coupons/analytics'),
        apiClient.get<RegionConfig[]>('/admin/regions').catch(() => [])
      ]);

      setCoupons(couponsData || []);
      setCampaigns(campaignsData || []);
      setGrants(grantsData || []);
      setAnalytics(analyticsData || null);
      setRegions(regionsData || []);
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

  const openEditModal = (coupon: Coupon) => {
    setSelectedCoupon(coupon);
    setEditForm({
      name: coupon.name,
      description: coupon.description || '',
      coupon_type: coupon.coupon_type,
      discount_value: String(coupon.discount_value || '0.00'),
      free_period_value: coupon.free_period_value || 0,
      free_period_unit: coupon.free_period_unit || 'MONTHS',
      eligibility_type: coupon.eligibility_type || 'ANY_USER',
      country: coupon.country || '',
      state: coupon.state || '',
      status: coupon.status || 'ACTIVE',
      end_date: coupon.end_date ? coupon.end_date.split('T')[0] : '',
      maximum_total_redemptions: coupon.maximum_total_redemptions ? String(coupon.maximum_total_redemptions) : '',
      maximum_redemptions_per_user: coupon.maximum_redemptions_per_user || 1,
      internal_reason: coupon.internal_reason || ''
    });
    setEditModalError(null);
    setIsEditModalOpen(true);
  };

  const handleUpdateCoupon = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCoupon) return;
    setIsSubmittingEdit(true);
    setEditModalError(null);
    try {
      await apiClient.patch(`/admin/coupons/${selectedCoupon.id}`, {
        name: editForm.name.trim(),
        description: editForm.description.trim() || undefined,
        coupon_type: editForm.coupon_type,
        discount_value: parseFloat(editForm.discount_value) || 0,
        free_period_value: Number(editForm.free_period_value) || 0,
        free_period_unit: editForm.free_period_unit,
        eligibility_type: editForm.eligibility_type,
        country: editForm.country.trim() ? editForm.country.toUpperCase().trim() : undefined,
        state: editForm.state.trim() || undefined,
        status: editForm.status,
        end_date: editForm.end_date ? new Date(editForm.end_date).toISOString() : undefined,
        maximum_total_redemptions: editForm.maximum_total_redemptions
          ? parseInt(editForm.maximum_total_redemptions)
          : undefined,
        maximum_redemptions_per_user: Number(editForm.maximum_redemptions_per_user) || 1,
        internal_reason: editForm.internal_reason.trim() || undefined
      });
      setIsEditModalOpen(false);
      setSuccessMessage(`Coupon "${selectedCoupon.code}" updated successfully.`);
      fetchData();
    } catch (err: any) {
      setEditModalError(err?.message || 'Failed to update coupon.');
    } finally {
      setIsSubmittingEdit(false);
    }
  };

  const handleToggleCouponStatus = async (coupon: Coupon) => {
    const newStatus = coupon.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    try {
      await apiClient.patch(`/admin/coupons/${coupon.id}`, {
        status: newStatus,
        internal_reason: `Super Admin toggled status to ${newStatus}`
      });
      setSuccessMessage(`Coupon "${coupon.code}" status changed to ${newStatus}.`);
      fetchData();
    } catch (err: any) {
      setError(err?.message || 'Failed to update coupon status.');
    }
  };

  const handleArchiveCoupon = async (coupon: Coupon) => {
    if (!confirm(`Are you sure you want to archive coupon "${coupon.code}"? It will no longer be redeemable.`)) return;
    try {
      await apiClient.patch(`/admin/coupons/${coupon.id}`, {
        status: 'ARCHIVED',
        internal_reason: 'Super Admin archived coupon'
      });
      setSuccessMessage(`Coupon "${coupon.code}" archived successfully.`);
      fetchData();
    } catch (err: any) {
      setError(err?.message || 'Failed to archive coupon.');
    }
  };

  const openRedemptionsModal = async (coupon: Coupon) => {
    setViewingCouponCode(coupon.code);
    setIsRedemptionsModalOpen(true);
    setIsLoadingRedemptions(true);
    try {
      const res = await apiClient.get<any[]>(`/admin/coupons/${coupon.id}/redemptions`);
      setRedemptionsList(res || []);
    } catch {
      setRedemptionsList([]);
    } finally {
      setIsLoadingRedemptions(false);
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

  const filteredCoupons = coupons.filter((c) => {
    const matchesSearch =
      c.code.toLowerCase().includes(couponSearch.toLowerCase()) ||
      c.name.toLowerCase().includes(couponSearch.toLowerCase());
    const matchesStatus = couponStatusFilter === 'ALL' || c.status === couponStatusFilter;
    return matchesSearch && matchesStatus;
  });

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
            Create, edit, activate/deactivate commercial discount vouchers, campaign allocations, and direct household entitlements.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <button
            onClick={() => {
              setCouponModalError(null);
              setIsCouponModalOpen(true);
            }}
            data-testid="create-coupon-btn"
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
            boxShadow: 'var(--shadow-subtle)',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px'
          }}
        >
          {/* Search & Status Filter Bar */}
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: '240px', backgroundColor: '#f8fafc', padding: '8px 14px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
              <Search size={16} color="#64748b" />
              <input
                type="text"
                placeholder="Search coupons by code or name..."
                value={couponSearch}
                onChange={(e) => setCouponSearch(e.target.value)}
                style={{ border: 'none', background: 'transparent', outline: 'none', width: '100%', fontSize: '13px' }}
              />
            </div>

            <select
              value={couponStatusFilter}
              onChange={(e) => setCouponStatusFilter(e.target.value)}
              style={{ padding: '8px 14px', borderRadius: '10px', border: '1px solid #e2e8f0', backgroundColor: '#ffffff', fontSize: '13px', fontWeight: 600 }}
            >
              <option value="ALL">All Statuses</option>
              <option value="ACTIVE">Active</option>
              <option value="INACTIVE">Inactive</option>
              <option value="EXPIRED">Expired</option>
              <option value="ARCHIVED">Archived</option>
            </select>
          </div>

          {filteredCoupons.length === 0 ? (
            <div style={{ padding: '32px', textAlign: 'center', color: 'var(--color-text-secondary, #64748b)', fontSize: '14px' }}>
              No coupons found matching your query. Click "+ Create Coupon" to generate a voucher.
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '14px' }}>
              {filteredCoupons.map((c) => (
                <div
                  key={c.id}
                  data-testid={`coupon-card-${c.id}`}
                  style={{
                    padding: '18px',
                    borderRadius: 'var(--radius-md, 12px)',
                    border: '1px solid var(--color-border-subtle, #cbd5e1)',
                    backgroundColor: '#ffffff',
                    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.05)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--color-text-primary, #0f172a)' }}>
                        {c.code}
                      </div>
                      <div style={{ fontSize: '13px', color: 'var(--color-text-secondary, #64748b)', marginTop: '2px' }}>
                        {c.name}
                      </div>
                    </div>
                    <AdminBadge variant={c.status === 'ACTIVE' ? 'success' : c.status === 'ARCHIVED' ? 'neutral' : 'warning'}>
                      {c.status}
                    </AdminBadge>
                  </div>

                  <div style={{ fontSize: '16px', fontWeight: 800, color: '#2563eb' }} data-testid={`coupon-discount-${c.id}`}>
                    {c.coupon_type === 'FREE_PERIOD'
                      ? `🎁 ${c.free_period_value} ${c.free_period_unit} 100% Free`
                      : c.coupon_type === 'PERCENTAGE_DISCOUNT'
                      ? `${c.discount_value}% Off`
                      : `$${c.discount_value} Off`}
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                    <div>
                      Country:{' '}
                      <strong>
                        {(() => {
                          if (!c.country || c.country.toUpperCase() === 'GLOBAL') {
                            return '🌍 Global (All)';
                          }
                          const codes = c.country.split(',').map((x) => x.trim().toUpperCase()).filter(Boolean);
                          return (
                            <span>
                              {codes.map((code) => {
                                const reg = regions.find((r) => r.country_code.toUpperCase() === code);
                                const flag = getCountryFlag(code);
                                const isDeactivated = reg && !reg.is_active;
                                return (
                                  <span key={code} style={{ display: 'inline-flex', alignItems: 'center', gap: '3px', marginRight: '6px' }}>
                                    <span>{flag}</span>
                                    <span>{reg ? `${reg.country_name} (${code})` : code}</span>
                                    {isDeactivated && (
                                      <span style={{ color: '#ef4444', fontSize: '11px', fontWeight: 700 }}>
                                        {' '}(⚠️ Deactivated in Master)
                                      </span>
                                    )}
                                  </span>
                                );
                              })}
                            </span>
                          );
                        })()}
                      </strong>
                    </div>
                    <div>Usage: <strong>{c.redemptions_count}</strong> {c.maximum_total_redemptions ? `/ ${c.maximum_total_redemptions}` : '(Unlimited)'}</div>
                    <div>Per User: <strong>{c.maximum_redemptions_per_user || 1}</strong></div>
                    <div>Valid Until: <strong>{formatDate(c.end_date)}</strong></div>
                  </div>

                  {/* Actions Row */}
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '6px', paddingTop: '10px', borderTop: '1px solid #e2e8f0' }}>
                    <button
                      onClick={() => openEditModal(c)}
                      data-testid={`edit-coupon-btn-${c.id}`}
                      style={{
                        padding: '8px 14px',
                        borderRadius: '8px',
                        border: '1px solid #2563eb',
                        backgroundColor: '#eff6ff',
                        color: '#1d4ed8',
                        fontSize: '12px',
                        fontWeight: 700,
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        minHeight: '36px'
                      }}
                    >
                      <Edit2 size={13} />
                      <span>Edit Coupon</span>
                    </button>

                    <button
                      onClick={() => handleToggleCouponStatus(c)}
                      style={{
                        padding: '6px 12px',
                        borderRadius: '6px',
                        border: '1px solid #cbd5e1',
                        backgroundColor: '#ffffff',
                        fontSize: '12px',
                        fontWeight: 600,
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}
                    >
                      <Power size={13} color={c.status === 'ACTIVE' ? '#ef4444' : '#10b981'} />
                      <span>{c.status === 'ACTIVE' ? 'Deactivate' : 'Activate'}</span>
                    </button>

                    <button
                      onClick={() => openRedemptionsModal(c)}
                      style={{
                        padding: '6px 12px',
                        borderRadius: '6px',
                        border: '1px solid #cbd5e1',
                        backgroundColor: '#ffffff',
                        fontSize: '12px',
                        fontWeight: 600,
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}
                    >
                      <Eye size={13} />
                      <span>Redemptions ({c.redemptions_count})</span>
                    </button>

                    {c.status !== 'ARCHIVED' && (
                      <button
                        onClick={() => handleArchiveCoupon(c)}
                        style={{
                          padding: '6px 12px',
                          borderRadius: '6px',
                          border: 'none',
                          backgroundColor: '#f1f5f9',
                          color: '#64748b',
                          fontSize: '12px',
                          fontWeight: 600,
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px'
                        }}
                      >
                        <Archive size={13} />
                        <span>Archive</span>
                      </button>
                    )}
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
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)' }}>
                      {camp.name} ({camp.code})
                    </span>
                    <AdminBadge variant={camp.status === 'ACTIVE' ? 'success' : 'neutral'}>{camp.status}</AdminBadge>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                    {camp.description || 'Targeted customer acquisition campaign.'}
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                    Redemptions: <strong>{camp.redemptions_count}</strong> {camp.maximum_redemptions ? `/ ${camp.maximum_redemptions}` : ''}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary, #94a3b8)' }}>
                    Valid: {formatDate(camp.start_date)} - {formatDate(camp.end_date)}
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
              No direct Super Admin grants issued. Click "Grant Entitlement" to issue direct VIP access to a workspace.
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
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
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)' }}>
                      Home: {g.home_id.slice(0, 8)}...
                    </span>
                    <AdminBadge variant={g.status === 'ACTIVE' ? 'success' : 'neutral'}>{g.status}</AdminBadge>
                  </div>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--status-in-stock, #10b981)' }}>
                    🎁 {g.duration_value} {g.duration_unit} Direct Entitlement
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                    Reason: <strong>{g.reason}</strong>
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
      <Modal isOpen={isCouponModalOpen} onClose={() => setIsCouponModalOpen(false)} title="Create New Coupon Code">
        {couponModalError && (
          <div style={{ padding: '12px', backgroundColor: 'var(--status-overdue-bg, #fef2f2)', border: '1px solid #fecaca', borderRadius: 'var(--radius-md, 10px)', color: 'var(--status-overdue, #ef4444)', fontSize: '13px', marginBottom: '16px' }}>
            {couponModalError}
          </div>
        )}

        <form onSubmit={handleCreateCoupon} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                Coupon Code *
              </label>
              <input
                type="text"
                required
                data-testid="create-coupon-code-input"
                placeholder="WELCOME6M"
                value={couponForm.code}
                onChange={(e) => setCouponForm({ ...couponForm, code: e.target.value })}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', textTransform: 'uppercase' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                Display Name *
              </label>
              <input
                type="text"
                required
                data-testid="create-coupon-name-input"
                placeholder="6 Months Free Early Adopter Access"
                value={couponForm.name}
                onChange={(e) => setCouponForm({ ...couponForm, name: e.target.value })}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
              />
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
              Description
            </label>
            <input
              type="text"
              placeholder="Commercial promotional code description"
              value={couponForm.description}
              onChange={(e) => setCouponForm({ ...couponForm, description: e.target.value })}
              style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                Discount Type
              </label>
              <select
                value={couponForm.coupon_type}
                onChange={(e) => setCouponForm({ ...couponForm, coupon_type: e.target.value })}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
              >
                <option value="PERCENTAGE_DISCOUNT">Percentage Discount (%)</option>
                <option value="FIXED_DISCOUNT">Fixed Cash Discount ($)</option>
                <option value="FREE_PERIOD">100% Free Period Access</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                {couponForm.coupon_type === 'PERCENTAGE_DISCOUNT' ? 'Discount Percentage (%) *' : 'Discount Value *'}
              </label>
              <input
                type="number"
                step="0.01"
                required
                data-testid="create-coupon-discount-input"
                value={couponForm.discount_value}
                onChange={(e) => setCouponForm({ ...couponForm, discount_value: e.target.value })}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                Valid Country / Countries *
              </label>
              <ControlledCountrySelector
                value={couponForm.country}
                onChange={(val) => setCouponForm({ ...couponForm, country: val })}
                regions={regions}
                testId="create-coupon-country-selector"
                inputTestId="create-coupon-country-input"
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                Max Total Redemptions
              </label>
              <input
                type="number"
                placeholder="Blank for unlimited"
                value={couponForm.maximum_total_redemptions}
                onChange={(e) => setCouponForm({ ...couponForm, maximum_total_redemptions: e.target.value })}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
              />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '12px' }}>
            <button
              type="button"
              onClick={() => setIsCouponModalOpen(false)}
              disabled={isSubmittingCoupon}
              style={{ padding: '10px 18px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', backgroundColor: 'transparent', fontSize: '14px', fontWeight: 600, cursor: 'pointer' }}
            >
              Cancel
            </button>
            <button
              type="submit"
              data-testid="create-coupon-submit-btn"
              disabled={isSubmittingCoupon}
              style={{ padding: '10px 20px', borderRadius: 'var(--radius-md, 10px)', border: 'none', backgroundColor: 'var(--color-primary-900, #0f172a)', color: 'var(--color-text-inverse, #ffffff)', fontSize: '14px', fontWeight: 600, cursor: isSubmittingCoupon ? 'not-allowed' : 'pointer' }}
            >
              {isSubmittingCoupon ? 'Creating...' : 'Create Coupon'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Edit Coupon */}
      <Modal isOpen={isEditModalOpen} onClose={() => setIsEditModalOpen(false)} title={`Edit Coupon: ${selectedCoupon?.code}`}>
        {editModalError && (
          <div style={{ padding: '12px', backgroundColor: 'var(--status-overdue-bg, #fef2f2)', border: '1px solid #fecaca', borderRadius: 'var(--radius-md, 10px)', color: 'var(--status-overdue, #ef4444)', fontSize: '13px', marginBottom: '16px' }}>
            {editModalError}
          </div>
        )}

        <form onSubmit={handleUpdateCoupon} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
              Coupon Name *
            </label>
            <input
              type="text"
              required
              value={editForm.name}
              onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
              style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
              Description
            </label>
            <input
              type="text"
              value={editForm.description}
              onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
              style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                Discount Type
              </label>
              <select
                value={editForm.coupon_type}
                onChange={(e) => setEditForm({ ...editForm, coupon_type: e.target.value })}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
              >
                <option value="PERCENTAGE_DISCOUNT">Percentage Discount (%)</option>
                <option value="FIXED_DISCOUNT">Fixed Cash Discount ($)</option>
                <option value="FREE_PERIOD">100% Free Period Access</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                Discount Percentage / Value *
              </label>
              <input
                type="number"
                step="0.01"
                required
                data-testid="edit-coupon-discount-input"
                value={editForm.discount_value}
                onChange={(e) => setEditForm({ ...editForm, discount_value: e.target.value })}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                Valid Country / Countries *
              </label>
              <ControlledCountrySelector
                value={editForm.country}
                onChange={(val) => setEditForm({ ...editForm, country: val })}
                regions={regions}
                isEdit={true}
                testId="edit-coupon-country-selector"
                inputTestId="edit-coupon-country-input"
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                Status
              </label>
              <select
                data-testid="edit-coupon-status-select"
                value={editForm.status}
                onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
              >
                <option value="ACTIVE">ACTIVE</option>
                <option value="INACTIVE">INACTIVE</option>
                <option value="EXPIRED">EXPIRED</option>
                <option value="ARCHIVED">ARCHIVED</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                Max Total Redemptions
              </label>
              <input
                type="number"
                placeholder="Blank for unlimited"
                data-testid="edit-coupon-max-redemptions-input"
                value={editForm.maximum_total_redemptions}
                onChange={(e) => setEditForm({ ...editForm, maximum_total_redemptions: e.target.value })}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                Max Per User
              </label>
              <input
                type="number"
                min="1"
                data-testid="edit-coupon-per-user-input"
                value={editForm.maximum_redemptions_per_user}
                onChange={(e) => setEditForm({ ...editForm, maximum_redemptions_per_user: parseInt(e.target.value) || 1 })}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
              />
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
              Operational Reason for Edit
            </label>
            <input
              type="text"
              placeholder="e.g. Adjusted campaign discount percentage for Q4 launch"
              data-testid="edit-coupon-reason-input"
              value={editForm.internal_reason}
              onChange={(e) => setEditForm({ ...editForm, internal_reason: e.target.value })}
              style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
            />
          </div>

          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '12px' }}>
            <button
              type="button"
              onClick={() => setIsEditModalOpen(false)}
              disabled={isSubmittingEdit}
              style={{ padding: '10px 18px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', backgroundColor: 'transparent', fontSize: '14px', fontWeight: 600, cursor: 'pointer' }}
            >
              Cancel
            </button>
            <button
              type="submit"
              data-testid="save-coupon-submit-btn"
              disabled={isSubmittingEdit}
              style={{ padding: '10px 20px', borderRadius: 'var(--radius-md, 10px)', border: 'none', backgroundColor: '#2563eb', color: '#ffffff', fontSize: '14px', fontWeight: 600, cursor: isSubmittingEdit ? 'not-allowed' : 'pointer' }}
            >
              {isSubmittingEdit ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Redemptions History */}
      <Modal isOpen={isRedemptionsModalOpen} onClose={() => setIsRedemptionsModalOpen(false)} title={`Redemptions Audit Log: ${viewingCouponCode}`}>
        {isLoadingRedemptions ? (
          <div style={{ padding: '32px', textAlign: 'center', color: '#64748b' }}>Loading redemptions log...</div>
        ) : redemptionsList.length === 0 ? (
          <div style={{ padding: '32px', textAlign: 'center', color: '#64748b' }}>No redemptions recorded for this coupon yet.</div>
        ) : (
          <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #e2e8f0', textAlign: 'left', color: '#64748b' }}>
                  <th style={{ padding: '8px' }}>Redeemed At</th>
                  <th style={{ padding: '8px' }}>User ID</th>
                  <th style={{ padding: '8px' }}>Home ID</th>
                  <th style={{ padding: '8px' }}>Discount Applied</th>
                </tr>
              </thead>
              <tbody>
                {redemptionsList.map((r) => (
                  <tr key={r.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '8px' }}>{formatDate(r.redeemed_at)}</td>
                    <td style={{ padding: '8px', fontFamily: 'monospace' }}>{r.user_id?.slice(0, 8)}...</td>
                    <td style={{ padding: '8px', fontFamily: 'monospace' }}>{r.home_id?.slice(0, 8)}...</td>
                    <td style={{ padding: '8px', fontWeight: 600, color: '#10b981' }}>
                      {r.discount_amount_applied ? `$${r.discount_amount_applied}` : `${r.free_days_granted} Free Days`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Modal>

      {/* Modal: Direct Grant */}
      <Modal isOpen={isGrantModalOpen} onClose={() => setIsGrantModalOpen(false)} title="Issue Direct Entitlement Grant">
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
              style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
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
                style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                Unit
              </label>
              <select
                value={grantForm.duration_unit}
                onChange={(e) => setGrantForm({ ...grantForm, duration_unit: e.target.value })}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
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
              style={{ padding: '10px 18px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', backgroundColor: 'transparent', fontSize: '14px', fontWeight: 600, cursor: 'pointer' }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmittingGrant}
              style={{ padding: '10px 20px', borderRadius: 'var(--radius-md, 10px)', border: 'none', backgroundColor: 'var(--status-in-stock, #10b981)', color: 'var(--color-text-inverse, #ffffff)', fontSize: '14px', fontWeight: 600, cursor: isSubmittingGrant ? 'not-allowed' : 'pointer' }}
            >
              {isSubmittingGrant ? 'Issuing...' : 'Grant Entitlement'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
