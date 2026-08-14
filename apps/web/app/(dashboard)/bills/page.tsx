'use client';

import React, { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import {
  Receipt,
  Plus,
  Calendar,
  DollarSign,
  CheckCircle2,
  AlertCircle,
  Repeat,
  Trash2,
  Clock,
  Check,
  Sparkles,
  CreditCard,
  User,
  Zap,
  Droplets,
  Wifi,
  Home,
  Shield,
  FileText
} from 'lucide-react';

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
  category_name?: string | null;
  expected_amount: number;
  currency: string;
  due_date: string;
  is_overdue?: boolean;
  is_due_today?: boolean;
  recurrence_type?: string;
  recurrence_interval_days?: number | null;
  status: 'UNPAID' | 'PARTIALLY_PAID' | 'PAID' | 'CANCELLED';
  amount_paid: number;
  remaining_balance: number;
  responsible_member_name?: string | null;
  notes?: string | null;
  payments: PaymentRecord[];
}

export default function BillsPage() {
  const [activeTab, setActiveTab] = useState<'ALL' | 'DUE_TODAY' | 'OVERDUE' | 'UPCOMING' | 'MY_RESPONSIBLE' | 'PAID'>('ALL');
  const [quickTitle, setQuickTitle] = useState('');
  const [quickAmount, setQuickAmount] = useState('');
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  // Payment Modal State
  const [payingBill, setPayingBill] = useState<BillItem | null>(null);
  const [payAmount, setPayAmount] = useState('');
  const [payDate, setPayDate] = useState(new Date().toISOString().split('T')[0]);
  const [payMethod, setPayMethod] = useState('UPI');
  const [payNotes, setPayNotes] = useState('');
  const [payPayer, setPayPayer] = useState('Vivek');

  const [bills, setBills] = useState<BillItem[]>([
    {
      id: 'bill-1',
      title: 'Electricity Bill (BESCOM)',
      category_name: 'Utilities',
      expected_amount: 2000.00,
      currency: 'INR',
      due_date: new Date().toISOString().split('T')[0],
      is_due_today: true,
      is_overdue: false,
      recurrence_type: 'MONTHLY',
      status: 'UNPAID',
      amount_paid: 0.00,
      remaining_balance: 2000.00,
      responsible_member_name: 'Vivek',
      notes: 'Meter RR No: 4421-E',
      payments: []
    },
    {
      id: 'bill-2',
      title: 'High-Speed Fiber Internet',
      category_name: 'Communication',
      expected_amount: 999.00,
      currency: 'INR',
      due_date: new Date(Date.now() - 86400000 * 2).toISOString().split('T')[0],
      is_due_today: false,
      is_overdue: true,
      recurrence_type: 'MONTHLY',
      status: 'UNPAID',
      amount_paid: 0.00,
      remaining_balance: 999.00,
      responsible_member_name: 'Karthika',
      notes: 'Jio Fiber 300 Mbps',
      payments: []
    },
    {
      id: 'bill-3',
      title: 'House Rent',
      category_name: 'Housing',
      expected_amount: 25000.00,
      currency: 'INR',
      due_date: new Date(Date.now() + 86400000 * 10).toISOString().split('T')[0],
      is_due_today: false,
      is_overdue: false,
      recurrence_type: 'MONTHLY',
      status: 'UNPAID',
      amount_paid: 0.00,
      remaining_balance: 25000.00,
      responsible_member_name: 'Vivek',
      notes: 'Direct transfer to landlord',
      payments: []
    },
    {
      id: 'bill-4',
      title: 'School Tuition Fee (Term 2)',
      category_name: 'Education',
      expected_amount: 10000.00,
      currency: 'INR',
      due_date: new Date(Date.now() + 86400000 * 5).toISOString().split('T')[0],
      is_due_today: false,
      is_overdue: false,
      recurrence_type: 'QUARTERLY',
      status: 'PARTIALLY_PAID',
      amount_paid: 6000.00,
      remaining_balance: 4000.00,
      responsible_member_name: 'Karthika',
      notes: 'Installment 1 paid',
      payments: [
        {
          id: 'pay-101',
          amount_paid: 6000.00,
          currency: 'INR',
          paid_date: new Date().toISOString().split('T')[0],
          paid_by_name: 'Karthika',
          payment_method: 'BANK_TRANSFER',
          notes: 'First installment'
        }
      ]
    },
    {
      id: 'bill-5',
      title: 'Piped Gas (PNG)',
      category_name: 'Utilities',
      expected_amount: 800.00,
      currency: 'INR',
      due_date: new Date(Date.now() - 86400000 * 5).toISOString().split('T')[0],
      is_due_today: false,
      is_overdue: false,
      recurrence_type: 'MONTHLY',
      status: 'PAID',
      amount_paid: 842.00,
      remaining_balance: 0.00,
      responsible_member_name: 'Vivek',
      notes: 'Billed ₹842 actual',
      payments: [
        {
          id: 'pay-102',
          amount_paid: 842.00,
          currency: 'INR',
          paid_date: new Date(Date.now() - 86400000 * 5).toISOString().split('T')[0],
          paid_by_name: 'Vivek',
          payment_method: 'UPI',
          notes: 'GooglePay reference #88219'
        }
      ]
    }
  ]);

  // Form State for detailed add
  const [newDueDate, setNewDueDate] = useState('');
  const [newCategory, setNewCategory] = useState('Utilities');
  const [newRecurrenceType, setNewRecurrenceType] = useState('MONTHLY');
  const [newResponsible, setNewResponsible] = useState('Vivek');
  const [newNotes, setNewNotes] = useState('');

  const commonTemplates = [
    { title: 'Electricity Bill', cat: 'Utilities', amount: 2000, rec: 'MONTHLY' },
    { title: 'Water & Sewerage', cat: 'Utilities', amount: 650, rec: 'MONTHLY' },
    { title: 'Fiber Internet', cat: 'Communication', amount: 999, rec: 'MONTHLY' },
    { title: 'House Rent', cat: 'Housing', amount: 25000, rec: 'MONTHLY' },
    { title: 'Piped Gas', cat: 'Utilities', amount: 800, rec: 'MONTHLY' },
    { title: 'Car Insurance', cat: 'Insurance', amount: 14500, rec: 'YEARLY' },
  ];

  const handleQuickAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickTitle.trim() || !quickAmount) return;

    const amt = parseFloat(quickAmount);
    const todayStr = new Date().toISOString().split('T')[0];
    const due = newDueDate || todayStr;

    const newBill: BillItem = {
      id: `bill-${Date.now()}`,
      title: quickTitle.trim(),
      category_name: newCategory,
      expected_amount: amt,
      currency: 'INR',
      due_date: due,
      recurrence_type: newRecurrenceType,
      status: 'UNPAID',
      amount_paid: 0.00,
      remaining_balance: amt,
      responsible_member_name: newResponsible || null,
      notes: newNotes.trim() || null,
      payments: [],
      is_due_today: due === todayStr,
      is_overdue: due < todayStr
    };

    setBills([newBill, ...bills]);
    setQuickTitle('');
    setQuickAmount('');
    setNewDueDate('');
    setNewNotes('');
    setIsDetailOpen(false);
  };

  const handleOpenPayModal = (bill: BillItem) => {
    setPayingBill(bill);
    setPayAmount(bill.remaining_balance.toString());
    setPayDate(new Date().toISOString().split('T')[0]);
    setPayMethod('UPI');
    setPayNotes('');
    setPayPayer('Vivek');
  };

  const handleSavePayment = (e: React.FormEvent) => {
    e.preventDefault();
    if (!payingBill || !payAmount) return;

    const pAmt = parseFloat(payAmount);
    if (pAmt <= 0) return;

    const newPayment: PaymentRecord = {
      id: `pay-${Date.now()}`,
      amount_paid: pAmt,
      currency: payingBill.currency,
      paid_date: payDate,
      paid_by_name: payPayer,
      payment_method: payMethod,
      notes: payNotes.trim() || null
    };

    setBills(bills.map(b => {
      if (b.id === payingBill.id) {
        const totalPaid = b.amount_paid + pAmt;
        const isPaid = totalPaid >= b.expected_amount;
        return {
          ...b,
          amount_paid: totalPaid,
          remaining_balance: Math.max(0, b.expected_amount - totalPaid),
          status: isPaid ? 'PAID' : 'PARTIALLY_PAID',
          payments: [newPayment, ...b.payments]
        };
      }
      return b;
    }));

    setPayingBill(null);
  };

  const handleDelete = (id: string) => {
    setBills(bills.filter(b => b.id !== id));
  };

  // Metrics
  const activeBills = bills.filter(b => b.status !== 'PAID' && b.status !== 'CANCELLED');
  const dueTodayBills = activeBills.filter(b => b.is_due_today);
  const overdueBills = activeBills.filter(b => b.is_overdue);
  const upcomingBills = activeBills.filter(b => !b.is_due_today && !b.is_overdue);
  const myResponsibleBills = activeBills.filter(b => b.responsible_member_name === 'Vivek');
  const paidBills = bills.filter(b => b.status === 'PAID');

  const totalUnpaidAmount = activeBills.reduce((sum, b) => sum + b.remaining_balance, 0);
  const dueTodayAmount = dueTodayBills.reduce((sum, b) => sum + b.remaining_balance, 0);
  const overdueAmount = overdueBills.reduce((sum, b) => sum + b.remaining_balance, 0);
  const upcomingAmount = upcomingBills.reduce((sum, b) => sum + b.remaining_balance, 0);
  const paidThisMonthAmount = paidBills.reduce((sum, b) => sum + b.amount_paid, 0);

  const filteredBills = bills.filter(b => {
    if (activeTab === 'PAID') return b.status === 'PAID';
    if (b.status === 'PAID') return false;
    if (activeTab === 'DUE_TODAY') return b.is_due_today;
    if (activeTab === 'OVERDUE') return b.is_overdue;
    if (activeTab === 'UPCOMING') return !b.is_due_today && !b.is_overdue;
    if (activeTab === 'MY_RESPONSIBLE') return b.responsible_member_name === 'Vivek';
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
        </div>

        {/* Top Financial KPI Metrics */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 'var(--space-3)' }}>
          <Card
            onClick={() => setActiveTab('DUE_TODAY')}
            style={{
              padding: '12px 16px',
              cursor: 'pointer',
              border: activeTab === 'DUE_TODAY' ? '2px solid var(--color-primary-900)' : '1px solid var(--color-border)',
              backgroundColor: dueTodayBills.length > 0 ? 'rgba(239, 68, 68, 0.05)' : 'var(--color-surface-card)'
            }}
          >
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>Due Today ({dueTodayBills.length})</div>
            <div style={{ fontSize: '20px', fontWeight: 700, color: dueTodayBills.length > 0 ? '#ef4444' : 'var(--color-text-primary)', marginTop: '2px' }}>
              ₹{dueTodayAmount.toLocaleString()}
            </div>
          </Card>

          <Card
            onClick={() => setActiveTab('OVERDUE')}
            style={{
              padding: '12px 16px',
              cursor: 'pointer',
              border: activeTab === 'OVERDUE' ? '2px solid var(--color-primary-900)' : '1px solid var(--color-border)',
              backgroundColor: overdueBills.length > 0 ? 'rgba(245, 158, 11, 0.08)' : 'var(--color-surface-card)'
            }}
          >
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>Overdue ({overdueBills.length})</div>
            <div style={{ fontSize: '20px', fontWeight: 700, color: overdueBills.length > 0 ? '#f59e0b' : 'var(--color-text-primary)', marginTop: '2px' }}>
              ₹{overdueAmount.toLocaleString()}
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
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>Upcoming ({upcomingBills.length})</div>
            <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: '2px' }}>
              ₹{upcomingAmount.toLocaleString()}
            </div>
          </Card>

          <Card
            onClick={() => setActiveTab('PAID')}
            style={{
              padding: '12px 16px',
              cursor: 'pointer',
              border: activeTab === 'PAID' ? '2px solid var(--color-primary-900)' : '1px solid var(--color-border)'
            }}
          >
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>Paid This Month ({paidBills.length})</div>
            <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--status-in-stock)', marginTop: '2px' }}>
              ₹{paidThisMonthAmount.toLocaleString()}
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
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>Total Unpaid ({activeBills.length})</div>
            <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--color-primary-900)', marginTop: '2px' }}>
              ₹{totalUnpaidAmount.toLocaleString()}
            </div>
          </Card>
        </div>
      </div>

      {/* Quick Add Bar & Presets */}
      <Card style={{ padding: '16px 20px', border: '2px solid var(--color-primary-900)' }}>
        <form onSubmit={handleQuickAdd} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}>
            <input
              type="text"
              placeholder="Bill title (e.g. Electricity, Water, Rent)..."
              value={quickTitle}
              onChange={(e) => setQuickTitle(e.target.value)}
              style={{
                flex: 2,
                minWidth: '200px',
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
              type="number"
              step="0.01"
              placeholder="Amount (₹)"
              value={quickAmount}
              onChange={(e) => setQuickAmount(e.target.value)}
              style={{
                flex: 1,
                minWidth: '110px',
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
              <span>Add Bill</span>
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsDetailOpen(!isDetailOpen)}
            >
              {isDetailOpen ? 'Simple' : 'Options ▾'}
            </Button>
          </div>

          {/* Preset Chips */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', marginRight: '4px' }}>
              Common Bills:
            </span>
            {commonTemplates.map(tpl => (
              <button
                key={tpl.title}
                type="button"
                onClick={() => {
                  setQuickTitle(tpl.title);
                  setQuickAmount(tpl.amount.toString());
                  setNewCategory(tpl.cat);
                  setNewRecurrenceType(tpl.rec);
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

          {/* Optional Expanded Options */}
          {isDetailOpen && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', paddingTop: '8px', borderTop: '1px solid var(--color-border)' }}>
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
                  <option value="Vivek">Vivek</option>
                  <option value="Karthika">Karthika</option>
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
                  <option value="Transportation">Transportation</option>
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
                  <option value="NONE">One-time</option>
                  <option value="MONTHLY">Monthly</option>
                  <option value="QUARTERLY">Quarterly</option>
                  <option value="HALF_YEARLY">Half-Yearly</option>
                  <option value="YEARLY">Yearly</option>
                </select>
              </div>
            </div>
          )}
        </form>
      </Card>

      {/* Filter Tabs */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: 'var(--space-2)', overflowX: 'auto' }}>
        {[
          { id: 'ALL', label: `All Active (${activeBills.length})` },
          { id: 'DUE_TODAY', label: `Due Today (${dueTodayBills.length})` },
          { id: 'OVERDUE', label: `Overdue (${overdueBills.length})` },
          { id: 'UPCOMING', label: `Upcoming (${upcomingBills.length})` },
          { id: 'MY_RESPONSIBLE', label: `My Responsible (${myResponsibleBills.length})` },
          { id: 'PAID', label: `Paid History (${paidBills.length})` },
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

      {/* Bill List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
        {filteredBills.length === 0 ? (
          <Card style={{ padding: 'var(--space-12) var(--space-4)', textAlign: 'center' }}>
            <Sparkles size={36} color="var(--status-in-stock)" style={{ margin: '0 auto 10px' }} />
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-primary-900)' }}>
              {activeTab === 'PAID' ? 'No paid bills recorded yet' : 'No bills due in this view'}
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
              All household expenses are organized and up to date.
            </p>
          </Card>
        ) : (
          filteredBills.map((bill) => (
            <Card
              key={bill.id}
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
                padding: '16px 20px',
                opacity: bill.status === 'PAID' ? 0.85 : 1,
                borderLeft: bill.is_overdue
                  ? '4px solid #ef4444'
                  : bill.is_due_today
                  ? '4px solid #f59e0b'
                  : '1px solid var(--color-border)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '14px', flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                      {bill.title}
                    </span>

                    {bill.category_name && (
                      <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '4px', background: 'var(--color-surface-hover)', color: 'var(--color-text-secondary)', fontWeight: 500 }}>
                        {bill.category_name}
                      </span>
                    )}

                    {bill.is_overdue && (
                      <span style={{ fontSize: '11px', padding: '2px 6px', borderRadius: '4px', background: '#fee2e2', color: '#b91c1c', fontWeight: 700 }}>
                        OVERDUE
                      </span>
                    )}
                    {bill.is_due_today && (
                      <span style={{ fontSize: '11px', padding: '2px 6px', borderRadius: '4px', background: '#fef3c7', color: '#b45309', fontWeight: 700 }}>
                        DUE TODAY
                      </span>
                    )}
                    {bill.status === 'PARTIALLY_PAID' && (
                      <span style={{ fontSize: '11px', padding: '2px 6px', borderRadius: '4px', background: '#dbeafe', color: '#1d4ed8', fontWeight: 700 }}>
                        PARTIALLY PAID
                      </span>
                    )}
                    {bill.status === 'PAID' && (
                      <span style={{ fontSize: '11px', padding: '2px 6px', borderRadius: '4px', background: '#dcfce7', color: '#15803d', fontWeight: 700 }}>
                        PAID
                      </span>
                    )}
                  </div>

                  {bill.notes && (
                    <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
                      {bill.notes}
                    </div>
                  )}

                  <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '14px', marginTop: '4px', fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <User size={13} />
                      <span>Responsible: {bill.responsible_member_name ? bill.responsible_member_name : 'Unassigned'}</span>
                    </span>

                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={13} />
                      <span>Due {bill.due_date}</span>
                    </span>

                    {bill.recurrence_type && bill.recurrence_type !== 'NONE' && (
                      <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--color-primary-900)', fontWeight: 600 }}>
                        <Repeat size={13} />
                        <span>Repeats {bill.recurrence_type.toLowerCase()}</span>
                      </span>
                    )}
                  </div>
                </div>

                {/* Amount & Actions */}
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '6px' }}>
                  <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                    ₹{bill.expected_amount.toLocaleString()}
                  </div>

                  {bill.status === 'PARTIALLY_PAID' && (
                    <div style={{ fontSize: '12px', color: '#1d4ed8', fontWeight: 600 }}>
                      Paid ₹{bill.amount_paid.toLocaleString()} • ₹{bill.remaining_balance.toLocaleString()} Remaining
                    </div>
                  )}

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {bill.status !== 'PAID' && (
                      <Button size="sm" onClick={() => handleOpenPayModal(bill)}>
                        <CreditCard size={14} />
                        <span>Record Payment</span>
                      </Button>
                    )}

                    <button
                      onClick={() => handleDelete(bill.id)}
                      title="Delete Bill"
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-tertiary)', padding: '4px' }}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              </div>

              {/* Payment History Accordion if payments exist */}
              {bill.payments.length > 0 && (
                <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '8px', marginTop: '4px', fontSize: '12px' }}>
                  <span style={{ fontWeight: 600, color: 'var(--color-text-secondary)' }}>Payment Ledger:</span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '4px' }}>
                    {bill.payments.map((p) => (
                      <div key={p.id} style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--color-text-primary)' }}>
                        <span>
                          💳 ₹{p.amount_paid.toLocaleString()} paid on {p.paid_date} by {p.paid_by_name} ({p.payment_method})
                          {p.notes && ` — "${p.notes}"`}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          ))
        )}
      </div>

      {/* Record Payment Modal Dialog */}
      {payingBill && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <Card style={{ width: '100%', maxWidth: '480px', padding: '24px', border: '2px solid var(--color-primary-900)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: 700 }}>Record Bill Payment</h3>
                <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
                  {payingBill.title} • Expected: ₹{payingBill.expected_amount.toLocaleString()}
                </p>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setPayingBill(null)}>✕</Button>
            </div>

            <form onSubmit={handleSavePayment} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', fontWeight: 600 }}>Amount Paid (₹)</label>
                <input
                  type="number"
                  step="0.01"
                  value={payAmount}
                  onChange={(e) => setPayAmount(e.target.value)}
                  placeholder="Enter actual amount paid..."
                  style={{ height: '40px', padding: '0 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)', fontSize: '15px', fontWeight: 600 }}
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
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
                    <option value="Vivek">Vivek</option>
                    <option value="Karthika">Karthika</option>
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
                  <option value="BANK_TRANSFER">Bank NetBanking / NEFT</option>
                  <option value="CARD">Credit / Debit Card</option>
                  <option value="CASH">Cash</option>
                  <option value="OTHER">Other / Auto-Debit</option>
                </select>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '12px', fontWeight: 600 }}>Reference Notes / Txn ID (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. Txn #994821 or auto-debit"
                  value={payNotes}
                  onChange={(e) => setPayNotes(e.target.value)}
                  style={{ height: '38px', padding: '0 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '8px' }}>
                <Button type="button" variant="secondary" onClick={() => setPayingBill(null)}>
                  Cancel
                </Button>
                <Button type="submit">
                  <Check size={16} />
                  <span>Save Payment</span>
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}
    </div>
  );
}
