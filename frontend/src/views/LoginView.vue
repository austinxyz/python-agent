<template>
  <!--
    LoginView — multi-user-auth-core. Renders inside AppLayout main pane
    (sidebar visible). Mock anchor: docs/superpowers/specs/mocks/2026-05-09-
    multi-user-auth-mocks.html#login-flow.
  -->
  <div data-login-view class="h-full flex items-center justify-center bg-notion-surface-soft px-4 py-8">
    <div class="w-full max-w-[380px] bg-notion-canvas border border-notion-hairline rounded-xl shadow-sm p-8">
      <!-- Brand block -->
      <div class="text-center mb-6">
        <div class="inline-flex w-[52px] h-[52px] rounded-xl bg-notion-brand-navy text-notion-on-dark items-center justify-center text-[22px] font-semibold">知</div>
        <h2 class="text-[20px] font-semibold text-notion-ink mt-3 mb-1">登录</h2>
        <p class="text-[13px] text-notion-steel">使用邮箱密码 或 Google 账号</p>
      </div>

      <!-- Error banner -->
      <div v-if="errorText" data-login-error class="mb-3 px-3 py-2 bg-notion-tint-rose border border-notion-hairline rounded-md text-[12px] text-notion-error">
        {{ errorText }}
      </div>

      <!-- Form -->
      <form @submit.prevent="onSubmit" class="flex flex-col gap-3">
        <div>
          <label class="block text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel mb-1">邮箱</label>
          <input
            data-login-email
            v-model="email"
            type="email"
            required
            autocomplete="username"
            placeholder="austin.xyz@gmail.com"
            class="w-full h-[38px] px-3 bg-notion-canvas border border-notion-hairline-strong rounded-md text-[13px] text-notion-ink placeholder:text-notion-stone focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary"
          />
        </div>
        <div>
          <label class="block text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel mb-1">密码</label>
          <input
            data-login-password
            v-model="password"
            type="password"
            required
            autocomplete="current-password"
            placeholder="••••••••"
            class="w-full h-[38px] px-3 bg-notion-canvas border border-notion-hairline-strong rounded-md text-[13px] text-notion-ink placeholder:text-notion-stone focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary"
          />
        </div>
        <button
          data-login-submit
          type="submit"
          :disabled="submitting"
          :class="[
            'h-[40px] rounded-md text-[13px] font-medium mt-1 transition-colors',
            submitting
              ? 'bg-notion-hairline text-notion-muted-text cursor-not-allowed'
              : 'bg-notion-primary hover:bg-notion-primary-pressed text-notion-on-primary',
          ]"
        >{{ submitting ? '登录中…' : '登录' }}</button>

        <!-- Divider + GSI button (conditional on HTTPS / localhost AND has_google) -->
        <template v-if="showGoogle">
          <div class="flex items-center gap-2 my-2 text-[11px] text-notion-stone">
            <div class="flex-1 h-px bg-notion-hairline"></div>
            <span>或</span>
            <div class="flex-1 h-px bg-notion-hairline"></div>
          </div>
          <!-- Google renders its official button here via renderButton() -->
          <div
            v-if="gsiReady"
            ref="googleBtnContainer"
            data-google-signin
            class="flex justify-center"
          ></div>
          <div
            v-else
            data-google-signin
            class="h-[40px] rounded-md text-[13px] text-notion-muted-text bg-notion-canvas border border-notion-hairline-strong flex items-center justify-center"
          >Google 登录加载中…</div>
        </template>

        <p class="text-[11px] text-notion-stone text-center mt-2">没账号？请管理员发邀请链接</p>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { safeRedirect } from '../utils/safe-redirect.js'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const submitting = ref(false)
const errorText = ref('')
const gsiReady = ref(false)
const googleBtnContainer = ref(null)

onMounted(() => {
  if (auth.config === null) {
    auth.fetchConfig()
  }
})

watch(() => auth.config, (cfg) => {
  if (cfg?.has_google && cfg?.google_client_id) {
    loadGsi(cfg.google_client_id)
  }
}, { immediate: true })

function loadGsi(clientId) {
  if (typeof window === 'undefined') return
  if (document.getElementById('gsi-script')) {
    gsiReady.value = true
    nextTick(() => initGsi(clientId))
    return
  }
  const script = document.createElement('script')
  script.id = 'gsi-script'
  script.src = 'https://accounts.google.com/gsi/client'
  script.async = true
  script.defer = true
  script.onload = () => {
    gsiReady.value = true
    nextTick(() => initGsi(clientId))
  }
  script.onerror = () => { gsiReady.value = true }
  document.head.appendChild(script)
}

function initGsi(clientId) {
  try {
    window.google?.accounts?.id?.initialize({
      client_id: clientId,
      callback: handleGoogleCredential,
      auto_select: false,
    })
    if (googleBtnContainer.value) {
      window.google.accounts.id.renderButton(googleBtnContainer.value, {
        type: 'standard',
        theme: 'outline',
        size: 'large',
        text: 'signin_with',
        shape: 'rectangular',
        width: googleBtnContainer.value.offsetWidth || 320,
        locale: 'zh-CN',
      })
    }
  } catch (e) {
    // initialize/renderButton may throw for unauthorized origins
  }
}

async function handleGoogleCredential(response) {
  errorText.value = ''
  submitting.value = true
  try {
    await auth.loginWithGoogle(response.credential)
    router.push(safeRedirect(route.query.redirect))
  } catch (err) {
    errorText.value = err?.response?.data?.error ?? err?.message ?? 'Google 登录失败'
  } finally {
    submitting.value = false
  }
}

const isLocalhost = computed(() => {
  const h = typeof window !== 'undefined' ? window.location?.hostname ?? '' : ''
  return h === 'localhost' || h === '127.0.0.1'
})

const isHttps = computed(() => {
  return typeof window !== 'undefined' && window.location?.protocol === 'https:'
})

const showGoogle = computed(() => {
  return Boolean(auth.config?.has_google) && (isHttps.value || isLocalhost.value)
})

async function onSubmit() {
  errorText.value = ''
  submitting.value = true
  try {
    await auth.loginWithPassword(email.value.trim(), password.value)
    router.push(safeRedirect(route.query.redirect))
  } catch (err) {
    errorText.value = err?.response?.data?.error ?? err?.message ?? '登录失败'
  } finally {
    submitting.value = false
  }
}

</script>
