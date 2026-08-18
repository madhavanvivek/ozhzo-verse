'use client';

import React, { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle, X } from 'lucide-react';

interface AdminConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (reason: string) => Promise<void> | void;
  title: string;
  description: string;
  confirmLabel?: string;
  confirmVariant?: 'danger' | 'primary' | 'success';
  requireReason?: boolean;
  placeholderReason?: string;
  isSubmitting?: boolean;
  error?: string | null;
}

export function AdminConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  description,
  confirmLabel = 'Confirm',
  confirmVariant = 'danger',
  requireReason = true,
  placeholderReason = 'Enter reason for this administrative action...',
  isSubmitting = false,
  error = null
}: AdminConfirmModalProps) {
  const [reason, setReason] = useState('');

  useEffect(() => {
    if (isOpen) {
      setReason('');
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen && !isSubmitting) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isSubmitting, onClose]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (requireReason && !reason.trim()) return;
    onConfirm(reason.trim());
  };

  const variantColors = {
    danger: {
      btnBg: 'var(--status-overdue, #ef4444)',
      btnHover: '#dc2626',
      iconBg: 'var(--status-overdue-bg, #fef2f2)',
      iconColor: 'var(--status-overdue, #ef4444)'
    },
    primary: {
      btnBg: 'var(--color-primary-900, #0f172a)',
      btnHover: 'var(--color-primary-700, #1e293b)',
      iconBg: 'var(--color-surface-subtle, #f1f5f9)',
      iconColor: 'var(--color-primary-900, #0f172a)'
    },
    success: {
      btnBg: 'var(--status-in-stock, #10b981)',
      btnHover: '#059669',
      iconBg: 'var(--status-in-stock-bg, #ecfdf5)',
      iconColor: 'var(--status-in-stock, #10b981)'
    }
  };

  const styleConfig = variantColors[confirmVariant];

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.6)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px',
        zIndex: 9999
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !isSubmitting) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        style={{
          backgroundColor: 'var(--color-surface-card, #ffffff)',
          borderRadius: 'var(--radius-lg, 16px)',
          boxShadow: 'var(--shadow-modal, 0 20px 25px -5px rgba(15, 23, 42, 0.12))',
          border: '1px solid var(--color-border-subtle, #e2e8f0)',
          maxWidth: '480px',
          width: '100%',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          position: 'relative'
        }}
      >
        <button
          type="button"
          onClick={onClose}
          disabled={isSubmitting}
          aria-label="Close modal"
          style={{
            position: 'absolute',
            top: '16px',
            right: '16px',
            background: 'none',
            border: 'none',
            cursor: isSubmitting ? 'not-allowed' : 'pointer',
            padding: '8px',
            minHeight: '44px',
            minWidth: '44px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--color-text-secondary, #64748b)',
            borderRadius: 'var(--radius-sm, 6px)'
          }}
        >
          <X size={20} />
        </button>

        <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: 'var(--radius-md, 10px)',
              backgroundColor: styleConfig.iconBg,
              color: styleConfig.iconColor,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}
          >
            {confirmVariant === 'success' ? <CheckCircle size={22} /> : <AlertTriangle size={22} />}
          </div>
          <div>
            <h3
              id="modal-title"
              style={{
                fontSize: '18px',
                fontWeight: 700,
                color: 'var(--color-text-primary, #0f172a)',
                margin: 0,
                lineHeight: 1.3
              }}
            >
              {title}
            </h3>
            <p
              style={{
                fontSize: '14px',
                color: 'var(--color-text-secondary, #64748b)',
                marginTop: '6px',
                lineHeight: 1.5
              }}
            >
              {description}
            </p>
          </div>
        </div>

        {error && (
          <div
            style={{
              padding: '12px',
              backgroundColor: 'var(--status-overdue-bg, #fef2f2)',
              border: '1px solid #fecaca',
              borderRadius: 'var(--radius-md, 10px)',
              color: 'var(--status-overdue, #ef4444)',
              fontSize: '13px',
              lineHeight: 1.4
            }}
          >
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {requireReason && (
            <div>
              <label
                htmlFor="action-reason-input"
                style={{
                  display: 'block',
                  fontSize: '13px',
                  fontWeight: 600,
                  color: 'var(--color-text-primary, #0f172a)',
                  marginBottom: '6px'
                }}
              >
                Administrative Reason
              </label>
              <textarea
                id="action-reason-input"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder={placeholderReason}
                required={requireReason}
                rows={3}
                disabled={isSubmitting}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  borderRadius: 'var(--radius-md, 10px)',
                  border: '1px solid var(--color-border-subtle, #e2e8f0)',
                  backgroundColor: 'var(--color-surface-subtle, #f1f5f9)',
                  fontSize: '14px',
                  color: 'var(--color-text-primary, #0f172a)',
                  resize: 'vertical',
                  outline: 'none',
                  fontFamily: 'inherit'
                }}
              />
            </div>
          )}

          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              style={{
                minHeight: '44px',
                padding: '10px 18px',
                borderRadius: 'var(--radius-md, 10px)',
                border: '1px solid var(--color-border-subtle, #e2e8f0)',
                backgroundColor: 'transparent',
                color: 'var(--color-text-primary, #0f172a)',
                fontSize: '14px',
                fontWeight: 600,
                cursor: isSubmitting ? 'not-allowed' : 'pointer'
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || (requireReason && !reason.trim())}
              style={{
                minHeight: '44px',
                padding: '10px 20px',
                borderRadius: 'var(--radius-md, 10px)',
                border: 'none',
                backgroundColor: styleConfig.btnBg,
                color: 'var(--color-text-inverse, #ffffff)',
                fontSize: '14px',
                fontWeight: 600,
                cursor: isSubmitting || (requireReason && !reason.trim()) ? 'not-allowed' : 'pointer',
                opacity: isSubmitting || (requireReason && !reason.trim()) ? 0.6 : 1,
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              {isSubmitting ? 'Processing...' : confirmLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
