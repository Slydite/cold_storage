# UI Design Spec — Cold Storage Management System

Derived from approved mockups (dashboard, GRN list, create-GRN panel). This is the visual contract agents should build to — treat deviations from it as bugs, not creative freedom.

**Both light and dark mode are required, togglable at runtime (not a build-time choice).** They are not simple inverted palettes — each has its own accent identity (see §1). Persist the user's choice (local state / user preference), default to system preference on first load.

---

## 1. Color tokens

Two themes, one shared semantic layer (status colors) that stays consistent across both.

### Dark theme
| Token | Value | Usage |
|---|---|---|
| `--bg-page` | `#0E0A1E` | app background, near-black with a violet tint |
| `--bg-sidebar` | `#150F2A` | sidebar, slightly lifted off page bg |
| `--bg-surface` | `#1B1533` | cards, table containers, panels |
| `--bg-surface-hover` | `#241D42` | row hover, list hover |
| `--border-subtle` | `rgba(255,255,255,0.08)` | card borders, dividers |
| `--text-primary` | `#F5F3FF` | headings, primary values |
| `--text-secondary` | `#9C92B8` | labels, muted copy, timestamps |
| `--accent-primary` | `#8B5CF6` | brand accent — active nav, primary buttons, chart stroke, focus ring |
| `--accent-primary-hover` | `#7C3AED` | |

### Light theme
| Token | Value | Usage |
|---|---|---|
| `--bg-page` | `#F7F7FB` | app background |
| `--bg-sidebar` | `#FFFFFF` | sidebar |
| `--bg-surface` | `#FFFFFF` | cards, panels |
| `--bg-surface-hover` | `#F4F4F8` | row/list hover |
| `--border-subtle` | `rgba(15,15,25,0.08)` | card borders, dividers |
| `--text-primary` | `#1B1B23` | headings, primary values |
| `--text-secondary` | `#6B6B7A` | labels, muted copy |
| `--accent-primary` | `#F97316` | brand accent — active nav, primary buttons, chart stroke, focus ring |
| `--accent-primary-hover` | `#EA6A0C` | |

### Shared semantic tokens (identical in both themes — status meaning must never shift with theme)
| Token | Dark value | Light value | Usage |
|---|---|---|---|
| `--status-success` | `#22C55E` on `rgba(34,197,94,0.15)` | `#15803D` on `#DCFCE7` | Posted / Active / success toasts |
| `--status-warning` | `#F5B700` on `rgba(245,183,0,0.15)` | `#B45309` on `#FEF3C7` | Draft / pending |
| `--status-danger` | `#F43F5E` on `rgba(244,63,94,0.15)` | `#BE123C` on `#FFE4E6` | Cancelled / overdue / errors |
| `--status-info` | `#3B82F6` on `rgba(59,130,246,0.15)` | `#1D4ED8` on `#DBEAFE` | informational badges |

