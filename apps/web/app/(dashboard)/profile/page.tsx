'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import {
  User,
  Mail,
  Phone,
  Home,
  Shield,
  Calendar,
  Globe,
  CheckCircle2,
  AlertCircle,
  LogOut,
  Edit2,
  KeyRound,
  RefreshCw
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

interface HomeMembershipSummary {
  home_id: string;
  name: string;
  role: string;
  status: string;
  avatar_url?: string | null;
}

interface UserProfileDTO {
  id: string;
  phone_number?: string | null;
  country_code?: string | null;
  email?: string | null;
  display_name: string;
  avatar_url?: string | null;
  timezone: string;
  preferred_language: string;
  is_active: boolean;
  is_verified: boolean;
  mobile_verified: boolean;
  created_at?: string | null;
  updated_at?: string | null;
  homes: HomeMembershipSummary[];
}

export default function ProfilePage() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfileDTO | null>(null);
  const [activeHomeId, setActiveHomeId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit display name state
  const [isEditing, setIsEditing] = useState(false);
  const [editDisplayName, setEditDisplayName] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Password change state
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [isSavingPassword, setIsSavingPassword] = useState(false);

  const fetchProfile = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<UserProfileDTO>('/users/me');
      setProfile(data);
      setEditDisplayName(data.display_name);

      const homeId = await apiClient.getValidActiveHome();
      setActiveHomeId(homeId);
    } catch (err: any) {
      console.error('Failed to fetch user profile:', err);
      setError(err?.message || 'Unable to load profile. Please verify your connection.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editDisplayName.trim()) return;

    setIsSaving(true);
    setSaveSuccess(false);
    try {
      const updated = await apiClient.patch<UserProfileDTO>('/users/me', {
        display_name: editDisplayName.trim()
      });
      setProfile((prev) => (prev ? { ...prev, display_name: updated.display_name } : updated));
      setIsEditing(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: any) {
      console.error('Failed to update profile:', err);
      setError(err?.message || 'Failed to update profile.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(false);

    if (newPassword.length < 8) {
      setPasswordError('New password must be at least 8 characters long.');
      return;
    }

    setIsSavingPassword(true);
    try {
      await apiClient.patch('/users/me/password', {
        current_password: currentPassword,
        new_password: newPassword
      });
      setPasswordSuccess(true);
      setCurrentPassword('');
      setNewPassword('');
      setIsChangingPassword(false);
      setTimeout(() => setPasswordSuccess(false), 4000);
    } catch (err: any) {
      console.error('Failed to change password:', err);
      setPasswordError(err?.message || 'Failed to update password. Verify your current password.');
    } finally {
      setIsSavingPassword(false);
    }
  };

  const handleSignOut = () => {
    apiClient.clearSession();
    router.push('/login');
  };

  const getInitials = (name?: string | null): string => {
    if (!name || !name.trim()) return 'U';
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) {
      return parts[0].substring(0, 2).toUpperCase();
    }
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  };

  if (isLoading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '850px' }}>
        <div style={{ height: '60px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: 'var(--radius-md)', animation: 'pulse 1.5s infinite' }} />
        <div style={{ height: '240px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: 'var(--radius-lg)' }} />
      </div>
    );
  }

  if (error && !profile) {
    return (
      <div style={{ padding: 'var(--space-8)', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--space-4)' }}>
        <AlertCircle size={36} color="var(--status-overdue)" />
        <h2 style={{ fontSize: '18px', fontWeight: 700 }}>Something went wrong</h2>
        <p style={{ color: 'var(--color-text-secondary)', maxWidth: '400px', fontSize: '14px' }}>{error}</p>
        <Button onClick={fetchProfile} variant="secondary">
          <RefreshCw size={16} />
          <span>Try Again</span>
        </Button>
      </div>
    );
  }

  const activeHome = profile?.homes.find((h) => h.home_id === activeHomeId) || profile?.homes[0];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '850px' }}>
      {/* Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-3)' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-primary-900)', letterSpacing: '-0.02em' }}>
            Account & Profile
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)' }}>
            Manage your personal details, household memberships, and security credentials.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <Button variant="secondary" size="sm" onClick={handleSignOut} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <LogOut size={14} />
            <span>Sign Out</span>
          </Button>
        </div>
      </div>

      {saveSuccess && (
        <div style={{ padding: '10px 14px', backgroundColor: 'var(--status-in-stock-bg)', color: 'var(--status-in-stock)', borderRadius: 'var(--radius-md)', fontSize: '13px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <CheckCircle2 size={16} />
          <span>Profile updated successfully.</span>
        </div>
      )}

      {passwordSuccess && (
        <div style={{ padding: '10px 14px', backgroundColor: 'var(--status-in-stock-bg)', color: 'var(--status-in-stock)', borderRadius: 'var(--radius-md)', fontSize: '13px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <CheckCircle2 size={16} />
          <span>Password changed successfully.</span>
        </div>
      )}

      {/* Profile Overview Card */}
      <Card style={{ padding: 'var(--space-6)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', flexWrap: 'wrap' }}>
          <div
            style={{
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              backgroundColor: 'var(--color-primary-900)',
              color: 'var(--color-text-inverse)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '24px',
              fontWeight: 700,
              flexShrink: 0
            }}
          >
            {getInitials(profile?.display_name)}
          </div>

          <div style={{ flex: 1, minWidth: '220px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
              <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                {profile?.display_name || 'User'}
              </h2>
              {profile?.is_active ? (
                <Badge variant="completed">Active Account</Badge>
              ) : (
                <Badge variant="neutral">Inactive</Badge>
              )}
            </div>

            <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
              {activeHome ? `${activeHome.name} • ${activeHome.role}` : 'No active household assigned'}
            </p>
          </div>

          <div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setIsEditing(!isEditing)}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <Edit2 size={14} />
              <span>{isEditing ? 'Cancel' : 'Edit Profile'}</span>
            </Button>
          </div>
        </div>

        {/* Edit Form */}
        {isEditing && (
          <form onSubmit={handleUpdateProfile} style={{ marginTop: 'var(--space-4)', paddingTop: 'var(--space-4)', borderTop: '1px solid var(--color-border-subtle)', display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', maxWidth: '400px' }}>
            <Input
              id="displayNameInput"
              type="text"
              label="Display Name"
              value={editDisplayName}
              onChange={(e) => setEditDisplayName(e.target.value)}
              required
            />
            <div style={{ display: 'flex', gap: '8px' }}>
              <Button type="submit" size="sm" isLoading={isSaving}>
                Save Changes
              </Button>
              <Button type="button" variant="ghost" size="sm" onClick={() => setIsEditing(false)}>
                Cancel
              </Button>
            </div>
          </form>
        )}
      </Card>

      {/* Account Details Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 'var(--space-4)' }}>
        {/* Contact & Identity Card */}
        <Card style={{ padding: 'var(--space-6)' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-primary-900)', marginBottom: 'var(--space-4)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <User size={18} />
            <span>Personal Information</span>
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', fontSize: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', paddingBottom: '8px', borderBottom: '1px solid var(--color-border-subtle)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-text-secondary)' }}>
                <Phone size={16} />
                <span>Mobile Number</span>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>
                  {profile?.phone_number || 'Not available'}
                </div>
                {profile?.phone_number && (
                  <span style={{ fontSize: '11px', color: profile.mobile_verified ? 'var(--status-in-stock)' : 'var(--color-text-tertiary)', fontWeight: 600 }}>
                    {profile.mobile_verified ? '✓ Verified' : 'Unverified'}
                  </span>
                )}
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', paddingBottom: '8px', borderBottom: '1px solid var(--color-border-subtle)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-text-secondary)' }}>
                <Mail size={16} />
                <span>Email Address</span>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>
                  {profile?.email || 'Not available'}
                </div>
                {profile?.email && (
                  <span style={{ fontSize: '11px', color: profile.is_verified ? 'var(--status-in-stock)' : 'var(--color-text-tertiary)', fontWeight: 600 }}>
                    {profile.is_verified ? '✓ Verified' : 'Unverified'}
                  </span>
                )}
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '8px', borderBottom: '1px solid var(--color-border-subtle)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-text-secondary)' }}>
                <Globe size={16} />
                <span>Timezone & Language</span>
              </div>
              <span style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>
                {profile?.timezone || 'UTC'} ({profile?.preferred_language?.toUpperCase() || 'EN'})
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--color-text-secondary)' }}>
                <Calendar size={16} />
                <span>Member Since</span>
              </div>
              <span style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>
                {profile?.created_at
                  ? new Date(profile.created_at).toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' })
                  : 'Not available'}
              </span>
            </div>
          </div>
        </Card>

        {/* Security & Password Card */}
        <Card style={{ padding: 'var(--space-6)' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-primary-900)', marginBottom: 'var(--space-4)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Shield size={18} />
            <span>Security & Authentication</span>
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
            <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
              Manage password credentials and active session authentication.
            </div>

            {passwordError && (
              <div style={{ padding: '8px 12px', backgroundColor: 'var(--status-overdue-bg)', color: 'var(--status-overdue)', borderRadius: 'var(--radius-md)', fontSize: '13px', fontWeight: 500 }}>
                {passwordError}
              </div>
            )}

            {!isChangingPassword ? (
              <div>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setIsChangingPassword(true)}
                  style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <KeyRound size={14} />
                  <span>Change Password</span>
                </Button>
              </div>
            ) : (
              <form onSubmit={handleChangePassword} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                <Input
                  id="currPassword"
                  type="password"
                  label="Current Password"
                  placeholder="••••••••"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  required
                />

                <Input
                  id="newPassword"
                  type="password"
                  label="New Password (min 8 chars)"
                  placeholder="••••••••"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                />

                <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                  <Button type="submit" size="sm" isLoading={isSavingPassword}>
                    Update Password
                  </Button>
                  <Button type="button" variant="ghost" size="sm" onClick={() => setIsChangingPassword(false)}>
                    Cancel
                  </Button>
                </div>
              </form>
            )}
          </div>
        </Card>
      </div>

      {/* Household Memberships */}
      <Card style={{ padding: 'var(--space-6)' }}>
        <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-primary-900)', marginBottom: 'var(--space-4)', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Home size={18} />
          <span>Household Memberships</span>
        </h3>

        {!profile?.homes || profile.homes.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 'var(--space-4)', color: 'var(--color-text-secondary)', fontSize: '14px' }}>
            You have not joined any Home yet.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {profile.homes.map((h) => {
              const isCurrent = h.home_id === activeHomeId;
              return (
                <div
                  key={h.home_id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '12px 16px',
                    borderRadius: 'var(--radius-md)',
                    backgroundColor: isCurrent ? 'var(--color-surface-subtle)' : 'transparent',
                    border: '1px solid var(--color-border-subtle)'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ width: '36px', height: '36px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--color-primary-900)', color: 'var(--color-text-inverse)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '14px' }}>
                      {h.name.substring(0, 1).toUpperCase()}
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '14px', color: 'var(--color-text-primary)' }}>
                        {h.name}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                        Role: <strong>{h.role}</strong> • Status: {h.status}
                      </div>
                    </div>
                  </div>

                  <div>
                    {isCurrent ? (
                      <Badge variant="completed">Active Home</Badge>
                    ) : (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => {
                          localStorage.setItem('active_home_id', h.home_id);
                          setActiveHomeId(h.home_id);
                          window.location.reload();
                        }}
                      >
                        Switch
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
}
