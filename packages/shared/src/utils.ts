import { InventoryStatus } from '@ozhzo/types';

export function computeInventoryStatus(
  quantity: number,
  minThreshold: number | null | undefined,
  expiryDateStr?: string | null
): InventoryStatus {
  if (quantity <= 0) {
    return 'OUT_OF_STOCK';
  }

  if (expiryDateStr) {
    const today = new Date().toISOString().split('T')[0];
    if (expiryDateStr < today) {
      return 'EXPIRED';
    }
  }

  const threshold = minThreshold ?? 1.0;
  if (quantity <= threshold) {
    return 'LOW_STOCK';
  }

  return 'IN_STOCK';
}

export function formatCurrency(amount: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency
  }).format(amount);
}

export function getInitials(name: string): string {
  if (!name) return 'H';
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) {
    return parts[0].substring(0, 2).toUpperCase();
  }
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}
