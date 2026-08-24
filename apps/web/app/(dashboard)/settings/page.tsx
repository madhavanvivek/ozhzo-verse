'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import {
  Home,
  Users,
  CreditCard,
  Trash2,
  Check,
  AlertCircle,
  ChevronRight
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

interface HomeDetailDTO {
  id: string;
  name: string;
  country?: string | null;
  currency: string;
  timezone: string;
  address?: string | null;
  role: string;
  members_count: number;
}

export default function HomeSettingsPage() {
  const router = useRouter();
  const [activeHomeId, setActiveHomeId] = useState<string | null>(null);
  const [homeDetail, setHomeDetail] = useState<HomeDetailDTO | null>(null);
  const [homeName, setHomeName] = useState('');
  const [currency, setCurrency] = useState('USD');
  const [timezone, setTimezone] = useState('UTC');
  const [address, setAddress] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    const loadHomeSettings = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const homeId = await apiClient.getValidActiveHome();
        setActiveHomeId(homeId);

        if (homeId) {
          const data = await apiClient.get<HomeDetailDTO>(`/homes/${homeId}`);
          setHomeDetail(data);
          setHomeName(data.name || '');
          setCurrency(data.currency || 'USD');
          setTimezone(data.timezone || 'UTC');
          setAddress(data.address || '');
        }
      } catch (err: any) {
        console.error('Failed to load home settings:', err);
        setError(err?.message || 'Failed to load household profile.');
      } finally {
        setIsLoading(false);
      }
    };

    loadHomeSettings();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeHomeId || !homeName.trim()) return;

    setIsSaving(true);
    setSavedSuccess(false);
    setError(null);

    try {
      const updated = await apiClient.patch<HomeDetailDTO>(`/homes/${activeHomeId}`, {
        name: homeName.trim(),
        currency,
        timezone,
        address: address.trim() || undefined
      });

      setHomeDetail((prev) => (prev ? { ...prev, ...updated } : updated));
      setSavedSuccess(true);
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new Event('home-changed'));
      }
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err: any) {
      console.error('Failed to update home settings:', err);
      setError(err?.message || 'Failed to update home settings.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteHome = async () => {
    if (!activeHomeId) return;
    if (!confirm('Are you sure you want to delete this Home workspace? This action will archive all household data.')) return;

    setIsDeleting(true);
    try {
      await apiClient.delete(`/homes/${activeHomeId}`);
      localStorage.removeItem('active_home_id');
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new Event('home-changed'));
      }
      router.push('/dashboard');
    } catch (err: any) {
      console.error('Failed to delete home:', err);
      alert(err?.message || 'Failed to delete home workspace.');
      setIsDeleting(false);
    }
  };

  const isOwnerOrAdmin = homeDetail?.role === 'OWNER' || homeDetail?.role === 'HOME_ADMIN';

  if (isLoading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '800px' }}>
        <div style={{ height: '60px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: 'var(--radius-md)', animation: 'pulse 1.5s infinite' }} />
        <div style={{ height: '260px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: 'var(--radius-lg)' }} />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '800px' }}>
      <div>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-primary-900)' }}>
          Home Settings & Management
        </h1>
        <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)' }}>
          Manage household details, family members, subscriptions, and workspace settings for your active home.
        </p>
      </div>

      {savedSuccess && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 14px', backgroundColor: 'var(--status-in-stock-bg)', color: 'var(--status-in-stock)', borderRadius: 'var(--radius-md)', fontSize: '13px', fontWeight: 600 }}>
          <Check size={16} />
          <span>Home settings updated successfully.</span>
        </div>
      )}

      {error && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 14px', backgroundColor: 'var(--status-overdue-bg)', color: 'var(--status-overdue)', borderRadius: 'var(--radius-md)', fontSize: '13px', fontWeight: 500 }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Family Members Navigation Card */}
      <Card style={{ border: '2px solid var(--color-primary-900)', backgroundColor: 'var(--color-surface-overlay)', padding: 'var(--space-5)' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-3)', marginBottom: 'var(--space-3)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ width: '40px', height: '40px', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--color-primary-900)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Users size={22} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ fontSize: '17px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                  Family Members
                </h2>
                {homeDetail?.members_count !== undefined && (
                  <Badge variant="neutral">
                    {homeDetail.members_count} {homeDetail.members_count === 1 ? 'Member' : 'Members'}
                  </Badge>
                )}
              </div>
              <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
                Manage the people who belong to this Home, their roles and invitations.
              </p>
            </div>
          </div>

          <Link
            href="/members"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'var(--color-primary-900)',
              color: 'var(--color-text-inverse)',
              fontSize: '13px',
              fontWeight: 600,
              textDecoration: 'none',
              transition: 'background-color 0.15s ease'
            }}
          >
            <span>Manage Members</span>
            <ChevronRight size={16} />
          </Link>
        </div>

        <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', paddingTop: 'var(--space-3)', borderTop: '1px solid var(--color-border-subtle)' }}>
          Invite co-parents, children, guests, and manage access permissions for <strong>{homeDetail?.name || 'this Home'}</strong>.
        </div>
      </Card>

      {/* General Home Profile */}
      <Card>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)', paddingBottom: 'var(--space-3)', borderBottom: '1px solid var(--color-border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Home size={18} color="var(--color-primary-900)" />
            <h2 style={{ fontSize: '16px', fontWeight: 600 }}>Household Profile</h2>
          </div>
          {homeDetail?.role && (
            <Badge variant={isOwnerOrAdmin ? 'completed' : 'neutral'}>
              Your Role: {homeDetail.role}
            </Badge>
          )}
        </div>

        <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <Input
            id="homeName"
            label="Household Name"
            value={homeName}
            onChange={(e) => setHomeName(e.target.value)}
            required
            disabled={!isOwnerOrAdmin}
          />

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label htmlFor="currency" style={{ fontSize: '13px', fontWeight: 600 }}>
                Primary Currency
              </label>
              <select
                id="currency"
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                disabled={!isOwnerOrAdmin}
                style={{
                  height: '42px',
                  padding: '0 12px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border-strong)',
                  backgroundColor: 'var(--color-surface-card)',
                  color: 'var(--color-text-primary)',
                  fontSize: '14px'
                }}
              >
                <option value="USD">USD ($ - US Dollar)</option>
                <option value="EUR">EUR (€ - Euro)</option>
                <option value="GBP">GBP (£ - British Pound)</option>
                <option value="CAD">CAD ($ - Canadian Dollar)</option>
                <option value="AUD">AUD ($ - Australian Dollar)</option>
                <option value="INR">INR (₹ - Indian Rupee)</option>
              </select>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label htmlFor="timezone" style={{ fontSize: '13px', fontWeight: 600 }}>
                Household Timezone
              </label>
              <select
                id="timezone"
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                disabled={!isOwnerOrAdmin}
                style={{
                  height: '42px',
                  padding: '0 12px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border-strong)',
                  backgroundColor: 'var(--color-surface-card)',
                  color: 'var(--color-text-primary)',
                  fontSize: '14px'
                }}
              >
                <option value="America/New_York">America/New York (EST/EDT)</option>
                <option value="America/Chicago">America/Chicago (CST/CDT)</option>
                <option value="America/Los_Angeles">America/Los Angeles (PST/PDT)</option>
                <option value="Europe/London">Europe/London (GMT/BST)</option>
                <option value="Europe/Paris">Europe/Paris (CET/CEST)</option>
                <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
                <option value="UTC">UTC</option>
              </select>
            </div>
          </div>

          <Input
            id="address"
            label="Address / Location (Optional)"
            placeholder="e.g. 123 Main St, Apt 4B"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            disabled={!isOwnerOrAdmin}
          />

          {isOwnerOrAdmin && (
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 'var(--space-2)' }}>
              <Button type="submit" isLoading={isSaving}>
                Save Changes
              </Button>
            </div>
          )}
        </form>
      </Card>

      {/* Household Subscription */}
      <Card style={{ padding: 'var(--space-5)' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-3)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ width: '40px', height: '40px', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--color-surface-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <CreditCard size={20} color="var(--color-primary-900)" />
            </div>
            <div>
              <h2 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-primary-900)' }}>
                Household Subscription & Entitlements
              </h2>
              <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
                View seat allocations, standard list pricing, and introductory promotional discounts.
              </p>
            </div>
          </div>

          <Link
            href="/settings/subscription"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-border)',
              backgroundColor: 'var(--color-surface-card)',
              color: 'var(--color-text-primary)',
              fontSize: '13px',
              fontWeight: 600,
              textDecoration: 'none'
            }}
          >
            <span>View Subscription</span>
            <ChevronRight size={16} />
          </Link>
        </div>
      </Card>

      {/* Danger Zone: Delete Workspace */}
      {isOwnerOrAdmin && (
        <Card style={{ borderColor: 'var(--status-overdue-bg)', backgroundColor: '#fffcfc' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: 'var(--space-2)', color: 'var(--status-overdue)' }}>
            <AlertCircle size={18} />
            <h2 style={{ fontSize: '16px', fontWeight: 600 }}>Danger Zone</h2>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-4)', lineHeight: 1.5 }}>
            Deleting a Home workspace will soft-archive all associated inventory, chores, bills, and calendar records. Only a Home Admin or Owner can perform this action.
          </p>
          <Button variant="destructive" onClick={handleDeleteHome} isLoading={isDeleting}>
            <Trash2 size={16} />
            <span>Delete This Home</span>
          </Button>
        </Card>
      )}
    </div>
  );
}
