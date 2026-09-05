'use client';

import React, { useState, useRef, useEffect, useMemo } from 'react';
import { ChevronDown, Search, Check, X } from 'lucide-react';

export interface RegionConfig {
  id: string;
  country_code: string;
  country_name: string;
  region: string;
  currency: string;
  default_plan_code?: string;
  payment_gateway?: string;
  tax_percentage?: number | string;
  is_active: boolean;
  is_default?: boolean;
  promotional_eligibility_enabled?: boolean;
  metadata_json?: Record<string, any>;
}

export function getCountryFlag(iso2: string): string {
  if (!iso2) return '🌐';
  const code = iso2.trim().toUpperCase();
  if (code === 'GLOBAL' || code === 'GLB' || code === 'ALL' || code === '') return '🌍';
  if (code.length !== 2) return '🌐';
  const first = code.charCodeAt(0) - 65 + 0x1f1e6;
  const second = code.charCodeAt(1) - 65 + 0x1f1e6;
  if (first < 0x1f1e6 || first > 0x1f1ff || second < 0x1f1e6 || second > 0x1f1ff) return '🌐';
  return String.fromCodePoint(first, second);
}

export interface ControlledCountrySelectorProps {
  value: string; // e.g. "DE" or "IN,AE" or "GLOBAL" or ""
  onChange: (value: string) => void;
  regions: RegionConfig[];
  disabled?: boolean;
  allowMultiple?: boolean;
  testId?: string;
  inputTestId?: string;
  placeholder?: string;
  isEdit?: boolean;
}

