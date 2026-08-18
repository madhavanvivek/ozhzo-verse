'use client';

import React, { useEffect, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import {
  Plus,
  CheckCircle2,
  Trash2,
  Sparkles
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

interface ShoppingItem {
  id: string;
  name: string;
  quantity: number;
  unit: string;
  notes?: string | null;
  status: 'PENDING' | 'PURCHASED' | 'CANCELLED';
  added_by_name?: string | null;
  purchased_by_name?: string | null;
  version: number;
}

export default function ShoppingPage() {
  const [activeHomeId, setActiveHomeId] = useState<string | null>(null);
  const [items, setItems] = useState<ShoppingItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Form State
  const [newItemName, setNewItemName] = useState('');
  const [newItemQty, setNewItemQty] = useState('1');
  const [newItemUnit, setNewItemUnit] = useState('pcs');
  const [newItemNotes, setNewItemNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const savedHomeId = localStorage.getItem('active_home_id');
      let homeId = savedHomeId;

      if (!homeId) {
        const homes = await apiClient.get<Array<{ id: string }>>('/homes');
        if (homes && homes.length > 0) {
          homeId = homes[0].id;
          localStorage.setItem('active_home_id', homeId);
        }
      }

      setActiveHomeId(homeId);

      if (homeId) {
        const res = await apiClient.get<ShoppingItem[]>(`/homes/${homeId}/purchase-list?status_filter=ALL`);
        if (Array.isArray(res)) {
          setItems(res.map((i: any) => ({
            id: i.id,
            name: i.name,
            quantity: parseFloat(i.quantity) || 1,
            unit: i.unit || 'pcs',
            notes: i.notes,
            status: i.status || 'PENDING',
            added_by_name: i.added_by_name,
            purchased_by_name: i.purchased_by_name,
            version: i.version || 1
          })));
        }
      }
    } catch (err) {
      console.error('Failed to load shopping list:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const activeItems = items.filter(i => i.status === 'PENDING');
  const checkedItems = items.filter(i => i.status === 'PURCHASED');
  const totalCount = items.length;
  const completedCount = checkedItems.length;
  const progressPercent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  const handleToggleCheck = async (item: ShoppingItem) => {
    if (!activeHomeId) return;

    try {
      if (item.status === 'PENDING') {
        await apiClient.post(`/homes/${activeHomeId}/purchase-list/${item.id}/purchase`, {
          restock_inventory: true
        });
      }
      await loadData();
    } catch (err: any) {
      console.error('Failed to toggle purchase state:', err);
      alert(err?.message || 'Failed to update item status.');
    }
  };

  const handleAddItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newItemName.trim() || !activeHomeId) return;

    setIsSubmitting(true);
    try {
      const payload = {
        name: newItemName.trim(),
        quantity: parseFloat(newItemQty) || 1,
        unit: newItemUnit.trim() || 'pcs',
        notes: newItemNotes.trim() || undefined
      };

      await apiClient.post(`/homes/${activeHomeId}/purchase-list`, payload);
      setNewItemName('');
      setNewItemQty('1');
      setNewItemNotes('');
      await loadData();
    } catch (err: any) {
      console.error('Failed to add purchase item:', err);
      alert(err?.message || 'Failed to add item to purchase list.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteItem = async (id: string) => {
    if (!activeHomeId) return;
    try {
      await apiClient.delete(`/homes/${activeHomeId}/purchase-list/${id}`);
      await loadData();
    } catch (err: any) {
      console.error('Failed to delete purchase item:', err);
      alert(err?.message || 'Failed to remove item.');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '900px', width: '100%' }}>
      {/* Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-primary-900)', lineHeight: 1.2 }}>
            Household Shopping List
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
            Shared family groceries and household supplies with live cross-member synchronization.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Badge variant="in-stock">Live Sync Active</Badge>
        </div>
      </div>

      {/* Progress Bar */}
      <Card variant="subtle" style={{ padding: '14px 18px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-primary-900)' }}>
            Shopping Progress
          </span>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>
            {completedCount} of {totalCount} items purchased ({progressPercent}%)
          </span>
        </div>
        <div style={{ width: '100%', height: '8px', backgroundColor: 'var(--color-border-subtle)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
          <div style={{ width: `${progressPercent}%`, height: '100%', backgroundColor: 'var(--status-in-stock)', transition: 'width 0.3s ease' }} />
        </div>
      </Card>

      {/* Quick Add Bar */}
      <Card style={{ padding: 'var(--space-4)' }}>
        <form onSubmit={handleAddItem} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <div style={{ flex: '2 1 200px' }}>
              <Input
                id="itemName"
                placeholder="Add grocery or supply item... (e.g. Olive Oil, Milk, Bread)"
                value={newItemName}
                onChange={(e) => setNewItemName(e.target.value)}
                required
              />
            </div>
            <div style={{ flex: '1 1 80px' }}>
              <Input
                id="itemQty"
                type="number"
                step="0.1"
                placeholder="Qty"
                value={newItemQty}
                onChange={(e) => setNewItemQty(e.target.value)}
              />
            </div>
            <div style={{ flex: '1 1 90px' }}>
              <Input
                id="itemUnit"
                placeholder="Unit (pcs, kg)"
                value={newItemUnit}
                onChange={(e) => setNewItemUnit(e.target.value)}
              />
            </div>
            <Button type="submit" disabled={isSubmitting} style={{ minHeight: '40px', padding: '0 18px' }}>
              <Plus size={16} />
              <span>{isSubmitting ? 'Adding...' : 'Add Item'}</span>
            </Button>
          </div>
        </form>
      </Card>

      {/* Active Items */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
        <h2 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          To Buy ({activeItems.length})
        </h2>

        {isLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {[1, 2, 3].map((i) => (
              <div key={i} style={{ height: '56px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: 'var(--radius-md)', animation: 'pulse 1.5s infinite' }} />
            ))}
          </div>
        ) : activeItems.length === 0 ? (
          <Card style={{ padding: 'var(--space-8)', textAlign: 'center' }}>
            <Sparkles size={28} color="var(--status-in-stock)" style={{ margin: '0 auto 8px' }} />
            <p style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-primary-900)' }}>All items purchased!</p>
            <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>Your shopping list is currently clear.</p>
          </Card>
        ) : (
          activeItems.map((item) => (
            <Card
              key={item.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px 16px',
                transition: 'all 0.15s ease',
                gap: '12px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: 0, flex: 1 }}>
                <button
                  onClick={() => handleToggleCheck(item)}
                  className="touch-target"
                  style={{
                    width: '28px',
                    height: '28px',
                    borderRadius: '50%',
                    border: '2px solid var(--color-border-strong)',
                    backgroundColor: 'transparent',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0
                  }}
                  title="Mark as Purchased"
                  aria-label={`Mark ${item.name} as purchased`}
                />
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {item.name}
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                    {item.quantity} {item.unit}
                    {item.added_by_name && ` • Added by ${item.added_by_name}`}
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
                <Badge variant="neutral">Pending</Badge>
                <button
                  onClick={() => handleDeleteItem(item.id)}
                  className="touch-target"
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-tertiary)', padding: '6px' }}
                  aria-label={`Delete ${item.name}`}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </Card>
          ))
        )}
      </div>

      {/* Checked Items */}
      {checkedItems.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', marginTop: 'var(--space-2)' }}>
          <h2 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Purchased ({checkedItems.length})
          </h2>

          {checkedItems.map((item) => (
            <Card
              key={item.id}
              variant="subtle"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 16px',
                opacity: 0.75,
                gap: '12px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: 0, flex: 1 }}>
                <div
                  style={{
                    width: '28px',
                    height: '28px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--status-in-stock)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0
                  }}
                >
                  <CheckCircle2 size={18} color="#ffffff" />
                </div>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--color-text-secondary)', textDecoration: 'line-through', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {item.name}
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--color-text-tertiary)' }}>
                    {item.quantity} {item.unit} • Purchased
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
                <button
                  onClick={() => handleDeleteItem(item.id)}
                  className="touch-target"
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-tertiary)', padding: '6px' }}
                  aria-label={`Delete ${item.name}`}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
