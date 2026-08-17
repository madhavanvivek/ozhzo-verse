'use client';

import React, {useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { HomeSwitcher } from '@/components/home/HomeSwitcher';
import { Logo } from '@/components/brand/Logo';
import { Button } from '@/components/ui/Button';
import {
  LayoutDashboard,
  CalendarCheck,
  Package,
  ShoppingCart,
  CheckSquare,
  Receipt,
  Calendar,
  Settings,
  Bell,
  Search,
  Plus,
  X
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  const [homes, setHomes] = useState<
   { home_id: string; name: string; role: string }[]
  >([]);
  const [activeHomeId, setActiveHomeId] = useState<string | null>(null);
  const [userProfile, setUserProfile] = useState<{
    display_name: string;
    email?: string | null;
    phone_number?: string | null;
  } | null>(null);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [isQuickAddOpen, setIsQuickAddOpen] = useState(false);

  useEffect(() => {
    const loadUserDataAndHomes = async () => {
      try {
        const [userRes, homesRes] = await Promise.allSettled([
          apiClient.get<{
            display_name: string;
            email?: string | null;
            phone_number?: string | null;
          }>('/users/me'),
          apiClient.get<
            Array<{
              id: string;
              name: string;
              role: string;
            }>
          >('/homes')
        ]);

        if (userRes.status === 'fulfilled' && userRes.value) {
          setUserProfile(userRes.value);
        }

        if (homesRes.status === 'fulfilled' && homesRes.value) {
          const mappedHomes = homesRes.value.map((home) => ({
            home_id: home.id,
            name: home.name,
            role: home.role
          }));

          setHomes(mappedHomes);

          const savedHomeId = localStorage.getItem('active_home_id');

          if (savedHomeId && mappedHomes.some((h) => h.home_id === savedHomeId)) {
            setActiveHomeId(savedHomeId);
          } else if (mappedHomes.length > 0) {
            setActiveHomeId(mappedHomes[0].home_id);
            localStorage.setItem('active_home_id', mappedHomes[0].home_id);
          } else {
            setActiveHomeId(null);
            localStorage.removeItem('active_home_id');
          }
        }
      } catch (error) {
        console.error('Failed to load user and homes:', error);
        setHomes([]);
        setActiveHomeId(null);
        localStorage.removeItem('active_home_id');
      }
    };

    loadUserDataAndHomes();
  }, []);

  const getInitials = (name?: string | null): string => {
    if (!name || !name.trim()) return 'U';
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) {
      return parts[0].substring(0, 2).toUpperCase();
    }
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  };
  const activeHome = homes.find(h => h.home_id === activeHomeId);

  const navItems = [
    { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { label: 'Today', href: '/today', icon: CalendarCheck },
    { label: 'Home Memory', href: '/inventory', icon: Package },
    { label: 'Purchase List', href: '/shopping', icon: ShoppingCart },
    { label: 'Tasks & Chores', href: '/tasks', icon: CheckSquare },
    { label: 'Bills & Reminders', href: '/bills', icon: Receipt },
    { label: 'Calendar', href: '/calendar', icon: Calendar },
    { label: 'Home Settings', href: '/settings', icon: Settings },
  ];

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Desktop Sidebar */}
      <aside style={{ width: '250px', backgroundColor: 'var(--color-surface-card)', borderRight: '1px solid var(--color-border-subtle)', padding: 'var(--space-4)', display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
        <div style={{ padding: '0 8px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Logo variant="mark" width={32} height={32} href="/dashboard" />
          <div>
            <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-primary-900)', letterSpacing: '-0.02em', lineHeight: 1.2 }}>
              ozhzo verse
            </div>
            <div style={{ fontSize: '10px', color: 'var(--color-text-secondary)', fontWeight: 600, letterSpacing: '0.01em' }}>
              Where Home Comes Together.
            </div>
          </div>
        </div>

        <div style={{ padding: '0 8px' }}>
          <HomeSwitcher
            currentHome={activeHome}
            homes={homes}
            onSelectHome={(homeId) => {
  setActiveHomeId(homeId);
  localStorage.setItem('active_home_id', homeId);
}}
          />
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1 }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '8px 12px',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '14px',
                  fontWeight: isActive ? 600 : 500,
                  color: isActive ? 'var(--color-text-inverse)' : 'var(--color-text-primary)',
                  backgroundColor: isActive ? 'var(--color-primary-900)' : 'transparent',
                  transition: 'background-color 0.15s ease'
                }}
              >
                <Icon size={18} color={isActive ? 'var(--color-text-inverse)' : 'var(--color-text-secondary)'} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Main Content Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <header style={{ height: '60px', backgroundColor: 'var(--color-surface-card)', borderBottom: '1px solid var(--color-border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 var(--space-6)', gap: '16px' }}>
          {/* Global Search Bar */}
          <div style={{ display: 'flex', alignItems: 'center', flex: 1, maxWidth: '460px' }}>
            <div
              onClick={() => setIsSearchOpen(true)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                width: '100%',
                padding: '6px 14px',
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'var(--color-surface-subtle)',
                border: '1px solid var(--color-border)',
                cursor: 'pointer',
                fontSize: '13px',
                color: 'var(--color-text-secondary)'
              }}
            >
              <Search size={16} />
              <span style={{ flex: 1 }}>Search Home Memory (assets, pantry, chores, bills)...</span>
              <kbd style={{ fontSize: '11px', padding: '2px 6px', background: 'var(--color-surface-card)', borderRadius: '4px', border: '1px solid var(--color-border)' }}>
                Cmd+K
              </kbd>
            </div>
          </div>

          {/* Quick Add & Account Header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsQuickAddOpen(true)}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <Plus size={16} />
              <span>Add</span>
            </Button>

            <Link
              href="/notifications"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                textDecoration: 'none',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: '6px',
                position: 'relative'
              }}
              aria-label="Notifications"
            >
              <Bell size={20} color="var(--color-text-secondary)" />
              <span
                style={{
                  position: 'absolute',
                  top: '4px',
                  right: '4px',
                  width: '8px',
                  height: '8px',
                  backgroundColor: 'var(--status-low-stock)',
                  borderRadius: '50%'
                }}
              />
            </Link>

            <Link
              href="/profile"
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                backgroundColor: 'var(--color-primary-900)',
                color: 'var(--color-text-inverse)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '13px',
                fontWeight: 600,
                textDecoration: 'none',
                cursor: 'pointer'
              }}
              aria-label="User Profile"
            >
              {getInitials(userProfile?.display_name)}
            </Link>
          </div>
        </header>

        {/* Page Content */}
        <main style={{ flex: 1, padding: 'var(--space-6)', backgroundColor: 'var(--color-surface-page)', overflowY: 'auto' }}>
          {children}
        </main>
      </div>

      {/* Global Search Modal */}
      {isSearchOpen && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 100, display: 'flex', alignItems: 'flex-start', justifyContent: 'center', paddingTop: '10vh' }}>
          <div style={{ width: '90%', maxWidth: '600px', backgroundColor: 'var(--color-surface-card)', borderRadius: 'var(--radius-lg)', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)', overflow: 'hidden' }}>
            <div style={{ display: 'flex', alignItems: 'center', padding: '14px 18px', borderBottom: '1px solid var(--color-border)' }}>
              <Search size={20} color="var(--color-text-secondary)" style={{ marginRight: '10px' }} />
              <input
                type="text"
                autoFocus
                placeholder="Search tools, pantry stock, bills, chores, locations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{ flex: 1, border: 'none', outline: 'none', fontSize: '16px', backgroundColor: 'transparent' }}
              />
              <button onClick={() => setIsSearchOpen(false)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
                <X size={18} color="var(--color-text-tertiary)" />
              </button>
            </div>
            <div style={{ padding: '16px', maxHeight: '350px', overflowY: 'auto', fontSize: '13px', color: 'var(--color-text-secondary)' }}>
              {searchQuery.trim().length === 0 ? (
                <div style={{ textAlign: 'center', padding: '20px' }}>
                  <p>Type to search your entire Home Memory.</p>
                  <p style={{ fontSize: '12px', marginTop: '4px' }}>Try searching <em>"toolkit"</em>, <em>"drill"</em>, <em>"electricity"</em>, or <em>"rice"</em>.</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ padding: '10px 14px', borderRadius: 'var(--radius-md)', background: 'var(--color-surface-subtle)' }}>
                    <div style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>🔧 Electric Drill</div>
                    <div style={{ fontSize: '12px' }}>Garage ➔ Tool Cabinet ➔ Shelf 2 • Status: Available</div>
                  </div>
                  <div style={{ padding: '10px 14px', borderRadius: 'var(--radius-md)', background: 'var(--color-surface-subtle)' }}>
                    <div style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>⚡ BESCOM Electricity Bill</div>
                    <div style={{ fontSize: '12px' }}>INR 2,000.00 • Due in 2 days • UNPAID</div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Global Quick Add Modal */}
      {isQuickAddOpen && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ width: '90%', maxWidth: '480px', backgroundColor: 'var(--color-surface-card)', borderRadius: 'var(--radius-lg)', padding: '20px', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 700 }}>Quick Add to Home</h3>
              <button onClick={() => setIsQuickAddOpen(false)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <Link href="/tasks" onClick={() => setIsQuickAddOpen(false)} style={{ padding: '12px', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', textAlign: 'center', textDecoration: 'none', color: 'var(--color-text-primary)' }}>
                🧹 <strong>+ Task</strong>
                <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>Add chore or routine</div>
              </Link>
              <Link href="/shopping" onClick={() => setIsQuickAddOpen(false)} style={{ padding: '12px', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', textAlign: 'center', textDecoration: 'none', color: 'var(--color-text-primary)' }}>
                🛒 <strong>+ Shopping</strong>
                <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>Add purchase item</div>
              </Link>
              <Link href="/inventory" onClick={() => setIsQuickAddOpen(false)} style={{ padding: '12px', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', textAlign: 'center', textDecoration: 'none', color: 'var(--color-text-primary)' }}>
                🍚 <strong>+ Pantry Stock</strong>
                <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>Record consumable supply</div>
              </Link>
              <Link href="/inventory" onClick={() => setIsQuickAddOpen(false)} style={{ padding: '12px', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', textAlign: 'center', textDecoration: 'none', color: 'var(--color-text-primary)' }}>
                🔧 <strong>+ Home Asset</strong>
                <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>Record tool or appliance</div>
              </Link>
              <Link href="/bills" onClick={() => setIsQuickAddOpen(false)} style={{ padding: '12px', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', textAlign: 'center', textDecoration: 'none', color: 'var(--color-text-primary)' }}>
                ⚡ <strong>+ Bill</strong>
                <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>Track domestic expense</div>
              </Link>
              <Link href="/calendar" onClick={() => setIsQuickAddOpen(false)} style={{ padding: '12px', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', textAlign: 'center', textDecoration: 'none', color: 'var(--color-text-primary)' }}>
                🎂 <strong>+ Event</strong>
                <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>Add appointment or trip</div>
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
