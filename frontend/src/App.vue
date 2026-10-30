<template>
  <div class="app-shell" :class="{ 'app-shell--gate': isGate }">
    <AppHeader v-if="!isGate" :viewport-width="viewportWidth" @open-menu="menuOpen = true" />

    <main class="app-content">
      <router-view v-slot="{ Component }">
        <transition name="route-fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <AppNavDrawer v-if="!isGate" v-model="menuOpen" />
    <AppTabBar v-if="!isGate" />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import AppNavDrawer from '@/components/AppNavDrawer.vue'
import AppTabBar from '@/components/AppTabBar.vue'
import { useLocationStore } from '@/stores/location'
import { useAuthStore } from '@/stores/auth'
import { markEntryVerified } from '@/utils/oauth'

const route = useRoute()
const location = useLocationStore()
const auth = useAuthStore()

/** 当前视口宽度，驱动顶栏/导航的形态切换 */
const viewportWidth = ref(typeof window === 'undefined' ? 1440 : window.innerWidth)
const menuOpen = ref(false)
/** 登录/核验页是独立整页，不显示顶栏与导航（否则点了也是被弹回登录页） */
const isGate = computed(() => route.path === '/login')

function onResize() {
  viewportWidth.value = window.innerWidth
  // 放大到桌面宽度时自动收起抽屉，避免残留遮罩
  if (window.innerWidth >= 992) menuOpen.value = false
}

/**
 * 授权回调页（新窗口）通过 postMessage / localStorage 通知登录完成。
 * 放在应用外壳里而不是登录页：切换账号时用户可能停在任何页面。
 * 刷新整页，保证各 store 都按新账号重新初始化。
 */
let authSyncing = false
async function syncAuth() {
  if (authSyncing) return
  authSyncing = true
  await auth.fetchMe()
  if (auth.user) {
    // 刚完成一次授权核验，给刷新后的页面留一次性通行证，避免又被拦到登录页
    markEntryVerified()
    window.location.reload()
    return
  }
  authSyncing = false
}

function onAuthMessage(e) {
  if (e.origin !== window.location.origin) return
  if (e.data && e.data.type === 'agri:auth' && e.data.ok) syncAuth()
}

function onAuthStorage(e) {
  if (e.key === 'agri:auth') syncAuth()
}

onMounted(async () => {
  window.addEventListener('resize', onResize)
  window.addEventListener('message', onAuthMessage)
  window.addEventListener('storage', onAuthStorage)
  if (!location.provinces.length) await location.init()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('message', onAuthMessage)
  window.removeEventListener('storage', onAuthStorage)
})

// 路由切换后关闭移动抽屉
watch(() => route.fullPath, () => {
  menuOpen.value = false
})
</script>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  min-height: 100dvh;
  background: var(--bg-page);
}

.app-content {
  position: relative;
  flex: 1 1 auto;
  width: 100%;
  min-width: 0;
}

/* <768px 时给底部 TabBar 让位，避免内容被遮挡 */
@media (max-width: 767px) {
  .app-content {
    padding-bottom: var(--tabbar-h);
  }

  /* 登录/核验页没有 TabBar，不留白 */
  .app-shell--gate .app-content {
    padding-bottom: 0;
  }
}
</style>
