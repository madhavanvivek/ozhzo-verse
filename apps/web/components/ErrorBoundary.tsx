'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertCircle, RefreshCw, Home } from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught UI error caught by ErrorBoundary:', error, errorInfo);
  }

  private handleReload = () => {
    window.location.reload();
  };

  private handleGoHome = () => {
    window.location.href = '/dashboard';
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div
          role="alert"
          style={{
            minHeight: '300px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '32px 16px',
            textAlign: 'center',
            backgroundColor: 'var(--color-surface-card)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--color-border-subtle)',
            margin: '24px 0',
          }}
        >
          <div
            style={{
              width: '48px',
              height: '48px',
              borderRadius: '50%',
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ef4444',
              marginBottom: '16px',
            }}
          >
            <AlertCircle size={24} />
          </div>

          <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--color-primary-900)', margin: '0 0 8px 0' }}>
            Something went wrong
          </h3>

          <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)', maxWidth: '400px', margin: '0 0 20px 0' }}>
            An unexpected interface error occurred. Your household data is safe and untouched.
          </p>

          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', justifyContent: 'center' }}>
            <Button variant="primary" size="sm" onClick={this.handleReload}>
              <RefreshCw size={14} />
              <span>Reload Page</span>
            </Button>
            <Button variant="secondary" size="sm" onClick={this.handleGoHome}>
              <Home size={14} />
              <span>Go to Dashboard</span>
            </Button>

          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
