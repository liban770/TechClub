---
name: TechConnect Design System
colors:
  surface: '#fbf9f9'
  surface-dim: '#dbdad9'
  surface-bright: '#fbf9f9'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f3f3'
  surface-container: '#efeded'
  surface-container-high: '#e9e8e7'
  surface-container-highest: '#e3e2e2'
  on-surface: '#1b1c1c'
  on-surface-variant: '#444748'
  inverse-surface: '#303031'
  inverse-on-surface: '#f2f0f0'
  outline: '#747878'
  outline-variant: '#c4c7c7'
  surface-tint: '#5f5e5e'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#1c1b1b'
  on-primary-container: '#858383'
  inverse-primary: '#c8c6c5'
  secondary: '#735c00'
  on-secondary: '#ffffff'
  secondary-container: '#fed65b'
  on-secondary-container: '#745c00'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#1a1c1b'
  on-tertiary-container: '#838483'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e5e2e1'
  primary-fixed-dim: '#c8c6c5'
  on-primary-fixed: '#1c1b1b'
  on-primary-fixed-variant: '#474646'
  secondary-fixed: '#ffe088'
  secondary-fixed-dim: '#e9c349'
  on-secondary-fixed: '#241a00'
  on-secondary-fixed-variant: '#574500'
  tertiary-fixed: '#e2e3e1'
  tertiary-fixed-dim: '#c6c7c5'
  on-tertiary-fixed: '#1a1c1b'
  on-tertiary-fixed-variant: '#454746'
  background: '#fbf9f9'
  on-background: '#1b1c1c'
  surface-variant: '#e3e2e2'
typography:
  display:
    fontFamily: Manrope
    fontSize: 48px
    fontWeight: '800'
    lineHeight: 56px
    letterSpacing: -0.03em
  display-mobile:
    fontFamily: Manrope
    fontSize: 36px
    fontWeight: '800'
    lineHeight: 44px
    letterSpacing: -0.025em
  headline-lg:
    fontFamily: Manrope
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Manrope
    fontSize: 26px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Manrope
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  title-md:
    fontFamily: Manrope
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.005em
  body-lg:
    fontFamily: Manrope
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
    letterSpacing: 0em
  body-md:
    fontFamily: Manrope
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: 0em
  label-md:
    fontFamily: Manrope
    fontSize: 13px
    fontWeight: '600'
    lineHeight: 18px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Manrope
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.04em
  code:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 1rem
  margin: 3rem
  margin-tablet: 2rem
  margin-mobile: 1.25rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system embodies an authoritative, refined, and purposeful identity tailored for a thriving professional technology ecosystem. Rooted in the emerging tech scene of Hargeisa, it serves developers, product designers, technical founders, and executive mentors who value substance over spectacle.

### Brand Personality
- **Disciplined & Executive:** Structured, quiet confidence that mirrors top-tier enterprise developer tools and institutional knowledge hubs.
- **Catalytic & Collaborative:** Warmly engineered to invite mentorship, cross-discipline networking, and engineering rigor without casual social media noise.
- **Cultivated Elegance:** Grounded architectural structure enriched with an intentional gold accent, signaling quality, distinction, and upward momentum.

### Design Aesthetic
The aesthetic follows a **Refined Modern Minimalist** philosophy. It avoids decorative gradients, heavy blurs, and superficial ornamentation in favor of:
- Precise 1px borders delineating structural containers.
- Generous micro-whitespace paired with dense, legible data displays.
- High-contrast monochromatic hierarchy punctuated by singular, deliberate golden focal points.
- Balanced typography designed for extended reading, code sharing, and directory exploration.

## Colors

The palette establishes an editorial, high-contrast visual order designed for light mode clarity. It treats color as functional signaling rather than decoration.

