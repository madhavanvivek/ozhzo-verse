export interface EventParticipant {
  user_id: string;
  display_name: string;
  avatar_url?: string | null;
  status: 'INVITED' | 'ACCEPTED' | 'DECLINED';
}

export interface HomeEvent {
  id: string;
  home_id: string;
  title: string;
  description?: string | null;
  start_time: string;
  end_time: string;
  is_all_day: boolean;
  location?: string | null;
  reminder_minutes_before?: number | null;
  created_by: string;
  participants: EventParticipant[];
  created_at: string;
  updated_at: string;
}

export interface CreateEventInput {
  title: string;
  description?: string | null;
  start_time: string;
  end_time: string;
  is_all_day?: boolean;
  location?: string | null;
  reminder_minutes_before?: number | null;
  participant_user_ids?: string[];
}

export interface UpdateEventInput {
  title?: string;
  description?: string | null;
  start_time?: string;
  end_time?: string;
  is_all_day?: boolean;
  location?: string | null;
  reminder_minutes_before?: number | null;
  participant_user_ids?: string[];
}
