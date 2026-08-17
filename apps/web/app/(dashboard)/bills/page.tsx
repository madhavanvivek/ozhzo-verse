'use client';

import React, { useEffect, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import {
  Receipt,
  Plus,
  X,
  Sparkles,
  Trash2
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

interface PaymentRecord {
  id: string;
  amount_paid: number;
  currency: string;
  paid_date: string;
  paid_by_name: string;
  payment_method: string;
  notes?: string | null;
}

interface BillItem {
  id: string;
  title: string;
  category_name: string;
  expected_amount: number;
  currency: string;
  due_date: string;
  is_due_today: boolean;
  is_overdue: boolean;
  recurrence_type: string;
  status: 'UNPAID' | 'PARTIALLY_PAID' | 'PAID' | 'CANCELLED';
  amount_paid: number;
  remaining_balance: number;
  responsible_member_id?: string | null;
  responsible_member_name?: string | null;
  notes?: string | null;
  payments: PaymentRecord[];
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

export default function BillsPage() {
  const [activeHomeId, setActiveHomeId] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [members, setMembers] = useState<HomeMemberSummary[]>([]);
  const [bills, setBills] = useState<BillItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const [activeTab, setActiveTab] = useState<'ALL' | 'DUE_TODAY' | 'OVERDUE' | 'UPCOMING' | 'MY_RESPONSIBLE' | 'PAID'>('ALL');

  // Quick Add State
  const [quickTitle, setQuickTitle] = useState('');
  const [quickAmount, setQuickAmount] = useState('');
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  // Payment Modal State
  const [payingBill, setPayingBill] = useState<BillItem | null>(null);
  const [payAmount, setPayAmount] = useState('');
  const [payDate, setPayDate] = useState(new Date().toISOString().split('T')[0]);
  const [payMethod, setPayMethod] = useState('UPI');
  const [payNotes, setPayNotes] = useState('');
  const [payPayer, setPayPayer] = useState('');

  // Form State for detailed add
  const [newDueDate, setNewDueDate] = useState('');
  const [newCategory, setNewCategory] = useState('Utilities');
  const [newRecurrenceType, setNewRecurrenceType] = useState('MONTHLY');
  const [newResponsible, setNewResponsible] = useState('');
  const [newNotes, setNewNotes] = useState('');

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
        const [billsRes, membersRes] = await Promise.allSettled([
          apiClient.get<{ items: BillItem[] }>(`/homes/${homeId}/bills`),
          apiClient.get<HomeMemberSummary[]>(`/homes/${homeId}/members`)
        ]);

        if (billsRes.status === 'fulfilled' && billsRes.value?.items) {
          setBills(billsRes.value.items);
        } else {
          setBills([]);
        }

        if (membersRes.status === 'fulfilled' && membersRes.value) {
          setMembers(membersRes.value);
          if (membersRes.value.length > 0) {
            setNewResponsible(membersRes.value[0].display_name);
            setPayPayer(membersRes.value[0].display_name);
          }
        }
      }
    } catch (err) {
      console.error('Failed to load bills data:', err);
      setBills([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const commonTemplates = [
    { title: 'Electricity Bill', cat: 'Utilities', amount: 2000, rec: 'MONTHLY' },
    { title: 'Water & Sewerage', cat: 'Utilities', amount: 650, rec: 'MONTHLY' },
    { title: 'Fiber Internet', cat: 'Communication', amount: 999, rec: 'MONTHLY' },
    { title: 'House Rent', cat: 'Housing', amount: 25000, rec: 'MONTHLY' },
    { title: 'Piped Gas', cat: 'Utilities', amount: 800, rec: 'MONTHLY' },
    { title: 'Car Insurance', cat: 'Insurance', amount: 14500, rec: 'YEARLY' },
  ];

  const handleQuickAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickTitle.trim() || !quickAmount || !activeHomeId) return;

    const amt = parseFloat(quickAmount);
    const todayStr = new Date().toISOString().split('T')[0];
    const due = newDueDate || todayStr;

    const matchedMember = members.find((m) => m.display_name === newResponsible);

    const payload = {
      title: quickTitle.trim(),
      category_name: newCategory,
      expected_amount: amt,
      currency: 'INR',
      due_date: due,
      recurrence_type: newRecurrenceType,
      responsible_member_id: matchedMember ? matchedMember.id : undefined,
      notes: newNotes.trim() || undefined
    };

    try {
      const created = await apiClient.post<BillItem>(`/homes/${activeHomeId}/bills`, payload);
      setBills([created, ...bills]);
      setQuickTitle('');
      setQuickAmount('');
      setNewDueDate('');
      setNewNotes('');
      setIsDetailOpen(false);
    } catch (err) {
      console.error('Failed to add bill:', err);
      alert('Failed to save bill to backend.');
    }
  };

  const handleOpenPayModal = (bill: BillItem) => {
    setPayingBill(bill);
    setPayAmount(bill.remaining_balance.toString());
    setPayDate(new Date().toISOString().split('T')[0]);
    setPayMethod('UPI');
    setPayNotes('');
    setPayPayer(currentUser?.display_name || (members.length > 0 ? members[0].display_name : 'Unassigned'));
  };

  const handleSavePayment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!payingBill || !payAmount || !activeHomeId) return;

    const pAmt = parseFloat(payAmount);
    if (pAmt <= 0) return;

    const matchedPayer = members.find((m) => m.display_name === payPayer);

    const payload = {
      amount_paid: pAmt,
      paid_date: payDate,
      payment_method: payMethod,
      paid_by_member_id: matchedPayer ? matchedPayer.id : undefined,
      notes: payNotes.trim() || undefined
    };

    try {
      await apiClient.post(`/homes/${activeHomeId}/bills/${payingBill.id}/payments`, payload);
      // Reload bills
      loadData();
      setPayingBill(null);
    } catch (err) {
      console.error('Failed to record payment:', err);
      alert('Failed to record payment.');
    }
  };

  const handleDelete = async (id: string) => {
    if (!activeHomeId) return;
    if (!confirm('Are you sure you want to delete this bill?')) return;

    try {
      await apiClient.delete(`/homes/${activeHomeId}/bills/${id}`);
      setBills(bills.filter(b => b.id !== id));
    } catch (err) {
      console.error('Failed to delete bill:', err);
      alert('Failed to delete bill.');
    }
  };

  // Metrics
  const activeBills = bills.filter(b => b.status !== 'PAID' && b.status !== 'CANCELLED');
  const dueTodayBills = activeBills.filter(b => b.is_due_today);
  const overdueBills = activeBills.filter(b => b.is_overdue);
  const upcomingBills = activeBills.filter(b => !b.is_due_today && !b.is_overdue);
  const myResponsibleBills = activeBills.filter(b => b.responsible_member_name === currentUser?.display_name);
  const paidBills = bills.filter(b => b.status === 'PAID');

  const totalUnpaidAmount = activeBills.reduce((sum, b) => sum + (b.remaining_balance || b.expected_amount || 0), 0);
  const dueTodayAmount = dueTodayBills.reduce((sum, b) => sum + (b.remaining_balance || b.expected_amount || 0), 0);
  const overdueAmount = overdueBills.reduce((sum, b) => sum + (b.remaining_balance || b.expected_amount || 0), 0);
  const upcomingAmount = upcomingBills.reduce((sum, b) => sum + (b.remaining_balance || b.expected_amount || 0), 0);
  const paidThisMonthAmount = paidBills.reduce((sum, b) => sum + (b.amount_paid || 0), 0);

  const filteredBills = bills.filter(b => {
    if (activeTab === 'PAID') return b.status === 'PAID';
    if (b.status === 'PAID') return false;
    if (activeTab === 'DUE_TODAY') return b.is_due_today;
    if (activeTab === 'OVERDUE') return b.is_overdue;
    if (activeTab === 'UPCOMING') return !b.is_due_today && !b.is_overdue;
    if (activeTab === 'MY_RESPONSIBLE') return b.responsible_member_name === currentUser?.display_name;
    return true; // ALL active
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '980px' }}>
      {/* Header */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-3)' }}>
          <div>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-primary-900)' }}>
              Bills & Recurring Household Expenses
            </h1>
            <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)' }}>
              What our home needs to pay • Track due dates, variable utilities, partial payments, and shared responsibilities.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsDetailOpen(!isDetailOpen)}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <Plus size={16} />
              <span>{isDetailOpen ? 'Close Form' : 'New Bill'}</span>
            </Button>
          </div>
        </div>

        {/* Financial KPI Summary Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--space-3)' }}>
          <Card
            onClick={() => setActiveTab('ALL')}
            style={{
              cursor: 'pointer',
              borderColor: activeTab === 'ALL' ? 'var(--color-primary-900)' : 'transparent',
              backgroundColor: activeTab === 'ALL' ? 'var(--color-surface-overlay)' : 'var(--color-surface-card)',
              transition: 'all 0.15s ease'
            }}
          >
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>
              Total Active Unpaid
            </div>
            <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--color-primary-900)', marginTop: '4px' }}>
              ₹{totalUnpaidAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
              {activeBills.length} bills pending
            </div>
          </Card>

          <Card
            onClick={() => setActiveTab('OVERDUE')}
            style={{
              cursor: 'pointer',
              borderColor: activeTab === 'OVERDUE' ? 'var(--status-overdue)' : 'transparent',
              backgroundColor: activeTab === 'OVERDUE' ? 'var(--color-surface-overlay)' : 'var(--color-surface-card)',
              borderLeft: '4px solid var(--status-overdue)'
            }}
          >
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--status-overdue)', textTransform: 'uppercase' }}>
              Overdue
            </div>
            <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--status-overdue)', marginTop: '4px' }}>
              ₹{overdueAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
              {overdueBills.length} overdue bills
            </div>
          </Card>

          <Card
            onClick={() => setActiveTab('DUE_TODAY')}
            style={{
              cursor: 'pointer',
              borderColor: activeTab === 'DUE_TODAY' ? 'var(--status-low-stock)' : 'transparent',
              backgroundColor: activeTab === 'DUE_TODAY' ? 'var(--color-surface-overlay)' : 'var(--color-surface-card)',
              borderLeft: '4px solid var(--status-low-stock)'
            }}
          >
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--status-low-stock)', textTransform: 'uppercase' }}>
              Due Today
            </div>
            <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--status-low-stock)', marginTop: '4px' }}>
              ₹{dueTodayAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
              {dueTodayBills.length} due today
            </div>
          </Card>

          <Card
            onClick={() => setActiveTab('UPCOMING')}
            style={{
              cursor: 'pointer',
              borderColor: activeTab === 'UPCOMING' ? 'var(--color-primary-900)' : 'transparent',
              backgroundColor: activeTab === 'UPCOMING' ? 'var(--color-surface-overlay)' : 'var(--color-surface-card)'
            }}
          >
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>
              Upcoming
            </div>
            <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--color-text-primary)', marginTop: '4px' }}>
              ₹{upcomingAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
              {upcomingBills.length} upcoming
            </div>
          </Card>

          <Card
            onClick={() => setActiveTab('PAID')}
            style={{
              cursor: 'pointer',
              borderColor: activeTab === 'PAID' ? 'var(--status-in-stock)' : 'transparent',
              backgroundColor: activeTab === 'PAID' ? 'var(--color-surface-overlay)' : 'var(--color-surface-card)',
              borderLeft: '4px solid var(--status-in-stock)'
            }}
          >
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--status-in-stock)', textTransform: 'uppercase' }}>
              Paid (History)
            </div>
            <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--status-in-stock)', marginTop: '4px' }}>
              ₹{paidThisMonthAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
              {paidBills.length} settled bills
            </div>
          </Card>
        </div>
      </div>

      {/* Detail / Quick Add Box */}
      {isDetailOpen && (
        <Card style={{ border: '2px solid var(--color-primary-900)' }}>
          <form onSubmit={handleQuickAdd} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                Add New Household Bill
              </div>
              <button
                type="button"
                onClick={() => setIsDetailOpen(false)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-secondary)' }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Template Chips */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {commonTemplates.map((t, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                    setQuickTitle(t.title);
                    setQuickAmount(t.amount.toString());
                    setNewCategory(t.cat);
                    setNewRecurrenceType(t.rec);
                  }}
                  style={{
                    padding: '4px 10px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--color-border)',
                    backgroundColor: 'var(--color-surface-subtle)',
                    fontSize: '11px',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  + {t.title} (₹{t.amount})
                </button>
              ))}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--space-3)' }}>
              <Input
                id="quickTitle"
                label="Bill Name"
                placeholder="e.g. BESCOM Electricity Bill"
                value={quickTitle}
                onChange={(e) => setQuickTitle(e.target.value)}
                required
              />

              <Input
                id="quickAmount"
                type="number"
                label="Expected Amount (₹)"
                placeholder="2000.00"
                value={quickAmount}
                onChange={(e) => setQuickAmount(e.target.value)}
                required
              />

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
                <label style={{ fontSize: '12px', fontWeight: 600 }}>Responsible</label>
                <select
                  value={newResponsible}
                  onChange={(e) => setNewResponsible(e.target.value)}
                  style={{ height: '36px', padding: '0 8px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
                >
                  <option value="">Unassigned</option>
                  {members.map((m) => (
                    <option key={m.id} value={m.display_name}>
                      {m.display_name} ({m.role})
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', fontWeight: 600 }}>Category</label>
                <select
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                  style={{ height: '36px', padding: '0 8px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
                >
                  <option value="Utilities">Utilities</option>
                  <option value="Housing">Housing</option>
                  <option value="Communication">Communication</option>
                  <option value="Education">Education</option>
                  <option value="Insurance">Insurance</option>
                  <option value="Subscriptions">Subscriptions</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', fontWeight: 600 }}>Recurrence</label>
                <select
                  value={newRecurrenceType}
                  onChange={(e) => setNewRecurrenceType(e.target.value)}
                  style={{ height: '36px', padding: '0 8px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
                >
                  <option value="MONTHLY">Monthly</option>
                  <option value="QUARTERLY">Quarterly</option>
                  <option value="YEARLY">Yearly</option>
                  <option value="ONE_OFF">One-Off (Single Bill)</option>
                </select>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <Button type="button" variant="ghost" size="sm" onClick={() => setIsDetailOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" size="sm">
                Save Bill
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* Filter Tabs */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: 'var(--space-2)' }}>
        {[
          { key: 'ALL', label: `All Active (${activeBills.length})` },
          { key: 'DUE_TODAY', label: `Due Today (${dueTodayBills.length})` },
          { key: 'OVERDUE', label: `Overdue (${overdueBills.length})` },
          { key: 'UPCOMING', label: `Upcoming (${upcomingBills.length})` },
          { key: 'MY_RESPONSIBLE', label: `My Responsible (${myResponsibleBills.length})` },
          { key: 'PAID', label: `Paid History (${paidBills.length})` }
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

      {/* Bills List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
        {isLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {[1, 2, 3].map((i) => (
              <div key={i} style={{ height: '72px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: 'var(--radius-md)', animation: 'pulse 1.5s infinite' }} />
            ))}
          </div>
        ) : filteredBills.length === 0 ? (
          <Card style={{ padding: 'var(--space-8)', textAlign: 'center' }}>
            <Sparkles size={36} color="var(--status-in-stock)" style={{ margin: '0 auto 10px' }} />
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-primary-900)' }}>
              No bills found for this view
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
              All household expenses are settled or none exist in this category.
            </p>
          </Card>
        ) : (
          filteredBills.map((bill) => (
            <Card
              key={bill.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '14px 18px',
                borderLeft: bill.is_overdue
                  ? '4px solid var(--status-overdue)'
                  : bill.is_due_today
                  ? '4px solid var(--status-low-stock)'
                  : bill.status === 'PAID'
                  ? '4px solid var(--status-in-stock)'
                  : '1px solid var(--color-border-subtle)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
                <div style={{ width: '38px', height: '38px', borderRadius: '50%', backgroundColor: 'var(--color-surface-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Receipt size={18} color="var(--color-primary-900)" />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                  <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                    {bill.title}
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                    {bill.category_name} • Due: <strong>{new Date(bill.due_date).toLocaleDateString([], { month: 'short', day: 'numeric' })}</strong> • Responsible: <strong>{bill.responsible_member_name || 'Unassigned'}</strong>
                  </div>
                  {bill.notes && (
                    <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)' }}>
                      Note: {bill.notes}
                    </div>
                  )}
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '15px', fontWeight: 800, color: 'var(--color-primary-900)' }}>
                    ₹{bill.expected_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </div>
                  {bill.status === 'PARTIALLY_PAID' && (
                    <div style={{ fontSize: '11px', color: 'var(--status-low-stock)', fontWeight: 600 }}>
                      Remaining: ₹{bill.remaining_balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </div>
                  )}
                  {bill.status === 'PAID' && (
                    <div style={{ fontSize: '11px', color: 'var(--status-in-stock)', fontWeight: 600 }}>
                      ✓ Fully Paid
                    </div>
                  )}
                </div>

                {bill.status !== 'PAID' && (
                  <Button size="sm" variant="primary" onClick={() => handleOpenPayModal(bill)}>
                    Record Pay
                  </Button>
                )}

                <button
                  onClick={() => handleDelete(bill.id)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-tertiary)', padding: '4px' }}
                  aria-label="Delete bill"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </Card>
          ))
        )}
      </div>

      {/* Pay Modal */}
      {payingBill && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, padding: '20px' }}>
          <Card style={{ maxWidth: '440px', width: '100%', padding: 'var(--space-6)', backgroundColor: 'var(--color-surface-card)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
              <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                Record Payment — {payingBill.title}
              </div>
              <button
                onClick={() => setPayingBill(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-secondary)' }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSavePayment} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              <Input
                id="payAmt"
                type="number"
                label="Amount Paid (₹)"
                value={payAmount}
                onChange={(e) => setPayAmount(e.target.value)}
                required
              />

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <label style={{ fontSize: '12px', fontWeight: 600 }}>Payment Date</label>
                  <input
                    type="date"
                    value={payDate}
                    onChange={(e) => setPayDate(e.target.value)}
                    style={{ height: '38px', padding: '0 10px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
                    required
                  />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <label style={{ fontSize: '12px', fontWeight: 600 }}>Paid By</label>
                  <select
                    value={payPayer}
                    onChange={(e) => setPayPayer(e.target.value)}
                    style={{ height: '38px', padding: '0 10px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
                  >
                    <option value="">Unassigned</option>
                    {members.map((m) => (
                      <option key={m.id} value={m.display_name}>
                        {m.display_name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', fontWeight: 600 }}>Payment Method</label>
                <select
                  value={payMethod}
                  onChange={(e) => setPayMethod(e.target.value)}
                  style={{ height: '38px', padding: '0 10px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
                >
                  <option value="UPI">UPI (GooglePay / PhonePe / Paytm)</option>
                  <option value="NET_BANKING">Net Banking / Direct Transfer</option>
                  <option value="CREDIT_CARD">Credit Card</option>
                  <option value="DEBIT_CARD">Debit Card</option>
                  <option value="CASH">Cash</option>
                </select>
              </div>

              <Input
                id="payNotes"
                label="Notes / Transaction Reference (Optional)"
                placeholder="e.g. Ref #99214"
                value={payNotes}
                onChange={(e) => setPayNotes(e.target.value)}
              />

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: 'var(--space-2)' }}>
                <Button type="button" variant="ghost" size="sm" onClick={() => setPayingBill(null)}>
                  Cancel
                </Button>
                <Button type="submit" size="sm">
                  Confirm Payment
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}
    </div>
  );
}
