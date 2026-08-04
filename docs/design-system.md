# BNS AI Design System

> **Version:** 1.0
>
> **Purpose:** Canonical reference for the BNS AI visual language. Defines
> design principles, tokens, components, motion, theming, and usage rules
> so every screen ships a consistent, accessible, on-brand experience.

---

# 1. Design Principles

1.  **Trust through restraint.** BNS AI is a legal tool. Visuals must
    feel calm, precise, and authoritative — never playful or noisy.
2.  **Jade & Gold.** Jade (`#0d8a5e`) signals justice, clarity, and
    groundedness. Gold (`#b8860b`) signals eminence and legal prestige.
    These are the only two brand accents.
3.  **Glass, always layered on depth.** Surfaces are translucent
    panels with backdrop blur so content floats over animated
    gradients. Never flat cards on a flat background.
4.  **Motion with meaning.** Animation is used to orient the user
    (page entry, message arrival, progress). Nothing moves for its own
    sake.
5.  **Offline-first, performance-first.** The design must feel instant
    on low-end hardware. Prefer transform/opacity animations and honor
    `prefers-reduced-motion`.
6.  **Accessible by default.** Every accent must pass WCAG AA contrast
    against its surface in both themes.

---

# 2. Brand

| Attribute  | Value                                |
| ---------- | ------------------------------------ |
| Product    | BNS AI                               |
| Tagline    | Indian Legal Assistant               |
| Wordmark   | "BNS AI" (no icon required)          |
| Icon       | ⚖️ (scales, `nav-logo`)              |
| Accent     | Jade → Gold gradient (135°)          |

Text as a gradient uses:

```css
background: linear-gradient(135deg, var(--jade-light), var(--gold));
-webkit-background-clip: text;
-webkit-text-fill-color: transparent;
```

Applied to: `nav-title`, hero `h1`, page `h2` headings, `auth-card h2`.

---

# 3. Design Tokens

## 3.1 Color — Brand

Defined in `frontend/css/variables.css`.

| Token            | Value      | Usage                            |
| ---------------- | ---------- | -------------------------------- |
| `--jade`         | `#0d8a5e`  | Primary action, focus, active    |
| `--jade-dark`    | `#0a6e4a`  | Gradient end, hover depth        |
| `--jade-light`   | `#10b87a`  | Highlights, links, h3 accents    |
| `--gold`         | `#b8860b`  | Secondary accent                 |
| `--gold-light`   | `#daa520`  | `strong` emphasis in markdown    |

Status (hard-coded, not tokens):

| Meaning   | Value     |
| --------- | --------- |
| Danger    | `#dc3545` |
| Success   | `#22c55e` |
| Warning   | `#f59e0b` |
| Error text| `#ff6b6b` |
| Required  | `#ef4444` |

## 3.2 Color — Surfaces

Two themes: dark (default) and light, toggled via `data-theme` on
`<html>`.

**Dark theme** (`:root`, `variables.css`):

| Token               | Value                     |
| ------------------- | ------------------------- |
| `--bg-primary`      | `#0a0a1a`                 |
| `--bg-secondary`    | `#12122a`                 |
| `--bg-card`         | `rgba(18,18,42,0.7)`      |
| `--text-primary`    | `#e8e8f0`                 |
| `--text-secondary`  | `#a0a0b8`                 |
| `--border-color`    | `rgba(13,138,94,0.3)`     |

**Light theme** (`themes.css` `[data-theme="light"]`):

| Token               | Value                     |
| ------------------- | ------------------------- |
| `--bg-primary`      | `#f0f4f8`                 |
| `--bg-secondary`    | `#ffffff`                 |
| `--bg-card`         | `rgba(255,255,255,0.8)`   |
| `--text-primary`    | `#1a1a2e`                 |
| `--text-secondary`  | `#555577`                 |
| `--border-color`    | `rgba(13,138,94,0.2)`     |

## 3.3 Glass Surfaces

The signature treatment — translucent panels with blur.

| Token             | Dark theme                            | Light theme                            |
| ----------------- | ------------------------------------- | -------------------------------------- |
| `--glass-bg`      | `rgba(18,18,42,0.6)`                  | `rgba(255,255,255,0.7)`                |
| `--glass-border`  | `rgba(13,138,94,0.2)`                 | `rgba(13,138,94,0.15)`                 |
| `--glass-shadow`  | `0 8px 32px rgba(0,0,0,0.4)`          | `0 8px 32px rgba(0,0,0,0.1)`           |

Canonical glass recipe:

```css
.glass {
    background: var(--glass-bg);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--glass-border);
    border-radius: var(--radius);
    box-shadow: var(--glass-shadow);
}
```

## 3.4 Radius

| Token          | Value |
| -------------- | ----- |
| `--radius-sm`  | `8px` |
| `--radius`     | `16px`|

## 3.5 Shadow

| Token           | Value                          |
| --------------- | ------------------------------ |
| `--shadow`      | `0 8px 32px rgba(0,0,0,0.3)`   |

