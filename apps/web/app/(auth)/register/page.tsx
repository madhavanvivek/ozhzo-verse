'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Logo } from '@/components/brand/Logo';
import { apiClient } from '@/lib/apiClient';

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState('');
  const [countryCode, setCountryCode] = useState('+91');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const fullPhone = phoneNumber.trim() ? `${countryCode}${phoneNumber.trim()}` : null;
      const res = await apiClient.post<{ access_token: string; refresh_token?: string | null }>('/auth/register', {
        full_name: fullName,
        phone_number: fullPhone,
        country_code: countryCode,
        email: email.trim() || null,
        password
      });

      if (!res?.access_token) {
        throw new Error('Registration succeeded but no access token was returned.');
      }

      apiClient.setTokens({
        access_token: res.access_token,
        refresh_token: res.refresh_token
      });

      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Failed to register');
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
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--color-primary-900)' }}>Create an Account</h1>
          <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)' }}>Get started with Ozhzo Verse</p>
        </div>

        {error && (
          <div style={{ padding: '10px 12px', backgroundColor: 'var(--status-overdue-bg)', color: 'var(--status-overdue)', borderRadius: 'var(--radius-md)', fontSize: '13px', marginBottom: 'var(--space-4)', fontWeight: 500 }}>
            {error}
          </div>
        )}

        <form onSubmit={handleRegister} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <Input
            id="fullName"
            type="text"
            label="Full Name"
            placeholder="Enter your full name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
          />

          <div>
            <label htmlFor="phoneNumber" style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '6px', color: 'var(--color-text-primary)' }}>
              Mobile Number (Optional)
            </label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <select
                aria-label="Country Code"
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
                id="phoneNumber"
                type="tel"
                placeholder="9876543210"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
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

          <Input
            id="email"
            type="email"
            label="Email Address"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <Input
            id="password"
            type="password"
            label="Password (min 8 chars)"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <Button type="submit" size="lg" isLoading={isLoading} style={{ width: '100%', marginTop: 'var(--space-2)' }}>
            Get Started
          </Button>
        </form>

        <div style={{ marginTop: 'var(--space-6)', textAlign: 'center', fontSize: '13px', color: 'var(--color-text-secondary)' }}>
          Already have an account?{' '}
          <Link href="/login" style={{ fontWeight: 600, color: 'var(--color-primary-900)' }}>
            Sign in
          </Link>
        </div>
      </Card>
    </div>
  );
}
