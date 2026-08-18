'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Phone, ShieldCheck, ArrowRight, ArrowLeft, RefreshCw, AlertCircle, CheckCircle2, Lock } from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

function VerifyMobileForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const baseRedirect = searchParams.get('redirect') || '/dashboard';
  const actionParam = searchParams.get('action');
  const redirectTarget = actionParam
    ? `${baseRedirect}${baseRedirect.includes('?') ? '&' : '?'}action=${encodeURIComponent(actionParam)}`
    : baseRedirect;

  const [step, setStep] = useState<'input' | 'otp' | 'success'>('input');
  const [countryCode, setCountryCode] = useState('+91');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [countdown, setCountdown] = useState(0);

  const [isLoadingProfile, setIsLoadingProfile] = useState(true);
  const [isSendingOtp, setIsSendingOtp] = useState(false);
  const [isVerifyingOtp, setIsVerifyingOtp] = useState(false);
  const [demoOtp, setDemoOtp] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // 1. Fetch authenticated user profile
  useEffect(() => {
    const checkUser = async () => {
      setIsLoadingProfile(true);
      try {
        const token = apiClient.getAccessToken();
        if (!token) {
          router.replace(`/login?redirect=${encodeURIComponent('/verify-mobile')}`);
          return;
        }

        const profile = await apiClient.get<any>('/users/me');
        if (profile) {
          if (profile.mobile_verified) {
            setStep('success');
          } else if (profile.phone_number) {
            // Pre-fill existing phone number
            const num = profile.phone_number;
            if (num.startsWith('+91')) {
              setCountryCode('+91');
              setPhoneNumber(num.replace('+91', ''));
            } else if (num.startsWith('+1')) {
              setCountryCode('+1');
              setPhoneNumber(num.replace('+1', ''));
            } else if (num.startsWith('+44')) {
              setCountryCode('+44');
              setPhoneNumber(num.replace('+44', ''));
            } else if (num.startsWith('+971')) {
              setCountryCode('+971');
              setPhoneNumber(num.replace('+971', ''));
            } else {
              setPhoneNumber(num);
            }
          }
        }
      } catch (err: any) {
        console.error('Failed to load user profile:', err);
      } finally {
        setIsLoadingProfile(false);
      }
    };

    checkUser();
  }, [router]);

  // Countdown timer for OTP resend
  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setInterval(() => {
      setCountdown((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [countdown]);

  const handleSendOtp = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!phoneNumber.trim()) {
      setErrorMessage('Please enter a valid mobile number.');
      return;
    }

    setIsSendingOtp(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const fullPhone = `${countryCode}${phoneNumber.trim()}`;
      const res = await apiClient.post<{
        message: string;
        phone_number: string;
        otp_code?: string | null;
        is_demo_otp?: boolean;
      }>('/users/me/phone/send-otp', {
        phone_number: fullPhone,
        country_code: countryCode
      });

      if (res?.otp_code) {
        setDemoOtp(res.otp_code);
      } else if (res?.is_demo_otp) {
        setDemoOtp('123456');
      } else {
        setDemoOtp(null);
      }

      setSuccessMessage(`A 6-digit verification code was sent to ${fullPhone}`);
      setStep('otp');
      setCountdown(60); // 60s cooldown
    } catch (err: any) {
      setErrorMessage(err?.message || 'Failed to dispatch verification code. Please try again.');
    } finally {
      setIsSendingOtp(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!otpCode.trim() || otpCode.trim().length < 6) {
      setErrorMessage('Please enter the 6-digit verification code.');
      return;
    }

    setIsVerifyingOtp(true);
    setErrorMessage(null);

    try {
      const fullPhone = `${countryCode}${phoneNumber.trim()}`;
      await apiClient.post<any>('/users/me/phone/verify-otp', {
        phone_number: fullPhone,
        country_code: countryCode,
        otp_code: otpCode.trim()
      });

      setStep('success');
      setSuccessMessage('Mobile number verified successfully!');

      // Notify other tabs/components
      window.dispatchEvent(new Event('home-changed'));

      // Automatically redirect after short pause
      setTimeout(() => {
        router.replace(redirectTarget);
      }, 1200);
    } catch (err: any) {
      setErrorMessage(err?.message || 'Invalid or expired verification code. Please try again.');
    } finally {
      setIsVerifyingOtp(false);
    }
  };

  if (isLoadingProfile) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'var(--color-surface-base, #f8fafc)',
          padding: '24px'
        }}
      >
        <RefreshCw size={28} className="animate-spin" style={{ color: 'var(--color-primary-900, #0f172a)' }} />
      </div>
    );
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: 'var(--color-surface-base, #f8fafc)',
        color: 'var(--color-text-primary, #0f172a)',
        fontFamily: "'Plus Jakarta Sans', system-ui, -apple-system, sans-serif",
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px 16px'
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '440px',
          boxSizing: 'border-box'
        }}
      >
        {/* Card Container */}
        <div
          style={{
            backgroundColor: 'var(--color-surface-card, #ffffff)',
            border: '1px solid var(--color-border-subtle, #e2e8f0)',
            borderRadius: 'var(--radius-xl, 16px)',
            padding: '32px 24px',
            boxShadow: 'var(--shadow-elevation-medium, 0 10px 15px -3px rgba(0,0,0,0.07))'
          }}
        >
          {/* Top Brand / Verification Icon */}
          <div style={{ textAlign: 'center', marginBottom: '24px' }}>
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '56px',
                height: '56px',
                borderRadius: '16px',
                backgroundColor: 'rgba(217, 119, 6, 0.12)',
                color: '#d97706',
                marginBottom: '16px'
              }}
            >
              <Phone size={28} />
            </div>

            <h1
              style={{
                fontSize: '22px',
                fontWeight: 700,
                color: 'var(--color-text-primary, #0f172a)',
                margin: '0 0 8px 0',
                letterSpacing: '-0.02em'
              }}
            >
              Verify Mobile Number
            </h1>
            <p
              style={{
                fontSize: '14px',
                color: 'var(--color-text-secondary, #64748b)',
                margin: 0,
                lineHeight: '1.5'
              }}
            >
              {actionParam === 'create_home'
                ? 'Mobile verification is required before creating your Home workspace.'
                : 'Protect your household with verified SMS security and alerts.'}
            </p>
          </div>

          {/* Feedback Messages */}
          {errorMessage && (
            <div
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '10px',
                padding: '12px 14px',
                borderRadius: '10px',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#b91c1c',
                fontSize: '13px',
                marginBottom: '20px'
              }}
            >
              <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>{errorMessage}</div>
            </div>
          )}

          {successMessage && (
            <div
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '10px',
                padding: '12px 14px',
                borderRadius: '10px',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                color: '#047857',
                fontSize: '13px',
                marginBottom: '20px'
              }}
            >
              <CheckCircle2 size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>{successMessage}</div>
            </div>
          )}

          {/* Step 1: Input Mobile Number */}
          {step === 'input' && (
            <form onSubmit={handleSendOtp} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              <div>
                <label
                  htmlFor="verify-phone-input"
                  style={{
                    display: 'block',
                    fontSize: '13px',
                    fontWeight: 600,
                    color: 'var(--color-text-primary, #0f172a)',
                    marginBottom: '8px'
                  }}
                >
                  Mobile Number
                </label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <select
                    id="verify-country-code"
                    value={countryCode}
                    onChange={(e) => setCountryCode(e.target.value)}
                    disabled={isSendingOtp}
                    style={{
                      height: '46px',
                      backgroundColor: 'var(--color-surface-subtle, #f1f5f9)',
                      border: '1px solid var(--color-border-subtle, #cbd5e1)',
                      borderRadius: '10px',
                      padding: '0 8px',
                      fontSize: '14px',
                      fontWeight: 600,
                      color: 'var(--color-text-primary, #0f172a)',
                      outline: 'none'
                    }}
                  >
                    <option value="+91">🇮🇳 +91</option>
                    <option value="+1">🇺🇸 +1</option>
                    <option value="+44">🇬🇧 +44</option>
                    <option value="+971">🇦🇪 +971</option>
                    <option value="+61">🇦🇺 +61</option>
                    <option value="+65">🇸🇬 +65</option>
                  </select>

                  <input
                    id="verify-phone-input"
                    type="tel"
                    placeholder="9876543210"
                    required
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value)}
                    disabled={isSendingOtp}
                    style={{
                      flex: 1,
                      height: '46px',
                      backgroundColor: 'var(--color-surface-card, #ffffff)',
                      border: '1px solid var(--color-border-subtle, #cbd5e1)',
                      borderRadius: '10px',
                      padding: '0 14px',
                      fontSize: '15px',
                      color: 'var(--color-text-primary, #0f172a)',
                      outline: 'none',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>
              </div>

              <button
                type="submit"
                id="send-otp-btn"
                disabled={isSendingOtp}
                style={{
                  width: '100%',
                  height: '48px',
                  backgroundColor: '#d97706',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '10px',
                  fontSize: '14px',
                  fontWeight: 700,
                  cursor: isSendingOtp ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  marginTop: '4px',
                  opacity: isSendingOtp ? 0.75 : 1
                }}
              >
                {isSendingOtp ? (
                  <>
                    <RefreshCw size={18} className="animate-spin" /> Sending Code...
                  </>
                ) : (
                  <>
                    Send Verification Code <ArrowRight size={16} />
                  </>
                )}
              </button>
            </form>
          )}

          {/* Step 2: Enter 6-Digit OTP */}
          {step === 'otp' && (
            <form onSubmit={handleVerifyOtp} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <label
                    htmlFor="verify-otp-input"
                    style={{
                      fontSize: '13px',
                      fontWeight: 600,
                      color: 'var(--color-text-primary, #0f172a)'
                    }}
                  >
                    6-Digit Verification Code
                  </label>
                  <button
                    type="button"
                    onClick={() => {
                      setStep('input');
                      setErrorMessage(null);
                    }}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#d97706',
                      fontSize: '12px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      padding: 0
                    }}
                  >
                    Change Number
                  </button>
                </div>

                <div style={{ position: 'relative' }}>
                  <input
                    id="verify-otp-input"
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    autoComplete="one-time-code"
                    placeholder="123456"
                    required
                    value={otpCode}
                    onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                    disabled={isVerifyingOtp}
                    style={{
                      width: '100%',
                      height: '48px',
                      backgroundColor: 'var(--color-surface-card, #ffffff)',
                      border: '1px solid var(--color-border-subtle, #cbd5e1)',
                      borderRadius: '10px',
                      padding: '0 14px 0 42px',
                      fontSize: '18px',
                      fontWeight: 700,
                      letterSpacing: '0.2em',
                      color: 'var(--color-text-primary, #0f172a)',
                      outline: 'none',
                      boxSizing: 'border-box'
                    }}
                  />
                  <Lock
                    size={18}
                    style={{
                      position: 'absolute',
                      left: '14px',
                      top: '15px',
                      color: '#94a3b8',
                      pointerEvents: 'none'
                    }}
                  />
                </div>

                {demoOtp && (
                  <div
                    id="demo-otp-banner"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '8px',
                      marginTop: '10px',
                      padding: '6px 12px',
                      backgroundColor: 'rgba(217, 119, 6, 0.08)',
                      border: '1px solid rgba(217, 119, 6, 0.25)',
                      borderRadius: '8px',
                      fontSize: '12px',
                      color: 'var(--color-primary-900, #0f172a)'
                    }}
                  >
                    <span
                      style={{
                        fontSize: '10px',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        letterSpacing: '0.06em',
                        backgroundColor: 'rgba(217, 119, 6, 0.2)',
                        color: '#d97706',
                        padding: '2px 6px',
                        borderRadius: '4px'
                      }}
                    >
                      Demo Mode
                    </span>
                    <span>
                      Demo OTP: <strong style={{ letterSpacing: '0.08em', color: '#d97706' }}>{demoOtp}</strong>
                    </span>
                  </div>
                )}
              </div>

              <button
                type="submit"
                id="verify-otp-btn"
                disabled={isVerifyingOtp || otpCode.length < 6}
                style={{
                  width: '100%',
                  height: '48px',
                  backgroundColor: '#d97706',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '10px',
                  fontSize: '14px',
                  fontWeight: 700,
                  cursor: isVerifyingOtp || otpCode.length < 6 ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  opacity: isVerifyingOtp || otpCode.length < 6 ? 0.6 : 1
                }}
              >
                {isVerifyingOtp ? (
                  <>
                    <RefreshCw size={18} className="animate-spin" /> Verifying...
                  </>
                ) : (
                  'Verify & Continue'
                )}
              </button>

              <div style={{ textAlign: 'center', marginTop: '6px' }}>
                {countdown > 0 ? (
                  <span style={{ fontSize: '13px', color: '#94a3b8' }}>
                    Resend code in <strong>{countdown}s</strong>
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={() => handleSendOtp()}
                    disabled={isSendingOtp}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#d97706',
                      fontSize: '13px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      padding: '4px'
                    }}
                  >
                    Resend Verification Code
                  </button>
                )}
              </div>
            </form>
          )}

          {/* Step 3: Verified State */}
          {step === 'success' && (
            <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
              <div
                style={{
                  width: '64px',
                  height: '64px',
                  borderRadius: '50%',
                  backgroundColor: 'rgba(16, 185, 129, 0.12)',
                  color: '#059669',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                <ShieldCheck size={36} />
              </div>

              <div>
                <h2 style={{ fontSize: '18px', fontWeight: 700, margin: '0 0 6px 0', color: 'var(--color-text-primary, #0f172a)' }}>
                  Mobile Verified
                </h2>
                <p style={{ fontSize: '14px', color: 'var(--color-text-secondary, #64748b)', margin: 0 }}>
                  Your mobile number is verified. You can now create and manage Home workspaces.
                </p>
              </div>

              <Link
                href={redirectTarget}
                style={{
                  width: '100%',
                  height: '48px',
                  backgroundColor: '#d97706',
                  color: '#ffffff',
                  borderRadius: '10px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 700,
                  fontSize: '14px',
                  textDecoration: 'none',
                  marginTop: '8px'
                }}
              >
                Continue to Dashboard <ArrowRight size={16} style={{ marginLeft: '6px' }} />
              </Link>
            </div>
          )}

          {/* Back link */}
          <div
            style={{
              marginTop: '24px',
              paddingTop: '16px',
              borderTop: '1px solid var(--color-border-subtle, #e2e8f0)',
              textAlign: 'center'
            }}
          >
            <Link
              href="/dashboard"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '13px',
                color: 'var(--color-text-secondary, #64748b)',
                textDecoration: 'none'
              }}
            >
              <ArrowLeft size={14} /> Back to Household Dashboard
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function VerifyMobilePage() {
  return (
    <Suspense
      fallback={
        <div
          style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'var(--color-surface-base, #f8fafc)'
          }}
        >
          <RefreshCw size={28} className="animate-spin" style={{ color: '#d97706' }} />
        </div>
      }
    >
      <VerifyMobileForm />
    </Suspense>
  );
}
