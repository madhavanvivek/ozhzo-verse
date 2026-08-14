'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Logo } from '@/components/brand/Logo';

export default function LoginPage() {
  const router = useRouter();
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
        ? { phone_number: `${countryCode}${phoneNumber.trim()}`, password }
        : { email: email.trim(), password };

      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!data.success) {
        throw new Error(data.error?.message || data.detail || 'Login failed');
      }
      localStorage.setItem('access_token', data.data.access_token);
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Failed to sign in');
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
          <div style={{ padding: '10px 12px', backgroundColor: 'var(--status-overdue-bg)', color: 'var(--status-overdue)', borderRadius: 'var(--radius-md)', fontSize: '13px', marginBottom: 'var(--space-4)', fontWeight: 500 }}>
            {error}
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

          <Button type="submit" size="lg" isLoading={isLoading} style={{ width: '100%', marginTop: 'var(--space-2)' }}>
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
