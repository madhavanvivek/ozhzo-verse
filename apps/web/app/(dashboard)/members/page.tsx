'use client';

import React, { useEffect, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Users, UserPlus, Copy, Check, Trash2, Mail, AlertCircle, RefreshCw, X, Shield, KeyRound } from 'lucide-react';
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
  const [members, setMembers] = useState<MemberItem[]>([]);
  const [pendingInvites, setPendingInvites] = useState<InvitationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  // Role Editing State
  const [editingMemberRole, setEditingMemberRole] = useState<{ id: string; name: string; currentRole: string } | null>(null);
  const [newSelectedRole, setNewSelectedRole] = useState<string>('MEMBER');
  const [isSavingRole, setIsSavingRole] = useState(false);

  // New Invite Showcase Modal State
  const [createdInviteModal, setCreatedInviteModal] = useState<InvitationItem | null>(null);

  const loadData = async (showLoading = true) => {
    if (showLoading) setIsLoading(true);
    setError(null);
    try {
      const userRes = await apiClient.get<UserProfile>('/users/me');
      setCurrentUser(userRes);

      const homeId = await apiClient.getValidActiveHome();
      setActiveHomeId(homeId);

      if (homeId) {
        const [membersRes, invitesRes] = await Promise.allSettled([
          apiClient.get<MemberItem[]>(`/homes/${homeId}/members`),
          apiClient.get<InvitationItem[]>(`/homes/${homeId}/invitations`)
        ]);

        if (membersRes.status === 'fulfilled' && membersRes.value) {
          setMembers(Array.isArray(membersRes.value) ? membersRes.value : []);
        } else {
          setMembers([]);
        }

        if (invitesRes.status === 'fulfilled' && invitesRes.value) {
          setPendingInvites(Array.isArray(invitesRes.value) ? invitesRes.value : []);
        } else {
          setPendingInvites([]);
        }
      }
    } catch (err: any) {
      console.error('Failed to load members or invitations:', err);
      setError(formatErrorMessage(err));
    } finally {
      if (showLoading) setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const handleHomeChanged = () => loadData(false);
    window.addEventListener('home-changed', handleHomeChanged);
    return () => window.removeEventListener('home-changed', handleHomeChanged);
  }, []);

  const activeMembership = currentUser?.homes?.find((h) => h.home_id === activeHomeId);
  const currentUserRole = activeMembership?.role || 'MEMBER';
  const canManageMembers = ['OWNER', 'HOME_ADMIN', 'ADMIN'].includes(currentUserRole);

  const getInitials = (name?: string | null): string => {
    if (!name || !name.trim()) return 'M';
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) {
      return parts[0].substring(0, 2).toUpperCase();
    }
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  };

  const handleCopyLink = (token: string) => {
    const origin = typeof window !== 'undefined' ? window.location.origin : 'https://ozhzo-web.onrender.com';
    navigator.clipboard.writeText(`${origin}/invite/${token}`);
    setCopiedToken(token);
    setTimeout(() => setCopiedToken(null), 2000);
  };

  const handleCopyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  const handleCreateInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeHomeId) return;
    if (!inviteEmail.trim() && !invitePhone.trim()) {
      setInviteError('Please provide an email address or mobile number for the invitation.');
      return;
    }

    setIsSubmittingInvite(true);
    setInviteError(null);
    setInviteSuccess(null);

    try {
      const payload = {
        email: inviteEmail.trim() || undefined,
        phone_number: invitePhone.trim() || undefined,
        role: inviteRole,
        invitation_mode: 'INVITE_ONLY'
      };

      const newInvite = await apiClient.post<InvitationItem>(`/homes/${activeHomeId}/invitations`, payload);
      setCreatedInviteModal(newInvite);
      setPendingInvites(prev => [newInvite, ...prev.filter(i => i.id !== newInvite.id)]);
      setInviteEmail('');
      setInvitePhone('');
      const inviteCode = newInvite.invitation_code || (newInvite as any).invite_code || (newInvite as any).code;
      const codeMsg = inviteCode ? ` (Code: ${inviteCode})` : '';
      setInviteSuccess(`Invitation created successfully${codeMsg}. Share the link or code below with your family member.`);
      setTimeout(() => setInviteSuccess(null), 8000);
      loadData(false);
    } catch (err: any) {
      console.error('Failed to create invitation:', err);
      setInviteError(formatErrorMessage(err));
    } finally {
      setIsSubmittingInvite(false);
    }
  };

  const handleResendInvite = async (inviteId: string) => {
    if (!activeHomeId) return;
    setActionInProgressId(inviteId);
    try {
      await apiClient.post(`/homes/${activeHomeId}/invitations/${inviteId}/resend`, {});
      await loadData(false);
      setInviteSuccess('Invitation link refreshed and expiry extended.');
      setTimeout(() => setInviteSuccess(null), 4000);
    } catch (err: any) {
      alert(formatErrorMessage(err));
    } finally {
      setActionInProgressId(null);
    }
  };

  const handleCancelInvite = async (inviteId: string) => {
    if (!activeHomeId) return;
    if (!confirm('Cancel this pending invitation?')) return;
    setActionInProgressId(inviteId);
    try {
      await apiClient.delete(`/homes/${activeHomeId}/invitations/${inviteId}`);
      setPendingInvites(prev => prev.filter(i => i.id !== inviteId));
    } catch (err: any) {
      alert(formatErrorMessage(err));
    } finally {
      setActionInProgressId(null);
    }
  };

  const handleOpenRoleModal = (m: MemberItem) => {
    setEditingMemberRole({ id: m.id, name: m.display_name, currentRole: m.role });
    setNewSelectedRole(m.role === 'OWNER' ? 'HOME_ADMIN' : m.role);
  };

  const handleSaveMemberRole = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeHomeId || !editingMemberRole) return;

    setIsSavingRole(true);
    try {
      await apiClient.patch(`/homes/${activeHomeId}/members/${editingMemberRole.id}/role`, {
        role: newSelectedRole
      });
      setMembers(prev => prev.map(m => m.id === editingMemberRole.id ? { ...m, role: newSelectedRole } : m));
      setEditingMemberRole(null);
      await loadData(false);
    } catch (err: any) {
      alert(formatErrorMessage(err));
    } finally {
      setIsSavingRole(false);
    }
  };

  const handleRemoveMember = async (memberId: string, memberName: string) => {
    if (!activeHomeId) return;
    if (!confirm(`Are you sure you want to remove ${memberName} from this Home workspace?`)) return;

    setActionInProgressId(memberId);
    try {
      await apiClient.delete(`/homes/${activeHomeId}/members/${memberId}`);
      setMembers(prev => prev.filter((m) => m.id !== memberId));
    } catch (err: any) {
      console.error('Failed to remove member:', err);
      alert(formatErrorMessage(err));
    } finally {
      setActionInProgressId(null);
    }
  };

  const getRoleBadgeVariant = (role: string) => {
    switch (role) {
      case 'OWNER':
      case 'HOME_ADMIN':
        return 'completed';
      case 'ADMIN':
        return 'low-stock';
      case 'MEMBER':
        return 'neutral';
      case 'CHILD':
        return 'neutral';
      case 'GUEST':
      default:
        return 'neutral';
    }
  };

  const getRoleDisplayName = (role: string) => {
    switch (role) {
      case 'OWNER':
        return 'Owner';
      case 'HOME_ADMIN':
        return 'Home Admin';
      case 'ADMIN':
        return 'Admin';
      case 'MEMBER':
        return 'Member';
      case 'CHILD':
        return 'Child';
      case 'GUEST':
        return 'Guest';
      default:
        return role;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '900px', width: '100%' }}>
      <div>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-primary-900)' }}>
          Family Members & Roles
        </h1>
        <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)' }}>
          Manage who has access to this Home workspace and their permissions.
        </p>
      </div>

      {error && (
        <div style={{ padding: '12px 16px', backgroundColor: 'var(--status-overdue-bg)', color: 'var(--status-overdue)', borderRadius: 'var(--radius-md)', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Invite Member Section (Only for OWNER, HOME_ADMIN, ADMIN) */}
      {canManageMembers && (
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: 'var(--space-4)' }}>
            <UserPlus size={18} color="var(--color-accent-warm)" />
            <h2 style={{ fontSize: '16px', fontWeight: 600 }}>Invite New Member</h2>
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

      {/* Active Members List */}
      <Card>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)', paddingBottom: 'var(--space-3)', borderBottom: '1px solid var(--color-border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Users size={18} color="var(--color-primary-900)" />
            <h2 style={{ fontSize: '16px', fontWeight: 600 }}>
              Active Household Members ({members.length})
            </h2>
          </div>
          <Badge variant="neutral">Active Workspace</Badge>
        </div>

        {isLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {[1, 2, 3].map((i) => (
              <div key={i} style={{ height: '60px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: 'var(--radius-md)', animation: 'pulse 1.5s infinite' }} />
            ))}
          </div>
        ) : members.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 'var(--space-8)', color: 'var(--color-text-secondary)', fontSize: '14px' }}>
            No members found in this Home workspace.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            {members.map((m) => {
              const isMe = currentUser?.id === m.user_id;
              const canManageThisMember = canManageMembers && !isMe && !['OWNER'].includes(m.role);

              return (
                <div
                  key={m.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '12px 14px',
                    backgroundColor: 'var(--color-surface-subtle)',
                    borderRadius: 'var(--radius-md)',
                    flexWrap: 'wrap',
                    gap: '12px'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: '200px' }}>
                    <div style={{ width: '38px', height: '38px', borderRadius: '50%', backgroundColor: 'var(--color-primary-900)', color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '13px', fontWeight: 600 }}>
                      {getInitials(m.display_name)}
                    </div>
                    <div>
                      <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                        {m.display_name} {isMe && <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>(You)</span>}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                        {m.email || m.phone_number || 'No contact provided'}
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <Badge variant={getRoleBadgeVariant(m.role)}>
                      {getRoleDisplayName(m.role)}
                    </Badge>

                    {canManageThisMember && (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleOpenRoleModal(m)}
                        style={{ minHeight: '44px', padding: '0 10px', fontSize: '12px' }}
                      >
                        <Shield size={14} style={{ marginRight: '4px' }} />
                        <span>Role</span>
                      </Button>
                    )}

                    {canManageThisMember && (
                      <button
                        onClick={() => handleRemoveMember(m.id, m.display_name)}
                        disabled={actionInProgressId === m.id}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--status-overdue)', padding: '10px', minWidth: '44px', minHeight: '44px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
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

      {/* Pending Invitations */}
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

      {/* New Created Invitation Showcase Modal */}
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

            {/* Prominent Code Box */}
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

      {/* Change Member Role Modal */}
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
