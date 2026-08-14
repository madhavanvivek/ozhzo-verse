export type InventoryStatus = 'IN_STOCK' | 'LOW_STOCK' | 'OUT_OF_STOCK' | 'EXPIRED';

export interface InventoryCategory {
  id: string;
  home_id: string;
  name: string;
  icon?: string | null;
  sort_order: number;
  item_count: number;
  created_at: string;
}

export interface InventoryItem {
  id: string;
  home_id: string;
  category_id?: string | null;
  category_name?: string | null;
  name: string;
  quantity: number;
  unit: string;
  min_threshold?: number | null;
  location?: string | null;
  expiry_date?: string | null;
  notes?: string | null;
  status: InventoryStatus;
  created_at: string;
  updated_at: string;
}

export interface CreateInventoryItemInput {
  category_id?: string | null;
  name: string;
  quantity: number;
  unit: string;
  min_threshold?: number | null;
  location?: string | null;
  expiry_date?: string | null;
  notes?: string | null;
}

export interface UpdateInventoryItemInput {
  category_id?: string | null;
  name?: string;
  quantity?: number;
  unit?: string;
  min_threshold?: number | null;
  location?: string | null;
  expiry_date?: string | null;
  notes?: string | null;
}

export interface PaginatedInventory {
  items: InventoryItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
