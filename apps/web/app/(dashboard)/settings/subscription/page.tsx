'use client';

import React, { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import {
  CreditCard,
  CheckCircle2,
  AlertCircle,
  Clock,
  Users,
  ShieldCheck,
  Sparkles,
  ArrowRight,
  Info,
  Tag
} from 'lucide-react';

interface MemberEntitlement {
  user_id: string;
  display_name: string;
  role: string;
  is_free_entitled: boolean;
  is_seat_covered: boolean;
}

interface SubscriptionOverviewState {
  status: string;
  plan_name: string;
  currency: string;
  billing_period: string;
  list_price: number;
  additional_member_list_price: number;
  discount_type: string;
  discount_value: number;
  discount_amount: number;
  effective_price: number;
  promotion_code: string;
  days_remaining: number;
  is_in_introductory_trial: boolean;
  total_active_members: number;
  free_entitled_seats: number;
  required_paid_seats: number;
  active_paid_seats: number;
  is_fully_covered: boolean;
  annual_total_price: number;
  members: MemberEntitlement[];
}

export default function SubscriptionPage() {
  const [overview, setOverview] = useState<SubscriptionOverviewState>({
    status: 'TRIALING',
    plan_name: 'Ozhzo Home Standard',
    currency: 'USD',
    billing_period: 'ANNUAL',
    list_price: 0,
    additional_member_list_price: 20.00,
    discount_type: 'PERCENTAGE',
    discount_value: 50.00,
    discount_amount: 10.00,
    effective_price: 10.00,
    promotion_code: 'LAUNCH50',
    days_remaining: 365,
    is_in_introductory_trial: true,
    total_active_members: 3,
    free_entitled_seats: 1,
    required_paid_seats: 2,
    active_paid_seats: 2,
    is_fully_covered: true,
    annual_total_price: 20.00,
    members: [
      { user_id: '1', display_name: 'Home Owner', role: 'OWNER', is_free_entitled: true, is_seat_covered: true },
      { user_id: '2', display_name: 'Family Member 1', role: 'MEMBER', is_free_entitled: false, is_seat_covered: true },
      { user_id: '3', display_name: 'Family Member 2', role: 'CHILD', is_free_entitled: false, is_seat_covered: true },
    ]
  });

  const [seats, setSeats] = useState(2);

  // Dynamic currency symbol formatter
  const formatCurrency = (amount: number, currency: string) => {
    try {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency || 'USD',
      }).format(amount);
    } catch {
      return `${currency} ${amount.toFixed(2)}`;
    }
  };

  const handleUpdateSeats = (newSeats: number) => {
    if (newSeats < 0) return;
    setSeats(newSeats);
    const newTotal = newSeats * overview.effective_price;
    setOverview(prev => ({
      ...prev,
      active_paid_seats: newSeats,
      annual_total_price: newTotal,
      is_fully_covered: newSeats >= prev.required_paid_seats
    }));
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '900px' }}>
      {/* Header */}
      <div>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-primary-900)' }}>
          Household Subscription & Dynamic Entitlements
        </h1>
        <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)' }}>
          Transparent, data-driven pricing: Standard List Price + Promotional Discount = Effective Customer Price.
        </p>
      </div>

      {/* Trial Status Card */}
      <Card style={{ border: '2px solid var(--color-primary-900)', backgroundColor: 'var(--color-surface-overlay)' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-3)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ width: '44px', height: '44px', borderRadius: '50%', backgroundColor: 'var(--color-primary-900)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Sparkles size={22} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ fontSize: '17px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                  {overview.plan_name}
                </h2>
                <Badge variant="in-stock">
                  {overview.is_in_introductory_trial ? 'Introductory Period Active' : overview.status}
                </Badge>
                {overview.promotion_code && (
                  <Badge variant="neutral">Promo: {overview.promotion_code}</Badge>
                )}
              </div>
              <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
                {overview.days_remaining} days remaining in current billing cycle ({overview.billing_period.toLowerCase()}).
              </p>
            </div>
          </div>

          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--color-primary-900)' }}>
              {formatCurrency(overview.annual_total_price, overview.currency)}{' '}
              <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--color-text-secondary)' }}>
                / {overview.billing_period.toLowerCase()}
              </span>
            </div>
            <span style={{ fontSize: '12px', color: 'var(--color-text-tertiary)' }}>
              {overview.active_paid_seats} additional member seat(s)
            </span>
          </div>
        </div>
      </Card>

      {/* Dynamic Pricing Model Breakdown */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 'var(--space-4)' }}>
        <Card variant="subtle">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <ShieldCheck size={18} color="var(--status-in-stock)" />
            <h3 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-primary-900)' }}>Home Admin / Custodian</h3>
          </div>
          <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--color-primary-900)' }}>
            {overview.is_in_introductory_trial ? 'Free for 1st Year' : formatCurrency(overview.list_price, overview.currency)}
          </div>
          <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
            Configurable introductory offer includes primary home creator and custodian.
          </p>
        </Card>

        <Card variant="subtle">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <Tag size={18} color="var(--color-primary-900)" />
            <h3 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-primary-900)' }}>Standard List Price</h3>
          </div>
          <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--color-text-secondary)', textDecoration: 'line-through' }}>
            {formatCurrency(overview.additional_member_list_price, overview.currency)}{' '}
            <span style={{ fontSize: '13px', fontWeight: 500 }}>
              / user / {overview.billing_period.toLowerCase()}
            </span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
            Standard published seat list price before promotional discounts.
          </p>
        </Card>

        <Card variant="subtle">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <Users size={18} color="var(--color-primary-900)" />
            <h3 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-primary-900)' }}>Effective Customer Price</h3>
          </div>
          <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--color-primary-900)' }}>
            {formatCurrency(overview.effective_price, overview.currency)}{' '}
            <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--status-in-stock)' }}>
              ({overview.discount_value}% OFF)
            </span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
            Active promotion: <strong>{overview.promotion_code}</strong> ({formatCurrency(overview.discount_amount, overview.currency)} discount/seat).
          </p>
        </Card>
      </div>

      {/* Member Entitlement Breakdown */}
      <Card>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
              Member Entitlements & Seat Allocation
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
              Breakdown of free introductory entitlement vs. dynamically allocated paid seats.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Button size="sm" variant="secondary" onClick={() => handleUpdateSeats(seats - 1)} disabled={seats <= 0}>
              -
            </Button>
            <span style={{ fontSize: '14px', fontWeight: 700, minWidth: '60px', textAlign: 'center' }}>
              {seats} Seats
            </span>
            <Button size="sm" variant="secondary" onClick={() => handleUpdateSeats(seats + 1)}>
              +
            </Button>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
          {overview.members.map((m) => (
            <div
              key={m.user_id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px 16px',
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'var(--color-surface-subtle)'
              }}
            >
              <div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                  {m.display_name}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                  Role: {m.role}
                </div>
              </div>

              <div>
                {m.is_free_entitled ? (
                  <Badge variant="in-stock">Free Admin Entitlement</Badge>
                ) : m.is_seat_covered ? (
                  <Badge variant="neutral">Paid Member Seat</Badge>
                ) : (
                  <Badge variant="overdue">Uncovered Seat</Badge>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
