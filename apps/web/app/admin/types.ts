export interface AdminAnalyticsSummary {
  total_users: number;
  active_users: number;
  suspended_users: number;
  total_homes: number;
  active_homes: number;
  suspended_homes: number;
  average_members_per_home: number;
  total_active_subscriptions: number;
  total_paid_member_seats: number;
  generated_at: string;
}

export interface AdminSystemConfig {
  environment: string;
  supported_currencies: string[];
  default_timezone: string;
  feature_flags: Record<string, boolean>;
  available_system_roles: string[];
  available_home_roles: string[];
  password_hashing_algorithm: string;
  mfa_enforced_for_admins: boolean;
  rate_limiting_enabled: boolean;
}

export interface AdminUserListItem {
  id: string;
  email?: string | null;
  phone_number?: string | null;
  country_code?: string | null;
  display_name: string;
  is_active: boolean;
  is_verified: boolean;
  mobile_verified: boolean;
  is_super_admin: boolean;
  system_role: string;
  homes_count: number;
  created_at?: string | null;
}

export interface AdminUserHomeMembership {
  home_id: string;
  home_name: string;
  role: string;
  status: string;
  joined_at?: string | null;
}

export interface AdminUserDetail {
  id: string;
  email?: string | null;
  phone_number?: string | null;
  country_code?: string | null;
  display_name: string;
  avatar_url?: string | null;
  timezone?: string | null;
  preferred_language?: string | null;
  is_active: boolean;
  is_verified: boolean;
  mobile_verified: boolean;
  is_super_admin: boolean;
  system_role: string;
  created_at?: string | null;
  updated_at?: string | null;
  memberships: AdminUserHomeMembership[];
}

export interface AdminHomeListItem {
  id: string;
  name: string;
  public_home_id?: string | null;
  home_qr_status?: string;
  home_qr_version?: number;
  status: string;
  currency: string;
  created_by_email?: string | null;
  created_by_name?: string | null;
  members_count: number;
  subscription_status: string;
  created_at?: string | null;
}

export interface AdminHomeMemberItem {
  user_id: string;
  display_name: string;
  email?: string | null;
  phone_number?: string | null;
  role: string;
  status: string;
  created_at?: string | null;
}

export interface AdminHomeInvitationItem {
  id: string;
  email?: string | null;
  phone_number?: string | null;
  role: string;
  invitation_code?: string | null;
  status: string;
  invited_by_id: string;
  invited_by_email?: string | null;
  expires_at: string;
  created_at?: string | null;
}

export interface AdminHomeDetail {
  id: string;
  name: string;
  public_home_id?: string | null;
  home_qr_status?: string;
  home_qr_version?: number;
  status: string;
  currency: string;
  timezone: string;
  address?: string | null;
  created_by_id: string;
  created_by_email?: string | null;
  created_by_name: string;
  created_at?: string | null;
  members_count: number;
  subscription_status: string;
  subscription_plan: string;
  paid_seats: number;
  members: AdminHomeMemberItem[];
  invitations?: AdminHomeInvitationItem[];
}

export interface AdminActivityItem {
  id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  performed_by?: string | null;
  performed_by_email?: string | null;
  old_values?: string | null;
  new_values?: string | null;
  reason?: string | null;
  created_at?: string | null;
}

export interface SubscriptionPrice {
  id: string;
  plan_id: string;
  country: string;
  region: string;
  currency: string;
  billing_period: string;
  list_price: string | number;
  additional_member_list_price: string | number;
  base_price: string | number;
  additional_member_price: string | number;
  version: number;
  is_active: boolean;
  effective_from: string;
  effective_until?: string | null;
}

export interface SubscriptionFeature {
  id: string;
  code: string;
  name: string;
  description?: string | null;
  is_active: boolean;
}

export interface SubscriptionPlan {
  id: string;
  name: string;
  code: string;
  description?: string | null;
  plan_type: string;
  status: string;
  included_members: number;
  maximum_members?: number | null;
  max_homes?: number;
  additional_member_allowed: boolean;
  introductory_enabled: boolean;
  introductory_duration_days: number;
  introductory_price: string | number;
  prices?: SubscriptionPrice[];
  features?: SubscriptionFeature[];
}

export interface Promotion {
  id: string;
  code: string;
  name: string;
  description?: string | null;
  discount_type: string;
  discount_value: string | number;
  status: string;
  start_date: string;
  end_date?: string | null;
  applicable_plan_id?: string | null;
  currency?: string | null;
  country?: string | null;
  maximum_redemptions?: number | null;
  redemptions_count: number;
  new_users_only: boolean;
}

export interface Coupon {
  id: string;
  campaign_id?: string | null;
  name: string;
  code: string;
  description?: string | null;
  coupon_type: string;
  discount_value: string | number;
  free_period_value: number;
  free_period_unit: string;
  eligibility_type: string;
  target_user_id?: string | null;
  target_home_id?: string | null;
  country?: string | null;
  state?: string | null;
  district?: string | null;
  postal_code?: string | null;
  currency?: string | null;
  applicable_plan_id?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  maximum_total_redemptions?: number | null;
  redemptions_count: number;
  maximum_redemptions_per_user: number;
  maximum_redemptions_per_home: number;
  allow_stacking: boolean;
  status: string;
  notes?: string | null;
  internal_reason?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface Campaign {
  id: string;
  name: string;
  code: string;
  description?: string | null;
  status: string;
  start_date?: string | null;
  end_date?: string | null;
  budget_limit?: string | number | null;
  maximum_redemptions?: number | null;
  redemptions_count: number;
  country?: string | null;
  state?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface SubscriptionGrant {
  id: string;
  user_id?: string | null;
  home_id: string;
  plan_id: string;
  grant_type: string;
  duration_value: number;
  duration_unit: string;
  discount_value: string | number;
  start_date?: string | null;
  expiry_date?: string | null;
  status: string;
  reason: string;
  granted_by: string;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface CouponAnalytics {
  total_coupons: number;
  active_coupons: number;
  expired_coupons: number;
  total_campaigns: number;
  total_redemptions: number;
  free_users_generated: number;
  paid_conversions: number;
  coupon_conversion_rate: number;
  total_direct_grants: number;
  active_direct_grants: number;
  generated_at: string;
}

export interface AdminSubscriberListItem {
  id: string;
  user_id: string;
  user_name: string;
  user_email?: string | null;
  home_id: string;
  home_name: string;
  plan_name: string;
  plan_code: string;
  status: string;
  start_date?: string | null;
  renewal_date?: string | null;
  coupon_code?: string | null;
  discount_amount: string | number;
  paid_seats: number;
  currency: string;
  created_at?: string | null;
}

export interface PaymentTransaction {
  id: string;
  user_id: string;
  user_email?: string | null;
  home_id?: string | null;
  subscription_id?: string | null;
  plan_name: string;
  amount: string | number;
  discount_amount: string | number;
  final_amount: string | number;
  currency: string;
  provider: string;
  provider_transaction_id?: string | null;
  status: string;
  created_at: string;
}

export interface SubscriptionAnalytics {
  total_revenue: number;
  total_transactions: number;
  active_subscribers: number;
  trial_subscribers: number;
  past_due_subscribers: number;
  cancelled_subscribers: number;
  average_order_value: number;
  currency: string;
}

