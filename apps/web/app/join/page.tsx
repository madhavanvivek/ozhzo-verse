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
  ShieldCheck,
  HelpCircle
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

interface AcceptInvitationResponse {
  home_id: string;
  home_name: string;
  role: string;
  message: string;
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

function JoinHomeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [code, setCode] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [joinedHome, setJoinedHome] = useState<{ id: string; name: string; role: string } | null>(null);

  useEffect(() => {
    const codeParam = searchParams.get('code') || searchParams.get('token');
    if (codeParam) {
      setCode(codeParam.trim());
    }
  }, [searchParams]);

  const handleJoin = async (e: React.FormEvent) => {
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
        setJoinedHome({
          id: res.home_id,
          name: res.home_name,
          role: res.role
        });
      }

      setSuccessMessage(res?.message || `Welcome to ${res.home_name}!`);
      setTimeout(() => {
        router.push('/dashboard');
      }, 1500);
    } catch (err: any) {
      console.error('Join home failed:', err);
      setErrorMessage(formatErrorMessage(err));
      setIsSubmitting(false);
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
          maxWidth: '460px',
          width: '100%',
          padding: '32px',
          boxShadow: 'var(--shadow-floating, 0 10px 25px -5px rgba(0, 0, 0, 0.1))',
          borderRadius: 'var(--radius-lg, 16px)',
          border: '1px solid var(--color-border-subtle, #e2e8f0)'
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div
            style={{
              width: '60px',
              height: '60px',
              borderRadius: '50%',
              backgroundColor: 'var(--color-primary-900, #0f172a)',
              color: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 14px'
            }}
          >
            <KeyRound size={28} />
          </div>
          <h1 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
            Join a Home Workspace
          </h1>
          <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '4px', lineHeight: 1.4 }}>
            Enter your invitation code to connect with your household and access inventory, chores, and bills.
          </p>
        </div>

        {successMessage ? (
          <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', gap: '16px', padding: '12px 0' }}>
            <div
              style={{
                width: '56px',
                height: '56px',
                borderRadius: '50%',
                backgroundColor: 'var(--status-in-stock-bg, #ecfdf5)',
                color: 'var(--status-in-stock, #10b981)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto'
              }}
            >
              <Check size={28} />
            </div>
            <div>
              <h2 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                {joinedHome?.name || 'Workspace Joined'}
              </h2>
              <p style={{ fontSize: '14px', color: 'var(--status-in-stock)', fontWeight: 600, marginTop: '4px' }}>
                {successMessage}
              </p>
            </div>
            <Link href="/dashboard" style={{ textDecoration: 'none' }}>
              <Button style={{ width: '100%', minHeight: '44px' }}>
                <span>Open Household Dashboard</span>
                <ArrowRight size={16} />
              </Button>
            </Link>
          </div>
        ) : (
          <form onSubmit={handleJoin} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {errorMessage && (
              <div
                style={{
                  padding: '12px 14px',
                  backgroundColor: 'var(--status-overdue-bg, #fef2f2)',
                  color: 'var(--status-overdue, #ef4444)',
                  borderRadius: 'var(--radius-md, 10px)',
                  fontSize: '13px',
                  fontWeight: 500,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
              >
                <AlertCircle size={16} style={{ flexShrink: 0 }} />
                <span>{errorMessage}</span>
              </div>
            )}

            <div>
              <label
                htmlFor="invitationCode"
                style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text-primary)', display: 'block', marginBottom: '6px' }}
              >
                Invitation Code
              </label>
              <Input
                id="invitationCode"
                type="text"
                placeholder="e.g. OZ-7K4P92"
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                autoFocus
                style={{
                  fontSize: '16px',
                  fontWeight: 600,
                  letterSpacing: '1px',
                  textTransform: 'uppercase'
                }}
              />
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: 'var(--color-text-tertiary)', marginTop: '6px' }}>
                <HelpCircle size={13} />
                <span>Ask your Home Admin for the code if your link is not opening.</span>
              </div>
            </div>

            <Button
              type="submit"
              isLoading={isSubmitting}
              style={{ width: '100%', minHeight: '46px', fontSize: '15px', fontWeight: 600 }}
            >
              <ShieldCheck size={18} />
              <span>Join Home</span>
            </Button>

            <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '8px' }}>
              <Link href="/dashboard" style={{ color: 'var(--color-text-secondary)', textDecoration: 'none' }}>
                Cancel & Return
              </Link>
            </div>
          </form>
        )}
      </Card>
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
