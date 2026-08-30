'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { HomeSwitcher } from '@/components/home/HomeSwitcher';
import { Logo } from '@/components/brand/Logo';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
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
  X,
  Menu,
  Users,
  User,
  ArrowRight
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

interface SearchItemResult {
  id: string;
  domain: string;
  title: string;
  subtitle?: string | null;
  status?: string | null;
  navigation_target?: string | null;
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();

  const [homes, setHomes] = useState<
    { home_id: string; name: string; role: string }[]
  >([]);
  const [activeHomeId, setActiveHomeId] = useState<string | null>(null);
  const [userProfile, setUserProfile] = useState<{
    display_name: string;
    email?: string | null;
    phone_number?: string | null;
    mobile_verified?: boolean;
  } | null>(() => apiClient.getUser());
  const [unreadCount, setUnreadCount] = useState(0);

  // Modals & Navigation state
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchItemResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isQuickAddOpen, setIsQuickAddOpen] = useState(false);
  const [isMobileMoreOpen, setIsMobileMoreOpen] = useState(false);

  const loadUserDataAndHomes = async () => {
    try {
      const userRes = await apiClient.get<{
        id: string;
        display_name: string;
        email?: string | null;
        phone_number?: string | null;
        mobile_verified?: boolean;
        homes?: Array<{
          home_id?: string;
          id?: string;
          name: string;
          role: string;
        }>;
      }>('/users/me');

      if (userRes) {
        setUserProfile(userRes);
        apiClient.setUser(userRes);

        let mappedHomes: Array<{ home_id: string; name: string; role: string }> = [];
        if (Array.isArray(userRes.homes) && userRes.homes.length > 0) {
          mappedHomes = userRes.homes.map((home) => ({
            home_id: home.home_id || home.id || '',
            name: home.name,
            role: home.role
          }));
        } else {
          try {
            const freshHomes = await apiClient.get<Array<{ id: string; name: string; role: string }>>('/homes');
            if (Array.isArray(freshHomes)) {
              mappedHomes = freshHomes.map((h) => ({
                home_id: h.id,
                name: h.name,
                role: h.role
              }));
            }
          } catch {
            mappedHomes = [];
          }
        }

        setHomes(mappedHomes);
        const resolvedId = apiClient.resolveActiveHome(mappedHomes);
        setActiveHomeId(resolvedId);
      }
    } catch (error) {
      console.error('Failed to load user and homes:', error);
      setHomes([]);
      setActiveHomeId(null);
      apiClient.setActiveHomeId(null);
    }
  };

  useEffect(() => {
    loadUserDataAndHomes();

    const handleHomeChanged = () => {
      loadUserDataAndHomes();
    };

    window.addEventListener('home-changed', handleHomeChanged);
    return () => window.removeEventListener('home-changed', handleHomeChanged);
  }, []);

  // Check unread notifications count
  useEffect(() => {
    const checkNotifications = async () => {
      try {
        const res = await apiClient.get<{ unread_count?: number; items?: any[] }>('/notifications');
        if (typeof res?.unread_count === 'number') {
          setUnreadCount(res.unread_count);
        } else if (Array.isArray(res?.items)) {
          setUnreadCount(res.items.filter((n: any) => !n.is_read).length);
        }
      } catch (err) {
        // Silently ignore notification fetch failure
      }
    };
    checkNotifications();
  }, [pathname]);

  // Global search keyboard shortcuts and escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen((prev) => !prev);
      }
      if (e.key === 'Escape') {
        setIsSearchOpen(false);
        setIsQuickAddOpen(false);
        setIsMobileMoreOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Search API execution with debounce
  useEffect(() => {
    if (!isSearchOpen || !searchQuery.trim() || !activeHomeId) {
      setSearchResults([]);
      setIsSearching(false);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const res = await apiClient.get<{ results: SearchItemResult[] }>(
          `/homes/${activeHomeId}/search?q=${encodeURIComponent(searchQuery.trim())}`
        );
        setSearchResults(res?.results || []);
      } catch (err) {
        console.error('Search query failed:', err);
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [searchQuery, isSearchOpen, activeHomeId]);

  const getInitials = (name?: string | null): string => {
    if (!name || !name.trim()) return 'U';
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) {
      return parts[0].substring(0, 2).toUpperCase();
    }
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  };

  const activeHome = homes.find((h) => h.home_id === activeHomeId);

  const mainNavItems = [
    { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { label: 'Today', href: '/today', icon: CalendarCheck },
    { label: 'Home Memory', href: '/inventory', icon: Package },
    { label: 'Purchase List', href: '/shopping', icon: ShoppingCart },
    { label: 'Tasks & Chores', href: '/tasks', icon: CheckSquare },
    { label: 'Bills & Reminders', href: '/bills', icon: Receipt },
    { label: 'Calendar', href: '/calendar', icon: Calendar },
    { label: 'Family Members', href: '/members', icon: Users },
    { label: 'Home Settings', href: '/settings', icon: Settings },
  ];

  const handleSearchResultClick = (target?: string | null) => {
    setIsSearchOpen(false);
    setSearchQuery('');
    if (target) {
      router.push(target);
    }
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh', width: '100%', overflowX: 'hidden' }}>
      {/* Desktop & Tablet Sidebar */}
      <aside
        className="ozhzo-sidebar ozhzo-desktop-only"
        style={{
          width: '250px',
          backgroundColor: 'var(--color-surface-card)',
          borderRight: '1px solid var(--color-border-subtle)',
          padding: 'var(--space-4)',
          flexDirection: 'column',
          gap: 'var(--space-6)',
          flexShrink: 0,
        }}
      >
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
              apiClient.setActiveHomeId(homeId);
              window.dispatchEvent(new Event('home-changed'));
            }}
            onCreateNewHome={() => {
              router.push('/dashboard?action=create_home');
            }}
            onJoinHome={() => {
              router.push('/join');
            }}
          />
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1 }}>
          {mainNavItems.map((item) => {
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
                  transition: 'background-color 0.15s ease',
                  minHeight: '40px'
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
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflowX: 'hidden' }}>
        {/* Responsive Header */}
        <header
          style={{
            height: '60px',
            backgroundColor: 'var(--color-surface-card)',
            borderBottom: '1px solid var(--color-border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 var(--space-3)',
            gap: '8px',
            position: 'sticky',
            top: 0,
            zIndex: 40
          }}
        >
          {/* Left section: Logo/HomeSwitcher on mobile, Search bar on desktop */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: 0, maxWidth: '500px' }}>
            {/* Mobile Header Brand & HomeSwitcher */}
            <div className="ozhzo-mobile-only" style={{ alignItems: 'center', gap: '6px', flex: 1, minWidth: 0 }}>
              <Logo variant="mark" width={26} height={26} href="/dashboard" />
              <div style={{ flex: 1, minWidth: 0, maxWidth: '130px' }}>
                <HomeSwitcher
                  currentHome={activeHome}
                  homes={homes}
                  onSelectHome={(homeId) => {
                    setActiveHomeId(homeId);
                    apiClient.setActiveHomeId(homeId);
                    window.dispatchEvent(new Event('home-changed'));
                  }}
                  onCreateNewHome={() => {
                    router.push('/dashboard?action=create_home');
                  }}
                  onJoinHome={() => {
                    router.push('/join');
                  }}
                />
              </div>
            </div>

            {/* Desktop Global Search Bar */}
            <div
              className="ozhzo-header-search ozhzo-desktop-only"
              onClick={() => setIsSearchOpen(true)}
              style={{
                alignItems: 'center',
                gap: '8px',
                width: '100%',
                padding: '6px 14px',
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'var(--color-surface-subtle)',
                border: '1px solid var(--color-border-subtle)',
                cursor: 'pointer',
                fontSize: '13px',
                color: 'var(--color-text-secondary)',
                userSelect: 'none'
              }}
              role="button"
              tabIndex={0}
              aria-label="Open search dialog"
            >
              <Search size={16} />
              <span style={{ flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                Search Home Memory (assets, pantry, chores, bills)...
              </span>
              <kbd style={{ fontSize: '11px', padding: '2px 6px', background: 'var(--color-surface-card)', borderRadius: '4px', border: '1px solid var(--color-border-subtle)' }}>
                Cmd+K
              </kbd>
            </div>
          </div>

          {/* Right Header Action Controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
            {/* Mobile search icon trigger */}
            <button
              className="ozhzo-mobile-only touch-target"
              onClick={() => setIsSearchOpen(true)}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: '8px',
                borderRadius: 'var(--radius-md)',
                color: 'var(--color-text-secondary)'
              }}
              aria-label="Search"
            >
              <Search size={20} />
            </button>

            {/* Global Quick Add Button */}
            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsQuickAddOpen(true)}
              style={{ display: 'flex', alignItems: 'center', gap: '6px', minHeight: '36px', padding: '0 12px' }}
              aria-label="Quick Add to Home"
            >
              <Plus size={16} />
              <span className="ozhzo-desktop-only">Add</span>
            </Button>

            {/* Notifications link with unread dot */}
            <Link
              href="/notifications"
              className="touch-target"
              style={{
                textDecoration: 'none',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: '8px',
                position: 'relative',
                borderRadius: 'var(--radius-md)',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
              aria-label="Notifications"
            >
              <Bell size={20} color="var(--color-text-secondary)" />
              {unreadCount > 0 && (
                <span
                  style={{
                    position: 'absolute',
                    top: '6px',
                    right: '6px',
                    width: '8px',
                    height: '8px',
                    backgroundColor: 'var(--status-low-stock)',
                    borderRadius: '50%'
                  }}
                />
              )}
            </Link>

            {/* User Profile avatar */}
            <Link
              href="/profile"
              className="touch-target"
              style={{
                width: '34px',
                height: '34px',
                borderRadius: '50%',
                backgroundColor: 'var(--color-primary-900)',
                color: 'var(--color-text-inverse)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '13px',
                fontWeight: 600,
                textDecoration: 'none',
                cursor: 'pointer',
                flexShrink: 0
              }}
              aria-label="User Profile"
            >
              {getInitials(userProfile?.display_name)}
            </Link>
          </div>
        </header>

        {/* Page Content */}
        <main
          className="ozhzo-main-container"
          style={{
            flex: 1,
            padding: 'var(--space-6)',
            backgroundColor: 'var(--color-surface-page)',
            overflowY: 'auto',
            overflowX: 'hidden'
          }}
        >
          {children}
        </main>
      </div>

      {/* Mobile Bottom Navigation Bar (< 768px) */}
      <nav
        className="ozhzo-mobile-only"
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          height: '64px',
          backgroundColor: 'var(--color-surface-card)',
          borderTop: '1px solid var(--color-border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-around',
          padding: '0 8px',
          zIndex: 50,
          boxShadow: '0 -2px 10px rgba(0,0,0,0.05)'
        }}
        aria-label="Mobile Navigation"
      >
        {/* 1. Home */}
        <Link
          href="/dashboard"
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '3px',
            flex: 1,
            height: '100%',
            color: pathname === '/dashboard' ? 'var(--color-primary-900)' : 'var(--color-text-secondary)',
            fontWeight: pathname === '/dashboard' ? 700 : 500,
            fontSize: '11px',
            textDecoration: 'none'
          }}
        >
          <LayoutDashboard size={20} color={pathname === '/dashboard' ? 'var(--color-primary-900)' : 'var(--color-text-secondary)'} />
          <span>Home</span>
        </Link>

        {/* 2. Today */}
        <Link
          href="/today"
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '3px',
            flex: 1,
            height: '100%',
            color: pathname === '/today' ? 'var(--color-primary-900)' : 'var(--color-text-secondary)',
            fontWeight: pathname === '/today' ? 700 : 500,
            fontSize: '11px',
            textDecoration: 'none'
          }}
        >
          <CalendarCheck size={20} color={pathname === '/today' ? 'var(--color-primary-900)' : 'var(--color-text-secondary)'} />
          <span>Today</span>
        </Link>

        {/* 3. Central Quick Add Action (+) */}
        <button
          onClick={() => setIsQuickAddOpen(true)}
          style={{
            width: '46px',
            height: '46px',
            borderRadius: '50%',
            backgroundColor: 'var(--color-primary-900)',
            color: '#ffffff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: 'none',
            cursor: 'pointer',
            boxShadow: '0 4px 10px rgba(15, 23, 42, 0.25)',
            transform: 'translateY(-8px)'
          }}
          aria-label="Quick Add"
        >
          <Plus size={24} />
        </button>

        {/* 4. Memory */}
        <Link
          href="/inventory"
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '3px',
            flex: 1,
            height: '100%',
            color: pathname === '/inventory' ? 'var(--color-primary-900)' : 'var(--color-text-secondary)',
            fontWeight: pathname === '/inventory' ? 700 : 500,
            fontSize: '11px',
            textDecoration: 'none'
          }}
        >
          <Package size={20} color={pathname === '/inventory' ? 'var(--color-primary-900)' : 'var(--color-text-secondary)'} />
          <span>Memory</span>
        </Link>

        {/* 5. More (Drawer Toggle) */}
        <button
          onClick={() => setIsMobileMoreOpen(true)}
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '3px',
            flex: 1,
            height: '100%',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: isMobileMoreOpen ? 'var(--color-primary-900)' : 'var(--color-text-secondary)',
            fontWeight: isMobileMoreOpen ? 700 : 500,
            fontSize: '11px'
          }}
          aria-label="Open More Menu"
        >
          <Menu size={20} />
          <span>More</span>
        </button>
      </nav>

      {/* Mobile More Navigation Drawer */}
      {isMobileMoreOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 90,
            display: 'flex',
            alignItems: 'flex-end',
            justifyContent: 'center'
          }}
          onClick={() => setIsMobileMoreOpen(false)}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '500px',
              backgroundColor: 'var(--color-surface-card)',
              borderTopLeftRadius: 'var(--radius-lg)',
              borderTopRightRadius: 'var(--radius-lg)',
              padding: '20px var(--space-4) 30px',
              boxShadow: '0 -10px 25px rgba(0,0,0,0.15)',
              maxHeight: '80vh',
              overflowY: 'auto'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Logo variant="mark" width={24} height={24} />
                <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                  Household Modules
                </h3>
              </div>
              <button
                onClick={() => setIsMobileMoreOpen(false)}
                className="touch-target"
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '6px' }}
                aria-label="Close menu"
              >
                <X size={20} color="var(--color-text-secondary)" />
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {mainNavItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setIsMobileMoreOpen(false)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px',
                      padding: '12px 14px',
                      borderRadius: 'var(--radius-md)',
                      fontSize: '14px',
                      fontWeight: isActive ? 600 : 500,
                      color: isActive ? 'var(--color-text-inverse)' : 'var(--color-text-primary)',
                      backgroundColor: isActive ? 'var(--color-primary-900)' : 'var(--color-surface-subtle)',
                      textDecoration: 'none',
                      minHeight: '44px'
                    }}
                  >
                    <Icon size={20} color={isActive ? 'var(--color-text-inverse)' : 'var(--color-text-secondary)'} />
                    <span style={{ flex: 1 }}>{item.label}</span>
                    <ArrowRight size={14} color={isActive ? 'var(--color-text-inverse)' : 'var(--color-text-tertiary)'} />
                  </Link>
                );
              })}

              <div style={{ borderTop: '1px solid var(--color-border-subtle)', marginTop: '8px', paddingTop: '8px' }}>
                <Link
                  href="/profile"
                  onClick={() => setIsMobileMoreOpen(false)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    padding: '12px 14px',
                    borderRadius: 'var(--radius-md)',
                    fontSize: '14px',
                    fontWeight: 500,
                    color: 'var(--color-text-primary)',
                    backgroundColor: 'var(--color-surface-subtle)',
                    textDecoration: 'none',
                    minHeight: '44px'
                  }}
                >
                  <User size={20} color="var(--color-text-secondary)" />
                  <span style={{ flex: 1 }}>My Profile & Security</span>
                  <ArrowRight size={14} color="var(--color-text-tertiary)" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Global Unified Search Modal */}
      {isSearchOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            zIndex: 100,
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'center',
            paddingTop: '8vh',
            paddingLeft: '12px',
            paddingRight: '12px'
          }}
          onClick={() => setIsSearchOpen(false)}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '600px',
              backgroundColor: 'var(--color-surface-card)',
              borderRadius: 'var(--radius-lg)',
              boxShadow: '0 20px 25px -5px rgba(0,0,0,0.15)',
              overflow: 'hidden',
              maxHeight: '80vh',
              display: 'flex',
              flexDirection: 'column'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'center', padding: '14px 18px', borderBottom: '1px solid var(--color-border-subtle)', gap: '10px' }}>
              <Search size={20} color="var(--color-text-secondary)" />
              <input
                type="text"
                autoFocus
                placeholder="Search tools, pantry stock, bills, chores, locations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{ flex: 1, border: 'none', outline: 'none', fontSize: '15px', backgroundColor: 'transparent' }}
                aria-label="Search items"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px', color: 'var(--color-text-tertiary)' }}
                  aria-label="Clear search input"
                >
                  <X size={16} />
                </button>
              )}
              <button
                onClick={() => setIsSearchOpen(false)}
                className="touch-target"
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '6px' }}
                aria-label="Close search"
              >
                <X size={18} color="var(--color-text-secondary)" />
              </button>
            </div>

            <div style={{ padding: '16px', overflowY: 'auto', flex: 1, fontSize: '13px', color: 'var(--color-text-secondary)' }}>
              {isSearching ? (
                <div style={{ textAlign: 'center', padding: '24px' }}>
                  <p>Searching Home Memory...</p>
                </div>
              ) : searchQuery.trim().length === 0 ? (
                <div style={{ textAlign: 'center', padding: '24px' }}>
                  <p style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>Type to search your entire Home Memory.</p>
                  <p style={{ fontSize: '12px', marginTop: '6px' }}>
                    Quick examples: <em>&ldquo;Drill&rdquo;</em>, <em>&ldquo;Rice&rdquo;</em>, <em>&ldquo;Electricity&rdquo;</em>, <em>&ldquo;Keys&rdquo;</em>.
                  </p>
                </div>
              ) : searchResults.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '24px' }}>
                  <p style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>No matching items found.</p>
                  <p style={{ fontSize: '12px', marginTop: '4px' }}>Try a different keyword or location path.</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {searchResults.map((res) => (
                    <div
                      key={`${res.domain}-${res.id}`}
                      onClick={() => handleSearchResultClick(res.navigation_target)}
                      style={{
                        padding: '12px 14px',
                        borderRadius: 'var(--radius-md)',
                        background: 'var(--color-surface-subtle)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: '10px',
                        transition: 'background-color 0.15s ease'
                      }}
                    >
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <Badge variant="neutral">{res.domain}</Badge>
                          <span style={{ fontWeight: 600, color: 'var(--color-text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {res.title}
                          </span>
                        </div>
                        {res.subtitle && (
                          <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
                            {res.subtitle}
                          </div>
                        )}
                      </div>
                      <ArrowRight size={14} color="var(--color-text-tertiary)" />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Global Quick Add Modal */}
      {isQuickAddOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px'
          }}
          onClick={() => setIsQuickAddOpen(false)}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '480px',
              backgroundColor: 'var(--color-surface-card)',
              borderRadius: 'var(--radius-lg)',
              padding: '20px',
              boxShadow: '0 20px 25px -5px rgba(0,0,0,0.15)',
              maxHeight: '90vh',
              overflowY: 'auto'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-primary-900)' }}>Quick Add to Home</h3>
                <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>Select category to log new household entry</p>
              </div>
              <button
                onClick={() => setIsQuickAddOpen(false)}
                className="touch-target"
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '6px' }}
                aria-label="Close Quick Add dialog"
              >
                <X size={20} color="var(--color-text-secondary)" />
              </button>
            </div>

            <div
              className="ozhzo-responsive-form-grid"
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '10px'
              }}
            >
              <Link
                href="/tasks"
                onClick={() => setIsQuickAddOpen(false)}
                style={{
                  padding: '14px',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--color-surface-subtle)',
                  textAlign: 'center',
                  textDecoration: 'none',
                  color: 'var(--color-text-primary)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                  minHeight: '64px',
                  justifyContent: 'center'
                }}
              >
                <div style={{ fontSize: '14px', fontWeight: 700 }}>🧹 + Task</div>
                <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>Add chore or routine</div>
              </Link>

              <Link
                href="/shopping"
                onClick={() => setIsQuickAddOpen(false)}
                style={{
                  padding: '14px',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--color-surface-subtle)',
                  textAlign: 'center',
                  textDecoration: 'none',
                  color: 'var(--color-text-primary)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                  minHeight: '64px',
                  justifyContent: 'center'
                }}
              >
                <div style={{ fontSize: '14px', fontWeight: 700 }}>🛒 + Purchase</div>
                <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>Add shopping item</div>
              </Link>

              <Link
                href="/inventory"
                onClick={() => setIsQuickAddOpen(false)}
                style={{
                  padding: '14px',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--color-surface-subtle)',
                  textAlign: 'center',
                  textDecoration: 'none',
                  color: 'var(--color-text-primary)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                  minHeight: '64px',
                  justifyContent: 'center'
                }}
              >
                <div style={{ fontSize: '14px', fontWeight: 700 }}>🍚 + Pantry Stock</div>
                <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>Record consumable supply</div>
              </Link>

              <Link
                href="/inventory"
                onClick={() => setIsQuickAddOpen(false)}
                style={{
                  padding: '14px',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--color-surface-subtle)',
                  textAlign: 'center',
                  textDecoration: 'none',
                  color: 'var(--color-text-primary)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                  minHeight: '64px',
                  justifyContent: 'center'
                }}
              >
                <div style={{ fontSize: '14px', fontWeight: 700 }}>🔧 + Home Asset</div>
                <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>Record durable tool/key</div>
              </Link>

              <Link
                href="/bills"
                onClick={() => setIsQuickAddOpen(false)}
                style={{
                  padding: '14px',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--color-surface-subtle)',
                  textAlign: 'center',
                  textDecoration: 'none',
                  color: 'var(--color-text-primary)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                  minHeight: '64px',
                  justifyContent: 'center'
                }}
              >
                <div style={{ fontSize: '14px', fontWeight: 700 }}>⚡ + Bill</div>
                <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>Track domestic expense</div>
              </Link>

              <Link
                href="/calendar"
                onClick={() => setIsQuickAddOpen(false)}
                style={{
                  padding: '14px',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--color-surface-subtle)',
                  textAlign: 'center',
                  textDecoration: 'none',
                  color: 'var(--color-text-primary)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                  minHeight: '64px',
                  justifyContent: 'center'
                }}
              >
                <div style={{ fontSize: '14px', fontWeight: 700 }}>🎂 + Event</div>
                <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>Add schedule or trip</div>
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
