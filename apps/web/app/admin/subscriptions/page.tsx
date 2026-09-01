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
  ExternalLink,
  CreditCard,
  DollarSign,
  Activity,
  Coins,
  Calendar
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';
import { AdminBadge } from '../components/AdminBadge';
import {
  SubscriptionPlan,
  SubscriptionFeature,
  Promotion,
  AdminSubscriberListItem,
  PaymentTransaction,
  SubscriptionAnalytics,
  SubscriptionCredit
} from '../types';

export default function AdminSubscriptionsPage() {
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [features, setFeatures] = useState<SubscriptionFeature[]>([]);
  const [promotions, setPromotions] = useState<Promotion[]>([]);
  const [subscribers, setSubscribers] = useState<AdminSubscriberListItem[]>([]);
  const [transactions, setTransactions] = useState<PaymentTransaction[]>([]);
  const [credits, setCredits] = useState<SubscriptionCredit[]>([]);
  const [analytics, setAnalytics] = useState<SubscriptionAnalytics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Tab State
  const [activeTab, setActiveTab] = useState<'plans' | 'subscribers' | 'transactions' | 'promotions' | 'features' | 'credits'>('plans');

  // Credit Filter State
  const [creditSearch, setCreditSearch] = useState('');
  const [creditStatusFilter, setCreditStatusFilter] = useState('ALL');
  const [creditCurrencyFilter, setCreditCurrencyFilter] = useState('ALL');

  // Grant Credit Modal
  const [isGrantCreditModalOpen, setIsGrantCreditModalOpen] = useState(false);
  const [isSubmittingCredit, setIsSubmittingCredit] = useState(false);
  const [grantCreditForm, setGrantCreditForm] = useState({
    user_id: '',
    home_id: '',
    amount: '1000.00',
    currency: 'INR',
    credit_type: 'ADMIN_GRANT',
    reason: 'Customer compensation voucher',
    expires_in_days: '90',
    description: ''
  });
  const [grantCreditError, setGrantCreditError] = useState<string | null>(null);

  // Grant Subscription Modal
  const [isGrantSubModalOpen, setIsGrantSubModalOpen] = useState(false);
  const [isSubmittingSub, setIsSubmittingSub] = useState(false);
  const [grantSubForm, setGrantSubForm] = useState({
    home_id: '',
    user_id: '',
    plan_id: '',
    duration_days: 365,
    paid_member_seats: 0,
    reason: 'Admin direct grant'
  });
  const [grantSubError, setGrantSubError] = useState<string | null>(null);

  // Override Period Modal
  const [isOverrideModalOpen, setIsOverrideModalOpen] = useState(false);
  const [overrideSubId, setOverrideSubId] = useState('');
  const [overrideDate, setOverrideDate] = useState('');
  const [overrideReason, setOverrideReason] = useState('VIP pilot extension');
  const [isSubmittingOverride, setIsSubmittingOverride] = useState(false);

  // Plan Creation Modal
  const [isPlanModalOpen, setIsPlanModalOpen] = useState(false);
  const [isSubmittingPlan, setIsSubmittingPlan] = useState(false);
  const [planForm, setPlanForm] = useState({
    name: '',
    code: '',
    description: '',
    plan_type: 'HOME',
    included_members: 1,
    maximum_members: 10,
    max_homes: 5,
    additional_member_allowed: true,
    introductory_enabled: true,
    introductory_duration_days: 365,
    introductory_price: '0.00'
  });
  const [planModalError, setPlanModalError] = useState<string | null>(null);

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

  const fetchData = async (targetTab: string = activeTab) => {
    setIsLoading(true);
    setError(null);
    try {
      // Always load analytics summary in background
      apiClient.get<SubscriptionAnalytics>('/admin/subscriptions/analytics')
        .then((data) => setAnalytics(data))
        .catch(() => {});

      if (targetTab === 'plans' || targetTab === 'features') {
        const [plansData, featuresData] = await Promise.all([
          apiClient.get<SubscriptionPlan[]>('/admin/subscriptions/plans'),
          apiClient.get<SubscriptionFeature[]>('/admin/subscriptions/features')
        ]);
        setPlans(plansData || []);
        setFeatures(featuresData || []);
      } else if (targetTab === 'promotions') {
        const promotionsData = await apiClient.get<Promotion[]>('/admin/subscriptions/promotions');
        setPromotions(promotionsData || []);
      } else if (targetTab === 'subscribers') {
        const subscribersData = await apiClient.get<AdminSubscriberListItem[]>('/admin/subscriptions/subscribers');
        setSubscribers(subscribersData || []);
      } else if (targetTab === 'transactions') {
        const txData = await apiClient.get<PaymentTransaction[]>('/admin/subscriptions/transactions');
        setTransactions(txData || []);
      } else if (targetTab === 'credits') {
        const creditsData = await apiClient.get<SubscriptionCredit[]>('/admin/subscriptions/credits');
        setCredits(creditsData || []);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch subscription configuration.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData(activeTab);
  }, [activeTab]);

  const handleCreatePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmittingPlan(true);
    setPlanModalError(null);
    try {
      await apiClient.post('/admin/subscriptions/plans', {
        name: planForm.name.trim(),
        code: planForm.code.toUpperCase().trim(),
        description: planForm.description.trim() || undefined,
        plan_type: planForm.plan_type.toUpperCase(),
        included_members: Number(planForm.included_members) || 1,
        maximum_members: Number(planForm.maximum_members) || 10,
        max_homes: Number(planForm.max_homes) || 5,
        additional_member_allowed: planForm.additional_member_allowed,
        introductory_enabled: planForm.introductory_enabled,
        introductory_duration_days: Number(planForm.introductory_duration_days) || 365,
        introductory_price: parseFloat(planForm.introductory_price) || 0
      });
      setIsPlanModalOpen(false);
      setSuccessMessage(`Subscription plan "${planForm.name}" created successfully.`);
      fetchData('plans');
    } catch (err: any) {
      setPlanModalError(err?.message || 'Failed to create subscription plan.');
    } finally {
      setIsSubmittingPlan(false);
    }
  };

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
      fetchData('promotions');
    } catch (err: any) {
      setPromoModalError(err?.message || 'Failed to create promotion.');
    } finally {
      setIsSubmittingPromo(false);
    }
  };

  const handleGrantCredit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmittingCredit(true);
    setGrantCreditError(null);
    try {
      await apiClient.post('/admin/subscriptions/credits/grant', {
        user_id: grantCreditForm.user_id.trim(),
        home_id: grantCreditForm.home_id.trim() || undefined,
        amount: parseFloat(grantCreditForm.amount) || 0,
        currency: grantCreditForm.currency.toUpperCase().trim(),
        credit_type: grantCreditForm.credit_type,
        reason: grantCreditForm.reason.trim(),
        expires_in_days: grantCreditForm.expires_in_days ? parseInt(grantCreditForm.expires_in_days) : undefined,
        description: grantCreditForm.description.trim() || undefined
      });
      setIsGrantCreditModalOpen(false);
      setSuccessMessage(`Successfully granted ${grantCreditForm.currency.toUpperCase()} ${grantCreditForm.amount} credit.`);
      fetchData('credits');
    } catch (err: any) {
      setGrantCreditError(err?.message || 'Failed to grant subscription credit.');
    } finally {
      setIsSubmittingCredit(false);
    }
  };

  const handleRevokeCredit = async (creditId: string) => {
    const reason = window.prompt('Enter reason for revoking this credit:');
    if (!reason) return;
    try {
      await apiClient.post(`/admin/subscriptions/credits/${creditId}/revoke`, { reason: reason.trim() });
      setSuccessMessage('Subscription credit has been revoked.');
      fetchData('credits');
    } catch (err: any) {
      setError(err?.message || 'Failed to revoke credit.');
    }
  };

  const handleGrantSubscription = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmittingSub(true);
    setGrantSubError(null);
    try {
      await apiClient.post('/admin/subscriptions/grant', {
        home_id: grantSubForm.home_id.trim(),
        user_id: grantSubForm.user_id.trim() || undefined,
        plan_id: grantSubForm.plan_id.trim(),
        duration_days: Number(grantSubForm.duration_days) || 365,
        paid_member_seats: Number(grantSubForm.paid_member_seats) || 0,
        reason: grantSubForm.reason.trim()
      });
      setIsGrantSubModalOpen(false);
      setSuccessMessage('Subscription successfully granted to workspace.');
      fetchData('subscribers');
    } catch (err: any) {
      setGrantSubError(err?.message || 'Failed to grant subscription.');
    } finally {
      setIsSubmittingSub(false);
    }
  };

  const handleOverridePeriod = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!overrideSubId || !overrideDate) return;
    setIsSubmittingOverride(true);
    try {
      await apiClient.patch(`/admin/subscriptions/${overrideSubId}/override-period`, {
        current_period_ends_at: new Date(overrideDate).toISOString(),
        reason: overrideReason.trim()
      });
      setIsOverrideModalOpen(false);
      setSuccessMessage('Subscription period has been updated.');
      fetchData('subscribers');
    } catch (err: any) {
      setError(err?.message || 'Failed to override subscription period.');
    } finally {
      setIsSubmittingOverride(false);
    }
  };

  const handleCancelSubscription = async (subId: string) => {
    const reason = window.prompt('Enter reason for cancelling this subscription:');
    if (!reason) return;
    try {
      await apiClient.post(`/admin/subscriptions/${subId}/cancel`, { reason: reason.trim() });
      setSuccessMessage('Subscription cancelled. Tenant workspace remains intact.');
      fetchData('subscribers');
    } catch (err: any) {
      setError(err?.message || 'Failed to cancel subscription.');
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
            Subscription & Monetization Console
          </h1>
          <p
            style={{
              fontSize: '14px',
              color: 'var(--color-text-secondary, #64748b)',
              marginTop: '4px'
            }}
          >
            Manage subscription plans, multi-home entitlements, regional prices, transaction audit trails, and promotions.
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
            onClick={() => fetchData(activeTab)}
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

      {/* Analytics Summary Row */}
      {analytics && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
          <div style={{ padding: '16px', borderRadius: 'var(--radius-lg, 16px)', backgroundColor: 'var(--color-surface-card, #ffffff)', border: '1px solid var(--color-border-subtle, #e2e8f0)', boxShadow: 'var(--shadow-subtle)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-text-secondary, #64748b)', fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>
              <DollarSign size={16} color="var(--color-primary-900, #0f172a)" />
              <span>Total Revenue</span>
            </div>
            <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--color-primary-900, #0f172a)', marginTop: '6px' }}>
              ${Number(analytics.total_revenue).toFixed(2)}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--color-text-secondary, #64748b)', marginTop: '2px' }}>
              Avg Order: ${Number(analytics.average_order_value).toFixed(2)}
            </div>
          </div>

          <div style={{ padding: '16px', borderRadius: 'var(--radius-lg, 16px)', backgroundColor: 'var(--color-surface-card, #ffffff)', border: '1px solid var(--color-border-subtle, #e2e8f0)', boxShadow: 'var(--shadow-subtle)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-text-secondary, #64748b)', fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>
              <Users size={16} color="var(--status-in-stock, #10b981)" />
              <span>Active Subscribers</span>
            </div>
            <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--status-in-stock, #10b981)', marginTop: '6px' }}>
              {analytics.active_subscribers}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--color-text-secondary, #64748b)', marginTop: '2px' }}>
              + {analytics.trial_subscribers} on free intro trial
            </div>
          </div>

          <div style={{ padding: '16px', borderRadius: 'var(--radius-lg, 16px)', backgroundColor: 'var(--color-surface-card, #ffffff)', border: '1px solid var(--color-border-subtle, #e2e8f0)', boxShadow: 'var(--shadow-subtle)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-text-secondary, #64748b)', fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>
              <CreditCard size={16} color="var(--color-accent-warm, #f97316)" />
              <span>Total Transactions</span>
            </div>
            <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--color-primary-900, #0f172a)', marginTop: '6px' }}>
              {analytics.total_transactions}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--color-text-secondary, #64748b)', marginTop: '2px' }}>
              Settled payment intents
            </div>
          </div>

          <div style={{ padding: '16px', borderRadius: 'var(--radius-lg, 16px)', backgroundColor: 'var(--color-surface-card, #ffffff)', border: '1px solid var(--color-border-subtle, #e2e8f0)', boxShadow: 'var(--shadow-subtle)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-text-secondary, #64748b)', fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>
              <Activity size={16} color="var(--status-overdue, #ef4444)" />
              <span>Churn / Past Due</span>
            </div>
            <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--color-text-primary, #0f172a)', marginTop: '6px' }}>
              {analytics.past_due_subscribers + analytics.cancelled_subscribers}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--color-text-secondary, #64748b)', marginTop: '2px' }}>
              {analytics.past_due_subscribers} past due, {analytics.cancelled_subscribers} cancelled
            </div>
          </div>
        </div>
      )}

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
          <span>Subscription Plans ({plans.length})</span>
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
          onClick={() => setActiveTab('transactions')}
          style={{
            padding: '10px 16px',
            borderRadius: 'var(--radius-md, 10px)',
            border: 'none',
            backgroundColor: activeTab === 'transactions' ? 'var(--color-primary-900, #0f172a)' : 'transparent',
            color: activeTab === 'transactions' ? 'var(--color-text-inverse, #ffffff)' : 'var(--color-text-secondary, #64748b)',
            fontSize: '13px',
            fontWeight: 600,
            cursor: 'pointer',
            minHeight: '44px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          <CreditCard size={16} />
          <span>Payment Transactions ({transactions.length})</span>
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

        <button
          onClick={() => setActiveTab('credits')}
          style={{
            padding: '10px 16px',
            borderRadius: 'var(--radius-md, 10px)',
            border: 'none',
            backgroundColor: activeTab === 'credits' ? 'var(--color-primary-900, #0f172a)' : 'transparent',
            color: activeTab === 'credits' ? 'var(--color-text-inverse, #ffffff)' : 'var(--color-text-secondary, #64748b)',
            fontSize: '13px',
            fontWeight: 600,
            cursor: 'pointer',
            minHeight: '44px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          <Coins size={16} />
          <span>Subscription Credits ({credits.length})</span>
        </button>
      </div>

      {/* Tab: Plans & Regional Prices */}
      {activeTab === 'plans' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 700, margin: 0 }}>Configured Subscription Plans</h2>
            <button
              onClick={() => {
                setPlanModalError(null);
                setIsPlanModalOpen(true);
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
              <span>Create Subscription Plan</span>
            </button>
          </div>

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
                    <AdminBadge variant="info">Max {p.max_homes ?? 10} Homes</AdminBadge>
                  </div>
                  <p style={{ fontSize: '13px', color: 'var(--color-text-secondary, #64748b)', margin: '4px 0 0' }}>
                    {p.description || 'Full digital operating system subscription plan.'}
                  </p>
                </div>

                <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)', textAlign: 'right' }}>
                  <div>Home Capacity: <strong>{p.max_homes ?? 10} Households</strong></div>
                  <div>Included Members: <strong>{p.included_members}</strong> (Max: {p.maximum_members || 'Unlimited'})</div>
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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid var(--color-border-subtle, #e2e8f0)', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h2 style={{ fontSize: '16px', fontWeight: 700, margin: 0, color: 'var(--color-text-primary, #0f172a)' }}>
                Active Subscribers & Workspaces
              </h2>
              <p style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)', margin: '2px 0 0' }}>
                All commercial subscriptions binding users and tenant homes.
              </p>
            </div>
            <button
              onClick={() => {
                setGrantSubError(null);
                setIsGrantSubModalOpen(true);
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
              <span>Grant Subscription</span>
            </button>
          </div>

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
                    <th style={{ padding: '12px 16px', textAlign: 'right' }}>Actions</th>
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
                        <div style={{ display: 'inline-flex', gap: '6px', alignItems: 'center' }}>
                          <button
                            onClick={() => {
                              setOverrideSubId(s.id);
                              setOverrideDate(s.renewal_date ? new Date(s.renewal_date).toISOString().split('T')[0] : '');
                              setIsOverrideModalOpen(true);
                            }}
                            title="Override Period / Expiry"
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              padding: '6px 10px',
                              borderRadius: 'var(--radius-md, 8px)',
                              border: '1px solid var(--color-border-subtle, #e2e8f0)',
                              backgroundColor: 'var(--color-surface-subtle, #f1f5f9)',
                              fontSize: '12px',
                              fontWeight: 600,
                              color: 'var(--color-text-primary, #0f172a)',
                              cursor: 'pointer',
                              minHeight: '32px'
                            }}
                          >
                            <Calendar size={12} style={{ marginRight: '4px' }} />
                            <span>Override</span>
                          </button>

                          {s.status === 'ACTIVE' && (
                            <button
                              onClick={() => handleCancelSubscription(s.id)}
                              title="Cancel Subscription (Tenant Home Preserved)"
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                padding: '6px 10px',
                                borderRadius: 'var(--radius-md, 8px)',
                                border: '1px solid #fecaca',
                                backgroundColor: 'var(--status-overdue-bg, #fef2f2)',
                                fontSize: '12px',
                                fontWeight: 600,
                                color: 'var(--status-overdue, #ef4444)',
                                cursor: 'pointer',
                                minHeight: '32px'
                              }}
                            >
                              <span>Cancel</span>
                            </button>
                          )}

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
                              minHeight: '32px',
                              textDecoration: 'none'
                            }}
                          >
                            <span>Inspect</span>
                            <ExternalLink size={12} />
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab: Payment Transactions */}
      {activeTab === 'transactions' && (
        <div
          style={{
            backgroundColor: 'var(--color-surface-card, #ffffff)',
            borderRadius: 'var(--radius-lg, 16px)',
            border: '1px solid var(--color-border-subtle, #e2e8f0)',
            overflow: 'hidden',
            boxShadow: 'var(--shadow-subtle)'
          }}
        >
          {transactions.length === 0 ? (
            <div style={{ padding: '48px 24px', textAlign: 'center', color: 'var(--color-text-secondary, #64748b)', fontSize: '14px' }}>
              No financial transaction records recorded yet.
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
                    <th style={{ padding: '12px 16px' }}>Transaction ID</th>
                    <th style={{ padding: '12px 16px' }}>User / Customer</th>
                    <th style={{ padding: '12px 16px' }}>Plan Purchased</th>
                    <th style={{ padding: '12px 16px' }}>Amount</th>
                    <th style={{ padding: '12px 16px' }}>Discount</th>
                    <th style={{ padding: '12px 16px' }}>Final Paid</th>
                    <th style={{ padding: '12px 16px' }}>Provider</th>
                    <th style={{ padding: '12px 16px' }}>Status</th>
                    <th style={{ padding: '12px 16px' }}>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((tx) => (
                    <tr
                      key={tx.id}
                      style={{
                        borderBottom: '1px solid var(--color-border-subtle, #e2e8f0)',
                        transition: 'background-color 0.15s ease'
                      }}
                    >
                      <td style={{ padding: '12px 16px', fontFamily: 'monospace', fontSize: '12px' }}>
                        {tx.id.slice(0, 8)}...
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        {tx.user_email || tx.user_id.slice(0, 8)}
                      </td>
                      <td style={{ padding: '12px 16px', fontWeight: 600 }}>
                        {tx.plan_name}
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        {tx.currency} {Number(tx.amount).toFixed(2)}
                      </td>
                      <td style={{ padding: '12px 16px', color: 'var(--status-in-stock, #10b981)' }}>
                        -{tx.currency} {Number(tx.discount_amount).toFixed(2)}
                      </td>
                      <td style={{ padding: '12px 16px', fontWeight: 700, color: 'var(--color-primary-900, #0f172a)' }}>
                        {tx.currency} {Number(tx.final_amount).toFixed(2)}
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <AdminBadge variant="neutral">{tx.provider}</AdminBadge>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <AdminBadge variant={tx.status === 'SUCCESS' ? 'success' : tx.status === 'PENDING' ? 'warning' : 'danger'}>
                          {tx.status}
                        </AdminBadge>
                      </td>
                      <td style={{ padding: '12px 16px', color: 'var(--color-text-secondary, #64748b)', fontSize: '12px' }}>
                        {new Date(tx.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab: Promotions */}
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

      {/* Tab: Feature Flags */}
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

      {/* Tab: Subscription Credits */}
      {activeTab === 'credits' && (
        <div
          style={{
            backgroundColor: 'var(--color-surface-card, #ffffff)',
            borderRadius: 'var(--radius-lg, 16px)',
            border: '1px solid var(--color-border-subtle, #e2e8f0)',
            overflow: 'hidden',
            boxShadow: 'var(--shadow-subtle)'
          }}
        >
          {/* Header & Controls */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid var(--color-border-subtle, #e2e8f0)', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h2 style={{ fontSize: '16px', fontWeight: 700, margin: 0, color: 'var(--color-text-primary, #0f172a)' }}>
                Subscription Credit Ledger
              </h2>
              <p style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)', margin: '2px 0 0' }}>
                Authoritative reusable subscription value ledger. Fully audited with currency separation.
              </p>
            </div>

            <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
              <input
                type="text"
                placeholder="Search email, name, ref..."
                value={creditSearch}
                onChange={(e) => setCreditSearch(e.target.value)}
                style={{
                  padding: '8px 12px',
                  borderRadius: 'var(--radius-md, 8px)',
                  border: '1px solid var(--color-border-subtle, #e2e8f0)',
                  fontSize: '13px',
                  minWidth: '200px'
                }}
              />

              <select
                value={creditStatusFilter}
                onChange={(e) => setCreditStatusFilter(e.target.value)}
                style={{
                  padding: '8px 12px',
                  borderRadius: 'var(--radius-md, 8px)',
                  border: '1px solid var(--color-border-subtle, #e2e8f0)',
                  fontSize: '13px'
                }}
              >
                <option value="ALL">All Statuses</option>
                <option value="AVAILABLE">Available</option>
                <option value="PARTIALLY_USED">Partially Used</option>
                <option value="REDEEMED">Redeemed</option>
                <option value="EXPIRED">Expired</option>
                <option value="CANCELLED">Cancelled</option>
              </select>

              <select
                value={creditCurrencyFilter}
                onChange={(e) => setCreditCurrencyFilter(e.target.value)}
                style={{
                  padding: '8px 12px',
                  borderRadius: 'var(--radius-md, 8px)',
                  border: '1px solid var(--color-border-subtle, #e2e8f0)',
                  fontSize: '13px'
                }}
              >
                <option value="ALL">All Currencies</option>
                <option value="USD">USD</option>
                <option value="INR">INR</option>
                <option value="AED">AED</option>
                <option value="GBP">GBP</option>
                <option value="EUR">EUR</option>
              </select>

              <button
                onClick={() => {
                  setGrantCreditError(null);
                  setIsGrantCreditModalOpen(true);
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
                <span>Grant Credit</span>
              </button>
            </div>
          </div>

          {/* Table */}
          {credits.length === 0 ? (
            <div style={{ padding: '48px 24px', textAlign: 'center', color: 'var(--color-text-secondary, #64748b)', fontSize: '14px' }}>
              No subscription credits found in the ledger.
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
                    <th style={{ padding: '12px 16px' }}>User / Account</th>
                    <th style={{ padding: '12px 16px' }}>Original Amount</th>
                    <th style={{ padding: '12px 16px' }}>Remaining Balance</th>
                    <th style={{ padding: '12px 16px' }}>Currency</th>
                    <th style={{ padding: '12px 16px' }}>Type</th>
                    <th style={{ padding: '12px 16px' }}>Status</th>
                    <th style={{ padding: '12px 16px' }}>Reference / Reason</th>
                    <th style={{ padding: '12px 16px' }}>Expires</th>
                    <th style={{ padding: '12px 16px', textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {credits
                    .filter((c) => {
                      if (creditStatusFilter !== 'ALL' && c.status !== creditStatusFilter) return false;
                      if (creditCurrencyFilter !== 'ALL' && c.currency !== creditCurrencyFilter) return false;
                      if (creditSearch) {
                        const term = creditSearch.toLowerCase();
                        const matchEmail = (c.user_email || '').toLowerCase().includes(term);
                        const matchName = (c.user_name || '').toLowerCase().includes(term);
                        const matchRef = (c.reference || '').toLowerCase().includes(term);
                        const matchDesc = (c.description || '').toLowerCase().includes(term);
                        if (!matchEmail && !matchName && !matchRef && !matchDesc) return false;
                      }
                      return true;
                    })
                    .map((c) => (
                      <tr
                        key={c.id}
                        style={{
                          borderBottom: '1px solid var(--color-border-subtle, #e2e8f0)',
                          transition: 'background-color 0.15s ease'
                        }}
                      >
                        <td style={{ padding: '12px 16px' }}>
                          <div style={{ fontWeight: 600, color: 'var(--color-text-primary, #0f172a)' }}>
                            {c.user_name || 'User'}
                          </div>
                          <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                            {c.user_email || c.user_id.slice(0, 8)}
                          </div>
                        </td>

                        <td style={{ padding: '12px 16px', fontWeight: 600 }}>
                          {c.currency} {Number(c.amount).toFixed(2)}
                        </td>

                        <td style={{ padding: '12px 16px', fontWeight: 700, color: Number(c.remaining_amount) > 0 ? 'var(--status-in-stock, #10b981)' : 'var(--color-text-secondary, #64748b)' }}>
                          {c.currency} {Number(c.remaining_amount).toFixed(2)}
                        </td>

                        <td style={{ padding: '12px 16px' }}>
                          <AdminBadge variant="neutral">{c.currency}</AdminBadge>
                        </td>

                        <td style={{ padding: '12px 16px' }}>
                          <AdminBadge variant="purple">{c.credit_type}</AdminBadge>
                        </td>

                        <td style={{ padding: '12px 16px' }}>
                          <AdminBadge
                            variant={
                              c.status === 'AVAILABLE'
                                ? 'success'
                                : c.status === 'PARTIALLY_USED'
                                ? 'info'
                                : c.status === 'REDEEMED'
                                ? 'neutral'
                                : 'danger'
                            }
                          >
                            {c.status}
                          </AdminBadge>
                        </td>

                        <td style={{ padding: '12px 16px' }}>
                          <div style={{ fontSize: '12px', color: 'var(--color-text-primary, #0f172a)' }}>
                            {c.description || c.reference || '—'}
                          </div>
                          <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary, #94a3b8)' }}>
                            {c.reference ? `Ref: ${c.reference}` : ''}
                          </div>
                        </td>

                        <td style={{ padding: '12px 16px', color: 'var(--color-text-secondary, #64748b)', fontSize: '12px' }}>
                          {c.expires_at ? new Date(c.expires_at).toLocaleDateString() : 'Never'}
                        </td>

                        <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                          {(c.status === 'AVAILABLE' || c.status === 'PARTIALLY_USED') && Number(c.remaining_amount) > 0 && (
                            <button
                              onClick={() => handleRevokeCredit(c.id)}
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                padding: '6px 10px',
                                borderRadius: 'var(--radius-md, 8px)',
                                border: '1px solid #fecaca',
                                backgroundColor: 'var(--status-overdue-bg, #fef2f2)',
                                fontSize: '12px',
                                fontWeight: 600,
                                color: 'var(--status-overdue, #ef4444)',
                                cursor: 'pointer',
                                minHeight: '30px'
                              }}
                            >
                              <span>Revoke</span>
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Modal: Create Plan */}
      {isPlanModalOpen && (
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
            if (e.target === e.currentTarget && !isSubmittingPlan) setIsPlanModalOpen(false);
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
              position: 'relative'
            }}
          >
            <button
              onClick={() => setIsPlanModalOpen(false)}
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
              Create Subscription Plan
            </h2>

            {planModalError && (
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
                {planModalError}
              </div>
            )}

            <form onSubmit={handleCreatePlan} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                    Plan Name *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="Ozhzo Multi-Home Pro"
                    value={planForm.name}
                    onChange={(e) => setPlanForm({ ...planForm, name: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                    Plan Code *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="MULTI_HOME_PRO"
                    value={planForm.code}
                    onChange={(e) => setPlanForm({ ...planForm, code: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                  Description
                </label>
                <textarea
                  placeholder="Plan description and features..."
                  value={planForm.description}
                  onChange={(e) => setPlanForm({ ...planForm, description: e.target.value })}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '13px', minHeight: '70px', resize: 'vertical' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                    Max Allowed Homes (Entitlement) *
                  </label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={planForm.max_homes}
                    onChange={(e) => setPlanForm({ ...planForm, max_homes: parseInt(e.target.value) || 1 })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                    Included Family Members *
                  </label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={planForm.included_members}
                    onChange={(e) => setPlanForm({ ...planForm, included_members: parseInt(e.target.value) || 1 })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '12px' }}>
                <button
                  type="button"
                  onClick={() => setIsPlanModalOpen(false)}
                  disabled={isSubmittingPlan}
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
                  disabled={isSubmittingPlan}
                  style={{
                    padding: '10px 20px',
                    borderRadius: 'var(--radius-md, 10px)',
                    border: 'none',
                    backgroundColor: 'var(--color-primary-900, #0f172a)',
                    color: 'var(--color-text-inverse, #ffffff)',
                    fontSize: '14px',
                    fontWeight: 600,
                    cursor: isSubmittingPlan ? 'not-allowed' : 'pointer',
                    minHeight: '44px'
                  }}
                >
                  {isSubmittingPlan ? 'Creating Plan...' : 'Create Plan'}
                </button>
              </div>
            </form>
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

      {/* Modal: Grant Credit */}
      {isGrantCreditModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.6)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 50,
            padding: '16px'
          }}
        >
          <div
            style={{
              backgroundColor: 'var(--color-surface-card, #ffffff)',
              borderRadius: 'var(--radius-lg, 16px)',
              maxWidth: '520px',
              width: '100%',
              padding: '24px',
              boxShadow: 'var(--shadow-raised, 0 20px 25px -5px rgba(0, 0, 0, 0.1))',
              maxHeight: '90vh',
              overflowY: 'auto'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Coins size={20} color="var(--color-primary-900, #0f172a)" />
                <h3 style={{ fontSize: '18px', fontWeight: 700, margin: 0 }}>Grant Subscription Credit</h3>
              </div>
              <button
                onClick={() => setIsGrantCreditModalOpen(false)}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: '4px' }}
              >
                <X size={20} color="var(--color-text-secondary, #64748b)" />
              </button>
            </div>

            {grantCreditError && (
              <div style={{ padding: '12px', backgroundColor: 'var(--status-overdue-bg, #fef2f2)', border: '1px solid #fecaca', borderRadius: 'var(--radius-md, 8px)', color: 'var(--status-overdue, #ef4444)', fontSize: '13px', marginBottom: '16px' }}>
                {grantCreditError}
              </div>
            )}

            <form onSubmit={handleGrantCredit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                  Target User ID (UUID) *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000"
                  value={grantCreditForm.user_id}
                  onChange={(e) => setGrantCreditForm({ ...grantCreditForm, user_id: e.target.value })}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                    Credit Amount *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={grantCreditForm.amount}
                    onChange={(e) => setGrantCreditForm({ ...grantCreditForm, amount: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                    Currency *
                  </label>
                  <select
                    value={grantCreditForm.currency}
                    onChange={(e) => setGrantCreditForm({ ...grantCreditForm, currency: e.target.value })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                  >
                    <option value="INR">INR (₹)</option>
                    <option value="USD">USD ($)</option>
                    <option value="AED">AED (AED)</option>
                    <option value="GBP">GBP (£)</option>
                    <option value="EUR">EUR (€)</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                  Credit Type *
                </label>
                <select
                  value={grantCreditForm.credit_type}
                  onChange={(e) => setGrantCreditForm({ ...grantCreditForm, credit_type: e.target.value })}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                >
                  <option value="ADMIN_GRANT">Super Admin Grant</option>
                  <option value="COMPENSATION">Customer Service Compensation</option>
                  <option value="PROMOTIONAL">Marketing Goodwill</option>
                  <option value="RESERVATION_REFUND">Cancelled Reservation Credit</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                  Audit Reason (Authoritative & Traceable) *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. VIP onboarding gift or service restoration compensation"
                  value={grantCreditForm.reason}
                  onChange={(e) => setGrantCreditForm({ ...grantCreditForm, reason: e.target.value })}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                  Expires In Days (Leave empty for no expiry)
                </label>
                <input
                  type="number"
                  placeholder="e.g. 90"
                  value={grantCreditForm.expires_in_days}
                  onChange={(e) => setGrantCreditForm({ ...grantCreditForm, expires_in_days: e.target.value })}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                />
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '12px' }}>
                <button
                  type="button"
                  onClick={() => setIsGrantCreditModalOpen(false)}
                  disabled={isSubmittingCredit}
                  style={{ padding: '10px 18px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', backgroundColor: 'transparent', fontSize: '14px', fontWeight: 600, cursor: 'pointer', minHeight: '44px' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingCredit}
                  style={{ padding: '10px 20px', borderRadius: 'var(--radius-md, 10px)', border: 'none', backgroundColor: 'var(--color-primary-900, #0f172a)', color: 'var(--color-text-inverse, #ffffff)', fontSize: '14px', fontWeight: 600, cursor: isSubmittingCredit ? 'not-allowed' : 'pointer', minHeight: '44px' }}
                >
                  {isSubmittingCredit ? 'Granting...' : 'Issue Credit'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Grant Subscription */}
      {isGrantSubModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.6)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 50,
            padding: '16px'
          }}
        >
          <div
            style={{
              backgroundColor: 'var(--color-surface-card, #ffffff)',
              borderRadius: 'var(--radius-lg, 16px)',
              maxWidth: '520px',
              width: '100%',
              padding: '24px',
              boxShadow: 'var(--shadow-raised, 0 20px 25px -5px rgba(0, 0, 0, 0.1))',
              maxHeight: '90vh',
              overflowY: 'auto'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 700, margin: 0 }}>Direct Grant Subscription</h3>
              <button
                onClick={() => setIsGrantSubModalOpen(false)}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: '4px' }}
              >
                <X size={20} color="var(--color-text-secondary, #64748b)" />
              </button>
            </div>

            {grantSubError && (
              <div style={{ padding: '12px', backgroundColor: 'var(--status-overdue-bg, #fef2f2)', border: '1px solid #fecaca', borderRadius: 'var(--radius-md, 8px)', color: 'var(--status-overdue, #ef4444)', fontSize: '13px', marginBottom: '16px' }}>
                {grantSubError}
              </div>
            )}

            <form onSubmit={handleGrantSubscription} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                  Target Home Workspace ID (UUID) *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 770e8400-e29b-41d4-a716-446655440000"
                  value={grantSubForm.home_id}
                  onChange={(e) => setGrantSubForm({ ...grantSubForm, home_id: e.target.value })}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                  Target User ID (Optional, defaults to home creator)
                </label>
                <input
                  type="text"
                  placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000"
                  value={grantSubForm.user_id}
                  onChange={(e) => setGrantSubForm({ ...grantSubForm, user_id: e.target.value })}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                  Subscription Plan *
                </label>
                <select
                  required
                  value={grantSubForm.plan_id}
                  onChange={(e) => setGrantSubForm({ ...grantSubForm, plan_id: e.target.value })}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                >
                  <option value="">Select Plan...</option>
                  {plans.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.code})
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                    Duration (Days) *
                  </label>
                  <input
                    type="number"
                    required
                    min="1"
                    value={grantSubForm.duration_days}
                    onChange={(e) => setGrantSubForm({ ...grantSubForm, duration_days: parseInt(e.target.value) || 365 })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                    Paid Extra Seats
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={grantSubForm.paid_member_seats}
                    onChange={(e) => setGrantSubForm({ ...grantSubForm, paid_member_seats: parseInt(e.target.value) || 0 })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                  Grant Reason (Audited) *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. VIP partner household or non-profit sponsorship"
                  value={grantSubForm.reason}
                  onChange={(e) => setGrantSubForm({ ...grantSubForm, reason: e.target.value })}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                />
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '12px' }}>
                <button
                  type="button"
                  onClick={() => setIsGrantSubModalOpen(false)}
                  disabled={isSubmittingSub}
                  style={{ padding: '10px 18px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', backgroundColor: 'transparent', fontSize: '14px', fontWeight: 600, cursor: 'pointer', minHeight: '44px' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingSub}
                  style={{ padding: '10px 20px', borderRadius: 'var(--radius-md, 10px)', border: 'none', backgroundColor: 'var(--color-primary-900, #0f172a)', color: 'var(--color-text-inverse, #ffffff)', fontSize: '14px', fontWeight: 600, cursor: isSubmittingSub ? 'not-allowed' : 'pointer', minHeight: '44px' }}
                >
                  {isSubmittingSub ? 'Granting...' : 'Activate Subscription'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Override Period */}
      {isOverrideModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.6)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 50,
            padding: '16px'
          }}
        >
          <div
            style={{
              backgroundColor: 'var(--color-surface-card, #ffffff)',
              borderRadius: 'var(--radius-lg, 16px)',
              maxWidth: '460px',
              width: '100%',
              padding: '24px',
              boxShadow: 'var(--shadow-raised, 0 20px 25px -5px rgba(0, 0, 0, 0.1))'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Calendar size={18} color="var(--color-primary-900, #0f172a)" />
                <h3 style={{ fontSize: '18px', fontWeight: 700, margin: 0 }}>Override Subscription Period</h3>
              </div>
              <button
                onClick={() => setIsOverrideModalOpen(false)}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: '4px' }}
              >
                <X size={20} color="var(--color-text-secondary, #64748b)" />
              </button>
            </div>

            <form onSubmit={handleOverridePeriod} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                  New Expiry / Renewal Date *
                </label>
                <input
                  type="date"
                  required
                  value={overrideDate}
                  onChange={(e) => setOverrideDate(e.target.value)}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                  Override Reason (Audited) *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Complimentary extension due to service upgrade"
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', minHeight: '44px' }}
                />
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '12px' }}>
                <button
                  type="button"
                  onClick={() => setIsOverrideModalOpen(false)}
                  disabled={isSubmittingOverride}
                  style={{ padding: '10px 18px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', backgroundColor: 'transparent', fontSize: '14px', fontWeight: 600, cursor: 'pointer', minHeight: '44px' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingOverride}
                  style={{ padding: '10px 20px', borderRadius: 'var(--radius-md, 10px)', border: 'none', backgroundColor: 'var(--color-primary-900, #0f172a)', color: 'var(--color-text-inverse, #ffffff)', fontSize: '14px', fontWeight: 600, cursor: isSubmittingOverride ? 'not-allowed' : 'pointer', minHeight: '44px' }}
                >
                  {isSubmittingOverride ? 'Saving...' : 'Update Expiry'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