Hover elevation uses `--glass-shadow`.

---

# 4. Typography

| Token      | Value                                                        |
| ---------- | ------------------------------------------------------------ |
| `--font`   | `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif` |
| Mono       | `'Courier New', monospace` (draft previews, inline `code`)   |

Base: `body` uses `--text-primary` at 14–15px, `line-height: 1.6`.

Type scale (component-level, no dedicated tokens):

| Element           | Size    | Weight | Notes                                   |
| ----------------- | ------- | ------ | --------------------------------------- |
| Hero `h1`         | 48px    | 800    | Jade→Gold gradient, 48→32px on mobile   |
| Page `h2`         | 28px    | 700    | Jade→Gold gradient                      |
| Section `h3`      | 18px    | —      | `--jade-light`                          |
| Card title `h3`   | 15–17px | 600    |                                        |
| Nav title         | 22px    | 700    | Gradient wordmark                       |
| Body / labels     | 14px    | 400/500|                                        |
| Meta / captions   | 12px    | —      | `--text-secondary`                      |
| Stats `.stat-number`| 36px   | 800    | `--jade-light`                          |

Markdown emphasis inside assistant messages:
`strong` → `--gold-light`; code → jade-tinted chip
(`rgba(13,138,94,0.1)` background, `#13px`).

---

# 5. Spacing & Layout

No spacing tokens exist; use the established rhythm (4px base).

| Scale | Value |
| ----- | ----- |
| xs    | 4px   |
| sm    | 8px   |
| md    | 16px  |
| lg    | 24px  |
| xl    | 32px  |

- Page gutter: `#main-content` → `padding: 32px` (16px on mobile),
  `max-width: 1200px`, centered.
- Navbar height: 64–72px (sticky, glass, z-index 100).
- Grid gutters: 20–24px.
- Card padding: 24–28px.

---

# 6. Components

## 6.1 Buttons (`buttons.css`, `styles.css`)

| Class          | Usage                                   |
| -------------- | --------------------------------------- |
| `.btn`         | Base; `border-radius: var(--radius-sm)`, 14px/600 |
| `.btn-primary` | Jade→Jade-light 135° gradient, white text |
| `.btn-outline` | Transparent, glass border               |
| `.btn-danger`  | `#dc3545` background                    |
| `.btn-sm`      | `padding: 6px 14px`, 13px               |

Rules:
- Hover: `translateY(-1px)` + jade-tinted glow
  (`0 4px 16px rgba(13,138,94,0.4)`).
- Icons: buttons may embed an inline glyph with `gap: 8px`.
- Full-width inside forms: `.form-group .btn`.

## 6.2 Forms (`forms.css`)

- `.form-group` spacing: 20px vertical.
- Inputs: translucent (`rgba(255,255,255,0.05)`), glass border,
  `--radius-sm`, 15px text.
- Focus: jade border + `0 0 0 3px rgba(13,138,94,0.1)` ring.
- Labels: 14px, `--text-secondary`, weight 500.
- Errors: `.error-message` → `#ff6b6b` text on `rgba(255,107,107,0.1)`.

## 6.3 Cards

Families: `.feature-card`, `.draft-card`, `.stat-card`,
`.testimonial-card`, `.dashboard-list-item`. All share the glass recipe.

- Hover: `translateY(-2/-4px)`, jade border, `--glass-shadow`.
- Icons (`.feature-icon`, `.draft-card-icon`): 28–36px, float above title.
- `h3` titles in `--jade-light`.

## 6.4 Navigation

- `#navbar`: sticky glass bar, `backdrop-filter: blur(20px)`,
  bottom border `--glass-border`, z-index 100.
- `.nav-link`: `--text-secondary`, hover/active → jade-light + 10% jade wash.
- `.nav-title`: gradient wordmark.
- `.icon-btn`: 34–40px square, glass border; jade hover wash.
- `.user-badge`: Jade→Gold gradient pill, white text.

## 6.5 Chat

- Layout: `.chat-sidebar` (280–320px) + `.chat-main`, glass panels.
- `.message.user`: Jade→Jade-dark gradient, white, right-aligned.
- `.message.assistant`: 5% white surface + glass border, left-aligned;
  markdown styled per §4.
- `.chat-item.active`: 10% jade wash + jade border.
- Input `textarea`: translucent, glass border, focus jade border,
  auto-resize 48→160px.
- Empty state: 64px faint icon, `--text-secondary`.

## 6.6 Drafting Wizard

- `.draft-grid`: `repeat(auto-fill, minmax(320px, 1fr))` (1 col on mobile).
- `.draft-card`: glass, clickable; hover lift + jade border.
- `.draft-preview`: glass panel; `pre` block uses monospace on
  `rgba(0,0,0,0.3)`, scrolls past 500px.
- Actions: Generate / Copy / Download DOCX / New Draft.
- Keyboard shortcut: **Ctrl+Enter** submits.

## 6.7 Dashboard

