'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  ArrowLeft,
  User,
  CheckCircle,
  RefreshCw,
  Home,
  UserX,
  UserCheck
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';
import { AdminBadge } from '../../components/AdminBadge';
import { AdminConfirmModal } from '../../components/AdminConfirmModal';
import { AdminUserDetail } from '../../types';

export default function AdminUserDetailPage() {
  const params = useParams();
  const userId = params.id as string;

  const [user, setUser] = useState<AdminUserDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Modal State
  const [isSuspendModalOpen, setIsSuspendModalOpen] = useState(false);
  const [isReactivateModalOpen, setIsReactivateModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const fetchUserDetail = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<AdminUserDetail>(`/admin/users/${userId}`);
      setUser(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to retrieve user details.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (userId) {
      fetchUserDetail();
    }
  }, [userId]);

  const handleSuspend = async (reason: string) => {
    setIsSubmitting(true);
    setModalError(null);
    setActionSuccess(null);
    try {
      await apiClient.post(`/admin/users/${userId}/suspend`, {
        reason: reason || 'Administrative suspension'
      });
      setIsSuspendModalOpen(false);
      setActionSuccess('User account was successfully suspended and deactivated.');
      fetchUserDetail();
    } catch (err: any) {
      setModalError(err?.message || 'Failed to suspend user.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReactivate = async (reason: string) => {
    setIsSubmitting(true);
    setModalError(null);
    setActionSuccess(null);
    try {
      await apiClient.post(`/admin/users/${userId}/reactivate`, {
        reason: reason || 'Administrative reactivation'
      });
      setIsReactivateModalOpen(false);
      setActionSuccess('User account was successfully reactivated.');
      fetchUserDetail();
    } catch (err: any) {
      setModalError(err?.message || 'Failed to reactivate user.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return '—';
    try {
      return new Date(dateStr).toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  if (isLoading) {
    return (
      <div
        style={{
          padding: '60px 24px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '12px',
          color: 'var(--color-text-secondary, #64748b)'
        }}
      >
        <RefreshCw size={28} className="animate-spin" color="var(--color-accent-warm, #f97316)" />
        <span style={{ fontSize: '15px', fontWeight: 600 }}>Loading user record...</span>
      </div>
    );
  }

  if (error || !user) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <Link
          href="/admin/users"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            color: 'var(--color-text-secondary, #64748b)',
            fontSize: '14px',
            fontWeight: 600
          }}
        >
          <ArrowLeft size={16} />
          <span>Back to Users List</span>
        </Link>
        <div
          style={{
            padding: '24px',
            backgroundColor: 'var(--status-overdue-bg, #fef2f2)',
            border: '1px solid #fecaca',
            borderRadius: 'var(--radius-lg, 16px)',
            color: 'var(--status-overdue, #ef4444)'
          }}
        >
          <h2 style={{ fontSize: '18px', fontWeight: 700, margin: '0 0 8px' }}>User Record Not Found</h2>
          <p style={{ fontSize: '14px', margin: 0 }}>{error || 'Unable to locate user account.'}</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Navigation Breadcrumb */}
      <div>
        <Link
          href="/admin/users"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            color: 'var(--color-text-secondary, #64748b)',
            fontSize: '14px',
            fontWeight: 600,
            minHeight: '44px'
          }}
        >
          <ArrowLeft size={16} />
          <span>Back to Users List</span>
        </Link>
      </div>

      {/* Success Notification */}
      {actionSuccess && (
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
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* Profile Header Card */}
      <div
        style={{
          backgroundColor: 'var(--color-surface-card, #ffffff)',
          borderRadius: 'var(--radius-lg, 16px)',
          border: '1px solid var(--color-border-subtle, #e2e8f0)',
          padding: '24px',
          boxShadow: 'var(--shadow-subtle)',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '20px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div
            style={{
              width: '56px',
              height: '56px',
              borderRadius: 'var(--radius-full, 9999px)',
              backgroundColor: 'var(--color-surface-subtle, #f1f5f9)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--color-text-primary, #0f172a)',
              flexShrink: 0
            }}
          >
            <User size={28} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
              <h1
                style={{
                  fontSize: '22px',
                  fontWeight: 700,
                  color: 'var(--color-text-primary, #0f172a)',
                  margin: 0
                }}
              >
                {user.display_name}
              </h1>
              {user.is_active ? (
                <AdminBadge variant="success" size="md">
                  Active
                </AdminBadge>
              ) : (
                <AdminBadge variant="danger" size="md">
                  Suspended
                </AdminBadge>
              )}
              {user.is_super_admin && (
                <AdminBadge variant="purple" size="md">
                  SUPER ADMIN
                </AdminBadge>
              )}
            </div>
            <div style={{ fontSize: '13px', color: 'var(--color-text-secondary, #64748b)', marginTop: '4px' }}>
              User ID: <code>{user.id}</code>
            </div>
          </div>
        </div>

        {/* Administrative Action Buttons */}
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          {user.is_active ? (
            <button
              onClick={() => {
                setModalError(null);
                setIsSuspendModalOpen(true);
              }}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 18px',
                borderRadius: 'var(--radius-md, 10px)',
                backgroundColor: 'var(--status-overdue-bg, #fef2f2)',
                color: 'var(--status-overdue, #ef4444)',
                border: '1px solid #fecaca',
                fontSize: '14px',
                fontWeight: 600,
                cursor: 'pointer',
                minHeight: '44px'
              }}
            >
              <UserX size={16} />
              <span>Suspend Account</span>
            </button>
          ) : (
            <button
              onClick={() => {
                setModalError(null);
                setIsReactivateModalOpen(true);
              }}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 18px',
                borderRadius: 'var(--radius-md, 10px)',
                backgroundColor: 'var(--status-in-stock-bg, #ecfdf5)',
                color: 'var(--status-in-stock, #10b981)',
                border: '1px solid #a7f3d0',
                fontSize: '14px',
                fontWeight: 600,
                cursor: 'pointer',
                minHeight: '44px'
              }}
            >
              <UserCheck size={16} />
              <span>Reactivate Account</span>
            </button>
          )}
        </div>
      </div>

      {/* Profile Details & Verification Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '16px'
        }}
      >
        {/* Contact & Locale Card */}
        <div
          style={{
            backgroundColor: 'var(--color-surface-card, #ffffff)',
            borderRadius: 'var(--radius-lg, 16px)',
            border: '1px solid var(--color-border-subtle, #e2e8f0)',
            padding: '20px',
            boxShadow: 'var(--shadow-subtle)'
          }}
        >
          <h2 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)', margin: '0 0 16px' }}>
            Contact & Location Credentials
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '13px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: '8px' }}>
              <span style={{ color: 'var(--color-text-secondary, #64748b)' }}>Email Address</span>
              <span style={{ fontWeight: 600, color: 'var(--color-text-primary, #0f172a)' }}>{user.email || 'None'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: '8px' }}>
              <span style={{ color: 'var(--color-text-secondary, #64748b)' }}>Phone Number</span>
              <span style={{ fontWeight: 600, color: 'var(--color-text-primary, #0f172a)' }}>{user.phone_number || 'None'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: '8px' }}>
              <span style={{ color: 'var(--color-text-secondary, #64748b)' }}>Country Code</span>
              <span style={{ fontWeight: 600, color: 'var(--color-text-primary, #0f172a)' }}>{user.country_code || 'US'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: '8px' }}>
              <span style={{ color: 'var(--color-text-secondary, #64748b)' }}>Timezone</span>
              <span style={{ fontWeight: 600, color: 'var(--color-text-primary, #0f172a)' }}>{user.timezone || 'UTC'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--color-text-secondary, #64748b)' }}>Language</span>
              <span style={{ fontWeight: 600, color: 'var(--color-text-primary, #0f172a)' }}>{user.preferred_language || 'en'}</span>
            </div>
          </div>
        </div>

        {/* Security & Lifecycle Info */}
        <div
          style={{
            backgroundColor: 'var(--color-surface-card, #ffffff)',
            borderRadius: 'var(--radius-lg, 16px)',
            border: '1px solid var(--color-border-subtle, #e2e8f0)',
            padding: '20px',
            boxShadow: 'var(--shadow-subtle)'
          }}
        >
          <h2 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)', margin: '0 0 16px' }}>
            System Role & Verification Status
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '13px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: '8px' }}>
              <span style={{ color: 'var(--color-text-secondary, #64748b)' }}>Platform System Role</span>
              <AdminBadge variant={user.is_super_admin ? 'purple' : 'neutral'}>
                {user.system_role || 'USER'}
              </AdminBadge>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: '8px' }}>
              <span style={{ color: 'var(--color-text-secondary, #64748b)' }}>Email Verification</span>
              {user.is_verified ? (
                <AdminBadge variant="success">Verified</AdminBadge>
              ) : (
                <AdminBadge variant="warning">Unverified</AdminBadge>
              )}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: '8px' }}>
              <span style={{ color: 'var(--color-text-secondary, #64748b)' }}>Mobile SMS Verification</span>
              {user.mobile_verified ? (
                <AdminBadge variant="success">Verified</AdminBadge>
              ) : (
                <AdminBadge variant="neutral">Not Verified</AdminBadge>
              )}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: '8px' }}>
              <span style={{ color: 'var(--color-text-secondary, #64748b)' }}>Account Registered</span>
              <span style={{ color: 'var(--color-text-primary, #0f172a)' }}>{formatDate(user.created_at)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--color-text-secondary, #64748b)' }}>Last Updated</span>
              <span style={{ color: 'var(--color-text-primary, #0f172a)' }}>{formatDate(user.updated_at)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Household Memberships Section */}
      <div
        style={{
          backgroundColor: 'var(--color-surface-card, #ffffff)',
          borderRadius: 'var(--radius-lg, 16px)',
          border: '1px solid var(--color-border-subtle, #e2e8f0)',
          padding: '24px',
          boxShadow: 'var(--shadow-subtle)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <Home size={20} color="var(--color-text-secondary, #64748b)" />
          <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)', margin: 0 }}>
            Associated Household Workspaces ({user.memberships.length})
          </h2>
        </div>

        {user.memberships.length === 0 ? (
          <div
            style={{
              padding: '24px',
              textAlign: 'center',
              color: 'var(--color-text-secondary, #64748b)',
              fontSize: '14px'
            }}
          >
            This user currently does not belong to any household workspace.
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
            {user.memberships.map((m) => (
              <div
                key={m.home_id}
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
                  <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)' }}>
                    {m.home_name}
                  </div>
                  <AdminBadge variant={m.role === 'OWNER' ? 'purple' : 'info'}>
                    {m.role}
                  </AdminBadge>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                  Workspace Status: <strong>{m.status}</strong>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                  Member Since: {formatDate(m.joined_at)}
                </div>
                <Link
                  href={`/admin/homes/${m.home_id}`}
                  style={{
                    fontSize: '12px',
                    fontWeight: 600,
                    color: 'var(--color-primary-900, #0f172a)',
                    marginTop: '4px',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <span>Inspect Workspace</span>
                  <ArrowLeft size={12} style={{ transform: 'rotate(180deg)' }} />
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Confirmation Modals */}
      <AdminConfirmModal
        isOpen={isSuspendModalOpen}
        onClose={() => setIsSuspendModalOpen(false)}
        onConfirm={handleSuspend}
        title="Suspend Platform User"
        description={`Are you sure you want to suspend user "${user.display_name}" (${user.email})? They will be immediately blocked from signing in or modifying household data.`}
        confirmLabel="Suspend User"
        confirmVariant="danger"
        requireReason={true}
        placeholderReason="Provide violation reason (e.g. TOS violation, spam, chargeback)..."
        isSubmitting={isSubmitting}
        error={modalError}
      />

      <AdminConfirmModal
        isOpen={isReactivateModalOpen}
        onClose={() => setIsReactivateModalOpen(false)}
        onConfirm={handleReactivate}
        title="Reactivate Platform User"
        description={`Are you sure you want to restore access for user "${user.display_name}" (${user.email})?`}
        confirmLabel="Reactivate User"
        confirmVariant="success"
        requireReason={false}
        isSubmitting={isSubmitting}
        error={modalError}
      />
    </div>
  );
}
