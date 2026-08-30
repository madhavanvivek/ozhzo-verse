'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui/Card';
import {
  MapPin,
  Sparkles,
  AlertTriangle,
  Calendar as CalendarIcon,
  CheckCircle2,
  Receipt,
  ShoppingCart,
  Package
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

interface TodayTimelineItem {
  id: string;
  source_type: 'EVENT' | 'TASK' | 'BILL' | 'PURCHASE' | 'INVENTORY' | 'ASSET';
  source_id: string;
  title: string;
  start: string;
  end: string;
  all_day: boolean;
  priority: string;
  status: string;
  navigation_target: string;
  category_name?: string | null;
  location?: string | null;
  meta_info?: Record<string, any>;
}

interface TodayResponse {
  date: string;
  timezone: string;
  summary: {
    total_items: number;
    events_count: number;
    tasks_count: number;
    bills_count: number;
    purchase_urgent_count: number;
    inventory_alerts_count: number;
  };
  timeline: TodayTimelineItem[];
  attention_alerts: TodayTimelineItem[];
}

export default function TodayPage() {
  const [data, setData] = useState<TodayResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadTodayData = async () => {
      setIsLoading(true);
      try {
        const initialHomeId = apiClient.getActiveHomeId();
        const [homeIdRes, initialDataRes] = await Promise.allSettled([
          apiClient.getValidActiveHome(),
          initialHomeId ? apiClient.get<TodayResponse>(`/homes/${initialHomeId}/today`) : Promise.resolve(null)
        ]);

        let finalHomeId = initialHomeId;
        if (homeIdRes.status === 'fulfilled' && homeIdRes.value) {
          finalHomeId = homeIdRes.value;
        }

        if (initialDataRes.status === 'fulfilled' && initialDataRes.value) {
          setData(initialDataRes.value);
        } else if (finalHomeId && finalHomeId !== initialHomeId) {
          const res = await apiClient.get<TodayResponse>(`/homes/${finalHomeId}/today`);
          setData(res);
        } else {
          setData(null);
        }
      } catch (err) {
        console.error('Failed to load today data:', err);
        setData(null);
      } finally {
        setIsLoading(false);
      }
    };

    loadTodayData();
  }, []);

  const timeline = data?.timeline || [];
  const alerts = data?.attention_alerts || [];

  const getSourceIcon = (type: string) => {
    switch (type) {
      case 'EVENT':
        return <CalendarIcon size={16} color="var(--color-primary-900)" />;
      case 'TASK':
        return <CheckCircle2 size={16} color="var(--status-in-stock)" />;
      case 'BILL':
        return <Receipt size={16} color="var(--status-overdue)" />;
      case 'PURCHASE':
        return <ShoppingCart size={16} color="var(--status-low-stock)" />;
      case 'INVENTORY':
      case 'ASSET':
      default:
        return <Package size={16} color="var(--color-text-secondary)" />;
    }
  };

  const getBorderColor = (type: string) => {
    switch (type) {
      case 'EVENT':
        return 'var(--color-primary-900)';
      case 'TASK':
        return 'var(--status-in-stock)';
      case 'BILL':
        return 'var(--status-overdue)';
      case 'PURCHASE':
        return 'var(--status-low-stock)';
      default:
        return 'var(--color-border-subtle)';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '900px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-primary-900)' }}>
            Today's Household Agenda
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)' }}>
            Everything happening, due, or requiring action in your home today.
          </p>
        </div>
      </div>

      {/* Attention Alerts */}
      {alerts.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--status-low-stock)', letterSpacing: '0.05em' }}>
            Needs Attention Today ({alerts.length})
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
            {alerts.map((a) => (
              <Card key={a.id} style={{ padding: '14px 16px', borderLeft: '4px solid var(--status-low-stock)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <AlertTriangle size={18} color="var(--status-low-stock)" />
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '14px', color: 'var(--color-text-primary)' }}>{a.title}</div>
                    {a.location && <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>{a.location}</div>}
                  </div>
                </div>
                <Link href={a.navigation_target || '/dashboard'} style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-primary-900)', textDecoration: 'none' }}>
                  View ➔
                </Link>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Timeline Stream */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-text-secondary)', letterSpacing: '0.05em' }}>
          Chronological Schedule
        </div>

        {isLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {[1, 2, 3].map((i) => (
              <div key={i} style={{ height: '64px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: 'var(--radius-md)', animation: 'pulse 1.5s infinite' }} />
            ))}
          </div>
        ) : timeline.length === 0 ? (
          <Card style={{ padding: 'var(--space-8)', textAlign: 'center' }}>
            <Sparkles size={36} color="var(--status-in-stock)" style={{ margin: '0 auto 10px' }} />
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-primary-900)' }}>
              No items scheduled for today
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
              Your household agenda is completely clear today!
            </p>
          </Card>
        ) : (
          timeline.map((item) => (
            <Card
              key={item.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '16px 20px',
                borderLeft: `4px solid ${getBorderColor(item.source_type)}`
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <div style={{ minWidth: '75px', textAlign: 'center', padding: '6px 8px', borderRadius: 'var(--radius-md)', background: 'var(--color-surface-subtle)', fontWeight: 700, fontSize: '12px' }}>
                  {item.all_day ? 'All Day' : new Date(item.start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>

                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                      {getSourceIcon(item.source_type)}
                    </div>
                    <span style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-text-primary)' }}>{item.title}</span>
                  </div>
                  {item.location && (
                    <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <MapPin size={12} />
                      <span>{item.location}</span>
                    </div>
                  )}
                </div>
              </div>

              <Link href={item.navigation_target || '/dashboard'} style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-primary-900)', textDecoration: 'none' }}>
                Open ➔
              </Link>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
