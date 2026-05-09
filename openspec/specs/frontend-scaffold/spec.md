## Purpose

Defines the Vue 3 + Vite frontend scaffold and shared chrome: project bootstrap, routing, axios setup, top-level AppLayout (with mobile bottom-tab variant), shared TreeNav, and PWA manifest. Per-view capabilities (chat-view, ingest-view, etc.) extend this.
## Requirements
### Requirement: Vue 3 + Vite project with Pinia and Vue Router
The system SHALL have a `frontend/` directory initialised as a Vue 3 + Vite project with the following dependencies: `vue`, `vue-router`, `pinia`, `axios`. Dev dependencies: `vite`, `@vitejs/plugin-vue`, `vitest`, `@vue/test-utils`, `happy-dom`. The project MUST include a `vite.config.js` that configures the Vue plugin and a dev-server proxy: `server.proxy['/api'] = 'http://localhost:5000'`.

#### Scenario: Frontend dev server starts
- **WHEN** `cd frontend && npm run dev` is run
- **THEN** Vite starts without errors and the app is accessible at `http://localhost:3000`

#### Scenario: API calls are proxied
- **WHEN** the frontend makes an `axios.get('/api/health')` call during development
- **THEN** the request is forwarded to `http://localhost:5000/api/health` without CORS errors

### Requirement: Axios instance configured with /api baseURL
The system SHALL provide `frontend/src/api/index.js` that creates and exports a single Axios instance with `baseURL: '/api'`. All API calls in stores and components MUST import from this module. API calls MUST NOT prepend `/api` again (e.g., use `api.get('/wiki')`, not `api.get('/api/wiki')`).

#### Scenario: Axios baseURL is /api
- **WHEN** `import api from '@/api'` is used and `api.get('/wiki')` is called
- **THEN** the HTTP request goes to `/api/wiki`

### Requirement: App layout shell with left navigation
The system SHALL provide `frontend/src/App.vue` that renders `AppLayout.vue`. `AppLayout.vue` MUST implement a fixed left navigation bar of width 100px containing four navigation items with icons and labels: 📚 知识库 (links to `/wiki`), ⬆ 摄入 (links to `/ingest`), 💬 对话 (links to `/chat`), 🔒 私有 (links to `/private`). The active nav item MUST be highlighted using Vue Router's `router-link-active` class. The right side of the layout MUST contain a `<router-view />` slot for the current page.

#### Scenario: Left nav renders all four items
- **WHEN** the app is loaded at any route
- **THEN** all four navigation items are visible in the left sidebar

#### Scenario: Active nav item is highlighted
- **WHEN** the user navigates to `/chat`
- **THEN** the 💬 对话 nav item has the `router-link-active` class applied

### Requirement: Four view skeletons with Vue Router routes
The system SHALL provide four view components under `frontend/src/views/`: `WikiView.vue`, `IngestView.vue`, `ChatView.vue`, `PrivateView.vue`. Each view MUST render a heading with the page name (e.g., `<h1>知识库</h1>`). Vue Router MUST map: `/wiki` → `WikiView`, `/ingest` → `IngestView`, `/chat` → `ChatView`, `/private` → `PrivateView`. The root path `/` MUST redirect to `/wiki`.

#### Scenario: Navigation routes to correct view
- **WHEN** the user navigates to `/ingest`
- **THEN** `IngestView.vue` is rendered in the `<router-view />`

#### Scenario: Root redirect
- **WHEN** the user navigates to `/`
- **THEN** the router redirects to `/wiki` and `WikiView.vue` is rendered

### Requirement: TreeNav.vue stub component
The system SHALL provide `frontend/src/components/tree-nav/TreeNav.vue` that accepts two props: `items` (array of tree nodes) and `onSelect` (function called with the selected node). For this change, the component MUST render a `<ul>` list of the top-level item labels. The full tree expand/collapse behaviour is deferred to a feature change. The component MUST NOT duplicate tree logic — it is the single source of truth for tree navigation across the wiki page and the ingest files tab.

#### Scenario: TreeNav renders item labels
- **WHEN** `<TreeNav :items="[{label:'Finance'},{label:'Health'}]" :onSelect="() => {}" />` is rendered
- **THEN** the component displays "Finance" and "Health" as list items

### Requirement: Four Pinia store stubs
The system SHALL provide four Pinia store files under `frontend/src/stores/`: `wiki.js`, `ingest.js`, `chat.js`, `private.js`. Each store MUST export a `use<Domain>Store` composable (e.g., `useWikiStore`) and define at minimum an empty `state` object. Stores are empty stubs; feature changes populate them with state, getters, and actions.

#### Scenario: Stores are importable without error
- **WHEN** any of the four store composables are imported in a component
- **THEN** no import or runtime error occurs and the store is accessible via `useWikiStore()` etc.

### Requirement: Frontend vitest smoke test
The system SHALL include a `frontend/tests/` directory with `smoke.test.js` that: mounts `AppLayout.vue` and asserts the four nav items are present; mounts each of the four view components and asserts their heading is present. Tests MUST use `@vue/test-utils` with `happy-dom` as the test environment.

#### Scenario: Frontend smoke tests pass
- **WHEN** `cd frontend && npm test` is run
- **THEN** all smoke tests pass with exit code 0

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

