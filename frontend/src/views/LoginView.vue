<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-brand">
        <span class="login-brand__mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="28" height="28" fill="none">
            <path d="M12 3c3.6 2.4 5.4 5.2 5.4 8.1 0 3.3-2.4 5.9-5.4 5.9s-5.4-2.6-5.4-5.9C6.6 8.2 8.4 5.4 12 3Z" fill="currentColor" opacity="0.18" />
            <path d="M12 21V9M12 13.5c2.2 0 4-1.5 4-3.6M12 16.8c-2.2 0-4-1.4-4-3.4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
          </svg>
        </span>
        <div>
          <h1 class="login-title">农业气象智能体</h1>
          <p class="login-slogan">用一个昵称当账号，问答、地块与农事记录只存在这个账号下</p>
        </div>
      </div>

      <div class="login-modes" role="tablist" aria-label="登录或注册">
        <button
          v-for="tab in TABS"
          :key="tab.value"
          type="button"
          role="tab"
          class="login-mode"
          :class="{ 'is-active': mode === tab.value }"
          :aria-selected="mode === tab.value"
          @click="switchMode(tab.value)"
        >
          {{ tab.label }}
        </button>
      </div>

      <el-alert
        v-if="errorMsg"
        type="error"
        :closable="false"
        show-icon
        :title="errorMsg"
        class="login-alert"
      />

      <el-input
        v-model="nickname"
        class="login-field"
        size="large"
        placeholder="昵称（2–20 个字符）"
        maxlength="20"
        autocomplete="username"
        @keyup.enter="onSubmit"
      />
      <el-input
        v-model="password"
        class="login-field"
        size="large"
        type="password"
        show-password
        placeholder="密码（6–64 位）"
        maxlength="64"
        :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
        @keyup.enter="onSubmit"
      />
      <el-input
        v-if="mode === 'register'"
        v-model="password2"
        class="login-field"
        size="large"
        type="password"
        show-password
        placeholder="再输一次密码"
        maxlength="64"
        autocomplete="new-password"
        @keyup.enter="onSubmit"
      />

      <el-button type="primary" size="large" class="login-btn" :loading="submitting" @click="onSubmit">
        {{ mode === 'login' ? '登录' : '注册并登录' }}
      </el-button>

      <p class="login-tip">
        忘记密码只能换个昵称重新开始；账号与数据只保存在本空间的运行目录，重新部署后会清空。
      </p>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const TABS = [
  { value: 'login', label: '登录' },
  { value: 'register', label: '注册' }
]

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const mode = ref('login')
const nickname = ref('')
const password = ref('')
const password2 = ref('')
const submitting = ref(false)
const errorMsg = ref('')

function redirectTarget() {
  const raw = typeof route.query.redirect === 'string' ? route.query.redirect : ''
  // 只接受站内路径，避免 ?redirect=//evil.com 造成开放重定向
  return raw.startsWith('/') && !raw.startsWith('//') ? raw : '/dashboard'
}

function switchMode(next) {
  if (mode.value === next) return
  mode.value = next
  errorMsg.value = ''
  password.value = ''
  password2.value = ''
}

/** 与后端保持同一套长度约束，先在本地拦掉，省一次往返 */
function validate() {
  const name = nickname.value.trim()
  if (name.length < 2 || name.length > 20) return '昵称需为 2–20 个字符'
  if (password.value.length < 6 || password.value.length > 64) return '密码需为 6–64 位'
  if (mode.value === 'register' && password.value !== password2.value) return '两次输入的密码不一致'
  return ''
}

async function onSubmit() {
  if (submitting.value) return
  const problem = validate()
  if (problem) {
    errorMsg.value = problem
    return
  }
  errorMsg.value = ''
  submitting.value = true
  const name = nickname.value.trim()
  try {
    if (mode.value === 'register') {
      await auth.register(name, password.value)
      ElMessage.success('注册成功')
    } else {
      await auth.login(name, password.value)
    }
    // 整页跳转而不是 SPA 路由跳转：保证各 store 都按新账号重新初始化
    window.location.assign(redirectTarget())
  } catch (err) {
    errorMsg.value = err?.message || '登录失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  if (!auth.checked) await auth.fetchMe()
  if (auth.user) router.replace(redirectTarget())
})
</script>

<style scoped>
.login-page {
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background:
    radial-gradient(1200px 600px at 50% -10%, color-mix(in srgb, var(--brand-500) 10%, transparent), transparent 60%),
    var(--bg-page);
}

.login-card {
  width: 100%;
  max-width: 420px;
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg, 16px);
  padding: 32px 28px;
  box-shadow: 0 12px 40px rgba(15, 23, 42, 0.08);
}

.login-brand {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 22px;
}

.login-brand__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: var(--radius-icon, 14px);
  background: var(--brand-50);
  color: var(--brand-500);
  flex: 0 0 auto;
}

html.dark .login-brand__mark {
  background: color-mix(in srgb, var(--brand-500) 16%, transparent);
}

.login-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: var(--text-title);
}

.login-slogan {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--text-disabled);
  line-height: 1.5;
}

/* ---- 登录 / 注册 分段控件 ---- */
.login-modes {
  display: flex;
  gap: 4px;
  padding: 4px;
  margin-bottom: 18px;
  background: var(--bg-page);
  border: 1px solid var(--border-light);
  border-radius: 10px;
}

.login-mode {
  flex: 1;
  height: 34px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--text-secondary);
  font-family: inherit;
  font-size: var(--fs-body);
  font-weight: 500;
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease);
}

.login-mode:hover {
  color: var(--text-title);
}

.login-mode.is-active {
  background: var(--bg-card);
  color: var(--brand-600);
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
}

.login-alert {
  margin-bottom: 14px;
}

.login-field {
  margin-bottom: 12px;
}

.login-btn {
  width: 100%;
  margin-top: 6px;
}

.login-tip {
  margin: 14px 0 0;
  font-size: 12px;
  color: var(--text-disabled);
  line-height: 1.6;
}
</style>
