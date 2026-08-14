# Design System & UI Component Specification — Ozhzo Verse

*Document Classification: Definitive Source of Truth*  
*Target Platforms: Web (Next.js 14+ / CSS Variables) & Mobile (Flutter 3.x Theme Tokens)*  
*Target Audience: UI/UX Designers, Frontend Engineers, Mobile Engineers, QA Engineers*

---

## 1. Brand Identity & Visual Language

Ozhzo Verse is the **Digital Operating System for Homes**.
Our visual personality blends domestic warmth with architectural precision:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BRAND PERSONALITY SPECTRUM                         │
├──────────────────────┬──────────────────────┬───────────────────────────────┤
│ • MODERN & MINIMAL   │ • WARM & HARMONIOUS  │ • TRUSTWORTHY & CALM          │
│ Uncluttered, clean   │ Organic warm neutrals│ Reliable, predictable, and    │
│ lines, generous      │ (slate, terracotta,  │ non-intrusive. Reduces mental │
│ whitespace.          │ soft sage, oat).     │ stress instead of adding it.  │
├──────────────────────┴──────────────────────┴───────────────────────────────┤
│ • FAMILY-FRIENDLY & ACCESSIBLE              │ • PREMIUM BUT APPROACHABLE    │
│ High legibility, multi-generational clarity.│ Meticulously crafted feel.    │
└─────────────────────────────────────────────┴───────────────────────────────┘
```

---

## 2. Color System & Design Tokens

### 2.1. Light Mode Tokens (Primary Canvas)

```css
:root {
  /* Neutral Canvas & Surfaces */
  --color-bg-canvas: hsl(210, 40%, 98%);       /* #F8FAFC - Main App Canvas */
  --color-surface-card: hsl(0, 0%, 100%);      /* #FFFFFF - Base Cards & Sheets */
  --color-surface-subtle: hsl(210, 40%, 96%);    /* #F1F5F9 - Inactive Tabs, Pills */
  --color-surface-overlay: hsl(0, 0%, 100%);   /* #FFFFFF - Modals & Dropdowns */

  /* Text & Typography */
  --color-text-primary: hsl(222, 47%, 11%);    /* #0F172A - Main Headings & Body */
  --color-text-secondary: hsl(215, 16%, 47%);  /* #64748B - Subtitles, Captions */
  --color-text-tertiary: hsl(215, 16%, 65%);   /* #94A3B8 - Placeholder Text */
  --color-text-inverse: hsl(0, 0%, 100%);      /* #FFFFFF - Text on Dark CTA */

  /* Borders & Dividers */
  --color-border-subtle: hsl(214, 32%, 91%);   /* #E2E8F0 - Card Borders */
  --color-border-strong: hsl(215, 20%, 75%);   /* #CBD5E1 - Input Outlines */

  /* Primary Brand (Deep Slate Navy) */
  --color-primary-900: hsl(222, 47%, 11%);     /* #0F172A - Primary CTAs */
  --color-primary-700: hsl(221, 39%, 22%);     /* #1E293B - Primary Hover */
  --color-primary-100: hsl(214, 32%, 91%);     /* #F1F5F9 - Subtle Active */

  /* Accent (Warm Terracotta / Amber) */
  --color-accent-terracotta: hsl(24, 95%, 53%); /* #F97316 - Accent Warmth */
  --color-accent-amber: hsl(38, 92%, 50%);      /* #F59E0B - Alerts & Streaks */

  /* Domain Status Colors */
  --status-in-stock: hsl(158, 64%, 40%);        /* #10B981 - Green: Fresh, In Stock */
  --status-in-stock-bg: hsl(152, 76%, 96%);     /* #ECFDF5 - Green Subtle Pill */
  
  --status-low-stock: hsl(38, 92%, 50%);        /* #F59E0B - Amber: Low, Due Soon */
  --status-low-stock-bg: hsl(48, 100%, 96%);    /* #FFFBEB - Amber Subtle Pill */
  
  --status-overdue: hsl(0, 84%, 60%);           /* #EF4444 - Red: Overdue, Expired */
  --status-overdue-bg: hsl(0, 100%, 97%);       /* #FEF2F2 - Red Subtle Pill */
  
  --status-completed: hsl(173, 80%, 40%);       /* #0D9488 - Teal: Done, Settled */
  --status-completed-bg: hsl(168, 76%, 96%);    /* #F0FDFA - Teal Subtle Pill */

  --color-calendar-event: hsl(239, 84%, 67%);   /* #6366F1 - Indigo: Events */
}
```

### 2.2. Dark Mode Tokens

```css
[data-theme='dark'] {
  --color-bg-canvas: hsl(222, 47%, 7%);        /* #090D16 - Deep Dark Canvas */
  --color-surface-card: hsl(222, 47%, 11%);     /* #0F172A - Dark Card Surface */
  --color-surface-subtle: hsl(217, 33%, 17%);   /* #1E293B - Dark Inactive Tabs */
  
  --color-text-primary: hsl(210, 40%, 98%);     /* #F8FAFC - Bright Headings */
  --color-text-secondary: hsl(215, 20%, 65%);   /* #94A3B8 - Muted Subtitles */
  --color-border-subtle: hsl(217, 33%, 20%);    /* #1E293B - Card Border */
  
  --color-primary-900: hsl(210, 40%, 98%);      /* Inverted White Primary */
  --color-text-inverse: hsl(222, 47%, 11%);     /* Dark Text on Bright CTA */
}
```

---

## 3. Typography Scale

**Primary Typeface**: `Plus Jakarta Sans` (System Fallback: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`).

