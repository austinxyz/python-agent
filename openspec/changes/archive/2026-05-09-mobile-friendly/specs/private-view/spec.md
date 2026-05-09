## ADDED Requirements

### Requirement: PrivateView renders TreeNav as drawer below md
Below the `md` breakpoint (768px), `PrivateView.vue` SHALL hide the inline left TreeNav and expose it via a `☰` button (`data-tree-toggle`) in the page header. Tapping `☰` opens a full-width slide-in drawer with the TreeNav. Selecting a directory or entry in the drawer SHALL close the drawer and update the right-panel state. The right panel SHALL render at full viewport width below `md`. The "create new entry" affordance SHALL remain reachable via a `＋` button in the page header on mobile (one tap, no drawer).

#### Scenario: Phone viewport hides inline tree
- **WHEN** PrivateView renders at viewport 393px
- **THEN** `data-tree-inline` is `display: none`, `data-tree-toggle` is visible in the header, and the right panel takes full width

#### Scenario: ＋ button creates a new entry without opening the drawer
- **WHEN** the user taps `data-new-entry` at viewport 393px
- **THEN** the right panel transitions to the new-entry form state directly; no drawer is opened

#### Scenario: Desktop layout unchanged
- **WHEN** PrivateView renders at viewport 1280px
- **THEN** the inline tree renders as today; no `☰` or mobile-only `＋` button is present
