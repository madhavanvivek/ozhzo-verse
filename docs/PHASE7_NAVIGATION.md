# Ozhzo Verse — Phase 7: Unified Navigation Architecture

## 1. Multi-Platform Navigation Matrix

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             WEB SIDEBAR & HEADER                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ Top Bar:  [ 🏠 Home Switcher ▾ ]   [ 🔍 Search Home (Cmd+K) ]   [ + Add ]   │
│ Sidebar:  • 🏠 Dashboard                                                    │
│           • 📅 Today & Calendar                                             │
│           • 📦 Home Memory (Inventory & Assets)                             │
│           • 🛒 Purchase List                                                │
│           • 🧹 Tasks & Chores                                               │
│           • ⚡ Bills & Expenses                                             │
│           • ⚙️ Home Settings                                                │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                             MOBILE BOTTOM BAR (5 TABS)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│   [ 🏠 Home ]   [ 📅 Today ]   [ ➕ Add ]   [ 📦 Memory ]   [ ☰ More ]       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Multi-Home Switching Semantics
- **Persistent Header Anchor**: The active Home is always prominently displayed in the top header on both Web and Mobile.
- **Strict Scope Isolation**: Switching Homes in the switcher instantly resets all local state, invalidates cached queries, and executes clean queries anchored to the new `home_id`.
- **Zero Cross-Home Confusion**: All views, search queries, and quick adds execute strictly within the active Home scope.