export const ControlledCountrySelector: React.FC<ControlledCountrySelectorProps> = ({
  value,
  onChange,
  regions,
  disabled = false,
  allowMultiple = false,
  testId = 'controlled-country-selector',
  inputTestId = 'controlled-country-input',
  placeholder = 'Select country / region...',
  isEdit = false
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Close when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      setTimeout(() => {
        searchInputRef.current?.focus();
      }, 50);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  // Parse currently selected codes
  const selectedCodes = useMemo(() => {
    if (!value || value.trim() === '' || value.toUpperCase() === 'GLOBAL') {
      return [];
    }
    return value
      .split(',')
      .map((c) => c.trim().toUpperCase())
      .filter(Boolean);
  }, [value]);

  const isGlobal = selectedCodes.length === 0 || value.toUpperCase() === 'GLOBAL';

  // Filtered regions list from Country Master (excluding separate GLOBAL item which is handled as top choice)
  const availableRegions = useMemo(() => {
    return regions.filter((r) => r.country_code.toUpperCase() !== 'GLOBAL');
  }, [regions]);

  const filteredRegions = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return availableRegions;
    return availableRegions.filter((r) => {
      const nameMatch = (r.country_name || '').toLowerCase().includes(q);
      const codeMatch = (r.country_code || '').toLowerCase().includes(q);
      const currMatch = (r.currency || '').toLowerCase().includes(q);
      const regMatch = (r.region || '').toLowerCase().includes(q);
      return nameMatch || codeMatch || currMatch || regMatch;
    });
  }, [availableRegions, searchQuery]);

  const handleSelectGlobal = () => {
    onChange('');
    setIsOpen(false);
    setSearchQuery('');
  };

  const handleSelectRegion = (region: RegionConfig) => {
    if (!region.is_active && !isEdit) {
      return; // Disabled for new targeting
    }

    const code = region.country_code.toUpperCase();

    if (allowMultiple) {
      if (selectedCodes.includes(code)) {
        const next = selectedCodes.filter((c) => c !== code);
        onChange(next.join(','));
      } else {
        const next = [...selectedCodes, code];
        onChange(next.join(','));
      }
    } else {
      onChange(code);
      setIsOpen(false);
      setSearchQuery('');
    }
  };

  const handleRemoveCode = (codeToRemove: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const next = selectedCodes.filter((c) => c !== codeToRemove);
    onChange(next.join(','));
  };

  // Find region object by code
  const getRegionByCode = (code: string): RegionConfig | undefined => {
    return regions.find((r) => r.country_code.toUpperCase() === code.toUpperCase());
  };

  return (
    <div ref={containerRef} style={{ position: 'relative', width: '100%' }}>
      {/* Hidden input for synthetic form and automated test payload inspection */}
      <input
        type="text"
        data-testid={inputTestId}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{ position: 'absolute', opacity: 0, pointerEvents: 'none', height: 0, width: 0 }}
        tabIndex={-1}
        readOnly
      />

      {/* Main Trigger Button */}
      <div
        data-testid={testId}
        onClick={() => {
          if (!disabled) setIsOpen(!isOpen);
        }}
        style={{
          width: '100%',
          minHeight: '42px',
          padding: '8px 12px',
          borderRadius: 'var(--radius-md, 10px)',
          border: isOpen ? '1.5px solid #2563eb' : '1px solid var(--color-border-subtle, #cbd5e1)',
          backgroundColor: disabled ? '#f8fafc' : '#ffffff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: disabled ? 'not-allowed' : 'pointer',
          boxShadow: isOpen ? '0 0 0 3px rgba(37, 99, 235, 0.1)' : 'none',
          transition: 'all 0.15s ease',
          gap: '8px',
          userSelect: 'none'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', flex: 1 }}>
          {isGlobal ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13.5px', fontWeight: 600, color: '#0f172a' }}>
              <span>🌍</span>
              <span>Global / All Countries — GLOBAL — Multi-Currency</span>
            </div>
          ) : selectedCodes.length === 1 ? (
            (() => {
              const code = selectedCodes[0];
              const reg = getRegionByCode(code);
              const flag = getCountryFlag(code);
              return (
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13.5px', fontWeight: 600, color: '#0f172a' }}>
                  <span>{flag}</span>
                  <span>
                    {reg ? `${reg.country_name} — ${reg.country_code} — ${reg.currency}` : `${code} — ${code}`}
                  </span>
                  {reg && !reg.is_active && (
                    <span style={{ fontSize: '11px', color: '#ef4444', backgroundColor: '#fef2f2', padding: '2px 6px', borderRadius: '4px', border: '1px solid #fecaca' }}>
                      Deactivated
                    </span>
                  )}
                </div>
              );
            })()
          ) : (
            selectedCodes.map((code) => {
              const reg = getRegionByCode(code);
              const flag = getCountryFlag(code);
              return (
                <span
                  key={code}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    padding: '3px 8px',
                    borderRadius: '6px',
                    backgroundColor: '#eff6ff',
                    border: '1px solid #bfdbfe',
                    color: '#1d4ed8',
                    fontSize: '12px',
                    fontWeight: 600
                  }}
                >
                  <span>{flag}</span>
                  <span>{reg ? reg.country_name : code} ({code})</span>
                  <X
                    size={13}
                    onClick={(e) => handleRemoveCode(code, e)}
                    style={{ cursor: 'pointer', marginLeft: '2px' }}
                  />
                </span>
              );
            })
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#64748b' }}>
          {!isGlobal && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                handleSelectGlobal();
              }}
              title="Reset to Global"
              style={{
                border: 'none',
                background: 'transparent',
                cursor: 'pointer',
                padding: '2px',
                display: 'flex',
                alignItems: 'center',
                color: '#94a3b8'
              }}
            >
              <X size={15} />
            </button>
          )}
          <ChevronDown size={16} style={{ transform: isOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
        </div>
      </div>

      {/* Searchable Dropdown Popover */}
      {isOpen && (
        <div
          data-testid="country-selector-dropdown"
          style={{
            position: 'absolute',
            top: 'calc(100% + 4px)',
            left: 0,
            right: 0,
            zIndex: 9999,
            backgroundColor: '#ffffff',
            borderRadius: '12px',
            border: '1px solid #cbd5e1',
            boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
            overflow: 'hidden',
            maxHeight: '340px',
            display: 'flex',
            flexDirection: 'column'
          }}
        >
          {/* Search Input Bar */}
          <div style={{ padding: '8px 12px', borderBottom: '1px solid #f1f5f9', display: 'flex', alignItems: 'center', gap: '8px', backgroundColor: '#f8fafc' }}>
            <Search size={15} color="#64748b" />
            <input
              ref={searchInputRef}
              data-testid="country-selector-search-input"
              type="text"
              placeholder={placeholder || "Search country, ISO-2 (e.g. DE, IN), currency..."}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                border: 'none',
                outline: 'none',
                background: 'transparent',
                width: '100%',
                fontSize: '13px',
                color: '#0f172a'
              }}
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: '#94a3b8' }}
              >
                <X size={14} />
              </button>
            )}
          </div>

          {/* Options List */}
          <div style={{ overflowY: 'auto', flex: 1, padding: '4px' }}>
            {/* 1. Global Option */}
            {(!searchQuery || 'global'.includes(searchQuery.toLowerCase()) || 'all'.includes(searchQuery.toLowerCase())) && (
              <div
                data-testid="country-option-GLOBAL"
                onClick={handleSelectGlobal}
                style={{
                  padding: '9px 12px',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  cursor: 'pointer',
                  backgroundColor: isGlobal ? '#f1f5f9' : 'transparent',
                  fontWeight: isGlobal ? 700 : 500,
                  fontSize: '13px',
                  color: '#0f172a',
                  marginBottom: '2px'
                }}
                onMouseEnter={(e) => {
                  if (!isGlobal) e.currentTarget.style.backgroundColor = '#f8fafc';
                }}
                onMouseLeave={(e) => {
                  if (!isGlobal) e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '16px' }}>🌍</span>
                  <div>
                    <span>Global / All Countries</span>
                    <span style={{ color: '#64748b', fontSize: '11px', marginLeft: '6px' }}>— GLOBAL — Multi-Currency</span>
                  </div>
                </div>
                {isGlobal && <Check size={16} color="#2563eb" />}
              </div>
            )}

            <div style={{ height: '1px', backgroundColor: '#f1f5f9', margin: '4px 0' }} />

            {/* Dynamic Configured Regions */}
            {filteredRegions.length === 0 ? (
              <div style={{ padding: '16px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
                No configured countries match "{searchQuery}".
              </div>
            ) : (
              filteredRegions.map((region) => {
                const isSelected = selectedCodes.includes(region.country_code.toUpperCase());
                const flag = getCountryFlag(region.country_code);
                const isDeactivated = !region.is_active;

                return (
                  <div
                    key={region.id || region.country_code}
                    data-testid={`country-option-${region.country_code}`}
                    onClick={() => handleSelectRegion(region)}
                    style={{
                      padding: '9px 12px',
                      borderRadius: '8px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: isDeactivated && !isEdit ? 'not-allowed' : 'pointer',
                      opacity: isDeactivated && !isEdit ? 0.6 : 1,
                      backgroundColor: isSelected ? '#eff6ff' : 'transparent',
                      fontWeight: isSelected ? 700 : 500,
                      fontSize: '13px',
                      color: isSelected ? '#1d4ed8' : '#0f172a',
                      marginBottom: '2px'
                    }}
                    onMouseEnter={(e) => {
                      if (!isSelected && (!isDeactivated || isEdit)) {
                        e.currentTarget.style.backgroundColor = '#f8fafc';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isSelected) {
                        e.currentTarget.style.backgroundColor = 'transparent';
                      }
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '16px' }}>{flag}</span>
                      <div>
                        <span>{region.country_name}</span>
                        <span style={{ color: '#64748b', fontSize: '11px', marginLeft: '6px' }}>
                          — {region.country_code} — {region.currency}
                        </span>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {isDeactivated && (
                        <span
                          style={{
                            fontSize: '10px',
                            fontWeight: 700,
                            padding: '2px 5px',
                            borderRadius: '4px',
                            backgroundColor: '#fef2f2',
                            color: '#ef4444',
                            border: '1px solid #fecaca'
                          }}
                        >
                          Deactivated
                        </span>
                      )}
                      {isSelected && <Check size={16} color="#2563eb" />}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
};
