<template>
  <div class="app-shell">
    <AppHeader :viewport-width="viewportWidth" @open-menu="menuOpen = true" />

    <main class="app-content">
      <router-view v-slot="{ Component }">
        <transition name="route-fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <AppNavDrawer v-model="menuOpen" />
    <AppTabBar />
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import AppNavDrawer from '@/components/AppNavDrawer.vue'
import AppTabBar from '@/components/AppTabBar.vue'
import { useLocationStore } from '@/stores/location'

const route = useRoute()
const location = useLocationStore()

/** 当前视口宽度，驱动顶栏/导航的形态切换 */
const viewportWidth = ref(typeof window === 'undefined' ? 1440 : window.innerWidth)
const menuOpen = ref(false)

function onResize() {
  viewportWidth.value = window.innerWidth
  // 放大到桌面宽度时自动收起抽屉，避免残留遮罩
  if (window.innerWidth >= 992) menuOpen.value = false
}

onMounted(async () => {
  window.addEventListener('resize', onResize)
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
}
</style>
