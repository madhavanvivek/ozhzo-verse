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
  ChevronRight
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';
import { AdminBadge } from '../components/AdminBadge';
import { AdminHomeListItem } from '../types';

export default function AdminHomesPage() {
  const [homes, setHomes] = useState<AdminHomeListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Search & Filter
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'ACTIVE' | 'SUSPENDED'>('ALL');

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
            Inspect tenant household workspaces, membership density, and subscription statuses.
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
              placeholder="Search by workspace name..."
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
            <option value="ALL">All Workspaces</option>
            <option value="ACTIVE">Active Workspaces</option>
            <option value="SUSPENDED">Suspended Workspaces</option>
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

      {/* Error / Failure State with Retry Button */}
      {error && !isLoading && (
        <div
          style={{
            padding: '24px',
            backgroundColor: 'var(--status-overdue-bg, #fef2f2)',
            border: '1px solid #fecaca',
            borderRadius: 'var(--radius-lg, 16px)',
            color: 'var(--status-overdue, #ef4444)',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px'
          }}
        >
          <div style={{ fontWeight: 700, fontSize: '15px' }}>
            {error.includes('403') || error.toLowerCase().includes('permission') || error.toLowerCase().includes('admin')
              ? 'Platform administrator access required'
              : 'Unable to load household workspaces'}
          </div>
          <div style={{ fontSize: '13px', color: '#991b1b', lineHeight: '1.4' }}>
            {error}
          </div>
          <div>
            <button
              onClick={fetchHomes}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: 'var(--radius-md, 10px)',
                backgroundColor: 'var(--color-primary-900, #0f172a)',
                color: '#ffffff',
                border: 'none',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              <RefreshCw size={14} />
              <span>Retry</span>
            </button>
          </div>
        </div>
      )}

      {/* Table & Mobile Cards Container */}
      {!error && (
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
              <RefreshCw size={24} className="animate-spin" color="var(--status-in-stock, #10b981)" />
              <span style={{ fontSize: '14px', fontWeight: 500 }}>Loading households...</span>
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
                No household workspaces found.
              </div>
              <div style={{ fontSize: '14px', color: 'var(--color-text-secondary, #64748b)' }}>
                No household workspaces matched your current search or filter criteria.
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
                    <th style={{ padding: '12px 16px' }}>Workspace</th>
                    <th style={{ padding: '12px 16px' }}>Creator / Owner</th>
                    <th style={{ padding: '12px 16px' }}>Members</th>
                    <th style={{ padding: '12px 16px' }}>Status</th>
                    <th style={{ padding: '12px 16px' }}>Subscription</th>
                    <th style={{ padding: '12px 16px' }}>Created Date</th>
                    <th style={{ padding: '12px 16px', textAlign: 'right' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {homes.map((h) => (
                    <tr
                      key={h.id}
                      style={{
                        borderBottom: '1px solid var(--color-border-subtle, #e2e8f0)',
                        transition: 'background-color 0.15s ease'
                      }}
                    >
                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ fontWeight: 700, color: 'var(--color-text-primary, #0f172a)' }}>
                          {h.name}
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--color-text-secondary, #64748b)' }}>
                          Currency: {h.currency}
                        </div>
                      </td>

                      <td style={{ padding: '12px 16px', color: 'var(--color-text-secondary, #64748b)' }}>
                        <div style={{ fontWeight: 600, color: 'var(--color-text-primary, #0f172a)' }}>
                          {h.created_by_name || 'Home Creator'}
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--color-text-secondary, #64748b)' }}>
                          {h.created_by_email || '—'}
                        </div>
                      </td>

                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <Users size={14} color="var(--color-text-secondary, #64748b)" />
                          <span style={{ fontWeight: 600, color: 'var(--color-text-primary, #0f172a)' }}>
                            {h.members_count}
                          </span>
                        </div>
                      </td>

                      <td style={{ padding: '12px 16px' }}>
                        {h.status === 'ACTIVE' ? (
                          <AdminBadge variant="success">Active</AdminBadge>
                        ) : (
                          <AdminBadge variant="danger">Suspended</AdminBadge>
                        )}
                      </td>

                      <td style={{ padding: '12px 16px' }}>
                        <AdminBadge
                          variant={
                            h.subscription_status === 'ACTIVE'
                              ? 'success'
                              : h.subscription_status === 'TRIALING'
                              ? 'info'
                              : 'neutral'
                          }
                        >
                          {h.subscription_status}
                        </AdminBadge>
                      </td>

                      <td style={{ padding: '12px 16px', color: 'var(--color-text-secondary, #64748b)' }}>
                        {formatDate(h.created_at)}
                      </td>

                      <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                        <Link
                          href={`/admin/homes/${h.id}`}
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

            {/* Mobile Cards */}
            <div className="ozhzo-admin-cards-container" style={{ display: 'none', padding: '12px', flexDirection: 'column', gap: '12px' }}>
              {homes.map((h) => (
                <div
                  key={h.id}
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
                      <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)' }}>
                        {h.name}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                        Creator: {h.created_by_name ? `${h.created_by_name} (${h.created_by_email || 'No email'})` : (h.created_by_email || '—')}
                      </div>
                    </div>
                    {h.status === 'ACTIVE' ? (
                      <AdminBadge variant="success">Active</AdminBadge>
                    ) : (
                      <AdminBadge variant="danger">Suspended</AdminBadge>
                    )}
                  </div>

                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', fontSize: '12px' }}>
                    <AdminBadge variant="info">{h.members_count} Members</AdminBadge>
                    <AdminBadge variant="neutral">{h.currency}</AdminBadge>
                    <AdminBadge variant="purple">{h.subscription_status}</AdminBadge>
                  </div>

                  <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                    Created: {formatDate(h.created_at)}
                  </div>

                  <Link
                    href={`/admin/homes/${h.id}`}
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
                    <span>Inspect Household Details</span>
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
      )}

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
