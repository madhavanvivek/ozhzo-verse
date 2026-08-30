'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  ArrowLeft,
  Home,
  Users,
  CheckCircle,
  RefreshCw,
  PauseCircle,
  PlayCircle
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';
import { AdminBadge } from '../../components/AdminBadge';
import { AdminConfirmModal } from '../../components/AdminConfirmModal';
import { AdminHomeDetail } from '../../types';

export default function AdminHomeDetailPage() {
  const params = useParams();
  const homeId = params.id as string;

  const [home, setHome] = useState<AdminHomeDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Modals
  const [isSuspendModalOpen, setIsSuspendModalOpen] = useState(false);
  const [isReactivateModalOpen, setIsReactivateModalOpen] = useState(false);
  const [isHoldModalOpen, setIsHoldModalOpen] = useState(false);
  const [isArchiveModalOpen, setIsArchiveModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const fetchHomeDetail = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<AdminHomeDetail>(`/admin/homes/${homeId}`);
      setHome(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to retrieve workspace details.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (homeId) {
      fetchHomeDetail();
    }
  }, [homeId]);

  const handleSuspend = async (reason: string) => {
    setIsSubmitting(true);
    setModalError(null);
    setActionSuccess(null);
    try {
      await apiClient.post(`/admin/homes/${homeId}/suspend`, {
        reason: reason || 'Administrative workspace suspension'
      });
      setIsSuspendModalOpen(false);
      setActionSuccess('Household workspace was successfully suspended.');
      fetchHomeDetail();
    } catch (err: any) {
      setModalError(err?.message || 'Failed to suspend household workspace.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReactivate = async (reason: string) => {
    setIsSubmitting(true);
    setModalError(null);
    setActionSuccess(null);
    try {
      await apiClient.post(`/admin/homes/${homeId}/reactivate`, {
        reason: reason || 'Administrative workspace reactivation'
      });
      setIsReactivateModalOpen(false);
      setActionSuccess('Household workspace was successfully reactivated.');
      fetchHomeDetail();
    } catch (err: any) {
      setModalError(err?.message || 'Failed to reactivate household workspace.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleHold = async (reason: string) => {
    setIsSubmitting(true);
    setModalError(null);
    setActionSuccess(null);
    try {
      await apiClient.post(`/admin/homes/${homeId}/hold`, {
        reason: reason || 'Administrative compliance hold'
      });
      setIsHoldModalOpen(false);
      setActionSuccess('Household workspace placed on administrative hold.');
      fetchHomeDetail();
    } catch (err: any) {
      setModalError(err?.message || 'Failed to place workspace on hold.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleArchive = async (reason: string) => {
    setIsSubmitting(true);
    setModalError(null);
    setActionSuccess(null);
    try {
      await apiClient.post(`/admin/homes/${homeId}/archive`, {
        reason: reason || 'Administrative archival'
      });
      setIsArchiveModalOpen(false);
      setActionSuccess('Household workspace was archived.');
      fetchHomeDetail();
    } catch (err: any) {
      setModalError(err?.message || 'Failed to archive workspace.');
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
        <RefreshCw size={28} className="animate-spin" color="var(--status-in-stock, #10b981)" />
        <span style={{ fontSize: '15px', fontWeight: 600 }}>Loading household record...</span>
      </div>
    );
  }

  if (error || !home) {
    const is403 = error?.includes('403') || error?.toLowerCase().includes('permission') || error?.toLowerCase().includes('admin');
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <Link
          href="/admin/homes"
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
          <span>Back to Homes List</span>
        </Link>
        <div
          style={{
            padding: '24px',
            backgroundColor: 'var(--status-overdue-bg, #fef2f2)',
            border: '1px solid #fecaca',
            borderRadius: 'var(--radius-lg, 16px)',
            color: 'var(--status-overdue, #ef4444)',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px'
          }}
        >
          <h2 style={{ fontSize: '18px', fontWeight: 700, margin: 0 }}>
            {is403 ? 'Platform Administrator Access Required' : 'Unable to Load Workspace'}
          </h2>
          <p style={{ fontSize: '14px', margin: 0, color: '#991b1b' }}>{error || 'Unable to locate household workspace.'}</p>
          <div>
            <button
              onClick={fetchHomeDetail}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: 'var(--radius-md, 10px)',
                backgroundColor: 'var(--color-primary-900, #0f172a)',
                color: '#ffffff',
                border: 'none',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              <RefreshCw size={14} />
              <span>Retry</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Navigation Breadcrumb */}
      <div>
        <Link
          href="/admin/homes"
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
          <span>Back to Homes List</span>
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

      {/* Workspace Header Card */}
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
              borderRadius: 'var(--radius-md, 10px)',
              backgroundColor: 'var(--status-in-stock-bg, #ecfdf5)',
              color: 'var(--status-in-stock, #10b981)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}
          >
            <Home size={30} />
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
                {home.name}
              </h1>
              {home.status === 'ACTIVE' ? (
                <AdminBadge variant="success" size="md">
                  Active
                </AdminBadge>
              ) : (
                <AdminBadge variant="danger" size="md">
                  Suspended
                </AdminBadge>
              )}
              {home.public_home_id && (
                <AdminBadge variant="info" size="md">
                  {home.public_home_id}
                </AdminBadge>
              )}
              <AdminBadge variant={home.home_qr_status === 'ACTIVE' ? 'success' : 'neutral'} size="md">
                QR: {home.home_qr_status || 'ACTIVE'}
              </AdminBadge>
            </div>
            <div style={{ fontSize: '13px', color: 'var(--color-text-secondary, #64748b)', marginTop: '4px' }}>
              Public ID: <code>{home.public_home_id || 'N/A'}</code> &bull; UUID: <code>{home.id}</code>
            </div>
          </div>
        </div>

        {/* Administrative Actions */}
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          {home.status === 'ACTIVE' ? (
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
              <PauseCircle size={16} />
              <span>Suspend Workspace</span>
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
              <PlayCircle size={16} />
              <span>Reactivate Workspace</span>
            </button>
          )}

          <button
            onClick={() => {
              setModalError(null);
              setIsHoldModalOpen(true);
            }}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 18px',
              borderRadius: 'var(--radius-md, 10px)',
              backgroundColor: 'var(--color-surface-subtle, #f1f5f9)',
              color: 'var(--color-primary-900, #0f172a)',
              border: '1px solid var(--color-border-subtle, #e2e8f0)',
              fontSize: '14px',
              fontWeight: 600,
              cursor: 'pointer',
              minHeight: '44px'
            }}
          >
            <span>Place on Hold</span>
          </button>

          <button
            onClick={() => {
              setModalError(null);
              setIsArchiveModalOpen(true);
            }}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 18px',
              borderRadius: 'var(--radius-md, 10px)',
              backgroundColor: '#fef2f2',
              color: '#991b1b',
              border: '1px solid #fecaca',
              fontSize: '14px',
              fontWeight: 600,
              cursor: 'pointer',
              minHeight: '44px'
            }}
          >
            <span>Archive Workspace</span>
          </button>
        </div>
      </div>

      {/* Grid: Workspace Info & Subscription Roster */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '16px'
        }}
      >
        {/* Workspace Details */}
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
            Workspace Telemetry
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '13px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: '8px' }}>
              <span style={{ color: 'var(--color-text-secondary, #64748b)' }}>Creator / Primary Owner</span>
              <span style={{ fontWeight: 600, color: 'var(--color-text-primary, #0f172a)' }}>
                {home.created_by_name} ({home.created_by_email || 'No email'})
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: '8px' }}>
              <span style={{ color: 'var(--color-text-secondary, #64748b)' }}>Currency</span>
              <span style={{ fontWeight: 600, color: 'var(--color-text-primary, #0f172a)' }}>{home.currency}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: '8px' }}>
              <span style={{ color: 'var(--color-text-secondary, #64748b)' }}>Timezone</span>
              <span style={{ fontWeight: 600, color: 'var(--color-text-primary, #0f172a)' }}>{home.timezone}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: '8px' }}>
              <span style={{ color: 'var(--color-text-secondary, #64748b)' }}>Location Address</span>
              <span style={{ fontWeight: 500, color: 'var(--color-text-primary, #0f172a)' }}>{home.address || '—'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--color-text-secondary, #64748b)' }}>Created Date</span>
              <span style={{ color: 'var(--color-text-primary, #0f172a)' }}>{formatDate(home.created_at)}</span>
            </div>
          </div>
        </div>

        {/* Subscription Entitlement */}
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
            Subscription & Entitlements
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '13px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: '8px' }}>
              <span style={{ color: 'var(--color-text-secondary, #64748b)' }}>Subscription Plan</span>
              <AdminBadge variant="purple">{home.subscription_plan}</AdminBadge>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: '8px' }}>
              <span style={{ color: 'var(--color-text-secondary, #64748b)' }}>Entitlement Status</span>
              <AdminBadge
                variant={
                  home.subscription_status === 'ACTIVE'
                    ? 'success'
                    : home.subscription_status === 'TRIALING'
                    ? 'info'
                    : 'warning'
                }
              >
                {home.subscription_status}
              </AdminBadge>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #f1f5f9', paddingBottom: '8px' }}>
              <span style={{ color: 'var(--color-text-secondary, #64748b)' }}>Paid Member Seats</span>
              <span style={{ fontWeight: 700, color: 'var(--color-text-primary, #0f172a)' }}>
                {home.paid_seats} Paid Seats
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--color-text-secondary, #64748b)' }}>Total Active Members</span>
              <span style={{ fontWeight: 700, color: 'var(--color-text-primary, #0f172a)' }}>
                {home.members_count} Members
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Member Roster Section */}
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
          <Users size={20} color="var(--color-text-secondary, #64748b)" />
          <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)', margin: 0 }}>
            Household Member Roster ({home.members.length})
          </h2>
        </div>

        {home.members.length === 0 ? (
          <div style={{ padding: '24px', textAlign: 'center', color: 'var(--color-text-secondary, #64748b)' }}>
            No members are currently associated with this household workspace.
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
            {home.members.map((m) => (
              <div
                key={m.user_id}
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
                      {m.display_name}
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                      {m.email || 'No email'}
                    </div>
                  </div>
                  <AdminBadge variant={m.role === 'OWNER' ? 'purple' : m.role === 'HOME_ADMIN' ? 'warning' : 'neutral'}>
                    {m.role}
                  </AdminBadge>
                </div>

                <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                  Member Status: <strong>{m.status}</strong>
                </div>

                <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                  Joined: {formatDate(m.created_at)}
                </div>

                <Link
                  href={`/admin/users/${m.user_id}`}
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
                  <span>Inspect User Account</span>
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
        title="Suspend Household Workspace"
        description={`Are you sure you want to suspend household workspace "${home.name}"? Workspace members will be blocked from accessing household inventory, tasks, and data.`}
        confirmLabel="Suspend Workspace"
        confirmVariant="danger"
        requireReason={true}
        placeholderReason="Enter administrative reason for suspending workspace..."
        isSubmitting={isSubmitting}
        error={modalError}
      />

      <AdminConfirmModal
        isOpen={isReactivateModalOpen}
        onClose={() => setIsReactivateModalOpen(false)}
        onConfirm={handleReactivate}
        title="Reactivate Household Workspace"
        description={`Are you sure you want to reactivate household workspace "${home.name}"?`}
        confirmLabel="Reactivate Workspace"
        confirmVariant="success"
        requireReason={false}
        isSubmitting={isSubmitting}
        error={modalError}
      />

      <AdminConfirmModal
        isOpen={isHoldModalOpen}
        onClose={() => setIsHoldModalOpen(false)}
        onConfirm={handleHold}
        title="Place Household on Administrative Hold"
        description={`Are you sure you want to place workspace "${home.name}" on administrative hold? Members will be temporarily restricted from making changes.`}
        confirmLabel="Place on Hold"
        confirmVariant="primary"
        requireReason={true}
        placeholderReason="Specify compliance or investigation reason..."
        isSubmitting={isSubmitting}
        error={modalError}
      />

      <AdminConfirmModal
        isOpen={isArchiveModalOpen}
        onClose={() => setIsArchiveModalOpen(false)}
        onConfirm={handleArchive}
        title="Archive Household Workspace"
        description={`Are you sure you want to archive workspace "${home.name}"? This soft-deletes and retires the workspace.`}
        confirmLabel="Archive Workspace"
        confirmVariant="danger"
        requireReason={true}
        placeholderReason="Provide archival audit reason..."
        isSubmitting={isSubmitting}
        error={modalError}
      />
    </div>
  );
}

