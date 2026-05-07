# Frontend UI Design Guide

## Tech Foundation

- **Tailwind CSS** + HSL CSS variables (`src/style.css`)
- **lucide-vue-next** for icons
- **@tailwindcss/typography** for `prose` rich-text rendering
- CSS tokens mapped in `tailwind.config.cjs`: `bg-background`, `text-foreground`, `bg-primary`, `border-border`, etc.

## Page Root Structure

```
h-screen flex flex-col bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50
```

- Root container: `h-screen flex flex-col` — prevents inner scroll overflow
- Background: blue → purple → pink diagonal gradient

## Page Header

```html
<div class="bg-gradient-to-r from-blue-600 to-purple-600 shadow-lg px-6 py-4 flex-shrink-0">
  <h1 class="text-2xl font-bold text-white">Page Title</h1>
  <p class="text-xs text-blue-100 mt-1">Subtitle / description</p>
</div>
```

Blue → purple horizontal gradient, white text, `flex-shrink-0` keeps the header at fixed height.

## Card

```html
<div class="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
```

White background, `rounded-xl`, `border-gray-200`, `shadow-sm`.

## Buttons

| Purpose | Classes |
|---------|---------|
| Primary action (submit / ingest) | `bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white font-bold rounded-xl shadow-md` |
| Secondary action (new / create) | `bg-gradient-to-r from-green-400 to-emerald-500 text-white font-bold rounded-lg shadow-md` |
| Active tab | `bg-gradient-to-r from-blue-500 to-indigo-500 text-white border-transparent shadow-md` |
| Default tab | `bg-white text-gray-600 border-gray-200 hover:border-indigo-300` |

## Sidebar Section Header

```html
<div class="px-4 py-3 border-b border-gray-200 bg-gradient-to-r from-indigo-500 to-purple-500">
  <h2 class="text-sm font-semibold text-white">Section Title</h2>
</div>
```

## List Item — Selected / Active

```
bg-gradient-to-r from-blue-50 to-purple-50 border-l-4 border-l-blue-600 shadow-sm
```

Unselected hover: `hover:bg-gradient-to-r hover:from-gray-50 hover:to-blue-50`

## Badge / Pill

```html
<!-- Count badge -->
<span class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-indigo-100 text-indigo-600">3</span>

<!-- Domain label -->
<span class="px-3 py-1 text-sm font-bold rounded-full bg-gradient-to-r from-blue-500 to-indigo-500 text-white">Retirement</span>
```

## Empty State Placeholder

```html
<div class="flex flex-col items-center justify-center h-48 gap-3 text-gray-400">
  <span class="text-4xl">📂</span>
  <p class="text-sm">Descriptive message here</p>
</div>
```

## Input / Textarea

```html
<!-- Single-line -->
<input class="w-full px-3 py-2.5 rounded-lg border border-gray-200 bg-gray-50 text-sm
              placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-400
              focus:border-transparent transition-all" />

<!-- Multi-line (large text area) -->
<textarea class="... resize-y" style="min-height: 55vh" />
```

## AppLayout Navigation Sidebar

- Collapsible sidebar: expanded `w-56`, collapsed `w-16`, `transition-all duration-300`
- Active route: `bg-primary/10 text-primary`
- Icons from `lucide-vue-next`: Brain, BookOpen, Upload, MessageSquare, Lock, ChevronsLeft, ChevronsRight

## Right Panel Content Area

```html
<div class="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4 flex-shrink-0 shadow-md">
  <!-- Panel title row — fixed, does not scroll -->
</div>
<div class="flex-1 overflow-y-auto p-6">
  <!-- Content area — scrollable -->
</div>
```

`flex-1 overflow-y-auto` ensures the title row stays fixed while content scrolls independently.
