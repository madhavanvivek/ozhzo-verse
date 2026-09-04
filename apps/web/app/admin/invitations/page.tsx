'use client';

import React, { useState, useEffect } from 'react';
import {
  Search,
  RefreshCw,
  Clock,
  Ban,
  AlertTriangle
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';

interface AdminInvitation {
  id: string;
  home_id: string;
  home_name: string;
  invitation_code: string;
  role: string;
  email?: string | null;
  phone_number?: string | null;
  status: string;
  invited_by_id?: string | null;
  invited_by_name?: string | null;
  expires_at: string;
  created_at: string;
  is_expired: boolean;
}

export default function AdminInvitationsPage() {
  const [invitations, setInvitations] = useState<AdminInvitation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedInvite, setSelectedInvite] = useState<AdminInvitation | null>(null);

  // Modals
  const [isExtendModalOpen, setIsExtendModalOpen] = useState(false);
  const [isRevokeModalOpen, setIsRevokeModalOpen] = useState(false);

  const [extendDays, setExtendDays] = useState('7');
  const [actionReason, setActionReason] = useState('');
  const [feedbackMsg, setFeedbackMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchInvitations = async () => {
    try {
      setIsLoading(true);
      let endpoint = '/admin/invitations?limit=100';
      if (searchQuery.trim()) {
        endpoint += `&q=${encodeURIComponent(searchQuery.trim())}`;
      }
      if (statusFilter) {
        endpoint += `&status=${encodeURIComponent(statusFilter)}`;
      }
      const res = await apiClient.get<AdminInvitation[]>(endpoint);
      setInvitations(res || []);
    } catch (err: any) {
      setFeedbackMsg({ type: 'error', text: err?.message || 'Failed to fetch global invitations' });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchInvitations();
  }, [statusFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchInvitations();
  };

  const handleExtend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInvite) return;
    try {
      await apiClient.post(`/admin/invitations/${selectedInvite.id}/extend`, {
        days_to_add: parseInt(extendDays) || 7,
        reason: actionReason || 'Super Admin operational extension'
      });
      setFeedbackMsg({ type: 'success', text: `Invitation ${selectedInvite.invitation_code} extended.` });
      setIsExtendModalOpen(false);
      setActionReason('');
      fetchInvitations();
    } catch (err: any) {
      setFeedbackMsg({ type: 'error', text: err?.message || 'Failed to extend invitation' });
    }
  };

  const handleRevoke = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInvite) return;
    try {
      await apiClient.post(`/admin/invitations/${selectedInvite.id}/revoke`, {
        reason: actionReason || 'Super Admin administrative revocation'
      });
      setFeedbackMsg({ type: 'success', text: `Invitation ${selectedInvite.invitation_code} revoked.` });
      setIsRevokeModalOpen(false);
      setActionReason('');
      fetchInvitations();
    } catch (err: any) {
      setFeedbackMsg({ type: 'error', text: err?.message || 'Failed to revoke invitation' });
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 style={{ fontSize: '24px', fontWeight: 800, color: 'var(--color-primary-900, #0f172a)', margin: 0 }}>
              Global Household Invitations Desk
            </h1>
            <Badge variant="neutral">Cross-Tenant Visibility</Badge>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--color-text-secondary, #64748b)', marginTop: '4px' }}>
            Inspect, search, and operationally resolve invitation issues while strictly maintaining identity-binding security.
          </p>
        </div>

        <Button variant="secondary" onClick={fetchInvitations} disabled={isLoading}>
          <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
          <span style={{ marginLeft: '6px' }}>Refresh</span>
        </Button>
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

      {/* Search & Filter Controls */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '20px', flexWrap: 'wrap' }}>
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '8px', flex: 1, maxWidth: '500px' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
            <input
              type="text"
              placeholder="Search code (OZ-...), phone, or email..."
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
          <Button variant="primary" type="submit">
            Search
          </Button>
        </form>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{ padding: '10px 14px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
        >
          <option value="">All Statuses</option>
          <option value="PENDING">Pending</option>
          <option value="ACCEPTED">Accepted</option>
          <option value="REVOKED">Revoked</option>
          <option value="EXPIRED">Expired</option>
        </select>
      </div>

      {/* Invitations Table */}
      <Card style={{ padding: '0', overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#475569' }}>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>Code & Role</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>Household</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>Target Phone / Email</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>Invited By</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>Status</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>Expires At</th>
                <th style={{ padding: '14px 16px', fontWeight: 600, textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {invitations.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: '32px', textAlign: 'center', color: '#64748b' }}>
                    No invitations match the search criteria.
                  </td>
                </tr>
              ) : (
                invitations.map((inv) => (
                  <tr key={inv.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '14px 16px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontWeight: 800, fontFamily: 'monospace', color: 'var(--color-primary-900, #0f172a)' }}>
                          {inv.invitation_code}
                        </span>
                        <Badge variant="neutral">{inv.role}</Badge>
                      </div>
                    </td>

                    <td style={{ padding: '14px 16px', fontWeight: 600, color: '#1e293b' }}>
                      {inv.home_name}
                    </td>

                    <td style={{ padding: '14px 16px', color: '#475569' }}>
                      <div>{inv.phone_number || '—'}</div>
                      {inv.email && <div style={{ fontSize: '11px', color: '#64748b' }}>{inv.email}</div>}
                    </td>

                    <td style={{ padding: '14px 16px', color: '#475569' }}>
                      {inv.invited_by_name}
                    </td>

                    <td style={{ padding: '14px 16px' }}>
                      {inv.is_expired ? (
                        <Badge variant="overdue">Expired</Badge>
                      ) : (
                        <Badge
                          variant={
                            inv.status === 'ACCEPTED'
                              ? 'completed'
                              : inv.status === 'PENDING'
                              ? 'low-stock'
                              : 'neutral'
                          }
                        >
                          {inv.status}
                        </Badge>
                      )}
                    </td>

                    <td style={{ padding: '14px 16px', color: '#64748b' }}>
                      {new Date(inv.expires_at).toLocaleDateString()}
                    </td>

                    <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                      <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                        {inv.status === 'PENDING' && (
                          <>
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={() => {
                                setSelectedInvite(inv);
                                setIsExtendModalOpen(true);
                              }}
                            >
                              <Clock size={14} />
                              <span style={{ marginLeft: '4px' }}>Extend</span>
                            </Button>

                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                setSelectedInvite(inv);
                                setIsRevokeModalOpen(true);
                              }}
                            >
                              <Ban size={14} color="#ef4444" />
                            </Button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* MODAL: EXTEND INVITATION */}
      {isExtendModalOpen && selectedInvite && (
        <Modal
          title={`Extend Invitation Expiry: ${selectedInvite.invitation_code}`}
          isOpen={isExtendModalOpen}
          onClose={() => setIsExtendModalOpen(false)}
        >
          <form onSubmit={handleExtend} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <p style={{ fontSize: '13px', color: '#475569', margin: 0 }}>
              Extend active duration for household <strong>{selectedInvite.home_name}</strong>.
            </p>

            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                Days to Add *
              </label>
              <Input
                type="number"
                min="1"
                max="90"
                value={extendDays}
                onChange={(e) => setExtendDays(e.target.value)}
              />
            </div>

            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                Operational Reason * (Mandatory for Audit Compliance)
              </label>
              <textarea
                required
                rows={3}
                placeholder="e.g. User requested extension via support ticket #1049"
                value={actionReason}
                onChange={(e) => setActionReason(e.target.value)}
                style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '8px' }}>
              <Button variant="secondary" type="button" onClick={() => setIsExtendModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" type="submit">
                Confirm Extension
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* MODAL: REVOKE INVITATION */}
      {isRevokeModalOpen && selectedInvite && (
        <Modal
          title={`Revoke Invitation: ${selectedInvite.invitation_code}`}
          isOpen={isRevokeModalOpen}
          onClose={() => setIsRevokeModalOpen(false)}
        >
          <form onSubmit={handleRevoke} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center', backgroundColor: '#fef2f2', padding: '12px', borderRadius: '8px', color: '#991b1b' }}>
              <AlertTriangle size={24} />
              <div style={{ fontSize: '13px' }}>
                Revoking this invitation will immediately block anyone attempting to join using code <strong>{selectedInvite.invitation_code}</strong>.
              </div>
            </div>

            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                Revocation Reason * (Mandatory for Audit Compliance)
              </label>
              <textarea
                required
                rows={3}
                placeholder="e.g. Dispatched to incorrect recipient / household owner requested cancellation"
                value={actionReason}
                onChange={(e) => setActionReason(e.target.value)}
                style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '8px' }}>
              <Button variant="secondary" type="button" onClick={() => setIsRevokeModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" type="submit" style={{ backgroundColor: '#dc2626' }}>
                Revoke Invitation
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
