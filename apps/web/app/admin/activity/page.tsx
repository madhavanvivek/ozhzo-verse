'use client';

import React, { useState, useEffect } from 'react';
import {
  Activity,
  Search,
  RefreshCw,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';
import { AdminBadge } from '../components/AdminBadge';
import { AdminActivityItem } from '../types';

export default function AdminActivityPage() {
  const [logs, setLogs] = useState<AdminActivityItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [entityTypeFilter, setEntityTypeFilter] = useState<string>('ALL');
  const [actionQuery, setActionQuery] = useState<string>('');

  // Pagination
  const [page, setPage] = useState(0);
  const limit = 25;

  const fetchActivity = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (entityTypeFilter !== 'ALL') params.set('entity_type', entityTypeFilter);
      if (actionQuery.trim()) params.set('action', actionQuery.trim());
      params.set('limit', String(limit));
      params.set('offset', String(page * limit));

      const res = await apiClient.get<AdminActivityItem[]>(`/admin/activity?${params.toString()}`);
      setLogs(res || []);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch platform audit logs.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchActivity();
  }, [page, entityTypeFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    fetchActivity();
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return '—';
    try {
      return new Date(dateStr).toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
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
            Platform Activity & Audit Trail
          </h1>
          <p
            style={{
              fontSize: '14px',
              color: 'var(--color-text-secondary, #64748b)',
              marginTop: '4px'
            }}
          >
            Authoritative, immutable audit records of administrative operations, role modifications, and status changes.
          </p>
        </div>

        <button
          onClick={fetchActivity}
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
          <span>Refresh Logs</span>
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
          {/* Action Search */}
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
              placeholder="Search by action (e.g. SUSPEND_USER, CREATE_COUPON)..."
              value={actionQuery}
              onChange={(e) => setActionQuery(e.target.value)}
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

          {/* Entity Type Filter */}
          <select
            value={entityTypeFilter}
            onChange={(e) => {
              setEntityTypeFilter(e.target.value);
              setPage(0);
            }}
            aria-label="Filter by entity type"
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
            <option value="ALL">All Entity Types</option>
            <option value="USER">User Operations</option>
            <option value="HOME">Workspace Operations</option>
            <option value="PLAN">Plan Operations</option>
            <option value="PRICE">Price Operations</option>
            <option value="PROMOTION">Promotions</option>
            <option value="COUPON">Coupon Operations</option>
            <option value="DIRECT_GRANT">Direct Grants</option>
            <option value="CAMPAIGN">Campaigns</option>
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

      {/* Table & Mobile Cards */}
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
            <span style={{ fontSize: '14px', fontWeight: 500 }}>Loading activity audit records...</span>
          </div>
        ) : logs.length === 0 ? (
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
            <Activity size={36} color="var(--color-text-tertiary, #94a3b8)" />
            <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)' }}>
              No Audit Logs Found
            </div>
            <div style={{ fontSize: '14px', color: 'var(--color-text-secondary, #64748b)' }}>
              No platform activity matched your current search filters.
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
                    <th style={{ padding: '12px 16px' }}>Timestamp</th>
                    <th style={{ padding: '12px 16px' }}>Actor</th>
                    <th style={{ padding: '12px 16px' }}>Entity</th>
                    <th style={{ padding: '12px 16px' }}>Action</th>
                    <th style={{ padding: '12px 16px' }}>Target ID</th>
                    <th style={{ padding: '12px 16px' }}>Reason / Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr
                      key={log.id}
                      style={{
                        borderBottom: '1px solid var(--color-border-subtle, #e2e8f0)',
                        transition: 'background-color 0.15s ease'
                      }}
                    >
                      <td style={{ padding: '12px 16px', color: 'var(--color-text-secondary, #64748b)', whiteSpace: 'nowrap' }}>
                        {formatDate(log.created_at)}
                      </td>

                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ fontWeight: 600, color: 'var(--color-text-primary, #0f172a)' }}>
                          {log.performed_by_email || 'System Super Admin'}
                        </div>
                      </td>

                      <td style={{ padding: '12px 16px' }}>
                        <AdminBadge
                          variant={
                            log.entity_type === 'USER'
                              ? 'info'
                              : log.entity_type === 'HOME'
                              ? 'success'
                              : log.entity_type === 'COUPON'
                              ? 'purple'
                              : 'neutral'
                          }
                        >
                          {log.entity_type}
                        </AdminBadge>
                      </td>

                      <td style={{ padding: '12px 16px' }}>
                        <span style={{ fontWeight: 700, color: 'var(--color-text-primary, #0f172a)' }}>
                          {log.action}
                        </span>
                      </td>

                      <td style={{ padding: '12px 16px', color: 'var(--color-text-secondary, #64748b)', fontFamily: 'monospace', fontSize: '11px' }}>
                        {log.entity_id ? log.entity_id.slice(0, 12) + '...' : '—'}
                      </td>

                      <td style={{ padding: '12px 16px', color: 'var(--color-text-secondary, #64748b)', maxWidth: '300px' }}>
                        {log.reason || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile Cards */}
            <div className="ozhzo-admin-cards-container" style={{ display: 'none', padding: '12px', flexDirection: 'column', gap: '12px' }}>
              {logs.map((log) => (
                <div
                  key={log.id}
                  style={{
                    padding: '16px',
                    borderRadius: 'var(--radius-md, 10px)',
                    border: '1px solid var(--color-border-subtle, #e2e8f0)',
                    backgroundColor: 'var(--color-surface-card, #ffffff)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <span style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-text-primary, #0f172a)' }}>
                      {log.action}
                    </span>
                    <AdminBadge
                      variant={
                        log.entity_type === 'USER'
                          ? 'info'
                          : log.entity_type === 'HOME'
                          ? 'success'
                          : 'purple'
                      }
                    >
                      {log.entity_type}
                    </AdminBadge>
                  </div>

                  <div style={{ fontSize: '12px', color: 'var(--color-text-secondary, #64748b)' }}>
                    Actor: <strong>{log.performed_by_email || 'System'}</strong>
                  </div>

                  {log.reason && (
                    <div style={{ fontSize: '12px', color: 'var(--color-text-primary, #0f172a)' }}>
                      Reason: {log.reason}
                    </div>
                  )}

                  <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary, #94a3b8)', marginTop: '4px' }}>
                    {formatDate(log.created_at)} | Target: <code>{log.entity_id ? log.entity_id.slice(0, 8) : '—'}</code>
                  </div>
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
            Page <strong>{page + 1}</strong> ({logs.length} logs loaded)
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
              disabled={logs.length < limit || isLoading}
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
                cursor: logs.length < limit || isLoading ? 'not-allowed' : 'pointer',
                opacity: logs.length < limit ? 0.5 : 1,
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
