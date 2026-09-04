'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Sparkles, Send, X, Check, Loader2, Bot, User, CheckCircle2, ListTree, Brain } from 'lucide-react';

import { apiClient } from '@/lib/apiClient';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

interface ActionProposal {
  id: string;
  action_type: string;
  title?: string;
  name?: string;
  description?: string;
  explanation?: string;
  params?: Record<string, any>;
  requires_confirmation?: boolean;
}

interface PlanStep {
  step_number: number;
  action_type: string;
  target_domain: string;
  description: string;
  tool_name: string;
  parameters: Record<string, any>;
  permission_required: string;
  status: string;
}

interface AgentPlan {
  plan_id: string;
  title: string;
  summary: string;
  steps: PlanStep[];
  requires_confirmation: boolean;
}

interface Message {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  action_proposal?: ActionProposal | null;
  suggested_plan?: AgentPlan | null;
  retrieved_memory_snippets?: string[];
  suggested_quick_replies?: string[];
  timestamp: string;
}

interface AIAssistantWidgetProps {
  isOpen: boolean;
  onClose: () => void;
  activeHomeName?: string;
  activeHomeId?: string | null;
}

export function AIAssistantWidget({
  isOpen,
  onClose,
  activeHomeName = 'Home',
  activeHomeId
}: AIAssistantWidgetProps) {
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      sender: 'ai',
      text: `Hello! I am your Ozhzo Household Assistant for **${activeHomeName || 'Home'}**. How can I assist you today?`,
      suggested_quick_replies: [
        "What's due today?",
        "What bills are due?",
        "Prepare the house for the weekend",
        "Add Milk to shopping"
      ],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [executingActionId, setExecutingActionId] = useState<string | null>(null);
  const [executedActionIds, setExecutedActionIds] = useState<Set<string>>(new Set());

  const [executingPlan, setExecutingPlan] = useState(false);
  const [executedPlanIds, setExecutedPlanIds] = useState<Set<string>>(new Set());

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  useEffect(() => {
    if (activeHomeName) {
      setMessages((prev) => {
        if (prev.length === 1 && prev[0].id === 'welcome') {
          return [
            {
              id: 'welcome',
              sender: 'ai',
              text: `Hello! I am your Ozhzo Household Assistant for **${activeHomeName}**. How can I assist you today?`,
              suggested_quick_replies: [
                "What's due today?",
                "What bills are due?",
                "Prepare the house for the weekend",
                "Add Milk to shopping"
              ],
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            }
          ];
        }
        return prev;
      });
    }
  }, [activeHomeName]);

  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend || inputText).trim();
    if (!query || isLoading || !activeHomeId) return;

    setInputText('');
    const userMsg: Message = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    const isPlanningQuery =
      query.toLowerCase().includes('plan') ||
      query.toLowerCase().includes('prepare') ||
      query.toLowerCase().includes('agent');

    try {
      if (isPlanningQuery) {
        const res = await apiClient.post<any>(`/homes/${activeHomeId}/ai/agent/chat`, {
          prompt: query,
          session_token: sessionToken
        });

        if (res?.session_token) {
          setSessionToken(res.session_token);
        }

        const aiMsg: Message = {
          id: `ai-${Date.now()}`,
          sender: 'ai',
          text: res?.response_text || res?.message || 'I have prepared a household plan for your review.',
          action_proposal: res?.action_proposal,
          suggested_plan: res?.suggested_plan,
          retrieved_memory_snippets: res?.retrieved_memory_snippets || [],
          suggested_quick_replies: res?.suggested_quick_replies || [],
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        setMessages((prev) => [...prev, aiMsg]);
      } else {
        const res = await apiClient.post<any>(`/homes/${activeHomeId}/ai/chat`, {
          message: query
        });

        const aiMsg: Message = {
          id: `ai-${Date.now()}`,
          sender: 'ai',
          text: res?.message || res?.response_text || 'I have processed your household request.',
          action_proposal: res?.action_proposal,
          suggested_quick_replies: res?.suggested_quick_replies || [],
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        setMessages((prev) => [...prev, aiMsg]);
      }
    } catch (err: any) {
      const errorMsg: Message = {
        id: `ai-err-${Date.now()}`,
        sender: 'ai',
        text: err?.message || 'Sorry, I encountered an issue reaching the household assistant. Please try again.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirmPlan = async (plan: AgentPlan) => {
    if (!activeHomeId || !sessionToken || executingPlan) return;

    setExecutingPlan(true);
    try {
      const res = await apiClient.post<any>(`/homes/${activeHomeId}/ai/agent/plans/${sessionToken}/execute`, {});
      setExecutedPlanIds((prev) => new Set([...prev, plan.plan_id]));

      const successMsg: Message = {
        id: `ai-plan-exec-${Date.now()}`,
        sender: 'ai',
        text: `✓ Plan "${plan.title}" executed (${res?.executed_steps_count || plan.steps.length} steps completed).`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages((prev) => [...prev, successMsg]);

      if (typeof window !== 'undefined') {
        window.dispatchEvent(new Event('home-changed'));
      }
    } catch (err: any) {
      const failMsg: Message = {
        id: `ai-plan-fail-${Date.now()}`,
        sender: 'ai',
        text: `Failed to execute plan: ${err?.message || 'Permission denied'}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages((prev) => [...prev, failMsg]);
    } finally {
      setExecutingPlan(false);
    }
  };

  const handleConfirmAction = async (actionId: string) => {
    if (!activeHomeId || executingActionId) return;

    setExecutingActionId(actionId);
    try {
      const res = await apiClient.post<any>(`/homes/${activeHomeId}/ai/actions/${actionId}/confirm`, {});
      setExecutedActionIds((prev) => new Set([...prev, actionId]));

      const successMsg: Message = {
        id: `ai-confirm-${Date.now()}`,
        sender: 'ai',
        text: `✓ ${res?.message || 'Action executed successfully.'}`,
        suggested_quick_replies: ["What's due today?", 'Show shopping list'],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages((prev) => [...prev, successMsg]);

      if (typeof window !== 'undefined') {
        window.dispatchEvent(new Event('home-changed'));
      }
    } catch (err: any) {
      const failMsg: Message = {
        id: `ai-fail-${Date.now()}`,
        sender: 'ai',
        text: `Failed to execute action: ${err?.message || 'Permission denied or expired proposal.'}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages((prev) => [...prev, failMsg]);
    } finally {
      setExecutingActionId(null);
    }
  };

  const handleRejectAction = async (actionId: string) => {
    if (!activeHomeId) return;
    try {
      await apiClient.post(`/homes/${activeHomeId}/ai/actions/${actionId}/reject`, {});
      setExecutedActionIds((prev) => new Set([...prev, actionId]));
      const cancelMsg: Message = {
        id: `ai-cancel-${Date.now()}`,
        sender: 'ai',
        text: 'Action cancelled.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages((prev) => [...prev, cancelMsg]);
    } catch {
      // Silently dismiss
    }
  };

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-label="AI Household Assistant"
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        zIndex: 110,
        display: 'flex',
        alignItems: 'flex-end',
        justifyContent: 'flex-end',
        padding: '0'
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '440px',
          height: '100vh',
          maxHeight: '680px',
          backgroundColor: 'var(--color-surface-card)',
          borderRadius: 'var(--radius-lg) var(--radius-lg) 0 0',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 -4px 24px rgba(0, 0, 0, 0.15)',
          overflow: 'hidden'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Assistant Header */}
        <div
          style={{
            padding: '14px 16px',
            borderBottom: '1px solid var(--color-border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: 'var(--color-surface-subtle)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                backgroundColor: 'var(--color-primary-900)',
                color: '#ffffff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              <Sparkles size={16} />
            </div>
            <div>
              <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                Ozhzo Assistant
              </div>
              <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>
                Household Intelligence & Agent Planning
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              padding: '6px',
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <X size={20} color="var(--color-text-secondary)" />
          </button>
        </div>

        {/* Chat History Messages Stream */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px'
          }}
        >
          {messages.map((m) => (
            <div
              key={m.id}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: m.sender === 'user' ? 'flex-end' : 'flex-start',
                gap: '4px'
              }}
            >
              <div
                style={{
                  display: 'flex',
                  gap: '8px',
                  maxWidth: '90%',
                  flexDirection: m.sender === 'user' ? 'row-reverse' : 'row'
                }}
              >
                <div
                  style={{
                    width: '24px',
                    height: '24px',
                    borderRadius: '50%',
                    backgroundColor: m.sender === 'user' ? 'var(--color-surface-subtle)' : 'var(--color-primary-900)',
                    color: m.sender === 'user' ? 'var(--color-text-secondary)' : '#ffffff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    marginTop: '4px'
                  }}
                >
                  {m.sender === 'user' ? <User size={13} /> : <Bot size={13} />}
                </div>

                <div
                  style={{
                    padding: '10px 14px',
                    borderRadius: 'var(--radius-md)',
                    backgroundColor: m.sender === 'user' ? 'var(--color-primary-900)' : 'var(--color-surface-subtle)',
                    color: m.sender === 'user' ? 'var(--color-text-inverse)' : 'var(--color-text-primary)',
                    fontSize: '13px',
                    lineHeight: '1.45',
                    whiteSpace: 'pre-wrap'
                  }}
                >
                  {m.text}
                </div>
              </div>

              {/* Retrieved Memory Snippets Badge */}
              {m.retrieved_memory_snippets && m.retrieved_memory_snippets.length > 0 && (
                <div style={{ marginLeft: '32px', marginTop: '4px', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                  {m.retrieved_memory_snippets.map((snip, idx) => (
                    <div
                      key={idx}
                      style={{
                        fontSize: '11px',
                        padding: '2px 8px',
                        borderRadius: '6px',
                        backgroundColor: 'rgba(59, 130, 246, 0.08)',
                        color: 'var(--color-primary-900)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}
                    >
                      <Brain size={11} />
                      <span>{snip}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Multi-step Agent Plan Card */}
              {m.suggested_plan && (
                <div
                  style={{
                    marginLeft: '32px',
                    marginTop: '8px',
                    maxWidth: '92%',
                    backgroundColor: 'var(--color-surface-card)',
                    border: '1.5px solid var(--color-primary-900)',
                    borderRadius: 'var(--radius-md)',
                    padding: '14px',
                    boxShadow: '0 2px 10px rgba(0,0,0,0.06)'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                    <ListTree size={16} color="var(--color-primary-900)" />
                    <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                      {m.suggested_plan.title}
                    </span>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginBottom: '10px' }}>
                    {m.suggested_plan.summary}
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '12px' }}>
                    {m.suggested_plan.steps.map((step) => (
                      <div
                        key={step.step_number}
                        style={{
                          fontSize: '12px',
                          padding: '6px 8px',
                          borderRadius: 'var(--radius-sm)',
                          backgroundColor: 'var(--color-surface-subtle)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between'
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ fontWeight: 700, color: 'var(--color-primary-900)' }}>
                            {step.step_number}.
                          </span>
                          <span>{step.description}</span>
                        </div>
                        <Badge variant="neutral">{step.target_domain}</Badge>
                      </div>
                    ))}
                  </div>

                  {!executedPlanIds.has(m.suggested_plan.plan_id) ? (
                    <Button
                      size="sm"
                      variant="primary"
                      onClick={() => handleConfirmPlan(m.suggested_plan!)}
                      disabled={executingPlan}
                      style={{ width: '100%', minHeight: '34px', fontSize: '12px' }}
                    >
                      {executingPlan ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                      <span>{executingPlan ? 'Executing Plan Steps...' : 'Confirm & Execute Plan'}</span>
                    </Button>
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--status-in-stock)', fontWeight: 600 }}>
                      <CheckCircle2 size={16} />
                      <span>Plan executed successfully</span>
                    </div>
                  )}
                </div>
              )}

              {/* Single Action Proposal Card */}
              {m.action_proposal && !m.suggested_plan && (
                <div
                  style={{
                    marginLeft: '32px',
                    marginTop: '6px',
                    maxWidth: '85%',
                    backgroundColor: 'var(--color-surface-card)',
                    border: '1.5px solid var(--color-primary-900)',
                    borderRadius: 'var(--radius-md)',
                    padding: '12px 14px',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                    <Badge variant="neutral">{m.action_proposal.action_type}</Badge>
                    <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                      {m.action_proposal.title || m.action_proposal.name}
                    </span>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginBottom: '10px' }}>
                    {m.action_proposal.explanation || m.action_proposal.description}
                  </div>

                  {!executedActionIds.has(m.action_proposal.id || 'single-action') ? (
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <Button
                        size="sm"
                        variant="primary"
                        onClick={() => handleConfirmAction(m.action_proposal!.id || 'single-action')}
                        disabled={!!executingActionId}
                        style={{ minHeight: '32px', padding: '0 12px', fontSize: '12px' }}
                      >
                        {executingActionId ? (
                          <>
                            <Loader2 size={14} className="animate-spin" />
                            <span>Executing...</span>
                          </>
                        ) : (
                          <>
                            <Check size={14} />
                            <span>Confirm Action</span>
                          </>
                        )}
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleRejectAction(m.action_proposal!.id || 'single-action')}
                        disabled={!!executingActionId}
                        style={{ minHeight: '32px', padding: '0 10px', fontSize: '12px' }}
                      >
                        <span>Cancel</span>
                      </Button>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--status-in-stock)', fontWeight: 600 }}>
                      <CheckCircle2 size={16} />
                      <span>Action completed</span>
                    </div>
                  )}
                </div>
              )}

              {/* Quick suggestion prompt chips */}
              {m.suggested_quick_replies && m.suggested_quick_replies.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginLeft: '32px', marginTop: '6px' }}>
                  {m.suggested_quick_replies.map((chip, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendMessage(chip)}
                      style={{
                        padding: '4px 10px',
                        borderRadius: '12px',
                        border: '1px solid var(--color-border-subtle)',
                        backgroundColor: 'var(--color-surface-subtle)',
                        fontSize: '12px',
                        color: 'var(--color-primary-900)',
                        cursor: 'pointer'
                      }}
                    >
                      {chip}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginLeft: '8px' }}>
              <div
                style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--color-primary-900)',
                  color: '#ffffff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                <Bot size={13} />
              </div>
              <div
                style={{
                  padding: '8px 12px',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--color-surface-subtle)',
                  fontSize: '13px',
                  color: 'var(--color-text-secondary)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <Loader2 size={14} className="animate-spin" />
                <span>Thinking and planning...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Text Form */}
        <div
          style={{
            padding: '12px 16px',
            borderTop: '1px solid var(--color-border-subtle)',
            backgroundColor: 'var(--color-surface-card)',
            display: 'flex',
            gap: '8px',
            alignItems: 'center'
          }}
        >
          <input
            type="text"
            aria-label="Assistant message input"
            placeholder="Ask anything or request a plan..."
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSendMessage();
            }}
            disabled={isLoading}
            style={{
              flex: 1,
              padding: '10px 14px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-border-subtle)',
              fontSize: '13px',
              backgroundColor: 'var(--color-surface-subtle)',
              outline: 'none',
              minHeight: '40px'
            }}
          />
          <Button
            variant="primary"
            size="sm"
            onClick={() => handleSendMessage()}
            disabled={!inputText.trim() || isLoading}
            style={{ minHeight: '40px', minWidth: '40px', padding: '0' }}
            aria-label="Send message"
          >
            <Send size={16} />
          </Button>

        </div>
      </div>
    </div>
  );
}
