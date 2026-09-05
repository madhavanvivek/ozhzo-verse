'use client';

import React, { useEffect, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useRouter } from 'next/navigation';
import {
  Plus,
  Clock,
  MapPin,
  Trash2,
  Sparkles,
  Calendar as CalendarIcon,
  CheckCircle2,
  Receipt,
  Edit2,
  ChevronLeft,
  ChevronRight,
  X,
  Check,
  Wrench,
  GraduationCap,
  ExternalLink
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

interface ProjectedItem {
  source_type: 'EVENT' | 'TASK' | 'BILL' | 'COURSE' | 'INVENTORY' | 'AUTOMATION';
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
  const router = useRouter();
  const [activeHomeId, setActiveHomeId] = useState<string | null>(null);
  const [items, setItems] = useState<ProjectedItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const [viewMode, setViewMode] = useState<'AGENDA' | 'MONTH'>('AGENDA');
  const [filterType, setFilterType] = useState<'ALL' | 'EVENT' | 'TASK' | 'BILL' | 'INVENTORY' | 'COURSE'>('ALL');
  const [currentMonthDate, setCurrentMonthDate] = useState(new Date());

  // Quick Add State
  const [quickTitle, setQuickTitle] = useState('');
  const [quickDate, setQuickDate] = useState(new Date().toISOString().split('T')[0]);
  const [quickStartTime, setQuickStartTime] = useState('10:00');
  const [quickEndTime, setQuickEndTime] = useState('11:00');
  const [quickAllDay, setQuickAllDay] = useState(false);
  const [quickLocation, setQuickLocation] = useState('');
  const [quickNotes, setQuickNotes] = useState('');
  const [quickRecurrence, setQuickRecurrence] = useState<'NONE' | 'DAILY' | 'WEEKLY' | 'MONTHLY' | 'YEARLY'>('NONE');
  const [category, setCategory] = useState('Family');
  const [isOptionsOpen, setIsOptionsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Edit Event Modal State
  const [editingItem, setEditingItem] = useState<ProjectedItem | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editDate, setEditDate] = useState('');
  const [editStartTime, setEditStartTime] = useState('10:00');
  const [editEndTime, setEditEndTime] = useState('11:00');
  const [editAllDay, setEditAllDay] = useState(false);
  const [editLocation, setEditLocation] = useState('');
  const [editCategory, setEditCategory] = useState('Family');
  const [editNotes, setEditNotes] = useState('');
  const [editRecurrence, setEditRecurrence] = useState<'NONE' | 'DAILY' | 'WEEKLY' | 'MONTHLY' | 'YEARLY'>('NONE');
  const [isSavingEdit, setIsSavingEdit] = useState(false);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage((curr) => (curr === msg ? null : curr));
    }, 4000);
  };

  const loadData = async (showLoading = false) => {
    if (showLoading) setIsLoading(true);
    try {
      const homeId = await apiClient.getValidActiveHome();
      setActiveHomeId(homeId);

      if (homeId) {
        const start = new Date(Date.now() - 86400000 * 90).toISOString();
        const end = new Date(Date.now() + 86400000 * 180).toISOString();
        const queryParams = `?start_date=${encodeURIComponent(start)}&end_date=${encodeURIComponent(end)}`;

        try {
          const projection = await apiClient.get<any>(`/homes/${homeId}/calendar/projection${queryParams}`);
          const rawList = Array.isArray(projection)
            ? projection
            : (projection?.items || projection?.timeline_items || projection?.data?.items || projection?.data?.timeline_items || projection?.data || []);

          if (Array.isArray(rawList)) {
            setItems(rawList);
          } else {
            setItems([]);
          }
        } catch (projErr) {
          console.warn('Calendar projection failed, using fallback events endpoint:', projErr);
          try {
            const fallbackEvents = await apiClient.get<any>(`/homes/${homeId}/events`);
            const list = Array.isArray(fallbackEvents) ? fallbackEvents : (fallbackEvents?.data || []);
            const mapped: ProjectedItem[] = list.map((e: any) => ({
              source_type: 'EVENT',
              source_id: e.id,
              title: e.title,
              start: e.start_time,
              end: e.end_time,
              all_day: Boolean(e.is_all_day),
              editable: true,
              navigation_target: `/calendar/${e.id}`,
              status: e.status || 'CONFIRMED',
              category_name: e.category_name,
              location: e.location,
              meta_info: { description: e.description, recurrence_type: e.recurrence_type }
            }));
            setItems(mapped);
          } catch {
            setItems([]);
          }
        }
      } else {
        setItems([]);
      }
    } catch (err) {
      console.error('Failed to load calendar data:', err);
      setItems([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData(true);

    const handleHomeChanged = () => {
      loadData(true);
    };

    window.addEventListener('home-changed', handleHomeChanged);
    return () => window.removeEventListener('home-changed', handleHomeChanged);
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

    setIsSubmitting(true);
    try {
      let startIso: string;
      let endIso: string;

      const [y, m, d] = quickDate.split('-').map(Number);
      if (quickAllDay) {
        const startDate = new Date(y, m - 1, d, 0, 0, 0);
        const endDate = new Date(y, m - 1, d, 23, 59, 59);
        startIso = startDate.toISOString();
        endIso = endDate.toISOString();
      } else {
        const [sH, sM] = (quickStartTime || '10:00').split(':').map(Number);
        const [eH, eM] = (quickEndTime || '11:00').split(':').map(Number);
        const startDate = new Date(y, m - 1, d, sH, sM, 0);
        let endDate = new Date(y, m - 1, d, eH, eM, 0);
        if (endDate < startDate) {
          endDate = new Date(startDate.getTime() + 3600000);
        }
        startIso = startDate.toISOString();
        endIso = endDate.toISOString();
      }

      const payload = {
        title: quickTitle.trim(),
        description: quickNotes.trim() || undefined,
        start_time: startIso,
        end_time: endIso,
        is_all_day: quickAllDay,
        location: quickLocation.trim() || undefined,
        category_name: category,
        recurrence_type: quickRecurrence,
        reminder_minutes_before: 30
      };

      const res = await apiClient.post<any>(`/homes/${activeHomeId}/events`, payload);
      const createdEvent = res?.data || res;

      // Optimistically add item to UI immediately
      const newProjectedItem: ProjectedItem = {
        source_type: 'EVENT',
        source_id: createdEvent?.id || `temp-${Date.now()}`,
        title: payload.title,
        start: payload.start_time,
        end: payload.end_time,
        all_day: payload.is_all_day,
        editable: true,
        navigation_target: `/calendar/${createdEvent?.id || ''}`,
        status: 'CONFIRMED',
        category_name: payload.category_name,
        location: payload.location,
        meta_info: {
          description: payload.description,
          recurrence_type: payload.recurrence_type
        }
      };
      setItems(prev => [newProjectedItem, ...prev]);

      setQuickTitle('');
      setQuickLocation('');
      setQuickNotes('');
      setIsOptionsOpen(false);
      showToast(`"${payload.title}" added to your calendar.`);
      await loadData(false);
    } catch (err: any) {
      console.error('Failed to create calendar event:', err);
      const msg = err?.message || err?.detail || 'Unable to save this event right now. Please check the inputs and try again.';
      alert(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleItemNavigation = (item: ProjectedItem) => {
    if (item.source_type === 'EVENT') {
      openEditModal(item);
    } else if (item.source_type === 'TASK') {
      router.push('/tasks');
    } else if (item.source_type === 'BILL') {
      router.push('/bills');
    } else if (item.source_type === 'INVENTORY') {
      router.push('/inventory');
    } else if (item.source_type === 'COURSE') {
      router.push('/courses');
    } else if (item.navigation_target) {
      router.push(item.navigation_target);
    }
  };

  const openEditModal = (item: ProjectedItem) => {
    if (item.source_type !== 'EVENT') {
      handleItemNavigation(item);
      return;
    }

    setEditingItem(item);
    setEditTitle(item.title);

    const startDateObj = new Date(item.start);
    const endDateObj = new Date(item.end);
    const pad = (n: number) => String(n).padStart(2, '0');

    setEditDate(`${startDateObj.getFullYear()}-${pad(startDateObj.getMonth() + 1)}-${pad(startDateObj.getDate())}`);
    setEditStartTime(`${pad(startDateObj.getHours())}:${pad(startDateObj.getMinutes())}`);
    setEditEndTime(`${pad(endDateObj.getHours())}:${pad(endDateObj.getMinutes())}`);
    setEditAllDay(item.all_day);
    setEditLocation(item.location || '');
    setEditCategory(item.category_name || 'Family');
    setEditNotes(item.meta_info?.description || '');
    setEditRecurrence((item.meta_info?.recurrence_type as any) || 'NONE');
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingItem || !activeHomeId || !editTitle.trim()) return;

    setIsSavingEdit(true);
    try {
      let startIso: string;
      let endIso: string;

      const [y, m, d] = editDate.split('-').map(Number);
      if (editAllDay) {
        const startDate = new Date(y, m - 1, d, 0, 0, 0);
        const endDate = new Date(y, m - 1, d, 23, 59, 59);
        startIso = startDate.toISOString();
        endIso = endDate.toISOString();
      } else {
        const [sH, sM] = (editStartTime || '10:00').split(':').map(Number);
        const [eH, eM] = (editEndTime || '11:00').split(':').map(Number);
        const startDate = new Date(y, m - 1, d, sH, sM, 0);
        let endDate = new Date(y, m - 1, d, eH, eM, 0);
        if (endDate < startDate) {
          endDate = new Date(startDate.getTime() + 3600000);
        }
        startIso = startDate.toISOString();
        endIso = endDate.toISOString();
      }

      const payload = {
        title: editTitle.trim(),
        description: editNotes.trim() || undefined,
        start_time: startIso,
        end_time: endIso,
        is_all_day: editAllDay,
        location: editLocation.trim() || undefined,
        category_name: editCategory,
        recurrence_type: editRecurrence
      };

      await apiClient.patch(`/homes/${activeHomeId}/events/${editingItem.source_id}`, payload);

      setEditingItem(null);
      showToast(`Updated "${editTitle.trim()}".`);
      await loadData(false);
    } catch (err: any) {
      console.error('Failed to update event:', err);
      const msg = err?.message || err?.detail || 'Unable to update this event right now.';
      alert(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setIsSavingEdit(false);
    }
  };

  const handleDelete = async (item: ProjectedItem) => {
    if (!activeHomeId) return;
    if (item.source_type !== 'EVENT') {
      alert(`This is a projected ${item.source_type.toLowerCase()}. Please manage it from the ${item.source_type.toLowerCase()}s section.`);
      return;
    }

    if (!confirm(`Are you sure you want to delete "${item.title}"?`)) return;

    // Optimistic UI remove
    setItems(prev => prev.filter(i => i.source_id !== item.source_id));
    if (editingItem?.source_id === item.source_id) {
      setEditingItem(null);
    }

    try {
      await apiClient.delete(`/homes/${activeHomeId}/events/${item.source_id}`);
      showToast(`Deleted "${item.title}".`);
      loadData(false);
    } catch (err: any) {
      console.error('Failed to delete event:', err);
      alert(err?.message || 'Failed to delete event.');
      loadData(false);
    }
  };

  const filteredItems = items.filter(item => {
    if (filterType === 'ALL') return true;
    return item.source_type === filterType;
  });

  const getSourceIcon = (item: ProjectedItem) => {
    switch (item.source_type) {
      case 'EVENT':
        return <CalendarIcon size={16} color="var(--color-primary-900)" />;
      case 'TASK':
        return <CheckCircle2 size={16} color={item.status === 'COMPLETED' ? '#10b981' : 'var(--color-accent-warm)'} />;
      case 'BILL':
        return <Receipt size={16} color={item.status === 'PAID' ? '#10b981' : item.status === 'UPCOMING' ? '#3b82f6' : 'var(--status-overdue)'} />;
      case 'INVENTORY':
        return <Wrench size={16} color="#06b6d4" />;
      case 'COURSE':
        return <GraduationCap size={16} color="#6366f1" />;
      case 'AUTOMATION':
        return <Sparkles size={16} color="#8b5cf6" />;
      default:
        return <Clock size={16} color="var(--color-text-secondary)" />;
    }
  };

  const getItemBorderColor = (item: ProjectedItem) => {
    if (item.source_type === 'BILL') {
      if (item.status === 'PAID') return '#10b981';
      if (item.status === 'UPCOMING') return '#3b82f6';
      return 'var(--status-overdue)';
    }
    if (item.source_type === 'TASK') {
      if (item.status === 'COMPLETED') return '#10b981';
      if (item.status === 'IN_PROGRESS') return '#8b5cf6';
      return 'var(--color-accent-warm)';
    }
    if (item.source_type === 'INVENTORY') return '#06b6d4';
    if (item.source_type === 'COURSE') return '#6366f1';
    if (item.source_type === 'AUTOMATION') return '#8b5cf6';
    return 'var(--color-primary-900)';
  };

  const renderStatusBadge = (item: ProjectedItem) => {
    if (item.source_type === 'BILL') {
      if (item.status === 'PAID') {
        return (
          <span style={{ backgroundColor: '#ecfdf5', color: '#047857', border: '1px solid #a7f3d0', fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '12px' }}>
            Paid
          </span>
        );
      }
      if (item.status === 'UPCOMING') {
        return (
          <span style={{ backgroundColor: '#eff6ff', color: '#1d4ed8', border: '1px solid #bfdbfe', fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '12px' }}>
            Upcoming Cycle
          </span>
        );
      }
      if (item.status === 'OVERDUE') {
        return (
          <span style={{ backgroundColor: '#fef2f2', color: '#b91c1c', border: '1px solid #fecaca', fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '12px' }}>
            Overdue
          </span>
        );
      }
      return (
        <span style={{ backgroundColor: '#fffbeb', color: '#b45309', border: '1px solid #fde68a', fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '12px' }}>
          Due
        </span>
      );
    }
    if (item.source_type === 'TASK') {
      if (item.status === 'COMPLETED') {
        return (
          <span style={{ backgroundColor: '#ecfdf5', color: '#047857', border: '1px solid #a7f3d0', fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '12px' }}>
            Completed
          </span>
        );
      }
      if (item.status === 'IN_PROGRESS') {
        return (
          <span style={{ backgroundColor: '#f5f3ff', color: '#6d28d9', border: '1px solid #ddd6fe', fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '12px' }}>
            In Progress
          </span>
        );
      }
      return (
        <span style={{ backgroundColor: '#fffbeb', color: '#b45309', border: '1px solid #fde68a', fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '12px' }}>
          Pending
        </span>
      );
    }
    if (item.source_type === 'INVENTORY') {
      return (
        <span style={{ backgroundColor: '#ecfeff', color: '#0e7490', border: '1px solid #a5f3fc', fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '12px' }}>
          Maintenance
        </span>
      );
    }
    if (item.source_type === 'COURSE') {
      return (
        <span style={{ backgroundColor: '#eef2ff', color: '#4338ca', border: '1px solid #c7d2fe', fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '12px' }}>
          Course
        </span>
      );
    }
    return (
      <span style={{ backgroundColor: '#f0fdf4', color: 'var(--color-primary-900)', border: '1px solid #d1fae5', fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '12px' }}>
        Event
      </span>
    );
  };

  // Month View Calculation
  const year = currentMonthDate.getFullYear();
  const month = currentMonthDate.getMonth();
  const monthName = currentMonthDate.toLocaleString('default', { month: 'long', year: 'numeric' });
  const firstDayIndex = new Date(year, month, 1).getDay();
  const totalDaysInMonth = new Date(year, month + 1, 0).getDate();

  const handlePrevMonth = () => {
    setCurrentMonthDate(new Date(year, month - 1, 1));
  };

  const handleNextMonth = () => {
    setCurrentMonthDate(new Date(year, month + 1, 1));
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '960px', width: '100%' }}>
      {/* Toast Notification */}
      {toastMessage && (
        <div
          role="status"
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            backgroundColor: 'var(--color-primary-900)',
            color: '#ffffff',
            padding: '12px 20px',
            borderRadius: 'var(--radius-md)',
            boxShadow: '0 8px 24px rgba(0,0,0,0.18)',
            fontSize: '13px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            zIndex: 9999,
            animation: 'fadeIn 0.2s ease-out'
          }}
        >
          <Check size={16} color="var(--status-in-stock)" />
          <span>{toastMessage}</span>
          <button
            onClick={() => setToastMessage(null)}
            style={{ background: 'none', border: 'none', color: '#ffffff', cursor: 'pointer', marginLeft: '6px' }}
            aria-label="Close notification"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-3)' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-primary-900)', lineHeight: 1.2 }}>
            Household Calendar & Schedule
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
            Unified schedule • Family events, chore deadlines, bill due dates, and maintenance synchronized in one place.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <Button
            variant={viewMode === 'AGENDA' ? 'primary' : 'secondary'}
            size="sm"
            onClick={() => setViewMode('AGENDA')}
            style={{ minHeight: '40px', padding: '0 14px' }}
          >
            Agenda View
          </Button>
          <Button
            variant={viewMode === 'MONTH' ? 'primary' : 'secondary'}
            size="sm"
            onClick={() => setViewMode('MONTH')}
            style={{ minHeight: '40px', padding: '0 14px' }}
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
                flex: '2 1 220px',
                height: '44px',
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
                flex: '1 1 140px',
                height: '44px',
                padding: '0 12px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border)',
                fontSize: '13px'
              }}
            />
            <div style={{ display: 'flex', gap: '6px' }}>
              <Button type="submit" disabled={isSubmitting} style={{ minHeight: '44px', padding: '0 16px' }}>
                <Plus size={16} />
                <span>{isSubmitting ? 'Saving...' : 'Add Event'}</span>
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => setIsOptionsOpen(!isOptionsOpen)}
                style={{ minHeight: '44px', padding: '0 12px' }}
              >
                {isOptionsOpen ? 'Less' : 'More Options'}
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
                  padding: '5px 10px',
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
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', paddingTop: '10px', borderTop: '1px solid var(--color-border)' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', fontWeight: 600 }}>Start Time</label>
                <input
                  type="time"
                  disabled={quickAllDay}
                  value={quickStartTime}
                  onChange={(e) => setQuickStartTime(e.target.value)}
                  style={{ height: '38px', padding: '0 8px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
                />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', fontWeight: 600 }}>End Time</label>
                <input
                  type="time"
                  disabled={quickAllDay}
                  value={quickEndTime}
                  onChange={(e) => setQuickEndTime(e.target.value)}
                  style={{ height: '38px', padding: '0 8px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
                />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', fontWeight: 600 }}>Location (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. City Clinic, School"
                  value={quickLocation}
                  onChange={(e) => setQuickLocation(e.target.value)}
                  style={{ height: '38px', padding: '0 8px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
                />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', fontWeight: 600 }}>Category</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  style={{ height: '38px', padding: '0 8px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
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

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', fontWeight: 600 }}>Recurrence</label>
                <select
                  value={quickRecurrence}
                  onChange={(e) => setQuickRecurrence(e.target.value as any)}
                  style={{ height: '38px', padding: '0 8px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
                >
                  <option value="NONE">Does not repeat</option>
                  <option value="DAILY">Daily</option>
                  <option value="WEEKLY">Weekly</option>
                  <option value="MONTHLY">Monthly</option>
                  <option value="YEARLY">Yearly</option>
                </select>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '22px' }}>
                <input
                  type="checkbox"
                  id="allDayCheckbox"
                  checked={quickAllDay}
                  onChange={(e) => setQuickAllDay(e.target.checked)}
                  style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                />
                <label htmlFor="allDayCheckbox" style={{ fontSize: '12px', fontWeight: 600, cursor: 'pointer' }}>
                  All-Day Event
                </label>
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
          { key: 'TASK', label: `Tasks & Chores (${items.filter(i => i.source_type === 'TASK').length})` },
          { key: 'BILL', label: `Bills (${items.filter(i => i.source_type === 'BILL').length})` },
          { key: 'INVENTORY', label: `Maintenance (${items.filter(i => i.source_type === 'INVENTORY').length})` },
          { key: 'COURSE', label: `Courses (${items.filter(i => i.source_type === 'COURSE').length})` },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setFilterType(tab.key as any)}
            style={{
              padding: '8px 16px',
              minHeight: '40px',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              backgroundColor: filterType === tab.key ? 'var(--color-primary-900)' : 'transparent',
              color: filterType === tab.key ? 'var(--color-text-inverse)' : 'var(--color-text-secondary)',
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

      {/* Month View Grid */}
      {viewMode === 'MONTH' ? (
        <Card style={{ padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
              {monthName}
            </h2>
            <div style={{ display: 'flex', gap: '6px' }}>
              <Button size="sm" variant="secondary" onClick={handlePrevMonth} style={{ minHeight: '36px', padding: '0 10px' }}>
                <ChevronLeft size={16} />
              </Button>
              <Button size="sm" variant="secondary" onClick={handleNextMonth} style={{ minHeight: '36px', padding: '0 10px' }}>
                <ChevronRight size={16} />
              </Button>
            </div>
          </div>

          {/* Weekday headers */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', textAlign: 'center', fontWeight: 600, fontSize: '12px', color: 'var(--color-text-tertiary)', marginBottom: '8px' }}>
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(d => (
              <div key={d} style={{ padding: '4px' }}>{d}</div>
            ))}
          </div>

          {/* Days Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '4px' }}>
            {Array.from({ length: firstDayIndex }).map((_, i) => (
              <div key={`empty-${i}`} style={{ height: '70px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: 'var(--radius-sm)', opacity: 0.4 }} />
            ))}

            {Array.from({ length: totalDaysInMonth }).map((_, i) => {
              const dayNum = i + 1;
              const isToday =
                new Date().getFullYear() === year &&
                new Date().getMonth() === month &&
                new Date().getDate() === dayNum;

              const dayItems = filteredItems.filter(item => {
                const itemDate = new Date(item.start);
                return (
                  itemDate.getFullYear() === year &&
                  itemDate.getMonth() === month &&
                  itemDate.getDate() === dayNum
                );
              });

              return (
                <div
                  key={`day-${dayNum}`}
                  style={{
                    minHeight: '70px',
                    padding: '6px',
                    borderRadius: 'var(--radius-sm)',
                    border: isToday ? '2px solid var(--color-primary-900)' : '1px solid var(--color-border)',
                    backgroundColor: isToday ? 'var(--color-surface-subtle)' : '#ffffff',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '2px',
                    overflow: 'hidden'
                  }}
                >
                  <span style={{ fontSize: '11px', fontWeight: isToday ? 700 : 500, color: isToday ? 'var(--color-primary-900)' : 'var(--color-text-secondary)' }}>
                    {dayNum}
                  </span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', overflow: 'hidden' }}>
                    {dayItems.slice(0, 2).map((item, idx) => {
                      let bgColor = '#e0f2fe';
                      let textColor = '#0369a1';

                      if (item.source_type === 'BILL') {
                        if (item.status === 'PAID') {
                          bgColor = '#d1fae5';
                          textColor = '#047857';
                        } else if (item.status === 'UPCOMING') {
                          bgColor = '#dbeafe';
                          textColor = '#1d4ed8';
                        } else {
                          bgColor = 'var(--status-overdue-subtle, #fef2f2)';
                          textColor = 'var(--status-overdue, #dc2626)';
                        }
                      } else if (item.source_type === 'TASK') {
                        if (item.status === 'COMPLETED') {
                          bgColor = '#d1fae5';
                          textColor = '#047857';
                        } else {
                          bgColor = '#fef3c7';
                          textColor = '#b45309';
                        }
                      } else if (item.source_type === 'INVENTORY') {
                        bgColor = '#cffafe';
                        textColor = '#0e7490';
                      } else if (item.source_type === 'COURSE') {
                        bgColor = '#e0e7ff';
                        textColor = '#4338ca';
                      }

                      return (
                        <div
                          key={idx}
                          onClick={() => handleItemNavigation(item)}
                          style={{
                            fontSize: '10px',
                            padding: '2px 4px',
                            borderRadius: '2px',
                            backgroundColor: bgColor,
                            color: textColor,
                            fontWeight: 600,
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            cursor: 'pointer'
                          }}
                          title={`${item.title} (${item.status})`}
                        >
                          {item.title}
                        </div>
                      );
                    })}
                    {dayItems.length > 2 && (
                      <span style={{ fontSize: '9px', color: 'var(--color-text-tertiary)' }}>
                        +{dayItems.length - 2} more
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      ) : (
        /* Agenda Item List */
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
                Your family calendar has no scheduled events or due items in this category.
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
                  borderLeft: `4px solid ${getItemBorderColor(item)}`,
                  gap: '12px',
                  flexWrap: 'wrap'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px', minWidth: 0, flex: '1 1 240px' }}>
                  <div style={{ width: '36px', height: '36px', borderRadius: '50%', backgroundColor: 'var(--color-surface-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    {getSourceIcon(item)}
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <span
                        onClick={() => handleItemNavigation(item)}
                        style={{
                          fontSize: '14px',
                          fontWeight: 600,
                          color: 'var(--color-text-primary)',
                          cursor: 'pointer',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis'
                        }}
                      >
                        {item.title}
                      </span>
                      {renderStatusBadge(item)}
                    </div>

                    <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                      <span>{new Date(item.start).toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })}</span>
                      {!item.all_day && (
                        <span>• {new Date(item.start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      )}
                      {item.meta_info?.amount && (
                        <span style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>
                          • ₹{item.meta_info.amount}
                        </span>
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

                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
                  {item.source_type === 'EVENT' ? (
                    <>
                      {item.editable && (
                        <button
                          onClick={() => openEditModal(item)}
                          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-secondary)', padding: '8px', borderRadius: 'var(--radius-sm)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                          aria-label={`Edit ${item.title}`}
                          title="Edit Event"
                        >
                          <Edit2 size={16} />
                        </button>
                      )}
                      {item.editable && (
                        <button
                          onClick={() => handleDelete(item)}
                          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-tertiary)', padding: '8px', borderRadius: 'var(--radius-sm)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                          aria-label={`Delete ${item.title}`}
                          title="Delete Event"
                        >
                          <Trash2 size={16} />
                        </button>
                      )}
                    </>
                  ) : (
                    <button
                      onClick={() => handleItemNavigation(item)}
                      style={{
                        background: 'none',
                        border: '1px solid var(--color-border)',
                        borderRadius: 'var(--radius-sm)',
                        padding: '6px 10px',
                        cursor: 'pointer',
                        color: 'var(--color-text-secondary)',
                        fontSize: '12px',
                        fontWeight: 500,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}
                      title={`View in ${item.source_type.toLowerCase()} module`}
                    >
                      <span>View</span>
                      <ExternalLink size={12} />
                    </button>
                  )}
                </div>
              </Card>
            ))
          )}
        </div>
      )}

      {/* Edit Event Modal */}
      {editingItem && (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '16px'
          }}
        >
          <Card style={{ maxWidth: '520px', width: '100%', padding: '24px', maxHeight: '90vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                Edit Calendar Event
              </h3>
              <button
                onClick={() => setEditingItem(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '6px' }}
                aria-label="Close modal"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSaveEdit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                  Event Title *
                </label>
                <Input
                  id="editEventTitle"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                    Date *
                  </label>
                  <Input
                    type="date"
                    value={editDate}
                    onChange={(e) => setEditDate(e.target.value)}
                    required
                  />
                </div>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                    Category
                  </label>
                  <select
                    value={editCategory}
                    onChange={(e) => setEditCategory(e.target.value)}
                    style={{ width: '100%', height: '40px', padding: '0 8px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
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

              {!editAllDay && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div>
                    <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                      Start Time
                    </label>
                    <Input
                      type="time"
                      value={editStartTime}
                      onChange={(e) => setEditStartTime(e.target.value)}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                      End Time
                    </label>
                    <Input
                      type="time"
                      value={editEndTime}
                      onChange={(e) => setEditEndTime(e.target.value)}
                    />
                  </div>
                </div>
              )}

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input
                  type="checkbox"
                  id="editAllDayCheckbox"
                  checked={editAllDay}
                  onChange={(e) => setEditAllDay(e.target.checked)}
                  style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                />
                <label htmlFor="editAllDayCheckbox" style={{ fontSize: '12px', fontWeight: 600, cursor: 'pointer' }}>
                  All-Day Event
                </label>
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                  Location (Optional)
                </label>
                <Input
                  placeholder="e.g. City Clinic, Oakridge School"
                  value={editLocation}
                  onChange={(e) => setEditLocation(e.target.value)}
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                  Recurrence
                </label>
                <select
                  value={editRecurrence}
                  onChange={(e) => setEditRecurrence(e.target.value as any)}
                  style={{ width: '100%', height: '40px', padding: '0 8px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
                >
                  <option value="NONE">Does not repeat</option>
                  <option value="DAILY">Daily</option>
                  <option value="WEEKLY">Weekly</option>
                  <option value="MONTHLY">Monthly</option>
                  <option value="YEARLY">Yearly</option>
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px' }}>
                <Button
                  type="button"
                  variant="destructive"
                  onClick={() => handleDelete(editingItem)}
                  style={{ minHeight: '44px' }}
                >
                  <Trash2 size={16} />
                  <span>Delete</span>
                </Button>

                <div style={{ display: 'flex', gap: '8px' }}>
                  <Button type="button" variant="secondary" onClick={() => setEditingItem(null)} style={{ minHeight: '44px' }}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={isSavingEdit} style={{ minHeight: '44px' }}>
                    {isSavingEdit ? 'Saving...' : 'Save Changes'}
                  </Button>
                </div>
              </div>
            </form>
          </Card>
        </div>
      )}
    </div>
  );
}
