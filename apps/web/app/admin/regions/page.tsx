'use client';

import React, { useState, useEffect } from 'react';
import {
  Plus,
  RefreshCw,
  Edit2,
  Search,
  DollarSign
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';
import { COUNTRIES, findCountry, getCurrencySymbol } from '@/lib/countries';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';

interface RegionConfig {
  id: string;
  country_code: string;
  country_name: string;
  region: string;
  currency: string;
  default_plan_code: string;
  payment_gateway: string;
  tax_percentage: number | string;
  is_active: boolean;
  is_default: boolean;
  promotional_eligibility_enabled: boolean;
  metadata_json: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

interface PriceVersion {
  id: string;
  plan_id: string;
  country: string;
  country_name?: string;
  region: string;
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
  additional_member_list_price?: number | string;
  base_price?: number | string;
  additional_member_price?: number | string;
  version: number;
  is_active: boolean;
  effective_from: string;
  effective_until?: string | null;
}

interface PlanOption {
  id: string;
  name: string;
  code: string;
}

export default function AdminRegionsPage() {
  const [regions, setRegions] = useState<RegionConfig[]>([]);
  const [prices, setPrices] = useState<PriceVersion[]>([]);
  const [plans, setPlans] = useState<PlanOption[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRegion, setSelectedRegion] = useState<RegionConfig | null>(null);

  // Modals
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isPricesModalOpen, setIsPricesModalOpen] = useState(false);

  // Inline Add Price Form in Prices Modal
  const [showAddPriceForm, setShowAddPriceForm] = useState(false);
  const [isSubmittingPrice, setIsSubmittingPrice] = useState(false);
  const [priceForm, setPriceForm] = useState({
    plan_id: '',
    billing_period: 'ANNUAL',
    list_price: '1799.00',
    additional_member_list_price: '499.00'
  });

  // Edit Price Version Modal State
  const [isEditPriceModalOpen, setIsEditPriceModalOpen] = useState(false);
  const [selectedPriceForEdit, setSelectedPriceForEdit] = useState<PriceVersion | null>(null);
  const [isSubmittingEditPrice, setIsSubmittingEditPrice] = useState(false);
  const [editPriceForm, setEditPriceForm] = useState({
    list_price: '0.00',
    additional_member_list_price: '0.00',
    is_active: true,
    reason: ''
  });

  // Add Form State
  const [addForm, setAddForm] = useState({
    country_code: '',
    country_name: '',
    region: 'Global',
    currency: 'USD',
    default_plan_code: 'HOME_STANDARD',
    payment_gateway: 'STRIPE',
    tax_percentage: '0.00',
    is_active: true,
    is_default: false,
    promotional_eligibility_enabled: true
  });

  // Edit Form State
  const [editForm, setEditForm] = useState({
    country_name: '',
    region: '',
    currency: '',
    default_plan_code: '',
    payment_gateway: '',
    tax_percentage: '',
    is_active: true,
    is_default: false,
    promotional_eligibility_enabled: true
  });

  const [feedbackMsg, setFeedbackMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const DEFAULT_REGIONS: RegionConfig[] = [
    { id: 'reg-in', country_code: 'IN', country_name: 'India', region: 'South Asia', currency: 'INR', default_plan_code: 'OZHZO_HOME', payment_gateway: 'RAZORPAY', tax_percentage: 18.0, is_active: true, is_default: false, promotional_eligibility_enabled: true, metadata_json: {} },
    { id: 'reg-ae', country_code: 'AE', country_name: 'United Arab Emirates', region: 'Middle East', currency: 'AED', default_plan_code: 'OZHZO_HOME', payment_gateway: 'STRIPE', tax_percentage: 5.0, is_active: true, is_default: false, promotional_eligibility_enabled: true, metadata_json: {} },
    { id: 'reg-gb', country_code: 'GB', country_name: 'United Kingdom', region: 'Europe', currency: 'GBP', default_plan_code: 'OZHZO_HOME', payment_gateway: 'STRIPE', tax_percentage: 20.0, is_active: true, is_default: false, promotional_eligibility_enabled: true, metadata_json: {} },
    { id: 'reg-us', country_code: 'US', country_name: 'United States', region: 'North America', currency: 'USD', default_plan_code: 'OZHZO_HOME', payment_gateway: 'STRIPE', tax_percentage: 0.0, is_active: true, is_default: false, promotional_eligibility_enabled: true, metadata_json: {} },
    { id: 'reg-global', country_code: 'GLOBAL', country_name: 'Global / International', region: 'Global', currency: 'USD', default_plan_code: 'OZHZO_HOME', payment_gateway: 'STRIPE', tax_percentage: 0.0, is_active: true, is_default: true, promotional_eligibility_enabled: true, metadata_json: {} }
  ];

  const fetchRegions = async () => {
    try {
      setIsLoading(true);
      const [resRegions, resPlans] = await Promise.all([
        apiClient.get<RegionConfig[]>('/admin/regions').catch(() => DEFAULT_REGIONS),
        apiClient.get<PlanOption[]>('/admin/subscriptions/plans').catch(() => [])
      ]);
      setRegions(resRegions && resRegions.length > 0 ? resRegions : DEFAULT_REGIONS);
      setPlans(resPlans || []);
      if (resPlans && resPlans.length > 0 && !priceForm.plan_id) {
        setPriceForm((prev) => ({ ...prev, plan_id: resPlans[0].id }));
      }
    } catch (err: any) {
      setRegions(DEFAULT_REGIONS);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchRegionPrices = async (countryCode: string) => {
    try {
      const res = await apiClient.get<PriceVersion[]>(`/admin/regions/${countryCode}/pricing`).catch(async () => {
        const allPrices = await apiClient.get<PriceVersion[]>('/admin/subscriptions/prices').catch(() => []);
        return (allPrices || []).filter(p => p.country === countryCode || p.country === 'GLOBAL');
      });
      setPrices(res || []);
    } catch {
      setPrices([]);
    }
  };

  useEffect(() => {
    fetchRegions();
  }, []);

  const handleCountrySelectInRegions = (code: string) => {
    const c = findCountry(code);
    if (c) {
      setAddForm(prev => ({
        ...prev,
        country_code: c.iso2,
        country_name: c.name,
        region: c.region,
        currency: c.currency,
        payment_gateway: c.paymentGateway,
        tax_percentage: c.defaultTaxPct.toFixed(2),
      }));
    }
  };

  const handleCreateRegion = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiClient.post('/admin/regions', {
        ...addForm,
        tax_percentage: parseFloat(addForm.tax_percentage) || 0
      });
      setFeedbackMsg({ type: 'success', text: `Country ${addForm.country_name} (${addForm.country_code}) added successfully!` });
      setIsAddModalOpen(false);
      fetchRegions();
    } catch (err: any) {
      setFeedbackMsg({ type: 'error', text: err?.message || 'Failed to create country' });
    }
  };

  const handleUpdateRegion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRegion) return;
    try {
      await apiClient.patch(`/admin/regions/${selectedRegion.country_code}`, {
        ...editForm,
        tax_percentage: parseFloat(editForm.tax_percentage) || 0
      });
      setFeedbackMsg({ type: 'success', text: `Region ${selectedRegion.country_code} updated successfully!` });
      setIsEditModalOpen(false);
      fetchRegions();
    } catch (err: any) {
      setFeedbackMsg({ type: 'error', text: err?.message || 'Failed to update region' });
    }
  };

  const handleCreatePriceForRegion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRegion) return;
    setIsSubmittingPrice(true);
    try {
      await apiClient.post('/admin/subscriptions/prices', {
        plan_id: priceForm.plan_id || (plans[0]?.id ?? ''),
        country: selectedRegion.country_code,
        region: selectedRegion.region,
        currency: selectedRegion.currency,
        billing_period: priceForm.billing_period,
        list_price: parseFloat(priceForm.list_price) || 0,
        additional_member_list_price: parseFloat(priceForm.additional_member_list_price) || 0,
        base_price: parseFloat(priceForm.list_price) || 0,
        additional_member_price: parseFloat(priceForm.additional_member_list_price) || 0,
        effective_from: new Date().toISOString()
      });
      setFeedbackMsg({ type: 'success', text: `New price version published for ${selectedRegion.country_code}!` });
      setShowAddPriceForm(false);
      await fetchRegionPrices(selectedRegion.country_code);
    } catch (err: any) {
      setFeedbackMsg({ type: 'error', text: err?.message || 'Failed to create price version' });
    } finally {
      setIsSubmittingPrice(false);
    }
  };

  const openEditModal = (r: RegionConfig) => {
    setSelectedRegion(r);
    setEditForm({
      country_name: r.country_name,
      region: r.region,
      currency: r.currency,
      default_plan_code: r.default_plan_code,
      payment_gateway: r.payment_gateway,
      tax_percentage: String(r.tax_percentage || '0.00'),
      is_active: r.is_active,
      is_default: r.is_default,
      promotional_eligibility_enabled: r.promotional_eligibility_enabled
    });
    setIsEditModalOpen(true);
  };

  const openEditPriceModal = (p: PriceVersion) => {
    setSelectedPriceForEdit(p);
    setEditPriceForm({
      list_price: String(p.list_price || '0.00'),
      additional_member_list_price: String(p.additional_member_list_price || '0.00'),
      is_active: p.is_active ?? true,
      reason: ''
    });
    setIsEditPriceModalOpen(true);
  };

  const handleUpdatePriceVersion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPriceForEdit || !selectedRegion) return;
    setIsSubmittingEditPrice(true);
    try {
      const regPrice = parseFloat(editPriceForm.list_price) || 0;
      await apiClient.patch(`/admin/subscriptions/prices/${selectedPriceForEdit.id}`, {
        regular_price: regPrice,
        list_price: regPrice,
        additional_member_list_price: parseFloat(editPriceForm.additional_member_list_price) || 0,
        is_active: editPriceForm.is_active,
        reason: editPriceForm.reason.trim() || undefined
      });
      setFeedbackMsg({ type: 'success', text: `Price version updated successfully!` });
      setIsEditPriceModalOpen(false);
      await fetchRegionPrices(selectedRegion.country_code);
    } catch (err: any) {
      setFeedbackMsg({ type: 'error', text: err?.message || 'Failed to update price version' });
    } finally {
      setIsSubmittingEditPrice(false);
    }
  };

  const openPricesModal = async (r: RegionConfig) => {
    setSelectedRegion(r);
    setShowAddPriceForm(false);
    await fetchRegionPrices(r.country_code);
    setIsPricesModalOpen(true);
  };

  const filteredRegions = regions.filter((r) =>
    r.country_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    r.country_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
    r.currency.toLowerCase().includes(searchQuery.toLowerCase()) ||
    r.region.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 style={{ fontSize: '24px', fontWeight: 800, color: 'var(--color-primary-900, #0f172a)', margin: 0 }}>
              Regional Configuration & Dynamic Pricing
            </h1>
            <Badge variant="completed">Server Authoritative</Badge>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--color-text-secondary, #64748b)', marginTop: '4px' }}>
            Manage commercial countries, currencies, payment gateways, tax rates, and country-specific price versioning.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <Button variant="secondary" onClick={fetchRegions} disabled={isLoading}>
            <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
            <span style={{ marginLeft: '6px' }}>Refresh</span>
          </Button>

          <Button variant="primary" onClick={() => setIsAddModalOpen(true)}>
            <Plus size={16} />
            <span style={{ marginLeft: '6px' }}>Add Supported Country</span>
          </Button>
        </div>
      </div>

      {/* Feedback Toast */}
      {feedbackMsg && (
        <div
          style={{
            padding: '12px 16px',
            borderRadius: '8px',
            marginBottom: '20px',
            backgroundColor: feedbackMsg.type === 'success' ? '#f0fdf4' : '#fef2f2',
            border: `1px solid ${feedbackMsg.type === 'success' ? '#86efac' : '#fca5a5'}`,
            color: feedbackMsg.type === 'success' ? '#166534' : '#991b1b',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '14px'
          }}
        >
          <span>{feedbackMsg.text}</span>
          <button onClick={() => setFeedbackMsg(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }}>✕</button>
        </div>
      )}

      {/* Search & Filter Bar */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '20px' }}>
        <div style={{ position: 'relative', flex: 1, maxWidth: '400px' }}>
          <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
          <input
            type="text"
            placeholder="Search by country, code, or currency..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '10px 12px 10px 38px',
              borderRadius: '8px',
              border: '1px solid #cbd5e1',
              fontSize: '14px',
              outline: 'none'
            }}
          />
        </div>
      </div>

      {/* Regions Table */}
      <Card style={{ padding: '0', overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#475569' }}>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>Country & Code</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>Region</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>Currency</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>Payment Gateway</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>Tax %</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>Default Plan</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>Status</th>
                <th style={{ padding: '14px 16px', fontWeight: 600, textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredRegions.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ padding: '32px', textAlign: 'center', color: '#64748b' }}>
                    No regional configurations found.
                  </td>
                </tr>
              ) : (
                filteredRegions.map((r) => (
                  <tr key={r.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '14px 16px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontWeight: 700, color: '#0f172a' }}>{r.country_name}</span>
                        <Badge variant="neutral">{r.country_code}</Badge>
                        {r.is_default && <Badge variant="completed">Default Global</Badge>}
                      </div>
                    </td>
                    <td style={{ padding: '14px 16px', color: '#475569' }}>{r.region}</td>
                    <td style={{ padding: '14px 16px' }}>
                      <Badge variant="completed">{r.currency} ({getCurrencySymbol(r.currency)})</Badge>
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      <Badge variant={r.payment_gateway === 'RAZORPAY' ? 'in-stock' : 'neutral'}>
                        {r.payment_gateway}
                      </Badge>
                    </td>
                    <td style={{ padding: '14px 16px', color: '#475569' }}>{r.tax_percentage}%</td>
                    <td style={{ padding: '14px 16px', color: '#475569' }}>{r.default_plan_code}</td>
                    <td style={{ padding: '14px 16px' }}>
                      <Badge variant={r.is_active ? 'completed' : 'overdue'}>
                        {r.is_active ? 'Active' : 'Disabled'}
                      </Badge>
                    </td>
                    <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                      <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                        <Button size="sm" variant="secondary" onClick={() => openPricesModal(r)}>
                          <DollarSign size={14} />
                          <span style={{ marginLeft: '4px' }}>Prices</span>
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => openEditModal(r)}>
                          <Edit2 size={14} />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* MODAL: ADD COUNTRY */}
      {isAddModalOpen && (
        <Modal title="Add Supported Commercial Country" isOpen={isAddModalOpen} onClose={() => setIsAddModalOpen(false)}>
          <form onSubmit={handleCreateRegion} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ backgroundColor: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: '10px', padding: '12px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 700, color: '#0369a1', marginBottom: '6px' }}>
                🌍 Select Country (Auto-Populates Commercial ISO Codes, Currency & Tax)
              </label>
              <select
                data-testid="regions-country-select"
                value={addForm.country_code}
                onChange={(e) => handleCountrySelectInRegions(e.target.value)}
                style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid #0284c7', backgroundColor: '#ffffff', fontSize: '14px', fontWeight: 600, color: '#0f172a' }}
              >
                <option value="">-- Choose Country to Auto-Fill --</option>
                {COUNTRIES.map((c) => (
                  <option key={c.iso2} value={c.iso2}>
                    {c.name} ({c.iso2} / {c.iso3}) — {c.currency} ({c.currencySymbol}) [VAT: {c.defaultTaxPct}%]
                  </option>
                ))}
              </select>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Country Code (ISO-2) *
                </label>
                <Input
                  required
                  data-testid="regions-iso2-input"
                  placeholder="e.g. SG, AU, CA"
                  value={addForm.country_code}
                  onChange={(e) => setAddForm({ ...addForm, country_code: e.target.value.toUpperCase() })}
                />
              </div>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Country Name *
                </label>
                <Input
                  required
                  data-testid="regions-name-input"
                  placeholder="e.g. Singapore"
                  value={addForm.country_name}
                  onChange={(e) => setAddForm({ ...addForm, country_name: e.target.value })}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Region
                </label>
                <Input
                  placeholder="e.g. Southeast Asia, Europe"
                  value={addForm.region}
                  onChange={(e) => setAddForm({ ...addForm, region: e.target.value })}
                />
              </div>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Currency (ISO-3) *
                </label>
                <Input
                  required
                  placeholder="e.g. SGD, AUD, CAD"
                  value={addForm.currency}
                  onChange={(e) => setAddForm({ ...addForm, currency: e.target.value.toUpperCase() })}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Payment Gateway
                </label>
                <select
                  value={addForm.payment_gateway}
                  onChange={(e) => setAddForm({ ...addForm, payment_gateway: e.target.value })}
                  style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1' }}
                >
                  <option value="STRIPE">Stripe</option>
                  <option value="RAZORPAY">Razorpay</option>
                  <option value="MOCK">Mock Gateway (Testing)</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Tax / VAT Rate (%)
                </label>
                <Input
                  type="number"
                  step="0.01"
                  value={addForm.tax_percentage}
                  onChange={(e) => setAddForm({ ...addForm, tax_percentage: e.target.value })}
                />
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '12px' }}>
              <Button variant="secondary" type="button" onClick={() => setIsAddModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" type="submit">
                Add Country
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* MODAL: EDIT COUNTRY */}
      {isEditModalOpen && selectedRegion && (
        <Modal title={`Edit Regional Settings: ${selectedRegion.country_name} (${selectedRegion.country_code})`} isOpen={isEditModalOpen} onClose={() => setIsEditModalOpen(false)}>
          <form onSubmit={handleUpdateRegion} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Country Name
                </label>
                <Input
                  value={editForm.country_name}
                  onChange={(e) => setEditForm({ ...editForm, country_name: e.target.value })}
                />
              </div>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Region
                </label>
                <Input
                  value={editForm.region}
                  onChange={(e) => setEditForm({ ...editForm, region: e.target.value })}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Currency
                </label>
                <Input
                  value={editForm.currency}
                  onChange={(e) => setEditForm({ ...editForm, currency: e.target.value.toUpperCase() })}
                />
              </div>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Default Plan Code
                </label>
                <Input
                  value={editForm.default_plan_code}
                  onChange={(e) => setEditForm({ ...editForm, default_plan_code: e.target.value.toUpperCase() })}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Payment Gateway
                </label>
                <select
                  value={editForm.payment_gateway}
                  onChange={(e) => setEditForm({ ...editForm, payment_gateway: e.target.value })}
                  style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1' }}
                >
                  <option value="STRIPE">Stripe</option>
                  <option value="RAZORPAY">Razorpay</option>
                  <option value="MOCK">Mock Gateway (Testing)</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Tax / VAT Rate (%)
                </label>
                <Input
                  type="number"
                  step="0.01"
                  value={editForm.tax_percentage}
                  onChange={(e) => setEditForm({ ...editForm, tax_percentage: e.target.value })}
                />
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '8px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={editForm.is_active}
                  onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })}
                />
                Commercial Region Active
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={editForm.promotional_eligibility_enabled}
                  onChange={(e) => setEditForm({ ...editForm, promotional_eligibility_enabled: e.target.checked })}
                />
                Promotional Eligibility Enabled
              </label>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '12px' }}>
              <Button variant="secondary" type="button" onClick={() => setIsEditModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" type="submit">
                Save Changes
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* MODAL: VIEW REGIONAL PRICES & VERSION HISTORY */}
      {isPricesModalOpen && selectedRegion && (
        <Modal
          title={`Price Versions: ${selectedRegion.country_name} (${selectedRegion.currency})`}
          isOpen={isPricesModalOpen}
          onClose={() => setIsPricesModalOpen(false)}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <p style={{ fontSize: '13px', color: '#64748b', margin: 0 }}>
                Historical price versions are immutable to protect existing active subscribers.
              </p>
              <Button size="sm" variant="primary" onClick={() => setShowAddPriceForm(!showAddPriceForm)}>
                <Plus size={14} />
                <span style={{ marginLeft: '4px' }}>{showAddPriceForm ? 'Cancel' : 'Add Price Version'}</span>
              </Button>
            </div>

            {/* Inline Add Price Version Form */}
            {showAddPriceForm && (
              <form onSubmit={handleCreatePriceForRegion} style={{ padding: '14px', backgroundColor: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <h4 style={{ margin: '0 0 6px', fontSize: '13px', fontWeight: 700 }}>Publish New Price Version for {selectedRegion.country_code}</h4>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <div>
                    <label style={{ fontSize: '11px', fontWeight: 600, color: '#475569' }}>Plan</label>
                    <select
                      value={priceForm.plan_id}
                      onChange={(e) => setPriceForm({ ...priceForm, plan_id: e.target.value })}
                      style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px' }}
                    >
                      {plans.map((pl) => (
                        <option key={pl.id} value={pl.id}>{pl.name} ({pl.code})</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label style={{ fontSize: '11px', fontWeight: 600, color: '#475569' }}>Billing Period</label>
                    <select
                      value={priceForm.billing_period}
                      onChange={(e) => setPriceForm({ ...priceForm, billing_period: e.target.value })}
                      style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '13px' }}
                    >
                      <option value="ANNUAL">ANNUAL</option>
                      <option value="MONTHLY">MONTHLY</option>
                    </select>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <div>
                    <label style={{ fontSize: '11px', fontWeight: 600, color: '#475569' }}>Regular Subscription Price ({selectedRegion.currency}) *</label>
                    <Input
                      type="number"
                      step="0.01"
                      required
                      value={priceForm.list_price}
                      onChange={(e) => setPriceForm({ ...priceForm, list_price: e.target.value })}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: '11px', fontWeight: 600, color: '#475569' }}>Additional Member Rate (Optional) ({selectedRegion.currency})</label>
                    <Input
                      type="number"
                      step="0.01"
                      value={priceForm.additional_member_list_price}
                      onChange={(e) => setPriceForm({ ...priceForm, additional_member_list_price: e.target.value })}
                    />
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px', marginTop: '6px' }}>
                  <Button size="sm" variant="secondary" type="button" onClick={() => setShowAddPriceForm(false)}>Cancel</Button>
                  <Button size="sm" variant="primary" type="submit" disabled={isSubmittingPrice}>
                    {isSubmittingPrice ? 'Publishing...' : 'Publish Version'}
                  </Button>
                </div>
              </form>
            )}

            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
              <thead>
                <tr style={{ backgroundColor: '#f1f5f9', color: '#475569' }}>
                  <th style={{ padding: '8px 10px' }}>Version</th>
                  <th style={{ padding: '8px 10px' }}>Period</th>
                  <th style={{ padding: '8px 10px' }}>Regular Subscription Price</th>
                  <th style={{ padding: '8px 10px' }}>Additional Member Rate</th>
                  <th style={{ padding: '8px 10px' }}>Status</th>
                  <th style={{ padding: '8px 10px' }}>Effective From</th>
                  <th style={{ padding: '8px 10px', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {prices.length === 0 ? (
                  <tr>
                    <td colSpan={7} style={{ padding: '16px', textAlign: 'center', color: '#64748b' }}>
                      No price versions recorded yet for this region.
                    </td>
                  </tr>
                ) : (
                  prices.map((p) => (
                    <tr key={p.id} style={{ borderBottom: '1px solid #e2e8f0' }}>
                      <td style={{ padding: '8px 10px', fontWeight: 700 }}>v{p.version}</td>
                      <td style={{ padding: '8px 10px', fontWeight: 600 }}>{p.billing_period}</td>
                      <td style={{ padding: '8px 10px' }}>{selectedRegion.currency} {p.list_price}</td>
                      <td style={{ padding: '8px 10px' }}>{selectedRegion.currency} {p.additional_member_list_price || '—'}</td>
                      <td style={{ padding: '8px 10px' }}>
                        <Badge variant={p.is_active ? 'completed' : 'neutral'}>{p.is_active ? 'Active' : 'Archived'}</Badge>
                      </td>
                      <td style={{ padding: '8px 10px', color: '#64748b' }}>
                        {p.effective_from ? new Date(p.effective_from).toLocaleDateString() : 'N/A'}
                      </td>
                      <td style={{ padding: '8px 10px', textAlign: 'right' }}>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => openEditPriceModal(p)}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '4px 8px',
                            fontSize: '11px',
                            fontWeight: 700
                          }}
                        >
                          <Edit2 size={12} />
                          <span>Edit</span>
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '8px' }}>
              <Button variant="secondary" onClick={() => setIsPricesModalOpen(false)}>
                Close
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* MODAL: EDIT PRICE VERSION */}
      {isEditPriceModalOpen && selectedPriceForEdit && selectedRegion && (
        <Modal
          title={`Edit Price Version (v${selectedPriceForEdit.version}) - ${selectedRegion.country_name}`}
          isOpen={isEditPriceModalOpen}
          onClose={() => setIsEditPriceModalOpen(false)}
        >
          <form onSubmit={handleUpdatePriceVersion} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                Regular Subscription Price ({selectedRegion.currency}) *
              </label>
              <Input
                type="number"
                step="0.01"
                required
                value={editPriceForm.list_price}
                onChange={(e) => setEditPriceForm({ ...editPriceForm, list_price: e.target.value })}
              />
            </div>

            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                Additional Member Rate (Optional) ({selectedRegion.currency})
              </label>
              <Input
                type="number"
                step="0.01"
                value={editPriceForm.additional_member_list_price}
                onChange={(e) => setEditPriceForm({ ...editPriceForm, additional_member_list_price: e.target.value })}
              />
            </div>

            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                Operational Reason *
              </label>
              <Input
                required
                placeholder="e.g. Commercial discount adjustment / seasonal revision"
                value={editPriceForm.reason}
                onChange={(e) => setEditPriceForm({ ...editPriceForm, reason: e.target.value })}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px' }}>
              <input
                type="checkbox"
                id="price-active-check"
                checked={editPriceForm.is_active}
                onChange={(e) => setEditPriceForm({ ...editPriceForm, is_active: e.target.checked })}
              />
              <label htmlFor="price-active-check" style={{ fontSize: '13px', fontWeight: 600, color: '#334155', cursor: 'pointer' }}>
                Price Version Active
              </label>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '12px' }}>
              <Button variant="secondary" type="button" onClick={() => setIsEditPriceModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" type="submit" disabled={isSubmittingEditPrice}>
                {isSubmittingEditPrice ? 'Saving...' : 'Save Price Version'}
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
