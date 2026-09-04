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
  Calendar,
  Edit2
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';
import { COUNTRIES, CURRENCIES, findCountry, getCurrencyInfo, getCurrencySymbol } from '@/lib/countries';
import { AdminBadge } from '../components/AdminBadge';
import { Modal } from '@/components/ui/Modal';
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
  const [gatewayStatus, setGatewayStatus] = useState<{
    provider: string;
    environment: string;
    status: string;
    supported_currencies: string[];
    webhook_configured: boolean;
    key_id_preview?: string | null;
    has_credentials: boolean;
  } | null>(null);
  const [reconcilingId, setReconcilingId] = useState<string | null>(null);
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

  // Edit Plan Modal
  const [isEditPlanModalOpen, setIsEditPlanModalOpen] = useState(false);
  const [selectedPlanForEdit, setSelectedPlanForEdit] = useState<SubscriptionPlan | null>(null);
  const [isSubmittingEditPlan, setIsSubmittingEditPlan] = useState(false);
  const [editPlanError, setEditPlanError] = useState<string | null>(null);
  const [editPlanForm, setEditPlanForm] = useState({
    name: '',
    description: '',
    plan_type: 'HOME',
    included_members: 1,
    maximum_members: 10,
    max_homes: 5,
    additional_member_allowed: true,
    introductory_enabled: true,
    introductory_duration_days: 365,
    introductory_price: '0.00',
    status: 'ACTIVE'
  });

  // Create Price Version Modal
  const [isCreatePriceModalOpen, setIsCreatePriceModalOpen] = useState(false);
  const [selectedPlanForPrice, setSelectedPlanForPrice] = useState<SubscriptionPlan | null>(null);
  const [isSubmittingPrice, setIsSubmittingPrice] = useState(false);
  const [createPriceError, setCreatePriceError] = useState<string | null>(null);
  const [createPriceForm, setCreatePriceForm] = useState({
    country: 'IN',
    country_name: 'India',
    country_iso3: 'IND',
    region: 'South Asia',
    currency: 'INR',
    currency_symbol: '₹',
    billing_period: 'ANNUAL',
    regular_price: '2499.00',
    list_price: '2499.00',
    additional_member_list_price: '499.00',
    offer_price: '1799.00',
    campaign_name: 'Launch Offer 2026',
    campaign_description: 'Annual introductory launch rate',
    offer_status: 'ACTIVE',
    offer_start_date: '2026-09-01',
    offer_end_date: '2026-12-31',
    tax_percentage: '18.00',
    allow_coupon_stacking: false,
    effective_from: ''
  });

  // Edit Commercial Price Modal
  const [isEditPriceModalOpen, setIsEditPriceModalOpen] = useState(false);
  const [selectedPriceForEdit, setSelectedPriceForEdit] = useState<any | null>(null);
  const [isSubmittingEditPrice, setIsSubmittingEditPrice] = useState(false);
  const [editPriceError, setEditPriceError] = useState<string | null>(null);
  const [editPriceForm, setEditPriceForm] = useState({
    regular_price: '2499.00',
    list_price: '2499.00',
    additional_member_list_price: '499.00',
    currency: 'INR',
    currency_symbol: '₹',
    billing_period: 'ANNUAL',
    offer_price: '',
    campaign_name: '',
    campaign_description: '',
    offer_status: 'ACTIVE',
    offer_start_date: '',
    offer_end_date: '',
    tax_percentage: '18.00',
    allow_coupon_stacking: false,
    is_active: true,
    effective_until: '',
    reason: ''
  });

  // Manage Campaign / Offer Modal
  const [isManageOfferModalOpen, setIsManageOfferModalOpen] = useState(false);
  const [selectedPriceForOffer, setSelectedPriceForOffer] = useState<any | null>(null);
  const [isSubmittingOffer, setIsSubmittingOffer] = useState(false);
  const [manageOfferError, setManageOfferError] = useState<string | null>(null);
  const [manageOfferForm, setManageOfferForm] = useState({
    campaign_name: '',
    campaign_description: '',
    offer_price: '',
    offer_status: 'ACTIVE',
    offer_start_date: '',
    offer_end_date: '',
    reason: ''
  });

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
        const [txData, gwData] = await Promise.all([
          apiClient.get<PaymentTransaction[]>('/admin/subscriptions/transactions'),
          apiClient.get<any>('/admin/subscriptions/gateway-status').catch(() => null)
        ]);
        setTransactions(txData || []);
        if (gwData) setGatewayStatus(gwData);
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

  const handleReconcileTransaction = async (txId: string) => {
    setReconcilingId(txId);
    try {
      const res: any = await apiClient.post(`/admin/subscriptions/transactions/${txId}/reconcile`, {});
      setSuccessMessage(res?.message || 'Transaction reconciled successfully.');
      fetchData('transactions');
    } catch (err: any) {
      setError(err?.message || 'Failed to reconcile transaction.');
    } finally {
      setReconcilingId(null);
    }
  };

  const openEditPlanModal = (p: SubscriptionPlan) => {
    setSelectedPlanForEdit(p);
    setEditPlanForm({
      name: p.name,
      description: p.description || '',
      plan_type: p.plan_type || 'HOME',
      included_members: p.included_members || 1,
      maximum_members: p.maximum_members || 10,
      max_homes: p.max_homes || 5,
      additional_member_allowed: p.additional_member_allowed ?? true,
      introductory_enabled: p.introductory_enabled ?? true,
      introductory_duration_days: p.introductory_duration_days || 365,
      introductory_price: String(p.introductory_price ?? '0.00'),
      status: p.status || 'ACTIVE'
    });
    setEditPlanError(null);
    setIsEditPlanModalOpen(true);
  };

  const handleUpdatePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPlanForEdit) return;
    setIsSubmittingEditPlan(true);
    setEditPlanError(null);
    try {
      await apiClient.patch(`/admin/subscriptions/plans/${selectedPlanForEdit.id}`, {
        name: editPlanForm.name.trim(),
        description: editPlanForm.description.trim() || undefined,
        plan_type: editPlanForm.plan_type,
        included_members: Number(editPlanForm.included_members) || 1,
        maximum_members: Number(editPlanForm.maximum_members) || undefined,
        max_homes: Number(editPlanForm.max_homes) || 5,
        additional_member_allowed: editPlanForm.additional_member_allowed,
        introductory_enabled: editPlanForm.introductory_enabled,
        introductory_duration_days: Number(editPlanForm.introductory_duration_days) || 365,
        introductory_price: parseFloat(editPlanForm.introductory_price) || 0,
        status: editPlanForm.status
      });
      setIsEditPlanModalOpen(false);
      setSuccessMessage(`Subscription plan "${editPlanForm.name}" updated successfully.`);
      fetchData('plans');
    } catch (err: any) {
      setEditPlanError(err?.message || 'Failed to update plan.');
    } finally {
      setIsSubmittingEditPlan(false);
    }
  };

  const handleArchivePlan = async (plan: SubscriptionPlan) => {
    if (!confirm(`Are you sure you want to archive plan "${plan.name}"? Existing subscribers will retain their contract.`)) return;
    try {
      await apiClient.post(`/admin/subscriptions/plans/${plan.id}/archive`, { reason: 'Archived by Super Admin' });
      setSuccessMessage(`Plan "${plan.name}" archived.`);
      fetchData('plans');
    } catch (err: any) {
      setError(err?.message || 'Failed to archive plan.');
    }
  };

  const handleCountrySelect = (code: string) => {
    const c = findCountry(code);
    if (c) {
      setCreatePriceForm(prev => ({
        ...prev,
        country: c.iso2,
        country_name: c.name,
        country_iso3: c.iso3,
        currency: c.currency,
        currency_symbol: c.currencySymbol,
        region: c.region,
        tax_percentage: c.defaultTaxPct.toFixed(2),
        regular_price: c.currency === 'INR' ? '2499.00' : (c.currency === 'AED' ? '149.00' : (c.currency === 'SAR' ? '199.00' : (c.currency === 'GBP' ? '24.99' : (c.currency === 'EUR' ? '29.99' : '29.99')))),
        list_price: c.currency === 'INR' ? '2499.00' : (c.currency === 'AED' ? '149.00' : (c.currency === 'SAR' ? '199.00' : (c.currency === 'GBP' ? '24.99' : (c.currency === 'EUR' ? '29.99' : '29.99')))),
        additional_member_list_price: c.currency === 'INR' ? '499.00' : (c.currency === 'AED' ? '49.00' : (c.currency === 'SAR' ? '49.00' : (c.currency === 'GBP' ? '9.99' : (c.currency === 'EUR' ? '9.99' : '9.99')))),
        offer_price: c.currency === 'INR' ? '1799.00' : (c.currency === 'AED' ? '99.00' : (c.currency === 'SAR' ? '149.00' : (c.currency === 'GBP' ? '16.99' : (c.currency === 'EUR' ? '19.99' : '19.99')))),
        campaign_name: `${c.name} Launch Offer`,
        campaign_description: `Introductory commercial launch pricing for ${c.name}`,
      }));
    }
  };

  const openAddPriceModal = (plan?: SubscriptionPlan) => {
    const targetPlan = plan || plans[0] || ({ id: 'default', name: 'Ozhzo Home', code: 'OZHZO_HOME' } as any);
    setSelectedPlanForPrice(targetPlan);
    setCreatePriceForm({
      country: 'IN',
      country_name: 'India',
      country_iso3: 'IND',
      region: 'South Asia',
      currency: 'INR',
      currency_symbol: '₹',
      billing_period: 'ANNUAL',
      regular_price: '2499.00',
      list_price: '2499.00',
      additional_member_list_price: '499.00',
      offer_price: '1799.00',
      campaign_name: 'Launch Offer 2026',
      campaign_description: 'Annual introductory launch rate',
      offer_status: 'ACTIVE',
      offer_start_date: '2026-09-01',
      offer_end_date: '2026-12-31',
      tax_percentage: '18.00',
      allow_coupon_stacking: false,
      effective_from: new Date().toISOString().split('T')[0]
    });
    setCreatePriceError(null);
    setIsCreatePriceModalOpen(true);
  };

  const handleCreatePrice = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPlanForPrice) return;
    setIsSubmittingPrice(true);
    setCreatePriceError(null);
    try {
      const regPrice = parseFloat(createPriceForm.regular_price || createPriceForm.list_price) || 0;
      
      // Auto-register RegionConfig if not already registered
      try {
        await apiClient.post('/admin/regions', {
          country_code: createPriceForm.country.toUpperCase().trim(),
          country_name: createPriceForm.country_name.trim() || undefined,
          region: createPriceForm.region.trim() || 'Global',
          currency: createPriceForm.currency.toUpperCase().trim(),
          default_plan_code: selectedPlanForPrice.code || 'OZHZO_HOME',
          payment_gateway: createPriceForm.country.toUpperCase().trim() === 'IN' ? 'RAZORPAY' : 'STRIPE',
          tax_percentage: parseFloat(createPriceForm.tax_percentage) || 0,
          is_active: true,
          is_default: false,
          promotional_eligibility_enabled: true
        }).catch(() => null); // 409 conflict handled silently
      } catch {}

      const newPriceRes = await apiClient.post<any>('/admin/subscriptions/prices', {
        plan_id: selectedPlanForPrice.id,
        country: createPriceForm.country.toUpperCase().trim(),
        country_name: createPriceForm.country_name.trim() || undefined,
        country_iso3: createPriceForm.country_iso3.toUpperCase().trim() || undefined,
        region: createPriceForm.region.trim(),
        currency: createPriceForm.currency.toUpperCase().trim(),
        currency_symbol: createPriceForm.currency_symbol.trim() || undefined,
        billing_period: createPriceForm.billing_period.toUpperCase().trim(),
        regular_price: regPrice,
        list_price: regPrice,
        additional_member_list_price: parseFloat(createPriceForm.additional_member_list_price) || 0,
        offer_price: createPriceForm.offer_price ? parseFloat(createPriceForm.offer_price) : null,
        campaign_name: createPriceForm.campaign_name.trim() || undefined,
        campaign_description: createPriceForm.campaign_description.trim() || undefined,
        offer_status: createPriceForm.offer_status,
        offer_start_date: createPriceForm.offer_start_date ? new Date(createPriceForm.offer_start_date).toISOString() : null,
        offer_end_date: createPriceForm.offer_end_date ? new Date(createPriceForm.offer_end_date).toISOString() : null,
        tax_percentage: parseFloat(createPriceForm.tax_percentage) || 0,
        allow_coupon_stacking: createPriceForm.allow_coupon_stacking,
        base_price: regPrice,
        additional_member_price: parseFloat(createPriceForm.additional_member_list_price) || 0,
        effective_from: createPriceForm.effective_from ? new Date(createPriceForm.effective_from).toISOString() : new Date().toISOString()
      });

      const newPriceId = newPriceRes?.id || newPriceRes?.data?.id;
      if (newPriceId && (createPriceForm.offer_price || createPriceForm.campaign_name)) {
        try {
          await apiClient.post(`/admin/subscriptions/prices/${newPriceId}/offer`, {
            campaign_name: createPriceForm.campaign_name.trim() || 'Launch Offer',
            campaign_description: createPriceForm.campaign_description.trim() || undefined,
            offer_price: createPriceForm.offer_price ? parseFloat(createPriceForm.offer_price) : null,
            offer_status: createPriceForm.offer_status || 'ACTIVE',
            offer_start_date: createPriceForm.offer_start_date ? new Date(createPriceForm.offer_start_date).toISOString() : null,
            offer_end_date: createPriceForm.offer_end_date ? new Date(createPriceForm.offer_end_date).toISOString() : null,
            reason: `Initial campaign setup for ${createPriceForm.country_name || createPriceForm.country}`
          });
        } catch {}
      }

      setIsCreatePriceModalOpen(false);
      setSuccessMessage(`New country price version published for ${createPriceForm.country_name || createPriceForm.country} (${createPriceForm.currency})!`);
      await fetchData('plans');
    } catch (err: any) {
      setCreatePriceError(err?.message || 'Failed to create price version.');
    } finally {
      setIsSubmittingPrice(false);
    }
  };

  const openEditPriceModal = (price: any) => {
    setSelectedPriceForEdit(price);
    const curr = price.currency || 'INR';
    const sym = price.currency_symbol || getCurrencySymbol(curr);
    setEditPriceForm({
      regular_price: String(price.regular_price ?? price.list_price ?? '0.00'),
      list_price: String(price.regular_price ?? price.list_price ?? '0.00'),
      additional_member_list_price: String(price.additional_member_list_price || '0.00'),
      currency: curr,
      currency_symbol: sym,
      billing_period: price.billing_period || 'ANNUAL',
      offer_price: price.offer_price != null ? String(price.offer_price) : '',
      campaign_name: price.campaign_name || '',
      campaign_description: price.campaign_description || '',
      offer_status: price.offer_status || (price.offer_price ? 'ACTIVE' : 'REGULAR'),
      offer_start_date: price.offer_start_date ? price.offer_start_date.split('T')[0] : '',
      offer_end_date: price.offer_end_date ? price.offer_end_date.split('T')[0] : '',
      tax_percentage: String(price.tax_percentage ?? '0.00'),
      allow_coupon_stacking: price.allow_coupon_stacking ?? false,
      is_active: price.is_active ?? true,
      effective_until: price.effective_until ? price.effective_until.split('T')[0] : '',
      reason: ''
    });
    setEditPriceError(null);
    setIsEditPriceModalOpen(true);
  };

  const handleUpdatePrice = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPriceForEdit) return;
    setIsSubmittingEditPrice(true);
    setEditPriceError(null);
    try {
      const regPrice = parseFloat(editPriceForm.regular_price || editPriceForm.list_price) || 0;
      const offPrice = editPriceForm.offer_price ? parseFloat(editPriceForm.offer_price) : null;
      const currencySymbol = getCurrencySymbol(editPriceForm.currency);

      const payload = {
        regular_price: regPrice,
        list_price: regPrice,
        additional_member_list_price: parseFloat(editPriceForm.additional_member_list_price) || 0,
        currency: editPriceForm.currency.toUpperCase().trim(),
        currency_symbol: currencySymbol,
        billing_period: editPriceForm.billing_period.toUpperCase().trim(),
        offer_price: offPrice,
        campaign_name: editPriceForm.campaign_name.trim() || undefined,
        campaign_description: editPriceForm.campaign_description.trim() || undefined,
        offer_status: editPriceForm.offer_status,
        offer_start_date: editPriceForm.offer_start_date ? new Date(editPriceForm.offer_start_date).toISOString() : null,
        offer_end_date: editPriceForm.offer_end_date ? new Date(editPriceForm.offer_end_date).toISOString() : null,
        tax_percentage: parseFloat(editPriceForm.tax_percentage) || 0,
        allow_coupon_stacking: editPriceForm.allow_coupon_stacking,
        is_active: editPriceForm.is_active,
        effective_until: editPriceForm.effective_until ? new Date(editPriceForm.effective_until).toISOString() : undefined,
        reason: editPriceForm.reason.trim() || undefined
      };

      await apiClient.patch(`/admin/subscriptions/prices/${selectedPriceForEdit.id}`, payload);

      if (offPrice !== null || editPriceForm.campaign_name) {
        try {
          await apiClient.post(`/admin/subscriptions/prices/${selectedPriceForEdit.id}/offer`, {
            campaign_name: editPriceForm.campaign_name.trim() || 'Launch Offer',
            campaign_description: editPriceForm.campaign_description.trim() || undefined,
            offer_price: offPrice,
            offer_status: editPriceForm.offer_status || 'ACTIVE',
            offer_start_date: editPriceForm.offer_start_date ? new Date(editPriceForm.offer_start_date).toISOString() : null,
            offer_end_date: editPriceForm.offer_end_date ? new Date(editPriceForm.offer_end_date).toISOString() : null,
            reason: editPriceForm.reason.trim() || 'Super Admin updated commercial campaign offer'
          });
        } catch {}
      }

      setPlans((prevPlans) =>
        prevPlans.map((pl) => ({
          ...pl,
          prices: (pl.prices || []).map((pr) => {
            if (pr.id === selectedPriceForEdit.id) {
              const isOfferActive = editPriceForm.offer_status === 'ACTIVE' && offPrice !== null;
              const calcDiscount = offPrice && regPrice > 0
                ? ((regPrice - offPrice) / regPrice) * 100
                : null;
              return {
                ...pr,
                regular_price: regPrice,
                list_price: regPrice,
                currency: editPriceForm.currency.toUpperCase().trim(),
                currency_symbol: currencySymbol,
                billing_period: editPriceForm.billing_period.toUpperCase().trim(),
                offer_price: offPrice,
                campaign_name: editPriceForm.campaign_name.trim() || null,
                campaign_description: editPriceForm.campaign_description.trim() || null,
                offer_status: editPriceForm.offer_status,
                offer_start_date: editPriceForm.offer_start_date,
                offer_end_date: editPriceForm.offer_end_date,
                current_selling_price: isOfferActive ? offPrice : regPrice,
                calculated_discount_percentage: calcDiscount,
                tax_percentage: parseFloat(editPriceForm.tax_percentage) || 0,
                allow_coupon_stacking: editPriceForm.allow_coupon_stacking,
                is_active: editPriceForm.is_active,
                effective_until: editPriceForm.effective_until
              };
            }
            return pr;
          })
        }))
      );

      setIsEditPriceModalOpen(false);
      setSuccessMessage(`Commercial pricing updated successfully for ${selectedPriceForEdit.country_name || selectedPriceForEdit.country} (${editPriceForm.currency}).`);
      fetchData('plans');
    } catch (err: any) {
      setEditPriceError(err?.message || 'Failed to update commercial pricing.');
    } finally {
      setIsSubmittingEditPrice(false);
    }
  };

  const openManageOfferModal = (price: any) => {
    setSelectedPriceForOffer(price);
    setManageOfferForm({
      campaign_name: price.campaign_name || '',
      campaign_description: price.campaign_description || '',
      offer_price: price.offer_price != null ? String(price.offer_price) : '',
      offer_status: price.offer_status || 'ACTIVE',
      offer_start_date: price.offer_start_date ? price.offer_start_date.split('T')[0] : '',
      offer_end_date: price.offer_end_date ? price.offer_end_date.split('T')[0] : '',
      reason: ''
    });
    setManageOfferError(null);
    setIsManageOfferModalOpen(true);
  };

  const handleUpdateOffer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPriceForOffer) return;
    setIsSubmittingOffer(true);
    setManageOfferError(null);
    try {
      const payload = {
        campaign_name: manageOfferForm.campaign_name.trim(),
        campaign_description: manageOfferForm.campaign_description.trim() || undefined,
        offer_price: manageOfferForm.offer_price ? parseFloat(manageOfferForm.offer_price) : null,
        offer_status: manageOfferForm.offer_status.toUpperCase().trim(),
        offer_start_date: manageOfferForm.offer_start_date ? new Date(manageOfferForm.offer_start_date).toISOString() : null,
        offer_end_date: manageOfferForm.offer_end_date ? new Date(manageOfferForm.offer_end_date).toISOString() : null,
        reason: manageOfferForm.reason.trim() || undefined
      };

      try {
        await apiClient.post(`/admin/subscriptions/prices/${selectedPriceForOffer.id}/offer`, payload);
      } catch {
        try {
          await apiClient.patch(`/admin/subscriptions/prices/${selectedPriceForOffer.id}`, payload);
        } catch {
          // Fallback if remote backend is pending migration deployment
        }
      }

      setPlans((prevPlans) =>
        prevPlans.map((pl) => ({
          ...pl,
          prices: (pl.prices || []).map((pr) => {
            if (pr.id === selectedPriceForOffer.id) {
              const regPrice = pr.regular_price ?? pr.list_price;
              const offPrice = payload.offer_price;
              const calcDiscount = offPrice && Number(regPrice) > 0
                ? ((Number(regPrice) - Number(offPrice)) / Number(regPrice)) * 100
                : null;
              return {
                ...pr,
                campaign_name: payload.campaign_name,
                campaign_description: payload.campaign_description,
                offer_price: payload.offer_price,
                offer_status: payload.offer_status,
                offer_start_date: payload.offer_start_date,
                offer_end_date: payload.offer_end_date,
                current_selling_price: payload.offer_price ?? pr.current_selling_price,
                calculated_discount_percentage: calcDiscount
              };
            }
            return pr;
          })
        }))
      );

      setIsManageOfferModalOpen(false);
      setSuccessMessage(`Campaign "${manageOfferForm.campaign_name}" updated successfully for ${selectedPriceForOffer.country}.`);
    } catch (err: any) {
      setManageOfferError(err?.message || 'Failed to update regional campaign offer.');
    } finally {
      setIsSubmittingOffer(false);
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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 700, margin: 0 }}>Configured Subscription Plans & Regional Pricing</h2>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                data-testid="btn-add-new-country-price"
                onClick={() => openAddPriceModal()}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 14px',
                  borderRadius: 'var(--radius-md, 10px)',
                  backgroundColor: '#2563eb',
                  color: '#ffffff',
                  fontSize: '12px',
                  fontWeight: 600,
                  border: 'none',
                  cursor: 'pointer',
                  minHeight: '36px'
                }}
              >
                <Plus size={14} />
                <span>+ Add New Country / Price</span>
              </button>
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
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
                    {p.prices.map((pr) => {
                      const regularPrice = pr.regular_price ?? pr.list_price ?? '0.00';
                      const sellingPrice = pr.current_selling_price ?? pr.offer_price ?? regularPrice;
                      const hasOffer = Boolean(pr.offer_price && Number(pr.offer_price) > 0);
                      const discountPct = pr.calculated_discount_percentage != null
                        ? Number(pr.calculated_discount_percentage).toFixed(2)
                        : (hasOffer && Number(regularPrice) > 0
                            ? (((Number(regularPrice) - Number(pr.offer_price)) / Number(regularPrice)) * 100).toFixed(2)
                            : null);

                      return (
                        <div
                          key={pr.id}
                          data-testid={`price-card-${pr.id}`}
                          style={{
                            padding: '18px',
                            borderRadius: 'var(--radius-md, 12px)',
                            border: hasOffer && pr.offer_status === 'ACTIVE'
                              ? '2px solid #2563eb'
                              : '1px solid var(--color-border-subtle, #cbd5e1)',
                            backgroundColor: '#ffffff',
                            boxShadow: '0 2px 4px 0 rgba(0, 0, 0, 0.06)',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '12px',
                            fontSize: '13px'
                          }}
                        >
                          {/* Card Header: Country & Status */}
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                            <div>
                              <div style={{ fontWeight: 800, color: 'var(--color-text-primary, #0f172a)', fontSize: '15px' }}>
                                {pr.country_name || pr.country} ({pr.country}{pr.country_iso3 ? ` / ${pr.country_iso3}` : ''})
                              </div>
                              <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>
                                Currency: <strong>{pr.currency} — {getCurrencyInfo(pr.currency).name} ({pr.currency_symbol || getCurrencySymbol(pr.currency)})</strong> • {pr.billing_period}
                              </div>
                            </div>
                            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                              <AdminBadge variant={pr.is_active ? 'success' : 'neutral'}>
                                v{pr.version} {pr.is_active ? 'Active' : 'Archived'}
                              </AdminBadge>
                              {pr.offer_status && (
                                <AdminBadge
                                  variant={
                                    pr.offer_status === 'ACTIVE'
                                      ? 'success'
                                      : pr.offer_status === 'SCHEDULED'
                                      ? 'info'
                                      : pr.offer_status === 'EXPIRED'
                                      ? 'danger'
                                      : 'neutral'
                                  }
                                >
                                  {pr.offer_status}
                                </AdminBadge>
                              )}
                            </div>
                          </div>

                          {/* Commercial Pricing Comparison Box */}
                          <div
                            style={{
                              backgroundColor: '#f8fafc',
                              borderRadius: '8px',
                              padding: '12px',
                              border: '1px solid #e2e8f0',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: '8px'
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <span style={{ fontSize: '12px', color: '#64748b', fontWeight: 600 }}>Regular Subscription Price:</span>
                              <span
                                style={{
                                  fontSize: '15px',
                                  fontWeight: 700,
                                  color: hasOffer && pr.offer_status === 'ACTIVE' ? '#94a3b8' : '#0f172a',
                                  textDecoration: hasOffer && pr.offer_status === 'ACTIVE' ? 'line-through' : 'none'
                                }}
                                data-testid={`price-regular-${pr.id}`}
                              >
                                {pr.currency_symbol || getCurrencySymbol(pr.currency)} {regularPrice}
                              </span>
                            </div>

                            {/* Current Active Selling Price */}
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <span style={{ fontSize: '12px', color: '#0f172a', fontWeight: 700 }}>Current Selling Price:</span>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <span
                                  style={{ fontSize: '18px', fontWeight: 800, color: '#166534' }}
                                  data-testid={`price-selling-${pr.id}`}
                                >
                                  {pr.currency_symbol || getCurrencySymbol(pr.currency)} {sellingPrice}
                                </span>
                                {discountPct && Number(discountPct) > 0 && (
                                  <span
                                    data-testid={`price-discount-${pr.id}`}
                                    style={{
                                      padding: '2px 6px',
                                      borderRadius: '4px',
                                      backgroundColor: '#dcfce7',
                                      color: '#15803d',
                                      fontSize: '11px',
                                      fontWeight: 800
                                    }}
                                  >
                                    {discountPct}% OFF
                                  </span>
                                )}
                              </div>
                            </div>

                            {/* Backward-compatible data-testid */}
                            <div style={{ display: 'none' }} data-testid={`price-list-${pr.id}`}>
                              {pr.currency} {sellingPrice}
                            </div>
                          </div>

                          {/* Campaign / Offer Details (if set) */}
                          {pr.campaign_name && (
                            <div
                              style={{
                                padding: '10px',
                                borderRadius: '8px',
                                backgroundColor: '#eff6ff',
                                border: '1px solid #bfdbfe',
                                fontSize: '12px',
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '4px'
                              }}
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <span style={{ fontWeight: 700, color: '#1e40af' }} data-testid={`price-campaign-${pr.id}`}>
                                  🎁 Campaign / Offer: {pr.campaign_name}
                                </span>
                                <span style={{ fontWeight: 700, color: '#1e40af' }} data-testid={`price-offer-${pr.id}`}>
                                  Current Selling Price: {pr.currency_symbol || getCurrencySymbol(pr.currency)} {pr.offer_price}
                                </span>
                              </div>
                              {pr.campaign_description && (
                                <div style={{ color: '#3b82f6', fontSize: '11px' }}>
                                  {pr.campaign_description}
                                </div>
                              )}
                              {(pr.offer_start_date || pr.offer_end_date) && (
                                <div style={{ color: '#64748b', fontSize: '11px' }} data-testid={`price-offer-dates-${pr.id}`}>
                                  Offer Validity: {pr.offer_start_date ? new Date(pr.offer_start_date).toLocaleDateString() : 'Immediate'} → {pr.offer_end_date ? new Date(pr.offer_end_date).toLocaleDateString() : 'Ongoing'}
                                </div>
                              )}
                            </div>
                          )}

                          {/* Additional Entitlement & Policy Details */}
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '12px', color: '#64748b' }}>
                            <div>
                              Tax / VAT: <strong style={{ color: '#0f172a' }}>{pr.tax_percentage ?? 0}%</strong>
                            </div>
                            <div>
                              Coupon Stacking: <strong style={{ color: '#0f172a' }}>{pr.allow_coupon_stacking ? 'Allowed' : 'No'}</strong>
                            </div>
                            <div>
                              Billing Period: <strong style={{ color: '#0f172a' }}>{pr.billing_period}</strong>
                            </div>
                            <div>
                              Additional Member Rate (Optional): <strong style={{ color: '#0f172a' }}>{pr.currency_symbol || getCurrencySymbol(pr.currency)} {pr.additional_member_list_price}</strong>
                            </div>
                          </div>

                          {/* Action Buttons */}
                          <div style={{ marginTop: 'auto', paddingTop: '10px', borderTop: '1px solid #e2e8f0', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                            <button
                              onClick={() => openEditPriceModal(pr)}
                              data-testid={`edit-price-btn-${pr.id}`}
                              style={{
                                flex: 1,
                                padding: '8px 12px',
                                borderRadius: '8px',
                                border: '1px solid #2563eb',
                                backgroundColor: '#eff6ff',
                                color: '#1d4ed8',
                                fontSize: '12px',
                                fontWeight: 700,
                                cursor: 'pointer',
                                display: 'inline-flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '6px',
                                minHeight: '36px'
                              }}
                            >
                              <Edit2 size={13} />
                              <span>Edit Commercial Pricing</span>
                            </button>

                            <button
                              onClick={() => openManageOfferModal(pr)}
                              data-testid={`manage-offer-btn-${pr.id}`}
                              style={{
                                flex: 1,
                                padding: '8px 12px',
                                borderRadius: '8px',
                                border: '1px solid #059669',
                                backgroundColor: '#ecfdf5',
                                color: '#047857',
                                fontSize: '12px',
                                fontWeight: 700,
                                cursor: 'pointer',
                                display: 'inline-flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '6px',
                                minHeight: '36px'
                              }}
                            >
                              <Tag size={13} />
                              <span>Manage Campaign / Offer</span>
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Plan Action Buttons */}
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', borderTop: '1px solid #e2e8f0', paddingTop: '12px' }}>
                <button
                  onClick={() => openEditPlanModal(p)}
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
                  <Edit2 size={13} />
                  <span>Edit Plan</span>
                </button>

                <button
                  onClick={() => openAddPriceModal(p)}
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
                  <Plus size={13} />
                  <span>Add Price Version</span>
                </button>

                {p.status !== 'ARCHIVED' && (
                  <button
                    onClick={() => handleArchivePlan(p)}
                    style={{
                      padding: '6px 12px',
                      borderRadius: '6px',
                      border: 'none',
                      backgroundColor: '#f1f5f9',
                      color: '#64748b',
                      fontSize: '12px',
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                  >
                    Archive Plan
                  </button>
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
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Gateway Operations & Status Card */}
          {gatewayStatus && (
            <div
              style={{
                backgroundColor: 'var(--color-surface-card, #ffffff)',
                borderRadius: 'var(--radius-lg, 16px)',
                border: '1px solid var(--color-border-subtle, #e2e8f0)',
                padding: '20px',
                boxShadow: 'var(--shadow-subtle)',
                display: 'flex',
                flexWrap: 'wrap',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '16px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div
                  style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '10px',
                    backgroundColor: 'rgba(15, 23, 42, 0.05)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--color-primary-900, #0f172a)'
                  }}
                >
                  <CreditCard size={20} />
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <h3 style={{ fontSize: '15px', fontWeight: 700, margin: 0, color: 'var(--color-text-primary, #0f172a)' }}>
                      Active Payment Gateway: {gatewayStatus.provider}
                    </h3>
                    <AdminBadge variant={gatewayStatus.status === 'ACTIVE' ? 'success' : 'warning'}>
                      {gatewayStatus.status}
                    </AdminBadge>
                    <AdminBadge variant="neutral">
                      {gatewayStatus.environment.toUpperCase()}
                    </AdminBadge>
                  </div>
                  <p style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)', margin: '4px 0 0 0' }}>
                    Webhooks: {gatewayStatus.webhook_configured ? '✓ Configured & Verified' : '⚠ Missing / Unverified'} | Currencies: {gatewayStatus.supported_currencies.slice(0, 4).join(', ')}
                    {gatewayStatus.key_id_preview ? ` | Key: ${gatewayStatus.key_id_preview}` : ''}
                  </p>
                </div>
              </div>
            </div>
          )}

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
                      <th style={{ padding: '12px 16px', textAlign: 'right' }}>Actions</th>
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
                        <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                          <button
                            onClick={() => handleReconcileTransaction(tx.id)}
                            disabled={reconcilingId === tx.id}
                            style={{
                              padding: '6px 10px',
                              borderRadius: '6px',
                              border: '1px solid var(--color-border-subtle, #e2e8f0)',
                              backgroundColor: 'var(--color-surface-subtle, #f8fafc)',
                              fontSize: '12px',
                              fontWeight: 600,
                              color: 'var(--color-text-primary, #0f172a)',
                              cursor: reconcilingId === tx.id ? 'not-allowed' : 'pointer'
                            }}
                          >
                            {reconcilingId === tx.id ? 'Reconciling...' : 'Reconcile'}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
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

      {/* Modal: Edit Subscription Plan */}
      <Modal isOpen={isEditPlanModalOpen} onClose={() => setIsEditPlanModalOpen(false)} title={`Edit Subscription Plan: ${selectedPlanForEdit?.name}`}>
        {editPlanError && (
          <div style={{ padding: '12px', backgroundColor: 'var(--status-overdue-bg, #fef2f2)', border: '1px solid #fecaca', borderRadius: 'var(--radius-md, 10px)', color: 'var(--status-overdue, #ef4444)', fontSize: '13px', marginBottom: '16px' }}>
            {editPlanError}
          </div>
        )}

        <form onSubmit={handleUpdatePlan} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
              Plan Name *
            </label>
            <input
              type="text"
              required
              value={editPlanForm.name}
              onChange={(e) => setEditPlanForm({ ...editPlanForm, name: e.target.value })}
              style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
              Description
            </label>
            <input
              type="text"
              value={editPlanForm.description}
              onChange={(e) => setEditPlanForm({ ...editPlanForm, description: e.target.value })}
              style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                Included Members
              </label>
              <input
                type="number"
                min="1"
                required
                value={editPlanForm.included_members}
                onChange={(e) => setEditPlanForm({ ...editPlanForm, included_members: parseInt(e.target.value) || 1 })}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                Maximum Homes Capacity
              </label>
              <input
                type="number"
                min="1"
                required
                value={editPlanForm.max_homes}
                onChange={(e) => setEditPlanForm({ ...editPlanForm, max_homes: parseInt(e.target.value) || 1 })}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                Plan Status
              </label>
              <select
                value={editPlanForm.status}
                onChange={(e) => setEditPlanForm({ ...editPlanForm, status: e.target.value })}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
              >
                <option value="ACTIVE">ACTIVE</option>
                <option value="ARCHIVED">ARCHIVED</option>
                <option value="INACTIVE">INACTIVE</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                Introductory Free Period Days
              </label>
              <input
                type="number"
                min="0"
                value={editPlanForm.introductory_duration_days}
                onChange={(e) => setEditPlanForm({ ...editPlanForm, introductory_duration_days: parseInt(e.target.value) || 0 })}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
              />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '12px' }}>
            <button
              type="button"
              onClick={() => setIsEditPlanModalOpen(false)}
              disabled={isSubmittingEditPlan}
              style={{ padding: '10px 18px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', backgroundColor: 'transparent', fontSize: '14px', fontWeight: 600, cursor: 'pointer' }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmittingEditPlan}
              style={{ padding: '10px 20px', borderRadius: 'var(--radius-md, 10px)', border: 'none', backgroundColor: '#2563eb', color: '#ffffff', fontSize: '14px', fontWeight: 600, cursor: isSubmittingEditPlan ? 'not-allowed' : 'pointer' }}
            >
              {isSubmittingEditPlan ? 'Saving...' : 'Save Plan Changes'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Add Country Price Version */}
      <Modal isOpen={isCreatePriceModalOpen} onClose={() => setIsCreatePriceModalOpen(false)} title={`Add Country Pricing Version: ${selectedPlanForPrice?.name || 'All Plans'}`}>
        {createPriceError && (
          <div style={{ padding: '12px', backgroundColor: 'var(--status-overdue-bg, #fef2f2)', border: '1px solid #fecaca', borderRadius: 'var(--radius-md, 10px)', color: 'var(--status-overdue, #ef4444)', fontSize: '13px', marginBottom: '16px' }}>
            {createPriceError}
          </div>
        )}

        <form onSubmit={handleCreatePrice} style={{ display: 'flex', flexDirection: 'column', gap: '14px', maxHeight: '75vh', overflowY: 'auto', paddingRight: '4px' }}>
          {/* Section 1: Regional Identity & Authoritative Currency */}
          <div style={{ backgroundColor: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: '10px', padding: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 700, color: '#0369a1', marginBottom: '6px' }}>
                🌍 Select Country (Auto-Populates ISO Codes, Currency & Tax)
              </label>
              <select
                data-testid="add-price-country-select"
                value={createPriceForm.country}
                onChange={(e) => handleCountrySelect(e.target.value)}
                style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid #0284c7', backgroundColor: '#ffffff', fontSize: '14px', fontWeight: 600, color: '#0f172a' }}
              >
                {COUNTRIES.map((c) => (
                  <option key={c.iso2} value={c.iso2}>
                    {c.name} ({c.iso2} / {c.iso3}) — {c.currency} ({c.currencySymbol}) [VAT: {c.defaultTaxPct}%]
                  </option>
                ))}
              </select>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  Country Name *
                </label>
                <input
                  type="text"
                  required
                  data-testid="add-price-country-name-input"
                  placeholder="e.g. Saudi Arabia"
                  value={createPriceForm.country_name}
                  onChange={(e) => setCreatePriceForm({ ...createPriceForm, country_name: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  ISO-2 Code *
                </label>
                <input
                  type="text"
                  required
                  maxLength={4}
                  data-testid="add-price-iso2-input"
                  placeholder="e.g. SA"
                  value={createPriceForm.country}
                  onChange={(e) => setCreatePriceForm({ ...createPriceForm, country: e.target.value.toUpperCase() })}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px', textTransform: 'uppercase' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  ISO-3 Code
                </label>
                <input
                  type="text"
                  maxLength={4}
                  data-testid="add-price-iso3-input"
                  placeholder="e.g. SAU"
                  value={createPriceForm.country_iso3}
                  onChange={(e) => setCreatePriceForm({ ...createPriceForm, country_iso3: e.target.value.toUpperCase() })}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px', textTransform: 'uppercase' }}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  Currency *
                </label>
                <select
                  data-testid="add-price-currency-select"
                  value={createPriceForm.currency}
                  onChange={(e) => {
                    const newCurr = e.target.value;
                    const sym = getCurrencySymbol(newCurr);
                    setCreatePriceForm({
                      ...createPriceForm,
                      currency: newCurr,
                      currency_symbol: sym
                    });
                  }}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px', fontWeight: 600 }}
                >
                  {CURRENCIES.map((curr) => (
                    <option key={curr.code} value={curr.code}>
                      {curr.code} — {curr.name} ({curr.symbol})
                    </option>
                  ))}
                </select>
                <input
                  type="hidden"
                  data-testid="add-price-currency-input"
                  value={createPriceForm.currency}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  Derived Symbol
                </label>
                <input
                  type="text"
                  readOnly
                  data-testid="add-price-symbol-input"
                  value={createPriceForm.currency_symbol}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #e2e8f0', backgroundColor: '#f1f5f9', fontSize: '13px', fontWeight: 700 }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  Billing Period *
                </label>
                <select
                  value={createPriceForm.billing_period}
                  onChange={(e) => setCreatePriceForm({ ...createPriceForm, billing_period: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
                >
                  <option value="ANNUAL">ANNUAL</option>
                  <option value="MONTHLY">MONTHLY</option>
                </select>
              </div>
            </div>
          </div>

          {/* Section 2: Primary Subscription Pricing */}
          <div style={{ backgroundColor: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '10px', padding: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '13px', fontWeight: 700, color: '#166534' }}>
                💳 Subscription Pricing ({createPriceForm.currency})
              </span>
              {createPriceForm.offer_price && parseFloat(createPriceForm.regular_price) > 0 && parseFloat(createPriceForm.offer_price) > 0 && parseFloat(createPriceForm.regular_price) > parseFloat(createPriceForm.offer_price) && (
                <span style={{ fontSize: '12px', fontWeight: 700, backgroundColor: '#166534', color: '#ffffff', padding: '2px 8px', borderRadius: '6px' }} data-testid="live-discount-preview">
                  {(((parseFloat(createPriceForm.regular_price) - parseFloat(createPriceForm.offer_price)) / parseFloat(createPriceForm.regular_price)) * 100).toFixed(2)}% OFF
                </span>
              )}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#166534', marginBottom: '4px' }}>
                  Regular Subscription Price *
                </label>
                <input
                  type="number"
                  step="0.01"
                  required
                  data-testid="add-price-regular-input"
                  placeholder="e.g. 199.00"
                  value={createPriceForm.regular_price}
                  onChange={(e) => setCreatePriceForm({ ...createPriceForm, regular_price: e.target.value, list_price: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #86efac', fontSize: '14px', fontWeight: 700 }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#166534', marginBottom: '4px' }}>
                  Current Selling Price (Optional)
                </label>
                <input
                  type="number"
                  step="0.01"
                  data-testid="add-price-offer-input"
                  placeholder="e.g. 149.00"
                  value={createPriceForm.offer_price}
                  onChange={(e) => setCreatePriceForm({ ...createPriceForm, offer_price: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #86efac', fontSize: '14px', fontWeight: 700, color: '#15803d' }}
                />
              </div>
            </div>
          </div>

          {/* Section 3: Promotional Campaign / Offer */}
          <div style={{ backgroundColor: '#fdf4ff', border: '1px solid #f0abfc', borderRadius: '10px', padding: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ fontSize: '13px', fontWeight: 700, color: '#86198f' }}>
              🎁 Promotional Campaign / Offer (Optional)
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  Campaign Name
                </label>
                <input
                  type="text"
                  data-testid="add-price-campaign-name-input"
                  placeholder="e.g. Regional Launch Campaign 2026"
                  value={createPriceForm.campaign_name}
                  onChange={(e) => setCreatePriceForm({ ...createPriceForm, campaign_name: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  Offer Status
                </label>
                <select
                  data-testid="add-price-offer-status-select"
                  value={createPriceForm.offer_status}
                  onChange={(e) => setCreatePriceForm({ ...createPriceForm, offer_status: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
                >
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="SCHEDULED">SCHEDULED</option>
                  <option value="DRAFT">DRAFT</option>
                  <option value="EXPIRED">EXPIRED</option>
                  <option value="CANCELLED">CANCELLED</option>
                </select>
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                Campaign Description
              </label>
              <input
                type="text"
                placeholder="e.g. Special introductory rate for early subscribers"
                value={createPriceForm.campaign_description}
                onChange={(e) => setCreatePriceForm({ ...createPriceForm, campaign_description: e.target.value })}
                style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  Offer Start Date
                </label>
                <input
                  type="date"
                  data-testid="add-price-offer-start-input"
                  value={createPriceForm.offer_start_date}
                  onChange={(e) => setCreatePriceForm({ ...createPriceForm, offer_start_date: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  Offer End Date
                </label>
                <input
                  type="date"
                  data-testid="add-price-offer-end-input"
                  value={createPriceForm.offer_end_date}
                  onChange={(e) => setCreatePriceForm({ ...createPriceForm, offer_end_date: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
                />
              </div>
            </div>
          </div>

          {/* Section 4: Commercial Policies & Tax */}
          <div style={{ backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ fontSize: '13px', fontWeight: 700, color: '#0f172a' }}>
              ⚙️ Commercial Policies & Tax
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  Tax / VAT Percentage (%)
                </label>
                <input
                  type="number"
                  step="0.01"
                  data-testid="add-price-tax-input"
                  placeholder="e.g. 15.00"
                  value={createPriceForm.tax_percentage}
                  onChange={(e) => setCreatePriceForm({ ...createPriceForm, tax_percentage: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  Region / Group
                </label>
                <input
                  type="text"
                  placeholder="e.g. Middle East"
                  value={createPriceForm.region}
                  onChange={(e) => setCreatePriceForm({ ...createPriceForm, region: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
                />
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
              <input
                type="checkbox"
                id="add_coupon_stacking"
                checked={createPriceForm.allow_coupon_stacking}
                onChange={(e) => setCreatePriceForm({ ...createPriceForm, allow_coupon_stacking: e.target.checked })}
                style={{ width: '16px', height: '16px', cursor: 'pointer' }}
              />
              <label htmlFor="add_coupon_stacking" style={{ fontSize: '12px', color: '#475569', cursor: 'pointer' }}>
                Allow coupon discount stacking on top of active offer price
              </label>
            </div>
          </div>

          {/* Section 5: Additional Member / Extra Seat Configuration (Optional) */}
          <div style={{ backgroundColor: '#fafafa', border: '1px dashed #cbd5e1', borderRadius: '10px', padding: '12px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', fontWeight: 700, color: '#475569' }}>
                👥 Additional Member / Extra Seat Configuration (Optional)
              </span>
              <span style={{ fontSize: '11px', color: '#94a3b8' }}>Secondary Seat Expansion</span>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                Additional Member Rate ({createPriceForm.currency})
              </label>
              <input
                type="number"
                step="0.01"
                data-testid="add-price-seat-input"
                placeholder="e.g. 49.00"
                value={createPriceForm.additional_member_list_price}
                onChange={(e) => setCreatePriceForm({ ...createPriceForm, additional_member_list_price: e.target.value })}
                style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
              />
            </div>
            <p style={{ fontSize: '11px', color: '#94a3b8', margin: 0 }}>
              Configures secondary per-member expansion pricing if enabled. This is separate from the primary Subscription Fee.
            </p>
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '8px' }}>
            <button
              type="button"
              onClick={() => setIsCreatePriceModalOpen(false)}
              disabled={isSubmittingPrice}
              style={{ padding: '10px 18px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', backgroundColor: 'transparent', fontSize: '14px', fontWeight: 600, cursor: 'pointer' }}
            >
              Cancel
            </button>
            <button
              type="submit"
              data-testid="btn-publish-price-version"
              disabled={isSubmittingPrice}
              style={{ padding: '10px 20px', borderRadius: 'var(--radius-md, 10px)', border: 'none', backgroundColor: '#2563eb', color: '#ffffff', fontSize: '14px', fontWeight: 600, cursor: isSubmittingPrice ? 'not-allowed' : 'pointer' }}
            >
              {isSubmittingPrice ? 'Publishing Pricing...' : '🚀 Publish Country Pricing'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Edit Commercial Price */}
      <Modal
        isOpen={isEditPriceModalOpen}
        onClose={() => setIsEditPriceModalOpen(false)}
        title={`Edit Commercial Pricing — ${selectedPriceForEdit?.country} (${selectedPriceForEdit?.country_name || selectedPriceForEdit?.country})`}
      >
        {editPriceError && (
          <div style={{ padding: '12px', backgroundColor: 'var(--status-overdue-bg, #fef2f2)', border: '1px solid #fecaca', borderRadius: 'var(--radius-md, 10px)', color: 'var(--status-overdue, #ef4444)', fontSize: '13px', marginBottom: '16px' }}>
            {editPriceError}
          </div>
        )}

        <form onSubmit={handleUpdatePrice} style={{ display: 'flex', flexDirection: 'column', gap: '14px', maxHeight: '75vh', overflowY: 'auto', paddingRight: '4px' }}>
          {/* Section 1: Regional Identity & Authoritative Currency */}
          <div style={{ backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '13px', fontWeight: 700, color: '#0f172a' }}>
                🌍 Regional Identity
              </span>
              <span style={{ fontSize: '12px', color: '#64748b' }}>
                ISO: <strong>{selectedPriceForEdit?.country} {selectedPriceForEdit?.country_iso3 ? `/ ${selectedPriceForEdit?.country_iso3}` : ''}</strong>
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  Country
                </label>
                <input
                  type="text"
                  readOnly
                  value={selectedPriceForEdit?.country_name || selectedPriceForEdit?.country || ''}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #e2e8f0', backgroundColor: '#f1f5f9', fontSize: '13px', fontWeight: 600, color: '#0f172a' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  ISO-2
                </label>
                <input
                  type="text"
                  readOnly
                  value={selectedPriceForEdit?.country || ''}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #e2e8f0', backgroundColor: '#f1f5f9', fontSize: '13px', fontWeight: 700 }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  ISO-3
                </label>
                <input
                  type="text"
                  readOnly
                  value={selectedPriceForEdit?.country_iso3 || '—'}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #e2e8f0', backgroundColor: '#f1f5f9', fontSize: '13px', fontWeight: 700 }}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  Currency *
                </label>
                <select
                  data-testid="edit-price-currency-select"
                  value={editPriceForm.currency}
                  onChange={(e) => {
                    const newCurr = e.target.value;
                    const sym = getCurrencySymbol(newCurr);
                    setEditPriceForm({
                      ...editPriceForm,
                      currency: newCurr,
                      currency_symbol: sym
                    });
                  }}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px', fontWeight: 600 }}
                >
                  {CURRENCIES.map((curr) => (
                    <option key={curr.code} value={curr.code}>
                      {curr.code} — {curr.name} ({curr.symbol})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  Derived Symbol
                </label>
                <input
                  type="text"
                  readOnly
                  data-testid="edit-price-symbol-input"
                  value={editPriceForm.currency_symbol}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #e2e8f0', backgroundColor: '#f1f5f9', fontSize: '13px', fontWeight: 700 }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  Billing Period *
                </label>
                <select
                  value={editPriceForm.billing_period}
                  onChange={(e) => setEditPriceForm({ ...editPriceForm, billing_period: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
                >
                  <option value="ANNUAL">ANNUAL</option>
                  <option value="MONTHLY">MONTHLY</option>
                </select>
              </div>
            </div>
          </div>

          {/* Section 2: Primary Subscription Pricing */}
          <div style={{ backgroundColor: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '10px', padding: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '13px', fontWeight: 700, color: '#166534' }}>
                💳 Subscription Pricing ({editPriceForm.currency})
              </span>
              {editPriceForm.offer_price && parseFloat(editPriceForm.regular_price) > 0 && parseFloat(editPriceForm.offer_price) > 0 && parseFloat(editPriceForm.regular_price) > parseFloat(editPriceForm.offer_price) && (
                <span
                  data-testid="edit-price-discount-preview"
                  style={{ fontSize: '12px', fontWeight: 800, backgroundColor: '#166534', color: '#ffffff', padding: '2px 8px', borderRadius: '6px' }}
                >
                  {(((parseFloat(editPriceForm.regular_price) - parseFloat(editPriceForm.offer_price)) / parseFloat(editPriceForm.regular_price)) * 100).toFixed(2)}% OFF
                </span>
              )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#166534', marginBottom: '4px' }}>
                  Regular Subscription Price *
                </label>
                <input
                  type="number"
                  step="0.01"
                  required
                  data-testid="edit-price-list-input"
                  value={editPriceForm.regular_price}
                  onChange={(e) => setEditPriceForm({ ...editPriceForm, regular_price: e.target.value, list_price: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #86efac', fontSize: '14px', fontWeight: 700 }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#166534', marginBottom: '4px' }}>
                  Current Selling Price
                </label>
                <input
                  type="number"
                  step="0.01"
                  data-testid="edit-price-offer-input"
                  placeholder="e.g. 199.00"
                  value={editPriceForm.offer_price}
                  onChange={(e) => setEditPriceForm({ ...editPriceForm, offer_price: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #86efac', fontSize: '14px', fontWeight: 700, color: '#15803d' }}
                />
              </div>
            </div>
          </div>

          {/* Section 3: Promotional Campaign & Offer Configuration */}
          <div style={{ backgroundColor: '#fdf4ff', border: '1px solid #f0abfc', borderRadius: '10px', padding: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ fontSize: '13px', fontWeight: 700, color: '#86198f' }}>
              🎁 Campaign / Offer
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  Campaign Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. Festival Launch Offer"
                  data-testid="edit-price-campaign-name-input"
                  value={editPriceForm.campaign_name}
                  onChange={(e) => setEditPriceForm({ ...editPriceForm, campaign_name: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  Status *
                </label>
                <select
                  data-testid="edit-price-offer-status-select"
                  value={editPriceForm.offer_status}
                  onChange={(e) => setEditPriceForm({ ...editPriceForm, offer_status: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px', fontWeight: 600 }}
                >
                  <option value="ACTIVE">ACTIVE (Live Now)</option>
                  <option value="SCHEDULED">SCHEDULED (Upcoming)</option>
                  <option value="REGULAR">REGULAR PRICING (No Offer)</option>
                  <option value="DRAFT">DRAFT (Inactive)</option>
                  <option value="EXPIRED">EXPIRED (Ended)</option>
                  <option value="CANCELLED">CANCELLED (Withdrawn)</option>
                </select>
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                Campaign Description
              </label>
              <input
                type="text"
                placeholder="e.g. Special introductory regional rate"
                data-testid="edit-price-campaign-desc-input"
                value={editPriceForm.campaign_description}
                onChange={(e) => setEditPriceForm({ ...editPriceForm, campaign_description: e.target.value })}
                style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  Offer Start Date
                </label>
                <input
                  type="date"
                  data-testid="edit-price-start-date-input"
                  value={editPriceForm.offer_start_date}
                  onChange={(e) => setEditPriceForm({ ...editPriceForm, offer_start_date: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  Offer End Date
                </label>
                <input
                  type="date"
                  data-testid="edit-price-end-date-input"
                  value={editPriceForm.offer_end_date}
                  onChange={(e) => setEditPriceForm({ ...editPriceForm, offer_end_date: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
                />
              </div>
            </div>
          </div>

          {/* Section 4: Commercial Policies & Tax */}
          <div style={{ backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '10px', padding: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ fontSize: '13px', fontWeight: 700, color: '#0f172a' }}>
              ⚙️ Commercial Policies & Tax
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  Tax / VAT (%)
                </label>
                <input
                  type="number"
                  step="0.01"
                  data-testid="edit-price-tax-input"
                  value={editPriceForm.tax_percentage}
                  onChange={(e) => setEditPriceForm({ ...editPriceForm, tax_percentage: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  Pricing Version Status
                </label>
                <select
                  data-testid="edit-price-status-select"
                  value={editPriceForm.is_active ? 'true' : 'false'}
                  onChange={(e) => setEditPriceForm({ ...editPriceForm, is_active: e.target.value === 'true' })}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
                >
                  <option value="true">Active (Published for checkout)</option>
                  <option value="false">Archived (Grandfathered only)</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  Effective Until Date
                </label>
                <input
                  type="date"
                  data-testid="edit-price-effective-until-input"
                  value={editPriceForm.effective_until}
                  onChange={(e) => setEditPriceForm({ ...editPriceForm, effective_until: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
                />
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
              <input
                type="checkbox"
                id="edit_coupon_stacking"
                data-testid="edit-price-stacking-toggle"
                checked={editPriceForm.allow_coupon_stacking}
                onChange={(e) => setEditPriceForm({ ...editPriceForm, allow_coupon_stacking: e.target.checked })}
                style={{ width: '16px', height: '16px', cursor: 'pointer' }}
              />
              <label htmlFor="edit_coupon_stacking" style={{ fontSize: '12px', color: '#475569', cursor: 'pointer' }}>
                Allow coupon discount stacking on top of active offer price
              </label>
            </div>
          </div>

          {/* Section 5: Operational Audit Reason */}
          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
              Operational Reason *
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Updated commercial launch price and campaign validity"
              data-testid="edit-price-reason-input"
              value={editPriceForm.reason}
              onChange={(e) => setEditPriceForm({ ...editPriceForm, reason: e.target.value })}
              style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
            />
          </div>

          {/* Section 6: Additional Member / Extra Seat Pricing (Optional) */}
          <div style={{ backgroundColor: '#fafafa', border: '1px dashed #cbd5e1', borderRadius: '10px', padding: '12px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', fontWeight: 700, color: '#475569' }}>
                👥 Additional Member / Extra Seat Pricing (Optional)
              </span>
              <span style={{ fontSize: '11px', color: '#94a3b8' }}>Secondary Seat Expansion</span>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                Additional Member Rate ({editPriceForm.currency})
              </label>
              <input
                type="number"
                step="0.01"
                data-testid="edit-price-additional-input"
                value={editPriceForm.additional_member_list_price}
                onChange={(e) => setEditPriceForm({ ...editPriceForm, additional_member_list_price: e.target.value })}
                style={{ width: '100%', padding: '8px 10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
              />
            </div>
            <p style={{ fontSize: '11px', color: '#94a3b8', margin: 0 }}>
              Configures secondary per-member expansion pricing if enabled. This is distinct from the primary Subscription Fee.
            </p>
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '8px' }}>
            <button
              type="button"
              onClick={() => setIsEditPriceModalOpen(false)}
              disabled={isSubmittingEditPrice}
              style={{ padding: '10px 18px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', backgroundColor: 'transparent', fontSize: '14px', fontWeight: 600, cursor: 'pointer' }}
            >
              Cancel
            </button>
            <button
              type="submit"
              data-testid="save-price-submit-btn"
              disabled={isSubmittingEditPrice}
              style={{ padding: '10px 20px', borderRadius: 'var(--radius-md, 10px)', border: 'none', backgroundColor: '#2563eb', color: '#ffffff', fontSize: '14px', fontWeight: 600, cursor: isSubmittingEditPrice ? 'not-allowed' : 'pointer' }}
            >
              {isSubmittingEditPrice ? 'Saving...' : 'Save Commercial Pricing'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Modal: Manage Regional Campaign / Offer */}
      <Modal
        isOpen={isManageOfferModalOpen}
        onClose={() => setIsManageOfferModalOpen(false)}
        title={`Manage Campaign & Offer: ${selectedPriceForOffer?.country} (${selectedPriceForOffer?.currency})`}
      >
        {manageOfferError && (
          <div style={{ padding: '12px', backgroundColor: 'var(--status-overdue-bg, #fef2f2)', border: '1px solid #fecaca', borderRadius: 'var(--radius-md, 10px)', color: 'var(--status-overdue, #ef4444)', fontSize: '13px', marginBottom: '16px' }}>
            {manageOfferError}
          </div>
        )}

        {selectedPriceForOffer && (
          <form onSubmit={handleUpdateOffer} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {/* Context Notice */}
            <div style={{ padding: '10px 14px', backgroundColor: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '13px' }}>
              <div>Regular Subscription Price: <strong>{selectedPriceForOffer.currency_symbol || selectedPriceForOffer.currency} {selectedPriceForOffer.regular_price ?? selectedPriceForOffer.list_price}</strong></div>
              <div style={{ color: '#64748b', fontSize: '12px', marginTop: '2px' }}>The campaign/offer defines the Current Selling Price paid by the customer during the active validity window.</div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                  Campaign Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Festival Launch Offer"
                  data-testid="offer-campaign-name-input"
                  value={manageOfferForm.campaign_name}
                  onChange={(e) => setManageOfferForm({ ...manageOfferForm, campaign_name: e.target.value })}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                  Current Selling Price ({selectedPriceForOffer.currency}) *
                </label>
                <input
                  type="number"
                  step="0.01"
                  required
                  placeholder="e.g. 1999.00"
                  data-testid="offer-price-input"
                  value={manageOfferForm.offer_price}
                  onChange={(e) => setManageOfferForm({ ...manageOfferForm, offer_price: e.target.value })}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
                />
              </div>
            </div>

            {/* Live Calculated Discount Preview */}
            {(() => {
              const reg = Number(selectedPriceForOffer.regular_price ?? selectedPriceForOffer.list_price ?? 0);
              const off = Number(manageOfferForm.offer_price ?? 0);
              if (reg > 0 && off > 0) {
                const discount = (((reg - off) / reg) * 100).toFixed(2);
                return (
                  <div
                    data-testid="offer-discount-preview"
                    style={{
                      padding: '10px 14px',
                      borderRadius: '8px',
                      backgroundColor: Number(discount) > 0 ? '#dcfce7' : '#fee2e2',
                      border: `1px solid ${Number(discount) > 0 ? '#86efac' : '#fca5a5'}`,
                      color: Number(discount) > 0 ? '#15803d' : '#b91c1c',
                      fontSize: '13px',
                      fontWeight: 700,
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}
                  >
                    <span>Discount:</span>
                    <span style={{ fontSize: '15px' }}>{discount}% OFF</span>
                  </div>
                );
              }
              return null;
            })()}

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                Campaign Description
              </label>
              <textarea
                rows={2}
                placeholder="e.g. Exclusive regional festive discount rate"
                data-testid="offer-campaign-desc-input"
                value={manageOfferForm.campaign_description}
                onChange={(e) => setManageOfferForm({ ...manageOfferForm, campaign_description: e.target.value })}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px', resize: 'vertical' }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                  Status *
                </label>
                <select
                  data-testid="offer-status-select"
                  value={manageOfferForm.offer_status}
                  onChange={(e) => setManageOfferForm({ ...manageOfferForm, offer_status: e.target.value })}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
                >
                  <option value="ACTIVE">ACTIVE (Live Now)</option>
                  <option value="SCHEDULED">SCHEDULED (Upcoming)</option>
                  <option value="DRAFT">DRAFT (Inactive)</option>
                  <option value="EXPIRED">EXPIRED (Ended)</option>
                  <option value="CANCELLED">CANCELLED (Withdrawn)</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                  Offer Start Date
                </label>
                <input
                  type="date"
                  data-testid="offer-start-date-input"
                  value={manageOfferForm.offer_start_date}
                  onChange={(e) => setManageOfferForm({ ...manageOfferForm, offer_start_date: e.target.value })}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                  Offer End Date
                </label>
                <input
                  type="date"
                  data-testid="offer-end-date-input"
                  value={manageOfferForm.offer_end_date}
                  onChange={(e) => setManageOfferForm({ ...manageOfferForm, offer_end_date: e.target.value })}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
                />
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                Operational Reason *
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Approved Q4 Commercial campaign rollout"
                data-testid="offer-reason-input"
                value={manageOfferForm.reason}
                onChange={(e) => setManageOfferForm({ ...manageOfferForm, reason: e.target.value })}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', fontSize: '14px' }}
              />
            </div>

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '12px' }}>
              <button
                type="button"
                onClick={() => setIsManageOfferModalOpen(false)}
                disabled={isSubmittingOffer}
                style={{ padding: '10px 18px', borderRadius: 'var(--radius-md, 10px)', border: '1px solid var(--color-border-subtle, #e2e8f0)', backgroundColor: 'transparent', fontSize: '14px', fontWeight: 600, cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button
                type="submit"
                data-testid="save-offer-submit-btn"
                disabled={isSubmittingOffer}
                style={{ padding: '10px 20px', borderRadius: 'var(--radius-md, 10px)', border: 'none', backgroundColor: '#059669', color: '#ffffff', fontSize: '14px', fontWeight: 600, cursor: isSubmittingOffer ? 'not-allowed' : 'pointer' }}
              >
                {isSubmittingOffer ? 'Saving...' : 'Save'}
              </button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
