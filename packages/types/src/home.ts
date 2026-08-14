export interface Home {
  id: string;
  name: string;
  currency: string;
  timezone: string;
  address?: string | null;
  avatar_url?: string | null;
  created_by: string;
  role?: string;
  created_at: string;
  updated_at: string;
}

export interface HomeDetail extends Home {
  member_count: number;
  inventory_count: number;
  active_chores_count: number;
}

export interface CreateHomeInput {
  name: string;
  currency?: string;
  timezone?: string;
  address?: string | null;
  avatar_url?: string | null;
}

export interface UpdateHomeInput {
  name?: string;
  currency?: string;
  timezone?: string;
  address?: string | null;
  avatar_url?: string | null;
}

export interface HomeMember {
  id: string;
  home_id: string;
  user_id: string;
  display_name: string;
  email: string;
  avatar_url?: string | null;
  role: 'OWNER' | 'ADMIN' | 'MEMBER' | 'CHILD' | 'GUEST';
  status: 'ACTIVE' | 'SUSPENDED' | 'LEFT';
  joined_at: string;
}
