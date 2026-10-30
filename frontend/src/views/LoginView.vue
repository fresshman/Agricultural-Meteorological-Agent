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
          <p class="login-slogan">登录后，你的大豆问答、地块与农事记录都会单独保存在你的账户下</p>
        </div>
      </div>

      <el-alert
        v-if="route.query.err === 'oauth_failed'"
        type="error"
        :closable="false"
        show-icon
        title="魔搭授权失败"
        description="请重试，或改用演示登录。"
        class="login-alert"
      />

      <template v-if="auth.user">
        <div class="login-user">
          <el-avatar :size="44" :src="auth.user.avatar || undefined">{{ avatarText }}</el-avatar>
          <div class="login-user__meta">
            <div class="login-user__name">{{ auth.user.nickname }}</div>
            <div class="login-user__sub">已登录 · 数据已隔离到你的账户</div>
          </div>
        </div>
        <el-button type="primary" class="login-btn" @click="goHome">进入工作台</el-button>
        <el-button class="login-btn" plain @click="onLogout">退出登录</el-button>
      </template>

      <template v-else>
        <el-button
          type="primary"
          class="login-btn"
          size="large"
          :loading="oauthPending"
          @click="openModelScopeLogin"
        >
          <svg class="login-btn__logo" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
            <path d="M12 2 3 7v10l9 5 9-5V7l-9-5Zm0 2.3 6.9 3.8L12 11.9 5.1 8.1 12 4.3ZM5 9.9l6 3.3v6.6l-6-3.3V9.9Zm8 9.9v-6.6l6-3.3v6.6l-6 3.3Z" fill="currentColor" />
          </svg>
          使用魔搭（ModelScope）账号登录
        </el-button>
        <p v-if="oauthPending" class="login-tip login-tip--pending">
          已在新窗口打开魔搭授权页，完成授权后本页会自动进入工作台。
        </p>

        <div class="login-divider"><span>或</span></div>

        <div class="login-dev">
          <el-input
            v-model="nickname"
            placeholder="输入昵称用于演示登录"
            maxlength="20"
            class="login-dev__input"
            @keyup.enter="onDevLogin"
          />
          <el-button class="login-dev__btn" @click="onDevLogin" :loading="devLoading">演示登录</el-button>
        </div>
        <p class="login-tip">演示登录仅用于本地/未配置 OAuth 时体验，生产环境建议用魔搭账号。</p>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const nickname = ref('')
const devLoading = ref(false)
/** 已在弹窗里发起魔搭授权，等待回调页通知 */
const oauthPending = ref(false)

const avatarText = computed(() => (auth.user?.nickname || '众').slice(0, 1))

function redirectTarget() {
  const raw = typeof route.query.redirect === 'string' ? route.query.redirect : ''
  // 只接受站内路径，避免 ?redirect=//evil.com 造成开放重定向
  return raw.startsWith('/') && !raw.startsWith('//') ? raw : '/dashboard'
}

function goHome() {
  router.replace(redirectTarget())
}

/**
 * 登录成功后整页跳转而不是 SPA 路由跳转：
 * 保证 farm / chat / weather 等 store 全部按新用户重新初始化，不残留上一个账号的数据。
 */
function enterAsUser() {
  window.location.assign(redirectTarget())
}

/** 创空间页面运行在 iframe 里，授权必须在新窗口完成，否则 state cookie 会被浏览器丢弃 */
function openModelScopeLogin() {
  const url = '/api/auth/modelscope'
  // 独立标签页访问（studio 域名直连）时不需要弹窗，直接走整页跳转
  if (window.self === window.top) {
    window.location.href = url
    return
  }
  let win = null
  try {
    win = window.open(url, 'agri_modelscope_login', 'width=520,height=680')
  } catch (err) {
    win = null
  }
  if (!win) {
    // 弹窗被拦截：退化为当前窗口跳转，回调页结束时会自行进入工作台
    window.location.href = url
    return
  }
  oauthPending.value = true
}

function onAuthMessage(e) {
  if (e.origin !== window.location.origin) return
  const data = e.data
  if (data && data.type === 'agri:auth' && data.ok) finishLogin()
}

function onAuthStorage(e) {
  if (e.key === 'agri:auth') finishLogin()
}

let finishing = false
async function finishLogin() {
  if (finishing) return
  finishing = true
  await auth.fetchMe()
  finishing = false
  if (auth.user) enterAsUser()
  else oauthPending.value = false
}

onMounted(async () => {
  window.addEventListener('message', onAuthMessage)
  window.addEventListener('storage', onAuthStorage)
  if (!auth.checked) await auth.fetchMe()
  // 已登录直接进工作台
  if (auth.user && route.query.err !== 'oauth_failed') goHome()
})

onBeforeUnmount(() => {
  window.removeEventListener('message', onAuthMessage)
  window.removeEventListener('storage', onAuthStorage)
})

async function onDevLogin() {
  const name = nickname.value.trim()
  if (!name) {
    ElMessage.warning('请输入昵称')
    return
  }
  devLoading.value = true
  try {
    await auth.devLogin(name)
    ElMessage.success('登录成功')
    enterAsUser()
  } catch (err) {
    ElMessage.error(err?.message || '演示登录失败')
  } finally {
    devLoading.value = false
  }
}

async function onLogout() {
  await auth.logout()
  ElMessage.success('已退出登录')
}
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

.login-alert {
  margin-bottom: 18px;
}

.login-btn {
  width: 100%;
  margin-top: 8px;
}

.login-btn__logo {
  margin-right: 6px;
}

.login-tip--pending {
  margin-top: 10px;
  color: var(--brand-500);
}

.login-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 18px 0;
  color: var(--text-disabled);
  font-size: 12px;
}

.login-divider::before,
.login-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border-light);
}

.login-dev {
  display: flex;
  gap: 8px;
}

.login-dev__input {
  flex: 1;
}

.login-tip {
  margin: 12px 0 0;
  font-size: 12px;
  color: var(--text-disabled);
  line-height: 1.5;
}

.login-user {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md, 12px);
  margin-bottom: 16px;
}

.login-user__name {
  font-weight: 600;
  color: var(--text-title);
}

.login-user__sub {
  font-size: 12px;
  color: var(--text-disabled);
}
</style>
