export type TaskPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';
export type TaskStatus = 'TODO' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';
export type TaskRecurrence = 'DAILY' | 'WEEKLY' | 'MONTHLY' | 'CUSTOM';

export interface Task {
  id: string;
  home_id: string;
  title: string;
  description?: string | null;
  priority: TaskPriority;
  status: TaskStatus;
  assigned_to?: string | null;
  assigned_to_name?: string | null;
  due_date?: string | null;
  recurrence_rule?: TaskRecurrence | string | null;
  created_by: string;
  completed_by?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateTaskInput {
  title: string;
  description?: string | null;
  priority?: TaskPriority;
  assigned_to?: string | null;
  due_date?: string | null;
  recurrence_rule?: TaskRecurrence | string | null;
}

export interface UpdateTaskInput {
  title?: string;
  description?: string | null;
  priority?: TaskPriority;
  status?: TaskStatus;
  assigned_to?: string | null;
  due_date?: string | null;
  recurrence_rule?: TaskRecurrence | string | null;
}

export interface PaginatedTasks {
  items: Task[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
