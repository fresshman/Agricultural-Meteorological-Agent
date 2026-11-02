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
import { useAuthStore } from '@/stores/auth'
import { useLocationStore } from '@/stores/location'

const route = useRoute()
const auth = useAuthStore()
const location = useLocationStore()

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

onMounted(async () => {
  window.addEventListener('resize', onResize)
  // 位置存在账号分桶里，必须先确定身份再恢复，否则会读到未分桶的旧数据
  await auth.fetchMe()
  if (!location.provinces.length) await location.init()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
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
