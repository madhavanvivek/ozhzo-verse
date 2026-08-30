'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Logo } from '@/components/brand/Logo';
import {
  Home,
  Users,
  Check,
  Send,
  AlertCircle
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

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

export default function JoinHomeByTokenPage() {
  const params = useParams();
  const token = params.token as string;
  const router = useRouter();

  const [homeInfo, setHomeInfo] = useState<HomePublicInfoDTO | null>(null);
  const [joinMessage, setJoinMessage] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [requestSubmitted, setRequestSubmitted] = useState(false);

  useEffect(() => {
    if (!token) return;
    const fetchInfo = async () => {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const data = await apiClient.get<HomePublicInfoDTO>(`/homes/public/resolve-qr/${token}`);
        setHomeInfo(data);
      } catch (err: any) {
        console.error('Failed to resolve Home QR:', err);
        setErrorMessage(err?.message || 'This Home QR code has been revoked or is no longer valid.');
      } finally {
        setIsLoading(false);
      }
    };
    fetchInfo();
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;

    if (!apiClient.hasToken()) {
      router.push(`/login?redirect=/join/home/${encodeURIComponent(token)}`);
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await apiClient.post(`/homes/public/join-request/${token}`, {
        message: joinMessage.trim() || undefined
      });
      setRequestSubmitted(true);
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

        <Card style={{ padding: 'var(--space-6)', border: '1px solid var(--color-border-strong)' }}>
          {isLoading ? (
            <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--color-text-secondary)' }}>
              Verifying Home QR code...
            </div>
          ) : errorMessage && !homeInfo ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--space-4)', textAlign: 'center' }}>
              <div style={{ padding: '12px 16px', backgroundColor: 'var(--status-overdue-bg)', color: 'var(--status-overdue)', borderRadius: 'var(--radius-md)', fontSize: '13px', fontWeight: 600 }}>
                <AlertCircle size={18} style={{ display: 'inline', marginRight: '6px' }} />
                {errorMessage}
              </div>
              <Link href="/dashboard" style={{ textDecoration: 'none' }}>
                <Button variant="secondary">Go to Dashboard</Button>
              </Link>
            </div>
          ) : homeInfo ? (
            <div>
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
                  {homeInfo.home_name}
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
                    {homeInfo.public_home_id}
                  </span>
                  <span style={{ fontSize: '13px', color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Users size={14} /> {homeInfo.member_count} {homeInfo.member_count === 1 ? 'member' : 'members'}
                  </span>
                </div>
                {homeInfo.owner_name && (
                  <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                    Administered by {homeInfo.owner_name}
                  </p>
                )}
              </div>

              {requestSubmitted ? (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--space-4)', textAlign: 'center' }}>
                  <div style={{ padding: '12px 16px', backgroundColor: 'var(--status-in-stock-bg)', color: 'var(--status-in-stock)', borderRadius: 'var(--radius-md)', fontSize: '13px', fontWeight: 600 }}>
                    <Check size={18} style={{ display: 'inline', marginRight: '6px' }} />
                    Join request submitted successfully!
                  </div>
                  <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
                    The household administrator has been notified. When approved, this home will automatically be accessible in your account.
                  </p>
                  <Link href="/dashboard" style={{ textDecoration: 'none' }}>
                    <Button variant="secondary">Go to Dashboard</Button>
                  </Link>
                </div>
              ) : (
                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
                  {errorMessage && (
                    <div style={{ padding: '10px 14px', backgroundColor: 'var(--status-overdue-bg)', color: 'var(--status-overdue)', borderRadius: 'var(--radius-md)', fontSize: '13px' }}>
                      {errorMessage}
                    </div>
                  )}

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label htmlFor="tokenJoinMsg" style={{ fontSize: '13px', fontWeight: 600 }}>
                      Introduce yourself (Optional)
                    </label>
                    <textarea
                      id="tokenJoinMsg"
                      rows={3}
                      placeholder="e.g. Hi, I moved into apartment 4B!"
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
            </div>
          ) : null}
        </Card>

        <div style={{ textAlign: 'center' }}>
          <Link href="/dashboard" style={{ fontSize: '13px', color: 'var(--color-text-secondary)', textDecoration: 'none' }}>
            &larr; Back to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
