'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui/Card';
import {
  MapPin,

} from 'lucide-react';

export default function TodayPage() {
  const [items] = useState([
    {
      id: 'evt-1',
      source_type: 'EVENT',
      title: "Grandmother's 80th Birthday Celebration",
      time: 'All Day',
      location: 'Family Home',
      status: 'CONFIRMED',
      link: '/calendar/evt-1'
    },
    {
      id: 'evt-2',
      source_type: 'EVENT',
      title: 'Doctor Appointment — City Clinic (Karthika)',
      time: '10:30 AM',
      location: 'City Clinic Room 4',
      status: 'CONFIRMED',
      link: '/calendar/evt-2'
    },
    {
      id: 'task-1',
      source_type: 'TASK',
      title: 'Replace RO Water Filter Cartridge',
      time: '06:00 PM',
      location: 'Kitchen Utility',
      status: 'TODO',
      link: '/tasks/task-1'
    },
    {
      id: 'bill-1',
      source_type: 'BILL',
      title: 'BESCOM Electricity Bill Due (₹2,000.00)',
      time: 'Due Today',
      location: 'BESCOM Portal',
      status: 'UNPAID',
      link: '/bills/bill-1'
    }
  ]);

  const [alerts] = useState([
    {
      id: 'inv-1',
      source_type: 'INVENTORY',
      title: 'Basmati Rice is Out of Stock',
      subtitle: '0 kg left in Pantry',
      link: '/inventory/inv-1'
    },
    {
      id: 'pur-1',
      source_type: 'PURCHASE',
      title: 'Milk (2 L) — Urgent Purchase',
      subtitle: 'Added by Karthika',
      link: '/shopping'
    }
  ]);

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
            Needs Attention Today
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
            {alerts.map(a => (
              <Card key={a.id} style={{ padding: '14px 16px', borderLeft: '4px solid #f59e0b', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '14px' }}>{a.title}</div>
                  <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>{a.subtitle}</div>
                </div>
                <Link href={a.link} style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-primary-900)', textDecoration: 'none' }}>
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

        {items.map(item => {
          const isEvent = item.source_type === 'EVENT';
          const isTask = item.source_type === 'TASK';

          const borderColor = isEvent ? '#4f46e5' : isTask ? '#10b981' : '#f59e0b';
          const badgeBg = isEvent ? '#e0e7ff' : isTask ? '#d1fae5' : '#fef3c7';
          const badgeColor = isEvent ? '#3730a3' : isTask ? '#065f46' : '#92400e';

          return (
            <Card
              key={item.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '16px 20px',
                borderLeft: `4px solid ${borderColor}`
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <div style={{ minWidth: '75px', textAlign: 'center', padding: '6px 8px', borderRadius: 'var(--radius-md)', background: 'var(--color-surface-subtle)', fontWeight: 700, fontSize: '12px' }}>
                  {item.time}
                </div>

                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '10px', fontWeight: 700, padding: '2px 6px', borderRadius: '4px', background: badgeBg, color: badgeColor }}>
                      {item.source_type}
                    </span>
                    <span style={{ fontSize: '15px', fontWeight: 600 }}>{item.title}</span>
                  </div>
                  {item.location && (
                    <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <MapPin size={12} />
                      <span>{item.location}</span>
                    </div>
                  )}
                </div>
              </div>

              <Link href={item.link} style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-primary-900)', textDecoration: 'none' }}>
                Open ➔
              </Link>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