| Token | Size | Line Height | Weight | Letter Spacing | Use Case |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `font-display` | `2.25rem` (36px) | `2.75rem` (44px) | 700 (Bold) | `-0.02em` | Marketing / Onboarding Headlines |
| `font-h1` | `1.75rem` (28px) | `2.25rem` (36px) | 700 (Bold) | `-0.015em` | Page Titles, Dashboard Welcome |
| `font-h2` | `1.25rem` (20px) | `1.75rem` (28px) | 600 (SemiBold) | `-0.01em` | Section Headers, Card Titles |
| `font-h3` | `1.00rem` (16px) | `1.50rem` (24px) | 600 (SemiBold) | `0em` | Modal Titles, Task Names |
| `font-body` | `0.9375rem` (15px) | `1.50rem` (24px) | 400 (Regular) | `0em` | Default Body Text, Form Labels |
| `font-body-medium`| `0.9375rem` (15px) | `1.50rem` (24px) | 500 (Medium) | `0em` | List Items, Interactive Text |
| `font-caption` | `0.8125rem` (13px) | `1.125rem` (18px)| 500 (Medium) | `+0.01em` | Due Dates, Subtitles, Meta Info |
| `font-micro` | `0.6875rem` (11px) | `0.875rem` (14px)| 600 (SemiBold) | `+0.02em` | Status Badges, Priority Pills |

---

## 4. Spacing Scale (4px Baseline Grid)

```css
--space-1: 4px;   /* Micro spacing, badge padding */
--space-2: 8px;   /* Tight element gap, icon-to-label */
--space-3: 12px;  /* Form field inner padding */
--space-4: 16px;  /* Standard container / card padding */
--space-5: 20px;  /* Stack gap */
--space-6: 24px;  /* Section gutters */
--space-8: 32px;  /* Module separation */
--space-12: 48px; /* Page boundary padding */
```

---

## 5. Grid & Responsive Layout System

- **Desktop Layout (> 1024px)**: 12-Column fluid grid, max-width `1280px`, persistent 240px sidebar.
- **Tablet Layout (640px – 1024px)**: 8-Column fluid grid, 16px gutters, collapsible drawer.
- **Mobile Layout (< 640px)**: 4-Column fluid grid, 16px page margins, single vertical flow.

---

## 6. Border Radii & Elevation

### Border Radii Tokens:
- `--radius-sm`: `6px` (Checkboxes, micro tags, tooltips)
- `--radius-md`: `10px` (Input fields, primary buttons, dropdowns)
- `--radius-lg`: `16px` (Standard cards, modals, bottom sheets)
- `--radius-full`: `9999px` (Avatars, pill badges, FABs)

