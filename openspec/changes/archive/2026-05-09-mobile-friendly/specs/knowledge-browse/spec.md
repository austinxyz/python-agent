## ADDED Requirements

### Requirement: WikiView renders TreeNav as drawer below md
Below the `md` breakpoint (768px), `WikiView.vue` SHALL hide the inline left TreeNav and expose it via a `☰` button (`data-tree-toggle`) in the page header. Tapping `☰` opens a full-width slide-in drawer with the TreeNav. Selecting a domain or file in the drawer SHALL close the drawer and load that content into the right panel. The right panel SHALL render at full viewport width below `md`.

#### Scenario: Phone viewport hides inline tree
- **WHEN** WikiView renders at viewport 393px
- **THEN** `data-tree-inline` is `display: none`, `data-tree-toggle` is visible in the header, and the article/welcome content takes full width

#### Scenario: Drawer selection loads file content
- **WHEN** the user opens the drawer and taps a file entry
- **THEN** the drawer closes and the right panel renders that file's markdown content at full width

#### Scenario: Desktop layout unchanged
- **WHEN** WikiView renders at viewport 1280px
- **THEN** the inline tree renders as today; no `☰` button is present
