'use client';

import React, { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Shield, Lock, Mail, Eye, EyeOff, AlertCircle, ArrowLeft, RefreshCw } from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

function AdminLoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectTarget = searchParams.get('redirect') || '/admin';

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isAccessDenied, setIsAccessDenied] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMessage(null);
    setIsAccessDenied(false);

    try {
      // 1. Authenticate using the single centralized auth endpoint
      const response = await apiClient.post<any>('/auth/login', {
        email: email.trim(),
        password: password
      });

      const accessToken = response?.access_token || response?.token;
      const refreshToken = response?.refresh_token;

      if (!accessToken) {
        throw new Error('Invalid email or password.');
      }

      // Wipe previous session state before authenticating admin
      apiClient.clearSession();

      apiClient.setTokens({
        access_token: accessToken,
        refresh_token: refreshToken
      });

      // 2. Authoritative identity and platform role check
      const profile = await apiClient.get<any>('/users/me');

      const isSuper = Boolean(profile?.is_super_admin === true || profile?.system_role === 'SUPER_ADMIN');

      if (!isSuper) {
        // Clear tokens from admin scope if not authorized
        apiClient.clearTokens();
        setIsAccessDenied(true);
        setErrorMessage(
          'Platform administrator access required. Household accounts (OWNER, HOME_ADMIN, MEMBER) cannot administer the platform.'
        );
        return;
      }

      // 3. Authorized Super Admin -> redirect to Platform Console
      router.replace(redirectTarget);
    } catch (err: any) {
      const msg = err?.message || '';
      if (
        msg.includes('401') ||
        msg.includes('Invalid') ||
        msg.includes('credentials') ||
        msg.includes('password') ||
        msg.includes('Unauthorized') ||
        msg.includes('not found')
      ) {
        setErrorMessage('Invalid email or password.');
      } else if (msg.includes('429') || msg.includes('rate limit')) {
        setErrorMessage('Too many sign-in attempts. Please try again in a few moments.');
      } else {
        setErrorMessage(msg || 'An error occurred during authentication. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: '#0b1120',
        color: '#f8fafc',
        fontFamily: "'Plus Jakarta Sans', system-ui, -apple-system, sans-serif",
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px 16px'
      }}
    >
      {/* Background radial glow */}
      <div
        style={{
          position: 'fixed',
          top: '20%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '500px',
          height: '500px',
          background: 'radial-gradient(circle, rgba(245, 158, 11, 0.08) 0%, rgba(15, 23, 42, 0) 70%)',
          pointerEvents: 'none',
          zIndex: 0
        }}
      />

      <div
        style={{
          width: '100%',
          maxWidth: '440px',
          position: 'relative',
          zIndex: 1
        }}
      >
        {/* Brand Header */}
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '54px',
              height: '54px',
              borderRadius: '14px',
              backgroundColor: 'rgba(245, 158, 11, 0.12)',
              border: '1px solid rgba(245, 158, 11, 0.3)',
              color: '#f59e0b',
              marginBottom: '16px',
              boxShadow: '0 4px 16px rgba(245, 158, 11, 0.15)'
            }}
          >
            <Shield size={28} />
          </div>

          <div
            style={{
              display: 'inline-block',
              padding: '4px 12px',
              backgroundColor: 'rgba(245, 158, 11, 0.15)',
              border: '1px solid rgba(245, 158, 11, 0.35)',
              borderRadius: '9999px',
              fontSize: '11px',
              fontWeight: 700,
              letterSpacing: '0.08em',
              color: '#f59e0b',
              textTransform: 'uppercase',
              marginBottom: '10px'
            }}
          >
            Platform Operations Console
          </div>

          <h1
            style={{
              fontSize: '24px',
              fontWeight: 700,
              letterSpacing: '-0.02em',
              color: '#ffffff',
              margin: '0 0 6px 0'
            }}
          >
            Platform Administration
          </h1>
          <p
            style={{
              fontSize: '14px',
              color: '#94a3b8',
              margin: 0
            }}
          >
            Sign in to manage the Ozhzo platform
          </p>
        </div>

        {/* Login Card */}
        <div
          style={{
            backgroundColor: '#0f172a',
            border: '1px solid #1e293b',
            borderRadius: '16px',
            padding: '32px 28px',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5)'
          }}
        >
          {errorMessage && (
            <div
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px',
                padding: '14px 16px',
                borderRadius: '10px',
                backgroundColor: isAccessDenied ? 'rgba(239, 68, 68, 0.15)' : 'rgba(239, 68, 68, 0.12)',
                border: '1px solid rgba(239, 68, 68, 0.35)',
                color: '#fca5a5',
                fontSize: '13px',
                lineHeight: '1.5',
                marginBottom: '20px'
              }}
            >
              <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '2px', color: '#ef4444' }} />
              <div>
                <div style={{ fontWeight: 600, color: '#f87171', marginBottom: '2px' }}>
                  {isAccessDenied ? 'Access Restricted' : 'Authentication Failed'}
                </div>
                <div>{errorMessage}</div>
                {isAccessDenied && (
                  <div style={{ marginTop: '10px' }}>
                    <Link
                      href="/login"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        fontSize: '12px',
                        fontWeight: 600,
                        color: '#f59e0b',
                        textDecoration: 'none'
                      }}
                    >
                      <ArrowLeft size={14} /> Return to Household Login
                    </Link>
                  </div>
                )}
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Email Field */}
            <div>
              <label
                htmlFor="admin-login-email"
                style={{
                  display: 'block',
                  fontSize: '13px',
                  fontWeight: 600,
                  color: '#cbd5e1',
                  marginBottom: '8px'
                }}
              >
                Administrator Email
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  id="admin-login-email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  placeholder="admin@ozhzo.com"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  disabled={isLoading}
                  style={{
                    width: '100%',
                    height: '46px',
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '10px',
                    padding: '0 14px 0 42px',
                    fontSize: '14px',
                    color: '#f8fafc',
                    outline: 'none',
                    boxSizing: 'border-box',
                    transition: 'border-color 0.15s ease'
                  }}
                />
                <Mail
                  size={18}
                  style={{
                    position: 'absolute',
                    left: '14px',
                    top: '14px',
                    color: '#64748b',
                    pointerEvents: 'none'
                  }}
                />
              </div>
            </div>

            {/* Password Field */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <label
                  htmlFor="admin-login-password"
                  style={{
                    fontSize: '13px',
                    fontWeight: 600,
                    color: '#cbd5e1'
                  }}
                >
                  Password
                </label>
              </div>
              <div style={{ position: 'relative' }}>
                <input
                  id="admin-login-password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  disabled={isLoading}
                  style={{
                    width: '100%',
                    height: '46px',
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '10px',
                    padding: '0 42px 0 42px',
                    fontSize: '14px',
                    color: '#f8fafc',
                    outline: 'none',
                    boxSizing: 'border-box',
                    transition: 'border-color 0.15s ease'
                  }}
                />
                <Lock
                  size={18}
                  style={{
                    position: 'absolute',
                    left: '14px',
                    top: '14px',
                    color: '#64748b',
                    pointerEvents: 'none'
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  tabIndex={-1}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  style={{
                    position: 'absolute',
                    right: '12px',
                    top: '12px',
                    background: 'none',
                    border: 'none',
                    color: '#94a3b8',
                    cursor: 'pointer',
                    padding: '2px',
                    display: 'flex',
                    alignItems: 'center'
                  }}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              id="admin-submit-btn"
              disabled={isLoading}
              style={{
                width: '100%',
                height: '48px',
                backgroundColor: '#f59e0b',
                color: '#0f172a',
                border: 'none',
                borderRadius: '10px',
                fontSize: '14px',
                fontWeight: 700,
                cursor: isLoading ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                marginTop: '6px',
                transition: 'background-color 0.15s ease',
                opacity: isLoading ? 0.75 : 1
              }}
            >
              {isLoading ? (
                <>
                  <RefreshCw size={18} className="animate-spin" />
                  Verifying Platform Privileges...
                </>
              ) : (
                'Sign in to Platform'
              )}
            </button>
          </form>

          {/* Security footnote */}
          <div
            style={{
              marginTop: '24px',
              paddingTop: '20px',
              borderTop: '1px solid #1e293b',
              textAlign: 'center'
            }}
          >
            <Link
              href="/login"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '13px',
                fontWeight: 500,
                color: '#94a3b8',
                textDecoration: 'none',
                transition: 'color 0.15s ease'
              }}
            >
              <ArrowLeft size={14} /> Return to Household Login
            </Link>
          </div>
        </div>

        {/* Platform Notice */}
        <div
          style={{
            marginTop: '24px',
            textAlign: 'center',
            fontSize: '12px',
            color: '#64748b',
            lineHeight: '1.5'
          }}
        >
          Protected System. Unauthorized access attempts are logged and reported.
        </div>
      </div>
    </div>
  );
}

export default function AdminLoginPage() {
  return (
    <Suspense
      fallback={
        <div
          style={{
            minHeight: '100vh',
            backgroundColor: '#0b1120',
            color: '#f8fafc',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
        >
          <RefreshCw size={28} className="animate-spin" style={{ color: '#f59e0b' }} />
        </div>
      }
    >
      <AdminLoginForm />
    </Suspense>
  );
}
