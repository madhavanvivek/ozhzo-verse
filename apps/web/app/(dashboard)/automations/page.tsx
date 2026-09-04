'use client';

import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Play,
  Pause,
  Plus,
  Trash2,
  CheckCircle2,
  Zap,
  TrendingUp,
  X,
  Check,
  Loader2,
  Brain,
  Sliders,
  FileText
} from 'lucide-react';

import { apiClient } from '@/lib/apiClient';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';


interface Automation {
  id: string;
  home_id: string;
  name: string;
  description?: string;
  enabled: boolean;
  trigger_type: string;
  conditions: Record<string, any>;
  actions: Array<Record<string, any>>;
  schedule: Record<string, any>;
  execution_policy: Record<string, any>;
  last_run_at?: string;
  next_run_at?: string;
  status: string;
  failure_count: number;
  consecutive_failures: number;
  created_at: string;
}

interface Execution {
  id: string;
  automation_id: string;
  trigger_event: Record<string, any>;
  evaluated_conditions: Record<string, any>;
  actions_attempted: number;
  actions_succeeded: number;
  actions_failed: number;
  duration_ms: number;
  status: string;
  error_details?: string;
  created_at: string;
}

interface Recommendation {
  id: string;
  domain: string;
  title: string;
  reason: string;
  confidence: number;
  source_category: string;
  suggested_action?: Record<string, any>;
  status: string;
}

interface HouseholdMemory {
  id: string;
  category: string;
  content: string;
  source: string;
  confidence: number;
  status: string;
  created_at: string;
}

interface PersonalizationPrefs {
  personalization_enabled: boolean;
  ai_memory_enabled: boolean;
  reminder_timing_preference: string;
  recommendation_frequency: string;
  digest_enabled: boolean;
  digest_day_of_week: string;
}

interface HouseholdDigest {
  home_name: string;
  period_start: string;
  period_end: string;
  tasks_completed_count: number;
  tasks_overdue_count: number;
  bills_paid_count: number;
  bills_upcoming_count: number;
  shopping_items_purchased_count: number;
  inventory_low_count: number;
  automations_executed_count: number;
  highlights: string[];
  key_recommendations: string[];
}

interface DashboardSummary {
  home_name: string;
  active_automations_count: number;
  total_automations_count: number;
  recent_executions_count: number;
  failed_automations_count: number;
  active_automations: Automation[];
  recent_executions: Execution[];
  recommendations: Recommendation[];
  predicted_patterns: Array<{ pattern_type: string; insight: string; confidence: number }>;
}

