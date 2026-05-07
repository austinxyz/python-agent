# 前端 UI 设计规范

## 技术基础
- **Tailwind CSS** + HSL CSS 变量（`src/style.css`）
- **lucide-vue-next** 提供图标
- **@tailwindcss/typography** 用于 `prose` 富文本渲染
- CSS token 在 `tailwind.config.cjs` 中映射：`bg-background`、`text-foreground`、`bg-primary`、`border-border` 等

## 页面整体结构
```
h-screen flex flex-col bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50
```
- 页面根容器：`h-screen flex flex-col`，防止内部滚动溢出
- 背景：蓝→紫→粉渐变（`from-blue-50 via-purple-50 to-pink-50`）

## 页头（Page Header）
```html
<div class="bg-gradient-to-r from-blue-600 to-purple-600 shadow-lg px-6 py-4 flex-shrink-0">
  <h1 class="text-2xl font-bold text-white">页面标题</h1>
  <p class="text-xs text-blue-100 mt-1">副标题说明文字</p>
</div>
```
蓝→紫横向渐变，白色文字，`flex-shrink-0` 固定高度不参与 flex 伸缩。

## 卡片（Card）
```html
<div class="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
```
白底、`rounded-xl`、`border-gray-200`、`shadow-sm`。

## 按钮
| 用途 | 样式 |
|------|------|
| 主操作（提交/摄入） | `bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white font-bold rounded-xl shadow-md` |
| 次操作（新建） | `bg-gradient-to-r from-green-400 to-emerald-500 text-white font-bold rounded-lg shadow-md` |
| Tab 激活 | `bg-gradient-to-r from-blue-500 to-indigo-500 text-white border-transparent shadow-md` |
| Tab 默认 | `bg-white text-gray-600 border-gray-200 hover:border-indigo-300` |

## 侧边栏分区 Header
```html
<div class="px-4 py-3 border-b border-gray-200 bg-gradient-to-r from-indigo-500 to-purple-500">
  <h2 class="text-sm font-semibold text-white">标题</h2>
</div>
```

## 列表项选中 / 激活
```
bg-gradient-to-r from-blue-50 to-purple-50 border-l-4 border-l-blue-600 shadow-sm
```
未选中 hover：`hover:bg-gradient-to-r hover:from-gray-50 hover:to-blue-50`

## 徽章（Badge / Pill）
```html
<!-- 数量 -->
<span class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-indigo-100 text-indigo-600">N 篇</span>
<!-- 领域标签 -->
<span class="px-3 py-1 text-sm font-bold rounded-full bg-gradient-to-r from-blue-500 to-indigo-500 text-white">退休规划</span>
```

## 空状态占位
```html
<div class="flex flex-col items-center justify-center h-48 gap-3 text-gray-400">
  <span class="text-4xl">📂</span>
  <p class="text-sm">说明文字</p>
</div>
```

## 输入框 / 文本区
```html
<!-- 单行 -->
<input class="w-full px-3 py-2.5 rounded-lg border border-gray-200 bg-gray-50 text-sm
              placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-400
              focus:border-transparent transition-all" />
<!-- 多行（大文本框） -->
<textarea class="... resize-y" style="min-height: 55vh" />
```

## AppLayout 导航栏
- 可折叠侧边栏：展开 `w-56`，收起 `w-16`，`transition-all duration-300`
- 激活路由：`bg-primary/10 text-primary`
- 图标：`lucide-vue-next`（Brain、BookOpen、Upload、MessageSquare、Lock、ChevronsLeft、ChevronsRight）

## 右侧面板内容区
```html
<div class="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4 flex-shrink-0 shadow-md">
  <!-- 面板标题行，固定不滚动 -->
</div>
<div class="flex-1 overflow-y-auto p-6">
  <!-- 内容区，可滚动 -->
</div>
```
`flex-1 overflow-y-auto` 保证标题固定、内容独立滚动。
