'use client';

import React, { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Home, Shield, Trash2, Check, AlertCircle } from 'lucide-react';

export default function HomeSettingsPage() {
  const [homeName, setHomeName] = useState('Rivera Family Home');
  const [currency, setCurrency] = useState('USD');
  const [timezone, setTimezone] = useState('America/New_York');
  const [address, setAddress] = useState('742 Evergreen Terrace, Springfield');
  const [isSaving, setIsSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setSavedSuccess(false);

    // Simulate API update PATCH /api/v1/homes/{home_id}
    setTimeout(() => {
      setIsSaving(false);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    }, 600);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '800px' }}>
      <div>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-primary-900)' }}>
          Home Settings & Profile
        </h1>
        <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)' }}>
          Manage your household name, localization preferences, and workspace custody.
        </p>
      </div>

      {savedSuccess && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 14px', backgroundColor: 'var(--status-in-stock-bg)', color: 'var(--status-in-stock)', borderRadius: 'var(--radius-md)', fontSize: '13px', fontWeight: 600 }}>
          <Check size={16} />
          <span>Home settings updated successfully.</span>
        </div>
      )}

      {/* General Home Profile */}
      <Card>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)', paddingBottom: 'var(--space-3)', borderBottom: '1px solid var(--color-border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Home size={18} color="var(--color-primary-900)" />
            <h2 style={{ fontSize: '16px', fontWeight: 600 }}>Household Profile</h2>
          </div>
          <Badge variant="in-stock">OWNER</Badge>
        </div>

        <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <Input
            id="homeName"
            label="Household Name"
            value={homeName}
            onChange={(e) => setHomeName(e.target.value)}
            required
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
          />

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 'var(--space-2)' }}>
            <Button type="submit" isLoading={isSaving}>
              Save Changes
            </Button>
          </div>
        </form>
      </Card>

      {/* Danger Zone: Delete Workspace */}
      <Card style={{ borderColor: 'var(--status-overdue-bg)', backgroundColor: '#fffcfc' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: 'var(--space-2)', color: 'var(--status-overdue)' }}>
          <AlertCircle size={18} />
          <h2 style={{ fontSize: '16px', fontWeight: 600 }}>Danger Zone</h2>
        </div>
        <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-4)', lineHeight: 1.5 }}>
          Deleting a Home workspace will soft-archive all associated inventory, chores, bills, and calendar records. Only the Home Owner can perform this action.
        </p>
        <Button variant="destructive">
          <Trash2 size={16} />
          <span>Delete This Home</span>
        </Button>
      </Card>
    </div>
  );
}
