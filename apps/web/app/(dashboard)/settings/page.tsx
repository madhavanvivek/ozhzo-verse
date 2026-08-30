'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { QRCode, downloadQRCode } from '@/components/ui/QRCode';
import {
  Home,
  Users,
  CreditCard,
  Trash2,
  Check,
  AlertCircle,
  ChevronRight,
  Copy,
  QrCode,
  RefreshCw,
  Ban,
  Download,
  Printer,
  ShieldCheck,
  UserPlus,
  UserCheck,
  UserX
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

interface HomeDetailDTO {
  id: string;
  name: string;
  public_home_id?: string | null;
  home_qr_status?: string;
  home_qr_version?: number;
  home_qr_url?: string | null;
  country?: string | null;
  currency: string;
  timezone: string;
  address?: string | null;
  role: string;
  member_count: number;
}

interface HomeIdentityDTO {
  home_id: string;
  name: string;
  public_home_id: string;
  qr_token: string;
  qr_status: string;
  qr_version: number;
  qr_url: string;
  qr_created_at?: string | null;
  qr_revoked_at?: string | null;
}

interface JoinRequestDTO {
  id: string;
  home_id: string;
  home_name?: string;
  user_id: string;
  display_name: string;
  email?: string | null;
  avatar_url?: string | null;
  status: string;
  message?: string | null;
  created_at: string;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
}

export default function HomeSettingsPage() {
  const router = useRouter();
  const [activeHomeId, setActiveHomeId] = useState<string | null>(null);
  const [homeDetail, setHomeDetail] = useState<HomeDetailDTO | null>(null);
  const [identity, setIdentity] = useState<HomeIdentityDTO | null>(null);
  const [joinRequests, setJoinRequests] = useState<JoinRequestDTO[]>([]);
  const [homeName, setHomeName] = useState('');
  const [currency, setCurrency] = useState('USD');
  const [timezone, setTimezone] = useState('UTC');
  const [address, setAddress] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [copiedHomeId, setCopiedHomeId] = useState(false);
  const [copiedJoinUrl, setCopiedJoinUrl] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isRegeneratingQR, setIsRegeneratingQR] = useState(false);
  const [isRevokingQR, setIsRevokingQR] = useState(false);
  const [reviewingReqId, setReviewingReqId] = useState<string | null>(null);

  const loadHomeSettings = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const initialHomeId = apiClient.getActiveHomeId();
      const [homeIdRes, initialHomeDetailRes] = await Promise.allSettled([
        apiClient.getValidActiveHome(),
        initialHomeId ? apiClient.get<HomeDetailDTO>(`/homes/${initialHomeId}`) : Promise.resolve(null)
      ]);

      const homeId = homeIdRes.status === 'fulfilled' ? homeIdRes.value : null;
      setActiveHomeId(homeId);

      if (homeId) {
        let data: HomeDetailDTO | null = null;
        if (homeId === initialHomeId && initialHomeDetailRes.status === 'fulfilled' && initialHomeDetailRes.value) {
          data = initialHomeDetailRes.value;
        } else {
          data = await apiClient.get<HomeDetailDTO>(`/homes/${homeId}`);
        }

        if (data) {
          setHomeDetail(data);
          setHomeName(data.name || '');
          setCurrency(data.currency || 'USD');
          setTimezone(data.timezone || 'UTC');
          setAddress(data.address || '');
        }

        const role = (data?.role || '').toUpperCase();
        if (['OWNER', 'HOME_ADMIN', 'ADMIN'].includes(role)) {
          const [identRes, joinReqRes] = await Promise.allSettled([
            apiClient.get<HomeIdentityDTO>(`/homes/${homeId}/identity`),
            apiClient.get<JoinRequestDTO[]>(`/homes/${homeId}/join-requests`)
          ]);
          if (identRes.status === 'fulfilled' && identRes.value) {
            setIdentity(identRes.value);
          }
          if (joinReqRes.status === 'fulfilled' && joinReqRes.value) {
            setJoinRequests(joinReqRes.value);
          }
        }
      }
    } catch (err: any) {
      console.error('Failed to load home settings:', err);
      setError(err?.message || 'Failed to load household profile.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadHomeSettings();
    const handleHomeChanged = () => loadHomeSettings();
    window.addEventListener('home-changed', handleHomeChanged);
    return () => window.removeEventListener('home-changed', handleHomeChanged);
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeHomeId || !homeName.trim()) return;

    setIsSaving(true);
    setSavedSuccess(false);
    setError(null);

    try {
      const updated = await apiClient.patch<HomeDetailDTO>(`/homes/${activeHomeId}`, {
        name: homeName.trim(),
        currency,
        timezone,
        address: address.trim() || undefined
      });

      setHomeDetail((prev) => (prev ? { ...prev, ...updated } : updated));
      setSavedSuccess(true);
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new Event('home-changed'));
      }
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err: any) {
      console.error('Failed to update home settings:', err);
      setError(err?.message || 'Failed to update home settings.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCopyHomeId = () => {
    const idToCopy = identity?.public_home_id || homeDetail?.public_home_id || '';
    if (!idToCopy) return;
    navigator.clipboard.writeText(idToCopy);
    setCopiedHomeId(true);
    setTimeout(() => setCopiedHomeId(false), 2500);
  };

  const getJoinUrl = () => {
    const token = identity?.qr_token;
    if (!token) return '';
    if (typeof window !== 'undefined') {
      return `${window.location.origin}/join/home/${token}`;
    }
    return `https://ozhzo-web.onrender.com/join/home/${token}`;
  };

  const handleCopyJoinUrl = () => {
    const url = getJoinUrl();
    if (!url) return;
    navigator.clipboard.writeText(url);
    setCopiedJoinUrl(true);
    setTimeout(() => setCopiedJoinUrl(false), 2500);
  };

  const handleRegenerateQR = async () => {
    if (!activeHomeId) return;
    if (!confirm('Regenerating will immediately invalidate any previously shared QR codes for this home. Continue?')) return;

    setIsRegeneratingQR(true);
    try {
      const updatedIdentity = await apiClient.post<HomeIdentityDTO>(`/homes/${activeHomeId}/qr/regenerate`, {});
      setIdentity(updatedIdentity);
      alert('Home QR code regenerated successfully. The previous QR code is now invalid.');
    } catch (err: any) {
      console.error('Failed to regenerate QR:', err);
      alert(err?.message || 'Failed to regenerate QR code.');
    } finally {
      setIsRegeneratingQR(false);
    }
  };

  const handleRevokeQR = async () => {
    if (!activeHomeId) return;
    if (!confirm('Revoking will prevent anyone from discovering or requesting to join this home via QR until you regenerate a new code. Continue?')) return;

    setIsRevokingQR(true);
    try {
      const updatedIdentity = await apiClient.post<HomeIdentityDTO>(`/homes/${activeHomeId}/qr/revoke`, {});
      setIdentity(updatedIdentity);
      alert('Home QR code revoked. Discovery via this QR code is disabled.');
    } catch (err: any) {
      console.error('Failed to revoke QR:', err);
      alert(err?.message || 'Failed to revoke QR code.');
    } finally {
      setIsRevokingQR(false);
    }
  };

  const handleDownloadQR = () => {
    const canvas = document.querySelector('#home-qr-panel canvas') as HTMLCanvasElement | null;
    const filename = `ozhzo_home_${identity?.public_home_id || 'qr'}.png`;
    downloadQRCode(canvas, filename);
  };

  const handlePrintQR = () => {
    window.print();
  };

  const handleReviewJoinRequest = async (requestId: string, action: 'APPROVE' | 'REJECT') => {
    if (!activeHomeId) return;
    setReviewingReqId(requestId);
    try {
      await apiClient.post(`/homes/${activeHomeId}/join-requests/${requestId}/review`, {
        action,
        role: 'MEMBER'
      });
      const [updatedRequests, updatedDetail] = await Promise.all([
        apiClient.get<JoinRequestDTO[]>(`/homes/${activeHomeId}/join-requests`),
        apiClient.get<HomeDetailDTO>(`/homes/${activeHomeId}`)
      ]);
      setJoinRequests(updatedRequests);
      setHomeDetail(updatedDetail);
    } catch (err: any) {
      console.error(`Failed to ${action} join request:`, err);
      alert(err?.message || `Failed to ${action.toLowerCase()} join request.`);
    } finally {
      setReviewingReqId(null);
    }
  };

  const handleDeleteHome = async () => {
    if (!activeHomeId) return;
    if (!confirm('Are you sure you want to delete this Home workspace? This action will archive all household data.')) return;

    setIsDeleting(true);
    try {
      await apiClient.delete(`/homes/${activeHomeId}`);
      localStorage.removeItem('active_home_id');
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new Event('home-changed'));
      }
      router.push('/dashboard');
    } catch (err: any) {
      console.error('Failed to delete home:', err);
      alert(err?.message || 'Failed to delete home workspace.');
      setIsDeleting(false);
    }
  };

  const roleUpper = (homeDetail?.role || '').toUpperCase();
  const isOwnerOrAdmin = ['OWNER', 'HOME_ADMIN', 'ADMIN'].includes(roleUpper);
  const pendingRequests = joinRequests.filter((r) => r.status === 'PENDING');

  if (isLoading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '840px' }}>
        <div style={{ height: '60px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: 'var(--radius-md)', animation: 'pulse 1.5s infinite' }} />
        <div style={{ height: '260px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: 'var(--radius-lg)' }} />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '840px' }}>
      <div>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-primary-900)' }}>
          Home Settings & Management
        </h1>
        <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)' }}>
          Manage permanent household identity, secure Home QR discovery, family members, and workspace settings.
        </p>
      </div>

      {savedSuccess && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 14px', backgroundColor: 'var(--status-in-stock-bg)', color: 'var(--status-in-stock)', borderRadius: 'var(--radius-md)', fontSize: '13px', fontWeight: 600 }}>
          <Check size={16} />
          <span>Home settings updated successfully.</span>
        </div>
      )}

      {error && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 14px', backgroundColor: 'var(--status-overdue-bg)', color: 'var(--status-overdue)', borderRadius: 'var(--radius-md)', fontSize: '13px', fontWeight: 500 }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* 1. Permanent Home Identity & Public ID Card */}
      <Card style={{ border: '1px solid var(--color-border-strong)', backgroundColor: 'var(--color-surface-card)', padding: 'var(--space-5)' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', justifyContent: 'space-between', gap: 'var(--space-4)' }}>
          <div style={{ display: 'flex', gap: '14px' }}>
            <div style={{ width: '44px', height: '44px', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--color-primary-900)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <ShieldCheck size={24} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                <h2 style={{ fontSize: '17px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                  Permanent Home Identity
                </h2>
                <Badge variant="completed">Permanent</Badge>
              </div>
              <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '2px', maxWidth: '480px' }}>
                Your Home ID is a permanent, collision-resistant public identifier. It does not change if you rename the home or update settings.
              </p>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '12px', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>Public Home ID:</span>
                <span style={{
                  fontFamily: 'var(--font-mono, monospace)',
                  fontSize: '15px',
                  fontWeight: 700,
                  color: 'var(--color-primary-900)',
                  backgroundColor: 'var(--color-surface-subtle)',
                  padding: '4px 10px',
                  borderRadius: '6px',
                  letterSpacing: '1px'
                }}>
                  {identity?.public_home_id || homeDetail?.public_home_id || 'OZH-PENDING'}
                </span>
                <button
                  type="button"
                  onClick={handleCopyHomeId}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    padding: '4px 10px',
                    fontSize: '12px',
                    fontWeight: 600,
                    borderRadius: '6px',
                    border: '1px solid var(--color-border-strong)',
                    backgroundColor: 'var(--color-surface-card)',
                    color: copiedHomeId ? 'var(--status-in-stock)' : 'var(--color-text-primary)',
                    cursor: 'pointer'
                  }}
                >
                  {copiedHomeId ? <Check size={14} /> : <Copy size={14} />}
                  <span>{copiedHomeId ? 'Copied!' : 'Copy Home ID'}</span>
                </button>
              </div>

              {homeDetail?.id && (
                <div style={{ marginTop: '8px', fontSize: '11px', color: 'var(--color-text-tertiary)', fontFamily: 'monospace' }}>
                  UUID: {homeDetail.id}
                </div>
              )}
            </div>
          </div>
        </div>
      </Card>

      {/* 2. Interactive Home QR Code & Discovery Card */}
      {isOwnerOrAdmin && (
        <Card id="home-qr-panel" style={{ border: '1px solid var(--color-border-strong)', backgroundColor: 'var(--color-surface-card)', padding: 'var(--space-5)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)', paddingBottom: 'var(--space-3)', borderBottom: '1px solid var(--color-border-subtle)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <QrCode size={20} color="var(--color-primary-900)" />
              <h2 style={{ fontSize: '16px', fontWeight: 600 }}>Home QR Discovery & Physical Join Card</h2>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Badge variant={identity?.qr_status === 'ACTIVE' ? 'completed' : 'overdue'}>
                {identity?.qr_status || 'ACTIVE'}
              </Badge>
              <Badge variant="neutral">v{identity?.qr_version || 1}</Badge>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 'var(--space-6)', alignItems: 'center' }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '16px', backgroundColor: 'white', borderRadius: '12px', border: '1px solid var(--color-border)', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }}>
              <QRCode value={getJoinUrl()} size={160} />
              <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-primary-900)', marginTop: '8px', letterSpacing: '0.5px' }}>
                {identity?.public_home_id || 'OZH-HOME'}
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-primary-900)' }}>
                Secure QR for Guests & Family Members
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                Scanning this QR code directs visitors to a secure landing page where they can verify household details and submit a membership join request. Scanning does <strong>not</strong> grant instant membership; you must approve all requests.
              </p>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginTop: '4px' }}>
                <button
                  type="button"
                  onClick={handleCopyJoinUrl}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '6px 12px',
                    fontSize: '12px',
                    fontWeight: 600,
                    borderRadius: '6px',
                    border: '1px solid var(--color-border-strong)',
                    backgroundColor: 'var(--color-surface-subtle)',
                    color: copiedJoinUrl ? 'var(--status-in-stock)' : 'var(--color-text-primary)',
                    cursor: 'pointer'
                  }}
                >
                  {copiedJoinUrl ? <Check size={14} /> : <Copy size={14} />}
                  <span>{copiedJoinUrl ? 'Join Link Copied!' : 'Copy Join Link'}</span>
                </button>

                <Button variant="secondary" size="sm" onClick={handleDownloadQR}>
                  <Download size={14} />
                  <span>Download PNG</span>
                </Button>

                <Button variant="secondary" size="sm" onClick={handlePrintQR}>
                  <Printer size={14} />
                  <span>Print QR Card</span>
                </Button>

                <Button variant="secondary" size="sm" onClick={handleRegenerateQR} isLoading={isRegeneratingQR}>
                  <RefreshCw size={14} />
                  <span>Regenerate QR</span>
                </Button>

                {identity?.qr_status === 'ACTIVE' && (
                  <Button variant="destructive" size="sm" onClick={handleRevokeQR} isLoading={isRevokingQR}>
                    <Ban size={14} />
                    <span>Revoke QR</span>
                  </Button>
                )}
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* 3. Pending Join Requests Card (For Admins) */}
      {isOwnerOrAdmin && (
        <Card style={{ border: '1px solid var(--color-border-strong)', backgroundColor: 'var(--color-surface-card)', padding: 'var(--space-5)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-3)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <UserPlus size={18} color="var(--color-primary-900)" />
              <h2 style={{ fontSize: '16px', fontWeight: 600 }}>
                Pending Join Requests
              </h2>
            </div>
            <Badge variant={pendingRequests.length > 0 ? 'low-stock' : 'neutral'}>
              {pendingRequests.length} {pendingRequests.length === 1 ? 'Request' : 'Requests'}
            </Badge>
          </div>

          {pendingRequests.length === 0 ? (
            <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', padding: '12px 0' }}>
              No pending membership requests from QR scans. When someone scans your Home QR code and requests access, they will appear here for your review.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '10px' }}>
              {pendingRequests.map((req) => (
                <div
                  key={req.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '12px 14px',
                    backgroundColor: 'var(--color-surface-subtle)',
                    borderRadius: '8px',
                    border: '1px solid var(--color-border-subtle)',
                    flexWrap: 'wrap',
                    gap: '10px'
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                        {req.display_name}
                      </span>
                      {req.email && (
                        <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                          ({req.email})
                        </span>
                      )}
                    </div>
                    {req.message && (
                      <p style={{ fontSize: '12px', color: 'var(--color-text-primary)', marginTop: '4px', fontStyle: 'italic' }}>
                        &ldquo;{req.message}&rdquo;
                      </p>
                    )}
                    <span style={{ fontSize: '11px', color: 'var(--color-text-tertiary)' }}>
                      Requested {new Date(req.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Button
                      size="sm"
                      onClick={() => handleReviewJoinRequest(req.id, 'APPROVE')}
                      isLoading={reviewingReqId === req.id}
                    >
                      <UserCheck size={14} />
                      <span>Approve Member</span>
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => handleReviewJoinRequest(req.id, 'REJECT')}
                      isLoading={reviewingReqId === req.id}
                    >
                      <UserX size={14} />
                      <span>Reject</span>
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* 4. Family Members Navigation Card */}
      <Card style={{ border: '2px solid var(--color-primary-900)', backgroundColor: 'var(--color-surface-overlay)', padding: 'var(--space-5)' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-3)', marginBottom: 'var(--space-3)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ width: '40px', height: '40px', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--color-primary-900)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Users size={22} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ fontSize: '17px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                  Family Members
                </h2>
                {homeDetail?.member_count !== undefined && (
                  <Badge variant="neutral">
                    {homeDetail.member_count} {homeDetail.member_count === 1 ? 'Member' : 'Members'}
                  </Badge>
                )}
              </div>
              <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
                Manage the people who belong to this Home, their roles and invitations.
              </p>
            </div>
          </div>

          <Link
            href="/members"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'var(--color-primary-900)',
              color: 'var(--color-text-inverse)',
              fontSize: '13px',
              fontWeight: 600,
              textDecoration: 'none',
              transition: 'background-color 0.15s ease'
            }}
          >
            <span>Manage Members</span>
            <ChevronRight size={16} />
          </Link>
        </div>

        <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', paddingTop: 'var(--space-3)', borderTop: '1px solid var(--color-border-subtle)' }}>
          Invite co-parents, children, guests, and manage access permissions for <strong>{homeDetail?.name || 'this Home'}</strong>.
        </div>
      </Card>

      {/* 5. General Home Profile */}
      <Card>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)', paddingBottom: 'var(--space-3)', borderBottom: '1px solid var(--color-border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Home size={18} color="var(--color-primary-900)" />
            <h2 style={{ fontSize: '16px', fontWeight: 600 }}>Household Profile</h2>
          </div>
          {homeDetail?.role && (
            <Badge variant={isOwnerOrAdmin ? 'completed' : 'neutral'}>
              Your Role: {homeDetail.role}
            </Badge>
          )}
        </div>

        <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <Input
            id="homeName"
            label="Household Name"
            value={homeName}
            onChange={(e) => setHomeName(e.target.value)}
            required
            disabled={!isOwnerOrAdmin}
          />

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label htmlFor="currency" style={{ fontSize: '13px', fontWeight: 600 }}>
                Primary Currency
              </label>
              <select
                id="currency"
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                disabled={!isOwnerOrAdmin}
                style={{
                  height: '42px',
                  padding: '0 12px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border-strong)',
                  backgroundColor: 'var(--color-surface-card)',
                  color: 'var(--color-text-primary)',
                  fontSize: '14px'
                }}
              >
                <option value="USD">USD ($ - US Dollar)</option>
                <option value="EUR">EUR (€ - Euro)</option>
                <option value="GBP">GBP (£ - British Pound)</option>
                <option value="CAD">CAD ($ - Canadian Dollar)</option>
                <option value="AUD">AUD ($ - Australian Dollar)</option>
                <option value="INR">INR (₹ - Indian Rupee)</option>
              </select>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label htmlFor="timezone" style={{ fontSize: '13px', fontWeight: 600 }}>
                Household Timezone
              </label>
              <select
                id="timezone"
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                disabled={!isOwnerOrAdmin}
                style={{
                  height: '42px',
                  padding: '0 12px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border-strong)',
                  backgroundColor: 'var(--color-surface-card)',
                  color: 'var(--color-text-primary)',
                  fontSize: '14px'
                }}
              >
                <option value="America/New_York">America/New York (EST/EDT)</option>
                <option value="America/Chicago">America/Chicago (CST/CDT)</option>
                <option value="America/Los_Angeles">America/Los Angeles (PST/PDT)</option>
                <option value="Europe/London">Europe/London (GMT/BST)</option>
                <option value="Europe/Paris">Europe/Paris (CET/CEST)</option>
                <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
                <option value="UTC">UTC</option>
              </select>
            </div>
          </div>

          <Input
            id="address"
            label="Address / Location (Optional)"
            placeholder="e.g. 123 Main St, Apt 4B"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            disabled={!isOwnerOrAdmin}
          />

          {isOwnerOrAdmin && (
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 'var(--space-2)' }}>
              <Button type="submit" isLoading={isSaving}>
                Save Changes
              </Button>
            </div>
          )}
        </form>
      </Card>

      {/* 6. Household Subscription */}
      <Card style={{ padding: 'var(--space-5)' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-3)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ width: '40px', height: '40px', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--color-surface-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <CreditCard size={20} color="var(--color-primary-900)" />
            </div>
            <div>
              <h2 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-primary-900)' }}>
                Household Subscription & Entitlements
              </h2>
              <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
                View seat allocations, standard list pricing, and introductory promotional discounts.
              </p>
            </div>
          </div>

          <Link
            href="/settings/subscription"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-border)',
              backgroundColor: 'var(--color-surface-card)',
              color: 'var(--color-text-primary)',
              fontSize: '13px',
              fontWeight: 600,
              textDecoration: 'none'
            }}
          >
            <span>View Subscription</span>
            <ChevronRight size={16} />
          </Link>
        </div>
      </Card>

      {/* 7. Danger Zone: Delete Workspace */}
      {isOwnerOrAdmin && (
        <Card style={{ borderColor: 'var(--status-overdue-bg)', backgroundColor: '#fffcfc' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: 'var(--space-2)', color: 'var(--status-overdue)' }}>
            <AlertCircle size={18} />
            <h2 style={{ fontSize: '16px', fontWeight: 600 }}>Danger Zone</h2>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-4)', lineHeight: 1.5 }}>
            Deleting a Home workspace will soft-archive all associated inventory, chores, bills, and calendar records. Only a Home Admin or Owner can perform this action.
          </p>
          <Button variant="destructive" onClick={handleDeleteHome} isLoading={isDeleting}>
            <Trash2 size={16} />
            <span>Delete This Home</span>
          </Button>
        </Card>
      )}
    </div>
  );
}
