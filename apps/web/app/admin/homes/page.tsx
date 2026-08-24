'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Home,
  Search,
  RefreshCw,
  ExternalLink,
  Users,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  PauseCircle,
  Archive,
  Play
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';
import { AdminBadge } from '../components/AdminBadge';
import { AdminConfirmModal } from '../components/AdminConfirmModal';
import { AdminHomeListItem } from '../types';

export default function AdminHomesPage() {
  const [homes, setHomes] = useState<AdminHomeListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);

  // Selection & Bulk Actions
  const [selectedHomeIds, setSelectedHomeIds] = useState<Set<string>>(new Set());
  const [modalConfig, setModalConfig] = useState<{
    isOpen: boolean;
    title: string;
    description: string;
    action: 'ACTIVATE' | 'SUSPEND' | 'HOLD' | 'ARCHIVE' | 'DELETE';
    targetHomeIds: string[];
    confirmVariant: 'danger' | 'primary' | 'success';
  }>({
    isOpen: false,
    title: '',
    description: '',
    action: 'SUSPEND',
    targetHomeIds: [],
    confirmVariant: 'danger'
  });
  const [isSubmittingAction, setIsSubmittingAction] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Search & Filter
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'ACTIVE' | 'SUSPENDED' | 'HELD' | 'ARCHIVED'>('ALL');

  // Pagination
  const [page, setPage] = useState(0);
  const limit = 20;

  const fetchHomes = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (searchQuery.trim()) params.set('query', searchQuery.trim());
      if (statusFilter !== 'ALL') params.set('status', statusFilter);
      params.set('limit', String(limit));
      params.set('offset', String(page * limit));

      const res = await apiClient.get<AdminHomeListItem[]>(`/admin/homes?${params.toString()}`);
      setHomes(res || []);
      setSelectedHomeIds(new Set());
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch platform homes.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHomes();
  }, [page, statusFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    fetchHomes();
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return '—';
    try {
      return new Date(dateStr).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return dateStr;
    }
  };

  // Selection Handlers
  const toggleSelectAll = () => {
    if (selectedHomeIds.size === homes.length && homes.length > 0) {
      setSelectedHomeIds(new Set());
    } else {
      setSelectedHomeIds(new Set(homes.map((h) => h.id)));
    }
  };

  const toggleSelectHome = (homeId: string) => {
    setSelectedHomeIds((prev) => {
      const next = new Set(prev);
      if (next.has(homeId)) {
        next.delete(homeId);
      } else {
        next.add(homeId);
      }
      return next;
    });
  };

  // Action Triggers
  const openActionModal = (
    action: 'ACTIVATE' | 'SUSPEND' | 'HOLD' | 'ARCHIVE' | 'DELETE',
    targetIds: string[]
  ) => {
    if (targetIds.length === 0) return;
    setActionError(null);

    const isBulk = targetIds.length > 1;
    const countLabel = isBulk ? `${targetIds.length} household workspaces` : 'this household workspace';

    const configs = {
      ACTIVATE: {
        title: `Activate ${isBulk ? 'Workspaces' : 'Workspace'}`,
        description: `Restore full access and data mutation privileges for members of ${countLabel}?`,
        confirmVariant: 'success' as const
      },
      SUSPEND: {
        title: `Suspend ${isBulk ? 'Workspaces' : 'Workspace'}`,
        description: `This will block all member access and operations for ${countLabel}.`,
        confirmVariant: 'danger' as const
      },
      HOLD: {
        title: `Place Workspace on Hold`,
        description: `Temporarily lock workspace operations for ${countLabel} pending administrative investigation.`,
        confirmVariant: 'primary' as const
      },
      ARCHIVE: {
        title: `Archive Workspace`,
        description: `Archive ${countLabel}. This marks the workspace as retired and hides it from standard member views.`,
        confirmVariant: 'danger' as const
      },
      DELETE: {
        title: `Delete Workspace`,
        description: `Permanently soft-delete ${countLabel}.`,
        confirmVariant: 'danger' as const
      }
    };

    const cfg = configs[action];
    setModalConfig({
      isOpen: true,
      title: cfg.title,
      description: cfg.description,
      action,
      targetHomeIds: targetIds,
      confirmVariant: cfg.confirmVariant
    });
  };

  const handleConfirmAction = async (reason: string) => {
    setIsSubmittingAction(true);
    setActionError(null);
    try {
      if (modalConfig.targetHomeIds.length > 1) {
        const res = await apiClient.post<any>('/admin/homes/bulk-action', {
          home_ids: modalConfig.targetHomeIds,
          action: modalConfig.action,
          reason: reason || undefined
        });
        setFeedbackMessage(res?.message || `Bulk ${modalConfig.action} executed successfully.`);
      } else {
        const targetId = modalConfig.targetHomeIds[0];
        let endpoint = `/admin/homes/${targetId}/suspend`;
        if (modalConfig.action === 'ACTIVATE') endpoint = `/admin/homes/${targetId}/reactivate`;
        if (modalConfig.action === 'HOLD') endpoint = `/admin/homes/${targetId}/hold`;
        if (modalConfig.action === 'ARCHIVE') endpoint = `/admin/homes/${targetId}/archive`;
        if (modalConfig.action === 'DELETE') endpoint = `/admin/homes/${targetId}/archive`;

        const res = await apiClient.post<any>(endpoint, { reason: reason || undefined });
        setFeedbackMessage(res?.message || `Household workspace updated successfully.`);
      }

      setModalConfig((prev) => ({ ...prev, isOpen: false }));
      setSelectedHomeIds(new Set());
      fetchHomes();
    } catch (err: any) {
      setActionError(err?.message || `Failed to execute ${modalConfig.action}.`);
    } finally {
      setIsSubmittingAction(false);
    }
  };

  const isAllSelected = homes.length > 0 && selectedHomeIds.size === homes.length;
  const isSomeSelected = selectedHomeIds.size > 0 && selectedHomeIds.size < homes.length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px'
        }}
      >
        <div>
          <h1
            style={{
              fontSize: '22px',
              fontWeight: 700,
              color: 'var(--color-text-primary, #0f172a)',
              margin: 0
            }}
          >
            Household Workspaces
          </h1>
          <p
            style={{
              fontSize: '14px',
              color: 'var(--color-text-secondary, #64748b)',
              marginTop: '4px'
            }}
          >
            Inspect tenant household workspaces, membership density, and subscription statuses across the platform.
          </p>
        </div>

        <button
          onClick={fetchHomes}
          disabled={isLoading}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 16px',
            borderRadius: 'var(--radius-md, 10px)',
            border: '1px solid var(--color-border-subtle, #e2e8f0)',
            backgroundColor: 'var(--color-surface-card, #ffffff)',
            fontSize: '13px',
            fontWeight: 600,
            color: 'var(--color-text-primary, #0f172a)',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            minHeight: '44px'
          }}
        >
          <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Floating Bulk Action Bar */}
      {selectedHomeIds.size > 0 && (
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
            backgroundColor: 'var(--color-primary-900, #0f172a)',
            color: '#ffffff',
            padding: '12px 20px',
            borderRadius: 'var(--radius-lg, 16px)',
            boxShadow: '0 10px 25px -5px rgba(15, 23, 42, 0.3)',
            animation: 'fadeIn 0.2s ease-in-out'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '14px', fontWeight: 600 }}>
            <Home size={18} />
            <span>Selected {selectedHomeIds.size} {selectedHomeIds.size === 1 ? 'workspace' : 'workspaces'}</span>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={() => openActionModal('ACTIVATE', Array.from(selectedHomeIds))}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: 'var(--radius-md, 8px)',
                backgroundColor: 'var(--status-in-stock, #10b981)',
                color: '#ffffff',
                border: 'none',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
                minHeight: '38px'
              }}
            >
              <Play size={16} />
              <span>Activate</span>
            </button>

            <button
              onClick={() => openActionModal('SUSPEND', Array.from(selectedHomeIds))}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: 'var(--radius-md, 8px)',
                backgroundColor: 'var(--status-overdue, #ef4444)',
                color: '#ffffff',
                border: 'none',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
                minHeight: '38px'
              }}
            >
              <AlertTriangle size={16} />
              <span>Suspend</span>
            </button>

            <button
              onClick={() => openActionModal('HOLD', Array.from(selectedHomeIds))}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: 'var(--radius-md, 8px)',
                backgroundColor: 'var(--color-primary-700, #334155)',
                color: '#ffffff',
                border: 'none',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
                minHeight: '38px'
              }}
            >
              <PauseCircle size={16} />
              <span>Hold</span>
            </button>

            <button
              onClick={() => openActionModal('ARCHIVE', Array.from(selectedHomeIds))}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: 'var(--radius-md, 8px)',
                backgroundColor: '#7f1d1d',
                color: '#ffffff',
                border: 'none',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
                minHeight: '38px'
              }}
            >
              <Archive size={16} />
              <span>Archive</span>
            </button>

            <button
              onClick={() => setSelectedHomeIds(new Set())}
              style={{
                padding: '8px 12px',
                borderRadius: 'var(--radius-md, 8px)',
                backgroundColor: 'transparent',
                color: 'var(--color-text-tertiary, #94a3b8)',
                border: '1px solid #475569',
                fontSize: '13px',
                fontWeight: 500,
                cursor: 'pointer',
                minHeight: '38px'
              }}
            >
              Clear
            </button>
          </div>
        </div>
      )}

      {/* Feedback Toast */}
      {feedbackMessage && (
        <div
          style={{
            padding: '14px 16px',
            backgroundColor: 'var(--status-in-stock-bg, #ecfdf5)',
            border: '1px solid #a7f3d0',
            borderRadius: 'var(--radius-md, 10px)',
            color: 'var(--status-in-stock, #10b981)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '14px',
            fontWeight: 500
          }}
        >
          <span>{feedbackMessage}</span>
          <button
            onClick={() => setFeedbackMessage(null)}
            style={{ background: 'none', border: 'none', color: '#047857', cursor: 'pointer', fontWeight: 700 }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div
        style={{
          backgroundColor: 'var(--color-surface-card, #ffffff)',
          borderRadius: 'var(--radius-lg, 16px)',
          border: '1px solid var(--color-border-subtle, #e2e8f0)',
          padding: '16px',
          boxShadow: 'var(--shadow-subtle)',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}
      >
        <form
          onSubmit={handleSearchSubmit}
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '10px',
            alignItems: 'center'
          }}
        >
          {/* Search Input */}
          <div style={{ flex: '1 1 240px', position: 'relative' }}>
            <Search
              size={18}
              style={{
                position: 'absolute',
                left: '12px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--color-text-tertiary, #94a3b8)'
              }}
            />
            <input
              type="text"
              placeholder="Search by workspace name, ID, or creator..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '10px 12px 10px 38px',
                borderRadius: 'var(--radius-md, 10px)',
                border: '1px solid var(--color-border-subtle, #e2e8f0)',
                fontSize: '14px',
                backgroundColor: 'var(--color-surface-subtle, #f1f5f9)',
                color: 'var(--color-text-primary, #0f172a)',
                outline: 'none',
                minHeight: '44px'
              }}
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as any);
              setPage(0);
            }}
            aria-label="Filter by workspace status"
            style={{
              padding: '10px 14px',
              borderRadius: 'var(--radius-md, 10px)',
              border: '1px solid var(--color-border-subtle, #e2e8f0)',
              backgroundColor: 'var(--color-surface-subtle, #f1f5f9)',
              fontSize: '13px',
              fontWeight: 500,
              color: 'var(--color-text-primary, #0f172a)',
              minHeight: '44px',
              outline: 'none',
              cursor: 'pointer'
            }}
          >
            <option value="ALL">All Statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="SUSPENDED">Suspended</option>
            <option value="HELD">Held</option>
            <option value="ARCHIVED">Archived</option>
          </select>

          <button
            type="submit"
            style={{
              padding: '10px 18px',
              borderRadius: 'var(--radius-md, 10px)',
              backgroundColor: 'var(--color-primary-900, #0f172a)',
              color: 'var(--color-text-inverse, #ffffff)',
              fontSize: '13px',
              fontWeight: 600,
              border: 'none',
              cursor: 'pointer',
              minHeight: '44px'
            }}
          >
            Search
          </button>
        </form>
      </div>

      {/* Error Alert */}
      {error && (
        <div
          style={{
            padding: '16px 20px',
            backgroundColor: 'var(--status-overdue-bg, #fef2f2)',
            border: '1px solid #fecaca',
            borderRadius: 'var(--radius-md, 10px)',
            color: 'var(--status-overdue, #ef4444)',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
            fontSize: '14px'
          }}
        >
          <div>
            <span style={{ fontWeight: 700 }}>Unable to load household workspaces:</span> {error}
          </div>
          <button
            onClick={fetchHomes}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              borderRadius: 'var(--radius-md, 8px)',
              backgroundColor: 'var(--status-overdue, #ef4444)',
              color: '#ffffff',
              border: 'none',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              minHeight: '36px'
            }}
          >
            <RefreshCw size={14} />
            <span>Retry</span>
          </button>
        </div>
      )}

      {/* Homes Table & Responsive Cards */}
      <div
        style={{
          backgroundColor: 'var(--color-surface-card, #ffffff)',
          borderRadius: 'var(--radius-lg, 16px)',
          border: '1px solid var(--color-border-subtle, #e2e8f0)',
          overflow: 'hidden',
          boxShadow: 'var(--shadow-subtle)'
        }}
      >
        {isLoading ? (
          <div
            style={{
              padding: '48px 24px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '12px',
              color: 'var(--color-text-secondary, #64748b)'
            }}
          >
            <RefreshCw size={24} className="animate-spin" color="var(--color-accent-warm, #f97316)" />
            <span style={{ fontSize: '14px', fontWeight: 500 }}>Loading household workspaces...</span>
          </div>
        ) : homes.length === 0 ? (
          <div
            style={{
              padding: '48px 24px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              textAlign: 'center',
              gap: '8px'
            }}
          >
            <Home size={36} color="var(--color-text-tertiary, #94a3b8)" />
            <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)' }}>
              No Workspaces Found
            </div>
            <div style={{ fontSize: '14px', color: 'var(--color-text-secondary, #64748b)', maxWidth: '360px' }}>
              No household workspaces matched your search parameters.
            </div>
          </div>
        ) : (
          <>
            {/* Desktop / Tablet Table */}
            <div className="ozhzo-admin-table-container">
              <table
                style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  textAlign: 'left',
                  fontSize: '13px'
                }}
              >
                <thead>
                  <tr
                    style={{
                      borderBottom: '1px solid var(--color-border-subtle, #e2e8f0)',
                      backgroundColor: 'var(--color-surface-subtle, #f1f5f9)',
                      color: 'var(--color-text-secondary, #64748b)',
                      fontWeight: 600
                    }}
                  >
                    <th style={{ padding: '12px 16px', width: '40px' }}>
                      <input
                        type="checkbox"
                        checked={isAllSelected}
                        ref={(el) => {
                          if (el) el.indeterminate = isSomeSelected;
                        }}
                        onChange={toggleSelectAll}
                        aria-label="Select all workspaces"
                        style={{ cursor: 'pointer', width: '16px', height: '16px' }}
                      />
                    </th>
                    <th style={{ padding: '12px 16px' }}>Home Name</th>
                    <th style={{ padding: '12px 16px' }}>Status</th>
                    <th style={{ padding: '12px 16px' }}>Created By</th>
                    <th style={{ padding: '12px 16px' }}>Members</th>
                    <th style={{ padding: '12px 16px' }}>Subscription</th>
                    <th style={{ padding: '12px 16px' }}>Created</th>
                    <th style={{ padding: '12px 16px', textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {homes.map((h) => {
                    const isSelected = selectedHomeIds.has(h.id);
                    return (
                      <tr
                        key={h.id}
                        style={{
                          borderBottom: '1px solid var(--color-border-subtle, #e2e8f0)',
                          backgroundColor: isSelected ? 'rgba(59, 130, 246, 0.05)' : undefined,
                          transition: 'background-color 0.15s ease'
                        }}
                      >
                        <td style={{ padding: '12px 16px' }}>
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleSelectHome(h.id)}
                            aria-label={`Select workspace ${h.name}`}
                            style={{ cursor: 'pointer', width: '16px', height: '16px' }}
                          />
                        </td>

                        <td style={{ padding: '12px 16px' }}>
                          <div style={{ fontWeight: 600, color: 'var(--color-text-primary, #0f172a)' }}>
                            {h.name}
                          </div>
                          <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                            ID: {h.id.slice(0, 8)}... | Currency: {h.currency}
                          </div>
                        </td>

                        <td style={{ padding: '12px 16px' }}>
                          {h.status === 'ACTIVE' && <AdminBadge variant="success">Active</AdminBadge>}
                          {h.status === 'SUSPENDED' && <AdminBadge variant="danger">Suspended</AdminBadge>}
                          {h.status === 'HELD' && <AdminBadge variant="warning">Held</AdminBadge>}
                          {h.status === 'ARCHIVED' && <AdminBadge variant="neutral">Archived</AdminBadge>}
                        </td>

                        <td style={{ padding: '12px 16px', color: 'var(--color-text-secondary, #64748b)' }}>
                          <div style={{ fontWeight: 500, color: 'var(--color-text-primary, #0f172a)' }}>
                            {h.created_by_name || 'Home Owner'}
                          </div>
                          <div style={{ fontSize: '12px' }}>{h.created_by_email || '—'}</div>
                        </td>

                        <td style={{ padding: '12px 16px', color: 'var(--color-text-primary, #0f172a)' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <Users size={14} color="var(--color-text-secondary, #64748b)" />
                            <span>{h.members_count} {h.members_count === 1 ? 'member' : 'members'}</span>
                          </div>
                        </td>

                        <td style={{ padding: '12px 16px' }}>
                          <AdminBadge
                            variant={
                              h.subscription_status === 'ACTIVE'
                                ? 'success'
                                : h.subscription_status === 'PAST_DUE'
                                ? 'danger'
                                : 'info'
                            }
                          >
                            {h.subscription_status || 'TRIALING'}
                          </AdminBadge>
                        </td>

                        <td style={{ padding: '12px 16px', color: 'var(--color-text-secondary, #64748b)' }}>
                          {formatDate(h.created_at)}
                        </td>

                        <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                            <Link
                              href={`/admin/homes/${h.id}`}
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px',
                                padding: '6px 10px',
                                borderRadius: 'var(--radius-md, 8px)',
                                border: '1px solid var(--color-border-subtle, #e2e8f0)',
                                backgroundColor: 'var(--color-surface-subtle, #f1f5f9)',
                                fontSize: '12px',
                                fontWeight: 600,
                                color: 'var(--color-text-primary, #0f172a)',
                                minHeight: '32px'
                              }}
                            >
                              <span>Inspect</span>
                              <ExternalLink size={12} />
                            </Link>

                            {h.status === 'ACTIVE' ? (
                              <button
                                onClick={() => openActionModal('SUSPEND', [h.id])}
                                style={{
                                  padding: '6px 10px',
                                  borderRadius: 'var(--radius-md, 8px)',
                                  backgroundColor: 'var(--status-overdue-bg, #fef2f2)',
                                  color: 'var(--status-overdue, #ef4444)',
                                  border: '1px solid #fecaca',
                                  fontSize: '12px',
                                  fontWeight: 600,
                                  cursor: 'pointer',
                                  minHeight: '32px'
                                }}
                              >
                                Suspend
                              </button>
                            ) : (
                              <button
                                onClick={() => openActionModal('ACTIVATE', [h.id])}
                                style={{
                                  padding: '6px 10px',
                                  borderRadius: 'var(--radius-md, 8px)',
                                  backgroundColor: 'var(--status-in-stock-bg, #ecfdf5)',
                                  color: 'var(--status-in-stock, #10b981)',
                                  border: '1px solid #a7f3d0',
                                  fontSize: '12px',
                                  fontWeight: 600,
                                  cursor: 'pointer',
                                  minHeight: '32px'
                                }}
                              >
                                Activate
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Mobile Cards */}
            <div className="ozhzo-admin-cards-container" style={{ display: 'none', padding: '12px', flexDirection: 'column', gap: '12px' }}>
              {homes.map((h) => {
                const isSelected = selectedHomeIds.has(h.id);
                return (
                  <div
                    key={h.id}
                    style={{
                      padding: '16px',
                      borderRadius: 'var(--radius-md, 10px)',
                      border: isSelected ? '2px solid var(--color-primary-900, #0f172a)' : '1px solid var(--color-border-subtle, #e2e8f0)',
                      backgroundColor: 'var(--color-surface-card, #ffffff)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '10px'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSelectHome(h.id)}
                          aria-label={`Select workspace ${h.name}`}
                          style={{ cursor: 'pointer', width: '18px', height: '18px' }}
                        />
                        <div>
                          <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)' }}>
                            {h.name}
                          </div>
                          <div style={{ fontSize: '13px', color: 'var(--color-text-secondary, #64748b)' }}>
                            Owner: {h.created_by_name || 'Owner'} ({h.created_by_email || '—'})
                          </div>
                        </div>
                      </div>
                      {h.status === 'ACTIVE' && <AdminBadge variant="success">Active</AdminBadge>}
                      {h.status === 'SUSPENDED' && <AdminBadge variant="danger">Suspended</AdminBadge>}
                      {h.status === 'HELD' && <AdminBadge variant="warning">Held</AdminBadge>}
                      {h.status === 'ARCHIVED' && <AdminBadge variant="neutral">Archived</AdminBadge>}
                    </div>

                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', fontSize: '12px' }}>
                      <AdminBadge variant="info">{h.members_count} Members</AdminBadge>
                      <AdminBadge variant="neutral">{h.subscription_status || 'TRIALING'}</AdminBadge>
                      <AdminBadge variant="neutral">Currency: {h.currency}</AdminBadge>
                    </div>

                    <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                      Created: {formatDate(h.created_at)}
                    </div>

                    <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                      <Link
                        href={`/admin/homes/${h.id}`}
                        style={{
                          flex: 1,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '6px',
                          padding: '10px',
                          borderRadius: 'var(--radius-md, 10px)',
                          backgroundColor: 'var(--color-primary-900, #0f172a)',
                          color: 'var(--color-text-inverse, #ffffff)',
                          fontSize: '13px',
                          fontWeight: 600,
                          minHeight: '44px'
                        }}
                      >
                        <span>Inspect Workspace</span>
                        <ExternalLink size={14} />
                      </Link>

                      {h.status === 'ACTIVE' ? (
                        <button
                          onClick={() => openActionModal('SUSPEND', [h.id])}
                          style={{
                            padding: '10px 14px',
                            borderRadius: 'var(--radius-md, 10px)',
                            backgroundColor: 'var(--status-overdue-bg, #fef2f2)',
                            color: 'var(--status-overdue, #ef4444)',
                            border: '1px solid #fecaca',
                            fontSize: '13px',
                            fontWeight: 600,
                            cursor: 'pointer',
                            minHeight: '44px'
                          }}
                        >
                          Suspend
                        </button>
                      ) : (
                        <button
                          onClick={() => openActionModal('ACTIVATE', [h.id])}
                          style={{
                            padding: '10px 14px',
                            borderRadius: 'var(--radius-md, 10px)',
                            backgroundColor: 'var(--status-in-stock-bg, #ecfdf5)',
                            color: 'var(--status-in-stock, #10b981)',
                            border: '1px solid #a7f3d0',
                            fontSize: '13px',
                            fontWeight: 600,
                            cursor: 'pointer',
                            minHeight: '44px'
                          }}
                        >
                          Activate
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}

        {/* Pagination Bar */}
        <div
          style={{
            padding: '12px 16px',
            borderTop: '1px solid var(--color-border-subtle, #e2e8f0)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '13px',
            color: 'var(--color-text-secondary, #64748b)'
          }}
        >
          <div>
            Showing Page <strong>{page + 1}</strong> ({homes.length} workspaces loaded)
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0 || isLoading}
              aria-label="Previous Page"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                padding: '8px 12px',
                borderRadius: 'var(--radius-md, 10px)',
                border: '1px solid var(--color-border-subtle, #e2e8f0)',
                backgroundColor: 'var(--color-surface-subtle, #f1f5f9)',
                color: 'var(--color-text-primary, #0f172a)',
                cursor: page === 0 || isLoading ? 'not-allowed' : 'pointer',
                opacity: page === 0 ? 0.5 : 1,
                minHeight: '40px'
              }}
            >
              <ChevronLeft size={16} />
              <span>Previous</span>
            </button>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={homes.length < limit || isLoading}
              aria-label="Next Page"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                padding: '8px 12px',
                borderRadius: 'var(--radius-md, 10px)',
                border: '1px solid var(--color-border-subtle, #e2e8f0)',
                backgroundColor: 'var(--color-surface-subtle, #f1f5f9)',
                color: 'var(--color-text-primary, #0f172a)',
                cursor: homes.length < limit || isLoading ? 'not-allowed' : 'pointer',
                opacity: homes.length < limit ? 0.5 : 1,
                minHeight: '40px'
              }}
            >
              <span>Next</span>
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Confirmation Modal */}
      <AdminConfirmModal
        isOpen={modalConfig.isOpen}
        onClose={() => setModalConfig((prev) => ({ ...prev, isOpen: false }))}
        onConfirm={handleConfirmAction}
        title={modalConfig.title}
        description={modalConfig.description}
        confirmLabel={`Confirm ${modalConfig.action}`}
        confirmVariant={modalConfig.confirmVariant}
        isSubmitting={isSubmittingAction}
        error={actionError}
      />

      <style jsx>{`
        @media (max-width: 767.98px) {
          .ozhzo-admin-table-container {
            display: none !important;
          }
          .ozhzo-admin-cards-container {
            display: flex !important;
          }
        }
      `}</style>
    </div>
  );
}
