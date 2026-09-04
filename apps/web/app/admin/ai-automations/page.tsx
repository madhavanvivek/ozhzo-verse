'use client';

import React, { useState, useEffect } from 'react';
import {
  RefreshCw,
  Sliders,
  DollarSign,
  CheckCircle2,
  ShieldCheck,
  PauseCircle,
  PlayCircle,
  Activity,
  Cpu
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';

interface AIPlatformConfig {
  provider: string;
  model: string;
  daily_request_limit_default: number;
  monthly_cost_budget_usd: number;
  max_context_tokens: number;
  total_ai_records: number;
  total_estimated_cost_usd: number;
  total_tokens_consumed: number;
  active_quotas_count: number;
}

interface QuarantinedAutomation {
  id: string;
  home_id: string;
  home_name: string;
  name: string;
  trigger_type: string;
  failure_count: number;
  consecutive_failures: number;
  last_error?: string | null;
  status: string;
  enabled: boolean;
  updated_at: string;
}

export default function AdminAIAutomationsPage() {
  const [aiConfig, setAiConfig] = useState<AIPlatformConfig | null>(null);
  const [quarantinedAutomations, setQuarantinedAutomations] = useState<QuarantinedAutomation[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Modals
  const [isEditAIModalOpen, setIsEditAIModalOpen] = useState(false);
  const [aiForm, setAiForm] = useState({
    provider: 'GEMINI',
    model: 'gemini-1.5-flash',
    daily_request_limit_default: '100',
    monthly_cost_budget_usd: '500.00',
    max_context_tokens: '8192'
  });

  const [feedbackMsg, setFeedbackMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchData = async () => {
    try {
      setIsLoading(true);
      const [aiRes, qRes] = await Promise.all([
        apiClient.get<AIPlatformConfig>('/admin/ai/config'),
        apiClient.get<QuarantinedAutomation[]>('/admin/automations/quarantine')
      ]);
      setAiConfig(aiRes || null);
      if (aiRes) {
        setAiForm({
          provider: aiRes.provider || 'GEMINI',
          model: aiRes.model || 'gemini-1.5-flash',
          daily_request_limit_default: String(aiRes.daily_request_limit_default || 100),
          monthly_cost_budget_usd: String(aiRes.monthly_cost_budget_usd || 500.00),
          max_context_tokens: String(aiRes.max_context_tokens || 8192)
        });
      }
      setQuarantinedAutomations(qRes || []);
    } catch (err: any) {
      setFeedbackMsg({ type: 'error', text: err?.message || 'Failed to load telemetry' });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleUpdateAIConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiClient.patch('/admin/ai/config', {
        provider: aiForm.provider,
        model: aiForm.model,
        daily_request_limit_default: parseInt(aiForm.daily_request_limit_default) || 100,
        monthly_cost_budget_usd: parseFloat(aiForm.monthly_cost_budget_usd) || 500.00,
        max_context_tokens: parseInt(aiForm.max_context_tokens) || 8192
      });
      setFeedbackMsg({ type: 'success', text: 'AI platform parameters updated successfully!' });
      setIsEditAIModalOpen(false);
      fetchData();
    } catch (err: any) {
      setFeedbackMsg({ type: 'error', text: err?.message || 'Failed to update AI config' });
    }
  };

  const handleRestoreAutomation = async (autoId: string) => {
    try {
      await apiClient.post(`/admin/automations/${autoId}/restore`);
      setFeedbackMsg({ type: 'success', text: 'Automation restored and execution guard reset.' });
      fetchData();
    } catch (err: any) {
      setFeedbackMsg({ type: 'error', text: err?.message || 'Failed to restore automation' });
    }
  };

  const handleDisableAutomation = async (autoId: string) => {
    try {
      await apiClient.post(`/admin/automations/${autoId}/disable`);
      setFeedbackMsg({ type: 'success', text: 'Automation disabled administratively.' });
      fetchData();
    } catch (err: any) {
      setFeedbackMsg({ type: 'error', text: err?.message || 'Failed to disable automation' });
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 style={{ fontSize: '24px', fontWeight: 800, color: 'var(--color-primary-900, #0f172a)', margin: 0 }}>
              AI Intelligence & Automations Operations
            </h1>
            <Badge variant="completed">Active Protection</Badge>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--color-text-secondary, #64748b)', marginTop: '4px' }}>
            Monitor platform AI token budgets, Gemini provider limits, and manage quarantined high-frequency automations.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <Button variant="secondary" onClick={fetchData} disabled={isLoading}>
            <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
            <span style={{ marginLeft: '6px' }}>Refresh</span>
          </Button>

          <Button variant="primary" onClick={() => setIsEditAIModalOpen(true)}>
            <Sliders size={16} />
            <span style={{ marginLeft: '6px' }}>Configure AI Parameters</span>
          </Button>
        </div>
      </div>

      {/* Feedback Toast */}
      {feedbackMsg && (
        <div
          style={{
            padding: '12px 16px',
            borderRadius: '8px',
            marginBottom: '20px',
            backgroundColor: feedbackMsg.type === 'success' ? '#f0fdf4' : '#fef2f2',
            border: `1px solid ${feedbackMsg.type === 'success' ? '#86efac' : '#fca5a5'}`,
            color: feedbackMsg.type === 'success' ? '#166534' : '#991b1b',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '14px'
          }}
        >
          <span>{feedbackMsg.text}</span>
          <button onClick={() => setFeedbackMsg(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }}>✕</button>
        </div>
      )}

      {/* AI Telemetry Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <Card style={{ padding: '16px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ width: '44px', height: '44px', borderRadius: '10px', backgroundColor: '#e0e7ff', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#4338ca' }}>
            <Cpu size={24} />
          </div>
          <div>
            <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 600 }}>ACTIVE MODEL & PROVIDER</div>
            <div style={{ fontSize: '16px', fontWeight: 800, color: '#0f172a' }}>
              {aiConfig?.provider} / {aiConfig?.model}
            </div>
            <div style={{ fontSize: '11px', color: '#64748b' }}>Daily limit: {aiConfig?.daily_request_limit_default} req/user</div>
          </div>
        </Card>

        <Card style={{ padding: '16px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ width: '44px', height: '44px', borderRadius: '10px', backgroundColor: '#f0fdf4', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#15803d' }}>
            <DollarSign size={24} />
          </div>
          <div>
            <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 600 }}>ESTIMATED COST</div>
            <div style={{ fontSize: '18px', fontWeight: 800, color: '#0f172a' }}>
              ${aiConfig?.total_estimated_cost_usd?.toFixed(2) || '0.00'}
            </div>
            <div style={{ fontSize: '11px', color: '#64748b' }}>Budget: ${aiConfig?.monthly_cost_budget_usd}/mo</div>
          </div>
        </Card>

        <Card style={{ padding: '16px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ width: '44px', height: '44px', borderRadius: '10px', backgroundColor: '#eff6ff', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#1d4ed8' }}>
            <Activity size={24} />
          </div>
          <div>
            <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 600 }}>TOKENS CONSUMED</div>
            <div style={{ fontSize: '18px', fontWeight: 800, color: '#0f172a' }}>
              {(aiConfig?.total_tokens_consumed || 0).toLocaleString()}
            </div>
            <div style={{ fontSize: '11px', color: '#64748b' }}>Across {aiConfig?.total_ai_records || 0} inferences</div>
          </div>
        </Card>

        <Card style={{ padding: '16px', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ width: '44px', height: '44px', borderRadius: '10px', backgroundColor: '#fef3c7', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#b45309' }}>
            <ShieldCheck size={24} />
          </div>
          <div>
            <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 600 }}>QUARANTINED AUTOMATIONS</div>
            <div style={{ fontSize: '18px', fontWeight: 800, color: '#0f172a' }}>
              {quarantinedAutomations.length}
            </div>
            <div style={{ fontSize: '11px', color: '#64748b' }}>Self-healing loop guards active</div>
          </div>
        </Card>
      </div>

      {/* Quarantined Automations Table */}
      <div style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 style={{ fontSize: '18px', fontWeight: 700, color: '#0f172a', margin: 0 }}>
          Platform Automation Quarantine Desk
        </h2>
        <Badge variant="neutral">{quarantinedAutomations.length} failing rules</Badge>
      </div>

      <Card style={{ padding: '0', overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#475569' }}>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>Automation Name</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>Household</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>Trigger</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>Consecutive Failures</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>Status</th>
                <th style={{ padding: '14px 16px', fontWeight: 600, textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {quarantinedAutomations.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ padding: '32px', textAlign: 'center', color: '#64748b' }}>
                    <CheckCircle2 size={32} color="#10b981" style={{ margin: '0 auto 8px auto' }} />
                    <div>All household automations are running normally without loop trips or quota exhaustion.</div>
                  </td>
                </tr>
              ) : (
                quarantinedAutomations.map((auto) => (
                  <tr key={auto.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '14px 16px' }}>
                      <div style={{ fontWeight: 700, color: '#0f172a' }}>{auto.name}</div>
                      {auto.last_error && (
                        <div style={{ fontSize: '11px', color: '#dc2626', marginTop: '2px' }}>{auto.last_error}</div>
                      )}
                    </td>

                    <td style={{ padding: '14px 16px', color: '#475569' }}>{auto.home_name}</td>

                    <td style={{ padding: '14px 16px' }}>
                      <Badge variant="neutral">{auto.trigger_type}</Badge>
                    </td>

                    <td style={{ padding: '14px 16px', fontWeight: 700, color: '#dc2626' }}>
                      {auto.consecutive_failures} fails
                    </td>

                    <td style={{ padding: '14px 16px' }}>
                      <Badge variant="overdue">{auto.status}</Badge>
                    </td>

                    <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                      <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                        <Button size="sm" variant="secondary" onClick={() => handleRestoreAutomation(auto.id)}>
                          <PlayCircle size={14} />
                          <span style={{ marginLeft: '4px' }}>Restore & Reset</span>
                        </Button>

                        <Button size="sm" variant="ghost" onClick={() => handleDisableAutomation(auto.id)}>
                          <PauseCircle size={14} color="#ef4444" />
                          <span style={{ marginLeft: '4px', color: '#ef4444' }}>Disable</span>
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* MODAL: EDIT AI CONFIG */}
      {isEditAIModalOpen && (
        <Modal title="Configure Platform AI Parameters" isOpen={isEditAIModalOpen} onClose={() => setIsEditAIModalOpen(false)}>
          <form onSubmit={handleUpdateAIConfig} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Provider
                </label>
                <select
                  value={aiForm.provider}
                  onChange={(e) => setAiForm({ ...aiForm, provider: e.target.value })}
                  style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1' }}
                >
                  <option value="GEMINI">Google Gemini</option>
                  <option value="OPENAI">OpenAI</option>
                  <option value="ANTHROPIC">Anthropic</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Model
                </label>
                <Input
                  value={aiForm.model}
                  onChange={(e) => setAiForm({ ...aiForm, model: e.target.value })}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Default Daily Request Limit
                </label>
                <Input
                  type="number"
                  value={aiForm.daily_request_limit_default}
                  onChange={(e) => setAiForm({ ...aiForm, daily_request_limit_default: e.target.value })}
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Monthly Budget Cap (USD)
                </label>
                <Input
                  type="number"
                  step="0.01"
                  value={aiForm.monthly_cost_budget_usd}
                  onChange={(e) => setAiForm({ ...aiForm, monthly_cost_budget_usd: e.target.value })}
                />
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '12px' }}>
              <Button variant="secondary" type="button" onClick={() => setIsEditAIModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" type="submit">
                Save Parameters
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
