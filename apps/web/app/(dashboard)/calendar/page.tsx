'use client';

import React, { useEffect, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import {
  Plus,
  Clock,
  MapPin,
  Trash2,
  Sparkles,
  Calendar as CalendarIcon,
  CheckCircle2,
  Receipt
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

interface ProjectedItem {
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

interface CalendarProjectionResponse {
  timeline_items: ProjectedItem[];
  total_events: number;
  total_tasks: number;
  total_bills: number;
}

export default function CalendarPage() {
  const [activeHomeId, setActiveHomeId] = useState<string | null>(null);
  const [items, setItems] = useState<ProjectedItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const [viewMode, setViewMode] = useState<'AGENDA' | 'MONTH'>('AGENDA');
  const [filterType, setFilterType] = useState<'ALL' | 'EVENT' | 'TASK' | 'BILL'>('ALL');
  const [quickTitle, setQuickTitle] = useState('');
  const [quickDate, setQuickDate] = useState(new Date().toISOString().split('T')[0]);
  const [quickLocation, setQuickLocation] = useState('');
  const [isOptionsOpen, setIsOptionsOpen] = useState(false);
  const [category, setCategory] = useState('Family');

  const loadData = async () => {
    setIsLoading(true);
    try {
      const savedHomeId = localStorage.getItem('active_home_id');
      let homeId = savedHomeId;

      if (!homeId) {
        const homes = await apiClient.get<Array<{ id: string }>>('/homes');
        if (homes && homes.length > 0) {
          homeId = homes[0].id;
          localStorage.setItem('active_home_id', homeId);
        }
      }

      setActiveHomeId(homeId);

      if (homeId) {
        const start = new Date(Date.now() - 86400000 * 30).toISOString();
        const end = new Date(Date.now() + 86400000 * 60).toISOString();

        const projection = await apiClient.get<CalendarProjectionResponse>(
          `/homes/${homeId}/calendar/projection?start_date=${encodeURIComponent(start)}&end_date=${encodeURIComponent(end)}`
        );

        setItems(projection?.timeline_items || []);
      }
    } catch (err) {
      console.error('Failed to load calendar projection:', err);
      setItems([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const presetChips = [
    { title: 'Doctor Appointment', cat: 'Appointment', loc: 'City Clinic' },
    { title: 'Birthday Gathering', cat: 'Birthday', loc: 'Home' },
    { title: 'School Parent Meeting', cat: 'School', loc: 'School Auditorium' },
    { title: 'AC Maintenance Visit', cat: 'Maintenance', loc: 'Home' },
    { title: 'Family Dinner', cat: 'Family', loc: 'Dining Room' },
  ];

  const handleQuickAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickTitle.trim() || !activeHomeId) return;

    const payload = {
      title: quickTitle.trim(),
      start_time: `${quickDate}T10:00:00Z`,
      end_time: `${quickDate}T11:00:00Z`,
      is_all_day: false,
      location: quickLocation.trim() || undefined,
      category_name: category
    };

    try {
      await apiClient.post(`/homes/${activeHomeId}/calendar/events`, payload);
      setQuickTitle('');
      setQuickLocation('');
      setIsOptionsOpen(false);
      loadData();
    } catch (err) {
      console.error('Failed to create calendar event:', err);
      alert('Failed to save calendar event to backend.');
    }
  };

  const handleDelete = async (item: ProjectedItem) => {
    if (!activeHomeId) return;
    if (item.source_type !== 'EVENT') {
      alert(`This is a projected ${item.source_type.toLowerCase()}. Please manage it from the ${item.source_type.toLowerCase()}s section.`);
      return;
    }

    if (!confirm('Are you sure you want to delete this calendar event?')) return;

    try {
      await apiClient.delete(`/homes/${activeHomeId}/calendar/events/${item.source_id}`);
      setItems(items.filter(i => i.source_id !== item.source_id));
    } catch (err) {
      console.error('Failed to delete event:', err);
      alert('Failed to delete event.');
    }
  };

  const filteredItems = items.filter(item => {
    if (filterType === 'ALL') return true;
    return item.source_type === filterType;
  });

  const getSourceIcon = (type: string) => {
    switch (type) {
      case 'EVENT':
        return <CalendarIcon size={16} color="var(--color-primary-900)" />;
      case 'TASK':
        return <CheckCircle2 size={16} color="var(--color-accent-warm)" />;
      case 'BILL':
        return <Receipt size={16} color="var(--status-overdue)" />;
      default:
        return <Clock size={16} color="var(--color-text-secondary)" />;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '960px' }}>
      {/* Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-3)' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-primary-900)' }}>
            Household Calendar & Schedule
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)' }}>
            Unified schedule • Family events, chore deadlines, and bill due dates synchronized in one place.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <Button
            variant={viewMode === 'AGENDA' ? 'primary' : 'secondary'}
            size="sm"
            onClick={() => setViewMode('AGENDA')}
          >
            Agenda View
          </Button>
          <Button
            variant={viewMode === 'MONTH' ? 'primary' : 'secondary'}
            size="sm"
            onClick={() => setViewMode('MONTH')}
          >
            Month View
          </Button>
        </div>
      </div>

      {/* Quick Add Bar */}
      <Card style={{ border: '2px solid var(--color-primary-900)', padding: 'var(--space-4)' }}>
        <form onSubmit={handleQuickAdd} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
            <input
              type="text"
              placeholder="Add event to family calendar... (e.g. Doctor appointment, Parent-teacher meeting)"
              value={quickTitle}
              onChange={(e) => setQuickTitle(e.target.value)}
              style={{
                flex: '1 1 220px',
                height: '42px',
                padding: '0 14px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border)',
                fontSize: '14px'
              }}
              required
            />
            <input
              type="date"
              value={quickDate}
              onChange={(e) => setQuickDate(e.target.value)}
              style={{
                flex: '0 1 150px',
                height: '42px',
                padding: '0 12px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border)',
                fontSize: '13px'
              }}
            />
            <div style={{ display: 'flex', gap: '6px' }}>
              <Button type="submit" size="md">
                <Plus size={16} />
                <span>Add Event</span>
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="md"
                onClick={() => setIsOptionsOpen(!isOptionsOpen)}
              >
                {isOptionsOpen ? 'Simple' : 'Options'}
              </Button>
            </div>
          </div>

          {/* Quick Presets */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
            <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-text-tertiary)' }}>Presets:</span>
            {presetChips.map((chip, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  setQuickTitle(chip.title);
                  setCategory(chip.cat);
                  setQuickLocation(chip.loc);
                  setIsOptionsOpen(true);
                }}
                style={{
                  padding: '3px 8px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-border)',
                  backgroundColor: 'var(--color-surface-subtle)',
                  fontSize: '11px',
                  fontWeight: 500,
                  cursor: 'pointer'
                }}
              >
                + {chip.title}
              </button>
            ))}
          </div>

          {isOptionsOpen && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', paddingTop: '8px', borderTop: '1px solid var(--color-border)' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', fontWeight: 600 }}>Location (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. City Clinic, Oakridge School"
                  value={quickLocation}
                  onChange={(e) => setQuickLocation(e.target.value)}
                  style={{ height: '36px', padding: '0 8px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
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
                  <option value="Birthday">Birthday / Celebration</option>
                  <option value="Appointment">Doctor / Health</option>
                  <option value="School">School / Education</option>
                  <option value="Travel">Travel / Outing</option>
                  <option value="Maintenance">Maintenance</option>
                  <option value="Other">Other</option>
                </select>
              </div>
            </div>
          )}
        </form>
      </Card>

      {/* Filter Tabs */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: 'var(--space-2)', overflowX: 'auto' }}>
        {[
          { key: 'ALL', label: `All Items (${items.length})` },
          { key: 'EVENT', label: `Events (${items.filter(i => i.source_type === 'EVENT').length})` },
          { key: 'TASK', label: `Chores & Tasks (${items.filter(i => i.source_type === 'TASK').length})` },
          { key: 'BILL', label: `Bills Due (${items.filter(i => i.source_type === 'BILL').length})` }
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setFilterType(tab.key as any)}
            style={{
              padding: '6px 14px',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              backgroundColor: filterType === tab.key ? 'var(--color-primary-900)' : 'transparent',
              color: filterType === tab.key ? 'var(--color-text-inverse)' : 'var(--color-text-secondary)',
              fontWeight: 600,
              fontSize: '13px',
              cursor: 'pointer'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Agenda Item List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
        {isLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {[1, 2, 3].map((i) => (
              <div key={i} style={{ height: '64px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: 'var(--radius-md)', animation: 'pulse 1.5s infinite' }} />
            ))}
          </div>
        ) : filteredItems.length === 0 ? (
          <Card style={{ padding: 'var(--space-8)', textAlign: 'center' }}>
            <Sparkles size={36} color="var(--status-in-stock)" style={{ margin: '0 auto 10px' }} />
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-primary-900)' }}>
              No scheduled items found
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
              Your family calendar has no upcoming events or due items in this view.
            </p>
          </Card>
        ) : (
          filteredItems.map((item, idx) => (
            <Card
              key={`${item.source_type}-${item.source_id}-${idx}`}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px 16px',
                borderLeft: item.source_type === 'BILL'
                  ? '4px solid var(--status-overdue)'
                  : item.source_type === 'TASK'
                  ? '4px solid var(--color-accent-warm)'
                  : '4px solid var(--color-primary-900)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                <div style={{ width: '36px', height: '36px', borderRadius: '50%', backgroundColor: 'var(--color-surface-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  {getSourceIcon(item.source_type)}
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                  <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                    {item.title}
                  </div>

                  <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                    <span>{new Date(item.start).toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })}</span>
                    {!item.all_day && (
                      <span>• {new Date(item.start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    )}
                    {item.location && (
                      <span style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                        • <MapPin size={11} /> {item.location}
                      </span>
                    )}
                    {item.category_name && <span>• {item.category_name}</span>}
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                {item.editable && (
                  <button
                    onClick={() => handleDelete(item)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-tertiary)', padding: '4px' }}
                    aria-label="Delete event"
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
