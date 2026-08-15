'use client';

import React, { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import {
  Plus,
  CheckCircle2,
  Trash2,
  Sparkles,

} from 'lucide-react';

interface ShoppingItem {
  id: string;
  name: string;
  quantity: number;
  unit: string;
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';
  is_checked: boolean;
  assigned_to_name?: string | null;
  version: number;
}

export default function ShoppingPage() {
  const [items, setItems] = useState<ShoppingItem[]>([
    { id: '1', name: 'Extra Virgin Olive Oil', quantity: 1, unit: 'bottles', priority: 'HIGH', is_checked: false, assigned_to_name: 'Alex', version: 1 },
    { id: '2', name: 'Almond Milk (Unsweetened)', quantity: 2, unit: 'liters', priority: 'HIGH', is_checked: false, assigned_to_name: 'Sarah', version: 1 },
    { id: '3', name: 'Greek Yogurt (Plain)', quantity: 1, unit: 'tub', priority: 'MEDIUM', is_checked: false, assigned_to_name: null, version: 1 },
    { id: '4', name: 'Organic Sourdough Bread', quantity: 1, unit: 'loaf', priority: 'LOW', is_checked: false, assigned_to_name: null, version: 1 },
    { id: '5', name: 'Paper Towels (6-Pack)', quantity: 1, unit: 'pack', priority: 'MEDIUM', is_checked: true, assigned_to_name: 'Alex', version: 2 },
  ]);

  const [newItemName, setNewItemName] = useState('');
  const [newItemQty, setNewItemQty] = useState('1');
  const [newItemUnit, setNewItemUnit] = useState('pcs');
  const [newItemPriority, setNewItemPriority] = useState<'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT'>('MEDIUM');

  const activeItems = items.filter(i => !i.is_checked);
  const checkedItems = items.filter(i => i.is_checked);
  const totalCount = items.length;
  const completedCount = checkedItems.length;
  const progressPercent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  const handleToggleCheck = (id: string) => {
    setItems(items.map(item => {
      if (item.id === id) {
        return { ...item, is_checked: !item.is_checked, version: item.version + 1 };
      }
      return item;
    }));
  };

  const handleAddItem = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newItemName.trim()) return;

    const newItem: ShoppingItem = {
      id: `item-${Date.now()}`,
      name: newItemName.trim(),
      quantity: parseFloat(newItemQty) || 1,
      unit: newItemUnit || 'pcs',
      priority: newItemPriority,
      is_checked: false,
      assigned_to_name: null,
      version: 1,
    };

    setItems([newItem, ...items]);
    setNewItemName('');
    setNewItemQty('1');
  };

  const handleDeleteItem = (id: string) => {
    setItems(items.filter(i => i.id !== id));
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '900px' }}>
      {/* Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-3)' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-primary-900)' }}>
            Household Shopping List
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)' }}>
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
      <Card>
        <form onSubmit={handleAddItem} style={{ display: 'grid', gridTemplateColumns: '3fr 1fr 1fr 1fr auto', gap: 'var(--space-2)', alignItems: 'center' }}>
          <Input
            id="itemName"
            placeholder="Add grocery or supply item..."
            value={newItemName}
            onChange={(e) => setNewItemName(e.target.value)}
            required
          />
          <Input
            id="itemQty"
            type="number"
            step="0.1"
            placeholder="Qty"
            value={newItemQty}
            onChange={(e) => setNewItemQty(e.target.value)}
          />
          <Input
            id="itemUnit"
            placeholder="Unit (pcs, kg)"
            value={newItemUnit}
            onChange={(e) => setNewItemUnit(e.target.value)}
          />
          <select
            value={newItemPriority}
            onChange={(e) => setNewItemPriority(e.target.value as any)}
            style={{
              height: '42px',
              padding: '0 8px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-border-strong)',
              backgroundColor: 'var(--color-surface-card)',
              fontSize: '13px'
            }}
          >
            <option value="LOW">Low</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
            <option value="URGENT">Urgent</option>
          </select>
          <Button type="submit">
            <Plus size={16} />
            <span>Add</span>
          </Button>
        </form>
      </Card>

      {/* Active Items */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
        <h2 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          To Buy ({activeItems.length})
        </h2>

        {activeItems.length === 0 ? (
          <Card style={{ padding: 'var(--space-8)', textAlign: 'center' }}>
            <Sparkles size={28} color="var(--status-in-stock)" style={{ margin: '0 auto 8px' }} />
            <p style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-primary-900)' }}>All items purchased!</p>
            <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>Your shopping list is clear.</p>
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
                transition: 'all 0.15s ease'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <button
                  onClick={() => handleToggleCheck(item.id)}
                  style={{
                    width: '22px',
                    height: '22px',
                    borderRadius: '50%',
                    border: '2px solid var(--color-border-strong)',
                    backgroundColor: 'transparent',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'border-color 0.15s ease'
                  }}
                />
                <div>
                  <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-primary)' }}>{item.name}</div>
                  <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                    {item.quantity} {item.unit}
                    {item.assigned_to_name && ` • Assigned to ${item.assigned_to_name}`}
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Badge variant={item.priority === 'URGENT' || item.priority === 'HIGH' ? 'overdue' : 'neutral'}>
                  {item.priority}
                </Badge>
                <button
                  onClick={() => handleDeleteItem(item.id)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-tertiary)', padding: '4px' }}
                >
                  <Trash2 size={15} />
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
                opacity: 0.75
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <button
                  onClick={() => handleToggleCheck(item.id)}
                  style={{
                    width: '22px',
                    height: '22px',
                    borderRadius: '50%',
                    border: 'none',
                    backgroundColor: 'var(--status-in-stock)',
                    color: 'white',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  <CheckCircle2 size={16} />
                </button>
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 500, textDecoration: 'line-through', color: 'var(--color-text-secondary)' }}>
                    {item.name}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)' }}>
                    {item.quantity} {item.unit}
                  </div>
                </div>
              </div>

              <button
                onClick={() => handleDeleteItem(item.id)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-tertiary)', padding: '4px' }}
              >
                <Trash2 size={15} />
              </button>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
