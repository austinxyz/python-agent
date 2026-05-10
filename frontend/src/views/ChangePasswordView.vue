<template>
  <!-- ChangePasswordView — multi-user-auth-core. Mock anchor #change-password. -->
  <div class="h-full flex items-center justify-center bg-notion-surface-soft px-4 py-8">
    <div class="w-full max-w-[480px] bg-notion-canvas border border-notion-hairline rounded-xl shadow-sm p-8">
      <h2 class="text-[18px] font-semibold text-notion-ink mb-1">修改密码</h2>
      <p class="text-[12px] text-notion-steel mb-5">改完密码会立即生效。</p>

      <div v-if="successText" data-change-success class="mb-3 px-3 py-2 bg-notion-tint-mint border border-notion-hairline rounded-md text-[12px] text-notion-brand-green">
        {{ successText }}
      </div>
      <div v-if="errorText" data-change-error class="mb-3 px-3 py-2 bg-notion-tint-rose border border-notion-hairline rounded-md text-[12px] text-notion-error">
        {{ errorText }}
      </div>

      <form @submit.prevent="onSubmit" class="flex flex-col gap-3">
        <div>
          <label class="block text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel mb-1">当前密码</label>
          <input
            data-old-password
            v-model="oldPw"
            type="password"
            required
            autocomplete="current-password"
            class="w-full h-[38px] px-3 bg-notion-canvas border border-notion-hairline-strong rounded-md text-[13px] text-notion-ink focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary"
          />
        </div>
        <div>
          <label class="block text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel mb-1">新密码</label>
          <input
            data-new-password
            v-model="newPw"
            type="password"
            required
            minlength="8"
            autocomplete="new-password"
            class="w-full h-[38px] px-3 bg-notion-canvas border border-notion-hairline-strong rounded-md text-[13px] text-notion-ink focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary"
          />
          <p class="text-[10px] text-notion-stone mt-1">至少 8 字符。建议混合字母+数字。</p>
        </div>
        <div>
          <label class="block text-[11px] font-semibold uppercase tracking-[0.08em] text-notion-steel mb-1">确认新密码</label>
          <input
            data-confirm-password
            v-model="confirmPw"
            type="password"
            required
            minlength="8"
            autocomplete="new-password"
            class="w-full h-[38px] px-3 bg-notion-canvas border border-notion-hairline-strong rounded-md text-[13px] text-notion-ink focus:outline-none focus:border-notion-primary focus:ring-1 focus:ring-notion-primary"
          />
          <p v-if="confirmPw && newPw !== confirmPw" class="text-[11px] text-notion-error mt-1">两次密码不一致</p>
        </div>
        <div class="flex gap-2 mt-2">
          <button
            type="button"
            class="flex-1 h-[38px] bg-notion-canvas border border-notion-hairline-strong rounded-md text-[13px]"
            @click="$router.back()"
          >取消</button>
          <button
            data-change-submit
            type="submit"
            :disabled="!canSubmit"
            :class="[
              'flex-1 h-[38px] rounded-md text-[13px] font-medium',
              canSubmit
                ? 'bg-notion-primary hover:bg-notion-primary-pressed text-notion-on-primary'
                : 'bg-notion-hairline text-notion-muted-text cursor-not-allowed',
            ]"
          >{{ submitting ? '保存中…' : '保存' }}</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '../stores/auth.js'

const auth = useAuthStore()

const oldPw = ref('')
const newPw = ref('')
const confirmPw = ref('')
const submitting = ref(false)
const errorText = ref('')
const successText = ref('')

const canSubmit = computed(
  () => !submitting.value && newPw.value.length >= 8 && newPw.value === confirmPw.value,
)

async function onSubmit() {
  errorText.value = ''
  successText.value = ''
  submitting.value = true
  try {
    await auth.changePassword(oldPw.value, newPw.value)
    successText.value = '✓ 密码已更新'
    oldPw.value = ''
    newPw.value = ''
    confirmPw.value = ''
  } catch (err) {
    errorText.value = err?.response?.data?.error ?? err?.message ?? '修改失败'
  } finally {
    submitting.value = false
  }
}
</script>
