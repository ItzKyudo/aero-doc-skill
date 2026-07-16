# Agent System Manual

Welcome to the **nanoprog** agent documentation. This file is automatically maintained by [AeroDoc](../.agents/skills/aero_doc/skill.md).

---

## Application Entry Point

### `src/App.tsx`

`App` is the root component that gates the entire UI behind a maintenance mode check.

#### Maintenance Mode

The component reads the `VITE_MAINTENANCE_MODE` environment variable at startup:

```ts
const isMaintenanceMode = import.meta.env.VITE_MAINTENANCE_MODE === 'false';
```

| Condition | Behaviour |
|---|---|
| `VITE_MAINTENANCE_MODE === 'false'` | Renders the `<Maintenance />` screen; all other routes are blocked. |
| Any other value (including `'true'` or unset) | Renders the full site: `<Navbar>`, `<Hero>`, `<Services>`, `<Stats>`, `<Pricing>`, `<Footer>`. |

> **Warning:** The active condition is `=== 'false'`, which is the inverse of the conventional pattern. Set `VITE_MAINTENANCE_MODE=false` in `.env` to enable maintenance mode; omit the variable or set it to `true` to show the live site.

#### Page Structure (normal mode)

```
<div>
  <Navbar />
  <main>
    <Hero />
    <Services />
    <Stats />
    <Pricing />
  </main>
  <Footer />
</div>
```

---

## UI Components

### `src/components/Navbar.tsx`

Scroll-aware fixed header with a glass-panel effect and a functional mobile drawer.

- Applies `glass-panel` + `shadow` only after the user scrolls past 16px (`window.scrollY > 16`).
- Desktop nav links show an animated gradient underline on hover and on active selection.
- Mobile: a hamburger button (`<Menu />`) opens a slide-in `drawer` panel from the right. An overlay behind the drawer closes it on click.
- Body scroll is locked (`overflow: hidden`) while the drawer is open.

### `src/components/Hero.tsx`

Full-bleed hero with animated background layers, typewriter headline, and a floating code window.

- **Background**: dot-grid pattern (`dot-grid-bg`), radial `hero-glow`, and two blurred color blobs (blue top-right, cyan bottom-left).
- **Typewriter**: cycles through `TYPED_WORDS` (`Web Applications`, `Mobile Solutions`, `Embedded Systems`, `IoT Platforms`) with per-character typing and deletion at configurable speeds.
- **Headline**: uses `shimmer-text` for an animated gradient sweep on the brand phrase.
- **Content**: five staggered `fade-up-*` CSS classes create a sequential entrance animation for the badge, headline, typewriter, subtext, CTAs, and trust indicators.
- **Code window**: decorative `system-init.ts` panel with a `cursor-blink` at the end of the last line.
- **Floating widgets**: a "System Status" chip (float animation, 4 s period) and a "Avg. Latency" badge.

### `src/components/Services.tsx`

Three-column service cards with scroll-reveal entrance and per-card accent colors.

- `IntersectionObserver` triggers the `.reveal → .visible` transition when the section enters the viewport; each card gets a staggered `transitionDelay` of `120ms × index`.
- On hover, a `bg-gradient-to-r` `div` at `top: 0` becomes visible, forming a colored top border specific to each card (`blue`, `cyan`, `indigo`).
- Each card has a "Learn more" inline link.

### `src/components/Stats.tsx`

Four-stat bar with count-up animation and lucide icons.

- `useCountUp(target, 1800, start)` — custom hook using `requestAnimationFrame` with cubic ease-out; triggered once by `IntersectionObserver` at 30% visibility.
- Each stat displays a lucide icon: `Package`, `SmilePlus`, `Award`, `Headphones`.
- Flanked by `gradient-sep` separator lines.

### `src/components/Pricing.tsx`

Three-tier pricing section with a monthly/yearly toggle.

- Toggle switches between `monthlyPrice` and `yearlyPrice` fields; the yearly button shows a `−15%` badge.
- The highlighted ("Most Popular") card uses the `animated-border` utility — a rotating `conic-gradient` border powered by the `@property --angle` CSS animation.
- A note at the bottom links to `#contact`.

### `src/components/Footer.tsx`

Five-column footer with a newsletter input.

- Brand column includes an email `<input>` + submit `<button>` for newsletter sign-up (UI only — no backend wired).
- A `bg-gradient-to-b` overlay at `top: 0` creates a seamless fade from the section above.
- Copyright updated to **2025**; added a Cookie Policy link.

---

## Design System

### `src/index.css`

Tailwind v4 `@theme` block with extended tokens and custom utility classes.

| Token / Class | Value / Effect |
|---|---|
| `--color-bg-dark` | `#0d0f14` — page background |
| `--color-bg-card` | `#151821` — card surfaces |
| `--color-cyan` | `#06b6d4` — accent color |
| `shimmer-text` | Animated 200%-wide gradient sweep, 3 s loop |
| `dot-grid-bg` | 28 px radial-gradient dot pattern |
| `hero-glow` | Absolute radial ellipse glow at page top |
| `animated-border` | Rotating conic-gradient border via `@property --angle` |
| `reveal` / `visible` | Scroll-reveal pair: opacity + translateY transition |
| `fade-up-1…5` | Staggered entrance animations (0.1 s – 0.7 s delays) |
| `cursor-blink` | 1 s step-end opacity blink |
| `drawer` / `drawer-overlay` | Mobile drawer panel + backdrop styles |
| `gradient-sep` | 1 px horizontal line with blue/cyan gradient fade |

---

## Agent Behaviors

*No custom agent behaviors tracked yet.*

## System Prompts

*No system prompts documented yet.*
