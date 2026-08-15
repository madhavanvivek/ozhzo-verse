'use client';

import React, { useState } from 'react';
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

} from 'lucide-react';

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
  type: string;
  path: string;
  children?: LocationNode[];
}

export default function InventoryPage() {
  const [activeTab, setActiveTab] = useState<'ALL' | 'CONSUMABLES' | 'ASSETS' | 'LOCATIONS' | 'BORROWED'>('ALL');
  const [search, setSearch] = useState('');
  const [selectedLocation, setSelectedLocation] = useState<string | null>(null);
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [isMoveOpen, setIsMoveOpen] = useState(false);
  const [isBorrowOpen, setIsBorrowOpen] = useState(false);
  const [isReturnOpen, setIsReturnOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState<Item | null>(null);

  // Sample locations hierarchy tree
  const locationsTree: LocationNode[] = [
    {
      id: 'loc-1',
      name: 'Store Room',
      type: 'ROOM',
      path: 'Store Room',
      children: [
        {
          id: 'loc-2',
          name: '3rd Cupboard',
          type: 'FURNITURE',
          path: 'Store Room > 3rd Cupboard',
          children: [
            { id: 'loc-3', name: 'Blue Box', type: 'CONTAINER', path: 'Store Room > 3rd Cupboard > Blue Box' },
            { id: 'loc-4', name: 'Black File', type: 'CONTAINER', path: 'Store Room > 3rd Cupboard > Black File' },
          ],
        },
      ],
    },
    {
      id: 'loc-5',
      name: 'Kitchen',
      type: 'ROOM',
      path: 'Kitchen',
      children: [
        { id: 'loc-6', name: 'Upper Cabinet', type: 'FURNITURE', path: 'Kitchen > Upper Cabinet' },
        { id: 'loc-7', name: 'Refrigerator', type: 'FURNITURE', path: 'Kitchen > Refrigerator' },
      ],
    },
    {
      id: 'loc-8',
      name: 'Garage',
      type: 'ROOM',
      path: 'Garage',
      children: [
        { id: 'loc-9', name: 'Tool Rack', type: 'FURNITURE', path: 'Garage > Tool Rack' },
      ],
    },
  ];

  // Initial state items
  const [items, setItems] = useState<Item[]>([
    {
      id: 'item-1',
      name: 'Basmati Rice',
      item_type: 'CONSUMABLE',
      category_name: 'Pantry',
      quantity: 2.0,
      unit: 'kg',
      min_threshold: 5.0,
      preferred_quantity: 10.0,
      location_path: 'Kitchen > Upper Cabinet',
      asset_status: 'AVAILABLE',
      status: 'LOW',
      expiry_status: 'NORMAL',
    },
    {
      id: 'item-2',
      name: 'Extra Virgin Olive Oil',
      item_type: 'CONSUMABLE',
      category_name: 'Pantry',
      quantity: 0,
      unit: 'L',
      min_threshold: 1.0,
      preferred_quantity: 3.0,
      location_path: 'Kitchen > Upper Cabinet',
      asset_status: 'AVAILABLE',
      status: 'OUT_OF_STOCK',
      expiry_status: 'NORMAL',
    },
    {
      id: 'item-3',
      name: 'Cordless Power Drill',
      item_type: 'ASSET',
      category_name: 'Tools',
      quantity: 1,
      unit: 'pcs',
      location_path: 'Garage > Tool Rack',
      condition: 'EXCELLENT',
      asset_status: 'AVAILABLE',
      status: 'GOOD',
      expiry_status: 'NORMAL',
    },
    {
      id: 'item-4',
      name: 'Heavy Duty Toolkit',
      item_type: 'ASSET',
      category_name: 'Tools',
      quantity: 1,
      unit: 'pcs',
      location_path: 'Store Room > 3rd Cupboard > Blue Box',
      condition: 'GOOD',
      asset_status: 'BORROWED',
      current_holder_name: 'Ashraf',
      status: 'GOOD',
      expiry_status: 'NORMAL',
    },
    {
      id: 'item-5',
      name: 'House Keys (Spare Set)',
      item_type: 'ASSET',
      category_name: 'Keys',
      quantity: 1,
      unit: 'pcs',
      location_path: 'Store Room > 3rd Cupboard > Blue Box',
      condition: 'GOOD',
      asset_status: 'AVAILABLE',
      status: 'GOOD',
      expiry_status: 'NORMAL',
    },
  ]);

  // Modals form state
  const [newItemName, setNewItemName] = useState('');
  const [newItemType, setNewItemType] = useState<'CONSUMABLE' | 'ASSET'>('CONSUMABLE');
  const [newItemCategory] = useState('Pantry');
  const [newItemQty] = useState('1');
  const [newItemUnit] = useState('pcs');
  const [newItemThreshold] = useState('1');
  const [newItemLocationPath, setNewItemLocationPath] = useState('Store Room > 3rd Cupboard > Blue Box');

  // Relocation state
  const [targetLocation, setTargetLocation] = useState('Garage > Tool Rack');
  // Borrow state
  const [borrowerName, setBorrowerName] = useState('');

  const handleAddItem = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newItemName) return;

    const qty = parseFloat(newItemQty) || 0;
    const thresh = parseFloat(newItemThreshold) || 1;
    let status: 'GOOD' | 'LOW' | 'OUT_OF_STOCK' = 'GOOD';
    if (qty === 0) status = 'OUT_OF_STOCK';
    else if (qty <= thresh) status = 'LOW';

    const newItem: Item = {
      id: `item-${Date.now()}`,
      name: newItemName,
      item_type: newItemType,
      category_name: newItemCategory,
      quantity: qty,
      unit: newItemUnit,
      min_threshold: newItemType === 'CONSUMABLE' ? thresh : undefined,
      location_path: newItemLocationPath,
      asset_status: 'AVAILABLE',
      status,
      expiry_status: 'NORMAL',
    };

    setItems([...items, newItem]);
    setNewItemName('');
    setIsAddOpen(false);
  };

  const handleMoveItem = () => {
    if (!selectedItem) return;
    setItems(
      items.map((i) =>
        i.id === selectedItem.id ? { ...i, location_path: targetLocation } : i
      )
    );
    setIsMoveOpen(false);
    setSelectedItem(null);
  };

  const handleBorrowItem = () => {
    if (!selectedItem || !borrowerName) return;
    setItems(
      items.map((i) =>
        i.id === selectedItem.id
          ? { ...i, asset_status: 'BORROWED', current_holder_name: borrowerName }
          : i
      )
    );
    setBorrowerName('');
    setIsBorrowOpen(false);
    setSelectedItem(null);
  };

  const handleReturnItem = () => {
    if (!selectedItem) return;
    setItems(
      items.map((i) =>
        i.id === selectedItem.id
          ? { ...i, asset_status: 'AVAILABLE', current_holder_name: undefined }
          : i
      )
    );
    setIsReturnOpen(false);
    setSelectedItem(null);
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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '1100px' }}>
      {/* Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-3)' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-primary-900)' }}>
            Household Inventory & Home Memory
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)' }}>
            Know what we have, where it is kept, and who borrowed it.
          </p>
        </div>

        <Button onClick={() => setIsAddOpen(true)}>
          <Plus size={16} />
          <span>Add Item / Asset</span>
        </Button>
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

        <Card style={{ padding: 'var(--space-4)', borderLeft: '4px solid #EAB308' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: '#A16207' }}>LOW STOCK</span>
          <div style={{ fontSize: '24px', fontWeight: 800, color: '#A16207', marginTop: '4px' }}>
            {lowStockCount}
          </div>
          <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>Replenish soon</span>
        </Card>

        <Card style={{ padding: 'var(--space-4)', borderLeft: '4px solid #EF4444' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: '#B91C1C' }}>OUT OF STOCK</span>
          <div style={{ fontSize: '24px', fontWeight: 800, color: '#B91C1C', marginTop: '4px' }}>
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

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: '8px' }}>
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
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 1fr) 2fr', gap: 'var(--space-4)' }}>
          <Card style={{ padding: 'var(--space-4)' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 700, marginBottom: 'var(--space-3)' }}>Household Locations</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {locationsTree.map((room) => (
                <div key={room.id} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div
                    onClick={() => setSelectedLocation(room.name)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '6px 10px',
                      borderRadius: 'var(--radius-md)',
                      backgroundColor: selectedLocation === room.name ? 'var(--color-primary-50)' : 'transparent',
                      cursor: 'pointer',
                      fontSize: '13px',
                      fontWeight: 600,
                    }}
                  >
                    <FolderOpen size={16} color="var(--color-primary-700)" />
                    <span>{room.name}</span>
                  </div>

                  {room.children && (
                    <div style={{ paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      {room.children.map((sub) => (
                        <div key={sub.id}>
                          <div
                            onClick={() => setSelectedLocation(sub.name)}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '6px',
                              padding: '5px 8px',
                              borderRadius: 'var(--radius-md)',
                              backgroundColor: selectedLocation === sub.name ? 'var(--color-primary-50)' : 'transparent',
                              cursor: 'pointer',
                              fontSize: '13px',
                            }}
                          >
                            <Box size={14} color="var(--color-text-secondary)" />
                            <span>{sub.name}</span>
                          </div>

                          {sub.children && (
                            <div style={{ paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                              {sub.children.map((box) => (
                                <div
                                  key={box.id}
                                  onClick={() => setSelectedLocation(box.name)}
                                  style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '6px',
                                    padding: '4px 8px',
                                    borderRadius: 'var(--radius-md)',
                                    backgroundColor: selectedLocation === box.name ? 'var(--color-primary-100)' : 'transparent',
                                    cursor: 'pointer',
                                    fontSize: '12px',
                                    color: selectedLocation === box.name ? 'var(--color-primary-900)' : 'var(--color-text-secondary)',
                                  }}
                                >
                                  <span>📍 {box.name}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Card>

          <Card style={{ padding: 'var(--space-4)' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 700, marginBottom: 'var(--space-3)' }}>
              Items inside: {selectedLocation || 'All Locations'}
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {filteredItems.map((item) => (
                <div
                  key={item.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--color-border-subtle)',
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '14px' }}>{item.name}</div>
                    <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>{item.location_path}</div>
                  </div>
                  <Badge variant={item.asset_status === 'BORROWED' ? 'low-stock' : 'in-stock'}>
                    {item.asset_status === 'BORROWED' ? `With ${item.current_holder_name}` : 'Available'}
                  </Badge>
                </div>
              ))}
            </div>
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
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 'var(--space-4)' }}>
            {filteredItems.map((item) => (
              <Card key={item.id} style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: 'var(--space-3)' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                    <div>
                      <span style={{ fontSize: '11px', fontWeight: 700, color: item.item_type === 'ASSET' ? 'var(--color-primary-700)' : 'var(--color-text-tertiary)', textTransform: 'uppercase' }}>
                        {item.item_type} • {item.category_name || 'General'}
                      </span>
                      <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
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
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: 'var(--color-primary-800)', backgroundColor: 'var(--color-surface-overlay)', padding: '4px 8px', borderRadius: '4px' }}>
                      <MapPin size={13} />
                      <span style={{ fontWeight: 600 }}>{item.location_path}</span>
                    </div>
                  )}
                </div>

                {/* Card Action Controls */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 'var(--space-2)', borderTop: '1px solid var(--color-border-subtle)', gap: '6px' }}>
                  {item.item_type === 'ASSET' ? (
                    <>
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
                    </>
                  ) : (
                    <div style={{ display: 'flex', gap: '4px' }}>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => {
                          setItems(items.map(i => i.id === item.id ? { ...i, quantity: Math.max(0, i.quantity - 1) } : i));
                        }}
                      >
                        -1 {item.unit}
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => {
                          setItems(items.map(i => i.id === item.id ? { ...i, quantity: i.quantity + 1 } : i));
                        }}
                      >
                        +1 {item.unit}
                      </Button>
                    </div>
                  )}

                  <Button size="sm" variant="ghost" style={{ color: 'var(--status-overdue)' }}>
                    <Trash2 size={13} />
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </>
      )}

      {/* Move Item Modal */}
      {isMoveOpen && selectedItem && (
        <Card style={{ border: '2px solid var(--color-primary-900)' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: 'var(--space-3)' }}>
            Move &ldquo;{selectedItem.name}&rdquo;
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-3)' }}>
            Current: {selectedItem.location_path}
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <label style={{ fontSize: '13px', fontWeight: 600 }}>Select New Destination Location:</label>
            <select
              value={targetLocation}
              onChange={(e) => setTargetLocation(e.target.value)}
              style={{ height: '40px', padding: '0 12px', borderRadius: 'var(--radius-md)' }}
            >
              <option value="Garage > Tool Rack">Garage &gt; Tool Rack</option>
              <option value="Store Room > 3rd Cupboard > Blue Box">Store Room &gt; 3rd Cupboard &gt; Blue Box</option>
              <option value="Kitchen > Upper Cabinet">Kitchen &gt; Upper Cabinet</option>
            </select>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: 'var(--space-4)' }}>
            <Button variant="ghost" onClick={() => setIsMoveOpen(false)}>Cancel</Button>
            <Button onClick={handleMoveItem}>Confirm Relocation</Button>
          </div>
        </Card>
      )}

      {/* Borrow Asset Modal */}
      {isBorrowOpen && selectedItem && (
        <Card style={{ border: '2px solid var(--color-primary-900)' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: 'var(--space-3)' }}>
            Borrow &ldquo;{selectedItem.name}&rdquo;
          </h3>
          <Input
            id="borrower"
            label="Borrower Name (e.g. Ashraf, Neighbor Bob)"
            value={borrowerName}
            onChange={(e) => setBorrowerName(e.target.value)}
            required
          />
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: 'var(--space-4)' }}>
            <Button variant="ghost" onClick={() => setIsBorrowOpen(false)}>Cancel</Button>
            <Button onClick={handleBorrowItem}>Confirm Loan</Button>
          </div>
        </Card>
      )}

      {/* Return Asset Modal */}
      {isReturnOpen && selectedItem && (
        <Card style={{ border: '2px solid var(--color-primary-900)' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: 'var(--space-3)' }}>
            Return &ldquo;{selectedItem.name}&rdquo;
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-3)' }}>
            Currently with: <strong>{selectedItem.current_holder_name}</strong>
          </p>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: 'var(--space-4)' }}>
            <Button variant="ghost" onClick={() => setIsReturnOpen(false)}>Cancel</Button>
            <Button onClick={handleReturnItem}>Confirm Return to {selectedItem.location_path}</Button>
          </div>
        </Card>
      )}

      {/* Add Item Modal with Common Items Template Catalog */}
      {isAddOpen && (
        <Card style={{ border: '2px solid var(--color-primary-900)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 700 }}>
              Add Item to Home Inventory
            </h3>
            <Badge variant="neutral">Common Catalog or Custom</Badge>
          </div>

          {/* Quick Select Common Item Chips */}
          <div style={{ marginBottom: 'var(--space-4)' }}>
            <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '8px' }}>
              POPULAR HOUSEHOLD ITEMS (Click to Pre-fill):
            </label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {[
                { name: 'Rice', unit: 'kg', cat: 'Pantry' },
                { name: 'Sugar', unit: 'kg', cat: 'Pantry' },
                { name: 'Salt', unit: 'kg', cat: 'Pantry' },
                { name: 'Milk', unit: 'L', cat: 'Refrigerator' },
                { name: 'Cooking Oil', unit: 'L', cat: 'Pantry' },
                { name: 'Toothpaste', unit: 'pcs', cat: 'Personal Care' },
                { name: 'Detergent', unit: 'kg', cat: 'Cleaning' },
                { name: 'Batteries (AA)', unit: 'pack', cat: 'Household' },
              ].map((tpl) => (
                <button
                  key={tpl.name}
                  type="button"
                  onClick={() => {
                    setNewItemName(tpl.name);
                    setNewItemType('CONSUMABLE');
                  }}
                  style={{
                    padding: '4px 10px',
                    borderRadius: 'var(--radius-full)',
                    background: newItemName === tpl.name ? 'var(--color-primary-900)' : 'var(--color-surface-hover)',
                    color: newItemName === tpl.name ? '#ffffff' : 'var(--color-text-primary)',
                    border: '1px solid var(--color-border)',
                    fontSize: '12px',
                    fontWeight: 500,
                    cursor: 'pointer'
                  }}
                >
                  + {tpl.name} ({tpl.unit})
                </button>
              ))}
            </div>
          </div>

          <form onSubmit={handleAddItem} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--space-3)' }}>
              <Input
                id="name"
                label="Item Name"
                placeholder="e.g. Basmati Rice, House Keys, Pickle"
                value={newItemName}
                onChange={(e) => setNewItemName(e.target.value)}
                required
              />

              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '13px', fontWeight: 600 }}>Type</label>
                <select
                  value={newItemType}
                  onChange={(e) => setNewItemType(e.target.value as any)}
                  style={{ height: '40px', padding: '0 12px', borderRadius: 'var(--radius-md)' }}
                >
                  <option value="CONSUMABLE">Consumable (Pantry/Supplies)</option>
                  <option value="ASSET">Household Asset (Durable Tool/Keys)</option>
                </select>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ fontSize: '13px', fontWeight: 600 }}>Hierarchical Location</label>
                <select
                  value={newItemLocationPath}
                  onChange={(e) => setNewItemLocationPath(e.target.value)}
                  style={{ height: '40px', padding: '0 12px', borderRadius: 'var(--radius-md)' }}
                >
                  <option value="Kitchen > Pantry > 2nd Shelf > Blue Container">Kitchen &gt; Pantry &gt; 2nd Shelf &gt; Blue Container</option>
                  <option value="Store Room > 3rd Cupboard > Blue Box">Store Room &gt; 3rd Cupboard &gt; Blue Box</option>
                  <option value="Garage > Tool Rack">Garage &gt; Tool Rack</option>
                  <option value="Kitchen > Refrigerator">Kitchen &gt; Refrigerator</option>
                </select>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: 'var(--space-3)' }}>
              <Button type="button" variant="ghost" onClick={() => setIsAddOpen(false)}>Cancel</Button>
              <Button type="submit">Save to Home Inventory</Button>
            </div>
          </form>
        </Card>
      )}
    </div>
  );
}
