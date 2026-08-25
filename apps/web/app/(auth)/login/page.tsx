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

  const [authMode, setAuthMode] = useState<'phone' | 'email'>('phone');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [countryCode, setCountryCode] = useState('+91');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const payload = authMode === 'phone'
        ? { phone_number: `${countryCode}${phoneNumber.trim()}`, password: password.trim() }
        : { email: email.trim().toLowerCase(), password: password.trim() };

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
      const msg = err?.message || '';
      if (msg.includes('Platform administrator') || msg.includes('/admin/login')) {
        setError('Platform administrator accounts must sign in through the Administrator Console at /admin/login.');
      } else if (
        msg.includes('401') ||
        msg.includes('Invalid') ||
        msg.includes('credentials') ||
        msg.includes('password') ||
        msg.includes('Unauthorized') ||
        msg.includes('not found')
      ) {
        setError('Invalid email or password.');
      } else if (msg.includes('429') || msg.includes('rate limit')) {
        setError('Too many sign-in attempts. Please try again in a few moments.');
      } else {
        setError(msg || 'Failed to sign in. Please check your credentials and try again.');
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
          <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)' }}>Sign in to your Ozhzo Verse home</p>
        </div>

        {/* Tab Toggle */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: 'var(--space-4)', backgroundColor: 'var(--color-surface-subtle)', padding: '4px', borderRadius: 'var(--radius-md)' }}>
          <button
            id="phone-tab-btn"
            type="button"
            onClick={() => setAuthMode('phone')}
            style={{
              flex: 1,
              padding: '6px 12px',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              backgroundColor: authMode === 'phone' ? 'white' : 'transparent',
              color: authMode === 'phone' ? 'var(--color-primary-900)' : 'var(--color-text-secondary)',
              boxShadow: authMode === 'phone' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none'
            }}
          >
            Mobile Number
          </button>
          <button
            id="email-tab-btn"
            type="button"
            onClick={() => setAuthMode('email')}
            style={{
              flex: 1,
              padding: '6px 12px',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              backgroundColor: authMode === 'email' ? 'white' : 'transparent',
              color: authMode === 'email' ? 'var(--color-primary-900)' : 'var(--color-text-secondary)',
              boxShadow: authMode === 'email' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none'
            }}
          >
            Email
          </button>
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
          {authMode === 'phone' ? (
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '6px', color: 'var(--color-text-primary)' }}>
                Mobile Number
              </label>
              <div style={{ display: 'flex', gap: '8px' }}>
                <select
                  value={countryCode}
                  onChange={(e) => setCountryCode(e.target.value)}
                  style={{
                    padding: '8px 10px',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--color-border-subtle)',
                    fontSize: '14px',
                    backgroundColor: 'white'
                  }}
                >
                  <option value="+91">🇮🇳 +91</option>
                  <option value="+1">🇺🇸 +1</option>
                  <option value="+44">🇬🇧 +44</option>
                  <option value="+971">🇦🇪 +971</option>
                </select>
                <input
                  type="tel"
                  placeholder="9876543210"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  required
                  style={{
                    flex: 1,
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--color-border-subtle)',
                    fontSize: '14px'
                  }}
                />
              </div>
            </div>
          ) : (
            <Input
              id="email"
              type="email"
              label="Email Address"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          )}

          <Input
            id="password"
            type="password"
            label="Password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <Button id="login-submit-btn" type="submit" size="lg" isLoading={isLoading} style={{ width: '100%', marginTop: 'var(--space-2)' }}>
            Sign In
          </Button>
        </form>

        <div style={{ marginTop: 'var(--space-6)', textAlign: 'center', fontSize: '13px', color: 'var(--color-text-secondary)' }}>
          Don't have an account?{' '}
          <Link href="/register" style={{ fontWeight: 600, color: 'var(--color-primary-900)' }}>
            Create one
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
