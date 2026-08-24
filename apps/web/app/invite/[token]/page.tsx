'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { Logo } from '@/components/brand/Logo';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import {
  Home,
  Check,
  AlertCircle,
  Clock,
  XCircle,
  ArrowRight,
  ShieldCheck,
  KeyRound,
  UserCheck
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

interface InvitationDetail {
  id: string;
  home_id: string;
  home_name: string;
  role: string;
  token: string;
  invitation_code?: string | null;
  status: string;
  invited_by_name?: string | null;
  invited_by_email?: string | null;
  email?: string | null;
  phone_number?: string | null;
  expires_at: string;
  is_expired?: boolean;
  is_already_member?: boolean;
}

interface UserProfile {
  id: string;
  display_name: string;
  email?: string | null;
  phone_number?: string | null;
  is_active: boolean;
}

function formatErrorMessage(err: any): string {
  if (!err) return 'An error occurred';
  if (typeof err === 'string') return err;
  if (typeof err?.message === 'string') return err.message;
  if (Array.isArray(err?.detail)) {
    return err.detail.map((d: any) => (typeof d === 'string' ? d : d.msg || d.message || JSON.stringify(d))).join(', ');
  }
  if (typeof err?.detail === 'string') return err.detail;
  return 'An unexpected error occurred';
}