### Color Architecture
- **Primary (`#111111` - Jet Black):** Dictates dominant structural elements, primary CTA fills, active navigation states, and heavy display typography. Conveys finality and precision.
- **Secondary (`#D4AF37` - Architectural Gold):** Reserved strictly for high-value actions, verified mentor insignias, active tab highlights, and contextual callouts. Never used for long-form body text.
- **Tertiary (`#F8F8F6` - Soft Warm White):** Forms the foundational canvas for cards, contextual sidebars, code snippets, and surface offsets against the `#FFFFFF` application backdrop.
- **Neutral (`#737373` - Gray):** Handles secondary metadata, helper text, inactive control outlines, and timestamps.
- **Charcoal Text (`#292929`):** Replaces harsh pure black for body copy to prevent visual fatigue while preserving strict WCAG AAA contrast ratios.
- **Structural Border (`#E5E5E5`):** Standard 1px stroke defining surfaces, grid lines, and interactive bounds.
- **Semantic Feedback:**
  - **Success (`#198754`):** Active project statuses, confirmed mentorship sessions, and valid system responses.
  - **Error (`#DC3545`):** Destructive actions, field failures, and expired sessions.

## Typography

The typography leverages **Manrope** across all standard weights to present an engineered, balanced, and modern geometric rhythm. Its open counters and geometric structure provide exceptional legibility on high-resolution displays and mobile viewports alike.

### Typographic Principles
- **Headlines:** Set tightly with negative tracking (`-0.01em` to `-0.03em`) and substantial weight (700 to 800) to command authority and anchor community sections.
- **Body Text:** Uses a relaxed line height (`1.57` to `1.625`) in Charcoal (`#292929`) to preserve visual comfort during technical reading, documentation, and forum threads.
- **Labels & Microcopy:** Rendered with elevated weights (600 to 700) and uppercase transformations on `label-sm` with widened letter-spacing (`0.04em`) for metadata, status tags, and table column titles.
- **Monospace Code:** Integrated via **JetBrains Mono** for code snippets, API keys, terminal outputs, and system metrics.

## Layout & Spacing

This design system utilizes an 8px base rhythmic grid paired with a fixed-max-width 12-column responsive layout. The container max-width caps at `1280px` to maintain optimal line lengths and prevent interface sprawling on ultra-wide desktop monitors.

### Breakpoints & Responsive Behavior
- **Desktop (1024px+):** Full 12-column grid. Outer page margin is `3rem` (`48px`) with `1.5rem` (`24px`) gutters. Sidebars occupy 3 or 4 columns; content feeds occupy 8 or 9 columns.
- **Tablet (768px – 1023px):** 8-column layout. Outer margins compress to `2rem` (`32px`) with `1.25rem` (`20px`) gutters. Auxiliary sidebars collapse into toggleable drawer surfaces.
- **Mobile (< 768px):** 4-column fluid layout. Canvas margins contract to `1.25rem` (`20px`) with `1rem` (`16px`) gutters. All grid spans collapse to 4 columns (100% width).

### Layout Rules
- Internal card padding is strictly uniform: `1.5rem` (`space-lg`) on desktop and `1rem` (`space-md`) on mobile.
- Section vertical spacing follows an expansive cadence of `2.5rem` (`space-xl`) to `4rem` to clearly delineate content domains without relying on heavy graphic separators.

## Elevation & Depth

Visual hierarchy is constructed primarily through crisp surface boundaries (`#E5E5E5` 1px borders) combined with subtle, low-opacity ambient shadows. The interface maintains a flat, tactile profile reminiscent of architectural blueprints.

### Elevation Hierarchy
- **Level 0 (Flat Canvas):** `#FFFFFF` or `#F8F8F6`. Ground zero for all dashboards and index layouts. No shadow.
- **Level 1 (Card & Content Surface):** `#FFFFFF` bordered with 1px solid `#E5E5E5`. Ambient shadow: `0 1px 3px 0 rgba(17, 17, 17, 0.04), 0 1px 2px -1px rgba(17, 17, 17, 0.03)`.
- **Level 2 (Interactive Hover & Popovers):** Triggered on card hover or dropdown expansion. 1px solid `#D4D4D4`. Ambient shadow: `0 4px 12px -2px rgba(17, 17, 17, 0.06), 0 2px 6px -2px rgba(17, 17, 17, 0.04)`.
- **Level 3 (Modals & Overlays):** Fixed floating surfaces backed by a translucent backdrop (`rgba(17, 17, 17, 0.4)`). 1px solid `#E5E5E5`. Ambient shadow: `0 20px 25px -5px rgba(17, 17, 17, 0.1), 0 8px 10px -6px rgba(17, 17, 17, 0.06)`.