- `.dashboard-grid`: `repeat(auto-fit, minmax(280px, 1fr))`.
- `.stat-card`: centered, `.stat-number` 36px 800 in jade-light,
  `.stat-label` 14px muted.
- `.dashboard-list-item`: glass row, title + meta.

## 6.8 Feedback & Overlays

| Component        | Spec                                                |
| ---------------- | --------------------------------------------------- |
| `.toast`         | Fixed bottom-right, jade bg, white text, `slideIn`  |
| `.loader`        | 48px ring, jade top border, `spin` 0.8s             |
| `.loading-screen`| Centered column, "Loading BNS AI…" 14px muted       |
| `.badge`         | Pill, 12px/600, accent tint (see `bundle.css`)      |
| Modal (legacy)   | `.modal-overlay` blur(4px) + `.modal-content` scale-in |
| Tooltip          | `[data-tooltip]` attribute-driven, dark bg          |

---

# 7. Motion

Easing curves (`animations-enhanced.css`):

| Token              | Value                                  |
| ------------------ | -------------------------------------- |
| `--ease-out-expo`  | `cubic-bezier(0.19, 1, 0.22, 1)`       |
| `--ease-out-back`  | `cubic-bezier(0.34, 1.56, 0.64, 1)`    |
| `--ease-in-out-circ`| `cubic-bezier(0.85, 0, 0.15, 1)`       |
| `--ease-spring`    | `cubic-bezier(0.175, 0.885, 0.32, 1.275)` |

Named keyframes: `fadeIn`, `spin`, `gradientShift` (8–12s),
`slideIn`, `pageEnter`, `staggerFade`, `messageSlideRight/Left`,
`typingDot`, `toastEnter/Exit`, `heroFloat`, `bubbleIn`.

Timing guidelines:

| Interaction | Duration |
| ----------- | -------- |
| Page enter  | 0.5s expo |
| Message     | 0.4s      |
| Hover lift  | 0.2–0.3s  |
| Gradient bg | 8–12s loop|
| Progress    | 0.4s      |

Rules:
- Animate only `transform` / `opacity` when possible.
- Honor `@media (prefers-reduced-motion: reduce)` (already implemented
  globally in `animations-enhanced.css`).
- Staggered page children cap at 0.55s delay.

---

# 8. Theming & Responsive

- Theme bootstrapped in `index.html` head script; defaults to dark,
  toggled by `#theme-toggle` (`app.toggleTheme`).
- All components must resolve every color through tokens so a theme
  change is a token swap — no hard-coded colors in components.
- Breakpoints:
  - `≤768px`: stack layouts, hide `.nav-links`, 1-column grids,
    `#main-content` padding 16px, hero `h1` 32px, message width 95%.
  - Content max-width: 1200px.

---

# 9. Accessibility

- Minimum text contrast `4.5:1` (WCAG AA) in both themes; verify
  `--text-secondary` on `--glass-bg`.
- Focus visible: 3px jade/`--accent` ring (`0 0 0 3px rgba(13,138,94,0.1)`).
- Touch targets ≥ 34px (`.icon-btn`, nav links).
- `aria-label` on icon-only controls (theme toggle).
- Motion reducers supported via `prefers-reduced-motion`.
- Theme respects saved preference; do not flash unstyled light theme.

---

# 10. File Map

| Concern          | File                          |
| ---------------- | ----------------------------- |
| Tokens (dark)    | `css/variables.css`           |
| Tokens (light)   | `css/themes.css`              |
| Base + pages     | `css/styles.css`              |
| Buttons          | `css/buttons.css`             |
| Forms            | `css/forms.css`               |
| Cards            | `css/cards.css`               |
| Glass surfaces   | `css/glass.css`               |
| Motion           | `css/animations.css`, `css/animations-enhanced.css` |
| Responsive       | `css/responsive.css`          |
| Bundle (legacy)  | `css/bundle.css`              |

---

# 11. Known Divergence

The frontend currently ships **two parallel token sets**:

- **Canonical (this spec):** Jade/Gold + glassmorphism
  (`variables.css`, `styles.css`, `themes.css`).
- **Legacy:** navy/blue primary (`#1e3a5f`, `#2563eb`) in
  `bundle.css`, which also contains a `--primary`-based dark theme and
  additional components (wizard, stepper, hero, footer, FAQ, CTA).

Until consolidation, any component rendered by `bundle.css` should be
re-tokenized to the Jade/Gold set above. New work MUST use the canonical
tokens only.

---

# 12. Contribution Checklist

Before shipping UI changes, verify:

- [ ] Uses canonical tokens only (no hex literals, no `--primary`).
- [ ] Glass recipe applied to surfaces.
- [ ] Jade/Gold accent only; red reserved for destructive/error.
- [ ] Hover/focus/active states defined.
- [ ] Dark + light theme both resolve correctly.
- [ ] `prefers-reduced-motion` safe.
- [ ] WCAG AA contrast in both themes.
- [ ] Responsive at ≤768px.
- [ ] No new hard-coded colors or font stacks.
