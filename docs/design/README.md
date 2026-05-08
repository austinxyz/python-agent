# UI Design Sources

The project's visual language is anchored in a single **DESIGN.md** file from
[VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md).
The file captures color tokens, typography scale, spacing, surface treatments,
component specs, and motion — enough for any AI agent or human to implement
matching UI without re-deciding fundamentals each time.

## Status

| File | Role |
|---|---|
| **`notion.md`** | **Primary** — Notion's design system. Authoritative source for new components. Light-first (matches current direction), navy hero band, purple pill CTAs, illustration-rich. |
| `linear.md` | **Backup** — Linear's design system (dark-first, single lavender accent, Linear Display type). Use only if `notion.md` is rejected after first migration attempt. |

## How to use

1. **Before adding a new component or page**: read the relevant section of `notion.md`. Pick the closest token / pattern. Don't invent.
2. **When in doubt about a token**: the DESIGN.md is the source of truth. If a value isn't there, ask before adding one.
3. **For redesign work**: open `notion.md`, find the component you're redesigning, copy the relevant tokens into the Vue/Tailwind layer. Playwright E2E (`frontend/e2e/`) protects against behavior regression while you change the look.

## Key callouts (Notion as primary)

- **Notion is light-first** (`canvas: #ffffff`, `surface: #f6f5f4`). Aligns with current project direction; no dark-mode rewrite required.
- **Brand-navy hero band** (`#0a1530`) on the homepage section anchors a section without coloring the whole page. Translatable to a per-page header (replaces the current 4-step blue→purple→pink gradient).
- **Single primary purple** (`#5645d4`) used as the "pill" CTA shape. Reduces the current zoo of green/purple/pink gradient buttons to one canonical accent.
- **Pastel feature cards** (peach, rose, mint, lavender, sky, yellow) replace heavy gradients with soft tinted surfaces — fits a knowledge-base where each tag/category needs visual differentiation without competing with content.
- **Notion-Sans (Inter-based)** typeface across all UI surfaces — already free, no font licensing concerns.
- **Linear** stays as backup (`linear.md`). If a Notion-first redesign comes out feeling too cheerful for a personal finance tool, switch to Linear's restrained dark aesthetic.

## Why this format

`DESIGN.md` is a plain-Markdown convention introduced by Google Stitch and
adopted by the awesome-design-md collection. AI coding agents (Claude, Cursor,
etc.) can read it directly and produce consistent UI output. Sticking to this
format avoids the "every redesign re-decides fundamentals" trap that motivated
the swap (see `docs/log/2026-05-07.md` for the cost of the previous approach).
