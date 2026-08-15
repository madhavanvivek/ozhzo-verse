'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Search,
  Package,
  ShoppingCart,
  CheckSquare,
  Receipt,
  Calendar,
  X,
  ArrowRight,

} from 'lucide-react';
import { Badge } from '@/components/ui/Badge';

interface SearchResult {
  id: string;
  domain: 'INVENTORY' | 'SHOPPING' | 'TASK' | 'BILL' | 'EVENT';
  title: string;
  subtitle?: string | null;
  status?: string | null;
  url: string;
}

interface UnifiedSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function UnifiedSearchModal({ isOpen, onClose }: UnifiedSearchModalProps) {
  const [query, setQuery] = useState('');
  const router = useRouter();

  const [results] = useState<SearchResult[]>([
    { id: '1', domain: 'INVENTORY', title: 'Extra Virgin Olive Oil', subtitle: '0 bottles • Pantry Shelf 2', status: 'OUT_OF_STOCK', url: '/inventory' },
    { id: '2', domain: 'SHOPPING', title: 'Extra Virgin Olive Oil', subtitle: '1 bottles • Priority: HIGH', status: 'To Buy', url: '/shopping' },
    { id: '3', domain: 'TASK', title: 'Mop kitchen floor', subtitle: 'Priority: HIGH • Due Today', status: 'TODO', url: '/tasks' },
    { id: '4', domain: 'BILL', title: 'Fiber Internet (1Gbps)', subtitle: 'Utilities • USD 79.99 due Aug 28', status: 'UNPAID', url: '/bills' },
    { id: '5', domain: 'EVENT', title: 'Family Dinner & Game Night', subtitle: 'Fri, Aug 14 at 07:00 PM • Dining Room', status: 'SCHEDULED', url: '/calendar' },
  ]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        // Toggle search
      }
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!isOpen) return null;

  const filtered = query.trim()
    ? results.filter(r => r.title.toLowerCase().includes(query.toLowerCase()) || (r.subtitle && r.subtitle.toLowerCase().includes(query.toLowerCase())))
    : results;

  const getDomainIcon = (domain: string) => {
    switch (domain) {
      case 'INVENTORY':
        return <Package size={16} color="var(--color-primary-900)" />;
      case 'SHOPPING':
        return <ShoppingCart size={16} color="var(--status-in-stock)" />;
      case 'TASK':
        return <CheckSquare size={16} color="var(--color-accent-warm)" />;
      case 'BILL':
        return <Receipt size={16} color="var(--status-overdue)" />;
      case 'EVENT':
        return <Calendar size={16} color="var(--color-primary-700)" />;
      default:
        return <Search size={16} />;
    }
  };

  const handleSelect = (url: string) => {
    router.push(url);
    onClose();
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        backdropFilter: 'blur(4px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        paddingTop: '10vh',
        paddingLeft: '16px',
        paddingRight: '16px'
      }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '100%',
          maxWidth: '640px',
          backgroundColor: 'var(--color-surface-card)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
          border: '1px solid var(--color-border-strong)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        {/* Search Header */}
        <div style={{ display: 'flex', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid var(--color-border-subtle)', gap: '12px' }}>
          <Search size={20} color="var(--color-text-secondary)" />
          <input
            type="text"
            placeholder="Search inventory, chores, shopping, bills, events..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
            style={{
              flex: 1,
              border: 'none',
              outline: 'none',
              backgroundColor: 'transparent',
              fontSize: '16px',
              color: 'var(--color-text-primary)'
            }}
          />
          <button
            onClick={onClose}
            style={{ border: 'none', background: 'none', cursor: 'pointer', color: 'var(--color-text-tertiary)', padding: '4px' }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Results List */}
        <div style={{ maxHeight: '420px', overflowY: 'auto', padding: '8px' }}>
          {filtered.length === 0 ? (
            <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--color-text-secondary)' }}>
              <p style={{ fontSize: '14px', fontWeight: 600 }}>No results found for &ldquo;{query}&rdquo;</p>
              <p style={{ fontSize: '12px', marginTop: '4px' }}>Try searching another supply, chore, bill, or event name.</p>
            </div>
          ) : (
            filtered.map((item) => (
              <div
                key={`${item.domain}-${item.id}`}
                onClick={() => handleSelect(item.url)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px 16px',
                  borderRadius: 'var(--radius-md)',
                  cursor: 'pointer',
                  transition: 'background-color 0.15s ease'
                }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--color-surface-subtle)'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ width: '32px', height: '32px', borderRadius: '6px', backgroundColor: 'var(--color-surface-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    {getDomainIcon(item.domain)}
                  </div>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                        {item.title}
                      </span>
                      <span style={{ fontSize: '10px', fontWeight: 700, padding: '2px 6px', borderRadius: '4px', backgroundColor: 'var(--color-surface-subtle)', color: 'var(--color-text-tertiary)' }}>
                        {item.domain}
                      </span>
                    </div>
                    {item.subtitle && (
                      <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
                        {item.subtitle}
                      </div>
                    )}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {item.status && (
                    <Badge variant={item.status === 'LOW_STOCK' || item.status === 'OUT_OF_STOCK' || item.status === 'UNPAID' ? 'overdue' : 'neutral'}>
                      {item.status}
                    </Badge>
                  )}
                  <ArrowRight size={14} color="var(--color-text-tertiary)" />
                </div>
              </div>
            ))
          )}
        </div>

        {/* Search Footer */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 16px', borderTop: '1px solid var(--color-border-subtle)', backgroundColor: 'var(--color-surface-subtle)', fontSize: '11px', color: 'var(--color-text-tertiary)' }}>
          <span>Search strictly scoped to your active household.</span>
          <span>ESC to close</span>
        </div>
      </div>
    </div>
  );
}