Gradients and colored drop shadows are strictly prohibited to maintain professional restraint.

## Shapes

The shape system employs an intentional, geometric curvature range between 8px and 12px to strike a balance between precision engineering and contemporary warmth.

### Corner Radius Tokens
- **Base (8px / `0.5rem`):** Applied to standard interactive controls, including input fields, standard buttons, dropdown menus, and data table rows.
- **Large (12px / `0.75rem`):** Applied to content cards, modal dialogs, and code presentation blocks.
- **Pill (9999px):** Restricted entirely to status badges, category chips, and live availability indicators.

Sharp corners (0px) are reserved exclusively for horizontal divider rules and table internal grid strokes.

## Components

### Buttons
- **Primary:** Background `#111111`, text `#FFFFFF`, border 1px solid `#111111`, radius 8px (`rounded-base`). Hover: background `#292929`, border-color `#292929`. Active: transform scale `0.99`.
- **Accent (Featured Action):** Background `#D4AF37`, text `#111111`, border 1px solid `#D4AF37`, font-weight 600. Hover: background `#C29F2F`.
- **Secondary (Outline):** Background `#FFFFFF`, text `#111111`, border 1px solid `#E5E5E5`. Hover: background `#F8F8F6`, border-color `#D4D4D4`.
- **Ghost:** Background transparent, text `#292929`. Hover: background `#F8F8F6`, text `#111111`.

### Badges & Chips
- **Status Badges:** Fully rounded (`rounded-full`), height 24px, padding horizontal 8px. Typography: `label-sm`.
  - *Active / Available:* Background `#E8F5E9`, text `#198754`, 1px solid `#C8E6C9`.
  - *Mentor Verified:* Background `#FDFBF2`, text `#9A7B1C`, 1px solid `#F3E8B6`.
  - *Neutral / Tag:* Background `#F8F8F6`, text `#737373`, 1px solid `#E5E5E5`.
- **Filter Chips:** Radius 8px, height 32px, padding horizontal 12px. Interactive outline style with active state shifting to `#111111` background and `#FFFFFF` text.

### Inputs & Form Fields
- Height 40px (Desktop), padding horizontal 12px. Background `#FFFFFF`, border 1px solid `#E5E5E5`, radius 8px. Typography: `body-md` (`#292929`).
- **Placeholder:** Text `#737373`.
- **Focus State:** 1px solid `#111111` accompanied by an intentional outer focus ring: `0 0 0 3px rgba(212, 175, 55, 0.25)`.
- **Error State:** 1px solid `#DC3545`, focus ring: `0 0 0 3px rgba(220, 53, 69, 0.2)`.

### Cards
- Background `#FFFFFF`, border 1px solid `#E5E5E5`, radius 12px (`rounded-lg`), padding `1.5rem` (`24px`). Elevation Level 1.
- Hoverable cards shift border color to `#D4D4D4` with Level 2 elevation and a top accent bar (optional 2px border in `#D4AF37` for featured mentorship opportunities).

### Data Tables
- Structural borders: horizontal lines 1px solid `#E5E5E5`.
- **Header:** Background `#F8F8F6`, typography `label-sm` in `#737373`, uppercase, padding 12px 16px.
- **Row:** Height 56px, background `#FFFFFF`, hover state `#F8F8F6`. Cell typography: `body-md` in `#292929`.

### Mentorship & Community Directory Cards
- Distinct card layout featuring a 48px rounded avatar, verified mentor gold checkmark chip, inline specialty tags, and clear primary CTA (`Request Session`) anchored to the bottom-right.