'use client';

import React, { useState, useEffect } from 'react';
import {
  Plus,
  RefreshCw,
  Edit2,
  Trash2,
  Search
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';

interface FeatureFlag {
  id: string;
  key: string;
  name: string;
  description?: string;
  is_enabled: boolean;
  target_countries: string[];
  target_plans: string[];
  rollout_percentage: number;
  rules_json: Record<string, any>;
  starts_at?: string;
  expires_at?: string;
  created_at?: string;
}

export default function AdminFeatureFlagsPage() {
  const [flags, setFlags] = useState<FeatureFlag[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFlag, setSelectedFlag] = useState<FeatureFlag | null>(null);

  // Modals
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);

  // Add Form State
  const [addForm, setAddForm] = useState({
    key: '',
    name: '',
    description: '',
    is_enabled: false,
    target_countries_str: '',
    target_plans_str: '',
    rollout_percentage: '100'
  });

  // Edit Form State
  const [editForm, setEditForm] = useState({
    name: '',
    description: '',
    is_enabled: false,
    target_countries_str: '',
    target_plans_str: '',
    rollout_percentage: '100'
  });

  const [feedbackMsg, setFeedbackMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchFlags = async () => {
    try {
      setIsLoading(true);
      const res = await apiClient.get<FeatureFlag[]>('/admin/feature-flags');
      setFlags(res || []);
    } catch (err: any) {
      setFeedbackMsg({ type: 'error', text: err?.message || 'Failed to load feature flags' });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchFlags();
  }, []);

  const handleCreateFlag = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const targetCountries = addForm.target_countries_str
        ? addForm.target_countries_str.split(',').map((s) => s.trim().toUpperCase()).filter(Boolean)
        : [];
      const targetPlans = addForm.target_plans_str
        ? addForm.target_plans_str.split(',').map((s) => s.trim().toUpperCase()).filter(Boolean)
        : [];

      await apiClient.post('/admin/feature-flags', {
        key: addForm.key.toLowerCase(),
        name: addForm.name,
        description: addForm.description,
        is_enabled: addForm.is_enabled,
        target_countries: targetCountries,
        target_plans: targetPlans,
        rollout_percentage: parseInt(addForm.rollout_percentage) || 100
      });

      setFeedbackMsg({ type: 'success', text: `Feature flag '${addForm.key}' created!` });
      setIsAddModalOpen(false);
      fetchFlags();
    } catch (err: any) {
      setFeedbackMsg({ type: 'error', text: err?.message || 'Failed to create feature flag' });
    }
  };

  const handleUpdateFlag = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFlag) return;
    try {
      const targetCountries = editForm.target_countries_str
        ? editForm.target_countries_str.split(',').map((s) => s.trim().toUpperCase()).filter(Boolean)
        : [];
      const targetPlans = editForm.target_plans_str
        ? editForm.target_plans_str.split(',').map((s) => s.trim().toUpperCase()).filter(Boolean)
        : [];

      await apiClient.patch(`/admin/feature-flags/${selectedFlag.id}`, {
        name: editForm.name,
        description: editForm.description,
        is_enabled: editForm.is_enabled,
        target_countries: targetCountries,
        target_plans: targetPlans,
        rollout_percentage: parseInt(editForm.rollout_percentage) || 100
      });

      setFeedbackMsg({ type: 'success', text: `Feature flag '${selectedFlag.key}' updated!` });
      setIsEditModalOpen(false);
      fetchFlags();
    } catch (err: any) {
      setFeedbackMsg({ type: 'error', text: err?.message || 'Failed to update feature flag' });
    }
  };

  const handleToggleFlag = async (flag: FeatureFlag) => {
    try {
      await apiClient.patch(`/admin/feature-flags/${flag.id}`, {
        is_enabled: !flag.is_enabled
      });
      setFlags(flags.map((f) => (f.id === flag.id ? { ...f, is_enabled: !f.is_enabled } : f)));
      setFeedbackMsg({
        type: 'success',
        text: `Flag '${flag.key}' is now ${!flag.is_enabled ? 'ENABLED' : 'DISABLED'}.`
      });
    } catch (err: any) {
      setFeedbackMsg({ type: 'error', text: err?.message || 'Failed to toggle flag' });
    }
  };

  const handleDeleteFlag = async (flag: FeatureFlag) => {
    if (!confirm(`Are you sure you want to delete feature flag '${flag.key}'?`)) return;
    try {
      await apiClient.delete(`/admin/feature-flags/${flag.id}`);
      setFeedbackMsg({ type: 'success', text: `Flag '${flag.key}' deleted.` });
      fetchFlags();
    } catch (err: any) {
      setFeedbackMsg({ type: 'error', text: err?.message || 'Failed to delete flag' });
    }
  };

  const openEditModal = (flag: FeatureFlag) => {
    setSelectedFlag(flag);
    setEditForm({
      name: flag.name,
      description: flag.description || '',
      is_enabled: flag.is_enabled,
      target_countries_str: (flag.target_countries || []).join(', '),
      target_plans_str: (flag.target_plans || []).join(', '),
      rollout_percentage: String(flag.rollout_percentage || 100)
    });
    setIsEditModalOpen(true);
  };

  const filteredFlags = flags.filter((f) =>
    f.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    f.key.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (f.description && f.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 style={{ fontSize: '24px', fontWeight: 800, color: 'var(--color-primary-900, #0f172a)', margin: 0 }}>
              Feature Flags & Rollout Controls
            </h1>
            <Badge variant="completed">Dynamic Rollout</Badge>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--color-text-secondary, #64748b)', marginTop: '4px' }}>
            Control runtime feature availability, percentage rollouts, and country/plan level gating without deployments.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <Button variant="secondary" onClick={fetchFlags} disabled={isLoading}>
            <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
            <span style={{ marginLeft: '6px' }}>Refresh</span>
          </Button>

          <Button variant="primary" onClick={() => setIsAddModalOpen(true)}>
            <Plus size={16} />
            <span style={{ marginLeft: '6px' }}>Create Feature Flag</span>
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

      {/* Search Bar */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '20px' }}>
        <div style={{ position: 'relative', flex: 1, maxWidth: '400px' }}>
          <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
          <input
            type="text"
            placeholder="Search feature flags by name or key..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '10px 12px 10px 38px',
              borderRadius: '8px',
              border: '1px solid #cbd5e1',
              fontSize: '14px',
              outline: 'none'
            }}
          />
        </div>
      </div>

      {/* Feature Flags Table */}
      <Card style={{ padding: '0', overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#475569' }}>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>Status</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>Flag Name & Key</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>Target Countries</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>Target Plans</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>Rollout %</th>
                <th style={{ padding: '14px 16px', fontWeight: 600, textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredFlags.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ padding: '32px', textAlign: 'center', color: '#64748b' }}>
                    No feature flags found.
                  </td>
                </tr>
              ) : (
                filteredFlags.map((flag) => (
                  <tr key={flag.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '14px 16px' }}>
                      <button
                        onClick={() => handleToggleFlag(flag)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          background: 'none',
                          border: 'none',
                          cursor: 'pointer',
                          padding: 0
                        }}
                      >
                        <Badge variant={flag.is_enabled ? 'completed' : 'neutral'}>
                          {flag.is_enabled ? 'Active' : 'Disabled'}
                        </Badge>
                      </button>
                    </td>

                    <td style={{ padding: '14px 16px' }}>
                      <div style={{ fontWeight: 700, color: '#0f172a' }}>{flag.name}</div>
                      <div style={{ fontSize: '11px', color: '#64748b', fontFamily: 'monospace' }}>{flag.key}</div>
                      {flag.description && (
                        <div style={{ fontSize: '12px', color: '#475569', marginTop: '2px' }}>{flag.description}</div>
                      )}
                    </td>

                    <td style={{ padding: '14px 16px' }}>
                      {(!flag.target_countries || flag.target_countries.length === 0) ? (
                        <Badge variant="neutral">All Countries</Badge>
                      ) : (
                        <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                          {flag.target_countries.map((c) => (
                            <Badge key={c} variant="completed">{c}</Badge>
                          ))}
                        </div>
                      )}
                    </td>

                    <td style={{ padding: '14px 16px' }}>
                      {(!flag.target_plans || flag.target_plans.length === 0) ? (
                        <Badge variant="neutral">All Plans</Badge>
                      ) : (
                        <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                          {flag.target_plans.map((p) => (
                            <Badge key={p} variant="completed">{p}</Badge>
                          ))}
                        </div>
                      )}
                    </td>

                    <td style={{ padding: '14px 16px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <div style={{ width: '60px', height: '6px', backgroundColor: '#e2e8f0', borderRadius: '3px', overflow: 'hidden' }}>
                          <div
                            style={{
                              width: `${flag.rollout_percentage}%`,
                              height: '100%',
                              backgroundColor: flag.is_enabled ? '#10b981' : '#94a3b8'
                            }}
                          />
                        </div>
                        <span style={{ fontWeight: 600, fontSize: '12px', color: '#475569' }}>
                          {flag.rollout_percentage}%
                        </span>
                      </div>
                    </td>

                    <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                      <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                        <Button size="sm" variant="ghost" onClick={() => openEditModal(flag)}>
                          <Edit2 size={14} />
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => handleDeleteFlag(flag)}>
                          <Trash2 size={14} color="#ef4444" />
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

      {/* MODAL: ADD FLAG */}
      {isAddModalOpen && (
        <Modal title="Create Platform Feature Flag" isOpen={isAddModalOpen} onClose={() => setIsAddModalOpen(false)}>
          <form onSubmit={handleCreateFlag} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                Flag Key (unique_identifier) *
              </label>
              <Input
                required
                placeholder="e.g. dynamic_pricing_v2, ai_grocery_ordering"
                value={addForm.key}
                onChange={(e) => setAddForm({ ...addForm, key: e.target.value })}
              />
            </div>

            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                Display Name *
              </label>
              <Input
                required
                placeholder="e.g. Dynamic Regional Pricing"
                value={addForm.name}
                onChange={(e) => setAddForm({ ...addForm, name: e.target.value })}
              />
            </div>

            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                Description
              </label>
              <textarea
                rows={2}
                value={addForm.description}
                onChange={(e) => setAddForm({ ...addForm, description: e.target.value })}
                style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Target Countries (comma separated)
                </label>
                <Input
                  placeholder="e.g. IN, AE, US (blank for all)"
                  value={addForm.target_countries_str}
                  onChange={(e) => setAddForm({ ...addForm, target_countries_str: e.target.value })}
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Target Plans (comma separated)
                </label>
                <Input
                  placeholder="e.g. HOME_PRO, ENTERPRISE"
                  value={addForm.target_plans_str}
                  onChange={(e) => setAddForm({ ...addForm, target_plans_str: e.target.value })}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Rollout Percentage (0–100%)
                </label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  value={addForm.rollout_percentage}
                  onChange={(e) => setAddForm({ ...addForm, rollout_percentage: e.target.value })}
                />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', paddingTop: '20px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={addForm.is_enabled}
                    onChange={(e) => setAddForm({ ...addForm, is_enabled: e.target.checked })}
                  />
                  Enable Immediately
                </label>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '12px' }}>
              <Button variant="secondary" type="button" onClick={() => setIsAddModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" type="submit">
                Create Feature Flag
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* MODAL: EDIT FLAG */}
      {isEditModalOpen && selectedFlag && (
        <Modal title={`Edit Flag: ${selectedFlag.name}`} isOpen={isEditModalOpen} onClose={() => setIsEditModalOpen(false)}>
          <form onSubmit={handleUpdateFlag} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                Display Name
              </label>
              <Input
                value={editForm.name}
                onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
              />
            </div>

            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                Description
              </label>
              <textarea
                rows={2}
                value={editForm.description}
                onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px' }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Target Countries
                </label>
                <Input
                  value={editForm.target_countries_str}
                  onChange={(e) => setEditForm({ ...editForm, target_countries_str: e.target.value })}
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Target Plans
                </label>
                <Input
                  value={editForm.target_plans_str}
                  onChange={(e) => setEditForm({ ...editForm, target_plans_str: e.target.value })}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Rollout Percentage
                </label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  value={editForm.rollout_percentage}
                  onChange={(e) => setEditForm({ ...editForm, rollout_percentage: e.target.value })}
                />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', paddingTop: '20px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={editForm.is_enabled}
                    onChange={(e) => setEditForm({ ...editForm, is_enabled: e.target.checked })}
                  />
                  Feature Enabled
                </label>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '12px' }}>
              <Button variant="secondary" type="button" onClick={() => setIsEditModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" type="submit">
                Save Changes
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
