<template>
  <!--
    AcceptInviteView — multi-user-auth-core. Mock anchor:
    docs/.../mocks/2026-05-09-multi-user-auth-mocks.html#accept-invite.
  -->
  <div class="h-full flex items-center justify-center bg-notion-surface-soft px-4 py-8">
    <div class="w-full max-w-[420px] bg-notion-canvas border border-notion-hairline rounded-xl shadow-sm p-8">

      <div v-if="loading" class="text-center py-8 text-notion-stone text-[13px]">加载邀请信息…</div>

      <div v-else-if="state === 'expired'" data-invite-error class="text-center py-4">
        <div class="text-[32px] mb-2">⏰</div>
        <h3 class="text-[15px] font-semibold text-notion-warning mb-2">邀请链接已过期</h3>
        <p class="text-[13px] text-notion-charcoal mb-3">这个邀请已超过 7 天有效期。</p>
        <p class="text-[12px] text-notion-stone">请向管理员申请新的邀请链接。</p>
      </div>

      <div v-else-if="state === 'used'" data-invite-error class="text-center py-4">
        <div class="text-[32px] mb-2">✓</div>
        <h3 class="text-[15px] font-semibold text-notion-brand-green mb-2">邀请已激活</h3>
        <p class="text-[13px] text-notion-charcoal mb-4">这个邀请已经被使用过。</p>
        <button class="w-full h-[36px] bg-notion-primary text-notion-on-primary rounded-md text-[13px] font-medium" @click="goLogin">前往登录页 →</button>
      </div>

      <div v-else-if="state === 'invalid'" data-invite-error class="text-center py-4">
        <div class="text-[32px] mb-2">✗</div>
        <h3 class="text-[15px] font-semibold text-notion-error mb-2">链接无效</h3>
        <p class="text-[13px] text-notion-charcoal mb-2">这个邀请链接不存在或格式错误。</p>
        <p class="text-[12px] text-notion-stone">检查链接是否完整，或向管理员要新的。</p>
      </div>

      <div v-else-if="state === 'valid'">
        <div data-invite-banner class="bg-notion-tint-lavender rounded-lg p-3.5 mb-5 flex items-center gap-2.5">
          <div class="w-[38px] h-[38px] rounded-full bg-notion-primary text-notion-on-primary flex items-center justify-center font-semibold text-[16px]">
            {{ inviterInitial }}
          </div>
          <div class="flex-1 min-w-0">
            <div class="text-[13px] text-notion-charcoal"><strong>{{ inviterDisplay }}</strong> 邀请你加入</div>
            <div class="text-[11px] text-notion-slate mt-0.5">{{ user?.email ?? '' }}</div>
          </div>
        </div>

        <h2 class="text-[18px] font-semibold text-notion-ink mb-1">设置你的密码</h2>
        <p class="text-[12px] text-notion-steel mb-4">至少 8 个字符。设好后用邮箱+密码登录。</p>

        <div v-if="errorText" class="mb-3 px-3 py-2 bg-notion-tint-rose border border-notion-hairline rounded-md text-[12px] text-notion-error">
          {{ errorText }}
        </div>

        <form @submit.prevent="onSubmit" class="flex flex-col gap-3">
          <div>
            <label class="block text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel mb-1">新密码</label>
            <input
              data-accept-password
              v-model="password"
              type="password"
              required
              minlength="8"
              autocomplete="new-password"
              class="w-full h-[38px] px-3 bg-notion-canvas border border-notion-hairline-strong rounded-md text-[13px] text-notion-ink focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary"
            />
          </div>
          <div>
            <label class="block text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel mb-1">确认密码</label>
            <input
              data-accept-confirm
              v-model="confirm"
              type="password"
              required
              minlength="8"
              autocomplete="new-password"
              class="w-full h-[38px] px-3 bg-notion-canvas border border-notion-hairline-strong rounded-md text-[13px] text-notion-ink focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary"
            />
            <p v-if="confirm && password !== confirm" class="text-[11px] text-notion-error mt-1">两次密码不一致</p>
          </div>
          <button
            data-accept-submit
            type="submit"
            :disabled="!canSubmit"
            :class="[
              'h-[40px] rounded-md text-[13px] font-medium mt-1 transition-colors',
              canSubmit
                ? 'bg-notion-primary hover:bg-notion-primary-pressed text-notion-on-primary'
                : 'bg-notion-hairline text-notion-muted-text cursor-not-allowed',
            ]"
          >{{ submitting ? '激活中…' : '完成注册并登录' }}</button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const loading = ref(true)
const state = ref('valid')
const user = ref(null)
const inviter = ref(null)
const password = ref('')
const confirm = ref('')
const submitting = ref(false)
const errorText = ref('')

const token = computed(() => {
  const t = route.query.token
  return typeof t === 'string' ? t : ''
})

const canSubmit = computed(
  () => !submitting.value && password.value.length >= 8 && password.value === confirm.value,
)

const inviterDisplay = computed(() => {
  if (!inviter.value) return '管理员'
  return inviter.value.name || inviter.value.email || '管理员'
})

const inviterInitial = computed(() => {
  const s = inviter.value?.name || inviter.value?.email || '?'
  return s.charAt(0).toUpperCase()
})

onMounted(async () => {
  if (!token.value) {
    state.value = 'invalid'
    loading.value = false
    return
  }
  try {
    const data = await auth.fetchInvite(token.value)
    user.value = data.user ?? null
    inviter.value = data.inviter ?? null
    if (data.user === null) {
      state.value = 'invalid'
    } else if (data.expired) {
      state.value = 'expired'
    } else if (!data.valid) {
      state.value = 'used'
    } else {
      state.value = 'valid'
    }
  } catch {
    state.value = 'invalid'
  } finally {
    loading.value = false
  }
})

async function onSubmit() {
  errorText.value = ''
  submitting.value = true
  try {
    await auth.acceptInvite(token.value, password.value)
    router.push('/chat')
  } catch (err) {
    const status = err?.response?.status
    if (status === 410) {
      state.value = 'used'
    } else {
      errorText.value = err?.response?.data?.error ?? err?.message ?? '激活失败'
    }
  } finally {
    submitting.value = false
  }
}

function goLogin() {
  router.push('/login')
}
</script>
