'use client';

import React, { useEffect, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import {
  Tag,
  CreditCard,
  CheckCircle2,
  AlertCircle,
  Home,
  Check,
  X,
  Receipt,
  Users,
  RefreshCw,
  Coins
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';
import { getCurrencyInfo, formatMoney } from '@/lib/countries';

interface UserEntitlementSummary {
  free_home_consumed: boolean;
  free_home_included: number;
  active_homes_count: number;
  total_allowed_homes: number;
  can_create_home: boolean;
  active_subscription?: {
    id: string;
    plan_name: string;
    status: string;
    lifecycle_status?: string;
    current_period_ends_at?: string | null;
    days_until_expiry?: number | null;
    is_expiring_soon?: boolean;
    cancel_at_period_end?: boolean;
    paid_member_seats: number;
    effective_price: number | string;
    currency: string;
  } | null;
}

interface SubscriptionPrice {
  id: string;
  plan_id: string;
  country: string;
  country_name?: string;
  currency: string;
  currency_symbol?: string;
  billing_period: string;
  regular_price?: number | string;
  list_price: number | string;
  offer_price?: number | string | null;
  current_selling_price?: number | string;
  campaign_name?: string | null;
  campaign_description?: string | null;
  offer_status?: string;
  offer_start_date?: string | null;
  offer_end_date?: string | null;
  calculated_discount_percentage?: number | string | null;
  additional_member_list_price: number | string;
  is_active: boolean;
}

interface SubscriptionPlanDetail {
  id: string;
  name: string;
  code: string;
  description?: string | null;
  plan_type: string;
  status: string;
  included_members: number;
  maximum_members?: number | null;
  max_homes: number;
  additional_member_allowed: boolean;
  introductory_enabled: boolean;
  introductory_duration_days: number;
  introductory_price: number | string;
  prices: SubscriptionPrice[];
}

interface PaymentTransaction {
  id: string;
  plan_name: string;
  amount: number | string;
  discount_amount: number | string;
  final_amount: number | string;
  currency: string;
  provider: string;
  status: string;
  created_at: string;
}

interface SubscriptionCreditItem {
  id: string;
  amount: number | string;
  remaining_amount: number | string;
  currency: string;
  credit_type: string;
  status: string;
  reference?: string | null;
  description?: string | null;
  expires_at?: string | null;
  created_at: string;
}

interface MemberDTO {
  id: string;
  user_id: string;
  display_name: string;
  role: string;
  status: string;
}

export default function SubscriptionPage() {
  const [entitlements, setEntitlements] = useState<UserEntitlementSummary | null>(null);
  const [plans, setPlans] = useState<SubscriptionPlanDetail[]>([]);
  const [transactions, setTransactions] = useState<PaymentTransaction[]>([]);
  const [credits, setCredits] = useState<SubscriptionCreditItem[]>([]);
  const [members, setMembers] = useState<MemberDTO[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Selected checkout options
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);
  const [selectedCurrency, setSelectedCurrency] = useState('USD');
  const [couponCode, setCouponCode] = useState('');
  const [appliedCoupon, setAppliedCoupon] = useState<{
    code: string;
    discount_text: string;
    discount_amount: number;
    is_free: boolean;
  } | null>(null);
  const [couponError, setCouponError] = useState<string | null>(null);
  const [isValidatingCoupon, setIsValidatingCoupon] = useState(false);

  // Checkout modal & process
  const [isCheckingOut, setIsCheckingOut] = useState(false);
  const [checkoutResult, setCheckoutResult] = useState<{
    transaction_id: string;
    amount: number;
    discount_amount: number;
    credit_applied?: number;
    final_amount: number;
    currency: string;
    provider_transaction_id: string;
    payment_required: boolean;
  } | null>(null);
  const [isConfirming, setIsConfirming] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadAllData = async () => {
    setIsLoading(true);
    try {
      const [entData, plansData, txData, credData] = await Promise.all([
        apiClient.get<UserEntitlementSummary>('/subscription/me').catch(() => null),
        apiClient.get<SubscriptionPlanDetail[]>('/subscription/plans').catch(() => []),
        apiClient.get<PaymentTransaction[]>('/subscription/transactions').catch(() => []),
        apiClient.get<SubscriptionCreditItem[]>('/subscription/my-credits').catch(() => [])
      ]);

      setEntitlements(entData);
      setPlans(plansData || []);
      setTransactions(txData || []);
      setCredits(credData || []);

      if (plansData && plansData.length > 0 && !selectedPlanId) {
        setSelectedPlanId(plansData[0].id);
      }

      // Load members for active home if present
      const homeId = await apiClient.getValidActiveHome().catch(() => null);
      if (homeId) {
        const memData = await apiClient.get<MemberDTO[]>(`/homes/${homeId}/members`).catch(() => []);
        setMembers(memData || []);
      }
    } catch (err) {
      console.error('Failed to load subscription data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, []);

  const handleValidateCoupon = async () => {
    if (!couponCode.trim()) return;
    setIsValidatingCoupon(true);
    setCouponError(null);
    try {
      const res: any = await apiClient.post('/coupons/validate', {
        code: couponCode.trim()
      });
      if (res?.valid) {
        setAppliedCoupon({
          code: res.code,
          discount_text: res.benefit || 'Discount applied',
          discount_amount: Number(res.discount_value) || 0,
          is_free: res.coupon_type === 'FREE_PERIOD'
        });
      } else {
        setCouponError('Invalid or expired coupon code.');
      }
    } catch (err: any) {
      setCouponError(err?.message || 'Coupon not found or inactive.');
      setAppliedCoupon(null);
    } finally {
      setIsValidatingCoupon(false);
    }
  };

  const handleInitiateCheckout = async (planId: string) => {
    setIsCheckingOut(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const res = await apiClient.post<{
        transaction_id: string;
        amount: number;
        discount_amount: number;
        final_amount: number;
        currency: string;
        provider_transaction_id: string;
        payment_required: boolean;
      }>('/subscription/checkout', {
        plan_id: planId,
        currency: selectedCurrency,
        coupon_code: appliedCoupon ? appliedCoupon.code : (couponCode.trim() || undefined),
        billing_period: 'ANNUAL'
      });

      setCheckoutResult(res);
    } catch (err: any) {
      setErrorMessage(err?.message || 'Checkout failed. Please try again.');
    } finally {
      setIsCheckingOut(false);
    }
  };

  const handleConfirmPayment = async () => {
    if (!checkoutResult) return;
    setIsConfirming(true);
    setErrorMessage(null);
    try {
      await apiClient.post('/subscription/confirm-payment', {
        transaction_id: checkoutResult.transaction_id,
        provider_transaction_id: checkoutResult.provider_transaction_id
      });

      setSuccessMessage('Subscription activated successfully! Your household entitlements are now active.');
      setCheckoutResult(null);
      setAppliedCoupon(null);
      setCouponCode('');
      await loadAllData();
    } catch (err: any) {
      setErrorMessage(err?.message || 'Payment confirmation failed.');
    } finally {
      setIsConfirming(false);
    }
  };

  const handleCancelSubscription = async () => {
    if (!window.confirm('Are you sure you want to cancel your subscription at the end of the current billing cycle?')) return;
    try {
      await apiClient.post('/subscription/cancel', {});
      setSuccessMessage('Subscription scheduled for cancellation at the end of the current billing period.');
      await loadAllData();
    } catch (err: any) {
      setErrorMessage(err?.message || 'Failed to cancel subscription.');
    }
  };

  const availableCurrencies = React.useMemo(() => {
    const currencies = new Set<string>(['USD', 'INR', 'AED', 'GBP', 'EUR', 'SAR']);
    plans.forEach(p => {
      (p.prices || []).forEach(pr => {
        if (pr.currency) currencies.add(pr.currency);
      });
    });
    return Array.from(currencies);
  }, [plans]);

  const selectedPlan = plans.find((p) => p.id === selectedPlanId) || plans[0];

  if (isLoading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '50vh', gap: '10px', color: 'var(--color-primary-900)' }}>
        <RefreshCw size={24} className="animate-spin" />
        <span style={{ fontSize: '14px', fontWeight: 600 }}>Loading subscription entitlements...</span>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '900px' }}>
      {/* Header */}
      <div>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-primary-900)' }}>
          Household Subscription & Multi-Home Entitlements
        </h1>
        <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
          One user = One free Home lifetime. Upgrade your household subscription for additional homes, multi-member sync, and premium features.
        </p>
      </div>

      {/* Notifications */}
      {successMessage && (
        <div style={{ padding: '14px 18px', backgroundColor: 'var(--status-in-stock-bg)', border: '1px solid #a7f3d0', borderRadius: 'var(--radius-md)', color: 'var(--status-in-stock)', fontSize: '14px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <CheckCircle2 size={18} />
          <span>{successMessage}</span>
        </div>
      )}

      {errorMessage && (
        <div style={{ padding: '14px 18px', backgroundColor: 'var(--status-overdue-bg)', border: '1px solid #fecaca', borderRadius: 'var(--radius-md)', color: 'var(--status-overdue)', fontSize: '14px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertCircle size={18} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* User Entitlements Overview Card */}
      <Card style={{ border: '2px solid var(--color-primary-900)', backgroundColor: 'var(--color-surface-overlay)' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-4)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{ width: '48px', height: '48px', borderRadius: '50%', backgroundColor: 'var(--color-primary-900)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Home size={24} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                  {entitlements?.active_subscription ? entitlements.active_subscription.plan_name : 'Ozhzo Free Household Tier'}
                </h2>
                {entitlements?.active_subscription ? (
                  entitlements.active_subscription.lifecycle_status === 'EXPIRING' ? (
                    <Badge variant="overdue">
                      Expiring Soon ({entitlements.active_subscription.days_until_expiry ?? 7}d left)
                    </Badge>
                  ) : entitlements.active_subscription.lifecycle_status === 'EXPIRED' ? (
                    <Badge variant="overdue">
                      Expired
                    </Badge>
                  ) : (
                    <Badge variant="in-stock">
                      Active Subscriber
                    </Badge>
                  )
                ) : (
                  <Badge variant="neutral">
                    1 Free Home Tier
                  </Badge>
                )}
              </div>
              <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
                {entitlements?.free_home_consumed
                  ? 'Your lifetime free Home entitlement is consumed.'
                  : 'You have 1 free lifetime Home available.'}
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '16px', textAlign: 'right' }}>
            <div>
              <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>
                Active Households
              </div>
              <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--color-primary-900)' }}>
                {entitlements?.active_homes_count ?? 0} / {entitlements?.total_allowed_homes ?? 1}
              </div>
            </div>

            {entitlements?.active_subscription && (
              <div>
                <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>
                  {entitlements.active_subscription.lifecycle_status === 'EXPIRED' ? 'Expired On' : 'Renewal / Expiry'}
                </div>
                <div style={{ fontSize: '14px', fontWeight: 700, color: entitlements.active_subscription.lifecycle_status === 'EXPIRING' ? 'var(--status-overdue)' : 'var(--color-primary-900)', marginTop: '4px' }}>
                  {entitlements.active_subscription.current_period_ends_at
                    ? new Date(entitlements.active_subscription.current_period_ends_at).toLocaleDateString()
                    : '1 Year'}
                </div>
              </div>
            )}
          </div>
        </div>

        {entitlements?.active_subscription && (
          <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid var(--color-border-subtle)', display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            {(entitlements.active_subscription.lifecycle_status === 'EXPIRING' || entitlements.active_subscription.lifecycle_status === 'EXPIRED') && (
              <Button
                size="sm"
                onClick={() => {
                  if (plans.length > 0) {
                    setSelectedPlanId(plans[0].id);
                  }
                  window.scrollTo({ top: 600, behavior: 'smooth' });
                }}
              >
                <span>Renew Subscription</span>
              </Button>
            )}
            <Button size="sm" variant="secondary" onClick={handleCancelSubscription}>
              Cancel Auto-Renew
            </Button>
          </div>
        )}
      </Card>

      {/* Available Plans Section */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
            Choose Household Plan
          </h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
            <span style={{ color: 'var(--color-text-secondary)' }}>Billing Currency:</span>
            <select
              data-testid="customer-currency-selector"
              value={selectedCurrency}
              onChange={(e) => setSelectedCurrency(e.target.value)}
              style={{ padding: '6px 10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border-subtle)', fontSize: '13px', fontWeight: 600 }}
            >
              {availableCurrencies.map((curr) => {
                const info = getCurrencyInfo(curr);
                return (
                  <option key={curr} value={curr}>
                    {curr} — {info.name} ({info.symbol})
                  </option>
                );
              })}
            </select>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--space-4)' }}>
          {plans.map((p) => {
            const price = p.prices?.find((pr) => pr.currency === selectedCurrency) || p.prices?.[0];
            const regularAmount = price?.regular_price ?? price?.list_price ?? (p.introductory_price || '0.00');
            const sellingAmount = price?.current_selling_price ?? price?.offer_price ?? regularAmount;
            const hasOffer = Boolean(price?.offer_price && Number(price.offer_price) > 0 && price.offer_status === 'ACTIVE');
            const discountPct = price?.calculated_discount_percentage != null
              ? Number(price.calculated_discount_percentage).toFixed(0)
              : (hasOffer && Number(regularAmount) > 0
                  ? (((Number(regularAmount) - Number(sellingAmount)) / Number(regularAmount)) * 100).toFixed(0)
                  : null);
            const isSelected = selectedPlanId === p.id;

            return (
              <Card
                key={p.id}
                style={{
                  border: isSelected ? '2px solid var(--color-primary-900)' : '1px solid var(--color-border-subtle)',
                  backgroundColor: isSelected ? 'var(--color-surface-card)' : 'var(--color-surface-subtle)',
                  cursor: 'pointer',
                  position: 'relative',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between'
                }}
                onClick={() => setSelectedPlanId(p.id)}
              >
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-primary-900)' }}>{p.name}</h3>
                    {isSelected && <Badge variant="in-stock">Selected</Badge>}
                  </div>

                  <div style={{ marginBottom: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', flexWrap: 'wrap' }}>
                      {hasOffer && (
                        <span style={{ fontSize: '15px', color: 'var(--color-text-secondary)', textDecoration: 'line-through' }}>
                          {formatMoney(regularAmount, selectedCurrency)}
                        </span>
                      )}
                      <span style={{ fontSize: '24px', fontWeight: 800, color: 'var(--color-primary-900)' }} data-testid="customer-selling-price">
                        {formatMoney(sellingAmount, selectedCurrency)}
                      </span>
                      <span style={{ fontSize: '12px', fontWeight: 500, color: 'var(--color-text-secondary)' }}>/ year</span>
                      {hasOffer && discountPct && Number(discountPct) > 0 && (
                        <span style={{ marginLeft: '4px' }}>
                          <Badge variant="in-stock">
                            {discountPct}% OFF
                          </Badge>
                        </span>
                      )}
                    </div>
                    {hasOffer && price?.campaign_name && (
                      <div style={{ fontSize: '11px', color: '#15803d', fontWeight: 600, marginTop: '2px' }}>
                        🎁 {price.campaign_name}
                      </div>
                    )}
                  </div>

                  <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginBottom: '14px' }}>
                    {p.description || 'Complete household operating system with multi-home management.'}
                  </p>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12px', color: 'var(--color-text-primary)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Check size={14} color="var(--status-in-stock)" />
                      <span><strong>Up to {p.max_homes} Households</strong></span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Check size={14} color="var(--status-in-stock)" />
                      <span><strong>{p.included_members} Included Members</strong></span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Check size={14} color="var(--status-in-stock)" />
                      <span>Unlimited Inventory, Bills & Tasks</span>
                    </div>
                  </div>
                </div>

                <div style={{ marginTop: '16px' }}>
                  <Button
                    variant={isSelected ? 'primary' : 'secondary'}
                    style={{ width: '100%', minHeight: '40px' }}
                    isLoading={isCheckingOut && isSelected}
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedPlanId(p.id);
                      handleInitiateCheckout(p.id);
                    }}
                  >
                    Select & Subscribe
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Coupon Application & Checkout Box */}
      <Card variant="subtle">
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Tag size={18} color="var(--color-primary-900)" />
            <h3 style={{ fontSize: '15px', fontWeight: 700 }}>Have a Promotional Coupon or Grant Code?</h3>
          </div>

          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <input
              type="text"
              placeholder="e.g. LAUNCH50, MOSTWANTED"
              value={couponCode}
              onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
              style={{
                flex: 1,
                minWidth: '200px',
                padding: '10px 12px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border-subtle)',
                fontSize: '14px',
                minHeight: '44px'
              }}
            />
            <Button
              type="button"
              variant="secondary"
              onClick={handleValidateCoupon}
              isLoading={isValidatingCoupon}
              style={{ minHeight: '44px' }}
            >
              Apply Coupon
            </Button>
          </div>

          {appliedCoupon && (
            <div style={{ padding: '10px 12px', backgroundColor: 'var(--status-in-stock-bg)', borderRadius: 'var(--radius-md)', color: 'var(--status-in-stock)', fontSize: '13px', fontWeight: 600, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Coupon "{appliedCoupon.code}" applied: {appliedCoupon.discount_text}</span>
              <Button size="sm" variant="ghost" onClick={() => { setAppliedCoupon(null); setCouponCode(''); }}>
                <X size={14} />
              </Button>
            </div>
          )}

          {couponError && (
            <div style={{ fontSize: '13px', color: 'var(--status-overdue)', fontWeight: 500 }}>
              {couponError}
            </div>
          )}
        </div>
      </Card>

      {/* Checkout Modal / Summary */}
      {checkoutResult && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(15, 23, 42, 0.6)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px', zIndex: 9999 }}>
          <div style={{ backgroundColor: 'var(--color-surface-card)', borderRadius: 'var(--radius-lg)', padding: '24px', maxWidth: '480px', width: '100%', boxShadow: 'var(--shadow-modal)', border: '1px solid var(--color-border-subtle)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CreditCard size={20} color="var(--color-primary-900)" />
                <h3 style={{ fontSize: '18px', fontWeight: 700 }}>Confirm Subscription Purchase</h3>
              </div>
              <button onClick={() => setCheckoutResult(null)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
                <X size={20} />
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '14px', marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--color-text-secondary)' }}>Selected Plan:</span>
                <span style={{ fontWeight: 600 }}>{selectedPlan?.name}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--color-text-secondary)' }}>List Price:</span>
                <span>{checkoutResult.currency} {Number(checkoutResult.amount).toFixed(2)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--status-in-stock)' }}>
                <span>Discount:</span>
                <span>-{checkoutResult.currency} {Number(checkoutResult.discount_amount).toFixed(2)}</span>
              </div>
              {checkoutResult.credit_applied && Number(checkoutResult.credit_applied) > 0 && (
                <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--status-in-stock)' }}>
                  <span>Subscription Credit:</span>
                  <span>-{checkoutResult.currency} {Number(checkoutResult.credit_applied).toFixed(2)}</span>
                </div>
              )}
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '16px', fontWeight: 700, borderTop: '1px solid var(--color-border-subtle)', paddingTop: '8px' }}>
                <span>Total Amount Due:</span>
                <span>{checkoutResult.currency} {Number(checkoutResult.final_amount).toFixed(2)}</span>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <Button variant="secondary" onClick={() => setCheckoutResult(null)} disabled={isConfirming}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleConfirmPayment} isLoading={isConfirming}>
                {checkoutResult.final_amount > 0 ? 'Pay & Activate Subscription' : 'Activate Free Period'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Subscription Credits Table */}
      {credits.length > 0 && (
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <Coins size={18} color="var(--color-primary-900)" />
            <h3 style={{ fontSize: '15px', fontWeight: 700 }}>My Subscription Credits</h3>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--color-border-subtle)', color: 'var(--color-text-secondary)' }}>
                  <th style={{ padding: '8px 12px' }}>Date</th>
                  <th style={{ padding: '8px 12px' }}>Reason / Reference</th>
                  <th style={{ padding: '8px 12px' }}>Original Amount</th>
                  <th style={{ padding: '8px 12px' }}>Available Balance</th>
                  <th style={{ padding: '8px 12px' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {credits.map((c) => (
                  <tr key={c.id} style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
                    <td style={{ padding: '8px 12px' }}>{new Date(c.created_at).toLocaleDateString()}</td>
                    <td style={{ padding: '8px 12px' }}>{c.description || c.reference || c.credit_type}</td>
                    <td style={{ padding: '8px 12px' }}>{c.currency} {Number(c.amount).toFixed(2)}</td>
                    <td style={{ padding: '8px 12px', fontWeight: 700, color: Number(c.remaining_amount) > 0 ? 'var(--status-in-stock)' : 'var(--color-text-secondary)' }}>
                      {c.currency} {Number(c.remaining_amount).toFixed(2)}
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      <Badge variant={c.status === 'AVAILABLE' || c.status === 'PARTIALLY_USED' ? 'in-stock' : 'neutral'}>
                        {c.status}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Transaction Invoices Table */}
      {transactions.length > 0 && (
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <Receipt size={18} color="var(--color-primary-900)" />
            <h3 style={{ fontSize: '15px', fontWeight: 700 }}>Payment & Billing History</h3>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--color-border-subtle)', color: 'var(--color-text-secondary)' }}>
                  <th style={{ padding: '8px 12px' }}>Date</th>
                  <th style={{ padding: '8px 12px' }}>Plan</th>
                  <th style={{ padding: '8px 12px' }}>Amount</th>
                  <th style={{ padding: '8px 12px' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((t) => (
                  <tr key={t.id} style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
                    <td style={{ padding: '8px 12px' }}>{new Date(t.created_at).toLocaleDateString()}</td>
                    <td style={{ padding: '8px 12px', fontWeight: 600 }}>{t.plan_name}</td>
                    <td style={{ padding: '8px 12px' }}>{t.currency} {Number(t.final_amount).toFixed(2)}</td>
                    <td style={{ padding: '8px 12px' }}>
                      <Badge variant={t.status === 'SUCCESS' ? 'in-stock' : 'overdue'}>{t.status}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Household Members & Seat Status */}
      {members.length > 0 && (
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <Users size={18} color="var(--color-primary-900)" />
            <h3 style={{ fontSize: '15px', fontWeight: 700 }}>Household Members & Seat Allocation ({members.length})</h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {members.map((m, idx) => (
              <div
                key={m.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 12px',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--color-surface-subtle)'
                }}
              >
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600 }}>{m.display_name}</div>
                  <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>Role: {m.role}</div>
                </div>
                <Badge variant={idx === 0 ? 'in-stock' : 'neutral'}>
                  {idx === 0 ? 'Free Home Owner' : 'Household Member'}
                </Badge>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
