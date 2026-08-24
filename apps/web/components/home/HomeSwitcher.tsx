'use client';

import React, { useState } from 'react';
import { ChevronDown, Home as HomeIcon, Plus } from 'lucide-react';

interface HomeOption {
  home_id: string;
  name: string;
  role: string;
}

interface HomeSwitcherProps {
  currentHome?: HomeOption;
  homes: HomeOption[];
  onSelectHome: (homeId: string) => void;
  onCreateNewHome?: () => void;
  onJoinHome?: () => void;
}

export const HomeSwitcher: React.FC<HomeSwitcherProps> = ({
  currentHome,
  homes,
  onSelectHome,
  onCreateNewHome,
  onJoinHome
}) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div style={{ position: 'relative', display: 'inline-block', maxWidth: '100%', minWidth: 0 }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        id="home-switcher-dropdown-btn"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '6px 10px',
          backgroundColor: 'var(--color-surface-subtle)',
          border: '1px solid var(--color-border-subtle)',
          borderRadius: 'var(--radius-md)',
          cursor: 'pointer',
          fontWeight: 600,
          fontSize: '13px',
          color: 'var(--color-text-primary)',
          maxWidth: '100%',
          minWidth: 0,
          overflow: 'hidden'
        }}
      >
        <HomeIcon size={15} color="var(--color-primary-900)" style={{ flexShrink: 0 }} />
        <span id="current-active-home-name" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', minWidth: 0, flex: 1 }}>
          {currentHome?.name || 'Select Home'}
        </span>
        <ChevronDown size={13} color="var(--color-text-secondary)" style={{ flexShrink: 0 }} />
      </button>

      {isOpen && (
        <div
          id="home-switcher-menu"
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            marginTop: '6px',
            width: '240px',
            backgroundColor: 'var(--color-surface-overlay)',
            border: '1px solid var(--color-border-subtle)',
            borderRadius: 'var(--radius-lg)',
            boxShadow: 'var(--shadow-floating)',
            padding: '6px',
            zIndex: 100
          }}
        >
          <div style={{ padding: '6px 8px', fontSize: '11px', fontWeight: 600, color: 'var(--color-text-tertiary)', textTransform: 'uppercase' }}>
            Your Households
          </div>
          {homes.map((h) => (
            <button
              key={h.home_id}
              onClick={() => {
                onSelectHome(h.home_id);
                setIsOpen(false);
              }}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 10px',
                border: 'none',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: currentHome?.home_id === h.home_id ? 'var(--color-surface-subtle)' : 'transparent',
                cursor: 'pointer',
                textAlign: 'left',
                fontSize: '13px',
                color: 'var(--color-text-primary)'
              }}
            >
              <span style={{ fontWeight: currentHome?.home_id === h.home_id ? 600 : 400 }}>{h.name}</span>
              <span style={{ fontSize: '11px', color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>{h.role}</span>
            </button>
          ))}

          {(onCreateNewHome || onJoinHome) && (
            <div style={{ borderTop: '1px solid var(--color-border-subtle)', marginTop: '4px', paddingTop: '4px' }}>
              {onCreateNewHome && (
                <button
                  onClick={() => {
                    onCreateNewHome();
                    setIsOpen(false);
                  }}
                  id="switcher-create-home-btn"
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '8px 10px',
                    border: 'none',
                    backgroundColor: 'transparent',
                    cursor: 'pointer',
                    fontSize: '13px',
                    fontWeight: 600,
                    color: 'var(--color-accent-warm)',
                    borderRadius: 'var(--radius-sm)'
                  }}
                >
                  <Plus size={14} />
                  <span>Create New Home</span>
                </button>
              )}
              {onJoinHome && (
                <button
                  onClick={() => {
                    onJoinHome();
                    setIsOpen(false);
                  }}
                  id="switcher-join-home-btn"
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '8px 10px',
                    border: 'none',
                    backgroundColor: 'transparent',
                    cursor: 'pointer',
                    fontSize: '13px',
                    fontWeight: 600,
                    color: 'var(--color-text-secondary)',
                    borderRadius: 'var(--radius-sm)'
                  }}
                >
                  <HomeIcon size={14} />
                  <span>Join a Home</span>
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
