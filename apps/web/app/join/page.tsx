'use client';

import React, { useState, useEffect, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Logo } from '@/components/brand/Logo';
import {
  KeyRound,
  Check,
  AlertCircle,
  ArrowRight,
  Home,
  Users,
  Send
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

interface AcceptInvitationResponse {
  home_id: string;
  home_name: string;
  role: string;
  message: string;
}

interface HomePublicInfoDTO {
  home_id: string;
  home_name: string;
  public_home_id: string;
  owner_name?: string | null;
  member_count: number;
  qr_status: string;
  is_active: boolean;
  accepts_members: boolean;
}

function JoinHomeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [code, setCode] = useState('');
  const [qrToken, setQrToken] = useState<string | null>(null);
  const [qrHomeInfo, setQrHomeInfo] = useState<HomePublicInfoDTO | null>(null);
  const [joinMessage, setJoinMessage] = useState('');
  const [isLoadingQr, setIsLoadingQr] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [requestSubmitted, setRequestSubmitted] = useState(false);

  useEffect(() => {
    const codeParam = searchParams.get('code') || searchParams.get('token');
    const qrParam = searchParams.get('qr');

    if (qrParam) {
      setQrToken(qrParam.trim());
      resolveQr(qrParam.trim());
    } else if (codeParam) {
      setCode(codeParam.trim());
    }
  }, [searchParams]);

  const resolveQr = async (token: string) => {
    setIsLoadingQr(true);
    setErrorMessage(null);
    try {
      const res = await apiClient.get<HomePublicInfoDTO>(`/homes/public/resolve-qr/${token}`);
      setQrHomeInfo(res);
    } catch (err: any) {
      console.error('Failed to resolve Home QR:', err);
      setErrorMessage(err?.message || 'This Home QR code is invalid or has expired.');
    } finally {
      setIsLoadingQr(false);
    }
  };

  const handleRedeemInvitation = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanCode = code.trim();
    if (!cleanCode) {
      setErrorMessage('Please enter an invitation code or paste your invitation link.');
      return;
    }

    if (!apiClient.hasToken()) {
      router.push(`/login?redirect=/join?code=${encodeURIComponent(cleanCode)}`);
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const res = await apiClient.post<AcceptInvitationResponse>('/homes/invitations/redeem', {
        invitation_code: cleanCode
      });

      if (res?.home_id) {
        apiClient.setActiveHomeId(res.home_id);
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new Event('home-changed'));
        }
      }

      setSuccessMessage(res?.message || `Welcome to ${res.home_name}!`);
      setTimeout(() => {
        router.push('/dashboard');
      }, 1500);
    } catch (err: any) {
      console.error('Join home failed:', err);
      setErrorMessage(err?.message || 'Failed to accept invitation.');
      setIsSubmitting(false);
    }
  };

  const handleQrJoinRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!qrToken) return;

    if (!apiClient.hasToken()) {
      router.push(`/login?redirect=/join?qr=${encodeURIComponent(qrToken)}`);
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await apiClient.post(`/homes/public/join-request/${qrToken}`, {
        message: joinMessage.trim() || undefined
      });
      setRequestSubmitted(true);
      setSuccessMessage('Join request submitted! The household administrator will review your request.');
    } catch (err: any) {
      console.error('Failed to submit join request:', err);
      setErrorMessage(err?.message || 'Failed to submit join request.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        padding: 'var(--space-6) var(--space-4)',
        backgroundColor: 'var(--color-background)'
      }}
    >
      <div style={{ width: '100%', maxWidth: '440px', display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <Logo height={48} width={180} />
        </div>

        {isLoadingQr ? (
          <Card style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--color-text-secondary)' }}>
            Verifying Home QR code...
          </Card>
        ) : qrToken && qrHomeInfo ? (
          <Card style={{ padding: 'var(--space-6)', border: '1px solid var(--color-border-strong)' }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-5)' }}>
              <div
                style={{
                  width: '52px',
                  height: '52px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--color-surface-subtle)',
                  color: 'var(--color-primary-900)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                <Home size={26} />
              </div>
              <h1 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                {qrHomeInfo.home_name}
              </h1>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', justifyContent: 'center' }}>
                <span style={{
                  fontFamily: 'monospace',
                  fontSize: '13px',
                  fontWeight: 700,
                  backgroundColor: 'var(--color-surface-subtle)',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  color: 'var(--color-primary-900)'
                }}>
                  {qrHomeInfo.public_home_id}
                </span>
                <span style={{ fontSize: '13px', color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Users size={14} /> {qrHomeInfo.member_count} {qrHomeInfo.member_count === 1 ? 'member' : 'members'}
                </span>
              </div>
              {qrHomeInfo.owner_name && (
                <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                  Administered by {qrHomeInfo.owner_name}
                </p>
              )}
            </div>

            {requestSubmitted ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--space-4)', textAlign: 'center' }}>
                <div style={{ padding: '12px 16px', backgroundColor: 'var(--status-in-stock-bg)', color: 'var(--status-in-stock)', borderRadius: 'var(--radius-md)', fontSize: '13px', fontWeight: 600 }}>
                  <Check size={18} style={{ display: 'inline', marginRight: '6px' }} />
                  {successMessage}
                </div>
                <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
                  Once approved by the Home Administrator, this household workspace will appear in your home switcher.
                </p>
                <Link href="/dashboard" style={{ textDecoration: 'none' }}>
                  <Button variant="secondary">Go to Dashboard</Button>
                </Link>
              </div>
            ) : (
              <form onSubmit={handleQrJoinRequest} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
                {errorMessage && (
                  <div style={{ padding: '10px 14px', backgroundColor: 'var(--status-overdue-bg)', color: 'var(--status-overdue)', borderRadius: 'var(--radius-md)', fontSize: '13px' }}>
                    {errorMessage}
                  </div>
                )}

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label htmlFor="joinMessage" style={{ fontSize: '13px', fontWeight: 600 }}>
                    Introduce yourself (Optional)
                  </label>
                  <textarea
                    id="joinMessage"
                    rows={3}
                    placeholder="e.g. Hi, I'm Alex from apartment 4B!"
                    value={joinMessage}
                    onChange={(e) => setJoinMessage(e.target.value)}
                    maxLength={300}
                    style={{
                      padding: '10px 12px',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--color-border-strong)',
                      fontSize: '13px',
                      fontFamily: 'inherit',
                      resize: 'none'
                    }}
                  />
                </div>

                <Button type="submit" isLoading={isSubmitting} style={{ width: '100%', justifyContent: 'center' }}>
                  <Send size={16} />
                  <span>Request to Join Home</span>
                </Button>

                <p style={{ fontSize: '11px', color: 'var(--color-text-tertiary)', textAlign: 'center', lineHeight: 1.4 }}>
                  Scanning a QR code requests access. Your membership will be activated upon approval by the Home Administrator.
                </p>
              </form>
            )}
          </Card>
        ) : (
          <Card style={{ padding: 'var(--space-6)' }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-5)' }}>
              <div
                style={{
                  width: '48px',
                  height: '48px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--color-primary-900)',
                  color: 'white',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                <KeyRound size={24} />
              </div>
              <h1 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                Join a Household
              </h1>
              <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
                Enter the invitation code provided by your household admin or paste your join link.
              </p>
            </div>

            {successMessage && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 14px', backgroundColor: 'var(--status-in-stock-bg)', color: 'var(--status-in-stock)', borderRadius: 'var(--radius-md)', fontSize: '13px', fontWeight: 600, marginBottom: 'var(--space-4)' }}>
                <Check size={16} />
                <span>{successMessage}</span>
              </div>
            )}

            {errorMessage && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 14px', backgroundColor: 'var(--status-overdue-bg)', color: 'var(--status-overdue)', borderRadius: 'var(--radius-md)', fontSize: '13px', fontWeight: 500, marginBottom: 'var(--space-4)' }}>
                <AlertCircle size={16} />
                <span>{errorMessage}</span>
              </div>
            )}

            <form onSubmit={handleRedeemInvitation} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
              <Input
                id="invitationCode"
                label="Invitation Code or Token"
                placeholder="e.g. INV-XXXXXX"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                required
              />

              <Button type="submit" isLoading={isSubmitting} style={{ width: '100%', justifyContent: 'center' }}>
                <span>Accept Invitation</span>
                <ArrowRight size={16} />
              </Button>
            </form>
          </Card>
        )}

        <div style={{ textAlign: 'center' }}>
          <Link href="/dashboard" style={{ fontSize: '13px', color: 'var(--color-text-secondary)', textDecoration: 'none' }}>
            &larr; Back to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function JoinHomePage() {
  return (
    <Suspense fallback={<div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Loading...</div>}>
      <JoinHomeContent />
    </Suspense>
  );
}
