export type SubscriptionStatus = 'TRIALING' | 'ACTIVE' | 'PAST_DUE' | 'CANCELED' | 'EXPIRED';

export interface SubscriptionPlan {
  id: string;
  name: string;
  code: string;
  currency: string;
  admin_base_price_annual: number;
  price_per_additional_member_annual: number;
  introductory_trial_days: number;
  is_active: boolean;
}

export interface MemberEntitlement {
  user_id: string;
  display_name: string;
  role: string;
  is_admin_or_owner: boolean;
  is_free_entitled: boolean;
  requires_paid_seat: boolean;
  is_seat_covered: boolean;
}

export interface HomeSubscriptionOverview {
  home_id: string;
  status: SubscriptionStatus;
  plan_name: string;
  plan_code: string;
  currency: string;
  admin_base_price_annual: number;
  price_per_additional_member_annual: number;

  introductory_period_starts_at: string;
  introductory_period_ends_at: string;
  is_in_introductory_trial: bool;
  days_remaining_in_introductory_period: number;

  total_active_members: number;
  free_entitled_seats: number;
  required_paid_seats: number;
  active_paid_seats: number;
  is_fully_covered: bool;

  annual_total_price: number;
  members_entitlements: MemberEntitlement[];
}
