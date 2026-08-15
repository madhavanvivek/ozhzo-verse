'use client';

import React, { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import {
  Plus,
  Clock,
  MapPin,
  Users,
  Trash2,
  Sparkles,

} from 'lucide-react';

interface ProjectedItem {
  id: string;
  source_type: 'EVENT' | 'TASK' | 'BILL';
  source_id: string;
  title: string;
  start: string;
  end: string;
  all_day: boolean;
  editable: boolean;
  navigation_target: string;
  status: string;
  category_name?: string | null;
  location?: string | null;
  participants?: string[];
  meta_info?: Record<string, any>;
}

export default function CalendarPage() {
  const [viewMode, setViewMode] = useState<'AGENDA' | 'MONTH'>('AGENDA');
  const [filterType, setFilterType] = useState<'ALL' | 'EVENT' | 'TASK' | 'BILL'>('ALL');
  const [quickTitle, setQuickTitle] = useState('');
  const [quickDate, setQuickDate] = useState(new Date().toISOString().split('T')[0]);
  const [quickLocation, setQuickLocation] = useState('');
  const [isOptionsOpen, setIsOptionsOpen] = useState(false);
  const [category, setCategory] = useState('Family');

  const [items, setItems] = useState<ProjectedItem[]>([
    {
      id: 'proj-1',
      source_type: 'EVENT',
      source_id: 'evt-101',
      title: "Grandmother's 80th Birthday Celebration",
      start: '2026-08-15T00:00:00Z',
      end: '2026-08-15T23:59:59Z',
      all_day: true,
      editable: true,
      navigation_target: '/calendar/evt-101',
      status: 'CONFIRMED',
      category_name: 'Birthday',
      location: 'Family Home',
      participants: ['Vivek', 'Karthika', 'Amma']
    },
    {
      id: 'proj-2',
      source_type: 'TASK',
      source_id: 'task-201',
      title: 'Replace Kitchen Water Filter Cartridge',
      start: '2026-08-15T18:00:00Z',
      end: '2026-08-15T18:00:00Z',
      all_day: false,
      editable: false,
      navigation_target: '/tasks/task-201',
      status: 'TODO',
      category_name: 'Maintenance',
      meta_info: { priority: 'NORMAL', assigned_to_name: 'Vivek' }
    },
    {
      id: 'proj-3',
      source_type: 'EVENT',
      source_id: 'evt-102',
      title: 'Parent-Teacher Term Review Meeting',
      start: '2026-08-18T10:00:00Z',
      end: '2026-08-18T11:00:00Z',
      all_day: false,
      editable: true,
      navigation_target: '/calendar/evt-102',
      status: 'CONFIRMED',
      category_name: 'School',
      location: 'Oakridge School Room 204',
      participants: ['Karthika']
    },
    {
      id: 'proj-4',
      source_type: 'BILL',
      source_id: 'bill-301',
      title: 'BESCOM Electricity Bill Due',
      start: '2026-08-20T23:59:59Z',
      end: '2026-08-20T23:59:59Z',
      all_day: true,
      editable: false,
      navigation_target: '/bills/bill-301',
      status: 'UNPAID',
      category_name: 'Utilities',
      meta_info: { expected_amount: '2000.00', currency: 'INR', responsible_member_name: 'Vivek' }
    },
    {
      id: 'proj-5',
      source_type: 'EVENT',
      source_id: 'evt-103',
      title: 'Family Weekend Road Trip to Mysore',
      start: '2026-08-22T08:00:00Z',
      end: '2026-08-23T20:00:00Z',
      all_day: true,
      editable: true,
      navigation_target: '/calendar/evt-103',
      status: 'CONFIRMED',
      category_name: 'Travel',
      location: 'Mysore Heritage Resort',
      participants: ['Vivek', 'Karthika']
    }
  ]);

  const presetChips = [
    { title: 'Doctor Appointment', cat: 'Appointment', loc: 'City Clinic' },
    { title: 'Birthday Gathering', cat: 'Birthday', loc: 'Home' },
    { title: 'School Parent Meeting', cat: 'School', loc: 'School Auditorium' },
    { title: 'AC Maintenance Visit', cat: 'Maintenance', loc: 'Home' },
    { title: 'Family Dinner', cat: 'Family', loc: 'Dining Room' },
  ];

  const handleQuickAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickTitle.trim()) return;

    const newEv: ProjectedItem = {
      id: `proj-${Date.now()}`,
      source_type: 'EVENT',
      source_id: `evt-${Date.now()}`,
      title: quickTitle.trim(),
      start: `${quickDate}T10:00:00Z`,
      end: `${quickDate}T11:00:00Z`,
      all_day: false,
      editable: true,
      navigation_target: `/calendar/evt-${Date.now()}`,
      status: 'CONFIRMED',
      category_name: category,
      location: quickLocation.trim() || null,
      participants: ['Vivek', 'Karthika']
    };

    setItems([newEv, ...items]);
    setQuickTitle('');
    setQuickLocation('');
    setIsOptionsOpen(false);
  };

  const handleDelete = (id: string) => {
    setItems(items.filter(i => i.id !== id));
  };

  const filteredItems = items.filter(item => {
    if (filterType === 'ALL') return true;
    return item.source_type === filterType;
  });

  const eventCount = items.filter(i => i.source_type === 'EVENT').length;
  const taskCount = items.filter(i => i.source_type === 'TASK').length;
  const billCount = items.filter(i => i.source_type === 'BILL').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '980px' }}>
      {/* Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-3)' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-primary-900)' }}>
            Shared Calendar & Household Schedule
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)' }}>
            What is happening in our home • Unified timeline of family events, due chores, and bill payment deadlines.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <Button
            variant={viewMode === 'AGENDA' ? 'primary' : 'secondary'}
            onClick={() => setViewMode('AGENDA')}
          >
            Agenda Timeline
          </Button>
          <Button
            variant={viewMode === 'MONTH' ? 'primary' : 'secondary'}
            onClick={() => setViewMode('MONTH')}
          >
            Month View
          </Button>
        </div>
      </div>

      {/* Quick Add Bar & Presets */}
      <Card style={{ padding: '16px 20px', border: '2px solid var(--color-primary-900)' }}>
        <form onSubmit={handleQuickAdd} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}>
            <input
              type="text"
              placeholder="Event title (e.g. Doctor Visit, Birthday, Meeting)..."
              value={quickTitle}
              onChange={(e) => setQuickTitle(e.target.value)}
              style={{
                flex: 2,
                minWidth: '220px',
                height: '42px',
                padding: '0 14px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border-strong)',
                fontSize: '14px',
                backgroundColor: 'var(--color-surface-card)'
              }}
              required
            />
            <input
              type="date"
              value={quickDate}
              onChange={(e) => setQuickDate(e.target.value)}
              style={{
                flex: 1,
                minWidth: '140px',
                height: '42px',
                padding: '0 10px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border-strong)',
                fontSize: '14px',
                backgroundColor: 'var(--color-surface-card)'
              }}
              required
            />
            <Button type="submit">
              <Plus size={16} />
              <span>Add Event</span>
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsOptionsOpen(!isOptionsOpen)}
            >
              {isOptionsOpen ? 'Simple' : 'Options ▾'}
            </Button>
          </div>

          {/* Preset Chips */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', marginRight: '4px' }}>
              Quick Presets:
            </span>
            {presetChips.map(p => (
              <button
                key={p.title}
                type="button"
                onClick={() => {
                  setQuickTitle(p.title);
                  setCategory(p.cat);
                  setQuickLocation(p.loc);
                  setIsOptionsOpen(true);
                }}
                style={{
                  padding: '4px 10px',
                  borderRadius: 'var(--radius-full)',
                  background: 'var(--color-surface-hover)',
                  border: '1px solid var(--color-border)',
                  fontSize: '12px',
                  fontWeight: 500,
                  cursor: 'pointer',
                  color: 'var(--color-text-primary)'
                }}
              >
                + {p.title}
              </button>
            ))}
          </div>

          {/* Expanded Options */}
          {isOptionsOpen && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', paddingTop: '8px', borderTop: '1px solid var(--color-border)' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', fontWeight: 600 }}>Location (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. Clinic, School, Home..."
                  value={quickLocation}
                  onChange={(e) => setQuickLocation(e.target.value)}
                  style={{ height: '36px', padding: '0 10px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
                />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', fontWeight: 600 }}>Category</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  style={{ height: '36px', padding: '0 8px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
                >
                  <option value="Family">Family</option>
                  <option value="Birthday">Birthday</option>
                  <option value="Anniversary">Anniversary</option>
                  <option value="School">School</option>
                  <option value="Appointment">Appointment</option>
                  <option value="Travel">Travel</option>
                  <option value="Maintenance">Maintenance</option>
                </select>
              </div>
            </div>
          )}
        </form>
      </Card>

      {/* Filter Tabs & Source Indicators */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: 'var(--space-2)', overflowX: 'auto' }}>
        {[
          { id: 'ALL', label: `All Schedule (${items.length})` },
          { id: 'EVENT', label: `Events Only (${eventCount})` },
          { id: 'TASK', label: `Tasks Due (${taskCount})` },
          { id: 'BILL', label: `Bills Due (${billCount})` },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setFilterType(tab.id as any)}
            style={{
              padding: '6px 14px',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              backgroundColor: filterType === tab.id ? 'var(--color-primary-900)' : 'transparent',
              color: filterType === tab.id ? 'var(--color-text-inverse)' : 'var(--color-text-secondary)',
              fontWeight: 600,
              fontSize: '13px',
              cursor: 'pointer',
              whiteSpace: 'nowrap'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Timeline Stream */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
        {filteredItems.length === 0 ? (
          <Card style={{ padding: 'var(--space-12) var(--space-4)', textAlign: 'center' }}>
            <Sparkles size={36} color="var(--status-in-stock)" style={{ margin: '0 auto 10px' }} />
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-primary-900)' }}>
              No scheduled items found
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
              Your household calendar is completely clear.
            </p>
          </Card>
        ) : (
          filteredItems.map(item => {
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
                  flexDirection: 'column',
                  gap: '8px',
                  padding: '16px 20px',
                  borderLeft: `4px solid ${borderColor}`
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '14px', flexWrap: 'wrap' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <span
                        style={{
                          fontSize: '11px',
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: '4px',
                          background: badgeBg,
                          color: badgeColor,
                          textTransform: 'uppercase'
                        }}
                      >
                        {item.source_type}
                      </span>

                      {item.category_name && (
                        <span style={{ fontSize: '11px', padding: '2px 6px', borderRadius: '4px', background: 'var(--color-surface-hover)', color: 'var(--color-text-secondary)', fontWeight: 500 }}>
                          {item.category_name}
                        </span>
                      )}

                      <span style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                        {item.title}
                      </span>
                    </div>

                    <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '14px', marginTop: '4px', fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Clock size={13} />
                        <span>{item.all_day ? `All Day • ${item.start.split('T')[0]}` : new Date(item.start).toLocaleString()}</span>
                      </span>

                      {item.location && (
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <MapPin size={13} />
                          <span>{item.location}</span>
                        </span>
                      )}

                      {item.participants && item.participants.length > 0 && (
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <Users size={13} />
                          <span>{item.participants.join(', ')}</span>
                        </span>
                      )}

                      {item.meta_info?.assigned_to_name && (
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <span>Assigned: {item.meta_info.assigned_to_name}</span>
                        </span>
                      )}

                      {item.meta_info?.expected_amount && (
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 600, color: 'var(--color-primary-900)' }}>
                          <span>{item.meta_info.currency} {item.meta_info.expected_amount}</span>
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {item.editable && (
                      <button
                        onClick={() => handleDelete(item.id)}
                        title="Delete Event"
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-tertiary)', padding: '4px' }}
                      >
                        <Trash2 size={16} />
                      </button>
                    )}

                    {!item.editable && (
                      <span style={{ fontSize: '11px', color: 'var(--color-text-secondary)', background: 'var(--color-surface-hover)', padding: '2px 8px', borderRadius: '4px' }}>
                        Linked {item.source_type}
                      </span>
                    )}
                  </div>
                </div>
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
}
