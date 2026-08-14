'use client';

import React, { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Users, UserPlus, Shield, Copy, Check, Trash2, Mail } from 'lucide-react';

export default function MembersPage() {
  const [members] = useState([
    { id: '1', name: 'Alex Rivera', email: 'alex@example.com', role: 'OWNER', avatar: 'AR' },
    { id: '2', name: 'Sarah Rivera', email: 'sarah@example.com', role: 'ADMIN', avatar: 'SR' },
    { id: '3', name: 'Leo Rivera', email: 'leo@example.com', role: 'CHILD', avatar: 'LR' },
  ]);

  const [pendingInvites, setPendingInvites] = useState([
    { id: 'inv-1', email: 'grandma@example.com', role: 'GUEST', token: 'ozhzo_inv_78a1b2c3' }
  ]);

  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('MEMBER');
  const [copiedToken, setCopiedToken] = useState<string | null>(null);

  const handleCopyLink = (token: string) => {
    navigator.clipboard.writeText(`https://app.ozhzoverse.com/join?token=${token}`);
    setCopiedToken(token);
    setTimeout(() => setCopiedToken(null), 2000);
  };

  const handleCreateInvite = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail) return;
    setPendingInvites([
      ...pendingInvites,
      { id: `inv-${Date.now()}`, email: inviteEmail, role: inviteRole, token: `ozhzo_inv_${Math.random().toString(36).substring(2, 9)}` }
    ]);
    setInviteEmail('');
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

      {/* Invite Member Section */}
      <Card>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: 'var(--space-4)' }}>
          <UserPlus size={18} color="var(--color-accent-warm)" />
          <h2 style={{ fontSize: '16px', fontWeight: 600 }}>Invite New Member</h2>
        </div>

        <form onSubmit={handleCreateInvite} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr auto', gap: 'var(--space-3)', alignItems: 'flex-end' }}>
          <Input
            id="inviteEmail"
            type="email"
            label="Email Address (Optional)"
            placeholder="family.member@example.com"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
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
              <option value="CHILD">Child (Chores Only, Private)</option>
              <option value="GUEST">Guest (Limited Scope)</option>
            </select>
          </div>

          <Button type="submit">
            Generate Invite
          </Button>
        </form>
      </Card>

      {/* Active Members List */}
      <Card>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)', paddingBottom: 'var(--space-3)', borderBottom: '1px solid var(--color-border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Users size={18} color="var(--color-primary-900)" />
            <h2 style={{ fontSize: '16px', fontWeight: 600 }}>Active Household Members ({members.length}/5)</h2>
          </div>
          <Badge variant="in-stock">Free Tier: Max 5</Badge>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {members.map((m) => (
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
                  {m.avatar}
                </div>
                <div>
                  <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-primary)' }}>{m.name}</div>
                  <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>{m.email}</div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <Badge variant={m.role === 'OWNER' ? 'in-stock' : m.role === 'ADMIN' ? 'low-stock' : 'neutral'}>
                  {m.role}
                </Badge>
                {m.role !== 'OWNER' && (
                  <button style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--status-overdue)', padding: '4px' }}>
                    <Trash2 size={16} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Pending Invitations */}
      {pendingInvites.length > 0 && (
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: 'var(--space-4)' }}>
            <Mail size={18} color="var(--color-primary-900)" />
            <h2 style={{ fontSize: '16px', fontWeight: 600 }}>Pending Invitations</h2>
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
                  <div style={{ fontSize: '13px', fontWeight: 600 }}>{inv.email}</div>
                  <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>Role: {inv.role} • Expires in 7 days</div>
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
