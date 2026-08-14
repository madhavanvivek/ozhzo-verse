'use client';

import React, { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import {
  CheckSquare,
  Plus,
  Calendar,
  Clock,
  User,
  Repeat,
  CheckCircle2,
  AlertTriangle,
  Trash2,
  Sparkles,
  RotateCcw,
  Tag,
  Wrench
} from 'lucide-react';

interface TaskItem {
  id: string;
  title: string;
  description?: string | null;
  category_name?: string | null;
  priority: 'LOW' | 'NORMAL' | 'HIGH';
  status: 'TODO' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';
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

export default function TasksPage() {
  const [activeTab, setActiveTab] = useState<'ALL' | 'TODAY' | 'OVERDUE' | 'UPCOMING' | 'MY_TASKS' | 'COMPLETED'>('ALL');
  const [quickTitle, setQuickTitle] = useState('');
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  const [tasks, setTasks] = useState<TaskItem[]>([
    {
      id: 'task-1',
      title: 'Clean RO Water Filter',
      description: 'Replace 5-micron spun candle and sanitize pre-filter bowl',
      category_name: 'Maintenance',
      priority: 'HIGH',
      status: 'TODO',
      assigned_to_name: 'Karthika',
      due_date: new Date().toISOString(),
      is_due_today: true,
      is_overdue: false,
      recurrence_type: 'CUSTOM_DAYS',
      recurrence_interval_days: 30,
      recurrence_strategy: 'COMPLETION_DATE'
    },
    {
      id: 'task-2',
      title: 'Pay School Tuition Fee',
      description: 'Monthly tuition payment via net banking',
      category_name: 'Bills',
      priority: 'HIGH',
      status: 'TODO',
      assigned_to_name: 'Vivek',
      due_date: new Date(Date.now() - 86400000 * 2).toISOString(),
      is_overdue: true,
      is_due_today: false,
      recurrence_type: 'MONTHLY',
      recurrence_strategy: 'SCHEDULED_DATE'
    },
    {
      id: 'task-3',
      title: 'AC Service & Compressor Check',
      description: 'Clean air filters and check outdoor refrigerant pressure',
      category_name: 'Maintenance',
      priority: 'NORMAL',
      status: 'TODO',
      assigned_to_name: 'Vivek',
      due_date: new Date(Date.now() + 86400000 * 6).toISOString(),
      is_overdue: false,
      is_due_today: false,
      recurrence_type: 'CUSTOM_DAYS',
      recurrence_interval_days: 180,
      recurrence_strategy: 'COMPLETION_DATE'
    },
    {
      id: 'task-4',
      title: 'Change Bedsheets & Pillowcases',
      description: 'Wash and replace master bedroom and guest linens',
      category_name: 'Cleaning',
      priority: 'NORMAL',
      status: 'COMPLETED',
      assigned_to_name: 'Karthika',
      due_date: new Date(Date.now() - 86400000).toISOString(),
      is_overdue: false,
      is_due_today: false,
      recurrence_type: 'WEEKLY',
      recurrence_interval_days: 7,
      completed_by_name: 'Karthika',
      completed_at: new Date().toISOString()
    }
  ]);

  // Form State for detailed add
  const [newDesc, setNewDesc] = useState('');
  const [newPriority, setNewPriority] = useState<'LOW' | 'NORMAL' | 'HIGH'>('NORMAL');
  const [newAssignee, setNewAssignee] = useState('');
  const [newDueDate, setNewDueDate] = useState('');
  const [newRecurrenceType, setNewRecurrenceType] = useState('NONE');
  const [newIntervalDays, setNewIntervalDays] = useState('30');
  const [newCategory, setNewCategory] = useState('Maintenance');

  const commonTemplates = [
    { title: 'Clean Water Filter', cat: 'Maintenance', prio: 'NORMAL', rec: 'CUSTOM_DAYS', interval: 30 },
    { title: 'Service AC', cat: 'Maintenance', prio: 'NORMAL', rec: 'CUSTOM_DAYS', interval: 180 },
    { title: 'Change Bedsheets', cat: 'Cleaning', prio: 'NORMAL', rec: 'WEEKLY', interval: 7 },
    { title: 'Car Service', cat: 'Vehicle', prio: 'NORMAL', rec: 'CUSTOM_DAYS', interval: 180 },
    { title: 'Pay School Fee', cat: 'Bills', prio: 'HIGH', rec: 'MONTHLY', interval: 30 },
    { title: 'Water Garden Plants', cat: 'Garden', prio: 'NORMAL', rec: 'DAILY', interval: 1 },
  ];

  const handleQuickAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickTitle.trim()) return;

    const newTask: TaskItem = {
      id: `task-${Date.now()}`,
      title: quickTitle.trim(),
      description: newDesc.trim() || null,
      category_name: newCategory,
      priority: newPriority,
      status: 'TODO',
      assigned_to_name: newAssignee || null,
      due_date: newDueDate ? new Date(newDueDate).toISOString() : null,
      recurrence_type: newRecurrenceType,
      recurrence_interval_days: newRecurrenceType === 'CUSTOM_DAYS' ? parseInt(newIntervalDays) : undefined,
      is_overdue: false,
      is_due_today: newDueDate ? new Date(newDueDate).toDateString() === new Date().toDateString() : false
    };

    setTasks([newTask, ...tasks]);
    setQuickTitle('');
    setNewDesc('');
    setNewDueDate('');
    setNewRecurrenceType('NONE');
    setIsDetailOpen(false);
  };

  const handleComplete = (id: string) => {
    setTasks(tasks.map(t => {
      if (t.id === id) {
        return {
          ...t,
          status: 'COMPLETED',
          completed_by_name: 'You',
          completed_at: new Date().toISOString()
        };
      }
      return t;
    }));
  };

  const handleReopen = (id: string) => {
    setTasks(tasks.map(t => t.id === id ? { ...t, status: 'TODO', completed_by_name: null, completed_at: null } : t));
  };

  const handleDelete = (id: string) => {
    setTasks(tasks.filter(t => t.id !== id));
  };

  const totalActive = tasks.filter(t => t.status === 'TODO' || t.status === 'IN_PROGRESS').length;
  const dueTodayCount = tasks.filter(t => t.status !== 'COMPLETED' && t.is_due_today).length;
  const overdueCount = tasks.filter(t => t.status !== 'COMPLETED' && t.is_overdue).length;
  const upcomingCount = tasks.filter(t => t.status !== 'COMPLETED' && !t.is_due_today && !t.is_overdue && t.due_date).length;
  const myTasksCount = tasks.filter(t => t.status !== 'COMPLETED' && t.assigned_to_name === 'Vivek').length;

  const filteredTasks = tasks.filter(t => {
    if (activeTab === 'COMPLETED') return t.status === 'COMPLETED';
    if (t.status === 'COMPLETED') return false;
    if (activeTab === 'TODAY') return t.is_due_today;
    if (activeTab === 'OVERDUE') return t.is_overdue;
    if (activeTab === 'UPCOMING') return !t.is_due_today && !t.is_overdue && t.due_date;
    if (activeTab === 'MY_TASKS') return t.assigned_to_name === 'Vivek';
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
              backgroundColor: overdueCount > 0 ? 'rgba(245, 158, 11, 0.08)' : 'var(--color-surface-card)'
            }}
          >
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>Overdue</div>
            <div style={{ fontSize: '22px', fontWeight: 700, color: overdueCount > 0 ? '#f59e0b' : 'var(--color-text-primary)', marginTop: '2px' }}>
              {overdueCount}
            </div>
          </Card>

          <Card
            onClick={() => setActiveTab('UPCOMING')}
            style={{
              padding: '12px 16px',
              cursor: 'pointer',
              border: activeTab === 'UPCOMING' ? '2px solid var(--color-primary-900)' : '1px solid var(--color-border)'
            }}
          >
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>Upcoming</div>
            <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '2px' }}>
              {upcomingCount}
            </div>
          </Card>

          <Card
            onClick={() => setActiveTab('MY_TASKS')}
            style={{
              padding: '12px 16px',
              cursor: 'pointer',
              border: activeTab === 'MY_TASKS' ? '2px solid var(--color-primary-900)' : '1px solid var(--color-border)'
            }}
          >
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>My Tasks</div>
            <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--color-primary-900)', marginTop: '2px' }}>
              {myTasksCount}
            </div>
          </Card>

          <Card
            onClick={() => setActiveTab('ALL')}
            style={{
              padding: '12px 16px',
              cursor: 'pointer',
              border: activeTab === 'ALL' ? '2px solid var(--color-primary-900)' : '1px solid var(--color-border)'
            }}
          >
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>Total Active</div>
            <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '2px' }}>
              {totalActive}
            </div>
          </Card>
        </div>
      </div>

      {/* Quick Add Bar & Common Templates */}
      <Card style={{ padding: '16px 20px', border: '2px solid var(--color-primary-900)' }}>
        <form onSubmit={handleQuickAdd} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <input
              type="text"
              placeholder="+ Quick add task (e.g. Clean water filter, Service AC, Mop floor)..."
              value={quickTitle}
              onChange={(e) => setQuickTitle(e.target.value)}
              style={{
                flex: 1,
                height: '42px',
                padding: '0 14px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border-strong)',
                fontSize: '14px',
                backgroundColor: 'var(--color-surface-card)'
              }}
              required
            />
            <Button type="submit">
              <Plus size={16} />
              <span>Add</span>
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsDetailOpen(!isDetailOpen)}
            >
              {isDetailOpen ? 'Simple' : 'Options ▾'}
            </Button>
          </div>

          {/* Quick Preset Chips */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', marginRight: '4px' }}>
              Common Routines:
            </span>
            {commonTemplates.map(tpl => (
              <button
                key={tpl.title}
                type="button"
                onClick={() => {
                  setQuickTitle(tpl.title);
                  setNewCategory(tpl.cat);
                  setNewPriority(tpl.prio as any);
                  setNewRecurrenceType(tpl.rec);
                  setNewIntervalDays(tpl.interval.toString());
                  setIsDetailOpen(true);
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
                + {tpl.title}
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
                  <option value="Vivek">Vivek</option>
                  <option value="Karthika">Karthika</option>
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
                  <option value="NONE">One-time</option>
                  <option value="DAILY">Daily</option>
                  <option value="WEEKLY">Weekly (7 days)</option>
                  <option value="MONTHLY">Monthly</option>
                  <option value="CUSTOM_DAYS">Custom Interval (Days)</option>
                </select>
              </div>
            </div>
          )}
        </form>
      </Card>

      {/* Filter Tabs */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: 'var(--space-2)', overflowX: 'auto' }}>
        {[
          { id: 'ALL', label: 'All Active' },
          { id: 'TODAY', label: `Today (${dueTodayCount})` },
          { id: 'OVERDUE', label: `Overdue (${overdueCount})` },
          { id: 'UPCOMING', label: `Upcoming (${upcomingCount})` },
          { id: 'MY_TASKS', label: `My Tasks (${myTasksCount})` },
          { id: 'COMPLETED', label: 'History' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            style={{
              padding: '6px 14px',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              backgroundColor: activeTab === tab.id ? 'var(--color-primary-900)' : 'transparent',
              color: activeTab === tab.id ? 'var(--color-text-inverse)' : 'var(--color-text-secondary)',
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

      {/* Task Checklist Items */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
        {filteredTasks.length === 0 ? (
          <Card style={{ padding: 'var(--space-12) var(--space-4)', textAlign: 'center' }}>
            <Sparkles size={36} color="var(--status-in-stock)" style={{ margin: '0 auto 10px' }} />
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-primary-900)' }}>
              {activeTab === 'COMPLETED' ? 'No completed tasks yet' : 'No pending tasks in this view'}
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
              Everything for our home is up to date!
            </p>
          </Card>
        ) : (
          filteredTasks.map((task) => (
            <Card
              key={task.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '14px 18px',
                opacity: task.status === 'COMPLETED' ? 0.75 : 1,
                borderLeft: task.is_overdue
                  ? '4px solid #ef4444'
                  : task.is_due_today
                  ? '4px solid #f59e0b'
                  : '1px solid var(--color-border)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px', flex: 1 }}>
                <button
                  onClick={() => task.status === 'COMPLETED' ? handleReopen(task.id) : handleComplete(task.id)}
                  style={{
                    marginTop: '2px',
                    width: '24px',
                    height: '24px',
                    borderRadius: '6px',
                    border: task.status === 'COMPLETED' ? 'none' : '2px solid var(--color-border-strong)',
                    backgroundColor: task.status === 'COMPLETED' ? 'var(--status-in-stock)' : 'transparent',
                    color: 'white',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer'
                  }}
                >
                  {task.status === 'COMPLETED' && <CheckCircle2 size={16} />}
                </button>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-text-primary)', textDecoration: task.status === 'COMPLETED' ? 'line-through' : 'none' }}>
                      {task.title}
                    </span>

                    {task.category_name && (
                      <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '4px', background: 'var(--color-surface-hover)', color: 'var(--color-text-secondary)', fontWeight: 500 }}>
                        {task.category_name}
                      </span>
                    )}

                    {task.is_overdue && (
                      <span style={{ fontSize: '11px', padding: '2px 6px', borderRadius: '4px', background: '#fee2e2', color: '#b91c1c', fontWeight: 700 }}>
                        OVERDUE
                      </span>
                    )}
                    {task.is_due_today && (
                      <span style={{ fontSize: '11px', padding: '2px 6px', borderRadius: '4px', background: '#fef3c7', color: '#b45309', fontWeight: 700 }}>
                        DUE TODAY
                      </span>
                    )}
                  </div>

                  {task.description && (
                    <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
                      {task.description}
                    </div>
                  )}

                  <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '12px', marginTop: '4px', fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <User size={13} />
                      <span>{task.assigned_to_name ? task.assigned_to_name : 'Unassigned'}</span>
                    </span>

                    {task.due_date && (
                      <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Clock size={13} />
                        <span>Due {new Date(task.due_date).toLocaleDateString()}</span>
                      </span>
                    )}

                    {task.recurrence_type && task.recurrence_type !== 'NONE' && (
                      <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--color-primary-900)', fontWeight: 600 }}>
                        <Repeat size={13} />
                        <span>Repeats {task.recurrence_type === 'CUSTOM_DAYS' ? `every ${task.recurrence_interval_days || 30} days` : task.recurrence_type.toLowerCase()}</span>
                      </span>
                    )}

                    {task.completed_by_name && (
                      <span style={{ color: 'var(--status-in-stock)', fontWeight: 600 }}>
                        Completed by {task.completed_by_name}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Badge variant={task.priority === 'HIGH' ? 'overdue' : 'neutral'}>
                  {task.priority}
                </Badge>

                {task.status === 'COMPLETED' ? (
                  <button
                    onClick={() => handleReopen(task.id)}
                    title="Reopen Task"
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-secondary)', padding: '4px' }}
                  >
                    <RotateCcw size={16} />
                  </button>
                ) : (
                  <button
                    onClick={() => handleDelete(task.id)}
                    title="Delete Task"
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-tertiary)', padding: '4px' }}
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
