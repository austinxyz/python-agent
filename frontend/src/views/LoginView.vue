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
          <button
            data-google-signin
            type="button"
            :disabled="!gsiReady"
            @click="onGoogleSignIn"
            :class="[
              'h-[40px] rounded-md text-[13px] font-medium bg-notion-canvas border border-notion-hairline-strong flex items-center justify-center gap-2',
              gsiReady ? 'text-notion-charcoal hover:bg-notion-surface' : 'text-notion-muted-text cursor-wait',
            ]"
          >
            <svg v-if="gsiReady" width="16" height="16" viewBox="0 0 18 18">
              <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z" fill="#4285F4"/>
              <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332C2.438 15.983 5.482 18 9 18z" fill="#34A853"/>
              <path d="M3.964 10.71c-.18-.54-.282-1.117-.282-1.71s.102-1.17.282-1.71V4.958H.957C.347 6.173 0 7.548 0 9s.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
              <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0 5.482 0 2.438 2.017.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
            </svg>
            {{ gsiReady ? 'Sign in with Google' : 'Google 登录加载中…' }}
          </button>
        </template>

        <p class="text-[11px] text-notion-stone text-center mt-2">没账号？请管理员发邀请链接</p>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
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
    initGsi(clientId)
    gsiReady.value = true
    return
  }
  const script = document.createElement('script')
  script.id = 'gsi-script'
  script.src = 'https://accounts.google.com/gsi/client'
  script.async = true
  script.defer = true
  script.onload = () => {
    initGsi(clientId)
    gsiReady.value = true
  }
  script.onerror = () => { gsiReady.value = true }  // unblock button even on load failure
  document.head.appendChild(script)
}

function initGsi(clientId) {
  try {
    window.google?.accounts?.id?.initialize({
      client_id: clientId,
      callback: handleGoogleCredential,
      auto_select: false,
      cancel_on_tap_outside: true,
    })
  } catch (e) {
    // initialize() may throw for unauthorized origins; prompt() will surface the error
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

async function onGoogleSignIn() {
  if (!gsiReady.value || !window.google?.accounts?.id) return
  window.google.accounts.id.prompt()
}
</script>