### Stat-card icon badges (both themes — soft circular fills, rotate through these 4)
Blue → Green → Violet/Accent → Red, each as a tinted circle background with a matching solid icon color (same pattern as the semantic tokens above — reuse them, don't invent new ones per card).

**Implementation note:** define all of the above as CSS custom properties on `:root` and `[data-theme="dark"]`, and if using PrimeVue, feed them into a custom PrimeVue preset (extend the Aura preset) rather than fighting the default theme — see §7.

---

## 2. Typography

- **Typeface:** a clean geometric/grotesk sans — Inter is the closest safe match if not specified further. Load via `@fontsource/inter` or system font stack fallback (`-apple-system, "Segoe UI", Roboto, Inter, sans-serif`).
- **Scale:**
  | Role | Size | Weight | Usage |
  |---|---|---|---|
  | Display / stat value | 28–32px | 600 | stat card big numbers |
  | Page title | 22px | 600 | "Dashboard", "GRN / Inward" |
  | Section/card title | 15–16px | 600 | "Stock Trend", "Recent Activities" |
  | Body | 14px | 400–500 | table cells, form labels values |
  | Caption/muted | 12–13px | 400–500 | timestamps, helper text, "vs last month" |
- Numeric values (stat cards, table amounts) use tabular figures where the library supports it, so columns of numbers align.

---

## 3. Layout structure

```
┌──────────┬──────────────────────────────────────────────┐
│          │  Topbar: greeting/title  ·  date range  ·  🔔  ·  avatar │
│ Sidebar  ├──────────────────────────────────────────────┤
│ (240px,  │                                                │
│  fixed)  │  Content area (scrolls independently)          │
│          │                                                │
└──────────┴──────────────────────────────────────────────┘
```

- **Sidebar (240px, fixed):** logo + product name top; nav list (icon + label, one active state at a time — filled accent pill/background on active item, muted icon+text otherwise); **facility switcher pinned at the bottom** ("Main Facility" dropdown) sitting above a subtle decorative illustration — this bottom decorative art is a nice-to-have polish detail, not a functional requirement; skip it under time pressure rather than let it block real screens.
- **Topbar:** left = page title + one-line contextual subtitle (e.g. "Good evening, Admin 👋 / Here's what's happening..."); right = date-range picker, notification bell with unread-count badge, avatar with dropdown (profile/logout).
- **Content padding:** ~24px around content area, ~20–24px gaps between cards.
- **Corner radius:** consistent scale — 8px small elements (badges, inputs), 12–16px cards/panels, full-round for avatar/icon badges.
- **Shadows:** dark theme relies on borders + subtle bg elevation, not drop shadows. Light theme uses soft shadows (`0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)`) on cards.

---

## 4. Screen patterns

### 4.1 Dashboard
- **Stat card row** (4 cards): icon badge (top-left, colored circle), label, big value, small trend line ("▲ 4.35% vs last month" — green for positive, red for negative, never just color without the arrow glyph, for accessibility).
- **Two-column row below:** left ~65% = area chart card (title + range dropdown top-right, gradient-fill line chart); right ~35% = "Recent Activities" feed (icon + description + relative timestamp per row, "View all" link top-right).
- **Quick Actions row:** 4 equal-width buttons, each with a colored icon square/badge + two-line label (bold action + muted subtitle, e.g. "New GRN / Record Inward"). These are shortcuts to the respective create flows, not decorative.

### 4.2 List views (GRN/Inward, Lots, Delivery, etc.)
- Header: title + one-line description, right-aligned toolbar: search input, filter dropdown(s), "Filters" button, "Export" button, primary CTA button (accent-filled, "+ New GRN").
- Table: sortable columns, **status as a pill badge** (uses semantic tokens from §1, never plain text for status), row actions (icon buttons, e.g. view/delete) right-aligned, pagination footer (page numbers + total count, "Showing X to Y of Z entries").
- Empty state: replace the table body with a centered icon + message + primary CTA when zero rows — don't just show an empty table.

### 4.3 Create/Edit flows — master-detail split panel
This is the standout pattern in the mockups and worth calling out explicitly: **creating a GRN does not navigate away from the list.** Instead:
- List stays visible on the left (~35–40% width, can keep scrolling/browsing while the form is open)
- A panel slides in on the right (~60–65% width) with the create/edit form
- Panel header: breadcrumb-style context ("GRN / Inward > Create GRN"), Cancel / Save Draft / Save (primary) actions top-right
- Form body: grouped header fields first (date, auto-generated number, party, chamber, driver, vehicle — in a responsive 2–3 column grid), then a **line-items table** (add/remove rows inline, per-row fields: item, packaging, qty, weight, rate, computed amount), then a **totals summary bar** pinned at the bottom of the panel (total net weight, total amount).
- Use this split-panel pattern consistently for GRN, Delivery Challan, and Invoice creation — don't invent a different pattern (e.g. modal, full-page navigation) per module.

---

## 5. Component → library mapping (PrimeVue)

| Mockup element | PrimeVue component |
|---|---|
| Stat cards | custom thin wrapper around `Card`, not a built-in — compose from primitives |
| Area chart | `Chart` (Chart.js wrapper) with gradient fill config |
| Data tables (GRN list, Lots) | `DataTable` + `Column`, built-in sort/pagination, `Paginator` |
| Status pills | `Tag` component, severity mapped to semantic tokens |
| Filters/search toolbar | `InputText` (with search icon), `Dropdown`/`MultiSelect`, `Button` (outlined) for Filters/Export |
| Notification bell + badge | `OverlayBadge` or `Badge` on an icon `Button` |
| Avatar + dropdown | `Avatar` + `Menu` |
| Sidebar nav | custom component using `Menu`/`PanelMenu` primitives, styled to match — not the default PrimeVue sidebar skin |
| Create/edit split panel | `Drawer` (position right, custom width) or a custom flex layout — do **not** use `Dialog`/modal, the mockup pattern is a persistent side panel, not an overlay modal |
| Line-items editable table | `DataTable` with inline editing (`editMode="row"`) or a custom repeatable-rows component if inline editing proves awkward for add/remove |
| Date range picker | `DatePicker` (range mode) |
| Toasts | `Toast` service, severity mapped to semantic tokens |
| Theme toggle | custom switch component driving `data-theme` attribute + PrimeVue preset swap |

---

## 6. Iconography

- Line-style icons (not filled/glyph-heavy), consistent stroke weight — PrimeIcons covers most needs (search, filter, download/export, bell, user, trash, eye, chevrons, package/box for inventory, truck for delivery). Where PrimeIcons lacks a specific icon (snowflake logo, cold-storage-specific glyphs), fall back to `lucide` icons rather than hand-drawing SVGs.
- Icons inside stat-card badges and quick-action buttons are the one place icons carry color (matching their badge); everywhere else (nav, table actions) icons are neutral/muted and only shift to accent color on hover/active.

---

## 7. Implementation notes

- Build theming as CSS custom properties (§1) at the root, and configure a custom PrimeVue preset (`definePreset` off the Aura base) that reads those same values, so PrimeVue components and hand-built components stay visually consistent — don't let PrimeVue's default palette and your custom CSS drift into two different "purple"s.
- Theme switch = toggle `data-theme="dark"|"light"` on `<html>` + swap the PrimeVue preset at runtime; no page reload.
- All colors in this spec are token references, not literals, in component code — agents should use `var(--accent-primary)` / the PrimeVue preset equivalents, never hardcode a hex value inline. This is what makes light/dark actually maintainable instead of two hand-synced copies.
- Respect `prefers-reduced-motion` for chart animations and panel slide-in transitions, per the quality bar in the main tech spec.