export default function InvitationPage() {
  const params = useParams();
  const router = useRouter();
  const token = params.token as string;

  const [invitation, setInvitation] = useState<InvitationDetail | null>(null);
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAccepting, setIsAccepting] = useState(false);
  const [isDeclining, setIsDeclining] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    const fetchInviteAndUser = async () => {
      setIsLoading(true);
      setErrorMessage(null);

      // Check current user session
      let user: UserProfile | null = null;
      try {
        if (apiClient.hasToken()) {
          user = await apiClient.get<UserProfile>('/users/me');
          setCurrentUser(user);
        }
      } catch (err) {
        // Unauthenticated session is normal for prospective members
        setCurrentUser(null);
      }

      // Fetch invitation details
      try {
        const inviteData = await apiClient.get<InvitationDetail>(`/invitations/${token}`);
        setInvitation(inviteData);
      } catch (err: any) {
        console.error('Failed to load invitation details:', err);
        setErrorMessage(formatErrorMessage(err));
      } finally {
        setIsLoading(false);
      }
    };

    if (token) {
      fetchInviteAndUser();
    }
  }, [token]);

  const handleAccept = async () => {
    if (!token) return;
    setIsAccepting(true);
    setErrorMessage(null);
    try {
      const res = await apiClient.post<{ home_id: string; home_name: string; role: string; message: string }>(
        `/invitations/${token}/accept`,
        {}
      );

      // Set active home in storage and API client
      if (res?.home_id) {
        apiClient.setActiveHomeId(res.home_id);
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new Event('home-changed'));
        }
      }

      setSuccessMessage(res?.message || `You have joined '${invitation?.home_name}'!`);
      setTimeout(() => {
        router.push('/dashboard');
      }, 1500);
    } catch (err: any) {
      console.error('Accept invitation failed:', err);
      setErrorMessage(formatErrorMessage(err));
      setIsAccepting(false);
    }
  };

  const handleDecline = async () => {
    if (!token) return;
    if (!confirm('Are you sure you want to decline this invitation?')) return;
    setIsDeclining(true);
    setErrorMessage(null);
    try {
      await apiClient.post(`/invitations/${token}/decline`, {});
      setInvitation(prev => (prev ? { ...prev, status: 'DECLINED' } : null));
    } catch (err: any) {
      console.error('Decline invitation failed:', err);
      setErrorMessage(formatErrorMessage(err));
    } finally {
      setIsDeclining(false);
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
        return 'Adult Member';
      case 'CHILD':
        return 'Child';
      case 'GUEST':
        return 'Guest';
      default:
        return role;
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: 'var(--color-surface-background, #f8fafc)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px'
      }}
    >
      <div style={{ marginBottom: '24px' }}>
        <Logo variant="full" width={180} height={48} />
      </div>

      <Card
        style={{
          maxWidth: '480px',
          width: '100%',
          padding: '32px',
          boxShadow: 'var(--shadow-floating, 0 10px 25px -5px rgba(0, 0, 0, 0.1))',
          borderRadius: 'var(--radius-lg, 16px)',
          border: '1px solid var(--color-border-subtle, #e2e8f0)'
        }}
      >
        {isLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', padding: '24px 0' }}>
            <div style={{ width: '48px', height: '48px', borderRadius: '50%', border: '3px solid var(--color-primary-900)', borderTopColor: 'transparent', animation: 'spin 1s linear infinite' }} />
            <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)' }}>Verifying invitation link...</p>
          </div>
        ) : errorMessage && !invitation ? (
          <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ width: '56px', height: '56px', borderRadius: '50%', backgroundColor: 'var(--status-overdue-bg, #fef2f2)', color: 'var(--status-overdue, #ef4444)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto' }}>
              <AlertCircle size={28} />
            </div>
            <h2 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-text-primary)' }}>
              Invitation Unavailable
            </h2>
            <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
              {errorMessage || 'This invitation link could not be verified. It may have expired, been revoked, or already used.'}
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '12px' }}>
              <Link href="/join" style={{ textDecoration: 'none' }}>
                <Button variant="secondary" style={{ width: '100%', minHeight: '44px' }}>
                  <KeyRound size={16} />
                  <span>Enter Invitation Code</span>
                </Button>
              </Link>
              <Link href="/dashboard" style={{ textDecoration: 'none' }}>
                <Button variant="ghost" style={{ width: '100%', minHeight: '44px' }}>
                  Go to Dashboard
                </Button>
              </Link>
            </div>
          </div>
        ) : invitation ? (
          <div>
            {/* Header Icon */}
            <div style={{ textAlign: 'center', marginBottom: '20px' }}>
              <div
                style={{
                  width: '64px',
                  height: '64px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--color-primary-900, #0f172a)',
                  color: '#ffffff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 16px'
                }}
              >
                <Home size={32} />
              </div>
              <h1 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                Household Invitation
              </h1>
              <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
                <strong>{invitation.invited_by_name || 'A family member'}</strong> invited you to join:
              </p>
            </div>

            {/* Home Card Preview */}
            <div
              style={{
                backgroundColor: 'var(--color-surface-subtle, #f1f5f9)',
                borderRadius: 'var(--radius-md, 10px)',
                padding: '16px',
                marginBottom: '20px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                  {invitation.home_name}
                </span>
                <Badge variant="completed">
                  {getRoleDisplayName(invitation.role)}
                </Badge>
              </div>

              {invitation.invitation_code && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
                  <KeyRound size={14} />
                  <span>Invitation Code: <strong>{invitation.invitation_code}</strong></span>
                </div>
              )}

              <div style={{ fontSize: '12px', color: 'var(--color-text-tertiary)' }}>
                Expires: {new Date(invitation.expires_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
              </div>
            </div>

            {/* Success State */}
            {successMessage && (
              <div
                style={{
                  padding: '14px 18px',
                  backgroundColor: 'var(--status-in-stock-bg, #ecfdf5)',
                  color: 'var(--status-in-stock, #10b981)',
                  borderRadius: 'var(--radius-md, 10px)',
                  fontSize: '14px',
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  marginBottom: '16px'
                }}
              >
                <Check size={18} />
                <span>{successMessage}</span>
              </div>
            )}

            {/* Error Banner */}
            {errorMessage && (
              <div
                style={{
                  padding: '12px 16px',
                  backgroundColor: 'var(--status-overdue-bg, #fef2f2)',
                  color: 'var(--status-overdue, #ef4444)',
                  borderRadius: 'var(--radius-md, 10px)',
                  fontSize: '13px',
                  fontWeight: 500,
                  marginBottom: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
              >
                <AlertCircle size={16} />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* State Handling */}
            {invitation.is_already_member ? (
              <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', color: 'var(--status-in-stock)', fontWeight: 600, fontSize: '14px' }}>
                  <UserCheck size={18} />
                  <span>You are already an active member of this Home.</span>
                </div>
                <Link href="/dashboard" style={{ textDecoration: 'none' }}>
                  <Button style={{ width: '100%', minHeight: '44px' }}>
                    <span>Open Dashboard</span>
                    <ArrowRight size={16} />
                  </Button>
                </Link>
              </div>
            ) : invitation.status === 'ACCEPTED' ? (
              <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', color: 'var(--color-text-secondary)', fontSize: '14px' }}>
                  <Check size={18} />
                  <span>This invitation has already been accepted.</span>
                </div>
                <Link href="/dashboard" style={{ textDecoration: 'none' }}>
                  <Button style={{ width: '100%', minHeight: '44px' }}>
                    <span>Open Dashboard</span>
                    <ArrowRight size={16} />
                  </Button>
                </Link>
              </div>
            ) : invitation.is_expired || invitation.status === 'EXPIRED' ? (
              <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', color: 'var(--status-overdue)', fontSize: '14px', fontWeight: 600 }}>
                  <Clock size={18} />
                  <span>This invitation has expired.</span>
                </div>
                <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
                  Ask your Home Admin to resend the invitation or share a fresh invitation code.
                </p>
                <Link href="/join" style={{ textDecoration: 'none' }}>
                  <Button variant="secondary" style={{ width: '100%', minHeight: '44px' }}>
                    Join Home with Code
                  </Button>
                </Link>
              </div>
            ) : invitation.status === 'REVOKED' || invitation.status === 'DECLINED' ? (
              <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', color: 'var(--status-overdue)', fontSize: '14px', fontWeight: 600 }}>
                  <XCircle size={18} />
                  <span>This invitation has been revoked or declined.</span>
                </div>
                <Link href="/join" style={{ textDecoration: 'none' }}>
                  <Button variant="secondary" style={{ width: '100%', minHeight: '44px' }}>
                    Join Home with Code
                  </Button>
                </Link>
              </div>
            ) : !currentUser ? (
              /* Unauthenticated user flow */
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', textAlign: 'center', marginBottom: '4px' }}>
                  Sign in or create an account to accept this invitation:
                </p>
                <Link href={`/login?redirect=/invite/${token}`} style={{ textDecoration: 'none' }}>
                  <Button style={{ width: '100%', minHeight: '44px' }}>
                    <span>Sign In to Accept</span>
                    <ArrowRight size={16} />
                  </Button>
                </Link>
                <Link href={`/register?redirect=/invite/${token}`} style={{ textDecoration: 'none' }}>
                  <Button variant="secondary" style={{ width: '100%', minHeight: '44px' }}>
                    Create New Account
                  </Button>
                </Link>
              </div>
            ) : (
              /* Authenticated active member joining flow */
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)', textAlign: 'center', marginBottom: '6px' }}>
                  Signed in as <strong>{currentUser.display_name || currentUser.email}</strong>
                </div>
                <Button
                  onClick={handleAccept}
                  isLoading={isAccepting}
                  disabled={isDeclining || !!successMessage}
                  style={{ width: '100%', minHeight: '46px' }}
                >
                  <ShieldCheck size={18} />
                  <span>Accept & Join Home</span>
                </Button>
                <Button
                  variant="ghost"
                  onClick={handleDecline}
                  isLoading={isDeclining}
                  disabled={isAccepting || !!successMessage}
                  style={{ width: '100%', minHeight: '44px', color: 'var(--color-text-secondary)' }}
                >
                  Decline Invitation
                </Button>
              </div>
            )}
          </div>
        ) : null}
      </Card>

      <div style={{ marginTop: '20px', fontSize: '13px', color: 'var(--color-text-tertiary)' }}>
        Have an invitation code? <Link href="/join" style={{ color: 'var(--color-primary-900)', fontWeight: 600 }}>Enter Invitation Code</Link>
      </div>
    </div>
  );
}
