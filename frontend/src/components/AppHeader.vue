<template>
  <header class="app-header">
    <div class="app-header__inner">
      <router-link to="/dashboard" class="brand" aria-label="农业气象智能体首页">
        <span class="brand__mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none">
            <path
              d="M12 3c3.6 2.4 5.4 5.2 5.4 8.1 0 3.3-2.4 5.9-5.4 5.9s-5.4-2.6-5.4-5.9C6.6 8.2 8.4 5.4 12 3Z"
              fill="currentColor"
              opacity="0.18"
            />
            <path
              d="M12 21V9M12 13.5c2.2 0 4-1.5 4-3.6M12 16.8c-2.2 0-4-1.4-4-3.4"
              stroke="currentColor"
              stroke-width="1.6"
              stroke-linecap="round"
            />
          </svg>
        </span>
        <span class="brand__text">
          <span class="brand__title">农业气象智能体</span>
          <span class="brand__slogan">AgriMet Agent · 看天种地</span>
        </span>
      </router-link>

      <LocationSelector class="app-header__loc" :icon-only="isNarrow" @changed="onLocationChanged" />

      <nav class="nav" aria-label="主导航">
        <router-link
          v-for="item in NAV_ITEMS"
          :key="item.path"
          :to="item.path"
          class="nav__item"
          :class="{ 'is-active': isActive(item.path) }"
        >
          <el-icon :size="16"><component :is="item.icon" /></el-icon>
          <span>{{ item.title }}</span>
        </router-link>
      </nav>

      <div class="app-header__actions">
        <ThemeToggle />
        <el-dropdown v-if="auth.user" class="app-header__user" trigger="click">
          <button class="icon-button user-chip" type="button" aria-label="账户菜单">
            <el-avatar :size="26" :src="auth.user.avatar || undefined">{{ avatarText }}</el-avatar>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled>{{ auth.user.nickname }}</el-dropdown-item>
              <el-dropdown-item divided @click="onSwitchAccount">切换魔搭账号</el-dropdown-item>
              <el-dropdown-item @click="onLogout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <button
          v-if="showHamburger"
          class="icon-button"
          type="button"
          aria-label="打开导航菜单"
          @click="emit('open-menu')"
        >
          <el-icon :size="20"><Menu /></el-icon>
        </button>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { NAV_ITEMS } from '@/router'
import LocationSelector from '@/components/LocationSelector.vue'
import ThemeToggle from '@/components/ThemeToggle.vue'
import { useAuthStore } from '@/stores/auth'
import { startModelScopeLogin } from '@/utils/oauth'

const props = defineProps({
  /** 当前视口宽度（由 App.vue 传入，用于切换紧凑模式） */
  viewportWidth: { type: Number, default: 1440 }
})

const emit = defineEmits(['open-menu', 'location-changed'])

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const isNarrow = computed(() => props.viewportWidth < 768)
const showHamburger = computed(() => props.viewportWidth < 992)
const avatarText = computed(() => (auth.user?.nickname || '众').slice(0, 1))

/** 当前路由是否命中（支持子路径高亮，如 /farm/xxx） */
function isActive(path) {
  return route.path === path || route.path.startsWith(`${path}/`)
}

function onLocationChanged() {
  emit('location-changed')
}

async function onLogout() {
  await auth.logout()
  router.push('/login')
}

/**
 * 切换账号：带 prompt=login 重新发起授权。
 * 魔搭授权页用的是浏览器里 modelscope.cn 的登录态，不在本应用内，
 * 所以若魔搭侧仍返回原账号，需要先在 modelscope.cn 退出。
 */
function onSwitchAccount() {
  const { popup } = startModelScopeLogin({ switchAccount: true, next: route.fullPath })
  ElMessage.info(
    popup
      ? '已在新窗口打开魔搭授权页，完成授权后自动切换账号'
      : '正在跳转魔搭授权页…'
  )
}
</script>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  width: 100%;
  height: var(--header-h);
  background: color-mix(in srgb, var(--bg-card) 78%, transparent);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-light);
}

.app-header__inner {
  display: flex;
  align-items: center;
  gap: var(--sp-4);
  height: 100%;
  max-width: var(--container-max);
  margin: 0 auto;
  padding: 0 var(--sp-6);
}

/* ---- 品牌区 ---- */
.brand {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  flex: 0 0 auto;
  color: inherit;
}

.brand__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-icon);
  background: var(--brand-50);
  color: var(--brand-500);
}

html.dark .brand__mark {
  background: color-mix(in srgb, var(--brand-500) 16%, transparent);
}

.brand__text {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}

.brand__title {
  font-size: var(--fs-h4);
  font-weight: 700;
  color: var(--text-title);
  letter-spacing: 0.2px;
}

.brand__slogan {
  font-size: var(--fs-caption);
  color: var(--text-disabled);
  letter-spacing: 0.4px;
}

.app-header__loc {
  flex: 0 0 auto;
}

/* ---- 主导航（自绘，非 el-menu：选中态为 2px 主色下划线） ---- */
.nav {
  display: flex;
  align-items: center;
  gap: var(--sp-1);
  margin-left: auto;
}

.nav__item {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: var(--header-h);
  padding: 0 var(--sp-3);
  font-size: var(--fs-body);
  font-weight: 500;
  color: var(--text-secondary);
  transition: color var(--dur-fast) var(--ease);
}

.nav__item:hover {
  color: var(--text-title);
}

.nav__item.is-active {
  color: var(--brand-600);
  font-weight: 600;
}

.nav__item.is-active::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: 10px;
  width: 24px;
  height: 2px;
  border-radius: 2px;
  background: var(--brand-500);
  transform: translateX(-50%);
}

.app-header__actions {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex: 0 0 auto;
}

.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-full);
  background: var(--bg-card);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease);
}

.icon-button:hover {
  color: var(--brand-500);
  border-color: var(--brand-300);
}

/* ---- 响应式 ---- */
@media (max-width: 1199px) {
  .app-header__inner {
    padding: 0 var(--sp-5);
    gap: var(--sp-3);
  }
}

@media (max-width: 991px) {
  .nav {
    display: none;
  }

  .app-header__loc {
    margin-left: auto;
  }
}

@media (max-width: 767px) {
  .app-header__inner {
    padding: 0 var(--gutter-mobile);
    gap: var(--sp-2);
  }

  .brand__text {
    display: none;
  }
}
</style>
