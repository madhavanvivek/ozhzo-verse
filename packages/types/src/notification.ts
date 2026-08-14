export type NotificationType =
  | 'TASK_ASSIGNED'
  | 'BILL_REMINDER'
  | 'LOW_STOCK'
  | 'EVENT_REMINDER'
  | 'HOME_INVITATION'
  | 'SYSTEM';

export interface NotificationItem {
  id: string;
  home_id: string;
  user_id: string;
  title: string;
  body: string;
  type: NotificationType | string;
  is_read: boolean;
  read_at?: string | null;
  created_at: string;
}

export interface NotificationPreferences {
  in_app_enabled: boolean;
  push_enabled: boolean;
  email_enabled: boolean;
  sms_enabled: boolean;
  whatsapp_enabled: boolean;

  task_assigned_enabled: boolean;
  bill_reminder_enabled: boolean;
  low_stock_enabled: boolean;
  event_reminder_enabled: boolean;
  home_invitation_enabled: boolean;
  system_enabled: boolean;
}

export interface UpdateNotificationPreferencesInput {
  in_app_enabled?: boolean;
  push_enabled?: boolean;
  email_enabled?: boolean;
  sms_enabled?: boolean;
  whatsapp_enabled?: boolean;

  task_assigned_enabled?: boolean;
  bill_reminder_enabled?: boolean;
  low_stock_enabled?: boolean;
  event_reminder_enabled?: boolean;
  home_invitation_enabled?: boolean;
  system_enabled?: boolean;
}

export interface PaginatedNotifications {
  items: NotificationItem[];
  unread_count: number;
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
