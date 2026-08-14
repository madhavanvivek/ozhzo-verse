export type ShoppingPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';

export interface ShoppingList {
  id: string;
  home_id: string;
  name: string;
  total_items: number;
  checked_items: number;
  created_at: string;
  updated_at: string;
}

export interface ShoppingListItem {
  id: string;
  list_id: string;
  home_id: string;
  inventory_item_id?: string | null;
  name: string;
  quantity: number;
  unit: string;
  priority: ShoppingPriority;
  is_checked: boolean;
  added_by?: string | null;
  assigned_to?: string | null;
  assigned_to_name?: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface CreateShoppingItemInput {
  name: string;
  quantity?: number;
  unit?: string;
  priority?: ShoppingPriority;
  assigned_to?: string | null;
  inventory_item_id?: string | null;
}

export interface UpdateShoppingItemInput {
  name?: string;
  quantity?: number;
  unit?: string;
  priority?: ShoppingPriority;
  assigned_to?: string | null;
  is_checked?: boolean;
  version?: number;
}
