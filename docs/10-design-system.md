# 10 — Design System

## One DS, two front-ends

- **Mantine 9** is the only design system. ADR-0002 floats with major
  Mantine versions; the *decision* (Mantine as the sole DS) is what's
  locked, not the version number.
- Cross-cutting widgets and AI surfaces live in **`admin-ui/src/orbiteus-ui/`**
  (`widgets/` + `ai/`). `portal-ui` is a separate Next app; copy components
  from there when the portal needs the same UX (no shared npm package).
- No second DS. Adding one requires an ADR (and a strong reason — ADR `0002`
  documents the existing decision).

## Workspace layout

```
package.json                 (workspaces: ["admin-ui", "portal-ui"])
admin-ui/                    (Next.js 16 + React 19)
  src/orbiteus-ui/           (Badge, Monetary, Statusbar, Many2OneSelect, TagsField,
                              PromptInput, AIChatPanel, AIDashboard, useAIContext)
portal-ui/                   (Next.js 16 + React 19)
```

Imports in admin-ui:

```ts
import { PromptInput, AIDashboard } from "@/orbiteus-ui";
```

## Tokens and theme

- Mantine theme lives in `admin-ui/src/lib/theme.ts` (imported by
  `admin-ui/src/app/layout.tsx`). Portal UI uses the same palette in
  `portal-ui/src/lib/theme.ts`.
- Root layout wraps `<MantineProvider theme={orbiteusTheme}>`.
- Default **UI accent** is **charcoal / zinc** (`primaryColor: "dark"` with a
  custom 10-step scale from `#fafafa` to `#09090b`) — nav, buttons, active
  rows, focus rings. **Not** Mantine default blue.
- **Semantic / data colors** stay on the full Mantine palette (dashboard KPI
  icons, status badges, audit actors, module tiles) so lists and dashboards
  stay readable and lively without painting the chrome blue.
- `primaryColor`, font stack, default radius — live in `theme.ts`.

### Density (balanced compact)

Orbiteus targets **structured but readable** admin UI — not oversized ERP
chrome, not ultra-dense dev tools:

| Token | Value | Notes |
|---|---|---|
| `fontSizes.md` | 16px | body / table cells |
| `fontSizes.sm` | 14px | nav, labels, secondary |
| `fontSizes.xs` | 12px | meta, badges, code in tables |
| `spacing.md` | 16px | card padding, main shell gutter |
| List row min-height | 42px | `RecordRowList.module.css` |
| App shell header | 52px | sidebar 56px collapsed / 240px expanded |

Default control size is **`sm`** (Mantine) with the 16px scale above.
Do not hardcode `11px` fonts or `size="xs"` on primary actions — use theme
tokens or `sm`/`md`.

## Branding

- `useBranding()` in `admin-ui/src/lib/branding.tsx` reads `/api/base/branding` per tenant.
- Returns `{ name, logo_url, favicon_url }`.
- Components prefer `<Branding>` markers over hardcoded names.
- Product name is **never** hardcoded in tracked content (see `AGENTS.md`).

## Dark / light mode

- Both apps use Mantine's `ColorSchemeScript` for hydration-safe SSR.
- Default: light. User toggle persists in `localStorage`.

## Accessibility

- Color contrast: WCAG AA minimum on text and primary buttons.
- All interactive widgets must have keyboard equivalents.
- Mantine inputs already meet ARIA basics; custom widgets must too.

## What you ship vs reuse

- **Reuse from Mantine** whenever it covers the case (TextInput, Select,
  Modal, Drawer, Tabs, Button, Badge, ActionIcon, Notifications, Calendar).
- **Build in `admin-ui/src/orbiteus-ui/`** when you need engine semantics (badge color
  rules, monetary format with locale, statusbar transitions, RBAC-aware
  many2one resolver, AI prompt widgets).
- **Never build in `admin-ui/src/components/`** if `portal-ui` could ever need
  the same component — put it under `orbiteus-ui/` first (then copy to portal
  when that app adopts it).
