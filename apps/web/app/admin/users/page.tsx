'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Users,
  Search,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  ExternalLink,
  Home,
  UserCheck,
  UserX,
  PauseCircle,
  Trash2
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';
import { AdminBadge } from '../components/AdminBadge';
import { AdminConfirmModal } from '../components/AdminConfirmModal';
import { AdminUserListItem } from '../types';

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUserListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);

  // Selection & Bulk Actions
  const [selectedUserIds, setSelectedUserIds] = useState<Set<string>>(new Set());
  const [modalConfig, setModalConfig] = useState<{
    isOpen: boolean;
    title: string;
    description: string;
    action: 'ACTIVATE' | 'SUSPEND' | 'HOLD' | 'DELETE';
    targetUserIds: string[];
    confirmVariant: 'danger' | 'primary' | 'success';
  }>({
    isOpen: false,
    title: '',
    description: '',
    action: 'SUSPEND',
    targetUserIds: [],
    confirmVariant: 'danger'
  });
  const [isSubmittingAction, setIsSubmittingAction] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Filter & Search States
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'ACTIVE' | 'SUSPENDED'>('ALL');
  const [roleFilter, setRoleFilter] = useState<string>('ALL');
  const [sortBy, setSortBy] = useState<string>('created_at');
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');

  // Pagination
  const [page, setPage] = useState(0);
  const limit = 20;

  const fetchUsers = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (searchQuery.trim()) params.set('query', searchQuery.trim());
      if (statusFilter === 'ACTIVE') params.set('is_active', 'true');
      if (statusFilter === 'SUSPENDED') params.set('is_active', 'false');
      if (roleFilter !== 'ALL') params.set('system_role', roleFilter);
      params.set('sort_by', sortBy);
      params.set('sort_order', sortOrder);
      params.set('limit', String(limit));
      params.set('offset', String(page * limit));

      const res = await apiClient.get<AdminUserListItem[]>(`/admin/users?${params.toString()}`);
      setUsers(res || []);
      setSelectedUserIds(new Set()); // Reset selection on reload
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch platform users.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [page, statusFilter, roleFilter, sortBy, sortOrder]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    fetchUsers();
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
    if (selectedUserIds.size === users.length && users.length > 0) {
      setSelectedUserIds(new Set());
    } else {
      setSelectedUserIds(new Set(users.map((u) => u.id)));
    }
  };

  const toggleSelectUser = (userId: string) => {
    setSelectedUserIds((prev) => {
      const next = new Set(prev);
      if (next.has(userId)) {
        next.delete(userId);
      } else {
        next.add(userId);
      }
      return next;
    });
  };

  // Bulk / Row Action Triggers
  const openActionModal = (
    action: 'ACTIVATE' | 'SUSPEND' | 'HOLD' | 'DELETE',
    targetIds: string[]
  ) => {
    if (targetIds.length === 0) return;
    setActionError(null);

    const isBulk = targetIds.length > 1;
    const countLabel = isBulk ? `${targetIds.length} user accounts` : 'this user account';

    const configs = {
      ACTIVATE: {
        title: `Activate ${isBulk ? 'Selected Users' : 'User Account'}`,
        description: `Are you sure you want to restore full application access for ${countLabel}?`,
        confirmVariant: 'success' as const
      },
      SUSPEND: {
        title: `Suspend ${isBulk ? 'Selected Users' : 'User Account'}`,
        description: `This will immediately revoke authentication access and block all active sessions for ${countLabel}.`,
        confirmVariant: 'danger' as const
      },
      HOLD: {
        title: `Place on Administrative Hold`,
        description: `This will temporarily pause login and operations for ${countLabel} pending audit or review.`,
        confirmVariant: 'primary' as const
      },
      DELETE: {
        title: `Safely Deactivate & Delete`,
        description: `This will soft-delete and permanently deactivate ${countLabel}. Users who are active primary creators of Homes cannot be deleted until workspace ownership is transferred.`,
        confirmVariant: 'danger' as const
      }
    };

    const cfg = configs[action];
    setModalConfig({
      isOpen: true,
      title: cfg.title,
      description: cfg.description,
      action,
      targetUserIds: targetIds,
      confirmVariant: cfg.confirmVariant
    });
  };

  const handleConfirmAction = async (reason: string) => {
    setIsSubmittingAction(true);
    setActionError(null);
    try {
      if (modalConfig.targetUserIds.length > 1) {
        // Bulk API
        const res = await apiClient.post<any>('/admin/users/bulk-action', {
          user_ids: modalConfig.targetUserIds,
          action: modalConfig.action,
          reason: reason || undefined
        });
        setFeedbackMessage(res?.message || `Bulk ${modalConfig.action} executed successfully.`);
      } else {
        // Single user API
        const targetId = modalConfig.targetUserIds[0];
        let endpoint = `/admin/users/${targetId}/suspend`;
        if (modalConfig.action === 'ACTIVATE') endpoint = `/admin/users/${targetId}/reactivate`;
        if (modalConfig.action === 'HOLD') endpoint = `/admin/users/${targetId}/hold`;
        if (modalConfig.action === 'DELETE') endpoint = `/admin/users/${targetId}/delete`;

        const res = await apiClient.post<any>(endpoint, { reason: reason || undefined });
        setFeedbackMessage(res?.message || `User account updated successfully.`);
      }

      setModalConfig((prev) => ({ ...prev, isOpen: false }));
      setSelectedUserIds(new Set());
      fetchUsers();
    } catch (err: any) {
      setActionError(err?.message || `Failed to execute ${modalConfig.action}.`);
    } finally {
      setIsSubmittingAction(false);
    }
  };

  const isAllSelected = users.length > 0 && selectedUserIds.size === users.length;
  const isSomeSelected = selectedUserIds.size > 0 && selectedUserIds.size < users.length;

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
            User Accounts Management
          </h1>
          <p
            style={{
              fontSize: '14px',
              color: 'var(--color-text-secondary, #64748b)',
              marginTop: '4px'
            }}
          >
            Search, inspect, and manage platform user credentials, roles, and status across all tenants.
          </p>
        </div>

        <button
          onClick={fetchUsers}
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
      {selectedUserIds.size > 0 && (
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
            <Users size={18} />
            <span>Selected {selectedUserIds.size} {selectedUserIds.size === 1 ? 'user' : 'users'}</span>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={() => openActionModal('ACTIVATE', Array.from(selectedUserIds))}
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
              <UserCheck size={16} />
              <span>Activate</span>
            </button>

            <button
              onClick={() => openActionModal('SUSPEND', Array.from(selectedUserIds))}
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
              <UserX size={16} />
              <span>Suspend</span>
            </button>

            <button
              onClick={() => openActionModal('HOLD', Array.from(selectedUserIds))}
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
              onClick={() => openActionModal('DELETE', Array.from(selectedUserIds))}
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
              <Trash2 size={16} />
              <span>Delete</span>
            </button>

            <button
              onClick={() => setSelectedUserIds(new Set())}
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
          {/* Search Field */}
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
              placeholder="Search by email, phone, or name..."
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
            aria-label="Filter by account status"
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
            <option value="ACTIVE">Active Users</option>
            <option value="SUSPENDED">Suspended Users</option>
          </select>

          {/* System Role Filter */}
          <select
            value={roleFilter}
            onChange={(e) => {
              setRoleFilter(e.target.value);
              setPage(0);
            }}
            aria-label="Filter by platform role"
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
            <option value="ALL">All Roles</option>
            <option value="SUPER_ADMIN">Super Admin</option>
            <option value="PLATFORM_ADMIN">Platform Admin</option>
            <option value="SUPPORT_ADMIN">Support Admin</option>
            <option value="ANALYST">Analyst</option>
            <option value="USER">Standard User</option>
          </select>

          {/* Sort By */}
          <select
            value={`${sortBy}:${sortOrder}`}
            onChange={(e) => {
              const [by, ord] = e.target.value.split(':');
              setSortBy(by);
              setSortOrder(ord as any);
            }}
            aria-label="Sort users"
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
            <option value="created_at:desc">Newest First</option>
            <option value="created_at:asc">Oldest First</option>
            <option value="email:asc">Email (A-Z)</option>
            <option value="email:desc">Email (Z-A)</option>
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
            padding: '16px',
            backgroundColor: 'var(--status-overdue-bg, #fef2f2)',
            border: '1px solid #fecaca',
            borderRadius: 'var(--radius-md, 10px)',
            color: 'var(--status-overdue, #ef4444)',
            fontSize: '14px'
          }}
        >
          {error}
        </div>
      )}

      {/* User Table & Responsive Card Container */}
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
            <span style={{ fontSize: '14px', fontWeight: 500 }}>Loading platform users...</span>
          </div>
        ) : users.length === 0 ? (
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
            <Users size={36} color="var(--color-text-tertiary, #94a3b8)" />
            <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)' }}>
              No Users Found
            </div>
            <div style={{ fontSize: '14px', color: 'var(--color-text-secondary, #64748b)', maxWidth: '360px' }}>
              No platform users matched your current query or filter parameters.
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
                        aria-label="Select all users"
                        style={{ cursor: 'pointer', width: '16px', height: '16px' }}
                      />
                    </th>
                    <th style={{ padding: '12px 16px' }}>User</th>
                    <th style={{ padding: '12px 16px' }}>Contact</th>
                    <th style={{ padding: '12px 16px' }}>Status</th>
                    <th style={{ padding: '12px 16px' }}>Platform Role</th>
                    <th style={{ padding: '12px 16px' }}>Workspaces</th>
                    <th style={{ padding: '12px 16px' }}>Joined Date</th>
                    <th style={{ padding: '12px 16px', textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => {
                    const isSelected = selectedUserIds.has(u.id);
                    return (
                      <tr
                        key={u.id}
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
                            onChange={() => toggleSelectUser(u.id)}
                            aria-label={`Select user ${u.display_name}`}
                            style={{ cursor: 'pointer', width: '16px', height: '16px' }}
                          />
                        </td>

                        <td style={{ padding: '12px 16px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{ fontWeight: 600, color: 'var(--color-text-primary, #0f172a)' }}>
                              {u.display_name}
                            </span>
                            {(u.email?.includes('example.com') ||
                              u.email?.includes('demo_') ||
                              u.email?.includes('audit_user') ||
                              u.email?.includes('bulk') ||
                              u.email?.includes('prodtest') ||
                              u.display_name?.toLowerCase().includes('demo') ||
                              u.display_name?.toLowerCase().includes('auditor') ||
                              u.display_name?.toLowerCase().includes('tester')) && (
                              <AdminBadge variant="warning">DEMO / TEST</AdminBadge>
                            )}
                          </div>
                          <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                            {u.email || 'No email'}
                          </div>
                        </td>

                        <td style={{ padding: '12px 16px', color: 'var(--color-text-secondary, #64748b)' }}>
                          <div>{u.phone_number || '—'}</div>
                          <div style={{ fontSize: '11px', display: 'flex', gap: '4px', marginTop: '2px' }}>
                            {u.is_verified && <AdminBadge variant="success">Email Verified</AdminBadge>}
                            {u.mobile_verified && <AdminBadge variant="success">SMS Verified</AdminBadge>}
                          </div>
                        </td>

                        <td style={{ padding: '12px 16px' }}>
                          {u.is_active ? (
                            <AdminBadge variant="success">Active</AdminBadge>
                          ) : (
                            <AdminBadge variant="danger">Suspended</AdminBadge>
                          )}
                        </td>

                        <td style={{ padding: '12px 16px' }}>
                          {u.is_super_admin || u.system_role === 'SUPER_ADMIN' ? (
                            <AdminBadge variant="purple">SUPER ADMIN</AdminBadge>
                          ) : (
                            <AdminBadge variant="neutral">{u.system_role || 'USER'}</AdminBadge>
                          )}
                        </td>

                        <td style={{ padding: '12px 16px', color: 'var(--color-text-primary, #0f172a)' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <Home size={14} color="var(--color-text-secondary, #64748b)" />
                            <span>{u.homes_count} {u.homes_count === 1 ? 'Home' : 'Homes'}</span>
                          </div>
                        </td>

                        <td style={{ padding: '12px 16px', color: 'var(--color-text-secondary, #64748b)' }}>
                          {formatDate(u.created_at)}
                        </td>

                        <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                            <Link
                              href={`/admin/users/${u.id}`}
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

                            {u.is_active ? (
                              <button
                                onClick={() => openActionModal('SUSPEND', [u.id])}
                                title="Suspend User"
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
                                onClick={() => openActionModal('ACTIVATE', [u.id])}
                                title="Activate User"
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

            {/* Mobile Cards (Rendered on screen widths < 768px) */}
            <div className="ozhzo-admin-cards-container" style={{ display: 'none', padding: '12px', flexDirection: 'column', gap: '12px' }}>
              {users.map((u) => {
                const isSelected = selectedUserIds.has(u.id);
                return (
                  <div
                    key={u.id}
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
                          onChange={() => toggleSelectUser(u.id)}
                          aria-label={`Select user ${u.display_name}`}
                          style={{ cursor: 'pointer', width: '18px', height: '18px' }}
                        />
                        <div>
                          <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)' }}>
                            {u.display_name}
                          </div>
                          <div style={{ fontSize: '13px', color: 'var(--color-text-secondary, #64748b)' }}>
                            {u.email || 'No email'}
                          </div>
                        </div>
                      </div>
                      {u.is_active ? (
                        <AdminBadge variant="success">Active</AdminBadge>
                      ) : (
                        <AdminBadge variant="danger">Suspended</AdminBadge>
                      )}
                    </div>

                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', fontSize: '12px' }}>
                      {u.is_super_admin && <AdminBadge variant="purple">SUPER ADMIN</AdminBadge>}
                      <AdminBadge variant="neutral">{u.system_role}</AdminBadge>
                      <AdminBadge variant="info">{u.homes_count} Workspaces</AdminBadge>
                    </div>

                    <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                      Joined: {formatDate(u.created_at)}
                    </div>

                    <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                      <Link
                        href={`/admin/users/${u.id}`}
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
                        <span>Inspect User</span>
                        <ExternalLink size={14} />
                      </Link>

                      {u.is_active ? (
                        <button
                          onClick={() => openActionModal('SUSPEND', [u.id])}
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
                          onClick={() => openActionModal('ACTIVATE', [u.id])}
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
            Showing Page <strong>{page + 1}</strong> ({users.length} items loaded)
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
              disabled={users.length < limit || isLoading}
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
                cursor: users.length < limit || isLoading ? 'not-allowed' : 'pointer',
                opacity: users.length < limit ? 0.5 : 1,
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
