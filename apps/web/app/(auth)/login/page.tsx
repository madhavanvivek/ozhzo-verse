'use client';

import React, { useState, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Logo } from '@/components/brand/Logo';
import { apiClient } from '@/lib/apiClient';

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectUrl = searchParams.get('redirect') || '/dashboard';

  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanIdentifier = identifier.trim();
    const cleanPassword = password.trim();

    if (!cleanIdentifier || !cleanPassword) {
      setError('Please enter your email or mobile number and password.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const payload = {
        login_identifier: cleanIdentifier,
        password: cleanPassword
      };

      const res = await apiClient.post<{ access_token: string; refresh_token?: string | null }>('/auth/login', payload);

      if (!res?.access_token) {
        throw new Error('Login succeeded but no access token was returned.');
      }

      // Wipe previous session state before authenticating new user
      apiClient.clearSession();

      apiClient.setTokens({
        access_token: res.access_token,
        refresh_token: res.refresh_token
      });

      router.push(redirectUrl);
    } catch (err: any) {
      const msg = err?.message || err?.detail || '';
      if (typeof msg === 'string' && (msg.includes('Platform administrator') || msg.includes('/admin/login'))) {
        setError('Platform administrator accounts must sign in through the Administrator Console at /admin/login.');
      } else if (typeof msg === 'string' && msg.includes('verify your mobile number')) {
        setError('Please verify your mobile number before continuing.');
      } else if (
        typeof msg === 'string' &&
        (msg.includes('401') ||
          msg.includes('Invalid') ||
          msg.includes('credentials') ||
          msg.includes('password') ||
          msg.includes('Unauthorized') ||
          msg.includes('not found'))
      ) {
        setError('Invalid email/mobile number or password.');
      } else if (typeof msg === 'string' && (msg.includes('429') || msg.includes('rate limit') || msg.includes('Too many'))) {
        setError('Too many sign-in attempts. Please try again in a few moments.');
      } else {
        setError(typeof msg === 'string' ? msg : 'Failed to sign in. Please check your credentials and try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 'var(--space-4)' }}>
      <div style={{ marginBottom: 'var(--space-6)', textAlign: 'center' }}>
        <Logo variant="mark" width={48} height={48} />
      </div>

      <Card style={{ width: '100%', maxWidth: '420px', padding: 'var(--space-8)' }}>
        <div style={{ marginBottom: 'var(--space-6)', textAlign: 'center' }}>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--color-primary-900)' }}>Welcome Back</h1>
          <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
            Sign in to your Ozhzo Verse home
          </p>
        </div>

        {error && (
          <div
            id="login-error-alert"
            style={{
              padding: '12px 14px',
              backgroundColor: 'var(--status-overdue-bg, #fee2e2)',
              color: 'var(--status-overdue, #dc2626)',
              borderRadius: 'var(--radius-md)',
              fontSize: '13px',
              marginBottom: 'var(--space-4)',
              fontWeight: 500,
              border: '1px solid #fca5a5'
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: '2px', color: '#b91c1c' }}>Authentication Failed</div>
            <div>{error}</div>
          </div>
        )}

        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <div>
            <label htmlFor="login-identifier" style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '6px', color: 'var(--color-text-primary)' }}>
              Email or Mobile Number
            </label>
            <Input
              id="login-identifier"
              type="text"
              name="identifier"
              autoComplete="username"
              placeholder="e.g. name@example.com or +91 98765 43210"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              required
              style={{ width: '100%' }}
            />
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <label htmlFor="login-password" style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                Password
              </label>
            </div>
            <Input
              id="login-password"
              type="password"
              name="password"
              autoComplete="current-password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={{ width: '100%' }}
            />
          </div>

          <Button
            id="login-submit-btn"
            type="submit"
            isLoading={isLoading}
            style={{ width: '100%', marginTop: 'var(--space-2)' }}
          >
            Sign In
          </Button>
        </form>

        <div style={{ marginTop: 'var(--space-6)', textAlign: 'center', fontSize: '13px', color: 'var(--color-text-secondary)' }}>
          Don&apos;t have an account?{' '}
          <Link
            href={`/register${redirectUrl !== '/dashboard' ? `?redirect=${encodeURIComponent(redirectUrl)}` : ''}`}
            style={{ color: 'var(--color-primary-900)', fontWeight: 600, textDecoration: 'none' }}
          >
            Create one
          </Link>
        </div>

        <div style={{ marginTop: 'var(--space-4)', paddingTop: 'var(--space-4)', borderTop: '1px solid var(--color-border-subtle)', textAlign: 'center', fontSize: '12px', color: 'var(--color-text-tertiary)' }}>
          Have a Home Invitation Code?{' '}
          <Link href="/join" style={{ color: 'var(--color-primary-900)', fontWeight: 600, textDecoration: 'none' }}>
            Join with Code
          </Link>
        </div>
      </Card>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Loading...</div>}>
      <LoginForm />
    </Suspense>
  );
}