export default function AutomationsPage() {
  const [activeTab, setActiveTab] = useState<'automations' | 'insights' | 'history' | 'memory'>('automations');
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [memories, setMemories] = useState<HouseholdMemory[]>([]);
  const [personalization, setPersonalization] = useState<PersonalizationPrefs | null>(null);
  const [digest, setDigest] = useState<HouseholdDigest | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [runningAutoId, setRunningAutoId] = useState<string | null>(null);

  // AI Modal States
  const [isAiModalOpen, setIsAiModalOpen] = useState(false);
  const [aiPrompt, setAiPrompt] = useState('');
  const [isAiGenerating, setIsAiGenerating] = useState(false);
  const [aiProposal, setAiProposal] = useState<any | null>(null);

  // Create Manual Modal
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [newTrigger, setNewTrigger] = useState('INVENTORY_LOW');
  const [newActionType, setNewActionType] = useState('ADD_SHOPPING_ITEM');
  const [newItemName, setNewItemName] = useState('Milk');

  // New Memory Modal
  const [newMemoryContent, setNewMemoryContent] = useState('');
  const [newMemoryCategory, setNewMemoryCategory] = useState('PREFERENCE');

  const fetchDashboard = async () => {
    setIsLoading(true);
    try {
      const activeHomeId = localStorage.getItem('active_home_id');
      if (!activeHomeId) return;

      const res = await apiClient.get<DashboardSummary>(`/homes/${activeHomeId}/intelligence/dashboard`);
      setDashboard(res);

      // Fetch Stage 5 memories & personalization in parallel
      const [memsRes, prefsRes, digRes] = await Promise.all([
        apiClient.get<HouseholdMemory[]>(`/homes/${activeHomeId}/memories`).catch(() => []),
        apiClient.get<PersonalizationPrefs>(`/homes/${activeHomeId}/personalization`).catch(() => null),
        apiClient.get<HouseholdDigest>(`/homes/${activeHomeId}/intelligence/digest`).catch(() => null),
      ]);
      setMemories(memsRes || []);
      setPersonalization(prefsRes);
      setDigest(digRes);
    } catch {
      // Handled gracefully
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
    const handleHomeChange = () => fetchDashboard();
    window.addEventListener('home-changed', handleHomeChange);
    return () => window.removeEventListener('home-changed', handleHomeChange);
  }, []);

  const handleToggleEnable = async (auto: Automation) => {
    try {
      const endpoint = auto.enabled ? `/homes/${auto.home_id}/automations/${auto.id}/disable` : `/homes/${auto.home_id}/automations/${auto.id}/enable`;
      await apiClient.post(endpoint, {});
      fetchDashboard();
    } catch {
      // Ignored
    }
  };

  const handleRunNow = async (auto: Automation) => {
    setRunningAutoId(auto.id);
    try {
      await apiClient.post(`/homes/${auto.home_id}/automations/${auto.id}/run`, {});
      await fetchDashboard();
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new Event('home-changed'));
      }
    } catch {
      // Ignored
    } finally {
      setRunningAutoId(null);
    }
  };

  const handleDelete = async (auto: Automation) => {
    if (!confirm(`Delete automation "${auto.name}"?`)) return;
    try {
      await apiClient.delete(`/homes/${auto.home_id}/automations/${auto.id}`);
      fetchDashboard();
    } catch {
      // Ignored
    }
  };

  const handleAddMemory = async () => {
    if (!newMemoryContent.trim()) return;
    try {
      const activeHomeId = localStorage.getItem('active_home_id');
      if (!activeHomeId) return;

      await apiClient.post(`/homes/${activeHomeId}/memories`, {
        category: newMemoryCategory,
        content: newMemoryContent.trim(),
        source: 'USER_PROVIDED',
        confidence: 1.0
      });
      setNewMemoryContent('');
      fetchDashboard();
    } catch {
      // Ignored
    }
  };

  const handleDeleteMemory = async (memId: string) => {
    try {
      const activeHomeId = localStorage.getItem('active_home_id');
      if (!activeHomeId) return;
      await apiClient.delete(`/homes/${activeHomeId}/memories/${memId}`);
      fetchDashboard();
    } catch {
      // Ignored
    }
  };

  const handleUpdatePrefs = async (patch: Partial<PersonalizationPrefs>) => {
    try {
      const activeHomeId = localStorage.getItem('active_home_id');
      if (!activeHomeId) return;
      const updated = await apiClient.patch<PersonalizationPrefs>(`/homes/${activeHomeId}/personalization`, patch);
      setPersonalization(updated);
    } catch {
      // Ignored
    }
  };

  const handleGenerateAiProposal = async () => {
    if (!aiPrompt.trim()) return;
    setIsAiGenerating(true);
    try {
      const activeHomeId = localStorage.getItem('active_home_id');
      const res = await apiClient.post<any>(`/homes/${activeHomeId}/ai/automations/propose`, {
        prompt: aiPrompt
      });
      setAiProposal(res);
    } catch {
      // Ignored
    } finally {
      setIsAiGenerating(false);
    }
  };

  const handleConfirmAiProposal = async () => {
    if (!aiProposal) return;
    try {
      const activeHomeId = localStorage.getItem('active_home_id');
      await apiClient.post(`/homes/${activeHomeId}/automations`, {
        name: aiProposal.name,
        description: aiProposal.description,
        enabled: true,
        trigger_type: aiProposal.trigger_type,
        conditions: aiProposal.conditions || {},
        actions: aiProposal.actions || [],
        schedule: aiProposal.schedule || {}
      });
      setIsAiModalOpen(false);
      setAiProposal(null);
      setAiPrompt('');
      fetchDashboard();
    } catch {
      // Ignored
    }
  };

  const handleCreateManual = async () => {
    if (!newName.trim()) return;
    try {
      const activeHomeId = localStorage.getItem('active_home_id');
      let actions: any[] = [];
      let conditions: any = {};

      if (newActionType === 'ADD_SHOPPING_ITEM') {
        actions = [{ type: 'ADD_SHOPPING_ITEM', target_item_name: newItemName, quantity: 1, unit: 'pcs' }];
      } else if (newActionType === 'CREATE_TASK') {
        actions = [{ type: 'CREATE_TASK', target_item_name: `Restock ${newItemName}`, priority: 'NORMAL' }];
      }

      await apiClient.post(`/homes/${activeHomeId}/automations`, {
        name: newName,
        description: `Automated rule for ${newItemName}`,
        enabled: true,
        trigger_type: newTrigger,
        conditions: conditions,
        actions: actions,
        schedule: {}
      });

      setIsCreateModalOpen(false);
      setNewName('');
      fetchDashboard();
    } catch {
      // Ignored
    }
  };

  const handleAcceptRec = async (recId: string) => {
    try {
      const activeHomeId = localStorage.getItem('active_home_id');
      await apiClient.post(`/homes/${activeHomeId}/intelligence/recommendations/${recId}/accept`, {});
      fetchDashboard();
    } catch {
      // Ignored
    }
  };

  const handleDismissRec = async (recId: string) => {
    try {
      const activeHomeId = localStorage.getItem('active_home_id');
      await apiClient.post(`/homes/${activeHomeId}/intelligence/recommendations/${recId}/dismiss`, {});
      fetchDashboard();
    } catch {
      // Ignored
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Top Header */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '16px',
          marginBottom: '24px'
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 style={{ fontSize: '24px', fontWeight: 800, color: 'var(--color-primary-900)', margin: 0 }}>
              Household Automations & Insights
            </h1>
            <Badge variant="neutral">Stage 4 Intelligence</Badge>
            <Badge variant="completed">Stage 5 Intelligence</Badge>
          </div>



          <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
            Deterministic household event rules, long-term memory vault, proactive recommendations, and weekly digests.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setIsAiModalOpen(true)}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Sparkles size={16} color="var(--color-primary-900)" />
            <span>AI Rule Generator</span>
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => setIsCreateModalOpen(true)}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Plus size={16} />
            <span>New Automation</span>
          </Button>
        </div>
      </div>

      {/* Intelligence KPI Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '16px',
          marginBottom: '24px'
        }}
      >
        <Card style={{ padding: '16px', display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              backgroundColor: 'rgba(234, 88, 12, 0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ea580c'
            }}
          >
            <Zap size={22} />
          </div>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>
              Active Rules
            </div>
            <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--color-primary-900)' }}>
              {dashboard?.active_automations_count || 0}
            </div>
          </div>
        </Card>

        <Card style={{ padding: '16px', display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--status-in-stock)'
            }}
          >
            <CheckCircle2 size={22} />
          </div>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>
              Recent Executions
            </div>
            <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--color-primary-900)' }}>
              {dashboard?.recent_executions_count || 0}
            </div>
          </div>
        </Card>

        <Card style={{ padding: '16px', display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              backgroundColor: 'rgba(59, 130, 246, 0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--color-primary-900)'
            }}
          >
            <TrendingUp size={22} />
          </div>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>
              Proactive Insights
            </div>
            <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--color-primary-900)' }}>
              {dashboard?.recommendations?.length || 0}
            </div>
          </div>
        </Card>

        <Card style={{ padding: '16px', display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--status-in-stock)'
            }}
          >
            <Sparkles size={22} />
          </div>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>
              Execution Reliability
            </div>
            <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--status-in-stock)' }}>
              Optimal
            </div>
          </div>
        </Card>

        <Card style={{ padding: '16px', display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              backgroundColor: 'rgba(139, 92, 246, 0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#8b5cf6'
            }}
          >
            <Brain size={22} />
          </div>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>
              Stored Memories
            </div>
            <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--color-primary-900)' }}>
              {memories.length}
            </div>
          </div>
        </Card>
      </div>


      {/* Tabs */}
      <div
        style={{
          display: 'flex',
          borderBottom: '1px solid var(--color-border-subtle)',
          marginBottom: '20px',
          gap: '20px',
          overflowX: 'auto'
        }}
      >
        <button
          onClick={() => setActiveTab('automations')}
          style={{
            background: 'none',
            border: 'none',
            padding: '10px 4px',
            fontSize: '14px',
            fontWeight: activeTab === 'automations' ? 700 : 500,
            color: activeTab === 'automations' ? 'var(--color-primary-900)' : 'var(--color-text-secondary)',
            borderBottom: activeTab === 'automations' ? '2px solid var(--color-primary-900)' : '2px solid transparent',
            cursor: 'pointer'
          }}
        >
          Automations ({dashboard?.active_automations?.length || 0})
        </button>

        <button
          onClick={() => setActiveTab('insights')}
          style={{
            background: 'none',
            border: 'none',
            padding: '10px 4px',
            fontSize: '14px',
            fontWeight: activeTab === 'insights' ? 700 : 500,
            color: activeTab === 'insights' ? 'var(--color-primary-900)' : 'var(--color-text-secondary)',
            borderBottom: activeTab === 'insights' ? '2px solid var(--color-primary-900)' : '2px solid transparent',
            cursor: 'pointer'
          }}
        >
          Predictive Insights ({dashboard?.recommendations?.length || 0})
        </button>

        <button
          onClick={() => setActiveTab('memory')}
          style={{
            background: 'none',
            border: 'none',
            padding: '10px 4px',
            fontSize: '14px',
            fontWeight: activeTab === 'memory' ? 700 : 500,
            color: activeTab === 'memory' ? 'var(--color-primary-900)' : 'var(--color-text-secondary)',
            borderBottom: activeTab === 'memory' ? '2px solid var(--color-primary-900)' : '2px solid transparent',
            cursor: 'pointer'
          }}
        >
          Memory & Personalization ({memories.length})
        </button>

        <button
          onClick={() => setActiveTab('history')}
          style={{
            background: 'none',
            border: 'none',
            padding: '10px 4px',
            fontSize: '14px',
            fontWeight: activeTab === 'history' ? 700 : 500,
            color: activeTab === 'history' ? 'var(--color-primary-900)' : 'var(--color-text-secondary)',
            borderBottom: activeTab === 'history' ? '2px solid var(--color-primary-900)' : '2px solid transparent',
            cursor: 'pointer'
          }}
        >
          Execution History ({dashboard?.recent_executions?.length || 0})
        </button>
      </div>

      {/* TAB 1: AUTOMATIONS LIST */}
      {activeTab === 'automations' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {isLoading ? (
            <div style={{ padding: '32px', textAlign: 'center', color: 'var(--color-text-secondary)' }}>
              Loading household automations...
            </div>
          ) : !dashboard?.active_automations || dashboard.active_automations.length === 0 ? (
            <Card style={{ padding: '40px', textAlign: 'center' }}>
              <Zap size={32} color="var(--color-text-tertiary)" style={{ margin: '0 auto 12px' }} />
              <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                No active automations yet
              </div>
              <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '4px', marginBottom: '16px' }}>
                Set up deterministic rules like auto-restocking groceries or monthly bill reminders.
              </p>
              <Button variant="primary" size="sm" onClick={() => setIsAiModalOpen(true)}>
                <Sparkles size={16} />
                <span>Generate Rule with AI</span>
              </Button>
            </Card>
          ) : (
            dashboard.active_automations.map((auto) => (
              <Card key={auto.id} style={{ padding: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px' }}>
                <div style={{ flex: 1, minWidth: '240px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                      {auto.name}
                    </span>
                    <Badge variant={auto.enabled ? 'in-stock' : 'neutral'}>
                      {auto.enabled ? 'ACTIVE' : 'PAUSED'}
                    </Badge>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
                    Trigger: <span style={{ fontWeight: 600 }}>{auto.trigger_type}</span> | Actions: {auto.actions?.length || 0}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleRunNow(auto)}
                    disabled={runningAutoId === auto.id}
                  >
                    {runningAutoId === auto.id ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                    <span>Run Now</span>
                  </Button>

                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleToggleEnable(auto)}
                  >
                    {auto.enabled ? <Pause size={14} /> : <Play size={14} />}
                    <span>{auto.enabled ? 'Pause' : 'Enable'}</span>
                  </Button>

                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleDelete(auto)}
                    style={{ color: '#ef4444' }}
                  >
                    <Trash2 size={14} />
                  </Button>
                </div>
              </Card>
            ))
          )}
        </div>
      )}

      {/* TAB 2: PREDICTIVE INSIGHTS */}
      {activeTab === 'insights' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {dashboard?.predicted_patterns && dashboard.predicted_patterns.length > 0 && (
            <Card style={{ padding: '16px', backgroundColor: 'var(--color-surface-subtle)' }}>
              <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-primary-900)', marginBottom: '8px' }}>
                Detected Household Cycles & Patterns
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {dashboard.predicted_patterns.map((p, idx) => (
                  <div key={idx} style={{ fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Badge variant="neutral">{p.pattern_type}</Badge>
                    <span>{p.insight}</span>
                    <span style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>({Math.round(p.confidence * 100)}% pattern confidence)</span>
                  </div>
                ))}
              </div>

            </Card>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {dashboard?.recommendations?.map((rec) => (
              <Card key={rec.id} style={{ padding: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px' }}>
                <div style={{ flex: 1, minWidth: '260px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Badge variant="neutral">{rec.domain}</Badge>
                    <span style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                      {rec.title}
                    </span>
                  </div>
                  <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
                    {rec.reason}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '8px' }}>
                  <Button size="sm" variant="primary" onClick={() => handleAcceptRec(rec.id)}>
                    <Check size={14} />
                    <span>Accept & Execute</span>
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => handleDismissRec(rec.id)}>
                    <X size={14} />
                    <span>Dismiss</span>
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: HOUSEHOLD MEMORY & PERSONALIZATION */}
      {activeTab === 'memory' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Section A: Weekly Intelligence Digest */}
          {digest && (
            <Card style={{ padding: '20px', border: '1.5px solid var(--color-primary-900)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                <FileText size={18} color="var(--color-primary-900)" />
                <span style={{ fontSize: '16px', fontWeight: 800, color: 'var(--color-primary-900)' }}>
                  This Week at {digest.home_name}
                </span>
                <Badge variant="completed">Digest</Badge>
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                  gap: '12px',
                  marginBottom: '16px'
                }}
              >
                <div style={{ padding: '10px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: '8px' }}>
                  <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>Tasks Completed</div>
                  <div style={{ fontSize: '18px', fontWeight: 800 }}>{digest.tasks_completed_count}</div>
                </div>
                <div style={{ padding: '10px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: '8px' }}>
                  <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>Bills Paid</div>
                  <div style={{ fontSize: '18px', fontWeight: 800 }}>{digest.bills_paid_count}</div>
                </div>
                <div style={{ padding: '10px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: '8px' }}>
                  <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>Items Purchased</div>
                  <div style={{ fontSize: '18px', fontWeight: 800 }}>{digest.shopping_items_purchased_count}</div>
                </div>
                <div style={{ padding: '10px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: '8px' }}>
                  <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>Automations Run</div>
                  <div style={{ fontSize: '18px', fontWeight: 800 }}>{digest.automations_executed_count}</div>
                </div>
              </div>

              <div style={{ fontSize: '13px', color: 'var(--color-text-primary)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {digest.highlights.map((h, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <CheckCircle2 size={14} color="var(--status-in-stock)" />
                    <span>{h}</span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Section B: Personalization Controls */}
          <Card style={{ padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
              <Sliders size={18} color="var(--color-primary-900)" />
              <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                Personalization & Memory Controls
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
              <div>
                <label style={{ fontSize: '13px', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                  AI Memory & Personalization
                </label>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <Button
                    size="sm"
                    variant={personalization?.ai_memory_enabled ? 'primary' : 'ghost'}
                    onClick={() => handleUpdatePrefs({ ai_memory_enabled: !personalization?.ai_memory_enabled })}
                  >
                    {personalization?.ai_memory_enabled ? 'Memory Enabled' : 'Memory Disabled'}
                  </Button>
                </div>
              </div>

              <div>
                <label style={{ fontSize: '13px', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                  Default Reminder Timing
                </label>
                <select
                  value={personalization?.reminder_timing_preference || '1_DAY_BEFORE'}
                  onChange={(e) => handleUpdatePrefs({ reminder_timing_preference: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--color-border-subtle)',
                    fontSize: '13px',
                    backgroundColor: 'var(--color-surface-card)'
                  }}
                >
                  <option value="1_DAY_BEFORE">1 Day Before</option>
                  <option value="SAME_DAY_MORNING">Same Day Morning</option>
                  <option value="SAME_DAY_EVENING">Same Day Evening</option>
                  <option value="2_DAYS_BEFORE">2 Days Before</option>
                </select>
              </div>
            </div>
          </Card>

          {/* Section C: Household Memory Vault */}
          <Card style={{ padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Brain size={18} color="var(--color-primary-900)" />
                <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                  Long-Term Household Memory Vault ({memories.length})
                </span>
              </div>
            </div>

            {/* Add Memory Input */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }}>
              <select
                value={newMemoryCategory}
                onChange={(e) => setNewMemoryCategory(e.target.value)}
                style={{
                  padding: '8px 12px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border-subtle)',
                  fontSize: '13px',
                  backgroundColor: 'var(--color-surface-card)'
                }}
              >
                <option value="PREFERENCE">Preference</option>
                <option value="ROUTINE">Routine</option>
                <option value="HOUSEHOLD_PATTERN">Household Pattern</option>
                <option value="IMPORTANT_FACT">Important Fact</option>
              </select>

              <input
                type="text"
                placeholder="e.g. Family shops for groceries on Saturdays"
                value={newMemoryContent}
                onChange={(e) => setNewMemoryContent(e.target.value)}
                style={{
                  flex: 1,
                  minWidth: '200px',
                  padding: '8px 12px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border-subtle)',
                  fontSize: '13px'
                }}
              />

              <Button size="sm" variant="primary" onClick={handleAddMemory}>
                <Plus size={14} />
                <span>Save Memory</span>
              </Button>
            </div>

            {/* Memory List */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {memories.length === 0 ? (
                <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)', textAlign: 'center', padding: '16px' }}>
                  No stored memories yet. The AI assistant will learn your routines and preferences over time.
                </div>
              ) : (
                memories.map((m) => (
                  <div
                    key={m.id}
                    style={{
                      padding: '10px 14px',
                      borderRadius: '8px',
                      backgroundColor: 'var(--color-surface-subtle)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '10px'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Badge variant="neutral">{m.category}</Badge>
                      <span style={{ fontSize: '13px', color: 'var(--color-text-primary)' }}>{m.content}</span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>
                        {m.source} ({Math.round(m.confidence * 100)}%)
                      </span>
                      <button
                        onClick={() => handleDeleteMemory(m.id)}
                        style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', padding: '4px' }}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>
      )}

      {/* TAB 4: EXECUTION HISTORY */}
      {activeTab === 'history' && (
        <Card style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--color-border-subtle)', fontWeight: 700, fontSize: '15px' }}>
            Immutable Execution Trail
          </div>
          <div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ backgroundColor: 'var(--color-surface-subtle)', textAlign: 'left', borderBottom: '1px solid var(--color-border-subtle)' }}>
                    <th style={{ padding: '12px 16px' }}>Status</th>
                    <th style={{ padding: '12px 16px' }}>Timestamp</th>
                    <th style={{ padding: '12px 16px' }}>Actions (S/F/T)</th>
                    <th style={{ padding: '12px 16px' }}>Duration</th>
                    <th style={{ padding: '12px 16px' }}>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboard?.recent_executions?.map((e) => (
                    <tr key={e.id} style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
                      <td style={{ padding: '12px 16px' }}>
                        <Badge variant={e.status === 'SUCCESS' ? 'in-stock' : e.status === 'SKIPPED' ? 'neutral' : 'overdue'}>
                          {e.status}
                        </Badge>
                      </td>
                      <td style={{ padding: '12px 16px', color: 'var(--color-text-secondary)' }}>
                        {new Date(e.created_at).toLocaleString()}
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        {e.actions_succeeded} / {e.actions_failed} / {e.actions_attempted}
                      </td>
                      <td style={{ padding: '12px 16px', color: 'var(--color-text-secondary)' }}>
                        {e.duration_ms}ms
                      </td>
                      <td style={{ padding: '12px 16px', color: 'var(--color-text-secondary)' }}>
                        {e.error_details || 'Execution completed without errors.'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </Card>
      )}

      {/* MODAL 1: AI AUTOMATION GENERATOR */}
      {isAiModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            zIndex: 120,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px'
          }}
          onClick={() => setIsAiModalOpen(false)}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '540px',
              backgroundColor: 'var(--color-surface-card)',
              borderRadius: 'var(--radius-lg)',
              padding: '24px',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sparkles size={20} color="var(--color-primary-900)" />
                <h3 style={{ fontSize: '18px', fontWeight: 800, margin: 0, color: 'var(--color-primary-900)' }}>
                  AI Automation Generator
                </h3>
              </div>
              <button onClick={() => setIsAiModalOpen(false)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
                <X size={20} color="var(--color-text-secondary)" />
              </button>
            </div>

            <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginBottom: '14px' }}>
              Describe a routine or trigger in plain English. The AI agent will construct a deterministic rule proposal for your confirmation.
            </p>

            <textarea
              rows={3}
              value={aiPrompt}
              onChange={(e) => setAiPrompt(e.target.value)}
              placeholder="Whenever milk is low in pantry, create task to restock or add to shopping"
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border-subtle)',
                fontSize: '13px',
                marginBottom: '14px',
                outline: 'none'
              }}
            />

            {!aiProposal ? (
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <Button variant="ghost" size="sm" onClick={() => setIsAiModalOpen(false)}>
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleGenerateAiProposal}
                  disabled={!aiPrompt.trim() || isAiGenerating}
                >
                  {isAiGenerating ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                  <span>{isAiGenerating ? 'Analyzing Rule...' : 'Generate Automation Rule'}</span>
                </Button>
              </div>

            ) : (
              <div style={{ backgroundColor: 'var(--color-surface-subtle)', padding: '14px', borderRadius: 'var(--radius-md)', marginTop: '8px' }}>
                <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-primary-900)', marginBottom: '4px' }}>
                  Proposed: {aiProposal.name}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginBottom: '12px' }}>
                  {aiProposal.explanation}
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                  <Button variant="ghost" size="sm" onClick={() => setAiProposal(null)}>
                    Try Another
                  </Button>
                  <Button variant="primary" size="sm" onClick={handleConfirmAiProposal}>
                    <Check size={14} />
                    <span>Confirm & Create Rule</span>
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* MODAL 2: MANUAL CREATION */}
      {isCreateModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            zIndex: 120,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px'
          }}
          onClick={() => setIsCreateModalOpen(false)}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '480px',
              backgroundColor: 'var(--color-surface-card)',
              borderRadius: 'var(--radius-lg)',
              padding: '24px',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 800, margin: 0, color: 'var(--color-primary-900)' }}>
                New Automation Rule
              </h3>
              <button onClick={() => setIsCreateModalOpen(false)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
                <X size={20} color="var(--color-text-secondary)" />
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Rule Name</label>
                <input
                  type="text"
                  placeholder="e.g. Restock Coffee Beans"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)', fontSize: '13px' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Trigger Event</label>
                <select
                  value={newTrigger}
                  onChange={(e) => setNewTrigger(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)', fontSize: '13px', backgroundColor: 'var(--color-surface-card)' }}
                >
                  <option value="INVENTORY_LOW">When Inventory Stock is Low</option>
                  <option value="TASK_OVERDUE">When Task is Overdue</option>
                  <option value="BILL_APPROACHING">When Bill is Due Within 3 Days</option>
                  <option value="SCHEDULE">Recurring Schedule</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Target Item Name</label>
                <input
                  type="text"
                  placeholder="e.g. Coffee Beans"
                  value={newItemName}
                  onChange={(e) => setNewItemName(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)', fontSize: '13px' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Action</label>
                <select
                  value={newActionType}
                  onChange={(e) => setNewActionType(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)', fontSize: '13px', backgroundColor: 'var(--color-surface-card)' }}
                >
                  <option value="ADD_SHOPPING_ITEM">Add to Shopping List</option>
                  <option value="CREATE_TASK">Create Restock Task</option>
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '10px' }}>
                <Button variant="ghost" size="sm" onClick={() => setIsCreateModalOpen(false)}>
                  Cancel
                </Button>
                <Button variant="primary" size="sm" onClick={handleCreateManual} disabled={!newName.trim()}>
                  Create Automation
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
