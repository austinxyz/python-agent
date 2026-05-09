## ADDED Requirements

### Requirement: AppLayout uses bottom tab bar below md, sidebar at md+
`frontend/src/components/AppLayout.vue` SHALL render two distinct layouts based on viewport width using Tailwind's `md:` (768px) breakpoint. Below `md`: a 56px-tall bottom tab bar fixed at `bottom: 0` with `padding-bottom: env(safe-area-inset-bottom)`, listing the same 4 nav items as the desktop sidebar. At `md` and above: the existing left sidebar (collapsible w-56/w-16). Both variants SHALL share the same `navItems` array and `useRoute` active-state logic.

#### Scenario: Phone viewport renders bottom tab bar
- **WHEN** the viewport is 393px wide
- **THEN** `<aside>` (sidebar) is hidden, a bottom-fixed `<nav>` element with role `navigation` renders 4 tab items, and `safe-area-inset-bottom` is applied as bottom padding

#### Scenario: Desktop viewport renders left sidebar
- **WHEN** the viewport is 1280px wide
- **THEN** the left sidebar renders as today (w-56 expanded / w-16 collapsed); no bottom tab bar is rendered

#### Scenario: Active nav item styling is consistent across variants
- **WHEN** the user is on `/chat` at any viewport
- **THEN** the corresponding tab/sidebar item is visually marked active using `bg-notion-tint-lavender text-notion-brand-purple-800` (Notion design tokens)

### Requirement: AppLayout removes blue→purple gradient in favor of Notion design tokens
The legacy `bg-gradient-to-r from-blue-500 to-purple-600` logo background and `bg-primary/10 text-primary` active-state classes in `AppLayout.vue` SHALL be replaced by Notion design system tokens. The logo SHALL render as a navy monochrome mark (no gradient). The active-state styling SHALL match the rest of the redesigned views (per `docs/design/notion.md`). No other view component SHALL import the now-orphaned `primary` Tailwind utility for this purpose.

#### Scenario: No leftover gradient classes in AppLayout
- **WHEN** the `AppLayout.vue` source is grepped for `from-blue` or `to-purple`
- **THEN** no matches are found

### Requirement: Project includes PWA manifest and apple-touch-icon
The repository SHALL include `frontend/public/manifest.json` declaring `name`, `short_name`, `start_url`, `display: "standalone"`, `theme_color` matching Notion design system primary, `background_color`, and at minimum three icon entries (192px, 512px, and 512px maskable). `frontend/index.html` SHALL include `<link rel="manifest" href="/manifest.json">`, `<link rel="apple-touch-icon" href="/icons/192.png">`, and `<meta name="theme-color" content="...">` matching the manifest. The icons themselves SHALL exist at `frontend/public/icons/`.

#### Scenario: Manifest is served by the frontend container
- **WHEN** a browser fetches `http://10.0.0.20:8910/manifest.json`
- **THEN** the response is HTTP 200 with content-type `application/manifest+json` and parses as valid JSON containing the above fields

#### Scenario: Add to home screen launches in standalone mode
- **WHEN** the user adds the app to home screen on iOS Safari and launches from the home screen icon
- **THEN** the app opens without browser chrome (URL bar hidden, full-viewport app)
