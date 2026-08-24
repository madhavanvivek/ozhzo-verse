'use client';

import React, { useState, useEffect } from 'react';
import {
  Shield,
  KeyRound,
  Mail,
  Lock,
  Eye,
  EyeOff,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  X,
  Check
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

export default function AdminSettingsPage() {
  const [profile, setProfile] = useState<any>(null);
  const [isLoadingProfile, setIsLoadingProfile] = useState(true);

  // Modal / Flow state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [step, setStep] = useState<'OTP_INPUT' | 'NEW_PASSWORD' | 'SUCCESS'>('OTP_INPUT');
  
  // OTP state
  const [otpCode, setOtpCode] = useState('');
  const [verificationTicket, setVerificationTicket] = useState<string | null>(null);
  const [isSendingOtp, setIsSendingOtp] = useState(false);
  const [isVerifyingOtp, setIsVerifyingOtp] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [maskedEmail, setMaskedEmail] = useState('');

  // Password state
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmittingPassword, setIsSubmittingPassword] = useState(false);

  // General feedback
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Load Super Admin profile
  const fetchProfile = async () => {
    try {
      setIsLoadingProfile(true);
      const data = await apiClient.get<any>('/users/me');
      setProfile(data);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load profile details.');
    } finally {
      setIsLoadingProfile(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  // Cooldown countdown timer
  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setInterval(() => {
      setCooldown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [cooldown]);

  // Step 1: Open modal and send email OTP
  const handleStartChangePassword = async () => {
    setErrorMsg(null);
    setSuccessMsg(null);
    setOtpCode('');
    setNewPassword('');
    setConfirmPassword('');
    setIsModalOpen(true);
    setStep('OTP_INPUT');
    await handleSendOtp();
  };

  const handleSendOtp = async () => {
    setIsSendingOtp(true);
    setErrorMsg(null);
    try {
      const res = await apiClient.post<{
        message: string;
        email: string;
        cooldown_seconds: number;
        otp_code?: string;
      }>('/admin/security/send-email-otp');
      setMaskedEmail(res.email || profile?.email || 'your email');
      setCooldown(res.cooldown_seconds || 60);
      
      // If dev OTP is returned, auto-populate for development convenience
      if (res.otp_code) {
        setOtpCode(res.otp_code);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to send verification code. Please try again.');
    } finally {
      setIsSendingOtp(false);
    }
  };

  // Step 2: Verify email OTP
  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!otpCode.trim()) return;

    setIsVerifyingOtp(true);
    setErrorMsg(null);
    try {
      const res = await apiClient.post<{
        message: string;
        verification_ticket: string;
        expires_in_seconds: number;
      }>('/admin/security/verify-email-otp', {
        otp_code: otpCode.trim()
      });

      if (!res.verification_ticket) {
        throw new Error('Verification ticket not received.');
      }

      setVerificationTicket(res.verification_ticket);
      setStep('NEW_PASSWORD');
    } catch (err: any) {
      setErrorMsg(err.message || 'Invalid or expired verification code.');
    } finally {
      setIsVerifyingOtp(false);
    }
  };

  // Password validation checks
  const hasMinLength = newPassword.length >= 8;
  const hasUpper = /[A-Z]/.test(newPassword);
  const hasLower = /[a-z]/.test(newPassword);
  const hasNumber = /\d/.test(newPassword);
  const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(newPassword);
  const passwordsMatch = newPassword.length > 0 && newPassword === confirmPassword;
  const isPasswordValid = hasMinLength && hasUpper && hasLower && hasNumber && hasSpecial && passwordsMatch;

  // Step 3: Submit New Password
  const handleSubmitPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!verificationTicket || !isPasswordValid) return;

    setIsSubmittingPassword(true);
    setErrorMsg(null);
    try {
      const res = await apiClient.post<{
        message: string;
        access_token: string;
        refresh_token: string;
      }>('/admin/security/change-password', {
        verification_ticket: verificationTicket,
        new_password: newPassword,
        confirm_password: confirmPassword
      });

      // Update tokens in apiClient
      if (res.access_token) {
        apiClient.setTokens({
          access_token: res.access_token,
          refresh_token: res.refresh_token
        });
      }

      setStep('SUCCESS');
      setSuccessMsg('Password updated successfully. All other active sessions have been revoked.');
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to update password. Please try again.');
    } finally {
      setIsSubmittingPassword(false);
    }
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setOtpCode('');
    setNewPassword('');
    setConfirmPassword('');
    setVerificationTicket(null);
    setErrorMsg(null);
  };

  return (
    <div style={{ padding: '8px 0 32px 0', maxWidth: '900px' }}>
      {/* Page Header */}
      <div style={{ marginBottom: '28px' }}>
        <h1
          style={{
            fontSize: '24px',
            fontWeight: 700,
            color: '#ffffff',
            margin: '0 0 8px 0',
            letterSpacing: '-0.02em',
            display: 'flex',
            alignItems: 'center',
            gap: '10px'
          }}
        >
          <Shield size={26} color="#f59e0b" />
          Platform Security & Settings
        </h1>
        <p style={{ fontSize: '14px', color: '#94a3b8', margin: 0 }}>
          Manage Super Administrator account credentials and security preferences
        </p>
      </div>

      {/* Success Notification Banner */}
      {successMsg && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: '14px 18px',
            backgroundColor: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid rgba(16, 185, 129, 0.35)',
            borderRadius: '12px',
            color: '#6ee7b7',
            fontSize: '13px',
            fontWeight: 500,
            marginBottom: '20px'
          }}
        >
          <CheckCircle2 size={18} style={{ color: '#10b981', flexShrink: 0 }} />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Main Account Card */}
      <div
        style={{
          backgroundColor: '#0f172a',
          border: '1px solid #1e293b',
          borderRadius: '16px',
          padding: '28px',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.3)',
          marginBottom: '24px'
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid #1e293b',
            paddingBottom: '20px',
            marginBottom: '24px'
          }}
        >
          <div>
            <h2 style={{ fontSize: '17px', fontWeight: 600, color: '#ffffff', margin: '0 0 4px 0' }}>
              Super Administrator Account
            </h2>
            <p style={{ fontSize: '13px', color: '#94a3b8', margin: 0 }}>
              Primary identity used for both platform administration and household spaces
            </p>
          </div>

          <span
            style={{
              padding: '4px 10px',
              backgroundColor: 'rgba(245, 158, 11, 0.15)',
              border: '1px solid rgba(245, 158, 11, 0.35)',
              borderRadius: '9999px',
              fontSize: '11px',
              fontWeight: 700,
              color: '#f59e0b',
              textTransform: 'uppercase',
              letterSpacing: '0.05em'
            }}
          >
            {profile?.system_role || 'SUPER_ADMIN'}
          </span>
        </div>

        {isLoadingProfile ? (
          <div style={{ padding: '32px', textAlign: 'center', color: '#94a3b8' }}>
            <RefreshCw size={24} className="animate-spin" style={{ margin: '0 auto 12px auto' }} />
            <div>Loading administrator details...</div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Email field */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '16px',
                backgroundColor: '#1e293b',
                borderRadius: '10px',
                border: '1px solid #334155'
              }}
            >
              <div>
                <div style={{ fontSize: '12px', fontWeight: 600, color: '#94a3b8', marginBottom: '4px' }}>
                  Account
                </div>
                <div style={{ fontSize: '15px', fontWeight: 600, color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Mail size={16} color="#94a3b8" />
                  <span id="super-admin-email">{profile?.email || 'vivek@zinfog.com'}</span>
                </div>
              </div>
              <span style={{ fontSize: '12px', color: '#10b981', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
                <CheckCircle2 size={14} /> Verified
              </span>
            </div>

            {/* Password field */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '16px',
                backgroundColor: '#1e293b',
                borderRadius: '10px',
                border: '1px solid #334155'
              }}
            >
              <div>
                <div style={{ fontSize: '12px', fontWeight: 600, color: '#94a3b8', marginBottom: '4px' }}>
                  Password
                </div>
                <div style={{ fontSize: '15px', fontWeight: 600, color: '#94a3b8', letterSpacing: '0.2em' }}>
                  ••••••••••••
                </div>
              </div>

              <button
                id="change-password-btn"
                type="button"
                onClick={handleStartChangePassword}
                style={{
                  padding: '10px 18px',
                  backgroundColor: '#f59e0b',
                  color: '#0f172a',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '13px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  transition: 'background-color 0.15s ease'
                }}
              >
                <KeyRound size={15} />
                Change Password
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Security Architecture Guidelines Card */}
      <div
        style={{
          backgroundColor: '#0f172a',
          border: '1px solid #1e293b',
          borderRadius: '16px',
          padding: '24px',
          color: '#94a3b8',
          fontSize: '13px',
          lineHeight: 1.6
        }}
      >
        <div style={{ fontSize: '14px', fontWeight: 600, color: '#f8fafc', marginBottom: '8px' }}>
          Platform Security Architecture Note
        </div>
        <div>
          The Ozhzo Verse platform utilizes a unified identity framework. The password changed here applies universally to both the <strong>Platform Operations Console</strong> (<code>/admin</code>) and your <strong>Household Workspaces</strong> (<code>/dashboard</code>). Existing refresh sessions are automatically revoked on credential update.
        </div>
      </div>

      {/* Change Password Modal */}
      {isModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(4px)',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px'
          }}
        >
          <div
            style={{
              backgroundColor: '#0f172a',
              border: '1px solid #1e293b',
              borderRadius: '16px',
              maxWidth: '480px',
              width: '100%',
              padding: '28px',
              boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)',
              position: 'relative'
            }}
          >
            {/* Close button */}
            <button
              type="button"
              onClick={handleCloseModal}
              style={{
                position: 'absolute',
                top: '16px',
                right: '16px',
                background: 'none',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                padding: '4px'
              }}
              aria-label="Close"
            >
              <X size={20} />
            </button>

            {/* Error Banner */}
            {errorMsg && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '10px',
                  padding: '12px 14px',
                  backgroundColor: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid rgba(239, 68, 68, 0.35)',
                  borderRadius: '8px',
                  color: '#fca5a5',
                  fontSize: '13px',
                  marginBottom: '20px'
                }}
              >
                <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '2px', color: '#ef4444' }} />
                <div>{errorMsg}</div>
              </div>
            )}

            {/* STEP 1: OTP Input */}
            {step === 'OTP_INPUT' && (
              <div>
                <div style={{ textAlign: 'center', marginBottom: '20px' }}>
                  <div
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: '48px',
                      height: '48px',
                      borderRadius: '12px',
                      backgroundColor: 'rgba(245, 158, 11, 0.12)',
                      border: '1px solid rgba(245, 158, 11, 0.3)',
                      color: '#f59e0b',
                      marginBottom: '12px'
                    }}
                  >
                    <Mail size={24} />
                  </div>
                  <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#ffffff', margin: '0 0 6px 0' }}>
                    Verify your email
                  </h3>
                  <p style={{ fontSize: '13px', color: '#94a3b8', margin: 0, lineHeight: 1.5 }}>
                    Verify your email to change your password. We&apos;ve dispatched a 6-digit one-time code to <strong>{maskedEmail || profile?.email}</strong>.
                  </p>
                </div>

                <form onSubmit={handleVerifyOtp} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div>
                    <label
                      htmlFor="email-otp-input"
                      style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#cbd5e1', marginBottom: '6px' }}
                    >
                      Email verification code
                    </label>
                    <input
                      id="email-otp-input"
                      type="text"
                      inputMode="numeric"
                      pattern="[0-9]*"
                      maxLength={10}
                      autoFocus
                      required
                      placeholder="123456"
                      value={otpCode}
                      onChange={(e) => setOtpCode(e.target.value)}
                      disabled={isVerifyingOtp || isSendingOtp}
                      style={{
                        width: '100%',
                        height: '48px',
                        backgroundColor: '#1e293b',
                        border: '1px solid #334155',
                        borderRadius: '10px',
                        padding: '0 16px',
                        fontSize: '18px',
                        fontWeight: 600,
                        letterSpacing: '0.25em',
                        textAlign: 'center',
                        color: '#f8fafc',
                        outline: 'none',
                        boxSizing: 'border-box'
                      }}
                    />
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <button
                      type="button"
                      onClick={handleSendOtp}
                      disabled={cooldown > 0 || isSendingOtp}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: cooldown > 0 ? '#64748b' : '#f59e0b',
                        fontSize: '12px',
                        fontWeight: 600,
                        cursor: cooldown > 0 ? 'not-allowed' : 'pointer',
                        padding: 0
                      }}
                    >
                      {cooldown > 0 ? `Resend code in ${cooldown}s` : 'Resend verification code'}
                    </button>
                    <span style={{ fontSize: '12px', color: '#64748b' }}>Expires in 10 mins</span>
                  </div>

                  <button
                    id="verify-otp-btn"
                    type="submit"
                    disabled={isVerifyingOtp || !otpCode.trim()}
                    style={{
                      width: '100%',
                      height: '46px',
                      backgroundColor: '#f59e0b',
                      color: '#0f172a',
                      border: 'none',
                      borderRadius: '10px',
                      fontSize: '14px',
                      fontWeight: 700,
                      cursor: isVerifyingOtp || !otpCode.trim() ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                      marginTop: '8px',
                      opacity: isVerifyingOtp || !otpCode.trim() ? 0.7 : 1
                    }}
                  >
                    {isVerifyingOtp ? (
                      <>
                        <RefreshCw size={16} className="animate-spin" /> Verifying Code...
                      </>
                    ) : (
                      'Verify Email'
                    )}
                  </button>
                </form>
              </div>
            )}

            {/* STEP 2: New Password Entry */}
            {step === 'NEW_PASSWORD' && (
              <div>
                <div style={{ textAlign: 'center', marginBottom: '20px' }}>
                  <div
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: '48px',
                      height: '48px',
                      borderRadius: '12px',
                      backgroundColor: 'rgba(16, 185, 129, 0.12)',
                      border: '1px solid rgba(16, 185, 129, 0.3)',
                      color: '#10b981',
                      marginBottom: '12px'
                    }}
                  >
                    <Lock size={24} />
                  </div>
                  <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#ffffff', margin: '0 0 6px 0' }}>
                    Set New Password
                  </h3>
                  <p style={{ fontSize: '13px', color: '#94a3b8', margin: 0 }}>
                    Enter a new secure password for <strong>{profile?.email}</strong>.
                  </p>
                </div>

                <form onSubmit={handleSubmitPassword} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {/* New Password */}
                  <div>
                    <label
                      htmlFor="new-password-input"
                      style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#cbd5e1', marginBottom: '6px' }}
                    >
                      New Password
                    </label>
                    <div style={{ position: 'relative' }}>
                      <input
                        id="new-password-input"
                        type={showNewPassword ? 'text' : 'password'}
                        required
                        autoFocus
                        placeholder="••••••••"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        disabled={isSubmittingPassword}
                        style={{
                          width: '100%',
                          height: '44px',
                          backgroundColor: '#1e293b',
                          border: '1px solid #334155',
                          borderRadius: '10px',
                          padding: '0 40px 0 14px',
                          fontSize: '14px',
                          color: '#f8fafc',
                          outline: 'none',
                          boxSizing: 'border-box'
                        }}
                      />
                      <button
                        type="button"
                        onClick={() => setShowNewPassword(!showNewPassword)}
                        tabIndex={-1}
                        style={{
                          position: 'absolute',
                          right: '12px',
                          top: '12px',
                          background: 'none',
                          border: 'none',
                          color: '#94a3b8',
                          cursor: 'pointer'
                        }}
                      >
                        {showNewPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                      </button>
                    </div>
                  </div>

                  {/* Confirm Password */}
                  <div>
                    <label
                      htmlFor="confirm-password-input"
                      style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#cbd5e1', marginBottom: '6px' }}
                    >
                      Confirm New Password
                    </label>
                    <div style={{ position: 'relative' }}>
                      <input
                        id="confirm-password-input"
                        type={showConfirmPassword ? 'text' : 'password'}
                        required
                        placeholder="••••••••"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        disabled={isSubmittingPassword}
                        style={{
                          width: '100%',
                          height: '44px',
                          backgroundColor: '#1e293b',
                          border: '1px solid #334155',
                          borderRadius: '10px',
                          padding: '0 40px 0 14px',
                          fontSize: '14px',
                          color: '#f8fafc',
                          outline: 'none',
                          boxSizing: 'border-box'
                        }}
                      />
                      <button
                        type="button"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        tabIndex={-1}
                        style={{
                          position: 'absolute',
                          right: '12px',
                          top: '12px',
                          background: 'none',
                          border: 'none',
                          color: '#94a3b8',
                          cursor: 'pointer'
                        }}
                      >
                        {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                      </button>
                    </div>
                  </div>

                  {/* Password requirements checklist */}
                  <div
                    style={{
                      padding: '12px 14px',
                      backgroundColor: '#1e293b',
                      borderRadius: '8px',
                      fontSize: '12px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '6px'
                    }}
                  >
                    <div style={{ color: hasMinLength ? '#10b981' : '#94a3b8', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {hasMinLength ? <Check size={14} /> : <span style={{ width: '14px' }}>•</span>} At least 8 characters
                    </div>
                    <div style={{ color: hasUpper ? '#10b981' : '#94a3b8', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {hasUpper ? <Check size={14} /> : <span style={{ width: '14px' }}>•</span>} At least one uppercase letter (A-Z)
                    </div>
                    <div style={{ color: hasLower ? '#10b981' : '#94a3b8', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {hasLower ? <Check size={14} /> : <span style={{ width: '14px' }}>•</span>} At least one lowercase letter (a-z)
                    </div>
                    <div style={{ color: hasNumber ? '#10b981' : '#94a3b8', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {hasNumber ? <Check size={14} /> : <span style={{ width: '14px' }}>•</span>} At least one number (0-9)
                    </div>
                    <div style={{ color: hasSpecial ? '#10b981' : '#94a3b8', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {hasSpecial ? <Check size={14} /> : <span style={{ width: '14px' }}>•</span>} At least one special character (!@#$%^&*...)
                    </div>
                    <div style={{ color: passwordsMatch ? '#10b981' : '#94a3b8', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {passwordsMatch ? <Check size={14} /> : <span style={{ width: '14px' }}>•</span>} Passwords match
                    </div>
                  </div>

                  <button
                    id="submit-new-password-btn"
                    type="submit"
                    disabled={isSubmittingPassword || !isPasswordValid}
                    style={{
                      width: '100%',
                      height: '46px',
                      backgroundColor: '#f59e0b',
                      color: '#0f172a',
                      border: 'none',
                      borderRadius: '10px',
                      fontSize: '14px',
                      fontWeight: 700,
                      cursor: isSubmittingPassword || !isPasswordValid ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                      marginTop: '6px',
                      opacity: isSubmittingPassword || !isPasswordValid ? 0.7 : 1
                    }}
                  >
                    {isSubmittingPassword ? (
                      <>
                        <RefreshCw size={16} className="animate-spin" /> Updating Password...
                      </>
                    ) : (
                      'Update Password'
                    )}
                  </button>
                </form>
              </div>
            )}

            {/* STEP 3: Success Screen */}
            {step === 'SUCCESS' && (
              <div style={{ textAlign: 'center', padding: '12px 0' }}>
                <div
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '56px',
                    height: '56px',
                    borderRadius: '50%',
                    backgroundColor: 'rgba(16, 185, 129, 0.15)',
                    color: '#10b981',
                    marginBottom: '16px'
                  }}
                >
                  <CheckCircle2 size={32} />
                </div>
                <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#ffffff', margin: '0 0 8px 0' }}>
                  Password Updated Successfully
                </h3>
                <p style={{ fontSize: '13px', color: '#94a3b8', margin: '0 0 24px 0', lineHeight: 1.5 }}>
                  Your Super Admin password has been updated. All other active sessions have been securely invalidated, and your current session has been refreshed with new credentials.
                </p>

                <button
                  type="button"
                  id="password-success-done-btn"
                  onClick={handleCloseModal}
                  style={{
                    width: '100%',
                    height: '44px',
                    backgroundColor: '#1e293b',
                    color: '#ffffff',
                    border: '1px solid #334155',
                    borderRadius: '10px',
                    fontSize: '14px',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  Done
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
