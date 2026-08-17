'use client';

import React, { useEffect, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Users, UserPlus, Copy, Check, Trash2, Mail, AlertCircle } from 'lucide-react';
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
  invite_url?: string;
  status: string;
  invited_by?: string;
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
  const [removingMemberId, setRemovingMemberId] = useState<string | null>(null);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const savedHomeId = localStorage.getItem('active_home_id');
      let homeId = savedHomeId;

      const userRes = await apiClient.get<UserProfile>('/users/me');
      setCurrentUser(userRes);

      if (!homeId && userRes?.homes?.length > 0) {
        homeId = userRes.homes[0].home_id;
        localStorage.setItem('active_home_id', homeId);
      }

      setActiveHomeId(homeId);

      if (homeId) {
        const [membersRes, invitesRes] = await Promise.allSettled([
          apiClient.get<MemberItem[]>(`/homes/${homeId}/members`),
          apiClient.get<InvitationItem[]>(`/homes/${homeId}/invitations`)
        ]);

        if (membersRes.status === 'fulfilled' && membersRes.value) {
          setMembers(membersRes.value);
        } else {
          setMembers([]);
        }

        if (invitesRes.status === 'fulfilled' && invitesRes.value) {
          setPendingInvites(invitesRes.value);
        } else {
          setPendingInvites([]);
        }
      }
    } catch (err: any) {
      console.error('Failed to load members or invitations:', err);
      setError(err?.message || 'Unable to load members.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const activeMembership = currentUser?.homes.find((h) => h.home_id === activeHomeId);
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
    const origin = typeof window !== 'undefined' ? window.location.origin : 'https://app.ozhzoverse.com';
    navigator.clipboard.writeText(`${origin}/join?token=${token}`);
    setCopiedToken(token);
    setTimeout(() => setCopiedToken(null), 2000);
  };

  const handleCreateInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeHomeId) return;
    if (!inviteEmail.trim() && !invitePhone.trim()) {
      setInviteError('Please provide an email address or phone number for the invite.');
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
        invitation_mode: 'STANDARD'
      };

      const newInvite = await apiClient.post<InvitationItem>(`/homes/${activeHomeId}/invitations`, payload);
      setPendingInvites([newInvite, ...pendingInvites]);
      setInviteEmail('');
      setInvitePhone('');
      setInviteSuccess('Invitation created successfully. Copy the link below to share.');
      setTimeout(() => setInviteSuccess(null), 4000);
    } catch (err: any) {
      console.error('Failed to create invitation:', err);
      setInviteError(err?.message || 'Failed to create invitation.');
    } finally {
      setIsSubmittingInvite(false);
    }
  };

  const handleRemoveMember = async (memberId: string) => {
    if (!activeHomeId) return;
    if (!confirm('Are you sure you want to remove this member from the Home workspace?')) return;

    setRemovingMemberId(memberId);
    try {
      await apiClient.delete(`/homes/${activeHomeId}/members/${memberId}`);
      setMembers(members.filter((m) => m.id !== memberId));
    } catch (err: any) {
      console.error('Failed to remove member:', err);
      alert(err?.message || 'Failed to remove member.');
    } finally {
      setRemovingMemberId(null);
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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '900px' }}>
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
            <div style={{ padding: '8px 12px', backgroundColor: 'var(--status-in-stock-bg)', color: 'var(--status-in-stock)', borderRadius: 'var(--radius-md)', fontSize: '13px', fontWeight: 600, marginBottom: 'var(--space-3)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Check size={16} />
              <span>{inviteSuccess}</span>
            </div>
          )}

          {inviteError && (
            <div style={{ padding: '8px 12px', backgroundColor: 'var(--status-overdue-bg)', color: 'var(--status-overdue)', borderRadius: 'var(--radius-md)', fontSize: '13px', fontWeight: 500, marginBottom: 'var(--space-3)' }}>
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
              placeholder="+1234567890"
              value={invitePhone}
              onChange={(e) => setInvitePhone(e.target.value)}
            />

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label htmlFor="inviteRole" style={{ fontSize: '13px', fontWeight: 600 }}>
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
                <option value="ADMIN">Admin (Full Management)</option>
                <option value="MEMBER">Adult Member (Chores & Bills)</option>
                <option value="CHILD">Child (Chores Only)</option>
                <option value="GUEST">Guest (Limited Scope)</option>
              </select>
            </div>

            <Button type="submit" isLoading={isSubmittingInvite} disabled={!activeHomeId}>
              Generate Invite
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
              const canRemoveThisMember = canManageMembers && !isMe && !['OWNER', 'HOME_ADMIN'].includes(m.role);

              return (
                <div
                  key={m.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '12px 14px',
                    backgroundColor: 'var(--color-surface-subtle)',
                    borderRadius: 'var(--radius-md)'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ width: '36px', height: '36px', borderRadius: '50%', backgroundColor: 'var(--color-primary-900)', color: 'var(--color-text-inverse)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '13px', fontWeight: 600 }}>
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

                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <Badge variant={getRoleBadgeVariant(m.role)}>
                      {m.role}
                    </Badge>
                    {canRemoveThisMember && (
                      <button
                        onClick={() => handleRemoveMember(m.id)}
                        disabled={removingMemberId === m.id}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--status-overdue)', padding: '4px' }}
                        aria-label={`Remove ${m.display_name}`}
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
            {pendingInvites.map((inv) => (
              <div
                key={inv.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px 14px',
                  backgroundColor: 'var(--color-surface-subtle)',
                  borderRadius: 'var(--radius-md)'
                }}
              >
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                    {inv.email || inv.phone_number || 'General Link Invite'}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>
                    Role: {inv.role} • Status: {inv.status} • Expires: {new Date(inv.expires_at).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                  </div>
                </div>

                <Button size="sm" variant="secondary" onClick={() => handleCopyLink(inv.token)}>
                  {copiedToken === inv.token ? <Check size={14} color="var(--status-in-stock)" /> : <Copy size={14} />}
                  <span>{copiedToken === inv.token ? 'Copied' : 'Copy Link'}</span>
                </Button>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
