## ADDED Requirements

### Requirement: IngestView renders TreeNav as drawer below md
Below the `md` breakpoint (768px), `IngestView.vue` SHALL hide the inline left TreeNav and instead expose it via a `☰` button (`data-tree-toggle`) in the page header. Tapping the button opens a full-width slide-in drawer containing the TreeNav. Selecting a domain or file in the drawer SHALL close it and update the right-panel state-machine ref. The right panel SHALL render at full viewport width below `md`.

#### Scenario: Phone viewport hides inline tree, shows ☰
- **WHEN** IngestView renders at viewport 393px
- **THEN** the inline tree (`data-tree-inline`) is `display: none`, a `data-tree-toggle` button is visible in the page header, and the right panel takes full width

#### Scenario: Drawer selection updates the right panel
- **WHEN** the user opens the drawer and taps a domain
- **THEN** the drawer closes and the right panel transitions to `domain` state for that domain (state-machine ref unchanged from desktop behavior)

#### Scenario: Desktop layout unchanged
- **WHEN** IngestView renders at viewport 1280px
- **THEN** the inline tree renders as today; no `☰` button is present
