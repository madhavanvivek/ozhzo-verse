'use client';

import React, { useEffect, useState, useRef } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import {
  Plus,
  MapPin,
  Trash2,
  FolderOpen,
  Box,
  UserCheck,
  RotateCcw,
  ArrowRight,
  FolderPlus,
  X,
  Sparkles,
  Edit2,
  ShoppingCart
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

interface Item {
  id: string;
  name: string;
  item_type: 'CONSUMABLE' | 'ASSET';
  category_name?: string;
  quantity: number;
  unit: string;
  min_threshold?: number;
  preferred_quantity?: number;
  location_id?: string;
  location_path?: string;
  condition?: string;
  asset_status: 'AVAILABLE' | 'BORROWED' | 'MISSING' | 'ARCHIVED';
  current_holder_name?: string;
  expiry_date?: string | null;
  status: 'GOOD' | 'LOW' | 'OUT_OF_STOCK';
  expiry_status: 'NORMAL' | 'EXPIRING_SOON' | 'EXPIRED';
  notes?: string;
}

interface LocationNode {
  id: string;
  name: string;
  location_type?: string;
  path?: string;
  item_count?: number;
  children?: LocationNode[];
}

export default function InventoryPage() {
  const [activeHomeId, setActiveHomeId] = useState<string | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [locationsTree, setLocationsTree] = useState<LocationNode[]>([]);
  const [flatLocations, setFlatLocations] = useState<{ id: string; name: string; path?: string }[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const [activeTab, setActiveTab] = useState<'ALL' | 'CONSUMABLES' | 'ASSETS' | 'LOCATIONS' | 'BORROWED'>('ALL');
  const [search, setSearch] = useState('');
  const [selectedLocation, setSelectedLocation] = useState<string | null>(null);

  // Modals state
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [isAddLocationOpen, setIsAddLocationOpen] = useState(false);
  const [isMoveOpen, setIsMoveOpen] = useState(false);
  const [isBorrowOpen, setIsBorrowOpen] = useState(false);
  const [isReturnOpen, setIsReturnOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState<Item | null>(null);

  // Form states for Add Item
  const [newItemName, setNewItemName] = useState('');
  const [newItemType, setNewItemType] = useState<'CONSUMABLE' | 'ASSET'>('CONSUMABLE');
  const [newItemQty, setNewItemQty] = useState('1');
  const [newItemUnit, setNewItemUnit] = useState('pcs');
  const [newItemThreshold, setNewItemThreshold] = useState('1');
  const [newItemLocationId, setNewItemLocationId] = useState<string>('');
  const [newItemCondition, setNewItemCondition] = useState('Good');
  const [isSubmittingItem, setIsSubmittingItem] = useState(false);

  // Form states for Add Location
  const [newLocationName, setNewLocationName] = useState('');
  const [newLocationType, setNewLocationType] = useState('ROOM');
  const [newCustomLocationType, setNewCustomLocationType] = useState('');
  const [newLocationParentId, setNewLocationParentId] = useState<string>('');
  const [newLocationDescription, setNewLocationDescription] = useState('');
  const [isSubmittingLocation, setIsSubmittingLocation] = useState(false);

  // Form states for Edit Location
  const [isEditLocationOpen, setIsEditLocationOpen] = useState(false);
  const [editingLocationNode, setEditingLocationNode] = useState<LocationNode | null>(null);
  const [editLocationName, setEditLocationName] = useState('');
  const [editLocationType, setEditLocationType] = useState('ROOM');
  const [editCustomLocationType, setEditCustomLocationType] = useState('');
  const [editLocationParentId, setEditLocationParentId] = useState<string>('');
  const [editLocationDescription, setEditLocationDescription] = useState('');
  const [isSubmittingEditLocation, setIsSubmittingEditLocation] = useState(false);

  // Relocation state
  const [targetLocationId, setTargetLocationId] = useState('');
  // Borrow state
  const [borrowerName, setBorrowerName] = useState('');
  const [borrowerContact, setBorrowerContact] = useState('');

  // Location Types State
  const [locationTypes, setLocationTypes] = useState<Array<{ name: string; code: string; is_system_default?: boolean }>>([]);

  // Quick Usage State
  const [isQuickUseOpen, setIsQuickUseOpen] = useState(false);
  const [quickUseItem, setQuickUseItem] = useState<Item | null>(null);
  const [quickUseAmount, setQuickUseAmount] = useState('1');
  const [quickUseNotes, setQuickUseNotes] = useState('');
  const [isSubmittingUse, setIsSubmittingUse] = useState(false);

  // Quick Restock State
  const [isQuickRestockOpen, setIsQuickRestockOpen] = useState(false);
  const [quickRestockItem, setQuickRestockItem] = useState<Item | null>(null);
  const [quickRestockAmount, setQuickRestockAmount] = useState('1');
  const [quickRestockNotes, setQuickRestockNotes] = useState('');
  const [isSubmittingRestock, setIsSubmittingRestock] = useState(false);

  const nameInputRef = useRef<HTMLInputElement>(null);
  const locInputRef = useRef<HTMLInputElement>(null);

  const loadData = async (showLoadingState = false) => {
    if (showLoadingState) setIsLoading(true);
    try {
      const homeId = await apiClient.getValidActiveHome();
      setActiveHomeId(homeId);

      if (homeId) {
        const [itemsRes, flatLocsRes, locTypesRes] = await Promise.allSettled([
          apiClient.get<any>(`/homes/${homeId}/inventory/items`),
          apiClient.get<any>(`/homes/${homeId}/locations`),
          apiClient.get<any>(`/homes/${homeId}/location-types`)
        ]);

        if (locTypesRes.status === 'fulfilled' && Array.isArray(locTypesRes.value)) {
          setLocationTypes(locTypesRes.value);
        }

        if (itemsRes.status === 'fulfilled' && itemsRes.value) {
          const rawItems = itemsRes.value.items || itemsRes.value;
          if (Array.isArray(rawItems)) {
            setItems(rawItems.map((i: any) => ({
              id: i.id,
              name: i.name,
              item_type: i.item_type || 'CONSUMABLE',
              category_name: i.category_name || 'General',
              quantity: parseFloat(i.quantity) || 0,
              unit: i.unit || 'pcs',
              min_threshold: i.min_threshold ? parseFloat(i.min_threshold) : undefined,
              preferred_quantity: i.preferred_quantity ? parseFloat(i.preferred_quantity) : undefined,
              location_id: i.location_id,
              location_path: i.location_path || 'Unassigned',
              condition: i.condition || 'Good',
              asset_status: i.asset_status || 'AVAILABLE',
              current_holder_name: i.current_holder_name,
              expiry_date: i.expiry_date,
              status: i.status || 'GOOD',
              expiry_status: i.expiry_status || 'NORMAL',
              notes: i.notes
            })));
          }
        }

        if (flatLocsRes.status === 'fulfilled' && flatLocsRes.value) {
          const locs = Array.isArray(flatLocsRes.value) ? flatLocsRes.value : [];
          setFlatLocations(locs.map((l: any) => ({
            id: l.id,
            name: l.name,
            path: l.path || l.name
          })));

          const map = new Map<string, LocationNode>();
          const roots: LocationNode[] = [];
          locs.forEach((l: any) => {
            map.set(l.id, {
              id: l.id,
              name: l.name,
              location_type: l.location_type,
              path: l.path || l.name,
              item_count: l.item_count || 0,
              children: []
            });
          });
          locs.forEach((l: any) => {
            const node = map.get(l.id)!;
            if (l.parent_id && map.has(l.parent_id)) {
              map.get(l.parent_id)!.children!.push(node);
            } else {
              roots.push(node);
            }
          });
          setLocationsTree(roots);

          if (locs.length > 0) {
            setNewItemLocationId(locs[0].id);
            setTargetLocationId(locs[0].id);
          }
        }
      }
    } catch (err) {
      console.error('Failed to load inventory & locations:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData(true);
    const handleHomeChanged = () => {
      loadData(false);
    };
    window.addEventListener('home-changed', handleHomeChanged);
    return () => window.removeEventListener('home-changed', handleHomeChanged);
  }, []);

  const openAddItemModal = () => {
    setIsAddOpen(true);
    setTimeout(() => {
      nameInputRef.current?.focus();
    }, 100);
  };

  const openAddLocationModal = (parentId?: string) => {
    setNewLocationParentId(parentId || '');
    setNewLocationName('');
    setNewLocationType('ROOM');
    setNewCustomLocationType('');
    setNewLocationDescription('');
    setIsAddLocationOpen(true);
    setTimeout(() => {
      locInputRef.current?.focus();
    }, 100);
  };

  const openEditLocationModal = (node: LocationNode) => {
    setEditingLocationNode(node);
    setEditLocationName(node.name);
    const standardTypes = ['ROOM', 'FURNITURE', 'SHELF', 'CONTAINER'];
    if (node.location_type && !standardTypes.includes(node.location_type)) {
      setEditLocationType('CUSTOM');
      setEditCustomLocationType(node.location_type);
    } else {
      setEditLocationType(node.location_type || 'ROOM');
      setEditCustomLocationType('');
    }
    setEditLocationParentId((node as any).parent_id || '');
    setEditLocationDescription((node as any).description || '');
    setIsEditLocationOpen(true);
  };

  const handleAddItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newItemName.trim() || !activeHomeId) return;

    setIsSubmittingItem(true);
    try {
      const qty = parseFloat(newItemQty) || 1;
      const thresh = parseFloat(newItemThreshold) || 1;

      const payload = {
        name: newItemName.trim(),
        item_type: newItemType,
        quantity: qty,
        unit: newItemUnit || 'pcs',
        min_threshold: newItemType === 'CONSUMABLE' ? thresh : undefined,
        location_id: newItemLocationId || undefined,
        condition: newItemType === 'ASSET' ? newItemCondition : undefined
      };

      await apiClient.post(`/homes/${activeHomeId}/inventory/items`, payload);
      setNewItemName('');
      setIsAddOpen(false);
      await loadData();
    } catch (err: any) {
      console.error('Failed to add item:', err);
      alert(err?.message || 'Failed to save item to Home Inventory.');
    } finally {
      setIsSubmittingItem(false);
    }
  };

  const handleAddLocation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newLocationName.trim() || !activeHomeId) return;

    setIsSubmittingLocation(true);
    try {
      let finalType = newLocationType;
      if (newLocationType === 'CUSTOM' && newCustomLocationType.trim()) {
        try {
          await apiClient.post(`/homes/${activeHomeId}/location-types`, {
            name: newCustomLocationType.trim()
          });
        } catch {
          // Ignore duplicate code error
        }
        finalType = newCustomLocationType.trim();
      }

      const payload = {
        name: newLocationName.trim(),
        location_type: finalType,
        parent_id: newLocationParentId || undefined,
        description: newLocationDescription.trim() || undefined
      };

      const created: any = await apiClient.post(`/homes/${activeHomeId}/locations`, payload);
      if (created && created.id) {
        setNewItemLocationId(created.id);
      }
      setNewLocationName('');
      setNewLocationDescription('');
      setNewCustomLocationType('');
      setIsAddLocationOpen(false);
      await loadData();
    } catch (err: any) {
      console.error('Failed to create location:', err);
      alert(err?.message || 'Failed to create location.');
    } finally {
      setIsSubmittingLocation(false);
    }
  };

  const handleExecuteQuickUse = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickUseItem || !activeHomeId) return;
    const qty = parseFloat(quickUseAmount) || 0;
    if (qty <= 0) {
      alert('Please enter a valid positive quantity.');
      return;
    }
    setIsSubmittingUse(true);
    try {
      await apiClient.post(`/homes/${activeHomeId}/inventory/items/${quickUseItem.id}/consume`, {
        quantity: qty,
        notes: quickUseNotes.trim() || undefined
      });
      setIsQuickUseOpen(false);
      setQuickUseItem(null);
      setQuickUseNotes('');
      await loadData();
    } catch (err: any) {
      alert(err?.message || 'Failed to record stock usage.');
    } finally {
      setIsSubmittingUse(false);
    }
  };

  const handleExecuteQuickRestock = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickRestockItem || !activeHomeId) return;
    const qty = parseFloat(quickRestockAmount) || 0;
    if (qty <= 0) {
      alert('Please enter a valid positive quantity.');
      return;
    }
    setIsSubmittingRestock(true);
    try {
      await apiClient.post(`/homes/${activeHomeId}/inventory/items/${quickRestockItem.id}/restock`, {
        quantity: qty,
        notes: quickRestockNotes.trim() || undefined
      });
      setIsQuickRestockOpen(false);
      setQuickRestockItem(null);
      setQuickRestockNotes('');
      await loadData();
    } catch (err: any) {
      alert(err?.message || 'Failed to restock item.');
    } finally {
      setIsSubmittingRestock(false);
    }
  };

  const handleAddToShopping = async (item: Item) => {
    if (!activeHomeId) return;
    try {
      const res: any = await apiClient.post(`/homes/${activeHomeId}/inventory/items/${item.id}/add-to-shopping`);
      alert(res?.message || `Added "${item.name}" to the shopping list.`);
    } catch (err: any) {
      alert(err?.message || 'Failed to add item to shopping list.');
    }
  };

  const handleEditLocation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingLocationNode || !editLocationName.trim() || !activeHomeId) return;

    setIsSubmittingEditLocation(true);
    try {
      const finalType = editLocationType === 'CUSTOM'
        ? (editCustomLocationType.trim() || 'CUSTOM')
        : editLocationType;

      const payload = {
        name: editLocationName.trim(),
        location_type: finalType,
        parent_id: editLocationParentId || undefined,
        description: editLocationDescription.trim() || undefined
      };

      await apiClient.patch(`/homes/${activeHomeId}/locations/${editingLocationNode.id}`, payload);
      setIsEditLocationOpen(false);
      setEditingLocationNode(null);
      await loadData();
    } catch (err: any) {
      console.error('Failed to update location:', err);
      alert(err?.message || 'Failed to update location.');
    } finally {
      setIsSubmittingEditLocation(false);
    }
  };

  const handleDeleteLocation = async (node: LocationNode) => {
    if (!activeHomeId) return;

    if (node.children && node.children.length > 0) {
      alert(`Cannot delete "${node.name}" because it contains ${node.children.length} sub-location(s). Please remove or relocate child locations first.`);
      return;
    }

    const itemsInLoc = items.filter(i => i.location_id === node.id || i.location_path?.includes(node.name));
    if (itemsInLoc.length > 0) {
      alert(`Cannot delete "${node.name}" because it contains ${itemsInLoc.length} inventory item(s). Please move or reassign items first.`);
      return;
    }

    if (!confirm(`Are you sure you want to delete the location "${node.name}"?`)) return;

    try {
      await apiClient.delete(`/homes/${activeHomeId}/locations/${node.id}`);
      if (selectedLocation === node.name) {
        setSelectedLocation(null);
      }
      await loadData();
    } catch (err: any) {
      console.error('Failed to delete location:', err);
      alert(err?.message || 'Failed to delete location.');
    }
  };

  const handleMoveItem = async () => {
    if (!selectedItem || !targetLocationId || !activeHomeId) return;
    try {
      await apiClient.post(`/homes/${activeHomeId}/inventory/items/${selectedItem.id}/move`, {
        to_location_id: targetLocationId
      });
      setIsMoveOpen(false);
      setSelectedItem(null);
      await loadData();
    } catch (err: any) {
      console.error('Failed to move item:', err);
      alert(err?.message || 'Failed to move item.');
    }
  };

  const handleBorrowItem = async () => {
    if (!selectedItem || !borrowerName.trim() || !activeHomeId) return;
    try {
      await apiClient.post(`/homes/${activeHomeId}/inventory/items/${selectedItem.id}/borrow`, {
        borrower_name: borrowerName.trim(),
        borrower_contact: borrowerContact.trim() || undefined
      });
      setBorrowerName('');
      setBorrowerContact('');
      setIsBorrowOpen(false);
      setSelectedItem(null);
      await loadData();
    } catch (err: any) {
      console.error('Failed to record borrowed asset:', err);
      alert(err?.message || 'Failed to record loan.');
    }
  };

  const handleReturnItem = async () => {
    if (!selectedItem || !activeHomeId) return;
    try {
      await apiClient.post(`/homes/${activeHomeId}/inventory/items/${selectedItem.id}/return`, {});
      setIsReturnOpen(false);
      setSelectedItem(null);
      await loadData();
    } catch (err: any) {
      console.error('Failed to return item:', err);
      alert(err?.message || 'Failed to record return.');
    }
  };

  const handleAdjustStock = async (item: Item, delta: number) => {
    if (!activeHomeId) return;
    try {
      const movement_type = delta > 0 ? 'PURCHASE' : 'CONSUME';
      await apiClient.post(`/homes/${activeHomeId}/inventory/items/${item.id}/movements`, {
        quantity: Math.abs(delta),
        movement_type
      });
      await loadData();
    } catch (err: any) {
      console.error('Failed to adjust stock:', err);
    }
  };

  const handleDeleteItem = async (id: string) => {
    if (!activeHomeId) return;
    if (!confirm('Are you sure you want to delete this item from Home Memory?')) return;

    try {
      await apiClient.delete(`/homes/${activeHomeId}/inventory/items/${id}`);
      await loadData();
    } catch (err: any) {
      console.error('Failed to delete item:', err);
      alert(err?.message || 'Failed to delete item.');
    }
  };

  const filteredItems = items.filter((item) => {
    const matchesSearch =
      item.name.toLowerCase().includes(search.toLowerCase()) ||
      (item.location_path && item.location_path.toLowerCase().includes(search.toLowerCase())) ||
      (item.current_holder_name && item.current_holder_name.toLowerCase().includes(search.toLowerCase()));

    const matchesLocation =
      !selectedLocation || (item.location_path && item.location_path.includes(selectedLocation));

    if (activeTab === 'CONSUMABLES') return matchesSearch && matchesLocation && item.item_type === 'CONSUMABLE';
    if (activeTab === 'ASSETS') return matchesSearch && matchesLocation && item.item_type === 'ASSET';
    if (activeTab === 'BORROWED') return matchesSearch && matchesLocation && item.asset_status === 'BORROWED';
    return matchesSearch && matchesLocation;
  });

  const lowStockCount = items.filter((i) => i.item_type === 'CONSUMABLE' && i.status === 'LOW').length;
  const outOfStockCount = items.filter((i) => i.item_type === 'CONSUMABLE' && i.status === 'OUT_OF_STOCK').length;
  const borrowedCount = items.filter((i) => i.asset_status === 'BORROWED').length;
  const totalAssets = items.filter((i) => i.item_type === 'ASSET').length;

  const renderLocationTreeNodes = (nodes: LocationNode[], depth: number = 0) => {
    return nodes.map((node) => {
      const isSelected = selectedLocation === node.name;
      const formatTypeLabel = (t?: string) => {
        if (!t) return 'Room';
        if (t === 'ROOM') return 'Room';
        if (t === 'FURNITURE') return 'Cabinet';
        if (t === 'SHELF') return 'Shelf';
        if (t === 'CONTAINER') return 'Box';
        return t;
      };

      return (
        <div key={node.id} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '6px 8px',
              paddingLeft: `${Math.max(8, depth * 16 + 8)}px`,
              borderRadius: 'var(--radius-md)',
              backgroundColor: isSelected ? 'var(--color-primary-100)' : 'transparent',
              cursor: 'pointer',
              fontSize: '13px',
              fontWeight: depth === 0 ? 700 : 500,
              color: isSelected ? 'var(--color-primary-900)' : 'var(--color-text-primary)',
              transition: 'background-color 0.15s ease',
              gap: '6px',
              flexWrap: 'nowrap'
            }}
            onClick={() => setSelectedLocation(isSelected ? null : node.name)}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', minWidth: 0, flex: 1 }}>
              {depth === 0 ? <FolderOpen size={16} color="var(--color-primary-700)" /> : <Box size={14} color="var(--color-text-secondary)" />}
              <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{node.name}</span>
              <span style={{ fontSize: '10px', color: 'var(--color-text-tertiary)', padding: '1px 5px', borderRadius: '4px', backgroundColor: 'var(--color-surface-subtle)', flexShrink: 0 }}>
                {formatTypeLabel(node.location_type)}
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '2px', flexShrink: 0 }}>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  openAddLocationModal(node.id);
                }}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '6px',
                  minWidth: '44px',
                  minHeight: '44px',
                  borderRadius: '4px',
                  color: 'var(--color-text-secondary)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
                title={`Add sub-location inside ${node.name}`}
                aria-label={`Add sub-location inside ${node.name}`}
              >
                <Plus size={15} />
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  openEditLocationModal(node);
                }}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '6px',
                  minWidth: '44px',
                  minHeight: '44px',
                  borderRadius: '4px',
                  color: 'var(--color-text-secondary)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
                title={`Edit ${node.name}`}
                aria-label={`Edit ${node.name}`}
              >
                <Edit2 size={14} />
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteLocation(node);
                }}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '6px',
                  minWidth: '44px',
                  minHeight: '44px',
                  borderRadius: '4px',
                  color: 'var(--status-overdue)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
                title={`Delete ${node.name}`}
                aria-label={`Delete ${node.name}`}
              >
                <Trash2 size={14} />
              </button>
            </div>
          </div>
          {node.children && node.children.length > 0 && renderLocationTreeNodes(node.children, depth + 1)}
        </div>
      );
    });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '1100px', width: '100%' }}>
      {/* Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-primary-900)', lineHeight: 1.2 }}>
            Household Inventory & Home Memory
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
            Know what we have, where it is kept, and who borrowed it.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <Button
            id="addLocationBtn"
            variant="secondary"
            onClick={() => openAddLocationModal()}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <FolderPlus size={16} />
            <span>+ New Location</span>
          </Button>

          <Button
            id="addInventoryItemBtn"
            variant="primary"
            onClick={openAddItemModal}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Plus size={16} />
            <span>+ Add Item</span>
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--space-3)' }}>
        <Card style={{ padding: 'var(--space-4)' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-tertiary)' }}>TOTAL ITEMS</span>
          <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--color-primary-900)', marginTop: '4px' }}>
            {items.length}
          </div>
          <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>{totalAssets} durable assets</span>
        </Card>

        <Card style={{ padding: 'var(--space-4)', borderLeft: '4px solid var(--status-low-stock)' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--status-low-stock)' }}>LOW STOCK</span>
          <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--status-low-stock)', marginTop: '4px' }}>
            {lowStockCount}
          </div>
          <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>Replenish soon</span>
        </Card>

        <Card style={{ padding: 'var(--space-4)', borderLeft: '4px solid var(--status-overdue)' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--status-overdue)' }}>OUT OF STOCK</span>
          <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--status-overdue)', marginTop: '4px' }}>
            {outOfStockCount}
          </div>
          <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>Add to shopping list</span>
        </Card>

        <Card style={{ padding: 'var(--space-4)', borderLeft: '4px solid #3B82F6' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: '#1D4ED8' }}>BORROWED ASSETS</span>
          <div style={{ fontSize: '24px', fontWeight: 800, color: '#1D4ED8', marginTop: '4px' }}>
            {borrowedCount}
          </div>
          <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>Currently on loan</span>
        </Card>
      </div>

      {/* Navigation Tabs */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: '8px', overflowX: 'auto' }}>
        <Button
          variant={activeTab === 'ALL' ? 'primary' : 'ghost'}
          size="sm"
          onClick={() => { setActiveTab('ALL'); setSelectedLocation(null); }}
        >
          All Items ({items.length})
        </Button>
        <Button
          variant={activeTab === 'CONSUMABLES' ? 'primary' : 'ghost'}
          size="sm"
          onClick={() => { setActiveTab('CONSUMABLES'); setSelectedLocation(null); }}
        >
          Pantry Consumables ({items.filter(i => i.item_type === 'CONSUMABLE').length})
        </Button>
        <Button
          variant={activeTab === 'ASSETS' ? 'primary' : 'ghost'}
          size="sm"
          onClick={() => { setActiveTab('ASSETS'); setSelectedLocation(null); }}
        >
          Household Assets ({totalAssets})
        </Button>
        <Button
          variant={activeTab === 'BORROWED' ? 'primary' : 'ghost'}
          size="sm"
          onClick={() => { setActiveTab('BORROWED'); setSelectedLocation(null); }}
        >
          Borrowed Assets ({borrowedCount})
        </Button>
        <Button
          variant={activeTab === 'LOCATIONS' ? 'primary' : 'ghost'}
          size="sm"
          onClick={() => setActiveTab('LOCATIONS')}
        >
          Location Explorer
        </Button>
      </div>

      {/* Location Explorer View */}
      {activeTab === 'LOCATIONS' ? (
        <div
          className="ozhzo-location-explorer-grid"
          style={{
            display: 'grid',
            gridTemplateColumns: 'minmax(280px, 1fr) 2fr',
            gap: 'var(--space-4)',
            alignItems: 'start'
          }}
        >
          <Card style={{ padding: 'var(--space-4)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                Household Hierarchy
              </h3>
              <Button size="sm" variant="secondary" onClick={() => openAddLocationModal()}>
                <Plus size={14} />
                <span>Add Root</span>
              </Button>
            </div>

            {locationsTree.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '20px', color: 'var(--color-text-secondary)', fontSize: '13px' }}>
                <p>No locations created yet.</p>
                <Button size="sm" style={{ marginTop: '8px' }} onClick={() => openAddLocationModal()}>
                  + Create First Room
                </Button>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {renderLocationTreeNodes(locationsTree)}
              </div>
            )}
          </Card>

          <Card style={{ padding: 'var(--space-4)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                Items inside: {selectedLocation || 'All Locations'} ({filteredItems.length})
              </h3>
              {selectedLocation && (
                <Button size="sm" variant="ghost" onClick={() => setSelectedLocation(null)}>
                  Clear Filter
                </Button>
              )}
            </div>

            {filteredItems.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '30px', color: 'var(--color-text-secondary)', fontSize: '13px' }}>
                <p>No items found in this location.</p>
                <Button size="sm" style={{ marginTop: '8px' }} onClick={openAddItemModal}>
                  + Add Item Here
                </Button>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {filteredItems.map((item) => (
                  <div
                    key={item.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '10px 14px',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--color-border-subtle)',
                      backgroundColor: 'var(--color-surface-subtle)'
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '14px', color: 'var(--color-text-primary)' }}>{item.name}</div>
                      <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
                        {item.location_path} • {item.quantity} {item.unit}
                      </div>
                    </div>
                    <Badge variant={item.asset_status === 'BORROWED' ? 'low-stock' : item.status === 'LOW' ? 'low-stock' : item.status === 'OUT_OF_STOCK' ? 'overdue' : 'in-stock'}>
                      {item.asset_status === 'BORROWED' ? `With ${item.current_holder_name}` : item.status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      ) : (
        <>
          {/* Universal Search */}
          <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center' }}>
            <div style={{ flex: 1, position: 'relative' }}>
              <Input
                id="search"
                placeholder="Search by name, location (e.g. 'Blue Box'), or borrower ('Ashraf')..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>

          {/* Items Grid */}
          {isLoading ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 'var(--space-4)' }}>
              {[1, 2, 3, 4].map((n) => (
                <div key={n} style={{ height: '160px', backgroundColor: 'var(--color-surface-subtle)', borderRadius: 'var(--radius-md)', animation: 'pulse 1.5s infinite' }} />
              ))}
            </div>
          ) : filteredItems.length === 0 ? (
            <Card style={{ padding: 'var(--space-8)', textAlign: 'center' }}>
              <Sparkles size={32} color="var(--color-primary-700)" style={{ margin: '0 auto 8px' }} />
              <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                No items found
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
                Try another filter or click &ldquo;+ Add Item&rdquo; to record your first household item.
              </p>
              <Button style={{ marginTop: '16px' }} onClick={openAddItemModal}>
                + Add Item / Asset
              </Button>
            </Card>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 'var(--space-4)' }}>
              {filteredItems.map((item) => (
                <Card key={item.id} style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: 'var(--space-3)' }}>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                      <div>
                        <span style={{ fontSize: '11px', fontWeight: 700, color: item.item_type === 'ASSET' ? 'var(--color-primary-700)' : 'var(--color-text-tertiary)', textTransform: 'uppercase' }}>
                          {item.item_type} • {item.category_name || 'General'}
                        </span>
                        <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-primary-900)', marginTop: '2px' }}>
                          {item.name}
                        </h3>
                      </div>
                      {item.item_type === 'CONSUMABLE' ? (
                        <Badge variant={item.status === 'GOOD' ? 'in-stock' : item.status === 'LOW' ? 'low-stock' : 'overdue'}>
                          {item.status}
                        </Badge>
                      ) : (
                        <Badge variant={item.asset_status === 'AVAILABLE' ? 'in-stock' : 'low-stock'}>
                          {item.asset_status === 'BORROWED' ? `Borrowed (${item.current_holder_name})` : 'Available'}
                        </Badge>
                      )}
                    </div>

                    {item.item_type === 'CONSUMABLE' ? (
                      <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--color-primary-900)', margin: '8px 0' }}>
                        {item.quantity} <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--color-text-secondary)' }}>{item.unit}</span>
                      </div>
                    ) : (
                      <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)', margin: '8px 0' }}>
                        Condition: <strong>{item.condition || 'Good'}</strong>
                      </div>
                    )}

                    {item.location_path && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: 'var(--color-primary-800)', backgroundColor: 'var(--color-surface-subtle)', padding: '4px 8px', borderRadius: '4px', marginTop: '6px' }}>
                        <MapPin size={13} />
                        <span style={{ fontWeight: 600 }}>{item.location_path}</span>
                      </div>
                    )}
                  </div>

                  {/* Card Action Controls */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 'var(--space-2)', borderTop: '1px solid var(--color-border-subtle)', gap: '6px' }}>
                    {item.item_type === 'ASSET' ? (
                      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => { setSelectedItem(item); setIsMoveOpen(true); }}
                        >
                          <ArrowRight size={13} />
                          <span>Move</span>
                        </Button>

                        {item.asset_status === 'AVAILABLE' ? (
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => { setSelectedItem(item); setIsBorrowOpen(true); }}
                          >
                            <UserCheck size={13} />
                            <span>Borrow</span>
                          </Button>
                        ) : (
                          <Button
                            size="sm"
                            variant="primary"
                            onClick={() => { setSelectedItem(item); setIsReturnOpen(true); }}
                          >
                            <RotateCcw size={13} />
                            <span>Return</span>
                          </Button>
                        )}
                      </div>
                    ) : (
                      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', alignItems: 'center' }}>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => handleAdjustStock(item, -1)}
                          aria-label={`Reduce ${item.name} quantity by 1`}
                        >
                          -1
                        </Button>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => handleAdjustStock(item, 1)}
                          aria-label={`Increase ${item.name} quantity by 1`}
                        >
                          +1
                        </Button>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => {
                            setQuickUseItem(item);
                            setQuickUseAmount('1');
                            setQuickUseNotes('');
                            setIsQuickUseOpen(true);
                          }}
                          aria-label={`Use ${item.name}`}
                        >
                          Use
                        </Button>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => {
                            setQuickRestockItem(item);
                            setQuickRestockAmount('1');
                            setQuickRestockNotes('');
                            setIsQuickRestockOpen(true);
                          }}
                          aria-label={`Restock ${item.name}`}
                        >
                          + Restock
                        </Button>
                        {(item.quantity <= (item.min_threshold || 1) || item.status === 'LOW' || item.status === 'OUT_OF_STOCK') && (
                          <Button
                            size="sm"
                            variant="primary"
                            onClick={() => handleAddToShopping(item)}
                            style={{ fontSize: '11px', padding: '0 8px' }}
                            title="Add to Shopping List"
                          >
                            <ShoppingCart size={13} style={{ marginRight: '4px' }} />
                            <span>Buy</span>
                          </Button>
                        )}
                      </div>
                    )}

                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDeleteItem(item.id)}
                      style={{ color: 'var(--status-overdue)' }}
                      aria-label={`Delete ${item.name}`}
                    >
                      <Trash2 size={15} />
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </>
      )}

      {/* Add Item Modal */}
      {isAddOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px'
          }}
          onClick={() => setIsAddOpen(false)}
        >
          <Card
            style={{
              width: '100%',
              maxWidth: '560px',
              border: '2px solid var(--color-primary-900)',
              maxHeight: '90vh',
              overflowY: 'auto'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                  Add Item to Home Inventory
                </h3>
                <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                  Record durable tools, appliances, or consumables in Home Memory
                </p>
              </div>
              <button
                onClick={() => setIsAddOpen(false)}
                className="touch-target"
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}
                aria-label="Close add item dialog"
              >
                <X size={20} color="var(--color-text-secondary)" />
              </button>
            </div>

            {/* Quick Catalog Chips */}
            <div style={{ marginBottom: 'var(--space-4)' }}>
              <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '8px' }}>
                POPULAR HOUSEHOLD ITEMS (Click to Pre-fill):
              </label>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {[
                  { name: 'Basmati Rice', unit: 'kg', type: 'CONSUMABLE' as const },
                  { name: 'Olive Oil', unit: 'L', type: 'CONSUMABLE' as const },
                  { name: 'AA Batteries', unit: 'pack', type: 'CONSUMABLE' as const },
                  { name: 'Cordless Drill', unit: 'pcs', type: 'ASSET' as const },
                  { name: 'Toolkit', unit: 'pcs', type: 'ASSET' as const },
                  { name: 'Spare House Keys', unit: 'pcs', type: 'ASSET' as const },
                ].map((tpl) => (
                  <button
                    key={tpl.name}
                    type="button"
                    onClick={() => {
                      setNewItemName(tpl.name);
                      setNewItemUnit(tpl.unit);
                      setNewItemType(tpl.type);
                    }}
                    style={{
                      padding: '4px 10px',
                      borderRadius: 'var(--radius-full)',
                      background: newItemName === tpl.name ? 'var(--color-primary-900)' : 'var(--color-surface-subtle)',
                      color: newItemName === tpl.name ? '#ffffff' : 'var(--color-text-primary)',
                      border: '1px solid var(--color-border-subtle)',
                      fontSize: '12px',
                      fontWeight: 500,
                      cursor: 'pointer'
                    }}
                  >
                    + {tpl.name}
                  </button>
                ))}
              </div>
            </div>

            <form onSubmit={handleAddItem} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              <Input
                id="itemName"
                ref={nameInputRef}
                autoFocus
                label="Item Name *"
                placeholder="e.g. Cordless Power Drill, Basmati Rice"
                value={newItemName}
                onChange={(e) => setNewItemName(e.target.value)}
                required
              />

              <div
                className="ozhzo-responsive-form-grid"
                style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label htmlFor="itemType" style={{ fontSize: '13px', fontWeight: 600 }}>Item Type</label>
                  <select
                    id="itemType"
                    value={newItemType}
                    onChange={(e) => setNewItemType(e.target.value as any)}
                    style={{ height: '40px', padding: '0 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)' }}
                  >
                    <option value="CONSUMABLE">Consumable (Pantry/Supplies)</option>
                    <option value="ASSET">Household Asset (Tool/Durable)</option>
                  </select>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <label style={{ fontSize: '13px', fontWeight: 600 }}>Location</label>
                    <button
                      type="button"
                      onClick={() => openAddLocationModal()}
                      style={{
                        fontSize: '12px',
                        color: 'var(--color-primary-700, #334155)',
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        fontWeight: 600,
                        padding: 0
                      }}
                    >
                      + Add New Location
                    </button>
                  </div>
                  <select
                    value={newItemLocationId}
                    onChange={(e) => setNewItemLocationId(e.target.value)}
                    style={{ height: '40px', padding: '0 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)' }}
                  >
                    <option value="">-- No specific location --</option>
                    {flatLocations.map((loc) => (
                      <option key={loc.id} value={loc.id}>
                        {loc.path || loc.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div
                className="ozhzo-responsive-form-grid"
                style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 'var(--space-3)' }}
              >
                <Input
                  id="itemQty"
                  label="Initial Quantity"
                  type="number"
                  step="0.1"
                  value={newItemQty}
                  onChange={(e) => setNewItemQty(e.target.value)}
                />
                <Input
                  id="itemUnit"
                  label="Unit (e.g. kg, pcs)"
                  value={newItemUnit}
                  onChange={(e) => setNewItemUnit(e.target.value)}
                />
                {newItemType === 'CONSUMABLE' ? (
                  <Input
                    id="itemThreshold"
                    label="Min Alert Threshold"
                    type="number"
                    step="0.1"
                    value={newItemThreshold}
                    onChange={(e) => setNewItemThreshold(e.target.value)}
                  />
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '13px', fontWeight: 600 }}>Condition</label>
                    <select
                      value={newItemCondition}
                      onChange={(e) => setNewItemCondition(e.target.value)}
                      style={{ height: '40px', padding: '0 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)' }}
                    >
                      <option value="Excellent">Excellent</option>
                      <option value="Good">Good</option>
                      <option value="Fair">Fair</option>
                      <option value="Needs Repair">Needs Repair</option>
                    </select>
                  </div>
                )}
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: 'var(--space-3)' }}>
                <Button type="button" variant="ghost" onClick={() => setIsAddOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isSubmittingItem}>
                  {isSubmittingItem ? 'Saving...' : 'Save to Home Inventory'}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* Add Location Modal */}
      {isAddLocationOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px'
          }}
          onClick={() => setIsAddLocationOpen(false)}
        >
          <Card
            style={{
              width: '100%',
              maxWidth: '480px',
              border: '2px solid var(--color-primary-900)',
              maxHeight: '90vh',
              overflowY: 'auto'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                  Add Location to Home
                </h3>
                <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                  Organize storage rooms, cupboards, shelves, and containers
                </p>
              </div>
              <button
                onClick={() => setIsAddLocationOpen(false)}
                className="touch-target"
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}
                aria-label="Close location dialog"
              >
                <X size={20} color="var(--color-text-secondary)" />
              </button>
            </div>

            <form onSubmit={handleAddLocation} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              <Input
                id="locationName"
                ref={locInputRef}
                autoFocus
                label="Location Name *"
                placeholder="e.g. Master Bedroom, Tool Rack, Top Shelf"
                value={newLocationName}
                onChange={(e) => setNewLocationName(e.target.value)}
                required
              />

              <div
                className="ozhzo-responsive-form-grid"
                style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label htmlFor="locationType" style={{ fontSize: '13px', fontWeight: 600 }}>Location Type</label>
                  <select
                    id="locationType"
                    value={newLocationType}
                    onChange={(e) => setNewLocationType(e.target.value)}
                    style={{ height: '40px', padding: '0 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)' }}
                  >
                    {locationTypes.length > 0 ? (
                      locationTypes.map((lt) => (
                        <option key={lt.code} value={lt.code}>
                          {lt.name}
                        </option>
                      ))
                    ) : (
                      <>
                        <option value="ROOM">Room / Area</option>
                        <option value="CUPBOARD">Cupboard / Cabinet</option>
                        <option value="FURNITURE">Furniture</option>
                        <option value="SHELF">Shelf / Rack</option>
                        <option value="CONTAINER">Box / Container / Bin</option>
                        <option value="PANTRY">Kitchen Pantry</option>
                        <option value="ZONE">Storage Zone</option>
                        <option value="FREEZER">Freezer Section</option>
                        <option value="TOOL_RACK">Tool Rack</option>
                        <option value="MEDICINE">Medicine Cabinet</option>
                        <option value="BAG">Travel Bag</option>
                        <option value="FOLDER">Document Folder</option>
                      </>
                    )}
                    <option value="CUSTOM">+ Create Custom Location Type...</option>
                  </select>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label htmlFor="locationParent" style={{ fontSize: '13px', fontWeight: 600 }}>Parent Location</label>
                  <select
                    id="locationParent"
                    value={newLocationParentId}
                    onChange={(e) => setNewLocationParentId(e.target.value)}
                    style={{ height: '40px', padding: '0 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)' }}
                  >
                    <option value="">-- Root Level (No Parent) --</option>
                    {flatLocations.map((loc) => (
                      <option key={loc.id} value={loc.id}>
                        {loc.path || loc.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {newLocationType === 'CUSTOM' && (
                <Input
                  id="customLocationTypeInput"
                  label="Custom Location Type *"
                  placeholder="e.g. Garage Cabinet, Tool Rack, Vehicle Trunk"
                  value={newCustomLocationType}
                  onChange={(e) => setNewCustomLocationType(e.target.value)}
                  required
                />
              )}

              <Input
                id="locationDesc"
                label="Description / Notes"
                placeholder="Optional notes regarding this storage area..."
                value={newLocationDescription}
                onChange={(e) => setNewLocationDescription(e.target.value)}
              />

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: 'var(--space-3)' }}>
                <Button type="button" variant="ghost" onClick={() => setIsAddLocationOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isSubmittingLocation}>
                  {isSubmittingLocation ? 'Creating...' : 'Create Location'}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* Edit Location Modal */}
      {isEditLocationOpen && editingLocationNode && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px'
          }}
          onClick={() => setIsEditLocationOpen(false)}
        >
          <Card
            style={{ width: '100%', maxWidth: '500px', border: '2px solid var(--color-primary-900)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                Edit Location &ldquo;{editingLocationNode.name}&rdquo;
              </h3>
              <button
                type="button"
                onClick={() => setIsEditLocationOpen(false)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '6px' }}
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleEditLocation} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              <Input
                id="editLocationName"
                label="Location Name *"
                value={editLocationName}
                onChange={(e) => setEditLocationName(e.target.value)}
                required
              />

              <div
                className="ozhzo-responsive-form-grid"
                style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label htmlFor="editLocationType" style={{ fontSize: '13px', fontWeight: 600 }}>Location Type</label>
                  <select
                    id="editLocationType"
                    value={editLocationType}
                    onChange={(e) => setEditLocationType(e.target.value)}
                    style={{ height: '40px', padding: '0 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)' }}
                  >
                    <option value="ROOM">Room / Area</option>
                    <option value="FURNITURE">Cupboard / Cabinet / Furniture</option>
                    <option value="SHELF">Shelf / Rack</option>
                    <option value="CONTAINER">Box / Container / Bin</option>
                    <option value="CUSTOM">Custom Location Type...</option>
                  </select>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <label htmlFor="editLocationParent" style={{ fontSize: '13px', fontWeight: 600 }}>Parent Location</label>
                  <select
                    id="editLocationParent"
                    value={editLocationParentId}
                    onChange={(e) => setEditLocationParentId(e.target.value)}
                    style={{ height: '40px', padding: '0 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)' }}
                  >
                    <option value="">-- Root Level (No Parent) --</option>
                    {flatLocations.filter(loc => loc.id !== editingLocationNode.id).map((loc) => (
                      <option key={loc.id} value={loc.id}>
                        {loc.path || loc.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {editLocationType === 'CUSTOM' && (
                <Input
                  id="editCustomLocationTypeInput"
                  label="Custom Location Type *"
                  placeholder="e.g. Garage Cabinet, Tool Rack"
                  value={editCustomLocationType}
                  onChange={(e) => setEditCustomLocationType(e.target.value)}
                  required
                />
              )}

              <Input
                id="editLocationDesc"
                label="Description / Notes"
                placeholder="Optional notes regarding this storage area..."
                value={editLocationDescription}
                onChange={(e) => setEditLocationDescription(e.target.value)}
              />

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: 'var(--space-3)' }}>
                <Button type="button" variant="ghost" onClick={() => setIsEditLocationOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isSubmittingEditLocation}>
                  {isSubmittingEditLocation ? 'Saving...' : 'Save Changes'}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* Move Item Modal */}
      {isMoveOpen && selectedItem && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px'
          }}
          onClick={() => setIsMoveOpen(false)}
        >
          <Card
            style={{ width: '100%', maxWidth: '440px', border: '2px solid var(--color-primary-900)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: 'var(--space-2)' }}>
              Move &ldquo;{selectedItem.name}&rdquo;
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-3)' }}>
              Current: {selectedItem.location_path}
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <label style={{ fontSize: '13px', fontWeight: 600 }}>Select New Destination Location:</label>
              <select
                value={targetLocationId}
                onChange={(e) => setTargetLocationId(e.target.value)}
                style={{ height: '40px', padding: '0 12px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)' }}
              >
                {flatLocations.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.path || l.name}
                  </option>
                ))}
              </select>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: 'var(--space-4)' }}>
              <Button variant="ghost" onClick={() => setIsMoveOpen(false)}>Cancel</Button>
              <Button onClick={handleMoveItem}>Confirm Relocation</Button>
            </div>
          </Card>
        </div>
      )}

      {/* Borrow Asset Modal */}
      {isBorrowOpen && selectedItem && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px'
          }}
          onClick={() => setIsBorrowOpen(false)}
        >
          <Card
            style={{ width: '100%', maxWidth: '440px', border: '2px solid var(--color-primary-900)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: 'var(--space-2)' }}>
              Borrow &ldquo;{selectedItem.name}&rdquo;
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-3)' }}>
              Record who has custody of this household item.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              <Input
                id="borrower"
                label="Borrower Name *"
                placeholder="e.g. Ashraf, Neighbor Dave"
                value={borrowerName}
                onChange={(e) => setBorrowerName(e.target.value)}
                required
              />
              <Input
                id="contact"
                label="Contact / Phone (Optional)"
                placeholder="+1..."
                value={borrowerContact}
                onChange={(e) => setBorrowerContact(e.target.value)}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: 'var(--space-4)' }}>
              <Button variant="ghost" onClick={() => setIsBorrowOpen(false)}>Cancel</Button>
              <Button onClick={handleBorrowItem}>Confirm Loan</Button>
            </div>
          </Card>
        </div>
      )}

      {/* Return Asset Modal */}
      {isReturnOpen && selectedItem && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px'
          }}
          onClick={() => setIsReturnOpen(false)}
        >
          <Card
            style={{ width: '100%', maxWidth: '440px', border: '2px solid var(--color-primary-900)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: 'var(--space-2)' }}>
              Return &ldquo;{selectedItem.name}&rdquo;
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-3)' }}>
              Currently borrowed by: <strong>{selectedItem.current_holder_name}</strong>
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: 'var(--space-4)' }}>
              <Button variant="ghost" onClick={() => setIsReturnOpen(false)}>Cancel</Button>
              <Button onClick={handleReturnItem}>Confirm Return to {selectedItem.location_path}</Button>
            </div>
          </Card>
        </div>
      )}
      {/* Quick Use Modal */}
      {isQuickUseOpen && quickUseItem && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px'
          }}
          onClick={() => setIsQuickUseOpen(false)}
        >
          <Card
            style={{
              width: '100%',
              maxWidth: '420px',
              border: '2px solid var(--color-primary-900)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                  Use / Consume {quickUseItem.name}
                </h3>
                <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                  Current stock: {quickUseItem.quantity} {quickUseItem.unit}
                </p>
              </div>
              <button
                onClick={() => setIsQuickUseOpen(false)}
                className="touch-target"
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}
                aria-label="Close dialog"
              >
                <X size={20} color="var(--color-text-secondary)" />
              </button>
            </div>

            <form onSubmit={handleExecuteQuickUse} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              <Input
                id="quickUseAmountInput"
                autoFocus
                label={`Amount Used (${quickUseItem.unit}) *`}
                type="number"
                step="0.01"
                value={quickUseAmount}
                onChange={(e) => setQuickUseAmount(e.target.value)}
                required
              />

              <div style={{ display: 'flex', gap: '6px' }}>
                {[0.5, 1, 2, 5].map((preset) => (
                  <Button
                    key={preset}
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={() => setQuickUseAmount(preset.toString())}
                  >
                    {preset} {quickUseItem.unit}
                  </Button>
                ))}
              </div>

              <Input
                id="quickUseNotesInput"
                label="Notes (optional)"
                placeholder="e.g. Daily cooking, baking..."
                value={quickUseNotes}
                onChange={(e) => setQuickUseNotes(e.target.value)}
              />

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: 'var(--space-2)' }}>
                <Button type="button" variant="ghost" onClick={() => setIsQuickUseOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isSubmittingUse}>
                  {isSubmittingUse ? 'Recording...' : `Use ${quickUseAmount || 0} ${quickUseItem.unit}`}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* Quick Restock Modal */}
      {isQuickRestockOpen && quickRestockItem && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px'
          }}
          onClick={() => setIsQuickRestockOpen(false)}
        >
          <Card
            style={{
              width: '100%',
              maxWidth: '420px',
              border: '2px solid var(--color-primary-900)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                  Restock {quickRestockItem.name}
                </h3>
                <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                  Current stock: {quickRestockItem.quantity} {quickRestockItem.unit}
                </p>
              </div>
              <button
                onClick={() => setIsQuickRestockOpen(false)}
                className="touch-target"
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}
                aria-label="Close dialog"
              >
                <X size={20} color="var(--color-text-secondary)" />
              </button>
            </div>

            <form onSubmit={handleExecuteQuickRestock} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              <Input
                id="quickRestockAmountInput"
                autoFocus
                label={`Amount Added (${quickRestockItem.unit}) *`}
                type="number"
                step="0.01"
                value={quickRestockAmount}
                onChange={(e) => setQuickRestockAmount(e.target.value)}
                required
              />

              <div style={{ display: 'flex', gap: '6px' }}>
                {[1, 2, 5, 10].map((preset) => (
                  <Button
                    key={preset}
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={() => setQuickRestockAmount(preset.toString())}
                  >
                    +{preset} {quickRestockItem.unit}
                  </Button>
                ))}
              </div>

              <Input
                id="quickRestockNotesInput"
                label="Notes (optional)"
                placeholder="e.g. Grocery store, bulk purchase..."
                value={quickRestockNotes}
                onChange={(e) => setQuickRestockNotes(e.target.value)}
              />

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: 'var(--space-2)' }}>
                <Button type="button" variant="ghost" onClick={() => setIsQuickRestockOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isSubmittingRestock}>
                  {isSubmittingRestock ? 'Restocking...' : `Add +${quickRestockAmount || 0} ${quickRestockItem.unit}`}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}
    </div>
  );
}
