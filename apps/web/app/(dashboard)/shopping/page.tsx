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
  Sparkles,
  RotateCcw,
  Edit2,
  Search,
  Check,
  X
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
  const [search, setSearch] = useState('');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Form State for Quick Add
  const [newItemName, setNewItemName] = useState('');
  const [newItemQty, setNewItemQty] = useState('1');
  const [newItemUnit, setNewItemUnit] = useState('pcs');
  const [newItemNotes, setNewItemNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Edit Modal State
  const [editingItem, setEditingItem] = useState<ShoppingItem | null>(null);
  const [editName, setEditName] = useState('');
  const [editQty, setEditQty] = useState('1');
  const [editUnit, setEditUnit] = useState('pcs');
  const [editNotes, setEditNotes] = useState('');
  const [isSavingEdit, setIsSavingEdit] = useState(false);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage((curr) => (curr === msg ? null : curr));
    }, 4000);
  };

  const loadData = async (showLoading = false) => {
    if (showLoading) setIsLoading(true);
    try {
      const initialHomeId = apiClient.getActiveHomeId();
      const [homeIdRes, initialDataRes] = await Promise.allSettled([
        apiClient.getValidActiveHome(),
        initialHomeId ? apiClient.get<ShoppingItem[]>(`/homes/${initialHomeId}/purchase-list?status_filter=ALL`) : Promise.resolve(null)
      ]);

      let finalHomeId = initialHomeId;
      if (homeIdRes.status === 'fulfilled' && homeIdRes.value) {
        finalHomeId = homeIdRes.value;
      }
      setActiveHomeId(finalHomeId);

      let res = initialDataRes.status === 'fulfilled' ? initialDataRes.value : null;
      if (finalHomeId && finalHomeId !== initialHomeId) {
        res = await apiClient.get<ShoppingItem[]>(`/homes/${finalHomeId}/purchase-list?status_filter=ALL`);
      }

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
    } catch (err) {
      console.error('Failed to load shopping list:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData(true);
  }, []);

  const filteredItems = items.filter(i => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return i.name.toLowerCase().includes(q) || (i.notes && i.notes.toLowerCase().includes(q));
  });

  const activeItems = filteredItems.filter(i => i.status === 'PENDING');
  const checkedItems = filteredItems.filter(i => i.status === 'PURCHASED');
  const totalCount = items.length;
  const completedCount = items.filter(i => i.status === 'PURCHASED').length;
  const progressPercent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  const handleMarkPurchased = async (item: ShoppingItem) => {
    if (!activeHomeId) return;

    // Optimistic UI update
    setItems(prev => prev.map(i => i.id === item.id ? { ...i, status: 'PURCHASED' } : i));

    try {
      await apiClient.post(`/homes/${activeHomeId}/purchase-list/${item.id}/purchase`, {
        restock_inventory: true
      });
      showToast(`Marked "${item.name}" as purchased.`);
      loadData(false);
    } catch (err: any) {
      console.error('Failed to purchase item:', err);
      alert(err?.message || 'Failed to update item status.');
      loadData(false);
    }
  };

  const handleRestoreItem = async (item: ShoppingItem) => {
    if (!activeHomeId) return;

    // Optimistic UI update
    setItems(prev => prev.map(i => i.id === item.id ? { ...i, status: 'PENDING' } : i));

    try {
      await apiClient.post(`/homes/${activeHomeId}/purchase-list/${item.id}/restore`, {});
      showToast(`Added "${item.name}" back to your shopping list.`);
      loadData(false);
    } catch (err: any) {
      console.error('Failed to restore purchase item:', err);
      alert(err?.message || 'Failed to restore item to shopping list.');
      loadData(false);
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
      showToast(`Added "${payload.name}" to shopping list.`);
      await loadData(false);
    } catch (err: any) {
      console.error('Failed to add purchase item:', err);
      alert(err?.message || 'Failed to add item to purchase list.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const openEditModal = (item: ShoppingItem) => {
    setEditingItem(item);
    setEditName(item.name);
    setEditQty(item.quantity.toString());
    setEditUnit(item.unit);
    setEditNotes(item.notes || '');
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingItem || !activeHomeId || !editName.trim()) return;

    setIsSavingEdit(true);
    try {
      await apiClient.patch(`/homes/${activeHomeId}/purchase-list/${editingItem.id}`, {
        name: editName.trim(),
        quantity: parseFloat(editQty) || 1,
        unit: editUnit.trim() || 'pcs',
        notes: editNotes.trim() || undefined,
        version: editingItem.version
      });

      setEditingItem(null);
      showToast(`Updated "${editName.trim()}".`);
      await loadData(false);
    } catch (err: any) {
      console.error('Failed to update item:', err);
      alert(err?.message || 'Failed to save item changes.');
    } finally {
      setIsSavingEdit(false);
    }
  };

  const handleDeleteItem = async (id: string, name: string) => {
    if (!activeHomeId) return;
    if (!confirm(`Remove "${name}" from the shopping list?`)) return;

    // Optimistic remove
    setItems(prev => prev.filter(i => i.id !== id));

    try {
      await apiClient.delete(`/homes/${activeHomeId}/purchase-list/${id}`);
      showToast(`Removed "${name}".`);
      loadData(false);
    } catch (err: any) {
      console.error('Failed to delete purchase item:', err);
      alert(err?.message || 'Failed to remove item.');
      loadData(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '900px', width: '100%' }}>
      {/* Toast Notification */}
      {toastMessage && (
        <div
          role="status"
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            backgroundColor: 'var(--color-primary-900)',
            color: '#ffffff',
            padding: '12px 20px',
            borderRadius: 'var(--radius-md)',
            boxShadow: '0 8px 24px rgba(0,0,0,0.18)',
            fontSize: '13px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            zIndex: 9999,
            animation: 'fadeIn 0.2s ease-out'
          }}
        >
          <Check size={16} color="var(--status-in-stock)" />
          <span>{toastMessage}</span>
          <button
            onClick={() => setToastMessage(null)}
            style={{ background: 'none', border: 'none', color: '#ffffff', cursor: 'pointer', marginLeft: '6px' }}
            aria-label="Close notification"
          >
            <X size={14} />
          </button>
        </div>
      )}

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

      {/* Quick Add Bar & Search */}
      <Card style={{ padding: 'var(--space-4)' }}>
        <form onSubmit={handleAddItem} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <div style={{ flex: '2 1 200px' }}>
              <Input
                id="itemName"
                placeholder="Add grocery or supply item... (e.g. Basmati Rice, Olive Oil)"
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
            <Button type="submit" disabled={isSubmitting} style={{ minHeight: '44px', padding: '0 18px' }}>
              <Plus size={16} />
              <span>{isSubmitting ? 'Adding...' : 'Add Item'}</span>
            </Button>
          </div>
        </form>

        {items.length > 3 && (
          <div style={{ marginTop: '12px', position: 'relative' }}>
            <Search size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-tertiary)' }} />
            <input
              type="text"
              placeholder="Search shopping list..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                width: '100%',
                height: '38px',
                padding: '0 12px 0 34px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border)',
                fontSize: '13px',
                backgroundColor: 'var(--color-surface-subtle)'
              }}
            />
          </div>
        )}
      </Card>

      {/* Active Items ("To Buy") */}
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
                  onClick={() => handleMarkPurchased(item)}
                  style={{
                    width: '32px',
                    height: '32px',
                    minWidth: '44px',
                    minHeight: '44px',
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
                  {item.notes && (
                    <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)', marginTop: '2px' }}>
                      {item.notes}
                    </div>
                  )}
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleMarkPurchased(item)}
                  style={{ minHeight: '44px', padding: '0 10px', fontSize: '12px' }}
                >
                  <Check size={14} style={{ marginRight: '4px' }} />
                  <span>Mark Purchased</span>
                </Button>
                <button
                  onClick={() => openEditModal(item)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-secondary)', padding: '10px', minWidth: '44px', minHeight: '44px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                  aria-label={`Edit ${item.name}`}
                  title="Edit Item"
                >
                  <Edit2 size={16} />
                </button>
                <button
                  onClick={() => handleDeleteItem(item.id, item.name)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-tertiary)', padding: '10px', minWidth: '44px', minHeight: '44px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                  aria-label={`Delete ${item.name}`}
                  title="Delete Item"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </Card>
          ))
        )}
      </div>

      {/* Purchased Items ("Purchased") */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', marginTop: 'var(--space-2)' }}>
        <h2 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          Purchased ({checkedItems.length})
        </h2>

        {checkedItems.length === 0 ? (
          <div style={{ padding: '16px', textAlign: 'center', color: 'var(--color-text-tertiary)', fontSize: '13px' }}>
            No purchased items yet.
          </div>
        ) : (
          checkedItems.map((item) => (
            <Card
              key={item.id}
              variant="subtle"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 16px',
                opacity: 0.9,
                gap: '12px',
                flexWrap: 'wrap'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: 0, flex: '1 1 200px' }}>
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
                {/* Restore to Shopping List Action */}
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => handleRestoreItem(item)}
                  style={{
                    minHeight: '44px',
                    padding: '0 14px',
                    fontSize: '12px',
                    fontWeight: 600,
                    color: 'var(--color-primary-900)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                  aria-label={`Restore ${item.name} to Shopping List`}
                >
                  <RotateCcw size={14} />
                  <span>Restore to Shopping List</span>
                </Button>

                <button
                  onClick={() => openEditModal(item)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-secondary)', padding: '10px', minWidth: '44px', minHeight: '44px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                  aria-label={`Edit ${item.name}`}
                  title="Edit Record"
                >
                  <Edit2 size={15} />
                </button>

                <button
                  onClick={() => handleDeleteItem(item.id, item.name)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-tertiary)', padding: '10px', minWidth: '44px', minHeight: '44px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                  aria-label={`Delete ${item.name}`}
                  title="Delete Purchase Record"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </Card>
          ))
        )}
      </div>

      {/* Edit Item Modal */}
      {editingItem && (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '16px'
          }}
        >
          <Card style={{ maxWidth: '480px', width: '100%', padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                Edit Shopping Item
              </h3>
              <button
                onClick={() => setEditingItem(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '6px' }}
                aria-label="Close modal"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSaveEdit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                  Item Name *
                </label>
                <Input
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                    Quantity
                  </label>
                  <Input
                    type="number"
                    step="0.1"
                    value={editQty}
                    onChange={(e) => setEditQty(e.target.value)}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                    Unit
                  </label>
                  <Input
                    value={editUnit}
                    onChange={(e) => setEditUnit(e.target.value)}
                  />
                </div>
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                  Notes / Brand preference
                </label>
                <Input
                  placeholder="e.g. Extra virgin, organic"
                  value={editNotes}
                  onChange={(e) => setEditNotes(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '8px' }}>
                <Button type="button" variant="secondary" onClick={() => setEditingItem(null)} style={{ minHeight: '44px' }}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isSavingEdit} style={{ minHeight: '44px' }}>
                  {isSavingEdit ? 'Saving...' : 'Save Changes'}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}
    </div>
  );
}
