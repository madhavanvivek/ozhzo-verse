export interface User {
  id: string;
  email: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserProfile {
  user_id: string;
  display_name: string;
  phone_number?: string | null;
  avatar_url?: string | null;
  timezone: string;
  preferred_language: string;
}

export interface AuthenticatedUser extends UserProfile {
  id: string;
  email: string;
  is_active: boolean;
  is_verified: boolean;
  homes: Array<{
    home_id: string;
    name: string;
    role: string;
    avatar_url?: string | null;
  }>;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user_id: string;
  email: string;
}
