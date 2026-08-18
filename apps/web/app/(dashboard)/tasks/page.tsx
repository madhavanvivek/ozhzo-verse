'use client';

import React, { useEffect, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import {
  Plus,
  Repeat,
  CheckCircle2,
  Trash2,
  Sparkles
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

interface TaskItem {
  id: string;
  title: string;
  description?: string | null;
  category_name?: string | null;
  priority: 'LOW' | 'NORMAL' | 'HIGH';
  status: 'TODO' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';
  assigned_to?: string | null;
  assigned_to_name?: string | null;
  due_date?: string | null;
  is_overdue?: boolean;
  is_due_today?: boolean;
  recurrence_type?: string;
  recurrence_interval_days?: number | null;
  recurrence_strategy?: string;
  completed_by_name?: string | null;
  completed_at?: string | null;
}

interface HomeMemberSummary {
  id: string;
  user_id: string;
  display_name: string;
  role: string;
}

interface UserProfile {
  id: string;
  display_name: string;
}

export default function TasksPage() {
  const [activeHomeId, setActiveHomeId] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [members, setMembers] = useState<HomeMemberSummary[]>([]);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const [activeTab, setActiveTab] = useState<'ALL' | 'TODAY' | 'OVERDUE' | 'UPCOMING' | 'MY_TASKS' | 'COMPLETED'>('ALL');
  const [quickTitle, setQuickTitle] = useState('');
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  // Form State for detailed add
  const [newDesc, setNewDesc] = useState('');
  const [newPriority, setNewPriority] = useState<'LOW' | 'NORMAL' | 'HIGH'>('NORMAL');
  const [newAssignee, setNewAssignee] = useState('');
  const [newDueDate, setNewDueDate] = useState('');
  const [newRecurrenceType, setNewRecurrenceType] = useState('NONE');
  const [newIntervalDays, setNewIntervalDays] = useState('30');
  const [newCategory, setNewCategory] = useState('Maintenance');

  const loadData = async () => {
    setIsLoading(true);
    try {
      const savedHomeId = localStorage.getItem('active_home_id');
      let homeId = savedHomeId;

      const userRes = await apiClient.get<UserProfile>('/users/me');
      setCurrentUser(userRes);

      if (!homeId) {
        const homes = await apiClient.get<Array<{ id: string }>>('/homes');
        if (homes && homes.length > 0) {
          homeId = homes[0].id;
          localStorage.setItem('active_home_id', homeId);
        }
      }

      setActiveHomeId(homeId);

      if (homeId) {
        const [tasksRes, membersRes] = await Promise.allSettled([
          apiClient.get<{ items: TaskItem[] }>(`/homes/${homeId}/tasks`),
          apiClient.get<HomeMemberSummary[]>(`/homes/${homeId}/members`)
        ]);

        if (tasksRes.status === 'fulfilled' && tasksRes.value?.items) {
          setTasks(tasksRes.value.items);
        } else {
          setTasks([]);
        }

        if (membersRes.status === 'fulfilled' && membersRes.value) {
          setMembers(membersRes.value);
        }
      }
    } catch (err) {
      console.error('Failed to load tasks data:', err);
      setTasks([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const commonTemplates = [
    { title: 'Clean Water Filter', cat: 'Maintenance', prio: 'NORMAL', rec: 'CUSTOM_DAYS', interval: 30 },
    { title: 'Service AC', cat: 'Maintenance', prio: 'NORMAL', rec: 'CUSTOM_DAYS', interval: 180 },
    { title: 'Change Bedsheets', cat: 'Cleaning', prio: 'NORMAL', rec: 'WEEKLY', interval: 7 },
    { title: 'Car Service', cat: 'Vehicle', prio: 'NORMAL', rec: 'CUSTOM_DAYS', interval: 180 },
    { title: 'Pay Utility Bill', cat: 'Bills', prio: 'HIGH', rec: 'MONTHLY', interval: 30 },
    { title: 'Water Garden Plants', cat: 'Garden', prio: 'NORMAL', rec: 'DAILY', interval: 1 },
  ];

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickTitle.trim() || !activeHomeId) return;

    const matchedMember = members.find((m) => m.display_name === newAssignee);

    const payload = {
      title: quickTitle.trim(),
      description: newDesc.trim() || undefined,
      category_name: newCategory,
      priority: newPriority,
      assigned_to: matchedMember ? matchedMember.user_id : undefined,
      due_date: newDueDate ? `${newDueDate}T18:00:00Z` : undefined,
      recurrence_type: newRecurrenceType,
      recurrence_interval_days: newRecurrenceType === 'CUSTOM_DAYS' ? parseInt(newIntervalDays) : undefined,
      recurrence_strategy: 'SCHEDULED_DATE'
    };

    try {
      const created = await apiClient.post<TaskItem>(`/homes/${activeHomeId}/tasks`, payload);
      setTasks([created, ...tasks]);
      setQuickTitle('');
      setNewDesc('');
      setNewDueDate('');
      setNewAssignee('');
      setIsDetailOpen(false);
    } catch (err) {
      console.error('Failed to create task:', err);
      alert('Failed to save task to backend.');
    }
  };

  const handleToggleComplete = async (task: TaskItem) => {
    if (!activeHomeId) return;

    try {
      if (task.status !== 'COMPLETED') {
        await apiClient.post(`/homes/${activeHomeId}/tasks/${task.id}/complete`, {});
        setTasks(tasks.map(t => t.id === task.id ? {
          ...t,
          status: 'COMPLETED',
          completed_by_name: currentUser?.display_name || 'Member',
          completed_at: new Date().toISOString()
        } : t));
      } else {
        await apiClient.patch(`/homes/${activeHomeId}/tasks/${task.id}`, { status: 'TODO' });
        setTasks(tasks.map(t => t.id === task.id ? {
          ...t,
          status: 'TODO',
          completed_by_name: null,
          completed_at: null
        } : t));
      }
    } catch (err) {
      console.error('Failed to update task completion:', err);
    }
  };

  const handleDeleteTask = async (id: string) => {
    if (!activeHomeId) return;
    if (!confirm('Are you sure you want to delete this task?')) return;

    try {
      await apiClient.delete(`/homes/${activeHomeId}/tasks/${id}`);
      setTasks(tasks.filter(t => t.id !== id));
    } catch (err) {
      console.error('Failed to delete task:', err);
      alert('Failed to delete task.');
    }
  };

  const totalActive = tasks.filter(t => t.status === 'TODO' || t.status === 'IN_PROGRESS').length;
  const dueTodayCount = tasks.filter(t => t.status !== 'COMPLETED' && t.is_due_today).length;
  const overdueCount = tasks.filter(t => t.status !== 'COMPLETED' && t.is_overdue).length;
  const upcomingCount = tasks.filter(t => t.status !== 'COMPLETED' && !t.is_due_today && !t.is_overdue && t.due_date).length;
  const myTasksCount = tasks.filter(t => t.status !== 'COMPLETED' && (t.assigned_to === currentUser?.id || t.assigned_to_name === currentUser?.display_name)).length;

  const filteredTasks = tasks.filter(t => {
    if (activeTab === 'COMPLETED') return t.status === 'COMPLETED';
    if (t.status === 'COMPLETED') return false;
    if (activeTab === 'TODAY') return t.is_due_today;
    if (activeTab === 'OVERDUE') return t.is_overdue;
    if (activeTab === 'UPCOMING') return !t.is_due_today && !t.is_overdue && t.due_date;
    if (activeTab === 'MY_TASKS') return t.assigned_to === currentUser?.id || t.assigned_to_name === currentUser?.display_name;
    return true; // ALL active
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '960px' }}>
      {/* Header & KPI Summary */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-3)' }}>
          <div>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-primary-900)' }}>
              Home Tasks & Responsibilities
            </h1>
            <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)' }}>
              What needs to be done for our home • Maintenance, routines, and family chore assignments.
            </p>
          </div>
        </div>

        {/* Top KPI Metrics */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 'var(--space-3)' }}>
          <Card
            onClick={() => setActiveTab('TODAY')}
            style={{
              padding: '12px 16px',
              cursor: 'pointer',
              border: activeTab === 'TODAY' ? '2px solid var(--color-primary-900)' : '1px solid var(--color-border)',
              backgroundColor: dueTodayCount > 0 ? 'rgba(239, 68, 68, 0.05)' : 'var(--color-surface-card)'
            }}
          >
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>Due Today</div>
            <div style={{ fontSize: '22px', fontWeight: 700, color: dueTodayCount > 0 ? '#ef4444' : 'var(--color-text-primary)', marginTop: '2px' }}>
              {dueTodayCount}
            </div>
          </Card>

          <Card
            onClick={() => setActiveTab('OVERDUE')}
            style={{
              padding: '12px 16px',
              cursor: 'pointer',
              border: activeTab === 'OVERDUE' ? '2px solid var(--color-primary-900)' : '1px solid var(--color-border)',
              backgroundColor: overdueCount > 0 ? 'rgba(239, 68, 68, 0.05)' : 'var(--color-surface-card)'
            }}
          >
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--status-overdue)' }}>Overdue</div>
            <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--status-overdue)', marginTop: '2px' }}>
              {overdueCount}
            </div>
          </Card>

          <Card
            onClick={() => setActiveTab('MY_TASKS')}
            style={{
              padding: '12px 16px',
              cursor: 'pointer',
              border: activeTab === 'MY_TASKS' ? '2px solid var(--color-primary-900)' : '1px solid var(--color-border)',
              backgroundColor: 'var(--color-surface-card)'
            }}
          >
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>Assigned to Me</div>
            <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--color-primary-900)', marginTop: '2px' }}>
              {myTasksCount}
            </div>
          </Card>

          <Card
            onClick={() => setActiveTab('ALL')}
            style={{
              padding: '12px 16px',
              cursor: 'pointer',
              border: activeTab === 'ALL' ? '2px solid var(--color-primary-900)' : '1px solid var(--color-border)',
              backgroundColor: 'var(--color-surface-card)'
            }}
          >
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>All Active</div>
            <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '2px' }}>
              {totalActive}
            </div>
          </Card>
        </div>
      </div>

      {/* Quick Add Bar & Recurring Templates */}
      <Card style={{ border: '2px solid var(--color-primary-900)', padding: 'var(--space-4)' }}>
        <form onSubmit={handleCreateTask} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
            <input
              type="text"
              placeholder="Add a new task or chore... (e.g. Clean kitchen chimney, service RO)"
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
            <div style={{ display: 'flex', gap: '6px' }}>
              <Button type="submit" size="md">
                <Plus size={16} />
                <span>Add Task</span>
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="md"
                onClick={() => setIsDetailOpen(!isDetailOpen)}
              >
                {isDetailOpen ? 'Simple' : 'Options'}
              </Button>
            </div>
          </div>

          {/* Quick Preset Chips */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
            <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-text-tertiary)' }}>Templates:</span>
            {commonTemplates.map((t, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  setQuickTitle(t.title);
                  setNewCategory(t.cat);
                  setNewPriority(t.prio as any);
                  setNewRecurrenceType(t.rec);
                  if (t.interval) setNewIntervalDays(t.interval.toString());
                  setIsDetailOpen(true);
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
                + {t.title}
              </button>
            ))}
          </div>

          {/* Optional Expanded Fields */}
          {isDetailOpen && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', paddingTop: '8px', borderTop: '1px solid var(--color-border)' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', fontWeight: 600 }}>Assignee</label>
                <select
                  value={newAssignee}
                  onChange={(e) => setNewAssignee(e.target.value)}
                  style={{ height: '36px', padding: '0 8px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
                >
                  <option value="">Unassigned (Home Board)</option>
                  {members.map((m) => (
                    <option key={m.id} value={m.display_name}>
                      {m.display_name} ({m.role})
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', fontWeight: 600 }}>Priority</label>
                <select
                  value={newPriority}
                  onChange={(e) => setNewPriority(e.target.value as any)}
                  style={{ height: '36px', padding: '0 8px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
                >
                  <option value="LOW">Low</option>
                  <option value="NORMAL">Normal</option>
                  <option value="HIGH">High</option>
                </select>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', fontWeight: 600 }}>Category</label>
                <select
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                  style={{ height: '36px', padding: '0 8px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
                >
                  <option value="Maintenance">Maintenance</option>
                  <option value="Cleaning">Cleaning</option>
                  <option value="Bills">Bills</option>
                  <option value="Garden">Garden</option>
                  <option value="Vehicle">Vehicle</option>
                  <option value="Shopping">Shopping</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', fontWeight: 600 }}>Due Date</label>
                <input
                  type="date"
                  value={newDueDate}
                  onChange={(e) => setNewDueDate(e.target.value)}
                  style={{ height: '36px', padding: '0 8px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
                />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', fontWeight: 600 }}>Recurrence</label>
                <select
                  value={newRecurrenceType}
                  onChange={(e) => setNewRecurrenceType(e.target.value)}
                  style={{ height: '36px', padding: '0 8px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
                >
                  <option value="NONE">One-time task</option>
                  <option value="DAILY">Daily</option>
                  <option value="WEEKLY">Weekly</option>
                  <option value="MONTHLY">Monthly</option>
                  <option value="CUSTOM_DAYS">Every X Days</option>
                </select>
              </div>

              {newRecurrenceType === 'CUSTOM_DAYS' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <label style={{ fontSize: '12px', fontWeight: 600 }}>Interval (Days)</label>
                  <input
                    type="number"
                    value={newIntervalDays}
                    onChange={(e) => setNewIntervalDays(e.target.value)}
                    style={{ height: '36px', padding: '0 8px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
                  />
                </div>
              )}
            </div>
          )}
        </form>
      </Card>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: 'var(--space-2)', overflowX: 'auto' }}>
        {[
          { key: 'ALL', label: `All Active (${totalActive})` },
          { key: 'TODAY', label: `Due Today (${dueTodayCount})` },
          { key: 'OVERDUE', label: `Overdue (${overdueCount})` },
          { key: 'UPCOMING', label: `Upcoming (${upcomingCount})` },
          { key: 'MY_TASKS', label: `My Tasks (${myTasksCount})` },
          { key: 'COMPLETED', label: `Completed History` }
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            style={{
              padding: '6px 14px',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              backgroundColor: activeTab === tab.key ? 'var(--color-primary-900)' : 'transparent',
              color: activeTab === tab.key ? 'var(--color-text-inverse)' : 'var(--color-text-secondary)',
              fontWeight: 600,
              fontSize: '13px',
              cursor: 'pointer'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tasks List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
        {isLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {[1, 2, 3].map((i) => (
              <div key={i} style={{ height: '64px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: 'var(--radius-md)', animation: 'pulse 1.5s infinite' }} />
            ))}
          </div>
        ) : filteredTasks.length === 0 ? (
          <Card style={{ padding: 'var(--space-8)', textAlign: 'center' }}>
            <Sparkles size={36} color="var(--status-in-stock)" style={{ margin: '0 auto 10px' }} />
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-primary-900)' }}>
              No tasks found in this view
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
              Everything in this category is completed or no tasks have been created.
            </p>
          </Card>
        ) : (
          filteredTasks.map((t) => {
            const isCompleted = t.status === 'COMPLETED';

            return (
              <Card
                key={t.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px 16px',
                  opacity: isCompleted ? 0.7 : 1,
                  borderLeft: t.is_overdue
                    ? '4px solid var(--status-overdue)'
                    : t.is_due_today
                    ? '4px solid var(--status-low-stock)'
                    : isCompleted
                    ? '4px solid var(--status-in-stock)'
                    : '1px solid var(--color-border-subtle)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  <button
                    onClick={() => handleToggleComplete(t)}
                    style={{
                      width: '24px',
                      height: '24px',
                      borderRadius: '6px',
                      border: isCompleted ? 'none' : '2px solid var(--color-border-strong)',
                      backgroundColor: isCompleted ? 'var(--status-in-stock)' : 'transparent',
                      color: 'white',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      cursor: 'pointer'
                    }}
                  >
                    {isCompleted && <CheckCircle2 size={16} />}
                  </button>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                    <div style={{
                      fontSize: '14px',
                      fontWeight: 600,
                      color: 'var(--color-text-primary)',
                      textDecoration: isCompleted ? 'line-through' : 'none'
                    }}>
                      {t.title}
                    </div>

                    <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                      {t.category_name && <span>{t.category_name}</span>}
                      {t.assigned_to_name && (
                        <span>• Assigned: <strong>{t.assigned_to_name}</strong></span>
                      )}
                      {t.due_date && (
                        <span>• Due: {new Date(t.due_date).toLocaleDateString([], { month: 'short', day: 'numeric' })}</span>
                      )}
                      {t.recurrence_type && t.recurrence_type !== 'NONE' && (
                        <span style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                          • <Repeat size={12} /> {t.recurrence_type}
                        </span>
                      )}
                      {isCompleted && t.completed_by_name && (
                        <span style={{ color: 'var(--status-in-stock)' }}>
                          • Done by {t.completed_by_name}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Badge variant={t.priority === 'HIGH' ? 'overdue' : t.priority === 'LOW' ? 'neutral' : 'low-stock'}>
                    {t.priority}
                  </Badge>

                  <button
                    onClick={() => handleDeleteTask(t.id)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-tertiary)', padding: '4px' }}
                    aria-label="Delete task"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
}
