<template>
  <div class="h-full flex flex-col bg-notion-surface-soft">
    <!-- Hero band -->
    <div class="bg-notion-brand-navy text-notion-on-dark px-6 py-5 flex-shrink-0">
      <h1 class="text-xl font-semibold tracking-tight leading-tight">系统管理</h1>
    </div>

    <div class="flex-1 overflow-auto p-6">
      <div class="bg-notion-canvas border border-notion-hairline rounded-xl p-5 max-w-xl">
        <!-- Card header -->
        <div class="flex justify-between items-center mb-4">
          <span class="text-[15px] font-semibold text-notion-ink">证书与 Tailscale 状态</span>
          <span
            data-overall-pill
            :class="['text-[11px] font-medium px-3 py-0.5 rounded-full', pillClasses]"
          >{{ pillText }}</span>
        </div>

        <!-- Loading / error -->
        <div v-if="loading" class="text-[13px] text-notion-steel py-4 text-center">加载中…</div>
        <div v-else-if="fetchError && !status" class="text-[13px] text-notion-error py-4 text-center">无法获取状态</div>

        <!-- Rows (with optional stale-data banner when poll failed but we have cached data) -->
        <template v-else>
          <div v-if="fetchError" class="text-[11px] text-notion-warning mb-2">⚠ 上次刷新失败，显示的是缓存数据。</div>

          <div class="flex justify-between items-baseline py-2.5 border-b border-notion-hairline-soft text-[13px]">
            <span class="text-notion-steel">Tailnet 主机名</span>
            <span class="text-notion-charcoal font-mono text-[12px] font-semibold">{{ status.hostname || '—' }}</span>
          </div>

          <div class="flex justify-between items-baseline py-2.5 border-b border-notion-hairline-soft text-[13px]">
            <span class="text-notion-steel">证书到期</span>
            <span class="text-notion-charcoal font-mono text-[12px]">
              <template v-if="status.cert_expiry_iso">
                {{ status.cert_expiry_iso }}
                <span
                  data-days-badge
                  :class="['text-[11px] px-2 py-0.5 rounded ml-2', daysBadgeClasses]"
                >还剩 {{ status.days_remaining }} 天</span>
              </template>
              <template v-else>无法读取</template>
            </span>
          </div>

          <div class="flex justify-between items-baseline py-2.5 border-b border-notion-hairline-soft text-[13px]">
            <span class="text-notion-steel">Tailscale 连接</span>
            <span class="text-notion-charcoal font-mono text-[12px]">{{ status.tailscale_status }}</span>
          </div>

          <div class="flex justify-between items-baseline py-2.5 text-[13px]">
            <span class="text-notion-steel">上次 renew</span>
            <span class="text-notion-charcoal font-mono text-[12px]">{{ status.last_renew_iso || '—' }}</span>
          </div>

          <p class="mt-4 text-[11px] text-notion-stone">
            数据源：<code class="bg-notion-tint-lavender text-notion-brand-purple-800 px-1 rounded">GET /api/admin/cert-status</code>。每 60 秒自动刷新。
          </p>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import api from '../api/index.js'

const status = ref(null)
const loading = ref(true)
const fetchError = ref(false)

const pillVariant = computed(() => {
  if (!status.value || status.value.tailscale_status === 'offline') return 'error'
  const days = status.value.days_remaining
  if (days === null || days < 7) return 'error'
  if (days <= 30) return 'warning'
  return 'healthy'
})

const pillClasses = computed(() => ({
  healthy: 'bg-notion-tint-mint text-notion-brand-green',
  warning: 'bg-notion-tint-yellow text-notion-warning',
  error: 'bg-notion-tint-rose text-notion-error',
}[pillVariant.value]))

const pillText = computed(() => ({
  healthy: '健康',
  warning: '即将到期',
  error: '异常',
}[pillVariant.value]))

const daysBadgeClasses = computed(() => {
  const v = pillVariant.value
  return {
    healthy: 'bg-notion-tint-mint text-notion-brand-green',
    warning: 'bg-notion-tint-yellow text-notion-warning',
    error: 'bg-notion-tint-rose text-notion-error',
  }[v]
})

async function fetchStatus() {
  try {
    const resp = await api.get('/admin/cert-status')
    status.value = resp.data
    fetchError.value = false
  } catch {
    fetchError.value = true
    // preserve status.value — do not wipe previously good data on a transient failure
  } finally {
    loading.value = false
  }
}

let timer = null
onMounted(() => {
  fetchStatus()
  timer = setInterval(fetchStatus, 60_000)
})
onUnmounted(() => clearInterval(timer))
</script>
