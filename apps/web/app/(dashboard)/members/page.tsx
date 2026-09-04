'use client';

import React, { useEffect, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import {
  Users,
  UserPlus,
  Copy,
  Check,
  Trash2,
  Mail,
  AlertCircle,
  RefreshCw,
  X,
  Shield,
  KeyRound,
  BellRing,
  Info,
  Clock,
  Search,
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

interface MemberItem {
  id: string;
  user_id: string;
  display_name: string;
  phone_number?: string | null;
  email?: string | null;
  avatar_url?: string | null;
  role: string;
  status: string;
  joined_at?: string | null;
  access_status?: string | null;
  access_expires_at?: string | null;
  days_until_expiry?: number | null;
  is_expiring_soon?: boolean;
  plan_name?: string | null;
  is_reserved?: boolean;
}

interface MemberActivityItem {
  id: string;
  action: string;
  performed_by_name?: string | null;
  details?: Record<string, any>;
  created_at: string;
}

interface MemberDetailDTO {
  id: string;
  user_id: string;
  display_name: string;
  phone_number?: string | null;
  email?: string | null;
  avatar_url?: string | null;
  email_verified: boolean;
  mobile_verified: boolean;
  role: string;
  status: string;
  joined_at?: string | null;
  access_status?: string | null;
  access_expires_at?: string | null;
  days_until_expiry?: number | null;
  is_expiring_soon?: boolean;
  plan_name?: string | null;
  is_reserved?: boolean;
  recent_activity: MemberActivityItem[];
}

interface HomeAdminSummaryDTO {
  home_id: string;
  home_name: string;
  public_home_id?: string | null;
  qr_status?: string;
  join_policy: string;
  active_members_count: number;
  pending_invitations_count: number;
  pending_join_requests_count: number;
  expiring_access_count: number;
  expired_access_count: number;
}

interface InvitationItem {
  id: string;
  home_id: string;
  home_name?: string;
  phone_number?: string | null;
  email?: string | null;
  role: string;
  invitation_mode: string;
  token: string;
  invitation_code?: string | null;
  invite_url?: string;
  status: string;
  invited_by?: string;
  invited_by_name?: string | null;
  expires_at: string;
  created_at?: string;
}

interface UserProfile {
  id: string;
  display_name: string;
  email?: string | null;
  phone_number?: string | null;
  homes: Array<{
    home_id: string;
    name: string;
    role: string;
    status: string;
  }>;
}

function formatErrorMessage(err: any): string {
  if (!err) return 'An error occurred';
  if (typeof err === 'string') return err;
  if (typeof err?.message === 'string') return err.message;
  if (Array.isArray(err?.detail)) {
    return err.detail.map((d: any) => (typeof d === 'string' ? d : d.msg || d.message || JSON.stringify(d))).join(', ');
  }
  if (typeof err?.detail === 'string') return err.detail;
  if (typeof err?.detail === 'object') return JSON.stringify(err.detail);
  try {
    return JSON.stringify(err);
  } catch {
    return 'An unexpected error occurred';
  }
}

export default function MembersPage() {
  const [activeHomeId, setActiveHomeId] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [summary, setSummary] = useState<HomeAdminSummaryDTO | null>(null);
  const [members, setMembers] = useState<MemberItem[]>([]);
  const [pendingInvites, setPendingInvites] = useState<InvitationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Search & Filter
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [roleFilter, setRoleFilter] = useState('ALL');

  // Invite Form State
  const [inviteEmail, setInviteEmail] = useState('');
  const [invitePhone, setInvitePhone] = useState('');
  const [inviteRole, setInviteRole] = useState('MEMBER');
  const [isSubmittingInvite, setIsSubmittingInvite] = useState(false);
  const [inviteSuccess, setInviteSuccess] = useState<string | null>(null);
  const [inviteError, setInviteError] = useState<string | null>(null);

  const [copiedToken, setCopiedToken] = useState<string | null>(null);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [actionInProgressId, setActionInProgressId] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Role Editing State
  const [editingMemberRole, setEditingMemberRole] = useState<{ id: string; name: string; currentRole: string } | null>(null);
  const [newSelectedRole, setNewSelectedRole] = useState<string>('MEMBER');
  const [isSavingRole, setIsSavingRole] = useState(false);

  // Member Detail Inspection Modal
  const [inspectingMember, setInspectingMember] = useState<MemberDetailDTO | null>(null);

  // New Invite Showcase Modal State
  const [createdInviteModal, setCreatedInviteModal] = useState<InvitationItem | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const loadData = async (showLoading = true) => {
    if (showLoading) setIsLoading(true);
    setError(null);
    try {
      const initialHomeId = apiClient.getActiveHomeId();

      const [userRes, homeIdRes, initialMembersRes, initialInvitesRes, summaryRes] = await Promise.allSettled([
        apiClient.get<UserProfile>('/users/me'),
        apiClient.getValidActiveHome(),
        initialHomeId ? apiClient.get<MemberItem[]>(`/homes/${initialHomeId}/members`) : Promise.resolve(null),
        initialHomeId ? apiClient.get<InvitationItem[]>(`/homes/${initialHomeId}/invitations`) : Promise.resolve(null),
        initialHomeId ? apiClient.get<HomeAdminSummaryDTO>(`/homes/${initialHomeId}/admin/summary`) : Promise.resolve(null)
      ]);

      if (userRes.status === 'fulfilled' && userRes.value) {
        setCurrentUser(userRes.value);
      }

      const homeId = homeIdRes.status === 'fulfilled' ? homeIdRes.value : null;
      setActiveHomeId(homeId);

      if (homeId) {
        if (summaryRes.status === 'fulfilled' && summaryRes.value) {
          setSummary(summaryRes.value);
        } else {
          try {
            const sum = await apiClient.get<HomeAdminSummaryDTO>(`/homes/${homeId}/admin/summary`);
            setSummary(sum);
          } catch {
            setSummary(null);
          }
        }

        if (homeId === initialHomeId && initialMembersRes.status === 'fulfilled' && initialMembersRes.value) {
          setMembers(Array.isArray(initialMembersRes.value) ? initialMembersRes.value : []);
        } else {
          try {
            const freshMembers = await apiClient.get<MemberItem[]>(`/homes/${homeId}/members`);
            setMembers(Array.isArray(freshMembers) ? freshMembers : []);
          } catch {
            setMembers([]);
          }
        }

        if (homeId === initialHomeId && initialInvitesRes.status === 'fulfilled' && initialInvitesRes.value) {
          setPendingInvites(Array.isArray(initialInvitesRes.value) ? initialInvitesRes.value : []);
        } else {
          try {
            const freshInvites = await apiClient.get<InvitationItem[]>(`/homes/${homeId}/invitations`);
            setPendingInvites(Array.isArray(freshInvites) ? freshInvites : []);
          } catch {
            setPendingInvites([]);
          }
        }
      }
    } catch (err: any) {
      console.error('Failed to load members:', err);
      setError(formatErrorMessage(err));
    } finally {
      if (showLoading) setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData(true);
    const handleHomeChanged = () => loadData(true);
    window.addEventListener('home-changed', handleHomeChanged);
    return () => window.removeEventListener('home-changed', handleHomeChanged);
  }, []);

  const handleCreateInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeHomeId) return;
    if (!inviteEmail.trim() && !invitePhone.trim()) {
      setInviteError('Please provide an email address or mobile phone number.');
      return;
    }

    setIsSubmittingInvite(true);
    setInviteError(null);
    setInviteSuccess(null);

    try {
      const newInvite = await apiClient.post<InvitationItem>(`/homes/${activeHomeId}/invitations`, {
        email: inviteEmail.trim() || undefined,
        phone_number: invitePhone.trim() || undefined,
        role: inviteRole,
        invitation_mode: 'INVITE_ONLY'
      });

      setInviteEmail('');
      setInvitePhone('');
      setInviteSuccess('Invitation generated successfully!');
      setCreatedInviteModal(newInvite);
      await loadData(false);
    } catch (err: any) {
      console.error('Failed to create invitation:', err);
      setInviteError(formatErrorMessage(err));
    } finally {
      setIsSubmittingInvite(false);
    }
  };

  const handleCopyLink = async (token: string) => {
    const fullUrl = typeof window !== 'undefined' ? `${window.location.origin}/invite/${token}` : `/invite/${token}`;
    try {
      if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(fullUrl);
      }
    } catch {
      // ignore clipboard permission error
    }
    setCopiedToken(token);
    setTimeout(() => setCopiedToken(null), 3000);
  };

  const handleCopyCode = async (code: string) => {
    try {
      if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(code);
      }
    } catch {
      // ignore clipboard permission error
    }
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 3000);
  };

  const handleCancelInvite = async (invitationId: string) => {
    if (!activeHomeId) return;
    if (!confirm('Are you sure you want to revoke this pending invitation? The recipient will not be able to join using this link or code.')) return;

    setActionInProgressId(invitationId);
    try {
      await apiClient.delete(`/homes/${activeHomeId}/invitations/${invitationId}`);
      showToast('Invitation revoked successfully.');
      await loadData(false);
    } catch (err: any) {
      console.error('Failed to cancel invitation:', err);
      alert(formatErrorMessage(err));
    } finally {
      setActionInProgressId(null);
    }
  };

  const handleResendInvite = async (invitationId: string) => {
    if (!activeHomeId) return;

    setActionInProgressId(invitationId);
    try {
      const resent = await apiClient.post<InvitationItem>(`/homes/${activeHomeId}/invitations/${invitationId}/resend`, {});
      showToast('Invitation refreshed and expiry extended by 7 days.');
      setCreatedInviteModal(resent);
      await loadData(false);
    } catch (err: any) {
      console.error('Failed to resend invitation:', err);
      alert(formatErrorMessage(err));
    } finally {
      setActionInProgressId(null);
    }
  };

  const handleOpenRoleModal = (m: MemberItem) => {
    setEditingMemberRole({ id: m.id, name: m.display_name, currentRole: m.role });
    setNewSelectedRole(m.role);
  };

  const handleSaveMemberRole = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeHomeId || !editingMemberRole) return;

    setIsSavingRole(true);
    try {
      await apiClient.patch(`/homes/${activeHomeId}/members/${editingMemberRole.id}/role`, {
        role: newSelectedRole
      });
      showToast(`Role updated to ${newSelectedRole} for ${editingMemberRole.name}`);
      setEditingMemberRole(null);
      await loadData(false);
    } catch (err: any) {
      console.error('Failed to update role:', err);
      alert(formatErrorMessage(err));
    } finally {
      setIsSavingRole(false);
    }
  };

  const handleRemoveMember = async (memberId: string, memberName: string) => {
    if (!activeHomeId) return;
    if (!confirm(`Are you sure you want to remove ${memberName} from this Home? They will immediately lose access to all household data.`)) {
      return;
    }

    setActionInProgressId(memberId);
    try {
      await apiClient.delete(`/homes/${activeHomeId}/members/${memberId}`);
      showToast(`${memberName} has been removed from this Home.`);
      await loadData(false);
    } catch (err: any) {
      console.error('Failed to remove member:', err);
      alert(formatErrorMessage(err));
    } finally {
      setActionInProgressId(null);
    }
  };

  const handleRemindMember = async (memberId: string, memberName: string) => {
    if (!activeHomeId) return;

    setActionInProgressId(memberId);
    try {
      const res = await apiClient.post<{ message: string }>(`/homes/${activeHomeId}/members/${memberId}/remind`, {});
      showToast(res?.message || `Access reminder dispatched to ${memberName}.`);
    } catch (err: any) {
      console.error('Failed to send reminder:', err);
      alert(formatErrorMessage(err));
    } finally {
      setActionInProgressId(null);
    }
  };

  const handleViewMemberDetail = async (memberId: string) => {
    if (!activeHomeId) return;
    try {
      const detail = await apiClient.get<MemberDetailDTO>(`/homes/${activeHomeId}/members/${memberId}`);
      setInspectingMember(detail);
    } catch (err: any) {
      console.error('Failed to fetch member details:', err);
      alert(formatErrorMessage(err));
    }
  };

  const activeHome = currentUser?.homes?.find((h) => h.home_id === activeHomeId);
  const myRole = (activeHome?.role || '').toUpperCase();
  const canManageMembers = ['OWNER', 'HOME_ADMIN', 'ADMIN'].includes(myRole);

  const getInitials = (name: string) => {
    const parts = (name || '').trim().split(' ');
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    return (name || 'M').substring(0, 2).toUpperCase();
  };

  const getRoleDisplayName = (role: string) => {
    switch ((role || '').toUpperCase()) {
      case 'OWNER': return 'Owner';
      case 'HOME_ADMIN': return 'Home Admin';
      case 'ADMIN': return 'Admin';
      case 'MEMBER': return 'Adult Member';
      case 'CHILD': return 'Child';
      case 'GUEST': return 'Guest';
      default: return role;
    }
  };

  const getRoleBadgeVariant = (role: string): any => {
    switch ((role || '').toUpperCase()) {
      case 'OWNER': return 'completed';
      case 'HOME_ADMIN':
      case 'ADMIN': return 'in-stock';
      case 'MEMBER': return 'neutral';
      default: return 'low-stock';
    }
  };

  const getAccessStatusBadge = (m: MemberItem) => {
    const st = (m.access_status || 'ACTIVE').toUpperCase();
    if (st === 'EXPIRING' || m.is_expiring_soon) {
      return (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            padding: '3px 8px',
            borderRadius: '6px',
            backgroundColor: '#fef3c7',
            color: '#b45309',
            fontSize: '11px',
            fontWeight: 700,
            border: '1px solid #fde68a'
          }}
          title={m.access_expires_at ? `Expires on ${new Date(m.access_expires_at).toLocaleDateString()}` : undefined}
        >
          <Clock size={12} />
          <span>Expiring ({m.days_until_expiry ?? '<7'}d)</span>
        </span>
      );
    }
    if (st === 'EXPIRED') {
      return (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            padding: '3px 8px',
            borderRadius: '6px',
            backgroundColor: '#fee2e2',
            color: '#b91c1c',
            fontSize: '11px',
            fontWeight: 700,
            border: '1px solid #fca5a5'
          }}
        >
          <AlertTriangle size={12} />
          <span>Access Expired</span>
        </span>
      );
    }
    if (st === 'ACTIVE') {
      return (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            padding: '3px 8px',
            borderRadius: '6px',
            backgroundColor: '#f0fdf4',
            color: '#15803d',
            fontSize: '11px',
            fontWeight: 600,
            border: '1px solid #bbf7d0'
          }}
        >
          <CheckCircle2 size={12} />
          <span>Active Access</span>
        </span>
      );
    }
    return (
      <Badge variant="neutral">
        {st}
      </Badge>
    );
  };

  // Filtered members list
  const filteredMembers = members.filter((m) => {
    if (statusFilter !== 'ALL') {
      const mStatus = (m.access_status || m.status || 'ACTIVE').toUpperCase();
      if (statusFilter === 'ACTIVE' && mStatus !== 'ACTIVE') return false;
      if (statusFilter === 'EXPIRING' && mStatus !== 'EXPIRING') return false;
      if (statusFilter === 'EXPIRED' && mStatus !== 'EXPIRED') return false;
      if (statusFilter === 'REMOVED' && m.status !== 'REMOVED') return false;
    }
    if (roleFilter !== 'ALL') {
      if ((m.role || '').toUpperCase() !== roleFilter.toUpperCase()) return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      const matchName = (m.display_name || '').toLowerCase().includes(q);
      const matchEmail = (m.email || '').toLowerCase().includes(q);
      const matchPhone = (m.phone_number || '').toLowerCase().includes(q);
      if (!matchName && !matchEmail && !matchPhone) return false;
    }
    return true;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '960px' }}>
      {/* Header */}
      <div>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-primary-900)' }}>
          Family Members & Household Access Administration
        </h1>
        <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)' }}>
          Manage family members, assign roles, inspect entitlement states, issue invitations, and enforce permissions.
        </p>
      </div>

      {toastMessage && (
        <div style={{ padding: '10px 16px', backgroundColor: 'var(--color-primary-900)', color: '#ffffff', borderRadius: 'var(--radius-md)', fontSize: '13px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Check size={16} />
          <span>{toastMessage}</span>
        </div>
      )}

      {error && (
        <div style={{ padding: '12px 16px', backgroundColor: 'var(--status-overdue-bg)', color: 'var(--status-overdue)', borderRadius: 'var(--radius-md)', fontSize: '13px', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* 1. Admin KPI Summary Banner */}
      {summary && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--space-3)' }}>
          <Card style={{ padding: '16px' }}>
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>
              Active Members
            </div>
            <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--color-primary-900)', marginTop: '4px' }}>
              {summary.active_members_count}
            </div>
          </Card>

          <Card style={{ padding: '16px' }}>
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>
              Pending Invites
            </div>
            <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--color-primary-900)', marginTop: '4px' }}>
              {summary.pending_invitations_count}
            </div>
          </Card>

          <Card style={{ padding: '16px' }}>
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>
              Join Requests
            </div>
            <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--color-primary-900)', marginTop: '4px' }}>
              {summary.pending_join_requests_count}
            </div>
          </Card>

          <Card style={{ padding: '16px', backgroundColor: summary.expiring_access_count > 0 ? '#fffbeb' : undefined }}>
            <div style={{ fontSize: '12px', fontWeight: 600, color: summary.expiring_access_count > 0 ? '#b45309' : 'var(--color-text-secondary)', textTransform: 'uppercase' }}>
              Expiring Access
            </div>
            <div style={{ fontSize: '24px', fontWeight: 800, color: summary.expiring_access_count > 0 ? '#b45309' : 'var(--color-primary-900)', marginTop: '4px' }}>
              {summary.expiring_access_count}
            </div>
          </Card>
        </div>
      )}

      {/* 2. Send Invitation Form (Admin Only) */}
      {canManageMembers && (
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: 'var(--space-3)' }}>
            <UserPlus size={18} color="var(--color-primary-900)" />
            <h2 style={{ fontSize: '16px', fontWeight: 600 }}>Invite a New Family Member</h2>
          </div>

          {inviteSuccess && (
            <div style={{ padding: '10px 14px', backgroundColor: 'var(--status-in-stock-bg)', color: 'var(--status-in-stock)', borderRadius: 'var(--radius-md)', fontSize: '13px', fontWeight: 600, marginBottom: 'var(--space-3)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Check size={16} />
              <span>{inviteSuccess}</span>
            </div>
          )}

          {inviteError && (
            <div style={{ padding: '10px 14px', backgroundColor: 'var(--status-overdue-bg)', color: 'var(--status-overdue)', borderRadius: 'var(--radius-md)', fontSize: '13px', fontWeight: 500, marginBottom: 'var(--space-3)' }}>
              {inviteError}
            </div>
          )}

          <form onSubmit={handleCreateInvite} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr)) auto', gap: 'var(--space-3)', alignItems: 'flex-end' }}>
            <Input
              id="inviteEmail"
              type="email"
              label="Email Address"
              placeholder="name@domain.com"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
            />

            <Input
              id="invitePhone"
              type="tel"
              label="Mobile Number (Optional)"
              placeholder="+919876543210"
              value={invitePhone}
              onChange={(e) => setInvitePhone(e.target.value)}
            />

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label htmlFor="inviteRole" style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                Assigned Role
              </label>
              <select
                id="inviteRole"
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value)}
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
                <option value="HOME_ADMIN">Home Admin (Co-management)</option>
                <option value="ADMIN">Admin (Full Management)</option>
                <option value="MEMBER">Adult Member (Chores & Bills)</option>
                <option value="CHILD">Child (Chores Only)</option>
                <option value="GUEST">Guest (Limited Scope)</option>
              </select>
            </div>

            <Button type="submit" isLoading={isSubmittingInvite} disabled={!activeHomeId} style={{ minHeight: '44px', minWidth: '130px' }}>
              Send Invite
            </Button>
          </form>
        </Card>
      )}

      {/* 3. Member Directory Card with Search & Filters */}
      <Card>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '12px', marginBottom: 'var(--space-4)', paddingBottom: 'var(--space-3)', borderBottom: '1px solid var(--color-border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Users size={18} color="var(--color-primary-900)" />
            <h2 style={{ fontSize: '16px', fontWeight: 600 }}>
              Household Member Directory ({members.length})
            </h2>
          </div>
          <Badge variant="neutral">Home Scope Isolated</Badge>
        </div>

        {/* Search & Filter Toolbar */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginBottom: '16px' }}>
          <div style={{ flex: '1 1 240px', position: 'relative' }}>
            <Search size={16} style={{ position: 'absolute', left: '12px', top: '13px', color: 'var(--color-text-secondary)' }} />
            <input
              type="text"
              placeholder="Search by name, email, or phone..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                height: '40px',
                paddingLeft: '36px',
                paddingRight: '12px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border-strong)',
                backgroundColor: 'var(--color-surface-card)',
                fontSize: '13px'
              }}
            />
          </div>

          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{
                height: '40px',
                padding: '0 12px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border-strong)',
                backgroundColor: 'var(--color-surface-card)',
                fontSize: '13px'
              }}
            >
              <option value="ALL">All Statuses</option>
              <option value="ACTIVE">Active Access</option>
              <option value="EXPIRING">Expiring Soon</option>
              <option value="EXPIRED">Expired Access</option>
              <option value="REMOVED">Removed</option>
            </select>

            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              style={{
                height: '40px',
                padding: '0 12px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border-strong)',
                backgroundColor: 'var(--color-surface-card)',
                fontSize: '13px'
              }}
            >
              <option value="ALL">All Roles</option>
              <option value="OWNER">Owner</option>
              <option value="HOME_ADMIN">Home Admin</option>
              <option value="ADMIN">Admin</option>
              <option value="MEMBER">Member</option>
              <option value="CHILD">Child</option>
              <option value="GUEST">Guest</option>
            </select>
          </div>
        </div>

        {isLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {[1, 2, 3].map((i) => (
              <div key={i} style={{ height: '64px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: 'var(--radius-md)', animation: 'pulse 1.5s infinite' }} />
            ))}
          </div>
        ) : filteredMembers.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 'var(--space-8)', color: 'var(--color-text-secondary)', fontSize: '14px' }}>
            No members match the selected filters.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            {filteredMembers.map((m) => {
              const isMe = currentUser?.id === m.user_id;
              const isOwner = (m.role || '').toUpperCase() === 'OWNER';
              const canManageThisMember = canManageMembers && !isMe && !isOwner;
              const isExpiringOrExpired = m.is_expiring_soon || (m.access_status || '').toUpperCase() === 'EXPIRED';

              return (
                <div
                  key={m.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '14px 16px',
                    backgroundColor: 'var(--color-surface-subtle)',
                    borderRadius: 'var(--radius-md)',
                    flexWrap: 'wrap',
                    gap: '12px'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: '220px' }}>
                    <div style={{ width: '40px', height: '40px', borderRadius: '50%', backgroundColor: 'var(--color-primary-900)', color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px', fontWeight: 600 }}>
                      {getInitials(m.display_name)}
                    </div>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                          {m.display_name}
                        </span>
                        {isMe && <span style={{ fontSize: '11px', color: 'var(--color-text-secondary)', fontWeight: 500 }}>(You)</span>}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                        {m.email || m.phone_number || 'No contact provided'}
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <Badge variant={getRoleBadgeVariant(m.role)}>
                      {getRoleDisplayName(m.role)}
                    </Badge>

                    {getAccessStatusBadge(m)}

                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleViewMemberDetail(m.id)}
                      style={{ minHeight: '36px', padding: '0 10px', fontSize: '12px' }}
                      title="Inspect Member Details & Activity"
                    >
                      <Info size={14} style={{ marginRight: '4px' }} />
                      <span>Details</span>
                    </Button>

                    {canManageMembers && isExpiringOrExpired && (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleRemindMember(m.id, m.display_name)}
                        disabled={actionInProgressId === m.id}
                        style={{ minHeight: '36px', padding: '0 10px', fontSize: '12px' }}
                        title="Send Access Renewal Reminder"
                      >
                        <BellRing size={14} style={{ marginRight: '4px' }} />
                        <span>Remind</span>
                      </Button>
                    )}

                    {canManageThisMember && (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleOpenRoleModal(m)}
                        style={{ minHeight: '36px', padding: '0 10px', fontSize: '12px' }}
                      >
                        <Shield size={14} style={{ marginRight: '4px' }} />
                        <span>Role</span>
                      </Button>
                    )}

                    {canManageThisMember && (
                      <button
                        onClick={() => handleRemoveMember(m.id, m.display_name)}
                        disabled={actionInProgressId === m.id}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--status-overdue)', padding: '8px', minWidth: '36px', minHeight: '36px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                        aria-label={`Remove ${m.display_name}`}
                        title="Remove Member"
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      {/* 4. Pending Invitations */}
      {pendingInvites.length > 0 && (
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: 'var(--space-4)' }}>
            <Mail size={18} color="var(--color-primary-900)" />
            <h2 style={{ fontSize: '16px', fontWeight: 600 }}>
              Pending Invitations ({pendingInvites.length})
            </h2>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            {pendingInvites.map((inv) => {
              const code = inv.invitation_code || (inv as any).invite_code || (inv as any).code;
              return (
                <div
                  key={inv.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '14px 16px',
                    backgroundColor: 'var(--color-surface-subtle)',
                    borderRadius: 'var(--radius-md)',
                    flexWrap: 'wrap',
                    gap: '12px'
                  }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                      {inv.email || inv.phone_number || 'Family Member Invitation'}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <Badge variant={getRoleBadgeVariant(inv.role)}>
                        {getRoleDisplayName(inv.role)}
                      </Badge>
                      <Badge variant="low-stock">
                        {inv.status}
                      </Badge>
                      {code && (
                        <span
                          style={{
                            fontSize: '13px',
                            fontWeight: 700,
                            backgroundColor: '#f0fdf4',
                            padding: '3px 10px',
                            borderRadius: '6px',
                            border: '1px solid #bbf7d0',
                            fontFamily: 'monospace',
                            color: '#166534',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px'
                          }}
                        >
                          <KeyRound size={13} />
                          <span>Code:</span>
                          <strong style={{ letterSpacing: '0.05em', fontSize: '13px' }}>{code}</strong>
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)', marginTop: '2px' }}>
                      Expires: {new Date(inv.expires_at).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    {code && (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleCopyCode(code)}
                        style={{ minHeight: '38px', padding: '0 12px', fontSize: '12px', fontWeight: 600 }}
                        title="Copy Invitation Code"
                      >
                        {copiedCode === code ? <Check size={14} color="var(--status-in-stock)" /> : <KeyRound size={14} />}
                        <span>{copiedCode === code ? 'Code Copied' : 'Copy Code'}</span>
                      </Button>
                    )}

                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => handleCopyLink(inv.token)}
                      style={{ minHeight: '38px', padding: '0 12px', fontSize: '12px', fontWeight: 600 }}
                      title="Copy Invitation Link"
                    >
                      {copiedToken === inv.token ? <Check size={14} color="var(--status-in-stock)" /> : <Copy size={14} />}
                      <span>{copiedToken === inv.token ? 'Link Copied' : 'Copy Link'}</span>
                    </Button>

                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleResendInvite(inv.id)}
                      disabled={actionInProgressId === inv.id}
                      style={{ minHeight: '38px', padding: '0 8px' }}
                      title="Resend / Extend Invitation"
                    >
                      <RefreshCw size={14} className={actionInProgressId === inv.id ? 'animate-spin' : ''} />
                    </Button>

                    <button
                      onClick={() => handleCancelInvite(inv.id)}
                      disabled={actionInProgressId === inv.id}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--status-overdue)', padding: '8px', minWidth: '38px', minHeight: '38px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                      aria-label="Revoke invitation"
                      title="Revoke Invitation"
                    >
                      <X size={16} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* 5. Member Inspection Modal */}
      {inspectingMember && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Member Details Inspection"
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1100,
            padding: '16px'
          }}
        >
          <Card style={{ maxWidth: '560px', width: '100%', padding: '24px', maxHeight: '90vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', paddingBottom: '12px', borderBottom: '1px solid var(--color-border-subtle)' }}>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                  {inspectingMember.display_name}
                </h3>
                <div style={{ display: 'flex', gap: '6px', marginTop: '4px' }}>
                  <Badge variant={getRoleBadgeVariant(inspectingMember.role)}>
                    {getRoleDisplayName(inspectingMember.role)}
                  </Badge>
                  <Badge variant="neutral">Status: {inspectingMember.status}</Badge>
                </div>
              </div>
              <button
                onClick={() => setInspectingMember(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '6px' }}
                aria-label="Close modal"
              >
                <X size={18} />
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '13px' }}>
              <div>
                <span style={{ fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block' }}>Contact Information</span>
                <div style={{ marginTop: '4px' }}>
                  <div>Email: {inspectingMember.email || 'None'} {inspectingMember.email_verified && '✓'}</div>
                  <div>Phone: {inspectingMember.phone_number || 'None'} {inspectingMember.mobile_verified && '✓'}</div>
                </div>
              </div>

              <div>
                <span style={{ fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block' }}>Entitlement & Access State</span>
                <div style={{ marginTop: '4px', backgroundColor: 'var(--color-surface-subtle)', padding: '10px', borderRadius: '6px' }}>
                  <div>Access Status: <strong>{inspectingMember.access_status || 'ACTIVE'}</strong></div>
                  {inspectingMember.plan_name && <div>Plan: {inspectingMember.plan_name}</div>}
                  {inspectingMember.access_expires_at && (
                    <div>Expires At: {new Date(inspectingMember.access_expires_at).toLocaleString()}</div>
                  )}
                  {inspectingMember.days_until_expiry !== null && inspectingMember.days_until_expiry !== undefined && (
                    <div>Days Remaining: {inspectingMember.days_until_expiry} days</div>
                  )}
                </div>
              </div>

              <div>
                <span style={{ fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '6px' }}>
                  Recent Activity Timeline ({inspectingMember.recent_activity.length})
                </span>
                {inspectingMember.recent_activity.length === 0 ? (
                  <div style={{ color: 'var(--color-text-tertiary)', fontStyle: 'italic' }}>No audit activity recorded yet.</div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '160px', overflowY: 'auto' }}>
                    {inspectingMember.recent_activity.map((act) => (
                      <div key={act.id} style={{ padding: '8px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: '6px', fontSize: '12px' }}>
                        <div style={{ fontWeight: 600, color: 'var(--color-primary-900)' }}>{act.action}</div>
                        <div style={{ color: 'var(--color-text-tertiary)', fontSize: '11px' }}>
                          {new Date(act.created_at).toLocaleString()}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '20px' }}>
              <Button onClick={() => setInspectingMember(null)} style={{ minHeight: '40px' }}>
                Close
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* 6. New Created Invitation Showcase Modal */}
      {createdInviteModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Invitation Created"
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1100,
            padding: '16px'
          }}
        >
          <Card style={{ maxWidth: '480px', width: '100%', padding: '24px', position: 'relative', border: '2px solid var(--color-primary-900)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: '#f0fdf4', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#16a34a' }}>
                  <Check size={18} />
                </div>
                <h3 style={{ fontSize: '17px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                  Invitation Created!
                </h3>
              </div>
              <button
                onClick={() => setCreatedInviteModal(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '6px' }}
                aria-label="Close modal"
              >
                <X size={18} />
              </button>
            </div>

            <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginBottom: '16px', lineHeight: 1.5 }}>
              Share this invitation code or direct link with <strong>{createdInviteModal.email || createdInviteModal.phone_number || 'your family member'}</strong> so they can join your home workspace.
            </p>

            <div
              style={{
                backgroundColor: 'var(--color-surface-subtle)',
                border: '2px dashed var(--color-border-strong)',
                borderRadius: '8px',
                padding: '16px',
                textAlign: 'center',
                marginBottom: '16px'
              }}
            >
              <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px' }}>
                Invitation Code
              </div>
              <div
                style={{
                  fontSize: '24px',
                  fontWeight: 800,
                  fontFamily: 'monospace',
                  letterSpacing: '0.15em',
                  color: 'var(--color-primary-900)',
                  marginBottom: '12px'
                }}
              >
                {createdInviteModal.invitation_code || (createdInviteModal as any).invite_code || (createdInviteModal as any).code || 'OZ-PENDING'}
              </div>
              <div style={{ display: 'flex', justifyContent: 'center', gap: '8px' }}>
                {(createdInviteModal.invitation_code || (createdInviteModal as any).invite_code || (createdInviteModal as any).code) && (
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => handleCopyCode((createdInviteModal.invitation_code || (createdInviteModal as any).invite_code || (createdInviteModal as any).code)!)}
                    style={{ minHeight: '38px', padding: '0 14px', fontSize: '13px', fontWeight: 600 }}
                  >
                    {copiedCode === (createdInviteModal.invitation_code || (createdInviteModal as any).invite_code || (createdInviteModal as any).code) ? <Check size={15} color="var(--status-in-stock)" /> : <KeyRound size={15} />}
                    <span>{copiedCode === (createdInviteModal.invitation_code || (createdInviteModal as any).invite_code || (createdInviteModal as any).code) ? 'Code Copied' : 'Copy Code'}</span>
                  </Button>
                )}

                <Button
                  size="sm"
                  variant="primary"
                  onClick={() => handleCopyLink(createdInviteModal.token)}
                  style={{ minHeight: '38px', padding: '0 14px', fontSize: '13px', fontWeight: 600 }}
                >
                  {copiedToken === createdInviteModal.token ? <Check size={15} /> : <Copy size={15} />}
                  <span>{copiedToken === createdInviteModal.token ? 'Link Copied' : 'Copy Link'}</span>
                </Button>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Button onClick={() => setCreatedInviteModal(null)} style={{ minHeight: '40px' }}>
                Done
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* 7. Change Member Role Modal */}
      {editingMemberRole && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Change Member Role"
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '16px'
          }}
        >
          <Card style={{ maxWidth: '420px', width: '100%', padding: '24px', position: 'relative' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-primary-900)' }}>
                Change Role: {editingMemberRole.name}
              </h3>
              <button
                onClick={() => setEditingMemberRole(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '6px' }}
                aria-label="Close modal"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSaveMemberRole} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ fontSize: '13px', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                  Select New Household Role
                </label>
                <select
                  value={newSelectedRole}
                  onChange={(e) => setNewSelectedRole(e.target.value)}
                  style={{
                    width: '100%',
                    height: '42px',
                    padding: '0 12px',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--color-border-strong)',
                    backgroundColor: 'var(--color-surface-card)',
                    fontSize: '14px'
                  }}
                >
                  <option value="HOME_ADMIN">Home Admin (Co-management)</option>
                  <option value="ADMIN">Admin (Full Management)</option>
                  <option value="MEMBER">Adult Member (Chores & Bills)</option>
                  <option value="CHILD">Child (Chores Only)</option>
                  <option value="GUEST">Guest (Limited Scope)</option>
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '8px' }}>
                <Button type="button" variant="secondary" onClick={() => setEditingMemberRole(null)} style={{ minHeight: '44px' }}>
                  Cancel
                </Button>
                <Button type="submit" isLoading={isSavingRole} style={{ minHeight: '44px' }}>
                  Save Role
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}
    </div>
  );
}
