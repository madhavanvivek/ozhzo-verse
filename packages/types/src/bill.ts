export type BillStatus = 'UNPAID' | 'PAID' | 'OVERDUE';
export type BillRecurrence = 'MONTHLY' | 'QUARTERLY' | 'ANNUAL' | 'ONE_TIME';

export interface BillReminder {
  id: string;
  bill_id: string;
  reminder_date: string;
  days_before: number;
  is_sent: boolean;
  sent_at?: string | null;
}

export interface BillPayment {
  id: string;
  bill_id: string;
  home_id: string;
  amount_paid: number;
  paid_by?: string | null;
  paid_by_name?: string | null;
  paid_at: string;
  reference_notes?: string | null;
  created_at: string;
}

export interface Bill {
  id: string;
  home_id: string;
  title: string;
  category: string;
  amount: number;
  currency: string;
  due_date: string;
  recurrence_interval?: BillRecurrence | string | null;
  status: BillStatus;
  default_payer_id?: string | null;
  default_payer_name?: string | null;
  created_at: string;
  updated_at: string;
}

export interface BillDetail extends Bill {
  reminders: BillReminder[];
  payments: BillPayment[];
}

export interface CreateBillInput {
  title: string;
  category?: string;
  amount: number;
  currency?: string;
  due_date: string;
  recurrence_interval?: BillRecurrence | string | null;
  default_payer_id?: string | null;
  reminder_days_before?: number[];
}

export interface UpdateBillInput {
  title?: string;
  category?: string;
  amount?: number;
  currency?: string;
  due_date?: string;
  recurrence_interval?: BillRecurrence | string | null;
  default_payer_id?: string | null;
  status?: BillStatus;
}
