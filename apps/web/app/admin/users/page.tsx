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
  Home
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';
import { AdminBadge } from '../components/AdminBadge';
import { AdminUserListItem } from '../types';

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUserListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
            Search, inspect, and manage platform user credentials, roles, and status.
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
                    <th style={{ padding: '12px 16px' }}>User</th>
                    <th style={{ padding: '12px 16px' }}>Contact</th>
                    <th style={{ padding: '12px 16px' }}>Status</th>
                    <th style={{ padding: '12px 16px' }}>Platform Role</th>
                    <th style={{ padding: '12px 16px' }}>Workspaces</th>
                    <th style={{ padding: '12px 16px' }}>Joined Date</th>
                    <th style={{ padding: '12px 16px', textAlign: 'right' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr
                      key={u.id}
                      style={{
                        borderBottom: '1px solid var(--color-border-subtle, #e2e8f0)',
                        transition: 'background-color 0.15s ease'
                      }}
                    >
                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ fontWeight: 600, color: 'var(--color-text-primary, #0f172a)' }}>
                          {u.display_name}
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
                        <Link
                          href={`/admin/users/${u.id}`}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '8px 12px',
                            borderRadius: 'var(--radius-md, 10px)',
                            border: '1px solid var(--color-border-subtle, #e2e8f0)',
                            backgroundColor: 'var(--color-surface-subtle, #f1f5f9)',
                            fontSize: '12px',
                            fontWeight: 600,
                            color: 'var(--color-text-primary, #0f172a)',
                            minHeight: '36px'
                          }}
                        >
                          <span>Inspect</span>
                          <ExternalLink size={12} />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile Cards (Rendered on screen widths < 768px) */}
            <div className="ozhzo-admin-cards-container" style={{ display: 'none', padding: '12px', flexDirection: 'column', gap: '12px' }}>
              {users.map((u) => (
                <div
                  key={u.id}
                  style={{
                    padding: '16px',
                    borderRadius: 'var(--radius-md, 10px)',
                    border: '1px solid var(--color-border-subtle, #e2e8f0)',
                    backgroundColor: 'var(--color-surface-card, #ffffff)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '10px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)' }}>
                        {u.display_name}
                      </div>
                      <div style={{ fontSize: '13px', color: 'var(--color-text-secondary, #64748b)' }}>
                        {u.email || 'No email'}
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

                  <Link
                    href={`/admin/users/${u.id}`}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                      padding: '10px',
                      borderRadius: 'var(--radius-md, 10px)',
                      backgroundColor: 'var(--color-primary-900, #0f172a)',
                      color: 'var(--color-text-inverse, #ffffff)',
                      fontSize: '13px',
                      fontWeight: 600,
                      minHeight: '44px',
                      marginTop: '4px'
                    }}
                  >
                    <span>Inspect & Manage User</span>
                    <ExternalLink size={14} />
                  </Link>
                </div>
              ))}
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