### Elevation & Shadows:
```css
--shadow-subtle: 0 1px 2px 0 rgba(15, 23, 42, 0.04);
--shadow-card: 0 4px 6px -1px rgba(15, 23, 42, 0.06), 0 2px 4px -1px rgba(15, 23, 42, 0.03);
--shadow-floating: 0 10px 15px -3px rgba(15, 23, 42, 0.08), 0 4px 6px -2px rgba(15, 23, 42, 0.04);
--shadow-modal: 0 20px 25px -5px rgba(15, 23, 42, 0.12), 0 10px 10px -5px rgba(15, 23, 42, 0.04);
```

---

## 7. Component Specifications

### 7.1. Buttons
- **Variants**:
  - `Primary`: Solid navy background (`--color-primary-900`), white text, `radius-md`, subtle active scale (`0.98`).
  - `Secondary / Outline`: Transparent background, subtle border (`--color-border-strong`), dark text.
  - `Ghost`: Borderless, subtle hover background (`--color-surface-subtle`).
  - `Destructive`: Soft crimson background (`--status-overdue-bg`), red text (`--status-overdue`).
- **Touch Target**: Minimum `44px` height on mobile.

### 7.2. Form Inputs & Steppers
- **Text Inputs**: Height `44px`, 1px border (`--color-border-strong`), `10px` radius, focus ring (`2px solid --color-primary-900`).
- **Quantity Stepper**: Compact `[-] [ 2.0 pcs ] [+]` with tactile spring animation on tap.
- **Checkboxes**: Tactile `24x24px` target box with smooth check transition and strikethrough effect.

### 7.3. Cards & Surfaces
- **Base Card**: White surface (`--color-surface-card`), 1px subtle border (`--color-border-subtle`), 16px radius (`--radius-lg`), 16px padding.
- **Interactive Card**: Base card with hover elevation transition (`translateY(-2px)` + `--shadow-floating`).

### 7.4. Navigation & Home Switcher
- **Home Switcher**: Pill-shaped header button displaying active Home icon, Name, and chevron. Clicking opens home picker modal.
- **Mobile Bottom Bar**: 5 items (`Home`, `Shop`, `Tasks`, `Pantry`, `More`) with 12px active dot indicator and haptic feedback.

### 7.5. Dialogs, Modals & Sheets
- **Center Modal (Web)**: Max width `520px`, centered with backdrop blur (`backdrop-filter: blur(4px)`).
- **Bottom Sheet (Mobile)**: Draggable bottom sheet with swipe-down dismissal and safe-area padding.

### 7.6. Toasts & Feedback
- **Toast**: Floating pill at top-right (Web) or bottom-center (Mobile) with 4-second auto-dismiss.
- **Variants**: Success (Green icon), Error (Red icon), Info (Navy icon).

### 7.7. Status Badges & Pills
- **In Stock**: Emerald Green text on light green pill (`--status-in-stock-bg`).
- **Low Stock**: Amber text on soft amber pill (`--status-low-stock-bg`).
- **Overdue**: Crimson text on soft red pill (`--status-overdue-bg`).
- **Chore Priority**: `HIGH` / `URGENT` indicated by warm terracotta micro-dot.

### 7.8. Empty States
- **Design Pattern**: Warm domestic illustration (not corporate clip-art), concise heading, 1-line explanatory subtitle, and a prominent primary action button.

### 7.9. Loading States & Shimmer Skeletons
- **Rule**: Never show raw blank screens or blocking full-screen spinners for content loads.
- **Shimmer Animation**: 1.5s gentle pulse on rounded skeleton rectangles matching card layout.

### 7.10. Error States
- **Inline Field Errors**: Displayed directly below input in crimson (`--status-overdue`) with micro warning icon.
- **Network Retry Banner**: Non-blocking toast: *"Connection lost. Retrying in background..."* with manual "Retry" CTA.

---

## 8. Accessibility (a11y) & Usability Standards

1. **Color Contrast**: All text-to-background combinations exceed WCAG 2.1 AA minimum contrast of **4.5:1** (Bold titles exceed **7:1**).
2. **Touch Targets**: Minimum interactive touch targets of **44x44 points** on mobile Flutter controls.
3. **Screen Readers & ARIA**: All icons have `aria-label` or `Semantics(label: ...)` in Flutter.
4. **Keyboard Navigation**: Complete tab-order focus rings across all web interactive components.
5. **No Motion Sensitivity**: Respects `prefers-reduced-motion` media queries by disabling non-essential transitions.
