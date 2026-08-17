'use client';

import React, { useEffect, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import {
  Users,
  ShieldCheck,
  Sparkles,
  Tag
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

interface MemberEntitlement {
  user_id: string;
  display_name: string;
  role: string;
  is_free_entitled: boolean;
  is_seat_covered: boolean;
}

interface MemberDTO {
  id: string;
  user_id: string;
  display_name: string;
  phone_number?: string | null;
  email?: string | null;
  role: string;
  status: string;
}

export default function SubscriptionPage() {
  const [members, setMembers] = useState<MemberDTO[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const [seats, setSeats] = useState(0);

  const planName = 'Ozhzo Home Standard';
  const currency = 'USD';
  const additionalMemberListPrice = 20.00;
  const discountPercent = 50.00;
  const discountAmount = 10.00;
  const effectivePrice = 10.00;
  const promotionCode = 'LAUNCH50';

  useEffect(() => {
    const loadSubscriptionAndMembers = async () => {
      setIsLoading(true);
      try {
        const savedHomeId = localStorage.getItem('active_home_id');
        let homeId = savedHomeId;

        if (!homeId) {
          const homes = await apiClient.get<Array<{ id: string }>>('/homes');
          if (homes && homes.length > 0) {
            homeId = homes[0].id;
            localStorage.setItem('active_home_id', homeId);
          }
        }

        if (homeId) {
          const membersData = await apiClient.get<MemberDTO[]>(`/homes/${homeId}/members`);
          setMembers(membersData || []);
          const requiredPaid = Math.max(0, (membersData?.length || 1) - 1);
          setSeats(requiredPaid);
        }
      } catch (err) {
        console.error('Failed to load subscription members:', err);
        setMembers([]);
      } finally {
        setIsLoading(false);
      }
    };

    loadSubscriptionAndMembers();
  }, []);

  const formatCurrency = (amount: number, curr: string) => {
    try {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: curr || 'USD',
      }).format(amount);
    } catch {
      return `${curr} ${amount.toFixed(2)}`;
    }
  };

  const handleUpdateSeats = (newSeats: number) => {
    if (newSeats < 0) return;
    setSeats(newSeats);
  };

  const totalMembers = members.length || 1;
  const freeEntitledSeats = 1;
  const requiredPaidSeats = Math.max(0, totalMembers - freeEntitledSeats);
  const isFullyCovered = seats >= requiredPaidSeats;
  const annualTotalPrice = seats * effectivePrice;

  const memberEntitlements: MemberEntitlement[] = members.map((m, index) => {
    const isFree = index === 0;
    const isCovered = isFree || (index <= seats);
    return {
      user_id: m.user_id,
      display_name: m.display_name,
      role: m.role,
      is_free_entitled: isFree,
      is_seat_covered: isCovered
    };
  });

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
                  {planName}
                </h2>
                <Badge variant={isFullyCovered ? 'in-stock' : 'overdue'}>
                  {isFullyCovered ? 'Seats Covered' : 'Additional Seats Needed'}
                </Badge>
                <Badge variant="neutral">Promo: {promotionCode}</Badge>
              </div>
              <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
                Annual household custody plan with multi-seat member synchronization.
              </p>
            </div>
          </div>

          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--color-primary-900)' }}>
              {formatCurrency(annualTotalPrice, currency)} / year
            </div>
            <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
              365 Days Remaining
            </div>
          </div>
        </div>
      </Card>

      {/* Pricing Breakdown Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 'var(--space-4)' }}>
        <Card variant="subtle">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <ShieldCheck size={18} color="var(--color-primary-900)" />
            <h3 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-primary-900)' }}>Standard List Price</h3>
          </div>
          <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--color-primary-900)' }}>
            {formatCurrency(additionalMemberListPrice, currency)}{' '}
            <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--color-text-secondary)' }}>
              / additional member / yr
            </span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
            Includes 1 free Home Admin account plus shared memory storage.
          </p>
        </Card>

        <Card variant="subtle">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <Tag size={18} color="var(--status-low-stock)" />
            <h3 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-primary-900)' }}>Launch Promotion Discount</h3>
          </div>
          <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--status-in-stock)' }}>
            -{discountPercent}% OFF
          </div>
          <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
            Standard promotional deduction: -{formatCurrency(discountAmount, currency)}/seat.
          </p>
        </Card>

        <Card variant="subtle">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <Users size={18} color="var(--color-primary-900)" />
            <h3 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-primary-900)' }}>Effective Customer Price</h3>
          </div>
          <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--color-primary-900)' }}>
            {formatCurrency(effectivePrice, currency)}{' '}
            <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--status-in-stock)' }}>
              ({discountPercent}% OFF)
            </span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
            Active promotion: <strong>{promotionCode}</strong> ({formatCurrency(discountAmount, currency)} discount/seat).
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
              Breakdown of free introductory entitlement vs. dynamically allocated paid seats for current Home members ({totalMembers} active).
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

        {isLoading ? (
          <div style={{ height: '80px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: 'var(--radius-md)', animation: 'pulse 1.5s infinite' }} />
        ) : memberEntitlements.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 'var(--space-6)', color: 'var(--color-text-secondary)', fontSize: '14px' }}>
            No household members found for active Home workspace.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            {memberEntitlements.map((m) => (
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
        )}
      </Card>
    </div>
  );
}
